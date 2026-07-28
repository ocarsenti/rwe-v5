"""
Crosswalk — correspondance entre les bias_flags du moteur EvidenceAble
(models.py::BiasFlag) et les criticism_type extraits des avis HAS/CNEDiMTS
(cnedimts_analysis::opinions_structured.json).

Statut : première version, à valider/corriger par Olivier. Chaque entrée
porte un niveau de confiance :
  - 'directe'   : les deux décrivent le même mécanisme méthodologique
  - 'partielle' : chevauchement partiel, le flag moteur est plus étroit/large
                  que la catégorie HAS, ou la catégorie HAS peut avoir
                  d'autres causes que celle du flag
  - (absent)    : pas de correspondance identifiée — laissé volontairement
                  vide plutôt que de forcer un lien approximatif

Les motifs_refus (MF_A..MF_E / TCAT) de mf_analysis_100_v2.json n'ont pas de
description textuelle du contenu de chaque code dans les données ingérées
(seulement le code + un extrait de texte source) — pas assez d'information
pour les inclure dans ce mapping sans deviner ce que chaque code recouvre.
À compléter si tu as la grille de définition des motifs MF_A à MF_E.
"""

CROSSWALK = {
    "CIRCULARITY_RISK": {
        "directe": [],
        "partielle": ["critere_jugement_non_pertinent"],
        "note": "Le critère mesure le mécanisme même de l'intervention plutôt "
                "qu'un effet clinique indépendant. Pas de catégorie HAS dédiée "
                "identifiée dans les 19 observées — HAS semble absorber ce cas "
                "sous 'critere_jugement_non_pertinent' plus large.",
    },
    "DETECTION_BIAS": {
        "directe": ["biais_mesure"],
        "partielle": [],
        "note": "Correspondance directe : l'ascertainment de l'outcome est "
                "influencé par le dispositif — c'est le cœur de biais_mesure.",
    },
    "PERCEPTION_BIAS": {
        "directe": [],
        "partielle": ["biais_mesure"],
        "note": "Sous-cas de biais_mesure spécifique aux critères "
                "auto-rapportés (effet d'attente/placebo) — HAS ne semble pas "
                "distinguer ce sous-type dans les 19 catégories observées.",
    },
    "MEDIATION_GAP": {
        "directe": [],
        "partielle": ["design_etude_inadequat", "critere_jugement_non_pertinent"],
        "note": "Revendication à un niveau (mécanisme/processus) que "
                "l'endpoint mesuré ne couvre pas directement. Chevauche deux "
                "catégories HAS sans correspondre exactement à l'une ou "
                "l'autre — à valider avec toi si l'une est plus juste.",
    },
    "PROCESS_TAUTOLOGY": {
        "directe": [],
        "partielle": ["critere_jugement_non_pertinent"],
        "note": "Aucun cas observé dans nos 6 diagnostics moteur — mapping "
                "hypothétique, à confirmer sur un vrai cas.",
    },
    "SURROGATE_RISK": {
        "directe": [],
        "partielle": ["performances_algorithme_insuffisantes", "critere_jugement_non_pertinent"],
        "note": "Endpoint de substitution non validé. 'performances_algorithme_"
                "insuffisantes' n'est pertinent que pour les dispositifs "
                "numériques/algorithmiques — mapping partiel et contextuel, "
                "pas général.",
    },
    "ADJUDICATION_RISK": {
        "directe": [],
        "partielle": ["biais_mesure"],
        "note": "Absence de comité d'adjudication indépendant — HAS ne "
                "semble pas avoir de catégorie dédiée dans les 19 observées ; "
                "rattaché à biais_mesure par défaut mais c'est un mécanisme "
                "plus spécifique (absence de procédure, pas juste un biais "
                "de mesure en soi).",
    },
    "NO_COMPARATOR": {
        "directe": ["absence_bras_controle"],
        "partielle": ["absence_donnees_comparatives"],
        "note": "Correspondance directe claire.",
    },
    "PROTOCOL_FIXED_ENDPOINT": {
        "directe": [],
        "partielle": [],
        "note": "Aucune catégorie HAS observée ne semble correspondre — "
                "cette question (endpoint fixé au protocole vs modifié "
                "post-hoc) n'apparaît pas comme un poste de critique isolé "
                "dans les 19 catégories du corpus actuel.",
    },
}

