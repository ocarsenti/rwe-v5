"""
Recherche de précédents — étape 2 du système d'apprentissage EvidenceAble.

Étant donné le profil d'un dossier en cours d'analyse (device_category et/ou
bias_flags détectés), retrouve les précédents les plus proches dans patterns.db
et explique pourquoi chacun a été retenu (attributs partagés).

Deux sources distinctes, non fusionnées :
  - Précédents HAS publics (dossiers + criticisms + motifs_refus)
  - Précédents moteur (engine_diagnostics + engine_bias_flags)

Ces deux sources utilisent des taxonomies de biais différentes (les
criticism_type/motif_code HAS en français vs les bias_flags du moteur en
anglais type MEDIATION_GAP). Pas de mapping entre les deux pour l'instant —
donc pas de score unifié artificiel. Prochain vrai chantier si on veut
fusionner : construire cette table de correspondance.

Usage : voir find_precedents() ci-dessous, ou lancer ce fichier pour une démo.
"""

import sqlite3

from crosswalk import to_has_categories, to_has_categories_via_gaps

import os
DB_PATH = os.environ.get(
    "EVIDENCEABLE_PATTERNS_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "patterns.db"),
)


def find_unified_precedents(device_category=None, bias_flags=None, gap_topics=None, limit=5):
    """Traduit les bias_flags ET les gaps moteur en catégories HAS via
    crosswalk.py, puis cherche des précédents HAS avec ce vocabulaire traduit."""
    translated = set()
    for flag in bias_flags or []:
        translated |= set(to_has_categories(flag))
    for dimension, topic in gap_topics or []:
        translated |= set(to_has_categories_via_gaps(dimension, topic))
    if not translated:
        return [], []
    precedents = find_has_precedents(
        device_category=device_category, criticism_types=translated, limit=limit
    )
    return precedents, sorted(translated)


def find_has_precedents(device_category=None, criticism_types=None, limit=5):
    """Précédents côté avis HAS publics (dossiers + criticisms + motifs_refus).
    Score = nombre d'attributs partagés avec le profil recherché."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT d.id, d.device_name, d.device_category, d.decision,
               GROUP_CONCAT(DISTINCT c.criticism_type) AS criticisms,
               GROUP_CONCAT(DISTINCT m.motif_code) AS motifs
        FROM dossiers d
        LEFT JOIN criticisms c ON c.dossier_id = d.id
        LEFT JOIN motifs_refus m ON m.dossier_id = d.id
        WHERE d.device_category != 'A_CLASSIFIER'
        GROUP BY d.id
        """
    ).fetchall()
    conn.close()

    scored = []
    for row in rows:
        score = 0
        reasons = []
        if device_category and row["device_category"] == device_category:
            score += 1
            reasons.append(f"même catégorie ({device_category})")
        row_criticisms = set((row["criticisms"] or "").split(",")) - {""}
        if criticism_types:
            shared = row_criticisms & set(criticism_types)
            if shared:
                score += len(shared)
                reasons.append(f"critiques partagées: {', '.join(sorted(shared))}")
        if score > 0:
            scored.append((score, row, reasons))

    scored.sort(key=lambda x: -x[0])
    return scored[:limit]


