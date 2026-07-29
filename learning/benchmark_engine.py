"""
Benchmark engine — étape 3 du système d'apprentissage EvidenceAble.

Calcule, à partir de patterns.db (dossiers + criticisms, alimentés par
retrofill.py), l'écart de fréquence de chaque critique HAS entre dossiers
refusés et dossiers acceptés — par device_category si demandé.

Objectif : remplacer "X% des dossiers ont un comparateur externe" (une
description de pratique courante, pas un facteur de risque) par "les
dossiers refusés avaient Y points de plus de tel gap que les dossiers
acceptés (n=...)" — la vraie question du mode conseil design.

Deux fonctions d'entrée :
  - criticism_deltas()        : delta brut, dans le vocabulaire HAS (criticism_type)
  - benchmark_for_moteur_signal() : même chose, mais interrogé dans le
    vocabulaire moteur (bias_flag ou dimension/topic de gap), traduit vers
    HAS via crosswalk.py avant la requête
  - format_for_design_advice() : formatage texte prêt à injecter dans le
    prompt du mode conseil design

Garde-fous statistiques, volontaires :
  - un delta n'est calculé que si les DEUX bras (refusés et acceptés) ont au
    moins min_n dossiers dans le périmètre demandé — sinon on retourne un
    warning explicite plutôt qu'un pourcentage trompeur sur 3 cas
  - jamais de causalité affirmée dans le texte généré : "les dossiers
    refusés avaient plus souvent X", jamais "X cause le refus"

Usage :
    python3 benchmark_engine.py                    # tous domaines confondus
    python3 benchmark_engine.py orthopedie          # filtré par device_category
"""

import os
import sqlite3
from pathlib import Path

from crosswalk import to_has_categories, to_has_categories_via_gaps

DB_PATH = Path(os.environ.get(
    "EVIDENCEABLE_PATTERNS_DB",
    str(Path(os.path.dirname(os.path.abspath(__file__))) / "patterns.db"),
))

MIN_N = 5  # dossiers minimum par bras (refusé / accepté) pour publier un pourcentage


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def criticism_deltas(device_category=None, min_n=MIN_N):
    """Delta de fréquence par criticism_type, dans le vocabulaire HAS.

    Retourne un dict :
      results   : liste triée par delta_pts décroissant, chacune avec
                  criticism_type, pct_refused, pct_accepted, delta_pts,
                  n_refused_with, n_accepted_with
      n_refused_total / n_accepted_total : dénominateurs utilisés
      warning   : None, ou message si l'échantillon est trop petit pour
                  publier quoi que ce soit dans ce périmètre
    """
    conn = _connect()
    try:
        where = "d.decision IN ('FAVORABLE','DEFAVORABLE')"
        params = []
        if device_category:
            where += " AND d.device_category = ?"
            params.append(device_category)

        totals = dict(conn.execute(
            f"SELECT decision, COUNT(*) as n FROM dossiers d WHERE {where} GROUP BY decision",
            params,
        ).fetchall())
        n_refused_total = totals.get("DEFAVORABLE", 0)
        n_accepted_total = totals.get("FAVORABLE", 0)

        if n_refused_total < min_n or n_accepted_total < min_n:
            scope = f"device_category='{device_category}'" if device_category else "tous domaines"
            return {
                "results": [],
                "n_refused_total": n_refused_total,
                "n_accepted_total": n_accepted_total,
                "warning": (
                    f"Échantillon insuffisant ({scope}) : {n_refused_total} refusé(s), "
                    f"{n_accepted_total} accepté(s), minimum requis {min_n} par bras — "
                    "aucune stat publiée."
                ),
            }

        rows = conn.execute(
            f"""
            SELECT c.criticism_type,
                   SUM(CASE WHEN d.decision = 'DEFAVORABLE' THEN 1 ELSE 0 END) AS n_refused_with,
                   SUM(CASE WHEN d.decision = 'FAVORABLE' THEN 1 ELSE 0 END) AS n_accepted_with
            FROM criticisms c
            JOIN dossiers d ON d.id = c.dossier_id
            WHERE {where}
            GROUP BY c.criticism_type
            """,
            params,
        ).fetchall()

        results = []
        for row in rows:
            pct_refused = 100.0 * row["n_refused_with"] / n_refused_total
            pct_accepted = 100.0 * row["n_accepted_with"] / n_accepted_total
            results.append({
                "criticism_type": row["criticism_type"],
                "pct_refused": round(pct_refused, 1),
                "pct_accepted": round(pct_accepted, 1),
                "delta_pts": round(pct_refused - pct_accepted, 1),
                "n_refused_with": row["n_refused_with"],
                "n_accepted_with": row["n_accepted_with"],
            })
        results.sort(key=lambda r: r["delta_pts"], reverse=True)

        return {
            "results": results,
            "n_refused_total": n_refused_total,
            "n_accepted_total": n_accepted_total,
            "warning": None,
        }
    finally:
        conn.close()