# Le moteur EvidenceAble analyse le DESIGN méthodologique — pas les données ni
# les résultats. Deux sorties structurées existent côté design :
#   - bias_flags (epistemic_core, 9 valeurs, structure causale claim/endpoint)
#   - gaps (study_object.ComparisonReport, dimensions: device/population/
#     context/design/endpoint — alignement claim vs étude)
# Les 13 catégories HAS non mappées se répartissent en deux groupes très
# différents : certaines portent sur les DONNÉES/RÉSULTATS (hors du scope du
# moteur par construction, donc absence de mapping normale, pas un manque) ;
# d'autres portent sur le DESIGN et sont potentiellement dans le scope, via
# les gaps plutôt que via bias_flags — reclassées ci-dessous en conséquence.

HORS_SCOPE_DONNEES_RESULTATS = [
    "absence_demonstration_utilite_clinique",  # résultat clinique démontré ou non
    "benefice_clinique_non_demontre",          # résultat
    "confusion_residuelle",                     # analyse statistique du résultat
    "donnees_non_specifiques_comme_seule_preuve",  # nature/spécificité de la preuve
    "impact_organisationnel_non_demontre",      # résultat organisationnel
    "qualite_donnees_insuffisante",             # qualité des données elles-mêmes
]

DESIGN_POTENTIELLEMENT_DANS_SCOPE = {
    # catégorie HAS -> dimension de gap (study_object.py) probablement liée,
    # à vérifier cas par cas plutôt qu'à mapper aveuglément sur bias_flags
    "duree_suivi_insuffisante": "design",       # déjà observé en pratique dans
                                                  # les gaps ZEPHYR/FIBROREM ("suivi insuffisant")
    "population_non_representative": "population",  # déjà observé (gap ODYSIGHT)
    "controle_historique_inadequat": "device_ou_design",  # proche de NO_COMPARATOR
    "absence_critere_centre_patient": "endpoint",
}

# Cas ambigus : dépendent à la fois du design ET des données recrutées —
# pas tranchés ici, à discuter avec Olivier plutôt que classés à l'aveugle.
AMBIGU = [
    "effectif_insuffisant",        # taille d'échantillon réalisée (donnée) vs
                                     # calcul de puissance prévu au protocole (design)
    "validite_externe_limitee",    # généralisabilité — mélange population/contexte (design)
                                     # et représentativité des données recrutées
]

# Vraiment hors scope, sans lien design ni données identifié (critère
# réglementaire d'innovation, orthogonal à la méthodologie elle-même)
HORS_SCOPE_AUTRE = [
    "presomption_innovation_non_etablie",
]

UNMAPPED_HAS_CATEGORIES = (
    HORS_SCOPE_DONNEES_RESULTATS
    + list(DESIGN_POTENTIELLEMENT_DANS_SCOPE)
    + AMBIGU
    + HORS_SCOPE_AUTRE
)


def to_has_categories(engine_flag: str, include_partial: bool = True) -> list[str]:
    """Traduit un bias_flag moteur vers les catégories HAS correspondantes."""
    entry = CROSSWALK.get(engine_flag, {})
    result = list(entry.get("directe", []))
    if include_partial:
        result += list(entry.get("partielle", []))
    return result


# ---------------------------------------------------------------------------
# Deuxième crosswalk : les 'gaps' (study_object.ComparisonReport.gaps), qui
# couvrent le design au-delà des bias_flags — dimension + topic (sous-type),
# vérifié directement contre le code de study_object.py (pas deviné).
# ---------------------------------------------------------------------------

