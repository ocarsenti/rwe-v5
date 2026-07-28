"""
Persistance automatique — Option B du système d'apprentissage EvidenceAble.

Contrairement à retrofill.py (rétro-remplissage ponctuel depuis des scripts
test_*.py existants), ce module est fait pour être appelé à la fin de CHAQUE
nouvelle analyse de dossier, dès maintenant — pour que la base grossisse
automatiquement sans repasser par un remplissage manuel.

Deux façons de l'utiliser :

1. Intégration légère (recommandée) — appeler persist_diagnosis() toi-même
   à la fin de ton propre script d'analyse, juste après avoir obtenu
   output/comparison :

       from persist_case import persist_diagnosis
       ...
       output = analyze(claim)
       comparison = compare_claim_to_study(claim, study, epistemic_output=output)
       persist_diagnosis("MON_NOUVEAU_CAS", claim, output, comparison,
                          source_script="mon_script.py")

2. Wrapper complet — run_and_persist() rejoue toute la séquence
   (analyze + compare + repair) ET persiste en un seul appel, si ton script
   suit le même schéma que test_fibrorem_analysis.py (StudyObject déjà
   construit depuis un JSON de type FIBREPIK_JSON).

Réutilise le même schéma que retrofill.py (engine_diagnostics,
engine_bias_flags, engine_gaps) — les deux sources alimentent la même base,
sans duplication grâce à la contrainte UNIQUE(case_label, source_script).
"""

import os
import sqlite3

DB_PATH = os.environ.get(
    "EVIDENCEABLE_PATTERNS_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "patterns.db"),
)


def persist_diagnosis(case_label, claim, output, comparison, source_script="live", db_path=DB_PATH):
    """Sauvegarde le diagnostic d'un cas (bias_flags + gaps) dans patterns.db.
    Idempotent : un appel répété sur le même (case_label, source_script) ne
    duplique pas les lignes (ON CONFLICT ignore l'insertion du diagnostic,
    mais attention : les bias_flags/gaps ne sont ajoutés que si le diagnostic
    vient d'être créé, pour éviter les doublons en cas de ré-exécution)."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS engine_diagnostics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_label TEXT NOT NULL,
            intervention TEXT,
            source_script TEXT,
            overall_risk TEXT,
            n_gaps INTEGER,
            UNIQUE(case_label, source_script)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS engine_bias_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diagnostic_id INTEGER REFERENCES engine_diagnostics(id),
            flag TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS engine_gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diagnostic_id INTEGER REFERENCES engine_diagnostics(id),
            dimension TEXT NOT NULL,
            topic TEXT,
            severity TEXT
        )"""
    )

    intervention = claim.intervention if claim else None
    overall_risk = str(comparison.overall_risk).split(".")[-1] if comparison else None
    n_gaps = len(comparison.gaps) if comparison else None

    cur = conn.execute(
        """INSERT OR IGNORE INTO engine_diagnostics
           (case_label, intervention, source_script, overall_risk, n_gaps)
           VALUES (?, ?, ?, ?, ?)""",
        (case_label, intervention, source_script, overall_risk, n_gaps),
    )
    is_new = cur.lastrowid != 0
    if is_new:
        diag_id = cur.lastrowid
    else:
        diag_id = conn.execute(
            "SELECT id FROM engine_diagnostics WHERE case_label=? AND source_script=?",
            (case_label, source_script),
        ).fetchone()[0]
        # Diagnostic déjà présent : on ne réinsère pas ses flags/gaps pour
        # éviter les doublons à chaque ré-exécution du même script.
        conn.commit()
        conn.close()
        return {"diagnostic_id": diag_id, "created": False, "n_flags": 0, "n_gaps_saved": 0}

    n_flags = 0
    if output:
        for b in output.bias_flags:
            conn.execute(
                "INSERT INTO engine_bias_flags (diagnostic_id, flag) VALUES (?, ?)",
                (diag_id, b.flag.value),
            )
            n_flags += 1

    n_gaps_saved = 0
    if comparison:
        for g in comparison.gaps:
            conn.execute(
                "INSERT INTO engine_gaps (diagnostic_id, dimension, topic, severity) VALUES (?, ?, ?, ?)",
                (diag_id, g.dimension, g.topic, g.severity),
            )
            n_gaps_saved += 1

    conn.commit()
    conn.close()
    return {"diagnostic_id": diag_id, "created": True, "n_flags": n_flags, "n_gaps_saved": n_gaps_saved}


def run_and_persist(case_label, claim, study_json, source_script="live", lang="fr"):
    """Rejoue le pipeline complet (enrich -> analyze -> compare) et persiste.
    Suppose que study_json est au même format que les FIBREPIK_JSON/EFFECT_JSON
    des scripts test_*.py existants."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from llm_evidence_parser import _parse_study_object_result
    from engine import analyze
    from study_object import enrich_claim_with_study_object, compare_claim_to_study

    study = _parse_study_object_result(study_json, claim.intervention, claim.text)
    enrich_claim_with_study_object(claim, study)
    output = analyze(claim, lang=lang)
    comparison = compare_claim_to_study(claim, study, epistemic_output=output)

    result = persist_diagnosis(case_label, claim, output, comparison, source_script=source_script)
    return study, output, comparison, result


if __name__ == "__main__":
    # Démo : vérifie que persist_diagnosis fonctionne sur un cas déjà connu
    # (ODYSIGHT), sans dupliquer ce qui a été rétro-rempli par retrofill.py.
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    import io
    from contextlib import redirect_stdout
    _rwe_dir = os.path.dirname(os.path.abspath(__file__))
    ns = {"__file__": os.path.join(_rwe_dir, "test_odysight_repair.py")}
    with redirect_stdout(io.StringIO()):
        exec(compile(open(os.path.join(_rwe_dir, "test_odysight_repair.py"), encoding="utf-8").read(),
                      "test_odysight_repair.py", "exec"), ns)

    claim = ns.get("claim")
    output = ns.get("output")
    comparison = ns.get("report")

    print("=== Test 1 : persistance d'un NOUVEAU cas fictif ===")
    result = persist_diagnosis("DEMO_LIVE_CASE", claim, output, comparison, source_script="demo_persist_case.py")
    print(result)

    print("\n=== Test 2 : ré-appel identique (doit détecter created=False, pas de doublon) ===")
    result2 = persist_diagnosis("DEMO_LIVE_CASE", claim, output, comparison, source_script="demo_persist_case.py")
    print(result2)
