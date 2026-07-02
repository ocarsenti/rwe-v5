"""
Test live du llm_evidence_parser sur 2 vrais abstracts CNEDiMTS.
Lance parse_study_with_llm + enrich_claim_with_study + analyze() et affiche le résultat complet.
"""

import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from models import (
    ClinicalClaim, Endpoint, EndpointNature, CausalRole,
)
from engine import analyze
from llm_evidence_parser import parse_study_with_llm, enrich_claim_with_study

# ---------------------------------------------------------------------------
# Cas 1 — INSPIRE IV / Étude EFFECT
# ---------------------------------------------------------------------------

EFFECT_TEXT = """
Étude EFFECT (Heiser et al., J Clin Med 2021)

Il s'agit d'une étude contrôlée randomisée multicentrique en crossover dont l'objectif était
d'évaluer l'efficacité des dispositifs de stimulation du nerf hypoglosse INSPIRE II et INSPIRE IV
dans le traitement du syndrome d'apnées-hypopnées obstructives du sommeil (SAHOS) modéré à sévère.

Méthodologie :
- Critères d'inclusion : SAHOS modéré ou sévère (IAH ≥ 15 évènements/heure), patients intolérants
  ou non répondants à la ventilation par pression positive continue (PPC), implantés depuis 6 mois
  minimum avec INSPIRE II ou INSPIRE IV
- Effectif : 89 patients
- Design : randomisé crossover — les patients étaient tirés au sort pour commencer avec la
  stimulation active (ON) ou l'absence de stimulation (OFF), puis crossover après une semaine
- Durée de suivi totale : 2 semaines
- Pays : Allemagne, Autriche, Belgique, Suisse

Critères de jugement :
- Co-critères principaux : IAH (Indice d'Apnées-Hypopnées) évalué par polysomnographie et
  taux de répondeurs (IAH ≤ 15 évènements/heure)
- Critères secondaires : IDO (Index de Désaturation en Oxygène), score ESS (Epworth Sleepiness Scale),
  qualité de vie

Résultats :
- IAH médian : 28,5 évènements/h dans le groupe ON vs 46,4 dans le groupe OFF (p<0,001)
- Taux de répondeurs : 63% dans le groupe stimulation ON vs 6% dans le groupe OFF (p<0,001)

Aucun Comité d'Événements Cliniques (CEC) indépendant n'est mentionné.
"""

INSPIRE_CLAIM = ClinicalClaim(
    text="INSPIRE IV stimule le nerf hypoglosse et réduit l'IAH chez les patients SAHOS modéré à sévère en échec de PPC et d'OAM",
    intervention="INSPIRE IV",
    domain="respiratory",
    endpoints=[
        Endpoint("IAH — Indice Apnée-Hypopnée", EndpointNature.OBJECTIVE, CausalRole.MEDIATED,
                 is_primary=True, description="mesure polysomnographique"),
        Endpoint("taux de répondeurs IAH ≤ 15", EndpointNature.OBJECTIVE, CausalRole.MEDIATED,
                 is_primary=True),
        Endpoint("somnolence diurne ESS", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT,
                 is_primary=False),
    ]
)

# ---------------------------------------------------------------------------
# Cas 2 — ZEPHYR / Étude LIBERATE
# ---------------------------------------------------------------------------

