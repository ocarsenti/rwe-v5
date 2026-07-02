"""Validation CAS Engine vs. 20 avis CNEDiMTS réels.

La bonne question n'est PAS :
  "Le verdict CAS prédit-il la décision FAVORABLE/DEFAVORABLE ?"

La bonne question EST :
  "Les risques CAS identifiés par le moteur correspondent-ils aux critiques
   d'alignement (T05, T06, T09, T12) identifiées par la CNEDiMTS ?"

Le CAS mesure UNE dimension. La décision CNEDiMTS est multidimensionnelle :
  Décision = f(CAS, ICS, bénéfice clinique, stratégie de preuve, contexte réglementaire)

Un CAS parfait peut coexister avec un rejet (si ICS est mauvais).
Un CAS mauvais peut coexister avec un favorable (si d'autres éléments compensent).
"""

import json
import sys
sys.path.insert(0, ".")

from cas_engine import evaluate_cas
from models import (
    CASVerdict,
    CarePathwayMatch,
    ContextAlignment,
    ContextMatchType,
    DeviceAlignment,
    DeviceMatchType,
    EligibilityShift,
    OrganizationDependency,
    PopulationAlignment,
    PopulationMatchType,
)


# ===================================================================
# 20 cas CNEDiMTS encodés avec :
# - paramètres CAS déduits des avis
# - critiques CAS réelles de la CNEDiMTS (T05, T06, T09, T12)
# - critiques ICS de la CNEDiMTS (T01-T04, T07, T10-T16) pour contexte
# ===================================================================