def benchmark_for_moteur_signal(bias_flag=None, gap_dimension=None, gap_topic=None,
                                 device_category=None, min_n=MIN_N):
    """Même chose que criticism_deltas(), mais interrogée dans le vocabulaire
    moteur (bias_flag OU dimension/topic de gap) — traduit vers les
    catégories HAS via crosswalk.py avant de matcher.

    Retourne None si le crosswalk n'a aucune correspondance pour ce signal
    (angle mort du crosswalk lui-même) — à ne pas confondre avec un
    échantillon insuffisant (results vide + warning non-None), qui est un
    problème de données, pas de mapping.
    """
    if bias_flag:
        has_categories = to_has_categories(bias_flag)
    elif gap_dimension:
        has_categories = to_has_categories_via_gaps(gap_dimension, gap_topic)
    else:
        raise ValueError("Fournir bias_flag= ou gap_dimension= (+ gap_topic optionnel).")

    if not has_categories:
        return None

    bench = criticism_deltas(device_category=device_category, min_n=min_n)
    matched = [r for r in bench["results"] if r["criticism_type"] in has_categories]

    return {
        "moteur_signal": bias_flag or f"{gap_dimension}/{gap_topic}",
        "matched_has_categories": has_categories,
        "matches": matched,
        "n_refused_total": bench["n_refused_total"],
        "n_accepted_total": bench["n_accepted_total"],
        "warning": bench["warning"],
    }


def format_for_design_advice(device_category=None, min_n=MIN_N, top_n=8):
    """Formate les deltas les plus marqués en texte prêt à injecter dans le
    prompt du mode conseil design. Phrasing volontairement prudent : jamais
    de causalité affirmée, toujours le N à côté du pourcentage."""
    bench = criticism_deltas(device_category=device_category, min_n=min_n)
    if bench["warning"]:
        return bench["warning"]

    scope = f"dans la catégorie « {device_category} »" if device_category else "tous domaines confondus"
    lines = [
        f"Sur {bench['n_refused_total']} dossiers refusés et {bench['n_accepted_total']} "
        f"dossiers acceptés ({scope}) :"
    ]
    shown = 0
    for r in bench["results"]:
        if r["delta_pts"] <= 0:
            continue
        lines.append(
            f"- {r['criticism_type']} : présent dans {r['pct_refused']}% des refusés "
            f"(n={r['n_refused_with']}) vs {r['pct_accepted']}% des acceptés "
            f"(n={r['n_accepted_with']}) — écart de {r['delta_pts']:+.1f} pts"
        )
        shown += 1
        if shown >= top_n:
            break
    if shown == 0:
        lines.append("Aucune critique n'apparaît significativement plus fréquente côté refusés dans ce périmètre.")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    _device_category = sys.argv[1] if len(sys.argv) > 1 else None
    print(format_for_design_advice(device_category=_device_category))