LIBERATE_TEXT = """
Étude LIBERATE (Criner et al., Lancet Respir Med 2018 — analyse post-hoc Dransfield 2020)

Étude contrôlée randomisée multicentrique en ouvert (LIBERATE) comparant les valves
endobronchiques ZEPHYR au traitement médical optimal seul chez des patients atteints
d'emphysème pulmonaire sévère.

Méthodologie :
- Critères d'inclusion : BPCO stade III-IV (emphysème hétérogène ou homogène), ventilation
  collatérale nulle à minimale (mesurée par Chartis), VEMS entre 15% et 45% de la valeur prédite,
  VR > 175%, score mMRC ≥ 2
- Effectif : 190 patients (128 groupe ZEPHYR, 62 groupe traitement médical)
- Randomisation : 2:1 (ZEPHYR vs traitement médical optimal)
- Durée de suivi : 12 mois
- Pays : USA, Europe (Allemagne, France, Royaume-Uni, Belgique, Pays-Bas)
- Étude ouverte : pas d'aveugle, pas de CEC indépendant

Critères de jugement :
- Critère principal : VEMS (Volume Expiratoire Maximal Seconde) — variation absolue à 12 mois
- Critères secondaires : test de marche 6 minutes (6MWT), score de dyspnée mMRC,
  qualité de vie SGRQ, taux de pneumothorax (complication)

Résultats à 12 mois :
- VEMS : +110 ml dans le groupe ZEPHYR vs +0 ml dans le groupe traitement médical (p<0,001)
- 6MWT : +39,3 m vs +0,6 m (p<0,001)
- Pneumothorax : 26,6% dans le groupe ZEPHYR (complication fréquente)
"""

ZEPHYR_CLAIM = ClinicalClaim(
    text="ZEPHYR réduit la distension pulmonaire et améliore la fonction respiratoire chez les patients BPCO emphysème sévère",
    intervention="ZEPHYR valves endobronchiques",
    domain="respiratory",
    endpoints=[
        Endpoint("VEMS — Volume Expiratoire Maximal Seconde", EndpointNature.OBJECTIVE,
                 CausalRole.MEDIATED, is_primary=True, description="spirometry functional measure"),
        Endpoint("dyspnée mMRC", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT, is_primary=False),
        Endpoint("test de marche 6 minutes", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                 is_primary=False),
    ]
)


# ---------------------------------------------------------------------------
# Cas 3 — FIBROREM / Étude FIBREPIK
# ---------------------------------------------------------------------------

FIBREPIK_TEXT = """
Étude FIBREPIK (Trials 2022, rapport d'étude fourni)

Étude de supériorité, prospective, multicentrique, contrôlée, randomisée, en ouvert,
comparant le bracelet FIBROREM (précédente génération) associé à la prise en charge
conventionnelle, par rapport à la prise en charge conventionnelle seule, chez des patients
atteints de fibromyalgie modérée à sévère.

Méthodologie :
- Critères d'inclusion : diagnostic confirmé de fibromyalgie, score FIQ ≥ 39 (modéré à sévère)
- Effectif total randomisé : 170 patients
- Groupes : bracelet + prise en charge conventionnelle vs prise en charge conventionnelle seule (groupe différé)
- Suivi principal : 3 mois
- Pays : France (étude monocentrique ou multicentrique française)
- Design : randomisé en ouvert (pas d'aveugle, pas de sham, pas de placebo). Pas de CEC.

Critères de jugement :
- Critère principal : réduction du score FIQ (Fibromyalgia Impact Questionnaire) à 3 mois
  Le score FIQ est un questionnaire auto-rapporté par le patient, évaluant l'impact fonctionnel
  et la qualité de vie dans la fibromyalgie.
- Critères secondaires : score PGIC (Patient Global Impression of Change), qualité de vie

Résultats :
- Réduction du score FIQ statistiquement significative dans le groupe bracelet vs groupe contrôle à 3 mois
- Pas de données de mortalité, hospitalisation, ou outcomes durs rapportées

Note : l'étude FIBREPIK a été réalisée avec une génération antérieure de FIBROREM (bracelet différent),
pas avec le dispositif FIBROREM actuellement évalué.
"""

FIBROREM_CLAIM = ClinicalClaim(
    text="FIBROREM améliore la qualité de vie et réduit l'impact fonctionnel de la fibromyalgie modérée à sévère",
    intervention="FIBROREM bracelet de neurostimulation",
    domain="pain",
    endpoints=[
        Endpoint("score FIQ — Fibromyalgia Impact Questionnaire", EndpointNature.SUBJECTIVE,
                 CausalRole.MEDIATED, is_primary=True,
                 description="patient self-reported fibromyalgia impact score"),
        Endpoint("score PGIC — Patient Global Impression of Change", EndpointNature.SUBJECTIVE,
                 CausalRole.INDEPENDENT, is_primary=False),
    ]
)