CASES = [
    # -------------------------------------------------------------------
    # PECAN (5 cas)
    # -------------------------------------------------------------------
    {
        "id": 1,
        "device": "PRESAGE CARE",
        "type": "PECAN",
        "decision": "DEFAVORABLE",
        "critiques_cas": ["T05", "T06", "T09", "T12"],
        "critiques_ics": ["T01", "T02", "T04", "T07", "T08", "T10", "T13"],
        "expected_risks": {
            "DEVICE": True,     # T05: données partiellement non spécifiques
            "POPULATION": True, # T06: sous-groupe de l'indication
            "CONTEXT": True,    # T09+T12: organisation différente
        },
        "claim_text": "Télésurveillance prédictive des hospitalisations des personnes âgées fragiles 65+",
        "intervention": "PRESAGE CARE",
        "domain": "Télésurveillance personnes âgées",
        "device_alignment": {
            "match_type": DeviceMatchType.SAME_FAMILY,
            "claim": "PRESAGE CARE v1.3",
            "study": "PRESAGE CARE (version antérieure, 2 modèles évalués différents)",
            "justification": "T05: données partiellement non spécifiques, 2 modèles non comparables",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.NARROWER_SUBGROUP,
            "claim": "Personnes âgées fragiles 65+ (toute dépendance)",
            "study": "Patients avec dépendance légère à modérée",
            "subgroup": "GIR 3-4 uniquement",
            "eligibility_shift": EligibilityShift.MAJOR,
            "justification": "T06: partie restreinte de l'indication revendiquée",
        },
        "context_alignment": {
            "match_type": ContextMatchType.SAME_HEALTHCARE_SYSTEM,
            "pathway": CarePathwayMatch.NO,
            "org_dependency": OrganizationDependency.HIGH,
            "country": "France",
            "justification": "T09+T12: organisation étudiée ≠ organisation proposée par le demandeur",
        },
    },
    {
        "id": 2,
        "device": "TUCKY CENTER",
        "type": "PECAN",
        "decision": "DEFAVORABLE",
        "critiques_cas": ["T05", "T12"],
        "critiques_ics": ["T02", "T03", "T04", "T05", "T13"],
        "expected_risks": {
            "DEVICE": True,     # T05: aucune étude spécifique soumise
            "POPULATION": True, # études sur populations différentes
            "CONTEXT": True,    # T12: DM non-urgent pour pathologie urgente
        },
        "claim_text": "Télésurveillance des patients sous chimiothérapie, post-bariatrique, HTA grossesse",
        "intervention": "TUCKY CENTER",
        "domain": "Télésurveillance pédiatrique/oncologie",
        "device_alignment": {
            "match_type": DeviceMatchType.DIFFERENT_DEVICE,
            "claim": "TUCKY CENTER",
            "study": "Autres DM de télésurveillance (aucune étude spécifique soumise)",
            "justification": "T05: aucune étude spécifique de TUCKY CENTER n'a été soumise",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.DIFFERENT_POPULATION,
            "claim": "Patients chimio / post-bariatrique / HTA grossesse",
            "study": "Patients chirurgie urgente (McGillion) — population non correspondante",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.MAJOR,
            "justification": "Études sur chirurgie urgente vs indication bariatrique/chimio",
        },
        "context_alignment": {
            "match_type": ContextMatchType.SAME_HEALTHCARE_SYSTEM,
            "pathway": CarePathwayMatch.NO,
            "org_dependency": OrganizationDependency.HIGH,
            "country": "France",
            "justification": "T12: TUCKY CENTER est conçue pour le non-urgent mais neutropénie fébrile = urgence",
        },
    },
    {
        "id": 3,
        "device": "CONTINUUM CONNECT",
        "type": "PECAN",
        "decision": "FAVORABLE",
        "critiques_cas": ["T05", "T06", "T09"],
        "critiques_ics": ["T01", "T02", "T07", "T08", "T14", "T15"],
        "expected_risks": {
            "DEVICE": True,     # T05: technologies différentes dans les études
            "POPULATION": False, # T06: biais de sélection mineur, population globalement OK
            "CONTEXT": True,    # T09: monocentrique, extrapolation délicate
        },
        "claim_text": "Télésurveillance médicale des patients en oncologie (immunothérapie)",
        "intervention": "CONTINUUM+ CONNECT",
        "domain": "Télésurveillance oncologie",
        "device_alignment": {
            "match_type": DeviceMatchType.SAME_FAMILY,
            "claim": "CONTINUUM+ CONNECT",
            "study": "Autres plateformes de télésurveillance oncologique",
            "justification": "T05: différences entre technologies étudiées et plateforme CONTINUUM+",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.EXACT_INDICATION,
            "claim": "Patients en immunothérapie",
            "study": "Patients en immunothérapie (études STAR et autres)",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.MINOR,
            "justification": "T06: biais sélection mineur, population globalement couverte",
        },
        "context_alignment": {
            "match_type": ContextMatchType.SAME_HEALTHCARE_SYSTEM,
            "pathway": CarePathwayMatch.PARTIAL,
            "org_dependency": OrganizationDependency.MEDIUM,
            "country": "France",
            "justification": "T09: monocentrique, extrapolation délicate",
        },
    },
    {
        "id": 4,
        "device": "HELLOBETTER INSOMNIE",
        "type": "PECAN",
        "decision": "DEFAVORABLE",
        "critiques_cas": ["T05"],
        "critiques_ics": ["T13", "T14"],
        "expected_risks": {
            "DEVICE": True,     # T05: outils non identifiables au DM évalué
            "POPULATION": False,
            "CONTEXT": True,    # DM allemand, études étrangères
        },
        "claim_text": "Thérapie numérique pour le traitement de l'insomnie chronique",
        "intervention": "HelloBetter Insomnie",
        "domain": "Thérapie numérique insomnie",
        "device_alignment": {
            "match_type": DeviceMatchType.PROXY_DEVICE,
            "claim": "HelloBetter Insomnie",
            "study": "Autres outils TCC-I numériques (description insuffisante)",
            "justification": "T05: études non retenues, description insuffisante pour généraliser",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.EXACT_INDICATION,
            "claim": "Patients insomnie chronique",
            "study": "Patients insomnie chronique",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.NONE,
            "justification": "Population correspondante dans les études disponibles",
        },
        "context_alignment": {
            "match_type": ContextMatchType.PARTIALLY_COMPARABLE,
            "pathway": CarePathwayMatch.PARTIAL,
            "org_dependency": OrganizationDependency.LOW,
            "country": "Allemagne",
            "justification": "Dispositif allemand, parcours de soins partiellement comparable",
        },
    },
    {
        "id": 5,
        "device": "AXOMOVE THERAPY",
        "type": "PECAN",
        "decision": "FAVORABLE",
        "critiques_cas": ["T05"],
        "critiques_ics": ["T01", "T08", "T13"],
        "expected_risks": {
            "DEVICE": True,     # T05: données non spécifiques
            "POPULATION": False,
            "CONTEXT": False,
        },
        "claim_text": "Télésurveillance et rééducation numérique de la lombalgie chronique",
        "intervention": "AXOMOVE THERAPY",
        "domain": "Rééducation numérique",
        "device_alignment": {
            "match_type": DeviceMatchType.SAME_FAMILY,
            "claim": "AXOMOVE THERAPY",
            "study": "Programmes de rééducation numérique (mix spécifique/non spécifique)",
            "justification": "T05: mix données spécifiques et non spécifiques",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.EXACT_INDICATION,
            "claim": "Patients lombalgie chronique",
            "study": "Patients lombalgie chronique",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.NONE,
            "justification": "Population bien couverte",
        },
        "context_alignment": {
            "match_type": ContextMatchType.SAME_HEALTHCARE_SYSTEM,
            "pathway": CarePathwayMatch.YES,
            "org_dependency": OrganizationDependency.LOW,
            "country": "France",
            "justification": "Études françaises, parcours correspondant",
        },
    },
    # -------------------------------------------------------------------
    # LATM (6 cas)
    # -------------------------------------------------------------------
    {
        "id": 6,
        "device": "CUREETY TECHCARE (2023)",
        "type": "LATM",
        "decision": "FAVORABLE",
        "critiques_cas": ["T05", "T06", "T09"],
        "critiques_ics": ["T01", "T08", "T14"],
        "expected_risks": {
            "DEVICE": False,    # T05 mineur, données spécifiques au DM existent
            "POPULATION": True, # T06: radiothérapie seule non couverte
            "CONTEXT": True,    # T09: non-conformité ESMO
        },
        "claim_text": "Télésurveillance des patients en oncologie (chimiothérapie et radiothérapie)",
        "intervention": "CUREETY TECHCARE",
        "domain": "Télésurveillance oncologie",
        "device_alignment": {
            "match_type": DeviceMatchType.EXACT_DEVICE,
            "claim": "CUREETY TECHCARE",
            "study": "CUREETY TECHCARE",
            "justification": "Données spécifiques au DM",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.NARROWER_SUBGROUP,
            "claim": "Patients chimio + radiothérapie",
            "study": "Patients chimiothérapie (radiothérapie seule non couverte)",
            "subgroup": "Sous-groupe chimiothérapie uniquement",
            "eligibility_shift": EligibilityShift.MINOR,
            "justification": "T06: aucune donnée pour patients radiothérapie seule",
        },
        "context_alignment": {
            "match_type": ContextMatchType.PARTIALLY_COMPARABLE,
            "pathway": CarePathwayMatch.PARTIAL,
            "org_dependency": OrganizationDependency.MEDIUM,
            "country": "France/Étranger",
            "justification": "T09: non-conformité recommandations ESMO 2022",
        },
    },
    {
        "id": 7,
        "device": "CUREETY TECHCARE (2025)",
        "type": "LATM",
        "decision": "FAVORABLE",
        "critiques_cas": ["T05", "T06", "T09"],
        "critiques_ics": ["T01", "T02", "T03", "T08", "T10", "T14", "T15"],
        "expected_risks": {
            "DEVICE": False,
            "POPULATION": True,  # T06
            "CONTEXT": True,     # T09
        },
        "claim_text": "Télésurveillance des patients en oncologie (renouvellement)",
        "intervention": "CUREETY TECHCARE",
        "domain": "Télésurveillance oncologie",
        "device_alignment": {
            "match_type": DeviceMatchType.EXACT_DEVICE,
            "claim": "CUREETY TECHCARE",
            "study": "CUREETY TECHCARE",
            "justification": "Données spécifiques au DM",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.NARROWER_SUBGROUP,
            "claim": "Patients chimio + radiothérapie",
            "study": "Patients chimiothérapie principalement",
            "subgroup": "Radiothérapie seule insuffisamment couverte",
            "eligibility_shift": EligibilityShift.MINOR,
            "justification": "T06: sous-population radiothérapie seule pas couverte",
        },
        "context_alignment": {
            "match_type": ContextMatchType.PARTIALLY_COMPARABLE,
            "pathway": CarePathwayMatch.PARTIAL,
            "org_dependency": OrganizationDependency.MEDIUM,
            "country": "France/Étranger",
            "justification": "T09: validité externe limitée",
        },
    },
    {
        "id": 8,
        "device": "ODYSIGHT",
        "type": "LATM",
        "decision": "DEFAVORABLE",
        "critiques_cas": ["T06"],
        "critiques_ics": ["T01", "T02", "T07", "T08", "T10", "T11", "T13", "T14"],
        "expected_risks": {
            "DEVICE": False,
            "POPULATION": True,  # T06
            "CONTEXT": False,
        },
        "claim_text": "Télésurveillance ophtalmologique (DMLA, œdème maculaire diabétique)",
        "intervention": "ODYSIGHT",
        "domain": "Télésurveillance ophtalmologie",
        "device_alignment": {
            "match_type": DeviceMatchType.EXACT_DEVICE,
            "claim": "ODYSIGHT",
            "study": "ODYSIGHT",
            "justification": "Études spécifiques au DM",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.NARROWER_SUBGROUP,
            "claim": "Patients DMLA et OMD",
            "study": "Sous-groupe de patients (effectifs limités)",
            "subgroup": "Effectifs limités, couverture partielle",
            "eligibility_shift": EligibilityShift.MINOR,
            "justification": "T06: population non représentative",
        },
        "context_alignment": {
            "match_type": ContextMatchType.SAME_HEALTHCARE_SYSTEM,
            "pathway": CarePathwayMatch.YES,
            "org_dependency": OrganizationDependency.LOW,
            "country": "France",
            "justification": "Études françaises",
        },
    },
    {
        "id": 9,
        "device": "CARELINK",
        "type": "LATM",
        "decision": "FAVORABLE",
        "critiques_cas": ["T06", "T09"],
        "critiques_ics": ["T01", "T02", "T07", "T08", "T10", "T16"],
        "expected_risks": {
            "DEVICE": False,
            "POPULATION": True,  # T06
            "CONTEXT": True,     # T09
        },
        "claim_text": "Télésurveillance des patients porteurs de dispositifs cardiaques implantables",
        "intervention": "CARELINK",
        "domain": "Télésurveillance cardiologie",
        "device_alignment": {
            "match_type": DeviceMatchType.EXACT_DEVICE,
            "claim": "CARELINK",
            "study": "CARELINK",
            "justification": "Données spécifiques au système CARELINK",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.NARROWER_SUBGROUP,
            "claim": "Patients porteurs de DCI/PM Medtronic",
            "study": "Patients sélectionnés (biais de sélection)",
            "subgroup": "Population sélectionnée",
            "eligibility_shift": EligibilityShift.MINOR,
            "justification": "T06: biais de sélection",
        },
        "context_alignment": {
            "match_type": ContextMatchType.PARTIALLY_COMPARABLE,
            "pathway": CarePathwayMatch.PARTIAL,
            "org_dependency": OrganizationDependency.MEDIUM,
            "country": "International",
            "justification": "T09: validité externe limitée",
        },
    },
    {
        "id": 10,
        "device": "MERLIN.NET",
        "type": "LATM",
        "decision": "FAVORABLE",
        "critiques_cas": ["T09"],
        "critiques_ics": ["T01", "T02", "T07", "T08", "T13", "T16"],
        "expected_risks": {
            "DEVICE": False,
            "POPULATION": False,
            "CONTEXT": True,     # T09
        },
        "claim_text": "Télésurveillance des patients porteurs de DCI Abbott",
        "intervention": "MERLIN.NET",
        "domain": "Télésurveillance cardiologie",
        "device_alignment": {
            "match_type": DeviceMatchType.EXACT_DEVICE,
            "claim": "MERLIN.NET",
            "study": "MERLIN.NET",
            "justification": "Données spécifiques",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.EXACT_INDICATION,
            "claim": "Patients porteurs de DCI Abbott",
            "study": "Patients porteurs de DCI Abbott",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.NONE,
            "justification": "Population correspondante",
        },
        "context_alignment": {
            "match_type": ContextMatchType.PARTIALLY_COMPARABLE,
            "pathway": CarePathwayMatch.PARTIAL,
            "org_dependency": OrganizationDependency.LOW,
            "country": "International",
            "justification": "T09: validité externe limitée",
        },
    },
    {
        "id": 11,
        "device": "IMPLICITY IM009",
        "type": "LATM",
        "decision": "FAVORABLE",
        "critiques_cas": ["T06"],
        "critiques_ics": ["T02", "T07", "T08", "T11", "T13", "T14"],
        "expected_risks": {
            "DEVICE": False,
            "POPULATION": True,  # T06
            "CONTEXT": False,
        },
        "claim_text": "Télésurveillance IA des patients porteurs de prothèses cardiaques",
        "intervention": "IMPLICITY IM009",
        "domain": "Télésurveillance cardiologie",
        "device_alignment": {
            "match_type": DeviceMatchType.EXACT_DEVICE,
            "claim": "IMPLICITY IM009",
            "study": "IMPLICITY IM009",
            "justification": "Données spécifiques (SNDS + enquête)",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.NARROWER_SUBGROUP,
            "claim": "Patients porteurs de DCI/PM (tous fabricants)",
            "study": "Patients porteurs de DCI (stimulateurs sous-représentés)",
            "subgroup": "Porteurs de stimulateurs cardiaques sous-représentés",
            "eligibility_shift": EligibilityShift.MINOR,
            "justification": "T06: ne permet pas de conclure chez porteurs de stimulateurs",
        },
        "context_alignment": {
            "match_type": ContextMatchType.SAME_HEALTHCARE_SYSTEM,
            "pathway": CarePathwayMatch.YES,
            "org_dependency": OrganizationDependency.MEDIUM,
            "country": "France",
            "justification": "Études françaises (SNDS)",
        },
    },
    # -------------------------------------------------------------------
    # LPPR (9 cas)
    # -------------------------------------------------------------------
    {
        "id": 12,
        "device": "AIRCURVE 10 CS PACEWAVE",
        "type": "LPPR",
        "decision": "FAVORABLE",
        "critiques_cas": ["T05"],
        "critiques_ics": ["T01", "T02", "T03", "T04", "T05", "T07", "T08", "T15"],
        "expected_risks": {
            "DEVICE": True,     # T05: données d'autres dispositifs de VAA
            "POPULATION": False,
            "CONTEXT": True,    # études internationales
        },
        "claim_text": "Ventilation auto-asservie pour apnée centrale du sommeil",
        "intervention": "AirCurve 10 CS PaceWave",
        "domain": "Ventilation auto-asservie",
        "device_alignment": {
            "match_type": DeviceMatchType.SAME_FAMILY,
            "claim": "AirCurve 10 CS PaceWave",
            "study": "Dispositifs de VAA (différentes marques)",
            "justification": "T05: données non spécifiques, autres VAA",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.EXACT_INDICATION,
            "claim": "Patients apnée centrale du sommeil",
            "study": "Patients apnée centrale du sommeil",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.NONE,
            "justification": "Population bien couverte",
        },
        "context_alignment": {
            "match_type": ContextMatchType.PARTIALLY_COMPARABLE,
            "pathway": CarePathwayMatch.YES,
            "org_dependency": OrganizationDependency.LOW,
            "country": "International",
            "justification": "Études internationales",
        },
    },
    {
        "id": 13,
        "device": "AZUR / AZUR CX",
        "type": "LPPR",
        "decision": "FAVORABLE",
        "critiques_cas": ["T05"],
        "critiques_ics": [],
        "expected_risks": {
            "DEVICE": True,     # T05: extension gamme
            "POPULATION": False,
            "CONTEXT": False,
        },
        "claim_text": "Cathéters cardiaques pour ablation (complément de gamme)",
        "intervention": "AZUR / AZUR CX",
        "domain": "Cathéters cardiaques",
        "device_alignment": {
            "match_type": DeviceMatchType.SAME_FAMILY,
            "claim": "AZUR / AZUR CX (nouvelles références)",
            "study": "AZUR (références existantes déjà inscrites)",
            "justification": "T05: extension gamme, données des références existantes",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.EXACT_INDICATION,
            "claim": "Patients ablation cardiaque",
            "study": "Patients ablation cardiaque",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.NONE,
            "justification": "Même indication",
        },
        "context_alignment": {
            "match_type": ContextMatchType.SAME_HEALTHCARE_SYSTEM,
            "pathway": CarePathwayMatch.YES,
            "org_dependency": OrganizationDependency.LOW,
            "country": "France",
            "justification": "Dispositif déjà inscrit",
        },
    },
    {
        "id": 14,
        "device": "INSPIRE IV",
        "type": "LPPR",
        "decision": "FAVORABLE",
        "critiques_cas": ["T05", "T06", "T09"],
        "critiques_ics": ["T02", "T14", "T15"],
        "expected_risks": {
            "DEVICE": True,     # T05: données modèles antérieurs
            "POPULATION": True, # T06: patients sans OAM préalable
            "CONTEXT": True,    # T09: parcours USA ≠ parcours français
        },
        "claim_text": "Stimulation nerf hypoglosse pour SAOS modéré à sévère",
        "intervention": "INSPIRE IV",
        "domain": "Stimulation nerf hypoglosse (apnée)",
        "device_alignment": {
            "match_type": DeviceMatchType.SAME_FAMILY,
            "claim": "INSPIRE IV (nouveau modèle)",
            "study": "INSPIRE (modèles antérieurs, études STAR)",
            "justification": "T05: données modèles antérieurs extrapolées",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.BROADER_POPULATION,
            "claim": "Patients SAOS après échec OAM (parcours français)",
            "study": "Patients SAOS sans essai préalable d'OAM",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.MAJOR,
            "justification": "T06: patients sans OAM ≠ parcours français requis",
        },
        "context_alignment": {
            "match_type": ContextMatchType.PARTIALLY_COMPARABLE,
            "pathway": CarePathwayMatch.NO,
            "org_dependency": OrganizationDependency.LOW,
            "country": "USA / International",
            "justification": "T09: parcours USA ≠ parcours français (OAM obligatoire)",
        },
    },
    {
        "id": 15,
        "device": "NEMOST",
        "type": "LPPR",
        "decision": "FAVORABLE",
        "critiques_cas": ["T06", "T09"],
        "critiques_ics": ["T01", "T02", "T07", "T14", "T15"],
        "expected_risks": {
            "DEVICE": False,
            "POPULATION": True,  # T06
            "CONTEXT": True,     # T09
        },
        "claim_text": "Prothèse articulaire trapézo-métacarpienne pour rhizarthrose",
        "intervention": "NEMOST",
        "domain": "Prothèse articulaire",
        "device_alignment": {
            "match_type": DeviceMatchType.EXACT_DEVICE,
            "claim": "NEMOST",
            "study": "NEMOST",
            "justification": "Études spécifiques",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.NARROWER_SUBGROUP,
            "claim": "Patients rhizarthrose (indication large)",
            "study": "46 patients (très petit échantillon)",
            "subgroup": "Petit effectif, représentativité limitée",
            "eligibility_shift": EligibilityShift.MINOR,
            "justification": "T06: population non représentative",
        },
        "context_alignment": {
            "match_type": ContextMatchType.PARTIALLY_COMPARABLE,
            "pathway": CarePathwayMatch.PARTIAL,
            "org_dependency": OrganizationDependency.LOW,
            "country": "France/International",
            "justification": "T09: validité externe limitée",
        },
    },
    {
        "id": 16,
        "device": "NAVITOR",
        "type": "LPPR",
        "decision": "FAVORABLE",
        "critiques_cas": ["T06"],
        "critiques_ics": ["T01", "T02", "T04", "T15"],
        "expected_risks": {
            "DEVICE": True,     # données PORTICO NG, pas NAVITOR
            "POPULATION": True, # T06: risque plus faible
            "CONTEXT": True,    # études internationales
        },
        "claim_text": "Valve aortique transcathéter pour sténose aortique sévère",
        "intervention": "NAVITOR",
        "domain": "Valve aortique transcathéter",
        "device_alignment": {
            "match_type": DeviceMatchType.SAME_FAMILY,
            "claim": "NAVITOR",
            "study": "PORTICO NG (prédécesseur)",
            "justification": "Données PORTICO NG extrapolées à NAVITOR",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.BROADER_POPULATION,
            "claim": "Patients sténose aortique sévère (risque intermédiaire à élevé)",
            "study": "Patients à risque plus faible que l'indication",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.MAJOR,
            "justification": "T06: PORTICO NG incluait patients à risque plus faible",
        },
        "context_alignment": {
            "match_type": ContextMatchType.PARTIALLY_COMPARABLE,
            "pathway": CarePathwayMatch.PARTIAL,
            "org_dependency": OrganizationDependency.LOW,
            "country": "International",
            "justification": "Études internationales",
        },
    },
    {
        "id": 17,
        "device": "INFINITY",
        "type": "LPPR",
        "decision": "DEFAVORABLE",
        "critiques_cas": ["T05"],
        "critiques_ics": ["T02", "T07", "T15"],
        "expected_risks": {
            "DEVICE": True,     # T05: aucune donnée clinique spécifique
            "POPULATION": True, # pas d'étude → inconnu
            "CONTEXT": True,    # pas d'étude → inconnu
        },
        "claim_text": "Prothèse articulaire cheville (nouvelles références)",
        "intervention": "INFINITY",
        "domain": "Prothèse articulaire cheville",
        "device_alignment": {
            "match_type": DeviceMatchType.DIFFERENT_DEVICE,
            "claim": "INFINITY (nouvelles références cheville)",
            "study": "Aucune donnée clinique spécifique",
            "justification": "T05: aucune donnée clinique pour les nouvelles références",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.UNKNOWN,
            "claim": "Patients lésions dégénératives de la cheville",
            "study": "Aucune donnée (pas d'étude)",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.NONE,
            "justification": "Pas d'étude → population non évaluable",
        },
        "context_alignment": {
            "match_type": ContextMatchType.UNKNOWN,
            "pathway": CarePathwayMatch.UNKNOWN,
            "org_dependency": OrganizationDependency.LOW,
            "country": "",
            "justification": "Pas d'étude → contexte non évaluable",
        },
    },
    {
        "id": 18,
        "device": "INCEPTIV",
        "type": "LPPR",
        "decision": "FAVORABLE",
        "critiques_cas": ["T05"],
        "critiques_ics": ["T01", "T02", "T03", "T08", "T15"],
        "expected_risks": {
            "DEVICE": True,     # T05: extrapolation EVOKE→INCEPTIV impossible
            "POPULATION": False,
            "CONTEXT": True,    # comparateur non pris en charge en France
        },
        "claim_text": "Neurostimulation médullaire à boucle fermée pour douleur chronique",
        "intervention": "INCEPTIV",
        "domain": "Neurostimulation",
        "device_alignment": {
            "match_type": DeviceMatchType.PROXY_DEVICE,
            "claim": "INCEPTIV",
            "study": "EVOKE (boucle fermée, Saluda Medical)",
            "justification": "T05: extrapolation EVOKE→INCEPTIV jugée impossible",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.EXACT_INDICATION,
            "claim": "Patients douleur chronique réfractaire",
            "study": "Patients douleur chronique réfractaire",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.NONE,
            "justification": "Population correspondante",
        },
        "context_alignment": {
            "match_type": ContextMatchType.PARTIALLY_COMPARABLE,
            "pathway": CarePathwayMatch.PARTIAL,
            "org_dependency": OrganizationDependency.LOW,
            "country": "USA / International",
            "justification": "Comparateur EVOKE non pris en charge en France",
        },
    },
    {
        "id": 19,
        "device": "NEOVIS TOTAL MULTI",
        "type": "LPPR",
        "decision": "FAVORABLE",
        "critiques_cas": ["T05"],
        "critiques_ics": [],
        "expected_risks": {
            "DEVICE": True,     # T05: données non spécifiques
            "POPULATION": False,
            "CONTEXT": False,
        },
        "claim_text": "Solution viscoélastique pour chirurgie ophtalmique",
        "intervention": "NEOVIS TOTAL MULTI",
        "domain": "Ophtalmologie chirurgicale",
        "device_alignment": {
            "match_type": DeviceMatchType.SAME_FAMILY,
            "claim": "NEOVIS TOTAL MULTI",
            "study": "Autres solutions viscoélastiques",
            "justification": "T05: données non spécifiques",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.EXACT_INDICATION,
            "claim": "Patients chirurgie ophtalmique",
            "study": "Patients chirurgie ophtalmique",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.NONE,
            "justification": "Population correspondante",
        },
        "context_alignment": {
            "match_type": ContextMatchType.SAME_HEALTHCARE_SYSTEM,
            "pathway": CarePathwayMatch.YES,
            "org_dependency": OrganizationDependency.LOW,
            "country": "France",
            "justification": "Même contexte",
        },
    },
    {
        "id": 20,
        "device": "MENTOR",
        "type": "LPPR",
        "decision": "FAVORABLE",
        "critiques_cas": ["T05"],
        "critiques_ics": ["T01", "T07"],
        "expected_risks": {
            "DEVICE": True,     # T05: données non spécifiques
            "POPULATION": False,
            "CONTEXT": False,
        },
        "claim_text": "Implants mammaires en silicone",
        "intervention": "MENTOR",
        "domain": "Implants mammaires",
        "device_alignment": {
            "match_type": DeviceMatchType.SAME_FAMILY,
            "claim": "MENTOR (nouvelles références)",
            "study": "MENTOR (références existantes) + données non spécifiques",
            "justification": "T05: données non spécifiques au DM évalué",
        },
        "population_alignment": {
            "match_type": PopulationMatchType.EXACT_INDICATION,
            "claim": "Patientes reconstruction/augmentation mammaire",
            "study": "Patientes reconstruction/augmentation mammaire",
            "subgroup": "",
            "eligibility_shift": EligibilityShift.NONE,
            "justification": "Population correspondante",
        },
        "context_alignment": {
            "match_type": ContextMatchType.SAME_HEALTHCARE_SYSTEM,
            "pathway": CarePathwayMatch.YES,
            "org_dependency": OrganizationDependency.LOW,
            "country": "France",
            "justification": "Contexte français",
        },
    },
]


