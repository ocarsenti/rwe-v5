"""Test Mode 2 — Oncotype DX (score de récidive à 21 gènes) / essai TAILORx —
sans appel LLM.

Cas DIAGNOSTIQUE, pas thérapeutique — premier du genre dans le corpus. Pas un
avis CNEDiMTS (la CNEDiMTS évalue des dispositifs médicaux ; Oncotype DX est un
acte de biologie, évalué par la Commission d'évaluation des technologies de
santé diagnostiques, pronostiques et prédictives de la HAS/SEAP). Vérifié et
assumé comme tel avec Olivier avant de construire ce cas — la structure de
verdict (Service Attendu) et le raisonnement méthodologique restent comparables.

Reconstruit depuis les faits publics de l'essai TAILORx (Sparano et al., NEJM
2018) — le pivot d'Oncotype DX — et le rapport d'évaluation HAS (SEAP, 2019,
actualisé 2023, verdict Service Attendu Insuffisant maintenu).

Faits TAILORx utilisés (publiquement documentés, non inventés) :
- Design en 3 bras selon le score de récidive (RS) : RS 0-10 → hormonothérapie
  seule (non randomisé) ; RS 11-25 → randomisé hormonothérapie seule vs
  chimio+hormonothérapie ; RS >25 → chimio (non randomisé). Seul le bras
  randomisé (RS 11-25) est modélisé ici.
- N total 10 273 ; bras randomisé (RS 11-25) : 6 711
- Population : cancer du sein RH+/HER2-, ganglions négatifs
- Critère principal : survie sans maladie invasive (IDFS)
- Suivi médian : 7,5 ans (publication princeps 2018)
- Financement académique (NCI/ECOG-ACRIN, groupe coopérateur)
- Résultat : pas de bénéfice de la chimiothérapie ajoutée dans le bras
  randomisé global (bénéfice observé dans un sous-groupe : femmes ≤50 ans,
  RS 16-25)

Critique HAS réelle (SEAP 2019, confirmée 2023) : les essais disponibles ne
permettent pas de déterminer si les signatures génomiques apportent une valeur
ajoutée par rapport aux critères clinico-pathologiques déjà utilisés "en
contexte français" — un problème de comparateur/transposabilité, pas de
validité interne de TAILORx lui-même. Note structurelle importante : TAILORx
compare chimio vs pas de chimio DANS une population déjà sélectionnée par le
test — pas "décision guidée par le test" vs "décision guidée par les critères
cliniques standards". Le moteur, à qui on ne donne que les faits de protocole,
devrait retrouver un signal de ce type sans qu'on le lui dise.
"""
import sys
sys.path.insert(0, "/home/claude/rwe-v5")

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study

ONCOTYPE_JSON = {
    "acronym": "TAILORx",
    "title": (
        "TAILORx — Trial Assigning IndividuaLized Options for Treatment (Rx) — "
        "essai prospectif à 3 bras selon le score de récidive Oncotype DX, "
        "bras randomisé RS 11-25 : hormonothérapie seule vs chimio+hormonothérapie"
    ),
    "publication_year": 2018,
    "registration_id": "NCT00310180",
    "funding_type": "public",
    "study_design": "RCT",
    "is_randomized": True,
    "blinding_level": "open_label",
    "who_is_blinded": None,
    "allocation_concealment": True,
    "protocol_registered_before_enrollment": True,
    "has_comparator": True,
    "comparator_type": "ACTIVE",
    "comparator_description": "Hormonothérapie adjuvante seule (sans chimiothérapie)",
    "n_patients": 6711,
    "age_min": None,
    "age_max": None,
    "key_inclusion_criteria": [
        "Cancer du sein RH+ (récepteurs hormonaux positifs), HER2-négatif",
        "Ganglions axillaires négatifs",
        "Score de récidive Oncotype DX intermédiaire (11-25)",
    ],
    "key_exclusion_criteria": [],
    "device_studied": "Test Oncotype DX (score de récidive à 21 gènes)",
    "care_setting": "outpatient",
    "operator_training_required": False,
    "follow_up_months": 90.0,
    "longest_follow_up_months": 90.0,
    "dropout_rate_pct": None,
    "primary_analysis_set": "ITT",
    "sample_size_calculation_provided": True,
    "primary_endpoint_met": True,
    "study_countries": ["USA", "Canada"],
    "key_safety_signals": [],
    "endpoints": [
        {
            "name": "Survie sans maladie invasive (IDFS) à 9 ans",
            "is_primary": True,
            "time_point": "9 ans (suivi médian 7,5 ans à la publication princeps)",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "NON_INFERIOR",
            "reached_significance": True,
        },
        {
            "name": "Survie globale",
            "is_primary": False,
            "time_point": "9 ans",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "NON_INFERIOR",
            "reached_significance": True,
        },
    ],
    "device_alignment": {
        "device_match_type": "EXACT_DEVICE",
        "device_description_study": "Test Oncotype DX (score de récidive à 21 gènes)",
        "device_description_claim": "Test Oncotype DX (score de récidive à 21 gènes)",
        "justification": "Même test, même version, aucune extrapolation dispositif.",
    },
    "population_alignment": {
        "population_match_type": "EXACT_INDICATION",
        "population_description_study": "Cancer du sein RH+/HER2-, N0, score de récidive 11-25, cohorte nord-américaine",
        "population_description_claim": "Cancer du sein RH+/HER2- de stade précoce, patientes françaises en incertitude décisionnelle sur la chimiothérapie adjuvante",
        "eligibility_shift": "MINOR",
        "justification": "Même définition clinique de la population, cohorte d'origine nord-américaine plutôt que française.",
    },
    "context_alignment": {
        "context_match_type": "DIFFERENT_HEALTHCARE_SYSTEM",
        "study_country": "USA/Canada",
        "target_country": "France",
        "care_pathway_match": "PARTIAL",
        "organization_dependency": "MEDIUM",
        "justification": (
            "Système de santé et pratiques de décision oncologique différents du "
            "système français ; algorithmes clinico-pathologiques de référence "
            "(ex. équations de Magee, avis de RCP) utilisés en routine en France "
            "n'ont pas de rôle formalisé dans le protocole TAILORx."
        ),
    },
    # Ajouté après un premier passage sans ce champ (l'écart le plus important
    # était absent des gaps produits) : la vraie critique HAS porte sur le
    # COMPARATEUR, pas la géographie. TAILORx compare chimio vs pas de chimio
    # DANS une population déjà sélectionnée par le test — pas "décision guidée
    # par le test" vs "décision guidée par les critères clinico-pathologiques
    # standards", qui est ce que la claim revendique implicitement.
    "comparator_alignment": {
        "comparator_match_type": "DIFFERENT_COMPARATOR",
        "comparator_description_claim": "Décision de chimiothérapie guidée par les critères clinico-pathologiques standards (sans le test)",
        "comparator_description_study": "Hormonothérapie seule vs chimio+hormonothérapie, au sein d'une population déjà sélectionnée par le score Oncotype DX",
        "justification": (
            "TAILORx ne compare jamais 'décision guidée par le test' à 'décision "
            "guidée par les critères cliniques standards' — il compare deux "
            "traitements DANS le sous-groupe déjà défini par le test. La question "
            "de la valeur ajoutée du test lui-même par rapport à la pratique "
            "existante n'est pas testée par ce design."
        ),
    },
}

