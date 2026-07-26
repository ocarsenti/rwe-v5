"""
Retro-fill script — Option A
Ingère les analyses déjà produites (data/structured/*.json de cnedimts_analysis
+ les diagnostics moteur de rwe-v5) dans une base SQLite interrogeable.

IMPORTANT — ordre d'exécution : ce script régénère patterns.db entièrement à
chaque lancement (DB_PATH.unlink au début). classify_device_category.py doit
donc TOUJOURS être relancé juste après, sinon la colonne device_category
n'existe plus dans la base fraîchement recréée :

    python3 retrofill.py && python3 classify_device_category.py

Sources ingérées :
  - opinions_structured.json : 20 dossiers avec device_type, decision, sa_level,
    et critiques méthodologiques par catégorie
  - mf_analysis_100_v2.json  : 94 dossiers avec motifs de refus détectés (MF_A..MF_E)

Usage :
    python3 retrofill.py
Produit :
    patterns.db (SQLite)
"""

import json
import sqlite3
from pathlib import Path
import os

# cnedimts_analysis est un dépôt frère de rwe-v5 (même parent). Surchargeable
# via variable d'environnement si l'organisation locale diffère.
_THIS_DIR = Path(os.path.dirname(os.path.abspath(__file__)))  # rwe-v5/learning
_RWE_DIR = _THIS_DIR.parent  # rwe-v5

DATA_DIR = Path(os.environ.get(
    "EVIDENCEABLE_CNEDIMTS_ANALYSIS_DIR",
    str(_RWE_DIR.parent / "cnedimts_analysis"),
)) / "data" / "structured"

DB_PATH = Path(os.environ.get(
    "EVIDENCEABLE_PATTERNS_DB",
    str(_THIS_DIR / "patterns.db"),
))

SCHEMA = """
CREATE TABLE IF NOT EXISTS dossiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,              -- 'opinions_structured' ou 'mf_analysis'
    code_dossier TEXT,                 -- présent seulement pour mf_analysis
    device_name TEXT,
    device_type TEXT,                  -- LPPR / PECAN / LATM (voie réglementaire)
    company TEXT,
    year INTEGER,
    decision TEXT,                     -- FAVORABLE / DEFAVORABLE / INDETERMINE
    sa_level TEXT,
    device_category TEXT,
    device_category_confidence TEXT,
    is_primary BOOLEAN,
    UNIQUE(source, device_name, code_dossier)
);

CREATE TABLE IF NOT EXISTS criticisms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dossier_id INTEGER REFERENCES dossiers(id),
    criticism_type TEXT NOT NULL,      -- ex: absence_bras_controle, biais_mesure
    excerpt TEXT
);

CREATE TABLE IF NOT EXISTS motifs_refus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dossier_id INTEGER REFERENCES dossiers(id),
    motif_code TEXT NOT NULL,          -- MF_A, MF_B, MF_C, MF_D, MF_E
    tcat_code TEXT,                    -- ex: T15, T05 (sous-catégorie)
    excerpt TEXT
);

CREATE TABLE IF NOT EXISTS engine_diagnostics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_label TEXT NOT NULL,          -- ex: ODYSIGHT, ZEPHYR (nom du cas rwe-v5)
    intervention TEXT,
    source_script TEXT,                -- script test_*.py d'origine, pour traçabilité
    overall_risk TEXT,                 -- LOW/MEDIUM/HIGH/CRITICAL
    n_gaps INTEGER,
    UNIQUE(case_label, source_script)
);

CREATE TABLE IF NOT EXISTS engine_bias_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diagnostic_id INTEGER REFERENCES engine_diagnostics(id),
    flag TEXT NOT NULL                 -- ex: MEDIATION_GAP, DETECTION_BIAS
);

CREATE TABLE IF NOT EXISTS engine_gaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diagnostic_id INTEGER REFERENCES engine_diagnostics(id),
    dimension TEXT NOT NULL,           -- device/population/context/design/endpoint
    topic TEXT,                        -- sous-catégorie, ex: follow_up_insufficient
    severity TEXT                      -- LOW/MEDIUM/HIGH/CRITICAL
);
"""