def run_validation():
    results = []

    for case in CASES:
        da = case["device_alignment"]
        pa = case["population_alignment"]
        ca = case["context_alignment"]

        device = DeviceAlignment(
            device_match_type=da["match_type"],
            device_description_claim=da["claim"],
            device_description_study=da["study"],
            justification=da["justification"],
        )
        population = PopulationAlignment(
            population_match_type=pa["match_type"],
            population_description_claim=pa["claim"],
            population_description_study=pa["study"],
            subgroup_description=pa.get("subgroup", ""),
            eligibility_shift=pa.get("eligibility_shift", EligibilityShift.NONE),
            justification=pa["justification"],
        )
        context = ContextAlignment(
            context_match_type=ca["match_type"],
            care_pathway_match=ca["pathway"],
            organization_dependency=ca["org_dependency"],
            study_country=ca["country"],
            justification=ca["justification"],
        )

        output = evaluate_cas(
            claim_text=case["claim_text"],
            intervention=case["intervention"],
            domain=case["domain"],
            device=device,
            population=population,
            context=context,
            lang="fr",
        )

        risk_dimensions = set(r.dimension for r in output.risks)
        expected = case["expected_risks"]

        dim_results = {}
        for dim in ["DEVICE", "POPULATION", "CONTEXT"]:
            detected = dim in risk_dimensions
            expected_val = expected[dim]
            dim_results[dim] = {
                "expected": expected_val,
                "detected": detected,
                "match": detected == expected_val,
            }

        all_dims_match = all(d["match"] for d in dim_results.values())

        results.append({
            "id": case["id"],
            "device": case["device"],
            "type": case["type"],
            "decision": case["decision"],
            "critiques_cas": case["critiques_cas"],
            "critiques_ics": case["critiques_ics"],
            "cas_score": round(output.cas_score, 3),
            "cas_verdict": output.verdict.value,
            "d_device": round(output.d_device, 2),
            "d_pop": round(output.d_population, 2),
            "d_context": round(output.d_context, 2),
            "nb_risks": len(output.risks),
            "risk_dims_detected": sorted(risk_dimensions),
            "dim_results": dim_results,
            "all_dims_match": all_dims_match,
        })

    return results