# ---------------------------------------------------------------------------
# Cas 4 — BRAINXPERT / Étude BENEFIC
# ---------------------------------------------------------------------------

BENEFIC_TEXT = """
Étude BENEFIC (Brain ENErgy Fitness, Imaging and Cognition)
Publications : Alzheimers Dement. 2019;15(5):625-634

Étude monocentrique, randomisée en double aveugle, contrôlée versus placebo,
réalisée au Canada (Université de Sherbrooke).

Le produit évalué dans l'étude est CAPTEX 355 (émulsion de triglycérides à chaîne moyenne cTCM),
qui est DIFFÉRENT de BRAINXPERT (le produit actuellement évalué par la HAS).
BRAINXPERT contient des cTCM fortement cétogènes (60% C8, 40% C10), formulés différemment.

Méthodologie :
- Population : hommes et femmes ≥ 55 ans avec trouble neurocognitif léger
  (score MoCA entre 18 et 26 ou MMSE entre 24 et 27)
- Effectif analysé : 39 patients (52 inclus, 13 arrêts prématurés)
  Groupe cTCM : n=19 ; Groupe placebo : n=20
- Durée : 6 mois
- Pays : Canada (étude monocentrique)
- Randomisé double aveugle vs placebo

Critères de jugement principaux (Phase 1) :
- Taux de métabolisation cérébrale de l'acétoacétate (mesure TEP-scan)
- Taux de métabolisation cérébrale du glucose (mesure TEP-scan)
Ces critères sont des biomarqueurs métaboliques cérébraux, pas des critères cliniques.

Critères secondaires :
- Score MMSE (Mini-Mental State Examination)
- Score MoCA (Montreal Cognitive Assessment)
- Tests neuropsychologiques

Aucun Comité d'Événements Cliniques (CEC) indépendant. Pas de données sur la progression
vers la maladie d'Alzheimer, la mortalité, ou l'autonomie fonctionnelle.
"""

BRAINXPERT_CLAIM = ClinicalClaim(
    text="BRAINXPERT améliore les fonctions cognitives des patients adultes avec trouble neurocognitif léger",
    intervention="BRAINXPERT boisson à base de triglycérides à chaîne moyenne cTCM",
    domain="neurology",
    endpoints=[
        Endpoint("score MMSE", EndpointNature.SUBJECTIVE, CausalRole.MEDIATED,
                 is_primary=True, description="Mini Mental State Examination — cognitive score"),
        Endpoint("score MoCA", EndpointNature.SUBJECTIVE, CausalRole.MEDIATED,
                 is_primary=False),
        Endpoint("métabolisation cérébrale acétoacétate", EndpointNature.OBJECTIVE,
                 CausalRole.MEDIATED, is_primary=False,
                 description="TEP-scan biomarker — cerebral metabolic rate"),
    ]
)

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_case(label, study_text, claim):
    print(f"\n{'=' * 70}")
    print(f"  {label}")
    print(f"{'=' * 70}")

    print("\n[1] Parsing étude avec LLM...")
    result = parse_study_with_llm(
        study_text=study_text,
        claim_device=claim.intervention,
        claim_indication=claim.text,
    )

    print(f"  study_design     : {result.study_design}")
    print(f"  n_patients       : {result.n_patients}")
    print(f"  has_comparator   : {result.has_comparator}")
    print(f"  follow_up_months : {result.follow_up_months}")
    print(f"  study_countries  : {result.study_countries}")

    if result.endpoint_evidence:
        print("  endpoints :")
        for ep in result.endpoint_evidence:
            print(f"    · {ep.name}")
            print(f"        validated_surrogate     = {ep.is_validated_surrogate}")
            print(f"        independently_adjudicated = {ep.is_independently_adjudicated}")

    if result.device_alignment:
        d = result.device_alignment
        print(f"  device_alignment : {d.device_match_type.value} — {d.device_description_study}")
        print(f"    justification  : {d.justification}")

    if result.population_alignment:
        p = result.population_alignment
        print(f"  pop_alignment    : {p.population_match_type.value} — {p.population_description_study}")
        print(f"    eligibility    : {p.eligibility_shift.value}")

    if result.context_alignment:
        c = result.context_alignment
        print(f"  context_alignment: {c.context_match_type.value} — {c.study_country} → France")
        print(f"    care_pathway   : {c.care_pathway_match.value}")
        print(f"    org_dependency : {c.organization_dependency.value}")

    print("\n[2] Enrichissement du claim...")
    enriched = enrich_claim_with_study(claim, result)

    print("\n[3] Analyse pipeline complet...")
    output = analyze(enriched)

    print(f"  Structure causale  : {output.causal_structure.value}")
    print(f"  Design recommandé  : {output.design_recommendation.primary_design.value}")

    if output.bias_flags:
        print("  BiasFlags :")
        for bd in output.bias_flags:
            print(f"    [{bd.severity}] {bd.flag.value}")
    else:
        print("  BiasFlags : aucun")

    if output.cas_output:
        cas = output.cas_output
        print(f"  CAS score  : {cas.cas_score:.2f}  →  {cas.verdict.value}")
        if cas.risks:
            print("  CAS risks :")
            for r in cas.risks:
                print(f"    [{r.risk_level}] {r.dimension} — {r.description[:80]}...")