def load_json(filename):
    path = DATA_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ingest_opinions_structured(conn):
    data = load_json("opinions_structured.json")
    n_dossiers = 0
    n_criticisms = 0
    for entry in data:
        cur = conn.execute(
            """INSERT OR IGNORE INTO dossiers
               (source, code_dossier, device_name, device_type, company, year, decision, sa_level)
               VALUES (?, NULL, ?, ?, ?, ?, ?, ?)""",
            (
                "opinions_structured",
                entry.get("device_name"),
                entry.get("device_type"),
                entry.get("company"),
                entry.get("year"),
                entry.get("decision"),
                entry.get("sa_level"),
            ),
        )
        dossier_id = cur.lastrowid
        if dossier_id == 0:
            # déjà présent (contrainte UNIQUE) -> retrouver l'id existant
            row = conn.execute(
                "SELECT id FROM dossiers WHERE source=? AND device_name=? AND code_dossier IS NULL",
                ("opinions_structured", entry.get("device_name")),
            ).fetchone()
            dossier_id = row[0]
        else:
            n_dossiers += 1

        for crit_type, excerpts in (entry.get("criticisms") or {}).items():
            for excerpt in excerpts:
                conn.execute(
                    "INSERT INTO criticisms (dossier_id, criticism_type, excerpt) VALUES (?, ?, ?)",
                    (dossier_id, crit_type, excerpt[:300]),
                )
                n_criticisms += 1
    return n_dossiers, n_criticisms


def ingest_mf_analysis(conn):
    data = load_json("mf_analysis_100_v2.json")
    n_dossiers = 0
    n_motifs = 0
    for entry in data:
        cur = conn.execute(
            """INSERT OR IGNORE INTO dossiers
               (source, code_dossier, device_name, device_type, company, year, decision, sa_level, is_primary)
               VALUES (?, ?, ?, NULL, NULL, NULL, ?, NULL, ?)""",
            (
                "mf_analysis",
                entry.get("code_dossier"),
                entry.get("device_name"),
                entry.get("decision"),
                entry.get("is_primary"),
            ),
        )
        dossier_id = cur.lastrowid
        if dossier_id == 0:
            row = conn.execute(
                "SELECT id FROM dossiers WHERE source=? AND code_dossier=?",
                ("mf_analysis", entry.get("code_dossier")),
            ).fetchone()
            dossier_id = row[0]
        else:
            n_dossiers += 1

        tcats = entry.get("tcats_detected") or {}
        for motif_code, tcat_dict in tcats.items():
            for tcat_code, occurrences in tcat_dict.items():
                for occ in occurrences:
                    excerpt = occ[1] if isinstance(occ, list) and len(occ) > 1 else str(occ)
                    conn.execute(
                        "INSERT INTO motifs_refus (dossier_id, motif_code, tcat_code, excerpt) VALUES (?, ?, ?, ?)",
                        (dossier_id, motif_code, tcat_code, excerpt[:300]),
                    )
                    n_motifs += 1
    return n_dossiers, n_motifs


def ingest_engine_diagnostics(conn):
    """Exécute les scripts test_*.py de rwe-v5 (déterministes, sans appel LLM)
    et ingère leur diagnostic réel (bias_flags, overall_risk, gaps)."""
    import sys

    RWE_DIR = str(_RWE_DIR)
    sys.path.insert(0, RWE_DIR)

    scripts = [
        ("FIBROREM (v1)", "test_fibrorem_analysis.py"),
        ("ODYSIGHT", "test_odysight_repair.py"),
        ("ZEPHYR", "test_zephyr_repair.py"),
        ("BRAINXPERT", "test_brainxpert_repair.py"),
        ("FIBROREM (v2)", "test_fibrorem_repair.py"),
        ("INSPIRE IV", "test_inspire_repair.py"),
        ("TRIPLE ACTION", "case_triple_action.py"),
        ("I-STOP", "case_istop.py"),
    ]

    import io
    from contextlib import redirect_stdout

    n_diag = 0
    n_flags = 0
    for label, script in scripts:
        path = f"{RWE_DIR}/{script}"
        ns = {"__file__": path}
        with redirect_stdout(io.StringIO()):
            exec(compile(open(path, encoding="utf-8").read(), script, "exec"), ns)

        # Les scripts exposent soit (out, comp) via run(), soit des variables
        # de module 'output'/'claim'/'report'.
        if "run" in ns and callable(ns["run"]):
            result = ns["run"]()
            claim = ns.get("CLAIM")
            output = result[1] if len(result) > 1 else None
            comparison = result[2] if len(result) > 2 else None
        else:
            claim = ns.get("claim") or ns.get("CLAIM")
            output = ns.get("output")
            comparison = ns.get("report") or ns.get("comparison")

        intervention = claim.intervention if claim else None
        overall_risk = str(comparison.overall_risk).split(".")[-1] if comparison else None
        n_gaps = len(comparison.gaps) if comparison else None

        cur = conn.execute(
            """INSERT OR IGNORE INTO engine_diagnostics
               (case_label, intervention, source_script, overall_risk, n_gaps)
               VALUES (?, ?, ?, ?, ?)""",
            (label, intervention, script, overall_risk, n_gaps),
        )
        diag_id = cur.lastrowid
        if diag_id == 0:
            diag_id = conn.execute(
                "SELECT id FROM engine_diagnostics WHERE case_label=? AND source_script=?",
                (label, script),
            ).fetchone()[0]
        else:
            n_diag += 1

        if output:
            for b in output.bias_flags:
                conn.execute(
                    "INSERT INTO engine_bias_flags (diagnostic_id, flag) VALUES (?, ?)",
                    (diag_id, b.flag.value),
                )
                n_flags += 1

        if comparison:
            for g in comparison.gaps:
                conn.execute(
                    "INSERT INTO engine_gaps (diagnostic_id, dimension, topic, severity) VALUES (?, ?, ?, ?)",
                    (diag_id, g.dimension, g.topic, g.severity),
                )

    return n_diag, n_flags