GAPS_CROSSWALK = {
    # catégorie HAS -> (dimension, topic) du gap correspondant, si identifié
    "duree_suivi_insuffisante": {
        "dimension": "design",
        "topic": "follow_up_insufficient",
        "confiance": "directe",
        "note": "Vérifié : le gap follow_up_insufficient se déclenche exactement "
                "sur un suivi jugé trop court pour une revendication d'outcome — "
                "correspondance directe avec duree_suivi_insuffisante.",
    },
    "controle_historique_inadequat": {
        "dimension": "design",
        "topic": "external_control_cohort",
        "confiance": "directe",
        "note": "Vérifié : le gap external_control_cohort porte spécifiquement sur "
                "un comparateur historique/registre non concurrent et non "
                "randomisé — c'est exactement le mécanisme visé par la catégorie "
                "HAS.",
    },
    "population_non_representative": {
        "dimension": "population",
        "topic": None,  # pas de sous-catégorie : un seul type de gap population
        "confiance": "directe",
        "note": "Vérifié : _population_gap() ne produit qu'un seul type de gap "
                "(écart population étudiée vs revendiquée), sans sous-topic — "
                "correspondance directe au niveau dimension.",
    },
    "absence_critere_centre_patient": {
        "dimension": None,
        "topic": None,
        "confiance": "aucune",
        "note": "Recherché explicitement dans study_object.py — rien ne "
                "correspond. Le gap le plus proche trouvé (subjective_no_blinding, "
                "topic sur l'aveugle des critères PRO) concerne un problème "
                "différent : un critère patient-rapporté PRÉSENT mais mal aveuglé, "
                "pas l'ABSENCE totale d'un critère centré patient dans le dossier. "
                "Ne pas forcer ce lien — c'est un vrai angle mort du moteur, pas "
                "une erreur de mapping de ma part cette fois.",
    },
}


def to_has_categories_via_gaps(dimension: str, topic: str | None = None) -> list[str]:
    """Traduit un (dimension, topic) de gap moteur vers les catégories HAS
    correspondantes — sens inverse de GAPS_CROSSWALK, pour usage futur si les
    gaps sont un jour ingérés par cas dans patterns.db (ce qui n'est pas
    encore fait : seuls les bias_flags le sont actuellement)."""
    result = []
    for has_cat, entry in GAPS_CROSSWALK.items():
        if entry["dimension"] == dimension and entry["topic"] == topic:
            result.append(has_cat)
    return result


if __name__ == "__main__":
    print("=== Couverture du crosswalk ===\n")
    for flag, entry in CROSSWALK.items():
        n = len(entry["directe"]) + len(entry["partielle"])
        status = "directe" if entry["directe"] else ("partielle" if entry["partielle"] else "AUCUNE")
        print(f"{flag:26s} -> {status:9s} ({n} catégorie(s) HAS liée(s))")

    print(f"\n{len(UNMAPPED_HAS_CATEGORIES)}/19 catégories HAS sans flag moteur (bias_flags) correspondant, réparties ainsi :\n")
    print(f"  Hors scope (données/résultats, {len(HORS_SCOPE_DONNEES_RESULTATS)}) — normal que le moteur design-only ne les couvre pas :")
    for cat in HORS_SCOPE_DONNEES_RESULTATS:
        print("    -", cat)
    print(f"\n  Design, potentiellement dans le scope via 'gaps' plutôt que bias_flags ({len(DESIGN_POTENTIELLEMENT_DANS_SCOPE)}) :")
    for cat, dim in DESIGN_POTENTIELLEMENT_DANS_SCOPE.items():
        print(f"    - {cat} -> gap dimension probable: {dim}")
    print(f"\n  Ambigu, à trancher ({len(AMBIGU)}) :")
    for cat in AMBIGU:
        print("    -", cat)
    print(f"\n  Hors scope, autre ({len(HORS_SCOPE_AUTRE)}) :")
    for cat in HORS_SCOPE_AUTRE:
        print("    -", cat)

    print("\n=== Crosswalk gaps (dimension/topic) — vérifié contre le code ===\n")
    for cat, entry in GAPS_CROSSWALK.items():
        loc = f"{entry['dimension']}/{entry['topic']}" if entry["dimension"] else "—"
        print(f"  {cat:32s} -> {loc:30s} ({entry['confiance']})")

    print(
        "\nImportant : ce mapping n'est pas encore branché sur les données "
        "ingérées — patterns.db ne stocke pour l'instant que les bias_flags "
        "par cas moteur (engine_bias_flags), pas les gaps (dimension/topic). "
        "Pour l'exploiter dans precedent_search.py, il faudrait d'abord "
        "ingérer aussi comparison.gaps par cas, comme on l'a fait pour "
        "output.bias_flags."
    )