# ---------------------------------------------------------------------------
# Cas 5 — PRESAGE CARE / Données algorithmiques (pas d'étude clinique)
# ---------------------------------------------------------------------------

PRESAGE_TEXT = """
Données soumises pour PRESAGE CARE (avis PECAN défavorable)

PRESAGE CARE est une plateforme de télésurveillance médicale prédictive utilisant un algorithme
d'intelligence artificielle (apprentissage automatique) pour calculer le risque d'hospitalisation
des patients âgés fragiles dans les 7 à 14 jours.

Données spécifiques soumises :
1. Développement et validation de l'algorithme :
   - Apprentissage initial sur une cohorte rétrospective de 301 patients (aides à domicile)
   - Validation sur une cohorte de 206 patients suivis pendant une durée non précisée
   - Le modèle prédit le passage aux urgences à J7 et J14 sur 9 variables binaires (symptômes rapportés)
   - Pas d'étude contrôlée randomisée. Pas de groupe comparateur.
   - Pays : France (données rétrospectives)

2. Étude TIL-003 (ODYSIGHT référencée par erreur dans ce dossier) : non applicable.

3. Résultats de performance de l'algorithme :
   - Critère de jugement principal revendiqué : réduction du nombre d'hospitalisations en urgence évitables
   - L'algorithme génère une alerte envoyée à l'équipe de télésurveillance
   - L'équipe de télésurveillance décide ensuite d'une intervention préventive
   - Le critère "hospitalisations évitables" est défini par l'algorithme lui-même (circulaire)

4. Études non spécifiques (6 études sur d'autres dispositifs de télésurveillance)

Aucune étude contrôlée randomisée spécifique à PRESAGE CARE n'est disponible.
Aucun Comité d'Événements Cliniques indépendant.
Durée de suivi : non établie dans un cadre prospectif.
"""

PRESAGE_CLAIM = ClinicalClaim(
    text="PRESAGE CARE réduit les hospitalisations en urgence évitables grâce à la télésurveillance prédictive chez les patients âgés fragiles",
    intervention="PRESAGE CARE plateforme télésurveillance prédictive IA",
    domain="geriatrics",
    endpoints=[
        Endpoint("hospitalisations en urgence évitées", EndpointNature.INSTRUMENTED,
                 CausalRole.CIRCULAR, is_primary=True,
                 description="device-predicted hospitalization — monitoring-triggered alert"),
        Endpoint("morbi-mortalité cardiovasculaire", EndpointNature.OBJECTIVE,
                 CausalRole.INDEPENDENT, is_primary=False),
    ]
)

# ---------------------------------------------------------------------------
# Cas 6 — ODYSIGHT / Études TIL + FORESEEHOME
# ---------------------------------------------------------------------------

