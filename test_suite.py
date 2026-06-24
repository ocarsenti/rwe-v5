"""Test suite — full workflow tests for the 4 mandatory clinical cases.

Each case tests every layer of the pipeline:
  L1. Claim parsing (epistemic level)
  L2. Endpoint classification (nature, causal role, per-endpoint flags)
  L3. Causal graph building (structure, structural issues)
  L4. Bias detection (flags, severities)
  L5. Design recommendation (primary design, alternatives)
  L6. Repair engine V1 (strategies, failure modes)
  L7. Repair engine V2 (5-step: diagnosis → repairs → chain → designs → ranking)
  L8. Regulatory labeling (issue type, endpoint status, conditions)
  L9. Gold dataset output (final status, HAS interpretation, dataset row, JSON)
"""

from __future__ import annotations

import json
import unittest

from models import (
    BiasFlag,
    BiasThreshold,
    CausalRole,
    CausalStructure,
    ClaimLevel,
    ClinicalClaim,
    DesignTypeRequired,
    Endpoint,
    EndpointNature,
    EndpointRank,
    EndpointRepairKind,
    EndpointStatus,
    FailureArchetype,
    FinalRegulatoryStatus,
    GoldDatasetRow,
    IssueType,
    RegulatoryStrength,
    RepairEndpointType,
    RepairType,
    StudyDesign,
)
from claim_parser import classify_claim, parse_claim
from endpoint_classifier import classify_endpoint, classify_endpoints
from causal_graph_builder import build_causal_structure, detect_structural_issues
from bias_detector import build_bias_detections
from design_engine import recommend_design
from repair_engine import generate_repair_plan, generate_repair_plan_v2
from engine import analyze, analyze_to_json, analyze_to_gold, analyze_to_gold_json, design, design_to_json
from regulatory_labeler import label_case, build_gold_dataset_rows
from gold_dataset import (
    process_all_cases,
    generate_gold_dataset,
    generate_gold_dataset_json,
)
from mode_detector import detect_mode
from design_mode import run_design_mode
from epistemic_core import (
    recommend_design as core_recommend_design,
    assess_identification,
    infer_target_dag,
    compute_endpoint_families,
    generate_design_space,
    compute_regulatory_manifold,
)
from models import (
    DAGEdge,
    DesignCandidate,
    DesignModeOutput,
    DesignSpace,
    EndpointFamily,
    EvidenceDesignType,
    IdentificationRequirements,
    ManifoldPoint,
    Mode,
    RegulatoryManifold,
    TargetDAG,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_claim(text, intervention, endpoints=None, domain=""):
    return ClinicalClaim(
        text=text,
        intervention=intervention,
        endpoints=endpoints or [],
        domain=domain,
    )


# ===================================================================
# CASE 1 — OdySight  (full workflow)
# ===================================================================

class TestOdySightFullWorkflow(unittest.TestCase):
    """OdySight: remote monitoring device — time-to-detection endpoint.

    Expected profile:
      - Circular primary endpoint → MEASUREMENT_CIRCULARITY
      - Detection bias + circularity
      - RCT blocked under current endpoints
      - Repair via independent clinical endpoints
      - Gold: INVALID_AS_PRIMARY_ENDPOINT_ONLY
    """

    @classmethod
    def setUpClass(cls):
        cls.claim = _make_claim(
            text="OdySight enables earlier detection of visual acuity degradation "
                 "through remote monitoring, reducing time-to-detection of macular "
                 "degeneration progression.",
            intervention="OdySight remote visual acuity monitoring device",
            endpoints=[
                Endpoint(
                    name="time-to-detection of progression",
                    nature=EndpointNature.INSTRUMENTED,
                    causal_role=CausalRole.CIRCULAR,
                    is_primary=True,
                    description="Time from baseline to device-detected visual acuity change",
                ),
            ],
            domain="ophthalmology",
        )
        cls.parsed = parse_claim(
            _make_claim(cls.claim.text, cls.claim.intervention,
                        cls.claim.endpoints[:], cls.claim.domain)
        )
        cls.ep_analyses = classify_endpoints(cls.parsed)
        cls.structure = build_causal_structure(cls.parsed, cls.ep_analyses)
        cls.bias_flags = detect_structural_issues(cls.parsed, cls.ep_analyses, cls.structure)
        cls.bias_detections = build_bias_detections(cls.bias_flags, cls.ep_analyses, cls.structure)
        cls.design = recommend_design(cls.parsed, cls.ep_analyses, cls.structure, cls.bias_flags)
        cls.repair_v1 = generate_repair_plan(
            cls.parsed, cls.ep_analyses, cls.structure,
            cls.bias_flags, cls.bias_detections, cls.design,
        )
        cls.repair_v2 = generate_repair_plan_v2(
            cls.parsed, cls.ep_analyses, cls.structure,
            cls.bias_flags, cls.bias_detections, cls.design,
        )
        cls.output = analyze(cls.claim)
        cls.gold = analyze_to_gold("CASE_ODYSIGHT", cls.claim)

    # --- L1: Claim parsing ---

    def test_L1_claim_level_process_or_chain(self):
        self.assertIn(self.parsed.level, [ClaimLevel.B, ClaimLevel.D])

    # --- L2: Endpoint classification ---

    def test_L2_endpoint_nature_instrumented(self):
        self.assertEqual(self.ep_analyses[0].nature, EndpointNature.INSTRUMENTED)

    def test_L2_endpoint_causal_role_circular(self):
        self.assertEqual(self.ep_analyses[0].causal_role, CausalRole.CIRCULAR)

    def test_L2_endpoint_flags_circularity(self):
        self.assertIn(BiasFlag.CIRCULARITY_RISK, self.ep_analyses[0].flags)

    def test_L2_endpoint_flags_detection_bias(self):
        self.assertIn(BiasFlag.DETECTION_BIAS, self.ep_analyses[0].flags)

    # --- L3: Causal graph ---

    def test_L3_structure_circular(self):
        self.assertEqual(self.structure, CausalStructure.CIRCULAR)

    def test_L3_structural_issues_contain_circularity(self):
        self.assertIn(BiasFlag.CIRCULARITY_RISK, self.bias_flags)

    def test_L3_structural_issues_contain_detection(self):
        self.assertIn(BiasFlag.DETECTION_BIAS, self.bias_flags)

    # --- L4: Bias detection ---

    def test_L4_bias_detections_circularity(self):
        flags = {bd.flag for bd in self.bias_detections}
        self.assertIn(BiasFlag.CIRCULARITY_RISK, flags)

    def test_L4_bias_severity_circularity_high(self):
        circ = [bd for bd in self.bias_detections if bd.flag == BiasFlag.CIRCULARITY_RISK]
        self.assertEqual(circ[0].severity, "HIGH")

    def test_L4_bias_detections_detection_high(self):
        det = [bd for bd in self.bias_detections if bd.flag == BiasFlag.DETECTION_BIAS]
        self.assertTrue(len(det) >= 1)
        self.assertEqual(det[0].severity, "HIGH")

    # --- L5: Design recommendation ---

    def test_L5_primary_design_blocked(self):
        self.assertEqual(self.design.primary_design, StudyDesign.NOT_IDENTIFIABLE)

    def test_L5_alternatives_include_before_after(self):
        alt = {a for a in self.design.alternatives}
        self.assertTrue(StudyDesign.BEFORE_AFTER in alt or StudyDesign.EXPLORATORY in alt)

    def test_L5_rationale_mentions_repair(self):
        self.assertTrue(len(self.design.rationale) > 20)

    # --- L6: Repair V1 ---

    def test_L6_repair_v1_exists(self):
        self.assertIsNotNone(self.repair_v1)

    def test_L6_repair_v1_endpoint_replacement(self):
        types = {s.type for s in self.repair_v1.repair_strategies}
        self.assertIn(RepairType.ENDPOINT_REPLACEMENT, types)

    def test_L6_repair_v1_precise_outcomes(self):
        descriptions = " ".join(s.description.lower() for s in self.repair_v1.repair_strategies)
        self.assertTrue(
            any(kw in descriptions for kw in [
                "complication rate", "hospitalization", "treatment escalation",
                "adjudicated", "independent", "administrative",
            ]),
        )

    def test_L6_repair_v1_failure_modes_not_empty(self):
        self.assertTrue(len(self.repair_v1.failure_modes) >= 1)

    # --- L7: Repair V2 (5-step) ---

    def test_L7_v2_exists(self):
        self.assertIsNotNone(self.repair_v2)

    def test_L7_v2_status_repairable(self):
        self.assertEqual(self.repair_v2.status, "REPAIRABLE")

    def test_L7_step1_failure_archetype_detection_loop(self):
        self.assertEqual(self.repair_v2.failure_diagnosis.failure_type, FailureArchetype.DETECTION_LOOP)

    def test_L7_step1_severity_gte_08(self):
        self.assertGreaterEqual(self.repair_v2.failure_diagnosis.severity, 0.8)

    def test_L7_step1_rct_false(self):
        self.assertEqual(self.repair_v2.failure_diagnosis.is_rct_valid, "false")

    def test_L7_step2_endpoint_repairs_exist(self):
        self.assertTrue(len(self.repair_v2.endpoint_repairs) >= 1)

    def test_L7_step2_at_least_3_alternatives(self):
        for block in self.repair_v2.endpoint_repairs:
            self.assertGreaterEqual(len(block.repairs), 3)

    def test_L7_step2_repairs_precise(self):
        for block in self.repair_v2.endpoint_repairs:
            for r in block.repairs:
                self.assertTrue(len(r.endpoint) > 20, f"Too vague: {r.endpoint}")
                self.assertTrue(len(r.why_valid) > 30)
                self.assertTrue(len(r.risk_reduction) >= 1)

    def test_L7_step2_failure_reason_causal(self):
        for block in self.repair_v2.endpoint_repairs:
            self.assertIn("circular", block.failure_reason.lower())
            self.assertIn("OdySight", block.failure_reason)

    def test_L7_step3_causal_chain_structure(self):
        roles = [s.role for s in self.repair_v2.causal_chain]
        self.assertIn("INTERVENTION", roles)
        self.assertIn("OUTCOME", roles)

    def test_L7_step3_intervention_node_odysight(self):
        self.assertIn("OdySight", self.repair_v2.causal_chain[0].node)

    def test_L7_step3_outcome_repaired(self):
        outcome = [s for s in self.repair_v2.causal_chain if s.role == "OUTCOME"][0]
        self.assertIn("REPAIRED", outcome.node)

    def test_L7_step4_no_standard_rct(self):
        designs = {d.design for d in self.repair_v2.recommended_designs}
        self.assertNotIn(StudyDesign.RCT, designs)

    def test_L7_step4_pragmatic_rct(self):
        designs = {d.design for d in self.repair_v2.recommended_designs}
        self.assertIn(StudyDesign.PRAGMATIC_RCT, designs)

    def test_L7_step4_justifications_complete(self):
        for d in self.repair_v2.recommended_designs:
            self.assertTrue(len(d.why_valid) > 20)
            self.assertTrue(len(d.failures_prevented) >= 1)

    def test_L7_step5_original_rejected(self):
        orig = [r for r in self.repair_v2.endpoint_ranking
                if r.endpoint == "time-to-detection of progression"]
        self.assertEqual(orig[0].rank, EndpointRank.REJECTED)
        self.assertGreaterEqual(orig[0].bias_score, 0.8)

    def test_L7_step5_gold_repaired_exist(self):
        gold = [r for r in self.repair_v2.endpoint_ranking if r.rank == EndpointRank.GOLD]
        self.assertTrue(len(gold) >= 1)

    def test_L7_step5_ranking_sorted(self):
        order = {EndpointRank.GOLD: 0, EndpointRank.ACCEPTABLE: 1, EndpointRank.REJECTED: 2}
        for i in range(len(self.repair_v2.endpoint_ranking) - 1):
            self.assertLessEqual(
                order[self.repair_v2.endpoint_ranking[i].rank],
                order[self.repair_v2.endpoint_ranking[i + 1].rank],
            )

    # --- L8: Regulatory labeling ---

    def test_L8_issue_type_measurement_circularity(self):
        self.assertEqual(self.gold.issue_detection.primary_issue_type, IssueType.MEASUREMENT_CIRCULARITY)

    def test_L8_severity_high(self):
        self.assertGreaterEqual(self.gold.issue_detection.severity_score, 0.8)

    def test_L8_endpoint_status_invalid_unless_redefined(self):
        self.assertEqual(
            self.gold.endpoint_analyses[0].original_endpoint.status,
            EndpointStatus.INVALID_UNLESS_REDEFINED,
        )

    def test_L8_failure_mode_causal_not_binary(self):
        fm = self.gold.endpoint_analyses[0].original_endpoint.failure_mode
        self.assertTrue("entangled" in fm.lower() or "circular" in fm.lower())
        self.assertNotIn("RCT invalid", fm)
        self.assertNotIn("study rejected", fm.lower())

    def test_L8_repair_endpoints_with_robustness(self):
        for r in self.gold.endpoint_analyses[0].repair_endpoints:
            self.assertGreater(r.robustness_score, 0.0)
            self.assertLessEqual(r.robustness_score, 1.0)
            self.assertIn(r.regulatory_strength, set(RegulatoryStrength))
            self.assertIn(r.type, set(RepairEndpointType))

    def test_L8_repair_has_primary_candidate(self):
        has_pc = any(
            r.regulatory_strength == RegulatoryStrength.PRIMARY_CANDIDATE
            for r in self.gold.endpoint_analyses[0].repair_endpoints
        )
        self.assertTrue(has_pc)

    def test_L8_conditions_require_adjudication_and_external(self):
        self.assertTrue(any(rc.independent_adjudication_required for rc in self.gold.regulatory_conditions))
        self.assertTrue(any(rc.external_data_source_required for rc in self.gold.regulatory_conditions))

    def test_L8_conditions_design_types_valid(self):
        for rc in self.gold.regulatory_conditions:
            self.assertIn(rc.design_type_required, set(DesignTypeRequired))
            self.assertIn(rc.acceptable_bias_threshold, set(BiasThreshold))

    # --- L9: Gold dataset output ---

    def test_L9_case_id(self):
        self.assertEqual(self.gold.case_id, "CASE_ODYSIGHT")

    def test_L9_device_context(self):
        self.assertIn("OdySight", self.gold.device_context.name)
        self.assertEqual(self.gold.device_context.domain, "ophthalmology")
        self.assertEqual(self.gold.device_context.intervention_type, "MONITORING_DEVICE")

    def test_L9_causal_graph_summary(self):
        self.assertIn("OdySight", self.gold.causal_graph.summary)
        self.assertGreaterEqual(len(self.gold.causal_graph.measurement_influence_paths), 1)

    def test_L9_has_interpretation_realistic(self):
        self.assertGreater(len(self.gold.has_interpretation), 80)
        self.assertIn("time-to-detection", self.gold.has_interpretation)
        self.assertNotIn("rct invalid", self.gold.has_interpretation.lower())

    def test_L9_final_status_endpoint_level(self):
        self.assertEqual(
            self.gold.final_regulatory_status,
            FinalRegulatoryStatus.INVALID_AS_PRIMARY_ENDPOINT_ONLY,
        )

    def test_L9_json_complete(self):
        result = json.loads(analyze_to_gold_json("CASE_ODYSIGHT", self.claim))
        for key in ["case_id", "device_context", "causal_graph", "issue_detection",
                     "endpoint_analyses", "regulatory_conditions",
                     "has_interpretation", "final_regulatory_status"]:
            self.assertIn(key, result)

    def test_L9_engine_json_complete(self):
        result = json.loads(analyze_to_json(self.claim))
        for key in ["claim_level", "endpoint_analysis", "causal_structure",
                     "bias_flags", "design_recommendation", "repair_engine",
                     "regulatory_readout"]:
            self.assertIn(key, result)
        repair = result["repair_engine"]
        for key in ["status", "failure_diagnosis", "endpoint_repairs",
                     "causal_chain", "recommended_designs", "endpoint_ranking"]:
            self.assertIn(key, repair)


# ===================================================================
# CASE 2 — Moovcare  (full workflow)
# ===================================================================

class TestMoovcareFullWorkflow(unittest.TestCase):
    """Moovcare: web-based symptom monitoring → alert → survival.

    Expected profile:
      - Mediated structure, objective endpoints
      - No circularity, care pathway bias (mediation gap)
      - Low severity, RCT conditional
      - Minimal repair needed (mediator specification)
      - Gold: ACCEPTABLE_PRIMARY_WITH_CONDITIONS
    """

    @classmethod
    def setUpClass(cls):
        cls.claim = _make_claim(
            text="Moovcare improves overall survival in lung cancer patients "
                 "through web-based symptom monitoring and early alert to physicians.",
            intervention="Moovcare web-based symptom monitoring application",
            endpoints=[
                Endpoint(
                    name="overall survival",
                    nature=EndpointNature.OBJECTIVE,
                    causal_role=CausalRole.MEDIATED,
                    is_primary=True,
                    description="Time from randomization to death from any cause",
                ),
                Endpoint(
                    name="time-to-treatment modification",
                    nature=EndpointNature.OBJECTIVE,
                    causal_role=CausalRole.MEDIATED,
                    is_primary=False,
                    description="Time from symptom alert to treatment change",
                ),
            ],
            domain="oncology",
        )
        cls.parsed = parse_claim(
            _make_claim(cls.claim.text, cls.claim.intervention,
                        cls.claim.endpoints[:], cls.claim.domain)
        )
        cls.ep_analyses = classify_endpoints(cls.parsed)
        cls.structure = build_causal_structure(cls.parsed, cls.ep_analyses)
        cls.bias_flags = detect_structural_issues(cls.parsed, cls.ep_analyses, cls.structure)
        cls.bias_detections = build_bias_detections(cls.bias_flags, cls.ep_analyses, cls.structure)
        cls.design = recommend_design(cls.parsed, cls.ep_analyses, cls.structure, cls.bias_flags)
        cls.repair_v1 = generate_repair_plan(
            cls.parsed, cls.ep_analyses, cls.structure,
            cls.bias_flags, cls.bias_detections, cls.design,
        )
        cls.repair_v2 = generate_repair_plan_v2(
            cls.parsed, cls.ep_analyses, cls.structure,
            cls.bias_flags, cls.bias_detections, cls.design,
        )
        cls.output = analyze(cls.claim)
        cls.gold = analyze_to_gold("CASE_MOOVCARE", cls.claim)

    # --- L1: Claim parsing ---

    def test_L1_claim_level_outcome_or_chain(self):
        self.assertIn(self.parsed.level, [ClaimLevel.C, ClaimLevel.D])

    # --- L2: Endpoint classification ---

    def test_L2_survival_nature_objective(self):
        os_ep = [ea for ea in self.ep_analyses if ea.endpoint.name == "overall survival"]
        self.assertEqual(os_ep[0].nature, EndpointNature.OBJECTIVE)

    def test_L2_survival_causal_role_mediated(self):
        os_ep = [ea for ea in self.ep_analyses if ea.endpoint.name == "overall survival"]
        self.assertEqual(os_ep[0].causal_role, CausalRole.MEDIATED)

    def test_L2_no_circularity_flag(self):
        for ea in self.ep_analyses:
            self.assertNotIn(BiasFlag.CIRCULARITY_RISK, ea.flags)

    def test_L2_secondary_endpoint_classified(self):
        ttm = [ea for ea in self.ep_analyses if ea.endpoint.name == "time-to-treatment modification"]
        self.assertEqual(len(ttm), 1)
        self.assertIn(ttm[0].nature, [EndpointNature.OBJECTIVE, EndpointNature.INSTRUMENTED])

    # --- L3: Causal graph ---

    def test_L3_structure_mediated(self):
        self.assertEqual(self.structure, CausalStructure.MEDIATED)

    def test_L3_no_circularity_flag(self):
        self.assertNotIn(BiasFlag.CIRCULARITY_RISK, self.bias_flags)

    # --- L4: Bias detection ---

    def test_L4_no_circularity_detection(self):
        flags = {bd.flag for bd in self.bias_detections}
        self.assertNotIn(BiasFlag.CIRCULARITY_RISK, flags)

    def test_L4_no_perception_bias(self):
        flags = {bd.flag for bd in self.bias_detections}
        self.assertNotIn(BiasFlag.PERCEPTION_BIAS, flags)

    # --- L5: Design recommendation ---

    def test_L5_rct_or_cohort_valid(self):
        self.assertIn(self.design.primary_design, [StudyDesign.RCT, StudyDesign.COHORT])

    def test_L5_rationale_present(self):
        self.assertTrue(len(self.design.rationale) > 10)

    # --- L6: Repair V1 ---

    def test_L6_repair_minimal(self):
        if self.repair_v1:
            self.assertLessEqual(len(self.repair_v1.repair_strategies), 3)

    # --- L7: Repair V2 ---

    def test_L7_v2_repairable_if_exists(self):
        if self.repair_v2:
            self.assertEqual(self.repair_v2.status, "REPAIRABLE")

    def test_L7_rct_valid_or_conditional(self):
        if self.repair_v2:
            self.assertIn(self.repair_v2.failure_diagnosis.is_rct_valid, ["true", "conditional"])

    def test_L7_severity_low(self):
        if self.repair_v2:
            self.assertLessEqual(self.repair_v2.failure_diagnosis.severity, 0.6)

    def test_L7_survival_not_rejected(self):
        if self.repair_v2:
            for r in self.repair_v2.endpoint_ranking:
                if r.endpoint == "overall survival":
                    self.assertNotEqual(r.rank, EndpointRank.REJECTED)

    def test_L7_causal_chain_has_mediator(self):
        if self.repair_v2:
            roles = [s.role for s in self.repair_v2.causal_chain]
            self.assertIn("MEDIATOR", roles)

    # --- L8: Regulatory labeling ---

    def test_L8_issue_type_care_pathway(self):
        self.assertEqual(self.gold.issue_detection.primary_issue_type, IssueType.CARE_PATHWAY_BIAS)

    def test_L8_severity_lte_06(self):
        self.assertLessEqual(self.gold.issue_detection.severity_score, 0.6)

    def test_L8_survival_status_acceptable(self):
        os_gold = [ea for ea in self.gold.endpoint_analyses
                   if ea.original_endpoint.name == "overall survival"]
        self.assertIn(os_gold[0].original_endpoint.status,
                      [EndpointStatus.ACCEPTABLE, EndpointStatus.ACCEPTABLE_WITH_CONDITIONS])

    def test_L8_no_invalid_unless_redefined(self):
        for ea in self.gold.endpoint_analyses:
            self.assertNotEqual(ea.original_endpoint.status, EndpointStatus.INVALID_UNLESS_REDEFINED)

    def test_L8_failure_mode_no_binary_rejection(self):
        for ea in self.gold.endpoint_analyses:
            self.assertNotIn("RCT invalid", ea.original_endpoint.failure_mode)

    # --- L9: Gold dataset output ---

    def test_L9_case_id(self):
        self.assertEqual(self.gold.case_id, "CASE_MOOVCARE")

    def test_L9_device_context(self):
        self.assertEqual(self.gold.device_context.domain, "oncology")
        self.assertEqual(self.gold.device_context.intervention_type, "MONITORING_DEVICE")

    def test_L9_causal_graph_mediators(self):
        self.assertGreaterEqual(len(self.gold.causal_graph.mediators), 1)

    def test_L9_has_interpretation_not_rejection(self):
        interp = self.gold.has_interpretation.lower()
        self.assertNotIn("rct invalid", interp)
        self.assertNotIn("rejet", interp)
        self.assertGreater(len(self.gold.has_interpretation), 80)

    def test_L9_final_status_acceptable(self):
        self.assertIn(self.gold.final_regulatory_status, [
            FinalRegulatoryStatus.ACCEPTABLE_PRIMARY_WITH_CONDITIONS,
            FinalRegulatoryStatus.ACCEPTABLE_WITH_REDESIGN,
        ])

    def test_L9_conditions_exist(self):
        self.assertGreaterEqual(len(self.gold.regulatory_conditions), 1)

    def test_L9_json_complete(self):
        result = json.loads(analyze_to_gold_json("CASE_MOOVCARE", self.claim))
        self.assertEqual(result["final_regulatory_status"], self.gold.final_regulatory_status.value)


# ===================================================================
# CASE 3 — Remedee  (full workflow)
# ===================================================================

class TestRemedeeFullWorkflow(unittest.TestCase):
    """Remedee: neurostimulation wristband → endorphins → pain reduction.

    Expected profile:
      - All subjective endpoints → SUBJECTIVE_ENDPOINT_BIAS
      - Mediation gap (mechanism → outcome without measured intermediary)
      - Sham RCT required
      - Repair: objective anchors (analgesic consumption, walk test, biomarkers)
      - Gold: ACCEPTABLE_WITH_REDESIGN
    """

    @classmethod
    def setUpClass(cls):
        cls.claim = _make_claim(
            text="Remedee wristband uses millimeter-wave neurostimulation to trigger "
                 "endorphin release, reducing chronic pain.",
            intervention="Remedee millimeter-wave neurostimulation wristband",
            endpoints=[
                Endpoint(
                    name="pain VAS score",
                    nature=EndpointNature.SUBJECTIVE,
                    causal_role=CausalRole.INDEPENDENT,
                    is_primary=True,
                    description="Visual analog scale for pain intensity",
                ),
                Endpoint(
                    name="patient quality of life",
                    nature=EndpointNature.SUBJECTIVE,
                    causal_role=CausalRole.INDEPENDENT,
                    is_primary=False,
                    description="SF-36 quality of life questionnaire",
                ),
            ],
            domain="pain management",
        )
        cls.parsed = parse_claim(
            _make_claim(cls.claim.text, cls.claim.intervention,
                        cls.claim.endpoints[:], cls.claim.domain)
        )
        cls.ep_analyses = classify_endpoints(cls.parsed)
        cls.structure = build_causal_structure(cls.parsed, cls.ep_analyses)
        cls.bias_flags = detect_structural_issues(cls.parsed, cls.ep_analyses, cls.structure)
        cls.bias_detections = build_bias_detections(cls.bias_flags, cls.ep_analyses, cls.structure)
        cls.design = recommend_design(cls.parsed, cls.ep_analyses, cls.structure, cls.bias_flags)
        cls.repair_v1 = generate_repair_plan(
            cls.parsed, cls.ep_analyses, cls.structure,
            cls.bias_flags, cls.bias_detections, cls.design,
        )
        cls.repair_v2 = generate_repair_plan_v2(
            cls.parsed, cls.ep_analyses, cls.structure,
            cls.bias_flags, cls.bias_detections, cls.design,
        )
        cls.output = analyze(cls.claim)
        cls.gold = analyze_to_gold("CASE_REMEDEE", cls.claim)

    # --- L1: Claim parsing ---

    def test_L1_claim_level_mechanism_or_chain(self):
        self.assertIn(self.parsed.level, [ClaimLevel.A, ClaimLevel.D])

    # --- L2: Endpoint classification ---

    def test_L2_pain_nature_subjective(self):
        pain = [ea for ea in self.ep_analyses if ea.endpoint.name == "pain VAS score"]
        self.assertEqual(pain[0].nature, EndpointNature.SUBJECTIVE)

    def test_L2_qol_nature_subjective(self):
        qol = [ea for ea in self.ep_analyses if ea.endpoint.name == "patient quality of life"]
        self.assertEqual(qol[0].nature, EndpointNature.SUBJECTIVE)

    def test_L2_no_circularity_on_subjective(self):
        for ea in self.ep_analyses:
            self.assertNotEqual(ea.causal_role, CausalRole.CIRCULAR)

    # --- L3: Causal graph ---

    def test_L3_structure_mediated(self):
        self.assertIn(self.structure, [CausalStructure.MEDIATED, CausalStructure.DIRECT])

    # --- L4: Bias detection ---

    def test_L4_perception_bias_detected(self):
        flags = {bd.flag for bd in self.bias_detections}
        self.assertIn(BiasFlag.PERCEPTION_BIAS, flags)

    def test_L4_mediation_gap_detected(self):
        self.assertIn(BiasFlag.MEDIATION_GAP, self.bias_flags)

    def test_L4_perception_severity_medium(self):
        perc = [bd for bd in self.bias_detections if bd.flag == BiasFlag.PERCEPTION_BIAS]
        self.assertEqual(perc[0].severity, "MEDIUM")

    # --- L5: Design recommendation ---

    def test_L5_sham_rct_recommended(self):
        self.assertIn(self.design.primary_design, [StudyDesign.SHAM_RCT, StudyDesign.RCT])

    # --- L6: Repair V1 ---

    def test_L6_repair_v1_exists(self):
        self.assertIsNotNone(self.repair_v1)

    def test_L6_repair_v1_design_change(self):
        types = {s.type for s in self.repair_v1.repair_strategies}
        self.assertIn(RepairType.DESIGN_CHANGE, types)

    def test_L6_repair_v1_objective_proxy(self):
        descriptions = " ".join(s.description.lower() for s in self.repair_v1.repair_strategies)
        self.assertTrue(any(kw in descriptions for kw in [
            "analgesic", "morphine", "walk test", "actigraphy",
            "return-to-work", "functional", "hospitalization",
        ]))

    def test_L6_repair_v1_sham_mentioned(self):
        descriptions = " ".join(s.description.lower() for s in self.repair_v1.repair_strategies)
        self.assertTrue("sham" in descriptions or "double-blind" in descriptions)

    # --- L7: Repair V2 ---

    def test_L7_v2_exists(self):
        self.assertIsNotNone(self.repair_v2)

    def test_L7_step1_failure_subjective(self):
        self.assertEqual(self.repair_v2.failure_diagnosis.failure_type, FailureArchetype.SUBJECTIVE_ENDPOINT)

    def test_L7_step1_rct_conditional(self):
        self.assertEqual(self.repair_v2.failure_diagnosis.is_rct_valid, "conditional")

    def test_L7_step2_pain_repair_analgesic(self):
        pain_blocks = [b for b in self.repair_v2.endpoint_repairs if "pain" in b.original_endpoint.lower()]
        all_repairs = " ".join(r.endpoint.lower() for b in pain_blocks for r in b.repairs)
        self.assertIn("analgesic", all_repairs)

    def test_L7_step2_pain_repair_functional(self):
        pain_blocks = [b for b in self.repair_v2.endpoint_repairs if "pain" in b.original_endpoint.lower()]
        all_repairs = " ".join(r.endpoint.lower() for b in pain_blocks for r in b.repairs)
        self.assertTrue(any(kw in all_repairs for kw in ["walk test", "functional", "actigraphy", "return-to-work"]))

    def test_L7_step2_qol_repair_hospitalization(self):
        qol_blocks = [b for b in self.repair_v2.endpoint_repairs if "quality" in b.original_endpoint.lower()]
        self.assertTrue(len(qol_blocks) >= 1)
        all_repairs = " ".join(r.endpoint.lower() for b in qol_blocks for r in b.repairs)
        self.assertIn("hospitalization", all_repairs)

    def test_L7_step3_causal_chain_mediator(self):
        roles = [s.role for s in self.repair_v2.causal_chain]
        self.assertIn("MEDIATOR", roles)

    def test_L7_step3_mediator_endorphin(self):
        mediators = [s for s in self.repair_v2.causal_chain if s.role == "MEDIATOR"]
        mediator_text = " ".join(m.node.lower() for m in mediators)
        self.assertTrue("endorphin" in mediator_text or "sensory" in mediator_text)

    def test_L7_step4_sham_rct_in_designs(self):
        designs = {d.design for d in self.repair_v2.recommended_designs}
        self.assertIn(StudyDesign.SHAM_RCT, designs)

    def test_L7_step5_pain_rejected(self):
        pain_ranked = [r for r in self.repair_v2.endpoint_ranking if r.endpoint == "pain VAS score"]
        self.assertEqual(pain_ranked[0].rank, EndpointRank.REJECTED)

    def test_L7_step5_gold_repaired_exist(self):
        gold = [r for r in self.repair_v2.endpoint_ranking if r.rank == EndpointRank.GOLD]
        self.assertTrue(len(gold) >= 1)

    # --- L8: Regulatory labeling ---

    def test_L8_issue_type_subjective(self):
        self.assertEqual(self.gold.issue_detection.primary_issue_type, IssueType.SUBJECTIVE_ENDPOINT_BIAS)

    def test_L8_both_endpoints_conditional(self):
        for ea in self.gold.endpoint_analyses:
            self.assertEqual(ea.original_endpoint.status, EndpointStatus.ACCEPTABLE_WITH_CONDITIONS)

    def test_L8_failure_mode_blinding(self):
        fm = self.gold.endpoint_analyses[0].original_endpoint.failure_mode.lower()
        self.assertTrue("blinding" in fm or "sham" in fm or "placebo" in fm)

    def test_L8_repair_has_objective_types(self):
        types = {r.type for ea in self.gold.endpoint_analyses for r in ea.repair_endpoints}
        self.assertTrue(types & {RepairEndpointType.BIOMARKER, RepairEndpointType.HARD_CLINICAL, RepairEndpointType.UTILIZATION})

    def test_L8_conditions_require_blinding(self):
        self.assertTrue(any(rc.blinding_required for rc in self.gold.regulatory_conditions))

    def test_L8_no_binary_judgment(self):
        for ea in self.gold.endpoint_analyses:
            self.assertNotIn("RCT invalid", ea.original_endpoint.failure_mode)

    # --- L9: Gold dataset output ---

    def test_L9_device_context(self):
        self.assertEqual(self.gold.device_context.domain, "pain management")
        self.assertEqual(self.gold.device_context.intervention_type, "THERAPEUTIC_DEVICE")

    def test_L9_has_interpretation_aveugle(self):
        self.assertIn("aveugle", self.gold.has_interpretation.lower())
        self.assertGreater(len(self.gold.has_interpretation), 80)

    def test_L9_final_status_redesign(self):
        self.assertIn(self.gold.final_regulatory_status, [
            FinalRegulatoryStatus.ACCEPTABLE_WITH_REDESIGN,
            FinalRegulatoryStatus.ACCEPTABLE_SECONDARY_ONLY,
        ])

    def test_L9_causal_graph_mediator_endorphin(self):
        mediator_text = " ".join(self.gold.causal_graph.mediators).lower()
        self.assertIn("endorphin", mediator_text)

    def test_L9_json_complete(self):
        result = json.loads(analyze_to_gold_json("CASE_REMEDEE", self.claim))
        self.assertEqual(result["issue_detection"]["primary_issue_type"], "SUBJECTIVE_ENDPOINT_BIAS")


# ===================================================================
# CASE 4 — AI Triage AVC  (full workflow)
# ===================================================================

class TestAITriageFullWorkflow(unittest.TestCase):
    """AI Triage: AI CT scan triage → time-to-treatment for stroke.

    Expected profile:
      - Circular primary (AI-triggered measurement)
      - Detection acceleration (triage = detection, not treatment)
      - Repair: mortality, mRS, ICU LOS
      - Gold: INVALID_AS_PRIMARY_ENDPOINT_ONLY
    """

    @classmethod
    def setUpClass(cls):
        cls.claim = _make_claim(
            text="AI triage system reduces time-to-treatment for stroke patients "
                 "by automated detection and prioritization of brain CT scans.",
            intervention="AI-powered CT scan triage and prioritization system",
            endpoints=[
                Endpoint(
                    name="time-to-treatment",
                    nature=EndpointNature.INSTRUMENTED,
                    causal_role=CausalRole.CIRCULAR,
                    is_primary=True,
                    description="Time from scan acquisition to treatment initiation, "
                                "triggered by AI alert",
                ),
            ],
            domain="emergency neurology",
        )
        cls.parsed = parse_claim(
            _make_claim(cls.claim.text, cls.claim.intervention,
                        cls.claim.endpoints[:], cls.claim.domain)
        )
        cls.ep_analyses = classify_endpoints(cls.parsed)
        cls.structure = build_causal_structure(cls.parsed, cls.ep_analyses)
        cls.bias_flags = detect_structural_issues(cls.parsed, cls.ep_analyses, cls.structure)
        cls.bias_detections = build_bias_detections(cls.bias_flags, cls.ep_analyses, cls.structure)
        cls.design = recommend_design(cls.parsed, cls.ep_analyses, cls.structure, cls.bias_flags)
        cls.repair_v1 = generate_repair_plan(
            cls.parsed, cls.ep_analyses, cls.structure,
            cls.bias_flags, cls.bias_detections, cls.design,
        )
        cls.repair_v2 = generate_repair_plan_v2(
            cls.parsed, cls.ep_analyses, cls.structure,
            cls.bias_flags, cls.bias_detections, cls.design,
        )
        cls.output = analyze(cls.claim)
        cls.gold = analyze_to_gold("CASE_AI_TRIAGE_AVC", cls.claim)

    # --- L1: Claim parsing ---

    def test_L1_claim_level_process_or_chain(self):
        self.assertIn(self.parsed.level, [ClaimLevel.B, ClaimLevel.D])

    # --- L2: Endpoint classification ---

    def test_L2_endpoint_nature_instrumented(self):
        self.assertEqual(self.ep_analyses[0].nature, EndpointNature.INSTRUMENTED)

    def test_L2_endpoint_causal_role_circular(self):
        self.assertEqual(self.ep_analyses[0].causal_role, CausalRole.CIRCULAR)

    def test_L2_detection_bias_flag(self):
        self.assertIn(BiasFlag.DETECTION_BIAS, self.ep_analyses[0].flags)

    def test_L2_circularity_flag(self):
        self.assertIn(BiasFlag.CIRCULARITY_RISK, self.ep_analyses[0].flags)

    # --- L3: Causal graph ---

    def test_L3_structure_circular(self):
        self.assertEqual(self.structure, CausalStructure.CIRCULAR)

    def test_L3_both_bias_flags(self):
        self.assertIn(BiasFlag.CIRCULARITY_RISK, self.bias_flags)
        self.assertIn(BiasFlag.DETECTION_BIAS, self.bias_flags)

    # --- L4: Bias detection ---

    def test_L4_circularity_high(self):
        circ = [bd for bd in self.bias_detections if bd.flag == BiasFlag.CIRCULARITY_RISK]
        self.assertEqual(circ[0].severity, "HIGH")

    def test_L4_detection_bias_high(self):
        det = [bd for bd in self.bias_detections if bd.flag == BiasFlag.DETECTION_BIAS]
        self.assertEqual(det[0].severity, "HIGH")

    # --- L5: Design recommendation ---

    def test_L5_design_blocked(self):
        self.assertIn(self.design.primary_design, [StudyDesign.NOT_IDENTIFIABLE, StudyDesign.COHORT])

    # --- L6: Repair V1 ---

    def test_L6_repair_exists(self):
        self.assertIsNotNone(self.repair_v1)

    def test_L6_repair_precise_survival(self):
        descriptions = " ".join(s.description.lower() for s in self.repair_v1.repair_strategies)
        self.assertTrue(any(kw in descriptions for kw in [
            "mortality", "rankin", "survival", "icu", "discharge",
            "complication rate", "adjudicated",
        ]))

    # --- L7: Repair V2 ---

    def test_L7_v2_exists(self):
        self.assertIsNotNone(self.repair_v2)

    def test_L7_step1_failure_detection_loop(self):
        self.assertEqual(self.repair_v2.failure_diagnosis.failure_type, FailureArchetype.DETECTION_LOOP)

    def test_L7_step1_severity_high(self):
        self.assertGreaterEqual(self.repair_v2.failure_diagnosis.severity, 0.8)

    def test_L7_step1_rct_false(self):
        self.assertEqual(self.repair_v2.failure_diagnosis.is_rct_valid, "false")

    def test_L7_step2_repair_has_mortality(self):
        all_repairs = " ".join(r.endpoint.lower() for b in self.repair_v2.endpoint_repairs for r in b.repairs)
        self.assertIn("mortality", all_repairs)

    def test_L7_step2_repair_has_rankin_or_functional(self):
        all_repairs = " ".join(r.endpoint.lower() for b in self.repair_v2.endpoint_repairs for r in b.repairs)
        self.assertTrue("rankin" in all_repairs or "functional" in all_repairs)

    def test_L7_step2_repair_has_utilization(self):
        all_repairs = " ".join(r.endpoint.lower() for b in self.repair_v2.endpoint_repairs for r in b.repairs)
        self.assertTrue("icu" in all_repairs or "hospital" in all_repairs or "administrative" in all_repairs)

    def test_L7_step2_at_least_3_alternatives(self):
        for block in self.repair_v2.endpoint_repairs:
            self.assertGreaterEqual(len(block.repairs), 3)

    def test_L7_step3_causal_chain_intervention_outcome(self):
        roles = [s.role for s in self.repair_v2.causal_chain]
        self.assertIn("INTERVENTION", roles)
        self.assertIn("OUTCOME", roles)

    def test_L7_step4_pragmatic_rct(self):
        designs = {d.design for d in self.repair_v2.recommended_designs}
        self.assertIn(StudyDesign.PRAGMATIC_RCT, designs)

    def test_L7_step4_no_standard_rct(self):
        designs = {d.design for d in self.repair_v2.recommended_designs}
        self.assertNotIn(StudyDesign.RCT, designs)

    def test_L7_step5_original_rejected(self):
        orig = [r for r in self.repair_v2.endpoint_ranking if r.endpoint == "time-to-treatment"]
        self.assertEqual(orig[0].rank, EndpointRank.REJECTED)

    def test_L7_step5_gold_repaired_exist(self):
        gold = [r for r in self.repair_v2.endpoint_ranking if r.rank == EndpointRank.GOLD]
        self.assertTrue(len(gold) >= 1)

    # --- L8: Regulatory labeling ---

    def test_L8_issue_type_detection_acceleration(self):
        self.assertEqual(self.gold.issue_detection.primary_issue_type, IssueType.DETECTION_ACCELERATION)

    def test_L8_severity_high(self):
        self.assertGreaterEqual(self.gold.issue_detection.severity_score, 0.8)

    def test_L8_endpoint_invalid_unless_redefined(self):
        self.assertEqual(
            self.gold.endpoint_analyses[0].original_endpoint.status,
            EndpointStatus.INVALID_UNLESS_REDEFINED,
        )

    def test_L8_repair_has_survival_type(self):
        types = {r.type for r in self.gold.endpoint_analyses[0].repair_endpoints}
        self.assertIn(RepairEndpointType.SURVIVAL, types)

    def test_L8_repair_has_hard_clinical_type(self):
        types = {r.type for r in self.gold.endpoint_analyses[0].repair_endpoints}
        self.assertIn(RepairEndpointType.HARD_CLINICAL, types)

    def test_L8_conditions_pragmatic_or_registry(self):
        designs = {rc.design_type_required for rc in self.gold.regulatory_conditions}
        self.assertTrue(DesignTypeRequired.PRAGMATIC_RCT in designs or DesignTypeRequired.REGISTRY_RCT in designs)

    def test_L8_conditions_require_adjudication(self):
        self.assertTrue(any(rc.independent_adjudication_required for rc in self.gold.regulatory_conditions))

    def test_L8_failure_mode_causal(self):
        fm = self.gold.endpoint_analyses[0].original_endpoint.failure_mode.lower()
        self.assertTrue("entangled" in fm or "circular" in fm or "detection" in fm)
        self.assertNotIn("rct invalid", fm)

    # --- L9: Gold dataset output ---

    def test_L9_case_id(self):
        self.assertEqual(self.gold.case_id, "CASE_AI_TRIAGE_AVC")

    def test_L9_device_context(self):
        self.assertEqual(self.gold.device_context.domain, "emergency neurology")
        self.assertEqual(self.gold.device_context.intervention_type, "TRIAGE_SYSTEM")

    def test_L9_has_interpretation_detection(self):
        interp = self.gold.has_interpretation.lower()
        self.assertIn("time-to-treatment", interp)
        self.assertNotIn("rct invalid", interp)
        self.assertGreater(len(self.gold.has_interpretation), 80)

    def test_L9_final_status_endpoint_level(self):
        self.assertEqual(
            self.gold.final_regulatory_status,
            FinalRegulatoryStatus.INVALID_AS_PRIMARY_ENDPOINT_ONLY,
        )

    def test_L9_json_complete(self):
        result = json.loads(analyze_to_gold_json("CASE_AI_TRIAGE_AVC", self.claim))
        self.assertEqual(result["issue_detection"]["primary_issue_type"], "DETECTION_ACCELERATION")
        self.assertEqual(result["final_regulatory_status"], "INVALID_AS_PRIMARY_ENDPOINT_ONLY")


# ===================================================================
# GOLD DATASET TABLE — cross-case consistency
# ===================================================================

class TestGoldDatasetCrossCase(unittest.TestCase):
    """Cross-case consistency: severity ordering, taxonomy coherence, no binary verdicts."""

    @classmethod
    def setUpClass(cls):
        cls.cases = process_all_cases()
        cls.rows = generate_gold_dataset()

    def test_four_cases_processed(self):
        self.assertEqual(len(self.cases), 4)

    def test_all_case_ids(self):
        self.assertEqual(
            {c.case_id for c in self.cases},
            {"CASE_ODYSIGHT", "CASE_MOOVCARE", "CASE_REMEDEE", "CASE_AI_TRIAGE_AVC"},
        )

    def test_dataset_rows_gte_4(self):
        self.assertGreaterEqual(len(self.rows), 4)

    def test_severity_ordering(self):
        sev = {c.case_id: c.issue_detection.severity_score for c in self.cases}
        self.assertGreater(sev["CASE_ODYSIGHT"], sev["CASE_MOOVCARE"])
        self.assertGreater(sev["CASE_AI_TRIAGE_AVC"], sev["CASE_MOOVCARE"])
        self.assertGreater(sev["CASE_REMEDEE"], sev["CASE_MOOVCARE"])

    def test_no_binary_rct_rejection_anywhere(self):
        for case in self.cases:
            for ea in case.endpoint_analyses:
                self.assertNotIn("RCT invalid", ea.original_endpoint.failure_mode)
                self.assertNotIn("study rejected", ea.original_endpoint.failure_mode.lower())
                self.assertNotIn("trial invalid", ea.original_endpoint.failure_mode.lower())

    def test_no_global_study_rejection(self):
        for case in self.cases:
            self.assertNotEqual(
                case.final_regulatory_status,
                FinalRegulatoryStatus.REJECTED_UNLESS_EXTERNAL_VALIDATION,
            )

    def test_all_have_conditional_pathways(self):
        for case in self.cases:
            self.assertGreaterEqual(len(case.regulatory_conditions), 1)

    def test_endpoints_separated_from_trial(self):
        for case in self.cases:
            for ea in case.endpoint_analyses:
                fm = ea.original_endpoint.failure_mode.lower()
                self.assertNotIn("trial invalid", fm)
                self.assertNotIn("study invalid", fm)

    def test_repair_endpoints_actionable_for_invalid(self):
        for case in self.cases:
            for ea in case.endpoint_analyses:
                if ea.original_endpoint.status in (
                    EndpointStatus.INVALID_UNLESS_REDEFINED,
                    EndpointStatus.INVALID_AS_PRIMARY_ONLY,
                ):
                    self.assertGreaterEqual(len(ea.repair_endpoints), 1)

    def test_high_severity_cases_have_repairs(self):
        for case in self.cases:
            if case.issue_detection.severity_score > 0.5:
                total = sum(len(ea.repair_endpoints) for ea in case.endpoint_analyses)
                self.assertGreater(total, 0)

    def test_has_interpretation_realistic_length(self):
        for case in self.cases:
            self.assertGreater(len(case.has_interpretation), 80)

    def test_failure_modes_endpoint_specific(self):
        for case in self.cases:
            for ea in case.endpoint_analyses:
                if ea.original_endpoint.status != EndpointStatus.ACCEPTABLE:
                    self.assertIn(ea.original_endpoint.name.lower(),
                                  ea.original_endpoint.failure_mode.lower())

    def test_rows_all_fields_valid(self):
        for row in self.rows:
            self.assertTrue(row.device)
            self.assertTrue(row.original_endpoint)
            self.assertTrue(row.failure_type)
            self.assertIn(row.acceptable_primary, ["yes", "no", "conditional"])
            self.assertIn(row.regulatory_risk_level, ["low", "medium", "high"])
            self.assertGreaterEqual(row.severity, 0.0)
            self.assertLessEqual(row.severity, 1.0)

    def test_circular_rows_not_acceptable_primary(self):
        for row in self.rows:
            if row.failure_type in ("MEASUREMENT_CIRCULARITY", "DETECTION_ACCELERATION"):
                if row.severity >= 0.8:
                    self.assertNotEqual(row.acceptable_primary, "yes")

    def test_invalid_rows_have_repair(self):
        for row in self.rows:
            if row.acceptable_primary == "no":
                self.assertTrue(len(row.best_repair_endpoint) > 0)

    def test_json_full_output(self):
        result = json.loads(generate_gold_dataset_json())
        self.assertIn("cases", result)
        self.assertIn("gold_dataset_table", result)
        self.assertEqual(len(result["cases"]), 4)
        self.assertGreaterEqual(len(result["gold_dataset_table"]), 4)
        for case in result["cases"]:
            for key in ["case_id", "device_context", "causal_graph", "issue_detection",
                         "endpoint_analyses", "regulatory_conditions",
                         "has_interpretation", "final_regulatory_status"]:
                self.assertIn(key, case)
        for row in result["gold_dataset_table"]:
            for key in ["device", "original_endpoint", "failure_type", "severity",
                         "acceptable_primary", "required_design",
                         "best_repair_endpoint", "regulatory_risk_level"]:
                self.assertIn(key, row)


# ===================================================================
# Unit tests — individual modules
# ===================================================================

class TestClaimParserUnit(unittest.TestCase):

    def test_mechanism_claim(self):
        claim = _make_claim("Device uses electromagnetic stimulation at cellular level", "EM stimulator")
        self.assertEqual(classify_claim(claim), ClaimLevel.A)

    def test_process_claim(self):
        claim = _make_claim("System improves care pathway coordination and referral", "Care coordinator app")
        self.assertEqual(classify_claim(claim), ClaimLevel.B)

    def test_outcome_claim(self):
        claim = _make_claim("Treatment reduces mortality and hospitalization rates", "Treatment device")
        self.assertEqual(classify_claim(claim), ClaimLevel.C)

    def test_complete_chain_claim(self):
        claim = _make_claim("Neurostimulation activates pathways leading to reduced mortality", "Neurostimulator")
        self.assertEqual(classify_claim(claim), ClaimLevel.D)

    def test_default_with_endpoints(self):
        claim = _make_claim("Device works well", "Generic device",
                            endpoints=[Endpoint("mortality", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT)])
        self.assertEqual(classify_claim(claim), ClaimLevel.C)


class TestEndpointClassifierUnit(unittest.TestCase):

    def test_instrumented_detection(self):
        ea = classify_endpoint(Endpoint("time-to-detection", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True))
        self.assertEqual(ea.nature, EndpointNature.INSTRUMENTED)
        self.assertEqual(ea.causal_role, CausalRole.CIRCULAR)

    def test_subjective_pain(self):
        ea = classify_endpoint(Endpoint("pain score", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True))
        self.assertEqual(ea.nature, EndpointNature.SUBJECTIVE)

    def test_objective_mortality(self):
        ea = classify_endpoint(Endpoint("mortality rate", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True))
        self.assertEqual(ea.nature, EndpointNature.OBJECTIVE)

    def test_circularity_flag_primary_instrumented(self):
        ea = classify_endpoint(Endpoint("alert-based detection rate", EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR, True))
        self.assertIn(BiasFlag.CIRCULARITY_RISK, ea.flags)
        self.assertIn(BiasFlag.DETECTION_BIAS, ea.flags)


class TestCausalGraphUnit(unittest.TestCase):

    def test_direct(self):
        claim = _make_claim("Reduces mortality", "Device")
        claim.level = ClaimLevel.C
        analyses = classify_endpoints(ClinicalClaim("", "", endpoints=[
            Endpoint("mortality", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True)]))
        self.assertEqual(build_causal_structure(claim, analyses), CausalStructure.DIRECT)

    def test_circular(self):
        claim = _make_claim("Detects events", "Monitor")
        claim.level = ClaimLevel.B
        analyses = classify_endpoints(ClinicalClaim("", "", endpoints=[
            Endpoint("time-to-detection", EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR, True)]))
        self.assertEqual(build_causal_structure(claim, analyses), CausalStructure.CIRCULAR)

    def test_invalid(self):
        claim = _make_claim("Does something", "Device")
        claim.level = ClaimLevel.B
        self.assertEqual(build_causal_structure(claim, []), CausalStructure.INVALID)


class TestBiasDetectorUnit(unittest.TestCase):

    def test_circularity_high(self):
        d = build_bias_detections([BiasFlag.CIRCULARITY_RISK], [], CausalStructure.CIRCULAR)
        self.assertEqual([x for x in d if x.flag == BiasFlag.CIRCULARITY_RISK][0].severity, "HIGH")

    def test_perception_medium(self):
        d = build_bias_detections([BiasFlag.PERCEPTION_BIAS], [], CausalStructure.DIRECT)
        self.assertEqual([x for x in d if x.flag == BiasFlag.PERCEPTION_BIAS][0].severity, "MEDIUM")

    def test_no_duplicates(self):
        d = build_bias_detections([BiasFlag.CIRCULARITY_RISK, BiasFlag.CIRCULARITY_RISK], [], CausalStructure.CIRCULAR)
        self.assertEqual(len([x for x in d if x.flag == BiasFlag.CIRCULARITY_RISK]), 1)


class TestDesignEngineUnit(unittest.TestCase):

    def test_circular_blocks_rct(self):
        claim = _make_claim("Detect faster", "Device")
        claim.level = ClaimLevel.B
        rec = recommend_design(claim, [], CausalStructure.CIRCULAR, [BiasFlag.CIRCULARITY_RISK])
        self.assertEqual(rec.primary_design, StudyDesign.NOT_IDENTIFIABLE)

    def test_subjective_requires_sham(self):
        ea = classify_endpoint(Endpoint("pain", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT, True))
        claim = _make_claim("Reduces pain", "Device")
        claim.level = ClaimLevel.C
        rec = recommend_design(claim, [ea], CausalStructure.DIRECT, [BiasFlag.PERCEPTION_BIAS])
        self.assertEqual(rec.primary_design, StudyDesign.SHAM_RCT)

    def test_outcome_claim_rct(self):
        ea = classify_endpoint(Endpoint("mortality", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True))
        claim = _make_claim("Reduces mortality", "Device")
        claim.level = ClaimLevel.C
        self.assertEqual(recommend_design(claim, [ea], CausalStructure.DIRECT, []).primary_design, StudyDesign.RCT)


class TestRepairEngineUnit(unittest.TestCase):

    def test_clean_study_no_repair_v1(self):
        claim = _make_claim("Reduces mortality", "Device")
        claim.level = ClaimLevel.C
        ea = classify_endpoint(Endpoint("mortality", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True))
        design = recommend_design(claim, [ea], CausalStructure.DIRECT, [])
        self.assertIsNone(generate_repair_plan(claim, [ea], CausalStructure.DIRECT, [], [], design))

    def test_clean_study_no_repair_v2(self):
        claim = _make_claim("Reduces mortality", "Device")
        claim.level = ClaimLevel.C
        ea = classify_endpoint(Endpoint("mortality", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True))
        design = recommend_design(claim, [ea], CausalStructure.DIRECT, [])
        self.assertIsNone(generate_repair_plan_v2(claim, [ea], CausalStructure.DIRECT, [], [], design))


class TestEdgeCases(unittest.TestCase):

    def test_empty_endpoints(self):
        output = analyze(_make_claim("Device does something", "Device"))
        self.assertEqual(output.causal_structure, CausalStructure.INVALID)

    def test_mixed_endpoints_no_perception_bias(self):
        claim = _make_claim("Device reduces pain and hospitalization", "Treatment device", endpoints=[
            Endpoint("pain score", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT, True),
            Endpoint("hospitalization rate", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, False)])
        flags = {bd.flag for bd in analyze(claim).bias_flags}
        self.assertNotIn(BiasFlag.PERCEPTION_BIAS, flags)

    def test_process_tautology(self):
        claim = parse_claim(_make_claim(
            "Monitoring system improves monitoring coverage via screening", "Screening monitoring device",
            endpoints=[Endpoint("monitoring coverage rate", EndpointNature.INSTRUMENTED,
                                CausalRole.CIRCULAR, True, description="automated monitoring metric")]))
        flags = detect_structural_issues(claim, classify_endpoints(claim),
                                         build_causal_structure(claim, classify_endpoints(claim)))
        self.assertIn(BiasFlag.PROCESS_TAUTOLOGY, flags)

    def test_clean_study_gold_acceptable(self):
        claim = _make_claim("Reduces mortality", "Therapeutic device",
                            endpoints=[Endpoint("mortality", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True)])
        gold = analyze_to_gold("CLEAN", claim)
        self.assertEqual(gold.final_regulatory_status, FinalRegulatoryStatus.ACCEPTABLE_PRIMARY_WITH_CONDITIONS)

    def test_v2_causal_chain_structure(self):
        claim = _make_claim("Neurostimulation reduces pain via endorphin release", "Neurostim wristband",
                            endpoints=[Endpoint("pain VAS", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT, True)])
        v2 = analyze(claim).repair_plan_v2
        self.assertIsNotNone(v2)
        roles = [s.role for s in v2.causal_chain]
        self.assertEqual(roles[0], "INTERVENTION")
        self.assertEqual(roles[-1], "OUTCOME")


# ===================================================================
# MODE DETECTION
# ===================================================================

class TestModeDetection(unittest.TestCase):

    def test_review_protocol(self):
        self.assertEqual(detect_mode("Evaluate this RCT protocol with primary endpoint mortality"), Mode.REVIEW)

    def test_review_study(self):
        self.assertEqual(detect_mode("Assess the published study on OdySight"), Mode.REVIEW)

    def test_review_dossier(self):
        self.assertEqual(detect_mode("Review the HAS dossier for Moovcare"), Mode.REVIEW)

    def test_design_claim(self):
        self.assertEqual(detect_mode("Our claim is that AI triage improves stroke outcomes"), Mode.DESIGN)

    def test_design_intended_benefit(self):
        self.assertEqual(detect_mode("The intended benefit is pain reduction via neurostimulation"), Mode.DESIGN)

    def test_design_what_evidence(self):
        self.assertEqual(detect_mode("What evidence should we generate to demonstrate benefit?"), Mode.DESIGN)

    def test_design_product_concept(self):
        self.assertEqual(detect_mode("Product concept: remote monitoring for macular degeneration"), Mode.DESIGN)

    def test_ambiguous_defaults_design(self):
        self.assertEqual(detect_mode("We want to show our device works"), Mode.DESIGN)


# ===================================================================
# EPISTEMIC CORE — shared primitives
# ===================================================================

class TestEpistemicCoreShared(unittest.TestCase):

    def test_recommend_design_from_core(self):
        claim = _make_claim("Reduces mortality", "Device")
        claim.level = ClaimLevel.C
        ea = classify_endpoint(Endpoint("mortality", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True))
        rec = core_recommend_design(claim, [ea], CausalStructure.DIRECT, [])
        self.assertEqual(rec.primary_design, StudyDesign.RCT)

    def test_assess_identification_circular(self):
        claim = _make_claim("Detects faster via monitoring", "Monitor")
        claim.level = ClaimLevel.B
        ea = classify_endpoint(Endpoint("time-to-detection", EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR, True))
        ident = assess_identification(claim, [ea], CausalStructure.CIRCULAR,
                                       [BiasFlag.CIRCULARITY_RISK, BiasFlag.DETECTION_BIAS])
        self.assertTrue(ident.adjudication_needed)
        self.assertTrue(ident.external_data_needed)
        self.assertGreaterEqual(ident.minimum_design_strength, 0.7)

    def test_assess_identification_subjective(self):
        claim = _make_claim("Reduces pain", "Device")
        claim.level = ClaimLevel.C
        ea = classify_endpoint(Endpoint("pain VAS", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT, True))
        ident = assess_identification(claim, [ea], CausalStructure.DIRECT, [BiasFlag.PERCEPTION_BIAS])
        self.assertTrue(ident.blinding_needed)

    def test_assess_identification_clean(self):
        claim = _make_claim("Reduces mortality", "Device")
        claim.level = ClaimLevel.C
        ea = classify_endpoint(Endpoint("mortality", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True))
        ident = assess_identification(claim, [ea], CausalStructure.DIRECT, [])
        self.assertFalse(ident.blinding_needed)
        self.assertFalse(ident.adjudication_needed)


# ===================================================================
# DESIGN MODE — CASE 1: OdySight
# ===================================================================

class TestDesignOdySight(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.output = run_design_mode(
            claim_text="Remote monitoring enables earlier detection of visual acuity degradation",
            intervention="OdySight remote visual acuity monitoring device",
            domain="ophthalmology",
        )

    def test_mode_is_design(self):
        self.assertEqual(self.output.mode, "DESIGN")

    # DAG
    def test_dag_intervention(self):
        self.assertIn("OdySight", self.output.target_dag.intervention)

    def test_dag_has_mediators(self):
        self.assertGreaterEqual(len(self.output.target_dag.mediators), 2)

    def test_dag_has_outcomes(self):
        self.assertGreaterEqual(len(self.output.target_dag.outcomes), 2)

    def test_dag_has_prohibited(self):
        self.assertGreaterEqual(len(self.output.target_dag.prohibited_outcomes), 1)
        prohibited_text = " ".join(self.output.target_dag.prohibited_outcomes).lower()
        self.assertTrue("device" in prohibited_text or "detection" in prohibited_text
                        or "monitoring" in prohibited_text)

    def test_dag_has_edges(self):
        self.assertGreaterEqual(len(self.output.target_dag.edges), 2)

    # Identification
    def test_identification_adjudication(self):
        self.assertTrue(self.output.identification.adjudication_needed)

    def test_identification_external_data(self):
        self.assertTrue(self.output.identification.external_data_needed)

    # Endpoint families
    def test_endpoint_families_exist(self):
        self.assertGreaterEqual(len(self.output.endpoint_families), 1)

    def test_endpoint_families_have_primary(self):
        weights = {f.regulatory_weight for f in self.output.endpoint_families}
        self.assertIn("PRIMARY", weights)

    # Design space
    def test_design_space_8_candidates(self):
        self.assertEqual(len(self.output.design_space.candidates), 8)

    def test_design_space_types(self):
        types = {c.design_type for c in self.output.design_space.candidates}
        self.assertIn(EvidenceDesignType.INDIVIDUAL_RCT, types)
        self.assertIn(EvidenceDesignType.PRAGMATIC_RCT, types)
        self.assertIn(EvidenceDesignType.CLUSTER_RCT, types)
        self.assertIn(EvidenceDesignType.REGISTRY_RCT, types)
        self.assertIn(EvidenceDesignType.STEPPED_WEDGE, types)
        self.assertIn(EvidenceDesignType.CONTROLLED_ITS, types)
        self.assertIn(EvidenceDesignType.TARGET_TRIAL_EMULATION, types)
        self.assertIn(EvidenceDesignType.EXTERNAL_CONTROL_COHORT, types)

    def test_design_candidates_scores_valid(self):
        for c in self.output.design_space.candidates:
            self.assertGreater(c.causal_strength, 0.0)
            self.assertLessEqual(c.causal_strength, 1.0)
            self.assertGreater(c.feasibility, 0.0)
            self.assertGreater(c.has_acceptability, 0.0)
            self.assertTrue(len(c.expected_biases) >= 1)
            self.assertTrue(len(c.endpoint_compatibility) >= 1)

    # Regulatory manifold
    def test_manifold_8_points(self):
        self.assertEqual(len(self.output.regulatory_manifold.points), 8)

    def test_manifold_scores_valid(self):
        for p in self.output.regulatory_manifold.points:
            self.assertGreaterEqual(p.identification_score, 0.0)
            self.assertLessEqual(p.identification_score, 1.0)
            self.assertGreaterEqual(p.bias_risk, 0.0)
            self.assertGreaterEqual(p.operational_complexity, 0.0)
            self.assertGreaterEqual(p.regulatory_acceptability, 0.0)

    def test_manifold_best_point(self):
        best = self.output.regulatory_manifold.best_point()
        self.assertIsNotNone(best)
        self.assertGreater(best.regulatory_acceptability, 0.5)

    # Regulatory strategy
    def test_strategy_not_empty(self):
        self.assertGreater(len(self.output.regulatory_strategy), 50)

    # JSON
    def test_json_complete(self):
        result = json.loads(design_to_json(
            "Remote monitoring enables earlier detection",
            "OdySight device", "ophthalmology",
        ))
        for key in ["mode", "target_dag", "identification", "endpoint_families",
                     "design_space", "regulatory_manifold", "regulatory_strategy"]:
            self.assertIn(key, result)


# ===================================================================
# DESIGN MODE — CASE 2: Moovcare
# ===================================================================

class TestDesignMoovcare(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.output = run_design_mode(
            claim_text="Symptom monitoring improves overall survival through early alert to physicians",
            intervention="Moovcare web-based symptom monitoring application",
            domain="oncology",
        )

    def test_dag_mediators_include_alert(self):
        med_text = " ".join(self.output.target_dag.mediators).lower()
        self.assertTrue("alert" in med_text or "notification" in med_text or "detection" in med_text)

    def test_dag_outcomes_include_survival(self):
        out_text = " ".join(self.output.target_dag.outcomes).lower()
        self.assertIn("survival", out_text)

    def test_dag_prohibited_not_empty(self):
        self.assertGreaterEqual(len(self.output.target_dag.prohibited_outcomes), 1)

    def test_8_designs_generated(self):
        self.assertEqual(len(self.output.design_space.candidates), 8)

    def test_individual_rct_high_acceptability(self):
        rct = [c for c in self.output.design_space.candidates
               if c.design_type == EvidenceDesignType.INDIVIDUAL_RCT]
        self.assertGreaterEqual(rct[0].has_acceptability, 0.8)

    def test_endpoint_families_have_survival(self):
        all_eps = [e for f in self.output.endpoint_families for e in f.endpoints]
        eps_text = " ".join(all_eps).lower()
        self.assertIn("survival", eps_text)

    def test_manifold_rct_dominates(self):
        best = self.output.regulatory_manifold.best_point()
        self.assertIn(best.design.design_type, [
            EvidenceDesignType.INDIVIDUAL_RCT,
            EvidenceDesignType.PRAGMATIC_RCT,
            EvidenceDesignType.REGISTRY_RCT,
        ])

    def test_strategy_mentions_critere(self):
        self.assertIn("CRITÈRES", self.output.regulatory_strategy.upper())


# ===================================================================
# DESIGN MODE — CASE 3: Remedee
# ===================================================================

class TestDesignRemedee(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.output = run_design_mode(
            claim_text="Neurostimulation triggers endorphin release, reducing chronic pain",
            intervention="Remedee millimeter-wave neurostimulation wristband",
            domain="pain management",
        )

    def test_dag_mediators_endorphin(self):
        med_text = " ".join(self.output.target_dag.mediators).lower()
        self.assertIn("endorphin", med_text)

    def test_dag_outcomes_analgesic(self):
        out_text = " ".join(self.output.target_dag.outcomes).lower()
        self.assertTrue("analgesic" in out_text or "walk test" in out_text
                        or "return-to-work" in out_text)

    def test_identification_blinding_needed(self):
        self.assertTrue(self.output.identification.blinding_needed)

    def test_identification_mediator_measurement(self):
        self.assertTrue(self.output.identification.mediator_measurement_needed)

    def test_endpoint_families_biomarker(self):
        families = {f.family_name for f in self.output.endpoint_families}
        self.assertTrue("BIOMARKER" in families or "HARD_CLINICAL" in families)

    def test_8_designs(self):
        self.assertEqual(len(self.output.design_space.candidates), 8)

    def test_individual_rct_mentions_sham(self):
        rct = [c for c in self.output.design_space.candidates
               if c.design_type == EvidenceDesignType.INDIVIDUAL_RCT]
        biases_text = " ".join(rct[0].expected_biases).lower()
        self.assertIn("sham", biases_text)

    def test_strategy_mentions_aveugle(self):
        self.assertTrue("aveugle" in self.output.regulatory_strategy.lower()
                        or "blinding" in self.output.regulatory_strategy.lower()
                        or "sham" in self.output.regulatory_strategy.lower())


# ===================================================================
# DESIGN MODE — CASE 4: AI Triage AVC
# ===================================================================

class TestDesignAITriage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.output = run_design_mode(
            claim_text="AI triage improves stroke outcomes by prioritizing brain CT scans",
            intervention="AI-powered CT scan triage and prioritization system",
            domain="emergency neurology",
        )

    def test_dag_mediators_triage(self):
        med_text = " ".join(self.output.target_dag.mediators).lower()
        self.assertTrue("prioritization" in med_text or "scan" in med_text
                        or "decision" in med_text)

    def test_dag_outcomes_mortality_or_mrs(self):
        out_text = " ".join(self.output.target_dag.outcomes).lower()
        self.assertTrue("mortality" in out_text or "rankin" in out_text)

    def test_dag_prohibited_ai_triggered(self):
        proh_text = " ".join(self.output.target_dag.prohibited_outcomes).lower()
        self.assertTrue("ai" in proh_text or "triage" in proh_text or "time-to" in proh_text)

    def test_identification_adjudication_needed(self):
        self.assertTrue(self.output.identification.adjudication_needed)

    def test_8_designs(self):
        self.assertEqual(len(self.output.design_space.candidates), 8)

    def test_cluster_rct_higher_feasibility_in_emergency(self):
        cluster = [c for c in self.output.design_space.candidates
                   if c.design_type == EvidenceDesignType.CLUSTER_RCT]
        individual = [c for c in self.output.design_space.candidates
                      if c.design_type == EvidenceDesignType.INDIVIDUAL_RCT]
        self.assertGreater(cluster[0].feasibility, individual[0].feasibility)

    def test_individual_rct_lower_feasibility_emergency(self):
        rct = [c for c in self.output.design_space.candidates
               if c.design_type == EvidenceDesignType.INDIVIDUAL_RCT]
        self.assertLessEqual(rct[0].feasibility, 0.50)

    def test_manifold_best_not_external_control(self):
        best = self.output.regulatory_manifold.best_point()
        self.assertNotEqual(best.design.design_type, EvidenceDesignType.EXTERNAL_CONTROL_COHORT)

    def test_strategy_source_externe(self):
        strat = self.output.regulatory_strategy.lower()
        self.assertTrue("externe" in strat or "external" in strat)


# ===================================================================
# DESIGN SPACE CONSISTENCY — cross-case
# ===================================================================

class TestDesignSpaceCrossCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.odysight = run_design_mode(
            "Remote monitoring for visual acuity", "OdySight device", "ophthalmology")
        cls.moovcare = run_design_mode(
            "Symptom monitoring improves survival", "Moovcare app", "oncology")
        cls.remedee = run_design_mode(
            "Neurostimulation reduces pain via endorphin", "Remedee wristband", "pain management")
        cls.triage = run_design_mode(
            "AI triage improves stroke outcomes", "AI triage system", "emergency neurology")
        cls.all_outputs = [cls.odysight, cls.moovcare, cls.remedee, cls.triage]

    def test_all_produce_8_designs(self):
        for o in self.all_outputs:
            self.assertEqual(len(o.design_space.candidates), 8)

    def test_all_produce_8_manifold_points(self):
        for o in self.all_outputs:
            self.assertEqual(len(o.regulatory_manifold.points), 8)

    def test_all_have_nonempty_strategy(self):
        for o in self.all_outputs:
            self.assertGreater(len(o.regulatory_strategy), 50)

    def test_all_have_dag_edges(self):
        for o in self.all_outputs:
            self.assertGreaterEqual(len(o.target_dag.edges), 2)

    def test_all_have_endpoint_families(self):
        for o in self.all_outputs:
            self.assertGreaterEqual(len(o.endpoint_families), 1)

    def test_all_have_prohibited_outcomes(self):
        for o in self.all_outputs:
            self.assertGreaterEqual(len(o.target_dag.prohibited_outcomes), 1)

    def test_rct_always_highest_causal_strength(self):
        for o in self.all_outputs:
            rct = [c for c in o.design_space.candidates
                   if c.design_type == EvidenceDesignType.INDIVIDUAL_RCT]
            for c in o.design_space.candidates:
                self.assertLessEqual(c.causal_strength, rct[0].causal_strength + 0.01)

    def test_external_control_always_lowest_acceptability(self):
        for o in self.all_outputs:
            ext = [c for c in o.design_space.candidates
                   if c.design_type == EvidenceDesignType.EXTERNAL_CONTROL_COHORT]
            for c in o.design_space.candidates:
                self.assertGreaterEqual(c.has_acceptability, ext[0].has_acceptability - 0.01)

    def test_json_roundtrip(self):
        for o in self.all_outputs:
            d = o.to_dict()
            self.assertIn("target_dag", d)
            self.assertIn("design_space", d)
            self.assertIn("regulatory_manifold", d)
            self.assertEqual(len(d["design_space"]["candidates"]), 8)
            self.assertEqual(len(d["regulatory_manifold"]["points"]), 8)


# ===================================================================
# BOTH MODES USE SAME CORE — architecture tests
# ===================================================================

class TestSingleEpistemicCore(unittest.TestCase):

    def test_review_uses_core_recommend_design(self):
        claim = _make_claim("Reduces mortality", "Device",
                            endpoints=[Endpoint("mortality", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True)])
        output = analyze(claim)
        self.assertEqual(output.design_recommendation.primary_design, StudyDesign.RCT)

    def test_design_uses_core_identification(self):
        output = run_design_mode("AI triage improves outcomes", "AI system", "neurology")
        self.assertIsNotNone(output.identification)
        self.assertTrue(isinstance(output.identification, IdentificationRequirements))

    def test_design_uses_core_dag(self):
        output = run_design_mode("Monitoring improves survival", "Monitor app", "oncology")
        self.assertIsNotNone(output.target_dag)
        self.assertTrue(isinstance(output.target_dag, TargetDAG))

    def test_core_functions_importable(self):
        from epistemic_core import (
            parse_claim, classify_endpoints, build_causal_structure,
            detect_structural_issues, build_bias_detections,
            recommend_design, assess_identification,
            infer_target_dag, compute_endpoint_families,
            generate_design_space, compute_regulatory_manifold,
        )
        self.assertTrue(callable(recommend_design))
        self.assertTrue(callable(assess_identification))
        self.assertTrue(callable(infer_target_dag))

    def test_design_engine_wrapper_works(self):
        from design_engine import recommend_design as wrapper_recommend
        claim = _make_claim("Reduces mortality", "Device")
        claim.level = ClaimLevel.C
        ea = classify_endpoint(Endpoint("mortality", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True))
        rec = wrapper_recommend(claim, [ea], CausalStructure.DIRECT, [])
        self.assertEqual(rec.primary_design, StudyDesign.RCT)


# ===================================================================
# EPISTEMIC MANIFOLD — shared layer tests (L10)
# ===================================================================

from epistemic_manifold import (
    classify_region,
    compute_review_position,
    compute_design_manifold,
    compute_repair_delta,
)
from models import (
    BiasVector,
    DesignManifoldPoint,
    EpistemicManifoldOutput,
    EpistemicManifoldPosition,
    ManifoldCoordinates,
    ManifoldFeasibleRegion,
    ManifoldRegion,
    RepairDirection,
    RepairManifoldDelta,
)


class TestManifoldRegionClassification(unittest.TestCase):

    def test_high_coords_acceptable(self):
        c = ManifoldCoordinates(0.8, 0.8, 0.9, 0.7, 0.7, 0.8, 0.8)
        self.assertEqual(classify_region(c), ManifoldRegion.ACCEPTABLE)

    def test_low_outcome_independence_invalid(self):
        c = ManifoldCoordinates(0.1, 0.8, 0.9, 0.7, 0.7, 0.8, 0.8)
        self.assertEqual(classify_region(c), ManifoldRegion.INVALID)

    def test_low_ecv_invalid(self):
        c = ManifoldCoordinates(0.8, 0.8, 0.9, 0.7, 0.7, 0.1, 0.8)
        self.assertEqual(classify_region(c), ManifoldRegion.INVALID)

    def test_mid_coords_fragile(self):
        c = ManifoldCoordinates(0.4, 0.4, 0.3, 0.3, 0.4, 0.4, 0.4)
        self.assertEqual(classify_region(c), ManifoldRegion.FRAGILE)

    def test_all_zero_invalid(self):
        c = ManifoldCoordinates(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.assertEqual(classify_region(c), ManifoldRegion.INVALID)


class TestManifoldCoordinates(unittest.TestCase):

    def test_aggregate_score(self):
        c = ManifoldCoordinates(0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7)
        self.assertAlmostEqual(c.aggregate_score(), 0.7, places=2)

    def test_as_vector_length(self):
        c = ManifoldCoordinates(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
        self.assertEqual(len(c.as_vector()), 7)

    def test_to_dict_all_keys(self):
        c = ManifoldCoordinates(0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
        d = c.to_dict()
        for key in ["outcome_independence", "contamination_risk", "randomization_strength",
                     "blinding_strength", "temporal_depth", "endpoint_clinical_validity",
                     "data_source_independence"]:
            self.assertIn(key, d)


class TestBiasVector(unittest.TestCase):

    def test_magnitude_zero(self):
        bv = BiasVector()
        self.assertAlmostEqual(bv.magnitude(), 0.0)

    def test_magnitude_nonzero(self):
        bv = BiasVector(circularity=0.9, detection=0.9)
        self.assertGreater(bv.magnitude(), 1.0)

    def test_to_dict(self):
        bv = BiasVector(circularity=0.5, perception=0.3)
        d = bv.to_dict()
        self.assertAlmostEqual(d["circularity"], 0.5)
        self.assertAlmostEqual(d["perception"], 0.3)


class TestManifoldReviewOdySight(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.claim = _make_claim(
            text="OdySight enables earlier detection of visual acuity degradation "
                 "through remote monitoring",
            intervention="OdySight remote visual acuity monitoring device",
            endpoints=[
                Endpoint("time-to-detection of progression",
                         EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR, True),
            ],
            domain="ophthalmology",
        )
        cls.output = analyze(cls.claim)
        cls.pos = cls.output.manifold_position

    def test_manifold_position_exists(self):
        self.assertIsNotNone(self.pos)

    def test_region_invalid(self):
        self.assertEqual(self.pos.region, ManifoldRegion.INVALID)

    def test_outcome_independence_low(self):
        self.assertLess(self.pos.coordinates.outcome_independence, 0.3)

    def test_bias_vector_circularity_high(self):
        self.assertGreaterEqual(self.pos.bias_vector.circularity, 0.8)

    def test_bias_vector_detection_high(self):
        self.assertGreaterEqual(self.pos.bias_vector.detection, 0.5)

    def test_repair_directions_exist(self):
        self.assertGreater(len(self.pos.repair_directions), 0)

    def test_repair_direction_outcome_independence(self):
        axes = [r.axis for r in self.pos.repair_directions]
        self.assertIn("outcome_independence", axes)

    def test_regulatory_status_blocked(self):
        self.assertIn("BLOCKED", self.pos.regulatory_status)

    def test_aggregate_score_low(self):
        self.assertLess(self.pos.coordinates.aggregate_score(), 0.4)

    def test_json_contains_manifold(self):
        result = json.loads(analyze_to_json(self.claim))
        self.assertIn("epistemic_manifold", result)
        em = result["epistemic_manifold"]
        self.assertIn("coordinates", em)
        self.assertIn("region", em)
        self.assertIn("bias_vector", em)
        self.assertIn("repair_directions", em)
        self.assertEqual(em["region"], "INVALID")


class TestManifoldRepairDeltaOdySight(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.claim = _make_claim(
            text="OdySight enables earlier detection of visual acuity degradation "
                 "through remote monitoring",
            intervention="OdySight remote visual acuity monitoring device",
            endpoints=[
                Endpoint("time-to-detection of progression",
                         EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR, True),
            ],
            domain="ophthalmology",
        )
        cls.output = analyze(cls.claim)
        cls.delta = cls.output.repair_delta

    def test_repair_delta_exists(self):
        self.assertIsNotNone(self.delta)

    def test_region_before_invalid(self):
        self.assertEqual(self.delta.region_before, ManifoldRegion.INVALID)

    def test_region_after_acceptable(self):
        self.assertEqual(self.delta.region_after, ManifoldRegion.ACCEPTABLE)

    def test_outcome_independence_improves(self):
        self.assertGreater(
            self.delta.after.outcome_independence,
            self.delta.before.outcome_independence,
        )

    def test_ecv_improves(self):
        self.assertGreater(
            self.delta.after.endpoint_clinical_validity,
            self.delta.before.endpoint_clinical_validity,
        )

    def test_repair_vectors_nonzero(self):
        self.assertGreater(len(self.delta.repair_vectors), 0)

    def test_all_deltas_positive(self):
        for rv in self.delta.repair_vectors:
            self.assertGreater(rv.delta, 0.0)

    def test_json_contains_delta(self):
        result = json.loads(analyze_to_json(self.claim))
        self.assertIn("repair_manifold_delta", result)
        d = result["repair_manifold_delta"]
        self.assertIn("before", d)
        self.assertIn("after", d)
        self.assertEqual(d["region_before"], "INVALID")
        self.assertEqual(d["region_after"], "ACCEPTABLE")


class TestManifoldDesignOdySight(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.output = run_design_mode(
            "OdySight improves clinical management through earlier detection",
            "OdySight",
            "ophthalmology",
        )
        cls.em = cls.output.epistemic_manifold

    def test_epistemic_manifold_exists(self):
        self.assertIsNotNone(self.em)

    def test_design_points_count(self):
        self.assertEqual(len(self.em.design_points), 8)

    def test_all_points_have_coordinates(self):
        for p in self.em.design_points:
            self.assertIsNotNone(p.coordinates)
            self.assertEqual(len(p.coordinates.as_vector()), 7)

    def test_all_points_have_region(self):
        for p in self.em.design_points:
            self.assertIn(p.region, set(ManifoldRegion))

    def test_optimal_design_exists(self):
        self.assertIsNotNone(self.em.optimal_design)
        self.assertEqual(self.em.optimal_design.region, ManifoldRegion.ACCEPTABLE)

    def test_individual_rct_highest_aggregate(self):
        rct = [p for p in self.em.design_points if p.design_type == "INDIVIDUAL_RCT"]
        self.assertEqual(len(rct), 1)
        for p in self.em.design_points:
            self.assertGreaterEqual(
                rct[0].coordinates.aggregate_score(),
                p.coordinates.aggregate_score() - 0.01,
            )

    def test_external_control_lowest_aggregate(self):
        ext = [p for p in self.em.design_points if p.design_type == "EXTERNAL_CONTROL_COHORT"]
        self.assertEqual(len(ext), 1)
        for p in self.em.design_points:
            self.assertLessEqual(
                ext[0].coordinates.aggregate_score(),
                p.coordinates.aggregate_score() + 0.01,
            )

    def test_feasible_region_exists(self):
        self.assertIsNotNone(self.em.feasible_region)
        self.assertGreater(self.em.feasible_region.min_outcome_independence, 0.5)

    def test_monotonic_aggregate_with_acceptability(self):
        pairs = [(p.coordinates.aggregate_score(), p.regulatory_acceptability)
                 for p in self.em.design_points]
        for i in range(len(pairs)):
            for j in range(i + 1, len(pairs)):
                if pairs[i][1] > pairs[j][1]:
                    self.assertGreaterEqual(pairs[i][0], pairs[j][0] - 0.15)

    def test_json_contains_design_manifold(self):
        result = json.loads(design_to_json(
            "OdySight improves clinical management",
            "OdySight", "ophthalmology",
        ))
        self.assertIn("epistemic_manifold", result)
        em = result["epistemic_manifold"]
        self.assertIn("design_points", em)
        self.assertIn("feasible_region", em)
        self.assertIn("optimal_design", em)


class TestManifoldCrossMode(unittest.TestCase):

    def test_review_and_design_same_device_agree_on_direction(self):
        claim = _make_claim(
            text="AI triage improves stroke outcomes",
            intervention="AI-based triage system",
            endpoints=[
                Endpoint("time-to-treatment", EndpointNature.INSTRUMENTED,
                         CausalRole.CIRCULAR, True),
            ],
            domain="neurology",
        )
        review = analyze(claim)
        design_out = run_design_mode(
            "AI triage improves stroke outcomes",
            "AI-based triage system",
            "neurology",
        )

        review_oi = review.manifold_position.coordinates.outcome_independence
        design_top = design_out.epistemic_manifold.optimal_design
        self.assertGreater(design_top.coordinates.outcome_independence, review_oi)

    def test_clean_study_acceptable_region(self):
        claim = _make_claim(
            text="Drug X reduces mortality at 12 months",
            intervention="Drug X",
            endpoints=[
                Endpoint("all-cause mortality", EndpointNature.OBJECTIVE,
                         CausalRole.INDEPENDENT, True),
            ],
        )
        output = analyze(claim)
        self.assertEqual(output.manifold_position.region, ManifoldRegion.ACCEPTABLE)
        self.assertGreater(output.manifold_position.coordinates.aggregate_score(), 0.5)

    def test_subjective_only_has_perception_bias_and_low_ecv(self):
        claim = _make_claim(
            text="Device Y reduces pain",
            intervention="Device Y neurostimulation",
            endpoints=[
                Endpoint("pain VAS score", EndpointNature.SUBJECTIVE,
                         CausalRole.INDEPENDENT, True),
            ],
        )
        output = analyze(claim)
        self.assertGreater(output.manifold_position.bias_vector.perception, 0.5)
        self.assertLess(output.manifold_position.coordinates.endpoint_clinical_validity, 0.5)

    def test_repair_always_improves_aggregate(self):
        for case in [
            ("monitoring device", "time-to-detection",
             EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR),
            ("AI triage", "time-to-treatment",
             EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR),
        ]:
            claim = _make_claim(
                text=f"{case[0]} improves outcomes",
                intervention=case[0],
                endpoints=[Endpoint(case[1], case[2], case[3], True)],
            )
            output = analyze(claim)
            if output.repair_delta:
                self.assertGreater(
                    output.repair_delta.after.aggregate_score(),
                    output.repair_delta.before.aggregate_score(),
                    msg=f"Repair did not improve aggregate for {case[0]}",
                )

    def test_design_points_continuous_not_categorical(self):
        output = run_design_mode("Device improves survival", "Device", "oncology")
        scores = [p.coordinates.aggregate_score() for p in output.epistemic_manifold.design_points]
        unique_scores = set(round(s, 4) for s in scores)
        self.assertGreater(len(unique_scores), 3,
                           "Design points should have distinct continuous scores")


# ===================================================================
# L11 — CALIBRATION TESTS (manifold vs HAS/CNEDiMTS ground truth)
# ===================================================================

class TestCalibrationOdySight(unittest.TestCase):
    """HAS ground truth: NOT ACCEPTABLE as primary — circular endpoint."""

    @classmethod
    def setUpClass(cls):
        cls.claim = _make_claim(
            text="OdySight enables earlier detection of visual acuity degradation "
                 "through remote monitoring, reducing time-to-detection of macular "
                 "degeneration progression.",
            intervention="OdySight remote visual acuity monitoring device",
            endpoints=[
                Endpoint("time-to-detection of progression",
                         EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR, True,
                         "Time from baseline to device-detected visual acuity change"),
            ],
            domain="ophthalmology",
        )
        cls.output = analyze(cls.claim)
        cls.pos = cls.output.manifold_position

    def test_region_invalid(self):
        self.assertEqual(self.pos.region, ManifoldRegion.INVALID)

    def test_aggregate_below_fragile_threshold(self):
        self.assertLess(self.pos.coordinates.aggregate_score(), 0.35)

    def test_outcome_independence_near_zero(self):
        self.assertLessEqual(self.pos.coordinates.outcome_independence, 0.15)

    def test_ecv_near_zero(self):
        self.assertLessEqual(self.pos.coordinates.endpoint_clinical_validity, 0.10)

    def test_circularity_dominates_bias(self):
        self.assertGreaterEqual(self.pos.bias_vector.circularity, 0.8)

    def test_repair_delta_reaches_acceptable(self):
        self.assertIsNotNone(self.output.repair_delta)
        self.assertEqual(self.output.repair_delta.region_after, ManifoldRegion.ACCEPTABLE)

    def test_status_blocked(self):
        self.assertIn("BLOCKED", self.pos.regulatory_status)


class TestCalibrationMoovcare(unittest.TestCase):
    """HAS ground truth: ACCEPTABLE WITH CONDITIONS (ASA II, CAPRI trial)."""

    @classmethod
    def setUpClass(cls):
        cls.claim = _make_claim(
            text="Moovcare improves overall survival in lung cancer patients "
                 "through web-based symptom monitoring and early alert to physicians.",
            intervention="Moovcare web-based symptom monitoring application",
            endpoints=[
                Endpoint("overall survival", EndpointNature.OBJECTIVE,
                         CausalRole.MEDIATED, True,
                         "Time from randomization to death from any cause"),
                Endpoint("time-to-treatment modification", EndpointNature.OBJECTIVE,
                         CausalRole.MEDIATED, False,
                         "Time from symptom alert to treatment change"),
            ],
            domain="oncology",
        )
        cls.output = analyze(cls.claim)
        cls.pos = cls.output.manifold_position

    def test_region_acceptable(self):
        self.assertEqual(self.pos.region, ManifoldRegion.ACCEPTABLE)

    def test_aggregate_above_070(self):
        self.assertGreater(self.pos.coordinates.aggregate_score(), 0.70)

    def test_outcome_independence_full(self):
        self.assertGreaterEqual(self.pos.coordinates.outcome_independence, 0.90)

    def test_ecv_primary_weighted_above_06(self):
        self.assertGreater(self.pos.coordinates.endpoint_clinical_validity, 0.60)

    def test_no_circularity_bias(self):
        self.assertAlmostEqual(self.pos.bias_vector.circularity, 0.0)

    def test_dsi_above_06(self):
        self.assertGreater(self.pos.coordinates.data_source_independence, 0.60)

    def test_contamination_risk_above_08(self):
        self.assertGreater(self.pos.coordinates.contamination_risk, 0.80)

    def test_status_acceptable(self):
        self.assertIn("ACCEPTABLE", self.pos.regulatory_status)


class TestCalibrationRemedee(unittest.TestCase):
    """HAS ground truth: ACCEPTABLE WITH REDESIGN — sham + objective anchoring needed."""

    @classmethod
    def setUpClass(cls):
        cls.claim = _make_claim(
            text="Remedee wristband uses millimeter-wave neurostimulation to trigger "
                 "endorphin release, reducing chronic pain.",
            intervention="Remedee millimeter-wave neurostimulation wristband",
            endpoints=[
                Endpoint("pain VAS score", EndpointNature.SUBJECTIVE,
                         CausalRole.INDEPENDENT, True,
                         "Visual analog scale for pain intensity"),
                Endpoint("patient quality of life", EndpointNature.SUBJECTIVE,
                         CausalRole.INDEPENDENT, False,
                         "SF-36 quality of life questionnaire"),
            ],
            domain="pain management",
        )
        cls.output = analyze(cls.claim)
        cls.pos = cls.output.manifold_position

    def test_region_fragile(self):
        self.assertEqual(self.pos.region, ManifoldRegion.FRAGILE)

    def test_blinding_strength_low(self):
        self.assertLess(self.pos.coordinates.blinding_strength, 0.20)

    def test_ecv_low(self):
        self.assertLess(self.pos.coordinates.endpoint_clinical_validity, 0.40)

    def test_perception_bias_high(self):
        self.assertGreater(self.pos.bias_vector.perception, 0.5)

    def test_no_circularity(self):
        self.assertAlmostEqual(self.pos.bias_vector.circularity, 0.0)

    def test_outcome_independence_full(self):
        self.assertGreaterEqual(self.pos.coordinates.outcome_independence, 0.90)

    def test_status_conditional(self):
        self.assertIn("CONDITIONAL", self.pos.regulatory_status)

    def test_repair_delta_improves_blinding(self):
        delta = self.output.repair_delta
        self.assertIsNotNone(delta)
        self.assertGreater(delta.after.blinding_strength, delta.before.blinding_strength)
        self.assertGreater(delta.after.blinding_strength, 0.80)


class TestCalibrationAITriage(unittest.TestCase):
    """HAS ground truth: NOT ACCEPTABLE as primary — tautological + detection acceleration."""

    @classmethod
    def setUpClass(cls):
        cls.claim = _make_claim(
            text="AI triage system reduces time-to-treatment for stroke patients "
                 "by automated detection and prioritization of brain CT scans.",
            intervention="AI-powered CT scan triage and prioritization system",
            endpoints=[
                Endpoint("time-to-treatment", EndpointNature.INSTRUMENTED,
                         CausalRole.CIRCULAR, True,
                         "Time from scan acquisition to treatment initiation, triggered by AI alert"),
            ],
            domain="emergency neurology",
        )
        cls.output = analyze(cls.claim)
        cls.pos = cls.output.manifold_position

    def test_region_invalid(self):
        self.assertEqual(self.pos.region, ManifoldRegion.INVALID)

    def test_aggregate_lowest_of_all_cases(self):
        self.assertLess(self.pos.coordinates.aggregate_score(), 0.20)

    def test_tautology_bias_high(self):
        self.assertGreater(self.pos.bias_vector.tautology, 0.7)

    def test_circularity_bias_high(self):
        self.assertGreater(self.pos.bias_vector.circularity, 0.8)

    def test_ecv_near_zero(self):
        self.assertLess(self.pos.coordinates.endpoint_clinical_validity, 0.10)

    def test_repair_reaches_acceptable(self):
        self.assertIsNotNone(self.output.repair_delta)
        self.assertEqual(self.output.repair_delta.region_after, ManifoldRegion.ACCEPTABLE)

    def test_status_blocked(self):
        self.assertIn("BLOCKED", self.pos.regulatory_status)


class TestCalibrationCrossCaseOrdering(unittest.TestCase):
    """HAS-consistent severity ordering across all 4 cases."""

    @classmethod
    def setUpClass(cls):
        odysight = _make_claim(
            "OdySight enables earlier detection through remote monitoring",
            "OdySight remote visual acuity monitoring device",
            [Endpoint("time-to-detection of progression",
                      EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR, True)],
            "ophthalmology")
        moovcare = _make_claim(
            "Moovcare improves overall survival through web-based symptom monitoring",
            "Moovcare web-based symptom monitoring application",
            [Endpoint("overall survival", EndpointNature.OBJECTIVE,
                      CausalRole.MEDIATED, True, "Time from randomization to death"),
             Endpoint("time-to-treatment modification", EndpointNature.OBJECTIVE,
                      CausalRole.MEDIATED, False, "Time from symptom alert to treatment change")],
            "oncology")
        remedee = _make_claim(
            "Remedee wristband uses millimeter-wave neurostimulation to trigger endorphin release, reducing chronic pain.",
            "Remedee millimeter-wave neurostimulation wristband",
            [Endpoint("pain VAS score", EndpointNature.SUBJECTIVE,
                      CausalRole.INDEPENDENT, True),
             Endpoint("patient quality of life", EndpointNature.SUBJECTIVE,
                      CausalRole.INDEPENDENT, False)],
            "pain management")
        ai_triage = _make_claim(
            "AI triage system reduces time-to-treatment for stroke patients",
            "AI-powered CT scan triage and prioritization system",
            [Endpoint("time-to-treatment", EndpointNature.INSTRUMENTED,
                      CausalRole.CIRCULAR, True)],
            "emergency neurology")

        cls.scores = {}
        for name, claim in [("odysight", odysight), ("moovcare", moovcare),
                             ("remedee", remedee), ("ai_triage", ai_triage)]:
            o = analyze(claim)
            cls.scores[name] = o.manifold_position.coordinates.aggregate_score()

    def test_moovcare_highest(self):
        self.assertGreater(self.scores["moovcare"], self.scores["remedee"])
        self.assertGreater(self.scores["moovcare"], self.scores["odysight"])
        self.assertGreater(self.scores["moovcare"], self.scores["ai_triage"])

    def test_remedee_above_circular_cases(self):
        self.assertGreater(self.scores["remedee"], self.scores["odysight"])
        self.assertGreater(self.scores["remedee"], self.scores["ai_triage"])

    def test_ai_triage_lowest(self):
        self.assertLessEqual(self.scores["ai_triage"], self.scores["odysight"])

    def test_region_ordering(self):
        """MOOVCARE=ACCEPTABLE > REMEDEE=FRAGILE > ODYSIGHT=INVALID >= AI_TRIAGE=INVALID"""
        self.assertGreater(self.scores["moovcare"], 0.60)
        self.assertGreater(self.scores["remedee"], 0.35)
        self.assertLess(self.scores["odysight"], 0.35)
        self.assertLess(self.scores["ai_triage"], 0.35)


if __name__ == "__main__":
    unittest.main()