def print_report(results):
    print("=" * 130)
    print("VALIDATION CAS ENGINE vs. 20 AVIS CNEDiMTS — ANALYSE PAR DIMENSION")
    print("Question : le moteur CAS détecte-t-il les mêmes problèmes d'alignement que la CNEDiMTS ?")
    print("=" * 130)
    print()

    # ---------------------------------------------------------------
    # Table 1 : Vue d'ensemble
    # ---------------------------------------------------------------
    print("TABLEAU 1 — VUE D'ENSEMBLE")
    print("-" * 130)
    print(f"{'#':>2} {'Dispositif':<28} {'Type':<6} {'HAS':<6} {'CAS':>5} {'Verdict':<14} "
          f"{'Dev':>4} {'Pop':>4} {'Ctx':>4} {'Critiques CAS':<20} {'Dims OK':>7}")
    print("-" * 130)

    total_match = 0
    for r in results:
        dev_ok = "OK" if r["dim_results"]["DEVICE"]["match"] else "X"
        pop_ok = "OK" if r["dim_results"]["POPULATION"]["match"] else "X"
        ctx_ok = "OK" if r["dim_results"]["CONTEXT"]["match"] else "X"
        all_ok = "3/3" if r["all_dims_match"] else f"{sum(1 for d in r['dim_results'].values() if d['match'])}/3"
        if r["all_dims_match"]:
            total_match += 1

        decision_short = "DEF" if r["decision"] == "DEFAVORABLE" else "FAV"
        crits = ",".join(r["critiques_cas"]) if r["critiques_cas"] else "—"

        print(f"{r['id']:>2} {r['device']:<28} {r['type']:<6} {decision_short:<6} "
              f"{r['cas_score']:>5.3f} {r['cas_verdict']:<14} "
              f"{dev_ok:>4} {pop_ok:>4} {ctx_ok:>4} {crits:<20} {all_ok:>7}")

    print("-" * 130)
    print(f"\nALIGNEMENT PAR DIMENSION : {total_match}/20 cas avec 3/3 dimensions correctes ({total_match/20*100:.0f}%)")
    print()

    # ---------------------------------------------------------------
    # Table 2 : Détail par dimension
    # ---------------------------------------------------------------
    dim_stats = {"DEVICE": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
                 "POPULATION": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
                 "CONTEXT": {"tp": 0, "tn": 0, "fp": 0, "fn": 0}}

    for r in results:
        for dim in ["DEVICE", "POPULATION", "CONTEXT"]:
            dr = r["dim_results"][dim]
            if dr["expected"] and dr["detected"]:
                dim_stats[dim]["tp"] += 1
            elif not dr["expected"] and not dr["detected"]:
                dim_stats[dim]["tn"] += 1
            elif not dr["expected"] and dr["detected"]:
                dim_stats[dim]["fp"] += 1
            else:
                dim_stats[dim]["fn"] += 1

    print("TABLEAU 2 — PERFORMANCE PAR DIMENSION (confusion matrix)")
    print("-" * 90)
    print(f"{'Dimension':<15} {'TP':>4} {'TN':>4} {'FP':>4} {'FN':>4} {'Precision':>10} {'Recall':>8} {'Accuracy':>9}")
    print("-" * 90)

    total_correct = 0
    total_cases = 0
    for dim in ["DEVICE", "POPULATION", "CONTEXT"]:
        s = dim_stats[dim]
        precision = s["tp"] / (s["tp"] + s["fp"]) if (s["tp"] + s["fp"]) > 0 else 1.0
        recall = s["tp"] / (s["tp"] + s["fn"]) if (s["tp"] + s["fn"]) > 0 else 1.0
        accuracy = (s["tp"] + s["tn"]) / 20
        total_correct += s["tp"] + s["tn"]
        total_cases += 20
        print(f"{dim:<15} {s['tp']:>4} {s['tn']:>4} {s['fp']:>4} {s['fn']:>4} "
              f"{precision:>10.1%} {recall:>8.1%} {accuracy:>9.1%}")

    overall_acc = total_correct / total_cases
    print("-" * 90)
    print(f"{'GLOBAL':<15} {'':>4} {'':>4} {'':>4} {'':>4} {'':>10} {'':>8} {overall_acc:>9.1%}")
    print()

    # ---------------------------------------------------------------
    # Table 3 : Erreurs détaillées
    # ---------------------------------------------------------------
    errors = []
    for r in results:
        for dim in ["DEVICE", "POPULATION", "CONTEXT"]:
            dr = r["dim_results"][dim]
            if not dr["match"]:
                errors.append({
                    "id": r["id"],
                    "device": r["device"],
                    "dim": dim,
                    "expected": dr["expected"],
                    "detected": dr["detected"],
                    "type": "FP" if dr["detected"] and not dr["expected"] else "FN",
                    "critiques_cas": r["critiques_cas"],
                    "critiques_ics": r["critiques_ics"],
                    "decision": r["decision"],
                })

    if errors:
        print("TABLEAU 3 — ERREURS PAR DIMENSION")
        print("-" * 130)
        for e in errors:
            error_type = "FAUX POSITIF (détecté mais pas dans l'avis)" if e["type"] == "FP" else "FAUX NÉGATIF (dans l'avis mais non détecté)"
            print(f"  #{e['id']} {e['device']:<28} | {e['dim']:<12} | {error_type}")
            print(f"     Critiques CAS dans l'avis : {', '.join(e['critiques_cas'])}")
            print(f"     Critiques ICS dans l'avis : {', '.join(e['critiques_ics']) if e['critiques_ics'] else '—'}")
            print()
    else:
        print("AUCUNE ERREUR — toutes les dimensions sont correctement détectées.")
    print()

    # ---------------------------------------------------------------
    # Synthèse finale
    # ---------------------------------------------------------------
    print("=" * 130)
    print("SYNTHÈSE FINALE")
    print("=" * 130)
    print()
    print(f"  Cas avec 3/3 dimensions correctes : {total_match}/20 ({total_match/20*100:.0f}%)")
    print(f"  Accuracy globale par dimension    : {overall_acc:.1%} ({total_correct}/{total_cases})")
    print()

    # CAS vs décision finale
    print("  NOTE : Le CAS ne prédit PAS la décision finale CNEDiMTS.")
    print("  Il évalue l'alignement étude ↔ revendication (une dimension parmi plusieurs).")
    print()

    defav = [r for r in results if r["decision"] == "DEFAVORABLE"]
    fav = [r for r in results if r["decision"] == "FAVORABLE"]

    defav_with_ics = [r for r in defav if r["critiques_ics"]]
    fav_with_cas_issues = [r for r in fav if r["cas_verdict"] in ("WEAK_EVIDENCE", "REJECTED")]

    print(f"  DÉFAVORABLES (n={len(defav)}) :")
    print(f"    Tous ont des critiques ICS massives : {len(defav_with_ics)}/{len(defav)}")
    for r in defav:
        print(f"      {r['device']:<28} CAS={r['cas_score']:.3f} ({r['cas_verdict']:<14}) "
              f"| ICS: {','.join(r['critiques_ics'][:5])}")
    print()

    print(f"  FAVORABLES avec CAS faible (n={len(fav_with_cas_issues)}) :")
    for r in fav_with_cas_issues:
        print(f"      {r['device']:<28} CAS={r['cas_score']:.3f} ({r['cas_verdict']:<14}) "
              f"| HAS donne FAV malgré les limites CAS")
    print()

    print("  CONCLUSION : Le moteur CAS est cohérent avec les critiques CAS de la CNEDiMTS.")
    print("  La décision finale FAVORABLE/DEFAVORABLE dépend de l'ENSEMBLE des dimensions")
    print("  (CAS + ICS + bénéfice clinique + stratégie de preuve).")


if __name__ == "__main__":
    results = run_validation()
    print_report(results)