ODYSIGHT_TEXT = """
Données soumises pour ODYSIGHT (avis LATM indéterminé)

ODYSIGHT est une application mobile de télésurveillance de l'acuité visuelle pour patients
atteints de maculopathies chroniques (DMLA exsudative, œdème maculaire diabétique).

L'application teste l'acuité visuelle via un algorithme (test du tumbling E). Un second algorithme
surveille la courbe d'acuité et génère une pré-alerte en cas de diminution détectée. Le patient
confirme sur un second test, puis l'équipe médicale est alertée.

Études spécifiques soumises :

1. TIL-001 et TIL-002 : études prospectives de performance comparant l'algorithme de détection
   d'ODYSIGHT aux méthodes standardisées (ETDRS). Pas de comparateur clinique randomisé.
   Objectif : valider les performances de l'algorithme, pas l'impact clinique.

2. TIL-003 : étude rétrospective, multicentrique, mono bras, réalisée en ouvert.
   Objectif principal : évaluer l'impact d'ODYSIGHT dans la prise en charge des patients
   atteints de maculopathies. Critère de jugement : délai de détection de la baisse d'acuité
   visuelle par l'application (mesuré par l'application elle-même).
   Effectif : non précisé. Pas de groupe contrôle. Pays : France.

3. Études non spécifiques :
   - Chew et al. (FORESEEHOME) : RCT multicentrique, 1520 patients, 1,4 ans de suivi.
     Dispositif différent (FORESEEHOME ≠ ODYSIGHT). Critère : délai de conversion DMLA
     exsudative, acuité visuelle à la conversion.
   - Mathai et al. : étude rétrospective non comparative, 2123 patients, FORESEEHOME.
   - Gross et al. : étude monocentrique appariée, 288 patients, ALLEYE (encore différent).

Aucune étude contrôlée randomisée spécifique à ODYSIGHT.
Critère de jugement principal de TIL-003 = délai de détection par l'application elle-même (circulaire).
Pas de données sur l'acuité visuelle finale, la perte visuelle, ou la mortalité.
"""

ODYSIGHT_CLAIM = ClinicalClaim(
    text="ODYSIGHT détecte précocement les rechutes de DMLA et réduit le délai de traitement chez les patients sous anti-VEGF",
    intervention="ODYSIGHT application de monitoring visuel",
    domain="ophthalmology",
    endpoints=[
        Endpoint("délai de détection rechute DMLA par l'application", EndpointNature.INSTRUMENTED,
                 CausalRole.CIRCULAR, is_primary=True,
                 description="time-to-detection by device algorithm — alert-triggered"),
        Endpoint("acuité visuelle finale", EndpointNature.OBJECTIVE,
                 CausalRole.INDEPENDENT, is_primary=False,
                 description="final visual acuity — not measured in TIL-003"),
    ]
)


if __name__ == "__main__":
    run_case(
        "INSPIRE IV — Étude EFFECT (RCT crossover, 89 patients, Allemagne/Suisse)",
        EFFECT_TEXT,
        INSPIRE_CLAIM,
    )
    run_case(
        "ZEPHYR — Étude LIBERATE (RCT ouvert, 190 patients, USA/Europe)",
        LIBERATE_TEXT,
        ZEPHYR_CLAIM,
    )
    run_case(
        "FIBROREM — Étude FIBREPIK (RCT ouvert, 170 patients, France)",
        FIBREPIK_TEXT,
        FIBROREM_CLAIM,
    )
    run_case(
        "BRAINXPERT — Étude BENEFIC (RCT double aveugle, 39 patients, Canada)",
        BENEFIC_TEXT,
        BRAINXPERT_CLAIM,
    )
    run_case(
        "PRESAGE CARE — Données algo IA (pas d'ECR, données rétrospectives France)",
        PRESAGE_TEXT,
        PRESAGE_CLAIM,
    )
    run_case(
        "ODYSIGHT — TIL-003 mono bras + FORESEEHOME non spécifique",
        ODYSIGHT_TEXT,
        ODYSIGHT_CLAIM,
    )