claim = ClinicalClaim(
    text=(
        "Oncotype DX identifie, parmi les patientes avec un cancer du sein RH+/"
        "HER2- de stade précoce et un score de récidive intermédiaire (11-25), "
        "celles qui peuvent éviter une chimiothérapie adjuvante sans perte de "
        "survie sans maladie invasive, par rapport à une décision fondée sur les "
        "critères clinico-pathologiques standards"
    ),
    intervention="Test génomique de score de récidive à 21 gènes (Oncotype DX)",
    domain="cancer",
    endpoints=[
        Endpoint(
            "Survie sans maladie invasive (IDFS) à 9 ans",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=True,
            is_validated_surrogate=False,
            description="critère composite (récidive invasive, second cancer primitif, décès), non adjudiqué en aveugle",
        ),
        Endpoint(
            "Survie globale",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="critère clinique dur",
        ),
    ],
)

print("=" * 70)
print("  MODE 2 — Oncotype DX / TAILORx — pipeline complet (sans LLM)")
print("=" * 70)

print("\n[1] Construction StudyObject...")
study = _parse_study_object_result(ONCOTYPE_JSON, claim.intervention, claim.text)
print(f"  device_studied  : {study.device_studied}")
print(f"  study_design    : {study.study_design.value if study.study_design else 'None'}")
print(f"  is_randomized   : {study.is_randomized}")
print(f"  has_comparator  : {study.has_comparator}  ({study.comparator_type.value})")
print(f"  n_patients      : {study.n_patients}")
print(f"  follow_up       : {study.follow_up_months} mois")
print(f"  countries       : {study.study_countries}")

print("\n" + "─" * 70)
print("[2] Enrichissement claim + analyse épistémique (mode REVIEW)...")
enrich_claim_with_study_object(claim, study)
output = analyze(claim)

print(f"  Claim level       : {output.claim_level.value}")
print(f"  Causal structure  : {output.causal_structure.value}")
print(f"  Design recommandé : {output.design_recommendation.primary_design.value}")
if output.bias_flags:
    print("  BiasFlags :")
    for bd in output.bias_flags:
        print(f"    [{bd.severity}] {bd.flag.value} — {bd.detail[:90]}")
else:
    print("  BiasFlags : aucun")

print("\n  Endpoint analysis :")
for ea in output.endpoint_analysis:
    print(f"    {ea.endpoint.name[:50]:50s} nature={ea.nature.value:12s} reason={ea.nature_reason}")

print("\n" + "─" * 70)
print("[3] Comparaison claim vs étude (gaps device/population/context/design/endpoint)...")
report = compare_claim_to_study(claim, study, epistemic_output=output)
if report.gaps:
    for g in report.gaps:
        print(f"    [{g.severity}] {g.dimension} — {g.description[:100]}")
else:
    print("  Aucun gap détecté.")
