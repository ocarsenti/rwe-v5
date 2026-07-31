"""
kb_candidates — mémoire des candidats d'enrichissement de la KB du mode design.

Lit engine_diagnostics (domain, primary_endpoint — déjà collectés par
retrofill.py à chaque cas ingéré), normalise le domaine via
epistemic_core._DOMAIN_MAP (LA MÊME table que design_mode utilise déjà en
production — pas une règle de normalisation inventée séparément), et propose
chaque paire (domaine normalisé, endpoint) encore jamais vue.

Ne modifie JAMAIS _OUTCOME_KB automatiquement : chaque candidat reste
'proposed' jusqu'à une décision humaine explicite. Cette décision est
mémorisée — un candidat rejeté ne revient plus au prochain scan, même après
un nouveau retrofill (règle 3 discutée avec Olivier : mémoire de décision,
pas juste dédoublonnage).

Usage :
    python3 kb_candidates.py scan               # ingère les nouveaux candidats
    python3 kb_candidates.py list                # liste les candidats 'proposed', groupés par domaine
    python3 kb_candidates.py accept <id> [note]
    python3 kb_candidates.py reject <id> [note]
"""
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour importer epistemic_core
from epistemic_core import _DOMAIN_MAP

DB_PATH = Path(os.environ.get(
    "EVIDENCEABLE_PATTERNS_DB",
    str(Path(__file__).resolve().parent / "patterns.db"),
))

SCHEMA = """
CREATE TABLE IF NOT EXISTS kb_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_raw TEXT NOT NULL,
    domain_normalized TEXT NOT NULL,
    endpoint_text TEXT NOT NULL,
    source_case_labels TEXT,
    status TEXT NOT NULL DEFAULT 'proposed',  -- proposed / accepted / rejected
    first_seen_at TEXT,
    reviewed_at TEXT,
    reviewer_note TEXT,
    UNIQUE(domain_normalized, endpoint_text)
);
"""


def normalize_domain(domain_raw: str) -> str:
    """Réutilise EXACTEMENT _DOMAIN_MAP (epistemic_core.py), déjà utilisée en
    production par design_mode — pas une seconde règle divergente. Si le
    domaine brut n'y figure pas encore, retombe sur la chaîne elle-même en
    minuscules plutôt que de perdre le candidat : mieux vaut un groupe
    "non normalisé" visible qu'une perte silencieuse."""
    if not domain_raw:
        return "(domaine non renseigné)"
    return _DOMAIN_MAP.get(domain_raw.strip().lower(), domain_raw.strip().lower())


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def scan():
    """Propose chaque (domaine normalisé, endpoint) pas encore vu. Un
    candidat déjà présent — proposed, accepted OU rejected — ne revient
    jamais : c'est la mémoire de décision. S'il est revu sur un nouveau cas,
    seule sa liste de cas source s'étend, jamais son statut."""
    conn = _connect()
    rows = conn.execute(
        "SELECT case_label, domain, primary_endpoint FROM engine_diagnostics "
        "WHERE domain IS NOT NULL AND primary_endpoint IS NOT NULL"
    ).fetchall()

    now = datetime.now(timezone.utc).isoformat()
    n_new = n_seen = 0
    for row in rows:
        domain_raw = row["domain"]
        domain_norm = normalize_domain(domain_raw)
        endpoint_text = row["primary_endpoint"]

        existing = conn.execute(
            "SELECT id, source_case_labels FROM kb_candidates "
            "WHERE domain_normalized = ? AND endpoint_text = ?",
            (domain_norm, endpoint_text),
        ).fetchone()

        if existing:
            n_seen += 1
            labels = set((existing["source_case_labels"] or "").split(",")) - {""}
            if row["case_label"] not in labels:
                labels.add(row["case_label"])
                conn.execute(
                    "UPDATE kb_candidates SET source_case_labels = ? WHERE id = ?",
                    (",".join(sorted(labels)), existing["id"]),
                )
        else:
            conn.execute(
                "INSERT INTO kb_candidates "
                "(domain_raw, domain_normalized, endpoint_text, source_case_labels, status, first_seen_at) "
                "VALUES (?, ?, ?, ?, 'proposed', ?)",
                (domain_raw, domain_norm, endpoint_text, row["case_label"], now),
            )
            n_new += 1

    conn.commit()
    conn.close()
    print(f"{n_new} nouveau(x) candidat(s), {n_seen} déjà connu(s) (statut inchangé, non redemandés).")


def list_proposed():
    conn = _connect()
    rows = conn.execute(
        "SELECT id, domain_raw, domain_normalized, endpoint_text, source_case_labels "
        "FROM kb_candidates WHERE status = 'proposed' "
        "ORDER BY domain_normalized, id"
    ).fetchall()
    conn.close()

    if not rows:
        print("Aucun candidat en attente.")
        return

    current_domain = None
    for r in rows:
        if r["domain_normalized"] != current_domain:
            current_domain = r["domain_normalized"]
            print(f"\n=== {current_domain} ===")
        print(f"  [{r['id']}] {r['endpoint_text']}")
        print(f"       domaine brut : {r['domain_raw']!r} · cas source : {r['source_case_labels']}")


def decide(candidate_id: int, status: str, note: str = ""):
    assert status in ("accepted", "rejected")
    conn = _connect()
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "UPDATE kb_candidates SET status = ?, reviewed_at = ?, reviewer_note = ? WHERE id = ?",
        (status, now, note, candidate_id),
    )
    conn.commit()
    if cur.rowcount == 0:
        print(f"Aucun candidat avec l'id {candidate_id}.")
    else:
        print(f"Candidat {candidate_id} marqué {status}.")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "scan":
        scan()
    elif cmd == "list":
        list_proposed()
    elif cmd == "accept":
        decide(int(sys.argv[2]), "accepted", " ".join(sys.argv[3:]))
    elif cmd == "reject":
        decide(int(sys.argv[2]), "rejected", " ".join(sys.argv[3:]))
    else:
        print(__doc__)
        sys.exit(1)