def find_engine_precedents(bias_flags=None, gap_topics=None, limit=5):
    """Précédents côté diagnostics moteur, sur bias_flags ET/OU gaps (dimension,topic).
    gap_topics attend une liste de tuples (dimension, topic)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT ed.id, ed.case_label, ed.intervention, ed.overall_risk,
               GROUP_CONCAT(DISTINCT ebf.flag) AS flags
        FROM engine_diagnostics ed
        LEFT JOIN engine_bias_flags ebf ON ebf.diagnostic_id = ed.id
        GROUP BY ed.id
        """
    ).fetchall()

    gaps_by_diag = {}
    for r in conn.execute("SELECT diagnostic_id, dimension, topic FROM engine_gaps"):
        gaps_by_diag.setdefault(r[0], set()).add((r[1], r[2]))
    conn.close()

    scored = []
    for row in rows:
        row_flags = set((row["flags"] or "").split(",")) - {""}
        shared_flags = row_flags & set(bias_flags or [])
        shared_gaps = gaps_by_diag.get(row["id"], set()) & set(gap_topics or [])
        score = len(shared_flags) + len(shared_gaps)
        if score > 0:
            reasons = []
            if shared_flags:
                reasons.append(f"bias_flags partagés: {', '.join(sorted(shared_flags))}")
            if shared_gaps:
                gap_labels = [f"{dim}/{top}" if top else dim for dim, top in shared_gaps]
                reasons.append(f"gaps partagés: {', '.join(sorted(gap_labels))}")
            scored.append((score, row, reasons))

    scored.sort(key=lambda x: -x[0])
    return scored[:limit]


def format_for_llm_context(has_precedents, engine_precedents):
    """Formate les précédents trouvés comme contexte injectable dans un prompt LLM
    (étape 3 du plan — pas encore branché sur cas_engine.py, c'est le format cible)."""
    lines = []
    if has_precedents:
        lines.append("Précédents HAS (avis publics) structurellement proches :")
        for score, row, reasons in has_precedents:
            lines.append(
                f"  - {row['device_name']} ({row['device_category']}) "
                f"→ décision HAS: {row['decision']} — {'; '.join(reasons)}"
            )
    if engine_precedents:
        lines.append("Précédents issus de tes propres analyses moteur :")
        for score, row, reasons in engine_precedents:
            lines.append(
                f"  - {row['case_label']} → risque moteur: {row['overall_risk']} — {'; '.join(reasons)}"
            )
    return "\n".join(lines) if lines else "Aucun précédent structurellement proche trouvé."


if __name__ == "__main__":
    # Démo : profil d'un dossier fictif en cours d'analyse — dispositif
    # numérique avec un gap de médiation et un risque d'adjudication détectés.
    print("=== Démo : nouveau dossier fictif, DISPOSITIF_NUMERIQUE, MEDIATION_GAP + ADJUDICATION_RISK ===\n")

    has_prec = find_has_precedents(
        device_category="DISPOSITIF_NUMERIQUE",
        criticism_types=["absence_bras_controle", "biais_mesure", "design_etude_inadequat"],
    )
    engine_prec = find_engine_precedents(
        bias_flags=["MEDIATION_GAP", "ADJUDICATION_RISK"],
    )

    print(format_for_llm_context(has_prec, engine_prec))

    print("\n=== Démo : recherche unifiée via crosswalk (bias_flags -> catégories HAS) ===\n")
    unified_prec, translated = find_unified_precedents(
        device_category="DISPOSITIF_NUMERIQUE",
        bias_flags=["MEDIATION_GAP", "ADJUDICATION_RISK"],
    )
    print(f"Flags moteur traduits vers catégories HAS : {translated}\n")
    for score, row, reasons in unified_prec:
        print(f"  - {row['device_name']} → décision HAS: {row['decision']} — {'; '.join(reasons)}")

    print("\n=== Démo : profil incluant un gap 'follow_up_insufficient' ===\n")
    engine_prec2 = find_engine_precedents(
        bias_flags=["MEDIATION_GAP"],
        gap_topics=[("design", "follow_up_insufficient")],
    )
    for score, row, reasons in engine_prec2:
        print(f"  - {row['case_label']} → risque moteur: {row['overall_risk']} — {'; '.join(reasons)}")

    unified_prec2, translated2 = find_unified_precedents(
        bias_flags=["MEDIATION_GAP"],
        gap_topics=[("design", "follow_up_insufficient")],
    )
    print(f"\nCatégories HAS traduites (bias_flags + gaps) : {translated2}\n")
    for score, row, reasons in unified_prec2:
        print(f"  - {row['device_name']} → décision HAS: {row['decision']} — {'; '.join(reasons)}")