def ingest_manually_verified_decisions(conn):
    """Décisions HAS réelles vérifiées manuellement (recherche web + lecture
    de l'avis PDF original) pour des cas qui n'étaient pas dans les 2 sources
    structurées ci-dessus — nécessaire pour comparer certains diagnostics
    moteur (engine_diagnostics) à leur vraie décision HAS. Source de chaque
    ligne : voir le commentaire, avec date et référence de l'avis."""
    rows = [
        # (device_name, device_type, company, year, decision, sa_level, device_category)
        ("FIBROREM", "LPPR", "REMEDEE LABS", 2025, "DEFAVORABLE", "INSUFFISANT",
         "DISPOSITIF_NUMERIQUE"),  # avis CNEDiMTS 11/03/2025
        ("ZEPHYR", "LPPR", "PULMONX INTERNATIONAL", 2019, "FAVORABLE", "SUFFISANT (ASA III)",
         "IMPLANT_PASSIF"),  # avis CNEDiMTS 26/02/2019
        ("BRAINXPERT", "LPPR", "Nestlé Health Science", 2024, "DEFAVORABLE", "INSUFFISANT",
         "CONSOMMABLE"),  # avis CNEDIMTS-7370, 12/03/2024
        ("TRIPLE ACTION", "LPPR", "ALIANZA TECHNIQUES D'ORTHOPEDIE / BECKER ORTHOPEDIC", 2025,
         "DEFAVORABLE", "INSUFFISANT", "DISPOSITIF_PORTE_EXTERNE"),  # avis CNEDIMTS-7620, 28/01/2025
        ("I-STOP", "LPPR", "DiLo Medical / Apis Technologies", 2024, "DEFAVORABLE", "INSUFFISANT",
         "IMPLANT_PASSIF"),  # avis CNEDIMTS-7439, 26/03/2024 (SR, renouvellement intra-GHS)
    ]
    n = 0
    for device_name, device_type, company, year, decision, sa_level, device_category in rows:
        cur = conn.execute(
            """INSERT OR IGNORE INTO dossiers
               (source, code_dossier, device_name, device_type, company, year, decision, sa_level,
                device_category, device_category_confidence)
               VALUES ('verifie_manuellement', NULL, ?, ?, ?, ?, ?, ?, ?, 'haute_recherche_web')""",
            (device_name, device_type, company, year, decision, sa_level, device_category),
        )
        if cur.lastrowid != 0:
            n += 1
    return n


def main():
    DB_PATH.unlink(missing_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    n_d1, n_c = ingest_opinions_structured(conn)
    n_d2, n_m = ingest_mf_analysis(conn)
    n_d3, n_f = ingest_engine_diagnostics(conn)
    n_d4 = ingest_manually_verified_decisions(conn)
    conn.commit()

    print(f"opinions_structured.json -> {n_d1} dossiers, {n_c} critiques ingérées")
    print(f"mf_analysis_100_v2.json  -> {n_d2} dossiers, {n_m} motifs de refus ingérés")
    print(f"rwe-v5 test_*.py         -> {n_d3} diagnostics moteur, {n_f} bias_flags ingérés")
    print(f"Décisions vérifiées manuellement -> {n_d4} dossiers")
    print(f"Total dossiers en base   -> {conn.execute('SELECT COUNT(*) FROM dossiers').fetchone()[0]}")
    print(f"Base écrite dans : {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    main()
