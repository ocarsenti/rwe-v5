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
    ComparatorFeasibility,
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
        cls.bias_flags, cls.bias_reasons = detect_structural_issues(cls.parsed, cls.ep_analyses, cls.structure)
        cls.bias_detections = build_bias_detections(cls.bias_flags, cls.ep_analyses, cls.structure, cls.bias_reasons)
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
        cls.bias_flags, cls.bias_reasons = detect_structural_issues(cls.parsed, cls.ep_analyses, cls.structure)
        cls.bias_detections = build_bias_detections(cls.bias_flags, cls.ep_analyses, cls.structure, cls.bias_reasons)
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
        cls.bias_flags, cls.bias_reasons = detect_structural_issues(cls.parsed, cls.ep_analyses, cls.structure)
        cls.bias_detections = build_bias_detections(cls.bias_flags, cls.ep_analyses, cls.structure, cls.bias_reasons)
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
        self.assertTrue(any(kw in all_repairs for kw in ["analgesic", "analg"]))

    def test_L7_step2_pain_repair_functional(self):
        pain_blocks = [b for b in self.repair_v2.endpoint_repairs if "pain" in b.original_endpoint.lower()]
        all_repairs = " ".join(r.endpoint.lower() for b in pain_blocks for r in b.repairs)
        self.assertTrue(any(kw in all_repairs for kw in [
            "walk test", "marche", "functional", "fonctionnel",
            "actigraphy", "actimétrie", "return-to-work", "retour au travail",
        ]))

    def test_L7_step2_qol_repair_hospitalization(self):
        qol_blocks = [b for b in self.repair_v2.endpoint_repairs if "quality" in b.original_endpoint.lower()]
        self.assertTrue(len(qol_blocks) >= 1)
        all_repairs = " ".join(r.endpoint.lower() for b in qol_blocks for r in b.repairs)
        self.assertTrue(any(kw in all_repairs for kw in ["hospitalization", "hospitali"]))

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
        cls.bias_flags, cls.bias_reasons = detect_structural_issues(cls.parsed, cls.ep_analyses, cls.structure)
        cls.bias_detections = build_bias_detections(cls.bias_flags, cls.ep_analyses, cls.structure, cls.bias_reasons)
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
        self.assertTrue(any(kw in all_repairs for kw in ["mortality", "mortalit"]))

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
        # Circular-endpoint cases (ODYSIGHT, AI_TRIAGE) are always the most severe
        self.assertGreater(sev["CASE_ODYSIGHT"], sev["CASE_REMEDEE"])
        self.assertGreater(sev["CASE_AI_TRIAGE_AVC"], sev["CASE_REMEDEE"])
        # MOOVCARE (mediation gap + PROCESS_TAUTOLOGY) and REMEDEE (subjective endpoint)
        # are both below the circular cases — exact ordering between them is calibration-dependent
        self.assertGreater(sev["CASE_ODYSIGHT"], sev["CASE_MOOVCARE"])
        self.assertGreater(sev["CASE_AI_TRIAGE_AVC"], sev["CASE_MOOVCARE"])

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
        flags, _reasons = detect_structural_issues(claim, classify_endpoints(claim),
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


# ===================================================================
# CAS Engine tests
# ===================================================================

from cas_engine import evaluate_cas, compute_cas_score, apply_device_gate, determine_verdict
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
    CASGatingResult,
)


def _make_device(match_type, claim="Device A", study="Device A"):
    return DeviceAlignment(
        device_match_type=match_type,
        device_description_claim=claim,
        device_description_study=study,
    )


def _make_population(match_type, claim="Population A", study="Population A",
                     subgroup="", shift=EligibilityShift.NONE):
    return PopulationAlignment(
        population_match_type=match_type,
        population_description_claim=claim,
        population_description_study=study,
        subgroup_description=subgroup,
        eligibility_shift=shift,
    )


def _make_context(match_type, pathway=CarePathwayMatch.YES,
                  org=OrganizationDependency.LOW, country="France"):
    return ContextAlignment(
        context_match_type=match_type,
        care_pathway_match=pathway,
        organization_dependency=org,
        study_country=country,
    )


class TestCASScoreComputation(unittest.TestCase):

    def test_perfect_alignment(self):
        self.assertAlmostEqual(compute_cas_score(0, 0, 0), 1.0)

    def test_worst_alignment(self):
        self.assertAlmostEqual(compute_cas_score(1, 1, 1), 0.0)

    def test_device_only_distance(self):
        score = compute_cas_score(0.7, 0, 0)
        self.assertAlmostEqual(score, 1.0 - 0.4 * 0.7)

    def test_population_only_distance(self):
        score = compute_cas_score(0, 0.5, 0)
        self.assertAlmostEqual(score, 1.0 - 0.35 * 0.5)

    def test_context_only_distance(self):
        score = compute_cas_score(0, 0, 0.4)
        self.assertAlmostEqual(score, 1.0 - 0.25 * 0.4)

    def test_score_always_between_0_and_1(self):
        for dd in [0, 0.3, 0.5, 0.7, 1.0]:
            for dp in [0, 0.3, 0.5, 1.0]:
                for dc in [0, 0.4, 0.6, 1.0]:
                    s = compute_cas_score(dd, dp, dc)
                    self.assertGreaterEqual(s, 0.0)
                    self.assertLessEqual(s, 1.0)


class TestCASDeviceGate(unittest.TestCase):

    def test_exact_device_passes(self):
        self.assertTrue(apply_device_gate(0.0).device_gate_passed)

    def test_same_family_passes(self):
        self.assertTrue(apply_device_gate(0.3).device_gate_passed)

    def test_unknown_passes(self):
        self.assertTrue(apply_device_gate(0.5).device_gate_passed)

    def test_proxy_device_blocked(self):
        result = apply_device_gate(0.7)
        self.assertFalse(result.device_gate_passed)
        self.assertIn("mismatch", result.device_gate_reason.lower())

    def test_different_device_blocked(self):
        self.assertFalse(apply_device_gate(1.0).device_gate_passed)


class TestCASVerdict(unittest.TestCase):

    def test_acceptable(self):
        gating = CASGatingResult(device_gate_passed=True)
        self.assertEqual(determine_verdict(0.8, gating), CASVerdict.ACCEPTABLE)
        self.assertEqual(determine_verdict(0.7, gating), CASVerdict.ACCEPTABLE)

    def test_weak(self):
        gating = CASGatingResult(device_gate_passed=True)
        self.assertEqual(determine_verdict(0.6, gating), CASVerdict.WEAK_EVIDENCE)
        self.assertEqual(determine_verdict(0.5, gating), CASVerdict.WEAK_EVIDENCE)

    def test_rejected(self):
        gating = CASGatingResult(device_gate_passed=True)
        self.assertEqual(determine_verdict(0.4, gating), CASVerdict.REJECTED)

    def test_device_gate_overrides(self):
        gating = CASGatingResult(device_gate_passed=False, device_gate_reason="blocked")
        self.assertEqual(determine_verdict(0.9, gating), CASVerdict.REJECTED)


class TestCASFullEvaluation(unittest.TestCase):

    def test_perfect_case(self):
        result = evaluate_cas(
            "Device X improves outcome", "Device X", "cardiology",
            _make_device(DeviceMatchType.EXACT_DEVICE),
            _make_population(PopulationMatchType.EXACT_INDICATION),
            _make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM),
        )
        self.assertAlmostEqual(result.cas_score, 1.0)
        self.assertEqual(result.verdict, CASVerdict.ACCEPTABLE)
        self.assertTrue(result.gating.device_gate_passed)
        self.assertEqual(len(result.risks), 0)

    def test_proxy_device_rejected(self):
        result = evaluate_cas(
            "Device Y", "Device Y", "neuro",
            _make_device(DeviceMatchType.PROXY_DEVICE, "INCEPTIV", "EVOKE"),
            _make_population(PopulationMatchType.EXACT_INDICATION),
            _make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM),
        )
        self.assertEqual(result.verdict, CASVerdict.REJECTED)
        self.assertFalse(result.gating.device_gate_passed)
        self.assertTrue(any(r.dimension == "DEVICE" for r in result.risks))

    def test_narrower_subgroup_acceptable(self):
        result = evaluate_cas(
            "Claim", "DM", "onco",
            _make_device(DeviceMatchType.EXACT_DEVICE),
            _make_population(PopulationMatchType.NARROWER_SUBGROUP,
                           "All cancer patients", "Chemo only", "Chemo subgroup"),
            _make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM),
        )
        self.assertGreater(result.cas_score, 0.7)
        self.assertEqual(result.verdict, CASVerdict.ACCEPTABLE)
        self.assertTrue(any(r.dimension == "POPULATION" for r in result.risks))

    def test_different_context_reduces_score(self):
        result_same = evaluate_cas(
            "Claim", "DM", "onco",
            _make_device(DeviceMatchType.EXACT_DEVICE),
            _make_population(PopulationMatchType.EXACT_INDICATION),
            _make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM),
        )
        result_diff = evaluate_cas(
            "Claim", "DM", "onco",
            _make_device(DeviceMatchType.EXACT_DEVICE),
            _make_population(PopulationMatchType.EXACT_INDICATION),
            _make_context(ContextMatchType.DIFFERENT_SYSTEM, CarePathwayMatch.NO,
                         OrganizationDependency.HIGH, "USA"),
        )
        self.assertGreater(result_same.cas_score, result_diff.cas_score)

    def test_worst_case_zero(self):
        result = evaluate_cas(
            "Claim", "DM", "domain",
            _make_device(DeviceMatchType.DIFFERENT_DEVICE, "A", "B"),
            _make_population(PopulationMatchType.DIFFERENT_POPULATION, "Pop A", "Pop B"),
            _make_context(ContextMatchType.DIFFERENT_SYSTEM, CarePathwayMatch.NO,
                         OrganizationDependency.HIGH, "Japan"),
        )
        self.assertAlmostEqual(result.cas_score, 0.0)
        self.assertEqual(result.verdict, CASVerdict.REJECTED)

    def test_to_dict_structure(self):
        result = evaluate_cas(
            "Test claim", "TestDM", "test",
            _make_device(DeviceMatchType.SAME_FAMILY, "DM-A", "DM-B"),
            _make_population(PopulationMatchType.NARROWER_SUBGROUP, "All", "Sub"),
            _make_context(ContextMatchType.PARTIALLY_COMPARABLE,
                         CarePathwayMatch.PARTIAL, OrganizationDependency.MEDIUM, "Germany"),
        )
        d = result.to_dict()
        self.assertIn("scores", d)
        self.assertIn("cas_score", d["scores"])
        self.assertIn("device_alignment", d)
        self.assertIn("population_alignment", d)
        self.assertIn("context_alignment", d)
        self.assertIn("verdict", d)
        self.assertIn("gating", d)
        self.assertIn("risks", d)
        self.assertIn("regulatory_interpretation", d)

    def test_regulatory_interpretation_fr(self):
        result = evaluate_cas(
            "Claim FR", "DM", "domain",
            _make_device(DeviceMatchType.EXACT_DEVICE),
            _make_population(PopulationMatchType.EXACT_INDICATION),
            _make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM),
            lang="fr",
        )
        self.assertIn("ACCEPTABLE", result.regulatory_interpretation)
        self.assertIn("Dispositif", result.regulatory_interpretation)

    def test_regulatory_interpretation_en(self):
        result = evaluate_cas(
            "Claim EN", "DM", "domain",
            _make_device(DeviceMatchType.EXACT_DEVICE),
            _make_population(PopulationMatchType.EXACT_INDICATION),
            _make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM),
            lang="en",
        )
        self.assertIn("ACCEPTABLE", result.regulatory_interpretation)
        self.assertIn("Device", result.regulatory_interpretation)

    def test_eligibility_shift_major_adds_risk(self):
        result = evaluate_cas(
            "Claim", "DM", "domain",
            _make_device(DeviceMatchType.EXACT_DEVICE),
            _make_population(PopulationMatchType.EXACT_INDICATION,
                           shift=EligibilityShift.MAJOR),
            _make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM),
        )
        elig_risks = [r for r in result.risks if "eligibility" in r.description.lower()]
        self.assertGreater(len(elig_risks), 0)

    def test_care_pathway_no_adds_risk(self):
        result = evaluate_cas(
            "Claim", "DM", "domain",
            _make_device(DeviceMatchType.EXACT_DEVICE),
            _make_population(PopulationMatchType.EXACT_INDICATION),
            _make_context(ContextMatchType.PARTIALLY_COMPARABLE,
                         CarePathwayMatch.NO, OrganizationDependency.LOW, "UK"),
        )
        pathway_risks = [r for r in result.risks if "pathway" in r.description.lower()]
        self.assertGreater(len(pathway_risks), 0)

    def test_org_dependency_high_adds_risk(self):
        result = evaluate_cas(
            "Claim", "DM", "domain",
            _make_device(DeviceMatchType.EXACT_DEVICE),
            _make_population(PopulationMatchType.EXACT_INDICATION),
            _make_context(ContextMatchType.PARTIALLY_COMPARABLE,
                         CarePathwayMatch.PARTIAL, OrganizationDependency.HIGH, "Germany"),
        )
        org_risks = [r for r in result.risks if "organizational" in r.description.lower()]
        self.assertGreater(len(org_risks), 0)

    def test_care_pathway_partial_adds_moderate_risk(self):
        # cf. avis CNEDiMTS CONTINUUM CONNECT / SCEWO BRO 7425: even with
        # context_match_type=SAME_HEALTHCARE_SYSTEM (d_context=0), a partially
        # matching care pathway is a real, HAS-cited transposability concern
        # (T09) that must not be silently dropped just because it isn't NO.
        result = evaluate_cas(
            "Claim", "DM", "domain",
            _make_device(DeviceMatchType.EXACT_DEVICE),
            _make_population(PopulationMatchType.EXACT_INDICATION),
            _make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM,
                         CarePathwayMatch.PARTIAL, OrganizationDependency.LOW, "France"),
        )
        pathway_risks = [r for r in result.risks
                          if r.dimension == "CONTEXT" and "pathway" in r.description.lower()]
        self.assertEqual(len(pathway_risks), 1)
        self.assertEqual(pathway_risks[0].risk_level, "MODERATE")

    def test_care_pathway_yes_adds_no_risk(self):
        result = evaluate_cas(
            "Claim", "DM", "domain",
            _make_device(DeviceMatchType.EXACT_DEVICE),
            _make_population(PopulationMatchType.EXACT_INDICATION),
            _make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM,
                         CarePathwayMatch.YES, OrganizationDependency.MEDIUM, "France"),
        )
        # cf. IMPLICITY IM009 (CNEDiMTS validation case #11): org_dependency=MEDIUM
        # alone, with a fully matching pathway, is NOT a HAS-cited concern —
        # confirms org_dependency stays HIGH-only and isn't loosened alongside pathway.
        self.assertEqual(len(result.risks), 0)


class TestCASDistanceTables(unittest.TestCase):

    def test_device_distances_monotonic(self):
        from cas_engine import _D_DEVICE
        self.assertEqual(_D_DEVICE[DeviceMatchType.EXACT_DEVICE], 0.0)
        self.assertLess(_D_DEVICE[DeviceMatchType.SAME_FAMILY],
                       _D_DEVICE[DeviceMatchType.PROXY_DEVICE])
        self.assertLess(_D_DEVICE[DeviceMatchType.PROXY_DEVICE],
                       _D_DEVICE[DeviceMatchType.DIFFERENT_DEVICE])
        self.assertEqual(_D_DEVICE[DeviceMatchType.DIFFERENT_DEVICE], 1.0)

    def test_population_distances_monotonic(self):
        from cas_engine import _D_POP
        self.assertEqual(_D_POP[PopulationMatchType.EXACT_INDICATION], 0.0)
        self.assertLess(_D_POP[PopulationMatchType.NARROWER_SUBGROUP],
                       _D_POP[PopulationMatchType.BROADER_POPULATION])
        self.assertLess(_D_POP[PopulationMatchType.BROADER_POPULATION],
                       _D_POP[PopulationMatchType.DIFFERENT_POPULATION])
        self.assertEqual(_D_POP[PopulationMatchType.DIFFERENT_POPULATION], 1.0)

    def test_context_distances_monotonic(self):
        from cas_engine import _D_CONTEXT
        self.assertEqual(_D_CONTEXT[ContextMatchType.SAME_HEALTHCARE_SYSTEM], 0.0)
        self.assertLess(_D_CONTEXT[ContextMatchType.PARTIALLY_COMPARABLE],
                       _D_CONTEXT[ContextMatchType.DIFFERENT_SYSTEM])
        self.assertEqual(_D_CONTEXT[ContextMatchType.DIFFERENT_SYSTEM], 1.0)

    def test_weights_sum_to_one(self):
        from cas_engine import W_DEVICE, W_POP, W_CONTEXT
        self.assertAlmostEqual(W_DEVICE + W_POP + W_CONTEXT, 1.0)


class TestCASCNEDiMTSCases(unittest.TestCase):
    """Validate CAS engine against known CNEDiMTS corpus patterns."""

    def test_presage_care(self):
        result = evaluate_cas(
            "PRESAGE CARE améliore le suivi des personnes âgées fragiles",
            "PRESAGE CARE", "télésurveillance gériatrique",
            _make_device(DeviceMatchType.EXACT_DEVICE, "PRESAGE CARE v1.3", "PRESAGE CARE v1.3"),
            _make_population(PopulationMatchType.NARROWER_SUBGROUP,
                           "Personnes âgées fragiles 65+",
                           "Patients dépendance légère à modérée",
                           "GIR 3-4 uniquement",
                           EligibilityShift.MAJOR),
            _make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM,
                         CarePathwayMatch.NO, OrganizationDependency.HIGH, "France"),
        )
        self.assertEqual(result.verdict, CASVerdict.ACCEPTABLE)
        self.assertTrue(any(r.dimension == "POPULATION" for r in result.risks))
        self.assertTrue(any(r.dimension == "CONTEXT" for r in result.risks))

    def test_inceptiv_proxy(self):
        result = evaluate_cas(
            "INCEPTIV réduit la douleur chronique", "INCEPTIV", "neurostimulation",
            _make_device(DeviceMatchType.PROXY_DEVICE, "INCEPTIV", "EVOKE boucle fermée"),
            _make_population(PopulationMatchType.EXACT_INDICATION,
                           "Douleur chronique", "Douleur chronique"),
            _make_context(ContextMatchType.PARTIALLY_COMPARABLE,
                         CarePathwayMatch.PARTIAL, OrganizationDependency.LOW, "USA"),
        )
        self.assertEqual(result.verdict, CASVerdict.REJECTED)
        self.assertFalse(result.gating.device_gate_passed)

    def test_tucky_center_worst(self):
        result = evaluate_cas(
            "TUCKY CENTER télésurveillance pédiatrique", "TUCKY CENTER", "pédiatrie",
            _make_device(DeviceMatchType.DIFFERENT_DEVICE,
                        "TUCKY CENTER", "Autres DM de télésurveillance"),
            _make_population(PopulationMatchType.DIFFERENT_POPULATION,
                           "Enfants sous chimiothérapie", "Adultes post-chirurgie"),
            _make_context(ContextMatchType.DIFFERENT_SYSTEM,
                         CarePathwayMatch.NO, OrganizationDependency.HIGH, "Canada"),
        )
        self.assertAlmostEqual(result.cas_score, 0.0)
        self.assertEqual(result.verdict, CASVerdict.REJECTED)

    def test_continuum_connect_partial(self):
        result = evaluate_cas(
            "CONTINUUM CONNECT télésurveillance oncologie",
            "CONTINUUM+ CONNECT", "oncologie",
            _make_device(DeviceMatchType.SAME_FAMILY,
                        "CONTINUUM+ CONNECT", "Autres plateformes de télésurveillance"),
            _make_population(PopulationMatchType.EXACT_INDICATION,
                           "Patients en immunothérapie",
                           "Patients en immunothérapie"),
            _make_context(ContextMatchType.PARTIALLY_COMPARABLE,
                         CarePathwayMatch.PARTIAL, OrganizationDependency.MEDIUM, "France"),
        )
        self.assertTrue(0.5 <= result.cas_score < 1.0)
        self.assertIn(result.verdict, [CASVerdict.ACCEPTABLE, CASVerdict.WEAK_EVIDENCE])


class TestSurrogateRisk(unittest.TestCase):
    """Unit tests for BiasFlag.SURROGATE_RISK."""

    def _ep(self, name, role, is_primary=True, is_validated=False, description=""):
        return Endpoint(
            name=name,
            nature=EndpointNature.OBJECTIVE,
            causal_role=role,
            is_primary=is_primary,
            description=description,
            is_validated_surrogate=is_validated,
        )

    def test_fires_mediated_primary_not_validated(self):
        """Surrogate endpoint in primary position without validation → flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("HbA1c reduction", CausalRole.MEDIATED)
        result = classify_endpoint(ep)
        self.assertIn(BiasFlag.SURROGATE_RISK, result.flags)

    def test_suppressed_when_validated(self):
        """is_validated_surrogate=True suppresses the flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("HbA1c reduction", CausalRole.MEDIATED, is_validated=True)
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.SURROGATE_RISK, result.flags)

    def test_suppressed_for_hard_clinical_endpoint(self):
        """Hard clinical outcome (survival) does not trigger flag even if MEDIATED."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("overall survival", CausalRole.MEDIATED)
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.SURROGATE_RISK, result.flags)

    def test_suppressed_for_hard_clinical_endpoint_fr(self):
        """French hard clinical outcome (survie globale) does not trigger flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("survie globale", CausalRole.MEDIATED,
                      description="Temps entre randomisation et décès")
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.SURROGATE_RISK, result.flags)

    def test_suppressed_for_independent_role(self):
        """INDEPENDENT causal role does not trigger flag (not a surrogate position)."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("pain score", CausalRole.INDEPENDENT)
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.SURROGATE_RISK, result.flags)

    def test_suppressed_for_secondary_endpoint(self):
        """MEDIATED secondary endpoint does not trigger flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("HbA1c reduction", CausalRole.MEDIATED, is_primary=False)
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.SURROGATE_RISK, result.flags)

    def test_french_surrogate_fires(self):
        """French surrogate endpoint (réduction HbA1c) triggers flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("réduction de l'HbA1c", CausalRole.MEDIATED,
                      description="Variation de l'HbA1c à 6 mois")
        result = classify_endpoint(ep)
        self.assertIn(BiasFlag.SURROGATE_RISK, result.flags)

    def test_bias_detail_severity_high(self):
        """SURROGATE_RISK is classified as HIGH severity."""
        from bias_detector import BIAS_DETAILS
        self.assertEqual(BIAS_DETAILS[BiasFlag.SURROGATE_RISK]["severity"], "HIGH")


class TestAdjudicationRisk(unittest.TestCase):
    """Unit tests for BiasFlag.ADJUDICATION_RISK."""

    def _ep(self, name, nature=EndpointNature.OBJECTIVE, role=CausalRole.INDEPENDENT,
            is_primary=True, adjudicated=False, description=""):
        return Endpoint(
            name=name,
            nature=nature,
            causal_role=role,
            is_primary=is_primary,
            description=description,
            is_independently_adjudicated=adjudicated,
        )

    def test_fires_objective_primary_no_cec(self):
        """Objective primary endpoint without CEC → flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("hospitalisation pour insuffisance cardiaque",
                      description="Taux de réhospitalisation à 12 mois")
        result = classify_endpoint(ep)
        self.assertIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_fires_for_stroke_no_cec(self):
        """Stroke without CEC triggers flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("AVC invalidant",
                      description="Accident vasculaire cérébral confirmé par imagerie")
        result = classify_endpoint(ep)
        self.assertIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_fires_for_complications(self):
        """Device complication rate without CEC triggers flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("taux de complications du dispositif")
        result = classify_endpoint(ep)
        self.assertIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_suppressed_when_adjudicated(self):
        """is_independently_adjudicated=True suppresses the flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("hospitalisation pour insuffisance cardiaque", adjudicated=True)
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_suppressed_all_cause_mortality(self):
        """All-cause mortality is self-adjudicating — no flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("mortalité toutes causes",
                      description="Décès toutes causes à 24 mois")
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_suppressed_all_cause_death_en(self):
        """English all-cause death is self-adjudicating — no flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("all-cause mortality",
                      description="all-cause death at 24 months")
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_suppressed_for_subjective_endpoint(self):
        """Subjective endpoint does not trigger adjudication flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("pain VAS score", nature=EndpointNature.SUBJECTIVE)
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_suppressed_for_mediated_role(self):
        """MEDIATED role does not trigger adjudication flag (SURROGATE_RISK territory)."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("réhospitalisation", role=CausalRole.MEDIATED)
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_suppressed_for_secondary_endpoint(self):
        """Secondary endpoint does not trigger flag."""
        from endpoint_classifier import classify_endpoint
        ep = self._ep("hospitalisation pour insuffisance cardiaque", is_primary=False)
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_bias_detail_severity_medium(self):
        """ADJUDICATION_RISK is classified as MEDIUM severity."""
        from bias_detector import BIAS_DETAILS
        self.assertEqual(BIAS_DETAILS[BiasFlag.ADJUDICATION_RISK]["severity"], "MEDIUM")


class TestCNEDiMTSRealEndpoints(unittest.TestCase):
    """
    Tests fondés sur des avis CNEDiMTS réels (corpus 58 avis).
    Vérifie que SURROGATE_RISK et ADJUDICATION_RISK se déclenchent (ou non)
    sur les vrais endpoints et contextes d'étude rencontrés dans les dossiers HAS.
    """

    # ── SURROGATE_RISK ───────────────────────────────────────────────────────

    def test_inspire_iv_iah_is_surrogate(self):
        """
        INSPIRE IV (neurostimulateur SAHOS) — avis CNEDiMTS 2022/2025.
        Critère principal : IAH (Indice d'Apnées-Hypopnées) + IDO.
        L'IAH est un marqueur polysomnographique intermédiaire : il mesure
        la fréquence des apnées, pas le bénéfice clinique final (événements
        cardiovasculaires, mortalité, qualité de vie à long terme).
        HAS : 'Les critères de jugement de l'étude étaient l'IAH et l'IDO'
        — aucun endpoint clinique dur primaire.
        """
        from endpoint_classifier import classify_endpoint
        ep = Endpoint(
            name="indice d'apnées-hypopnées (IAH)",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.MEDIATED,
            is_primary=True,
            description="Variation de l'IAH à 12 mois (événements par heure de sommeil)",
        )
        result = classify_endpoint(ep)
        self.assertIn(BiasFlag.SURROGATE_RISK, result.flags)

    def test_zephyr_vems_is_surrogate(self):
        """
        ZEPHYR (valves endobronchiques BPCO) — avis CNEDiMTS 2024.
        Critère principal : variation du VEMS (FEV1) en pourcentage.
        Le VEMS est un marqueur fonctionnel intermédiaire de la BPCO — il
        ne constitue pas un endpoint clinique dur (exacerbations, hospitalisations,
        mortalité, qualité de vie). HAS : 'Le critère de jugement principal était
        le pourcentage de changement du VEMS'.
        """
        from endpoint_classifier import classify_endpoint
        ep = Endpoint(
            name="variation du VEMS",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.MEDIATED,
            is_primary=True,
            description=(
                "Variation en pourcentage du volume expiratoire maximum par seconde "
                "à 3 mois par rapport à la valeur basale"
            ),
        )
        result = classify_endpoint(ep)
        self.assertIn(BiasFlag.SURROGATE_RISK, result.flags)

    def test_freestyle_libre_hba1c_validated_no_surrogate_risk(self):
        """
        FREESTYLE LIBRE 2 PLUS (CGM diabète) — avis CNEDiMTS 2024.
        Critère principal : réduction du taux d'HbA1c à 6 mois.
        L'HbA1c EST un surrogate validé en diabétologie (lien HbA1c →
        complications diabétiques établi dans la littérature, reconnu ADA/HAS).
        Avec is_validated_surrogate=True, le flag ne doit PAS se déclencher.
        """
        from endpoint_classifier import classify_endpoint
        ep = Endpoint(
            name="taux d'HbA1c",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.MEDIATED,
            is_primary=True,
            description="Variation du taux d'HbA1c à 6 mois",
            is_validated_surrogate=True,
        )
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.SURROGATE_RISK, result.flags)

    def test_inspire_iv_survival_not_surrogate(self):
        """
        INSPIRE IV — mortalité toutes causes comme endpoint secondaire.
        La mortalité toutes causes est un endpoint clinique dur, pas un surrogate,
        même si le dispositif agit via un mécanisme médié (IAH → événements cardiaques).
        """
        from endpoint_classifier import classify_endpoint
        ep = Endpoint(
            name="mortalité toutes causes",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.MEDIATED,
            is_primary=False,
            description="Décès toutes causes à 60 mois",
        )
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.SURROGATE_RISK, result.flags)

    # ── ADJUDICATION_RISK ────────────────────────────────────────────────────

    def test_edwards_sapien3_rehospitalisation_no_cec(self):
        """
        EDWARDS SAPIEN 3 (valve TAVI) — avis CNEDiMTS 2024.
        Étude en ouvert (pas d'aveugle possible pour implant chirurgical).
        Endpoint composite incluant réhospitalisation pour insuffisance cardiaque.
        HAS : 'étude réalisée en ouvert'. La réhospitalisation est un événement
        nécessitant une classification par un comité indépendant pour éviter le
        biais d'attribution des causes entre les deux bras.
        """
        from endpoint_classifier import classify_endpoint
        ep = Endpoint(
            name="réhospitalisation pour insuffisance cardiaque",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=True,
            description=(
                "Taux de réhospitalisation à 2 ans dans l'étude PARTNER 3, "
                "étude contrôlée randomisée en ouvert"
            ),
        )
        result = classify_endpoint(ep)
        self.assertIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_edwards_sapien3_avc_no_cec(self):
        """
        EDWARDS SAPIEN 3 — AVC comme composant du critère composite.
        HAS rapporte les AVC invalides et non invalides. Dans une étude ouverte,
        la classification AVC/AIT nécessite un comité d'adjudication neurologique aveugle.
        """
        from endpoint_classifier import classify_endpoint
        ep = Endpoint(
            name="AVC invalidant ou non invalidant",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=True,
            description=(
                "Accidents vasculaires cérébraux confirmés, évalués sans comité "
                "d'adjudication indépendant dans l'étude en ouvert"
            ),
        )
        result = classify_endpoint(ep)
        self.assertIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_edwards_sapien3_deces_cardiovasculaire_no_cec(self):
        """
        EDWARDS SAPIEN 3 — décès cardiovasculaire.
        Contrairement à la mortalité toutes causes, la mortalité cardiovasculaire
        requiert une attribution de cause (cardiovasculaire vs autre), donc
        un comité d'adjudication. Sans CEC, biais possible.
        """
        from endpoint_classifier import classify_endpoint
        ep = Endpoint(
            name="décès cardiovasculaire",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=True,
            description="Décès attribués à une cause cardiovasculaire à 2 ans",
        )
        result = classify_endpoint(ep)
        self.assertIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_edwards_sapien3_with_cec_no_flag(self):
        """
        Même endpoint EDWARDS SAPIEN 3 AVEC comité d'adjudication documenté.
        Dès qu'un CEC aveugle est en place, le flag ne doit pas se déclencher.
        """
        from endpoint_classifier import classify_endpoint
        ep = Endpoint(
            name="réhospitalisation pour insuffisance cardiaque",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=True,
            description="Taux de réhospitalisation à 2 ans avec CEC aveugle indépendant",
            is_independently_adjudicated=True,
        )
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.ADJUDICATION_RISK, result.flags)

    def test_edwards_sapien3_deces_toutes_causes_no_flag(self):
        """
        EDWARDS SAPIEN 3 — mortalité toutes causes.
        La mortalité toutes causes est auto-adjudicable (décédé ou non),
        pas de biais d'attribution possible. Pas de flag.
        """
        from endpoint_classifier import classify_endpoint
        ep = Endpoint(
            name="mortalité toutes causes",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=True,
            description="all-cause death at 24 months, PARTNER 3 trial",
        )
        result = classify_endpoint(ep)
        self.assertNotIn(BiasFlag.ADJUDICATION_RISK, result.flags)


# ===================================================================
# CAS Wiring tests — EngineOutput.cas_output populated via analyze()
# ===================================================================

class TestCASWiring(unittest.TestCase):
    """Verify that analyze() populates cas_output when alignment objects are present."""

    def _claim_with_cas(self):
        return ClinicalClaim(
            text="Le stimulateur INSPIRE IV réduit l'IAH chez les patients SAOS",
            intervention="INSPIRE IV",
            domain="pulmonology",
            device_alignment=_make_device(DeviceMatchType.EXACT_DEVICE, "INSPIRE IV", "INSPIRE IV"),
            population_alignment=_make_population(PopulationMatchType.EXACT_INDICATION,
                                                   "SAOS sévère", "SAOS sévère"),
            context_alignment=_make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM,
                                             CarePathwayMatch.YES,
                                             OrganizationDependency.LOW, "France"),
        )

    def _claim_without_cas(self):
        return ClinicalClaim(
            text="Le stimulateur INSPIRE IV réduit l'IAH chez les patients SAOS",
            intervention="INSPIRE IV",
            domain="pulmonology",
        )

    def test_cas_output_present_when_alignments_provided(self):
        output = analyze(self._claim_with_cas())
        self.assertIsNotNone(output.cas_output)

    def test_cas_output_absent_when_no_alignments(self):
        output = analyze(self._claim_without_cas())
        self.assertIsNone(output.cas_output)

    def test_cas_output_has_correct_verdict_exact_alignment(self):
        output = analyze(self._claim_with_cas())
        self.assertEqual(output.cas_output.verdict, CASVerdict.ACCEPTABLE)

    def test_cas_output_cas_score_above_threshold(self):
        output = analyze(self._claim_with_cas())
        self.assertGreater(output.cas_output.cas_score, 0.7)

    def test_cas_output_claim_text_matches(self):
        claim = self._claim_with_cas()
        output = analyze(claim)
        self.assertEqual(output.cas_output.claim_text, claim.text)

    def test_cas_output_intervention_matches(self):
        claim = self._claim_with_cas()
        output = analyze(claim)
        self.assertEqual(output.cas_output.intervention, claim.intervention)

    def test_cas_output_rejected_on_different_device(self):
        claim = ClinicalClaim(
            text="Valve NAVITOR réduit la mortalité cardiovasculaire",
            intervention="NAVITOR",
            domain="cardiology",
            device_alignment=_make_device(DeviceMatchType.DIFFERENT_DEVICE,
                                           "NAVITOR", "EDWARDS SAPIEN 3"),
            population_alignment=_make_population(PopulationMatchType.EXACT_INDICATION,
                                                   "RA sévère", "RA sévère"),
            context_alignment=_make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM),
        )
        output = analyze(claim)
        self.assertEqual(output.cas_output.verdict, CASVerdict.REJECTED)

    def test_cas_output_in_to_dict(self):
        output = analyze(self._claim_with_cas())
        d = output.to_dict()
        self.assertIn("cas_output", d)
        self.assertIn("cas_score", d["cas_output"]["scores"])
        self.assertIn("verdict", d["cas_output"])

    def test_to_dict_no_cas_key_when_absent(self):
        output = analyze(self._claim_without_cas())
        d = output.to_dict()
        self.assertNotIn("cas_output", d)

    def test_cas_output_partial_alignment_device_only_returns_none(self):
        """Only device provided but not population/context — no CAS."""
        claim = ClinicalClaim(
            text="ZEPHYR réduit le VEMS",
            intervention="ZEPHYR EBV",
            domain="pulmonology",
            device_alignment=_make_device(DeviceMatchType.EXACT_DEVICE),
        )
        output = analyze(claim)
        self.assertIsNone(output.cas_output)


# ===================================================================
# Methodological risk trend — combines CAS alignment with causal structure +
# bias severity (2026-07-08 CNEDiMTS audit: CAS alone caught 0/7 real HAS
# rejections in a 34-dossier corpus because it never saw causal_structure
# or bias_flags at all; see cas_engine.assess_methodological_risk()).
#
# Renamed 2026-07-10 from determine_overall_verdict()/CASVerdict
# (ACCEPTABLE/WEAK_EVIDENCE/REJECTED) to assess_methodological_risk()/
# MethodologicalRiskLevel (LOW/MODERATE/HIGH) — see
# PROMPT_FIX_CLASSIFIER_ET_VERDICT.md, Part 2: the tool flags methodological
# problems, it does not predict a HAS decision. Escalation logic unchanged.
# ===================================================================

from cas_engine import assess_methodological_risk
from models import BiasDetection, CausalStructure, MethodologicalRiskLevel


def _bias(flag_severity: str) -> BiasDetection:
    return BiasDetection(flag=BiasFlag.NO_COMPARATOR, severity=flag_severity, detail="test")


class TestMethodologicalRisk(unittest.TestCase):

    def test_all_clean_is_low(self):
        a = assess_methodological_risk(CausalStructure.DIRECT, [], None)
        self.assertEqual(a.risk_level, MethodologicalRiskLevel.LOW)
        self.assertEqual(a.severity_counts, {})

    def test_circular_structure_alone_is_moderate(self):
        """Broken structure alone (no HIGH bias flag) is a caution, not a hard
        escalation — recalibrated 2026-07-09, see module comment: HIGH now
        requires structure + a HIGH flag together."""
        a = assess_methodological_risk(CausalStructure.CIRCULAR, [], None)
        self.assertEqual(a.risk_level, MethodologicalRiskLevel.MODERATE)
        self.assertEqual(a.severity_counts, {"CRITICAL": 1})

    def test_invalid_structure_alone_is_moderate(self):
        a = assess_methodological_risk(CausalStructure.INVALID, [], None)
        self.assertEqual(a.risk_level, MethodologicalRiskLevel.MODERATE)

    def test_circular_structure_with_high_bias_is_high(self):
        a = assess_methodological_risk(CausalStructure.CIRCULAR, [_bias("HIGH")], None)
        self.assertEqual(a.risk_level, MethodologicalRiskLevel.HIGH)
        self.assertEqual(a.severity_counts, {"CRITICAL": 1, "HIGH": 1})

    def test_high_severity_bias_alone_is_low(self):
        """A lone HIGH bias flag without a broken causal structure is deliberately
        NOT enough to escalate the trend — recalibrated 2026-07-09 (2nd pass, see
        module comment): SURROGATE_RISK fired alone on an accepted dossier (7947)
        as often as on a real HAS rejection (7425) in the 34-dossier audit (~17%
        precision) — bias severity alone, of any tier, is too noisy a signal;
        only a broken causal structure moves the trend. The HIGH flag still shows
        up in severity_counts — it just doesn't move risk_level alone."""
        a = assess_methodological_risk(CausalStructure.DIRECT, [_bias("HIGH")], None)
        self.assertEqual(a.risk_level, MethodologicalRiskLevel.LOW)
        self.assertEqual(a.severity_counts, {"HIGH": 1})

    def test_medium_severity_bias_alone_is_low(self):
        """A lone MEDIUM bias flag is deliberately NOT enough to escalate —
        recalibrated 2026-07-09: ~18% precision (2 real rejects vs 9 accepted
        dossiers) in the 34-dossier CNEDiMTS audit, too noisy to act on alone."""
        a = assess_methodological_risk(CausalStructure.DIRECT, [_bias("MEDIUM")], None)
        self.assertEqual(a.risk_level, MethodologicalRiskLevel.LOW)

    def test_low_severity_bias_alone_is_low(self):
        a = assess_methodological_risk(CausalStructure.DIRECT, [_bias("LOW")], None)
        self.assertEqual(a.risk_level, MethodologicalRiskLevel.LOW)

    def test_several_bias_flags_without_broken_structure_is_low(self):
        """Even several co-occurring flags (any severity mix) don't escalate the
        trend on their own without a broken causal structure — recalibrated
        2026-07-09 (2nd pass): pairs like MEDIATION_GAP+ADJUDICATION_RISK fired
        on several accepted dossiers (7717/7851/7990/8011) and never on a real
        reject in this combination. All three still appear in severity_counts."""
        a = assess_methodological_risk(
            CausalStructure.DIRECT, [_bias("LOW"), _bias("HIGH"), _bias("MEDIUM")], None,
        )
        self.assertEqual(a.risk_level, MethodologicalRiskLevel.LOW)
        self.assertEqual(a.severity_counts, {"LOW": 1, "HIGH": 1, "MEDIUM": 1})

    def test_cas_rejected_alone_is_high(self):
        claim = ClinicalClaim(
            text="Valve NAVITOR réduit la mortalité cardiovasculaire",
            intervention="NAVITOR", domain="cardiology",
            device_alignment=_make_device(DeviceMatchType.DIFFERENT_DEVICE, "NAVITOR", "EDWARDS SAPIEN 3"),
            population_alignment=_make_population(PopulationMatchType.EXACT_INDICATION, "RA sévère", "RA sévère"),
            context_alignment=_make_context(ContextMatchType.SAME_HEALTHCARE_SYSTEM),
        )
        output = analyze(claim)
        self.assertEqual(output.methodological_risk.risk_level, MethodologicalRiskLevel.HIGH)

    def test_clean_cas_does_not_mask_circular_structure_with_high_bias(self):
        """A dossier with perfect CAS alignment but a CIRCULAR causal structure
        plus a HIGH-severity bias flag must not be reported LOW overall — this is
        the actual WALRUS 7182 / TRIPLE ACTION 7620 shape (both carry
        CIRCULARITY_RISK/SURROGATE_RISK alongside the CIRCULAR structure, not
        a bare structure with no flags)."""
        a = assess_methodological_risk(
            CausalStructure.CIRCULAR, [_bias("HIGH")],
            cas_output=None,
        )
        self.assertEqual(a.risk_level, MethodologicalRiskLevel.HIGH)

    def test_methodological_risk_wired_into_analyze_output(self):
        claim = ClinicalClaim(
            text="Le stimulateur INSPIRE IV réduit l'IAH chez les patients SAOS",
            intervention="INSPIRE IV", domain="pulmonology",
        )
        output = analyze(claim)
        self.assertIsNotNone(output.methodological_risk)

    def test_methodological_risk_in_to_dict(self):
        claim = ClinicalClaim(
            text="Le stimulateur INSPIRE IV réduit l'IAH chez les patients SAOS",
            intervention="INSPIRE IV", domain="pulmonology",
        )
        output = analyze(claim)
        d = output.to_dict()
        self.assertIn("methodological_risk_trend", d)
        self.assertIn("trend_label", d["methodological_risk_trend"])
        self.assertIn("severity_counts", d["methodological_risk_trend"])

    def test_methodological_risk_trend_reported_after_bias_flags_and_gaps(self):
        """Item 9: bias_flags and repair_engine (gaps) must appear before the
        risk trend in the report — it is a secondary, clearly-labeled trend,
        not a leading verdict."""
        claim = ClinicalClaim(
            text="Le stimulateur INSPIRE IV réduit l'IAH chez les patients SAOS",
            intervention="INSPIRE IV", domain="pulmonology",
        )
        output = analyze(claim)
        d = output.to_dict()
        keys = list(d.keys())
        self.assertLess(keys.index("bias_flags"), keys.index("methodological_risk_trend"))
        self.assertLess(keys.index("repair_engine"), keys.index("methodological_risk_trend"))


# ===================================================================
# NO_COMPARATOR BiasFlag (T01)
# ===================================================================

class TestNoComparator(unittest.TestCase):

    def _claim(self, level, has_comparator):
        c = ClinicalClaim(
            text="Device reduces mortality in high-risk patients",
            intervention="Device",
            level=level,
            has_comparator=has_comparator,
            endpoints=[
                Endpoint("mortality", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True),
            ],
        )
        return c

    def test_no_comparator_fires_on_outcome_claim(self):
        output = analyze(self._claim(ClaimLevel.C, False))
        flags = {bd.flag for bd in output.bias_flags}
        self.assertIn(BiasFlag.NO_COMPARATOR, flags)

    def test_no_comparator_fires_on_complete_chain_claim(self):
        output = analyze(self._claim(ClaimLevel.D, False))
        flags = {bd.flag for bd in output.bias_flags}
        self.assertIn(BiasFlag.NO_COMPARATOR, flags)

    def test_no_comparator_silent_when_comparator_present(self):
        output = analyze(self._claim(ClaimLevel.C, True))
        flags = {bd.flag for bd in output.bias_flags}
        self.assertNotIn(BiasFlag.NO_COMPARATOR, flags)

    def test_no_comparator_silent_on_mechanism_claim(self):
        # "electromagnetic modulation" → mechanism → ClaimLevel.A → no NO_COMPARATOR
        claim = ClinicalClaim(
            text="Device activates neural receptors via electromagnetic modulation",
            intervention="Neurostimulator",
            has_comparator=False,
            endpoints=[Endpoint("mechanism marker", EndpointNature.OBJECTIVE, CausalRole.MEDIATED, True)],
        )
        flags = {bd.flag for bd in analyze(claim).bias_flags}
        self.assertNotIn(BiasFlag.NO_COMPARATOR, flags)

    def test_no_comparator_silent_on_process_claim(self):
        # "monitoring alerts surveillance" → process → ClaimLevel.B → no NO_COMPARATOR
        claim = ClinicalClaim(
            text="Device monitors symptoms and generates alerts for remote surveillance",
            intervention="Monitoring platform",
            has_comparator=False,
            endpoints=[Endpoint("alert rate", EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR, True)],
        )
        flags = {bd.flag for bd in analyze(claim).bias_flags}
        self.assertNotIn(BiasFlag.NO_COMPARATOR, flags)

    def test_no_comparator_silent_when_field_is_none(self):
        output = analyze(self._claim(ClaimLevel.C, None))
        flags = {bd.flag for bd in output.bias_flags}
        self.assertNotIn(BiasFlag.NO_COMPARATOR, flags)

    def test_no_comparator_severity_is_high(self):
        output = analyze(self._claim(ClaimLevel.C, False))
        for bd in output.bias_flags:
            if bd.flag == BiasFlag.NO_COMPARATOR:
                self.assertEqual(bd.severity, "HIGH")

    def test_inceptiv_single_arm_fires_no_comparator(self):
        """INCEPTIV = bras unique → NO_COMPARATOR.
        "stimulat" (mechanism) + "pain" (outcome) → ClaimLevel.D → fires.
        """
        claim = ClinicalClaim(
            text="INCEPTIV reduces chronic pain and functional disability in refractory neuropathic patients",
            intervention="INCEPTIV spinal cord stimulator",
            has_comparator=False,
            endpoints=[
                Endpoint("pain NRS", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT, True),
            ],
        )
        output = analyze(claim)
        flags = {bd.flag for bd in output.bias_flags}
        self.assertIn(BiasFlag.NO_COMPARATOR, flags)

    def test_no_comparator_suppressed_when_different_modality(self):
        """EDWARDS SAPIEN 3 pattern: single-arm, outcome claim, but the only
        alternative is open-heart surgery — HAS does not fault this (avis 7873,
        FAVORABLE, no comparator critique). NO_COMPARATOR must not fire.
        """
        claim = self._claim(ClaimLevel.C, False)
        claim.comparator_feasibility = ComparatorFeasibility.DIFFERENT_MODALITY
        flags = {bd.flag for bd in analyze(claim).bias_flags}
        self.assertNotIn(BiasFlag.NO_COMPARATOR, flags)

    def test_no_comparator_suppressed_when_no_alternative(self):
        claim = self._claim(ClaimLevel.C, False)
        claim.comparator_feasibility = ComparatorFeasibility.NO_ALTERNATIVE
        flags = {bd.flag for bd in analyze(claim).bias_flags}
        self.assertNotIn(BiasFlag.NO_COMPARATOR, flags)

    def test_no_comparator_still_fires_when_feasible(self):
        """APTA SANS CIMENT pattern: single-arm, outcome claim, but a directly
        comparable alternative (fixed-neck hip prosthesis) existed and wasn't
        used — HAS penalizes this explicitly (avis 7313, DEFAVORABLE). Must fire.
        """
        claim = self._claim(ClaimLevel.C, False)
        claim.comparator_feasibility = ComparatorFeasibility.FEASIBLE
        flags = {bd.flag for bd in analyze(claim).bias_flags}
        self.assertIn(BiasFlag.NO_COMPARATOR, flags)

    def test_no_comparator_still_fires_when_feasibility_unknown(self):
        """Default/conservative behavior: unknown feasibility still fires,
        matching pre-existing behavior when nothing more is known."""
        claim = self._claim(ClaimLevel.C, False)
        self.assertEqual(claim.comparator_feasibility, ComparatorFeasibility.UNKNOWN)
        flags = {bd.flag for bd in analyze(claim).bias_flags}
        self.assertIn(BiasFlag.NO_COMPARATOR, flags)


# ===================================================================
# Evidence parser — unit tests (sans appel LLM)
# ===================================================================

from llm_evidence_parser import (
    StudyParseResult, EndpointEvidence, enrich_claim_with_study, _parse_result,
)
from models import (
    DeviceAlignment, DeviceMatchType,
    PopulationAlignment, PopulationMatchType,
    ContextAlignment, ContextMatchType,
    CarePathwayMatch, OrganizationDependency, EligibilityShift,
)


class TestEvidenceParserMapping(unittest.TestCase):
    """Tests _parse_result() — the JSON→StudyParseResult mapping, no LLM call."""

    def _rct_json(self):
        return {
            "study_design": "RCT",
            "n_patients": 89,
            "has_comparator": True,
            "follow_up_months": 6.0,
            "study_countries": ["USA", "Germany"],
            "endpoints": [
                {"name": "IAH", "is_validated_surrogate": False, "is_independently_adjudicated": False},
            ],
            "device_alignment": {
                "device_match_type": "EXACT_DEVICE",
                "device_description_study": "INSPIRE IV UAS",
                "justification": "same device",
            },
            "population_alignment": {
                "population_match_type": "EXACT_INDICATION",
                "population_description_study": "SAHOS modéré à sévère intolérants PPC",
                "eligibility_shift": "NONE",
                "justification": "exact match",
            },
            "context_alignment": {
                "context_match_type": "PARTIALLY_COMPARABLE",
                "care_pathway_match": "PARTIAL",
                "organization_dependency": "LOW",
                "study_country": "USA",
                "justification": "US system differs from France",
            },
        }

    def test_study_design_mapped(self):
        result = _parse_result(self._rct_json(), "INSPIRE IV", "SAHOS")
        self.assertEqual(result.study_design, StudyDesign.RCT)

    def test_n_patients(self):
        result = _parse_result(self._rct_json(), "INSPIRE IV", "SAHOS")
        self.assertEqual(result.n_patients, 89)

    def test_has_comparator_true(self):
        result = _parse_result(self._rct_json(), "INSPIRE IV", "SAHOS")
        self.assertTrue(result.has_comparator)

    def test_comparator_feasibility_defaults_unknown(self):
        result = _parse_result(self._rct_json(), "INSPIRE IV", "SAHOS")
        self.assertEqual(result.comparator_feasibility, ComparatorFeasibility.UNKNOWN)

    def test_comparator_feasibility_mapped(self):
        data = dict(self._rct_json())
        data["comparator_feasibility"] = "DIFFERENT_MODALITY"
        result = _parse_result(data, "INSPIRE IV", "SAHOS")
        self.assertEqual(result.comparator_feasibility, ComparatorFeasibility.DIFFERENT_MODALITY)

    def test_follow_up_months(self):
        result = _parse_result(self._rct_json(), "INSPIRE IV", "SAHOS")
        self.assertEqual(result.follow_up_months, 6.0)

    def test_study_countries(self):
        result = _parse_result(self._rct_json(), "INSPIRE IV", "SAHOS")
        self.assertIn("USA", result.study_countries)

    def test_device_alignment_exact(self):
        result = _parse_result(self._rct_json(), "INSPIRE IV", "SAHOS")
        self.assertEqual(result.device_alignment.device_match_type, DeviceMatchType.EXACT_DEVICE)

    def test_population_alignment_exact(self):
        result = _parse_result(self._rct_json(), "INSPIRE IV", "SAHOS")
        self.assertEqual(result.population_alignment.population_match_type, PopulationMatchType.EXACT_INDICATION)

    def test_context_alignment_partially_comparable(self):
        result = _parse_result(self._rct_json(), "INSPIRE IV", "SAHOS")
        self.assertEqual(result.context_alignment.context_match_type, ContextMatchType.PARTIALLY_COMPARABLE)

    def test_context_country(self):
        result = _parse_result(self._rct_json(), "INSPIRE IV", "SAHOS")
        self.assertEqual(result.context_alignment.study_country, "USA")

    def test_endpoint_metadata(self):
        result = _parse_result(self._rct_json(), "INSPIRE IV", "SAHOS")
        self.assertEqual(len(result.endpoint_evidence), 1)
        self.assertFalse(result.endpoint_evidence[0].is_validated_surrogate)

    def test_single_arm_has_comparator_false(self):
        data = self._rct_json()
        data["study_design"] = "SINGLE_ARM"
        data["has_comparator"] = False
        result = _parse_result(data, "Device", "Indication")
        self.assertFalse(result.has_comparator)
        self.assertEqual(result.study_design, StudyDesign.EXPLORATORY)

    def test_single_arm_performance_goal_mapped_distinctly(self):
        """A pre-specified, documented performance objective must map to its
        own StudyDesign, not be collapsed into EXPLORATORY."""
        data = self._rct_json()
        data["study_design"] = "SINGLE_ARM_PERFORMANCE_GOAL"
        data["has_comparator"] = False
        result = _parse_result(data, "Device", "Indication")
        self.assertEqual(result.study_design, StudyDesign.SINGLE_ARM_PERFORMANCE_GOAL)
        self.assertNotEqual(result.study_design, StudyDesign.EXPLORATORY)

    def test_external_control_cohort_mapped_distinctly(self):
        """A single-arm study compared to an external/historical control cohort
        must map to its own StudyDesign, not be collapsed into EXPLORATORY,
        SINGLE_ARM_PERFORMANCE_GOAL, or MATCHED_OBSERVATIONAL."""
        data = self._rct_json()
        data["study_design"] = "EXTERNAL_CONTROL_COHORT"
        data["has_comparator"] = True
        result = _parse_result(data, "Device", "Indication")
        self.assertEqual(result.study_design, StudyDesign.EXTERNAL_CONTROL_COHORT)
        self.assertNotEqual(result.study_design, StudyDesign.EXPLORATORY)
        self.assertNotEqual(result.study_design, StudyDesign.SINGLE_ARM_PERFORMANCE_GOAL)


class TestEnrichClaim(unittest.TestCase):
    """Tests enrich_claim_with_study() — merging StudyParseResult into ClinicalClaim."""

    def _base_claim(self):
        return ClinicalClaim(
            text="INSPIRE IV réduit l'IAH chez les patients SAHOS",
            intervention="INSPIRE IV",
            endpoints=[
                Endpoint("IAH", EndpointNature.OBJECTIVE, CausalRole.MEDIATED, True),
            ],
        )

    def _rct_result(self):
        return StudyParseResult(
            study_design=StudyDesign.RCT,
            n_patients=89,
            has_comparator=True,
            follow_up_months=6.0,
            study_countries=["USA"],
            endpoint_evidence=[
                EndpointEvidence(name="IAH", is_validated_surrogate=False, is_independently_adjudicated=False),
            ],
            device_alignment=DeviceAlignment(
                device_match_type=DeviceMatchType.EXACT_DEVICE,
                device_description_claim="INSPIRE IV",
                device_description_study="INSPIRE IV UAS",
            ),
            population_alignment=PopulationAlignment(
                population_match_type=PopulationMatchType.EXACT_INDICATION,
                population_description_claim="SAHOS modéré à sévère",
                population_description_study="SAHOS modéré à sévère intolérants PPC",
            ),
            context_alignment=ContextAlignment(
                context_match_type=ContextMatchType.PARTIALLY_COMPARABLE,
                care_pathway_match=CarePathwayMatch.PARTIAL,
                organization_dependency=OrganizationDependency.LOW,
                study_country="USA",
            ),
        )

    def test_study_metadata_written(self):
        claim = enrich_claim_with_study(self._base_claim(), self._rct_result())
        self.assertEqual(claim.n_patients, 89)
        self.assertEqual(claim.follow_up_months, 6.0)
        self.assertTrue(claim.has_comparator)

    def test_cas_alignment_wired(self):
        claim = enrich_claim_with_study(self._base_claim(), self._rct_result())
        self.assertIsNotNone(claim.device_alignment)
        self.assertIsNotNone(claim.population_alignment)
        self.assertIsNotNone(claim.context_alignment)

    def test_cas_runs_after_enrichment(self):
        from engine import analyze
        claim = enrich_claim_with_study(self._base_claim(), self._rct_result())
        output = analyze(claim)
        self.assertIsNotNone(output.cas_output)

    def test_cas_verdict_partially_comparable(self):
        from engine import analyze
        claim = enrich_claim_with_study(self._base_claim(), self._rct_result())
        output = analyze(claim)
        self.assertIn(output.cas_output.verdict, [CASVerdict.ACCEPTABLE, CASVerdict.WEAK_EVIDENCE])

    def test_endpoint_surrogate_enriched(self):
        result = self._rct_result()
        result.endpoint_evidence[0].is_validated_surrogate = True
        claim = enrich_claim_with_study(self._base_claim(), result)
        self.assertTrue(claim.endpoints[0].is_validated_surrogate)

    def test_no_comparator_fires_after_enrichment(self):
        from engine import analyze
        result = self._rct_result()
        result.has_comparator = False
        claim = ClinicalClaim(
            text="Device réduit la mortalité",
            intervention="Device",
            level=ClaimLevel.C,
            endpoints=[
                Endpoint("mortalité", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True),
            ],
        )
        enrich_claim_with_study(claim, result)
        output = analyze(claim)
        flags = {bd.flag for bd in output.bias_flags}
        self.assertIn(BiasFlag.NO_COMPARATOR, flags)

    def test_countries_written(self):
        claim = enrich_claim_with_study(self._base_claim(), self._rct_result())
        self.assertIn("USA", claim.study_countries)


class TestStudyObject(unittest.TestCase):
    """Tests for StudyObject, ComparisonReport and compare_claim_to_study()."""

    def _make_study(self, **kwargs):
        from study_object import (
            AnalysisSet, BlindingLevel, CareSetting, ComparatorType,
            FundingType, StudyObject,
        )
        defaults = dict(
            acronym="TEST",
            study_design=StudyDesign.RCT,
            is_randomized=True,
            blinding_level=BlindingLevel.DOUBLE_BLIND,
            has_comparator=True,
            comparator_type=ComparatorType.SHAM,
            n_patients=100,
            follow_up_months=12.0,
            study_countries=["France"],
            primary_endpoint_met=True,
        )
        defaults.update(kwargs)
        return StudyObject(**defaults)

    def _make_claim(self, level=ClaimLevel.C):
        return ClinicalClaim(
            text="Device réduit la mortalité cardiovasculaire",
            intervention="MyDevice",
            level=level,
            endpoints=[
                Endpoint("mortalité CV", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, True),
            ],
        )

    # --- StudyObject basics ---

    def test_study_object_defaults(self):
        from study_object import StudyObject, BlindingLevel, ComparatorType, FundingType
        obj = StudyObject()
        self.assertIsNone(obj.study_design)
        self.assertEqual(obj.blinding_level, BlindingLevel.UNKNOWN)
        self.assertEqual(obj.comparator_type, ComparatorType.UNKNOWN)
        self.assertEqual(obj.funding_type, FundingType.UNKNOWN)
        self.assertEqual(obj.endpoints, [])
        self.assertEqual(obj.study_countries, [])

    def test_study_object_to_dict_complete(self):
        from study_object import StudyEndpoint, ResultDirection
        study = self._make_study()
        study.endpoints = [
            StudyEndpoint(
                name="mortalité CV",
                is_primary=True,
                is_independently_adjudicated=True,
                result_direction=ResultDirection.IMPROVED,
                reached_significance=True,
            )
        ]
        d = study.to_dict()
        self.assertEqual(d["study_design"], "RCT")
        self.assertTrue(d["is_randomized"])
        self.assertEqual(d["blinding_level"], "DOUBLE_BLIND")
        self.assertEqual(d["n_patients"], 100)
        self.assertEqual(len(d["endpoints"]), 1)
        self.assertTrue(d["endpoints"][0]["is_independently_adjudicated"])
        self.assertEqual(d["endpoints"][0]["result_direction"], "IMPROVED")

    def test_study_endpoint_to_dict(self):
        from study_object import StudyEndpoint, ResultDirection
        ep = StudyEndpoint(
            name="IAH", is_primary=True, time_point="3 mois",
            is_validated_surrogate=False, is_independently_adjudicated=False,
            result_direction=ResultDirection.IMPROVED, reached_significance=True,
        )
        d = ep.to_dict()
        self.assertEqual(d["name"], "IAH")
        self.assertTrue(d["is_primary"])
        self.assertEqual(d["time_point"], "3 mois")
        self.assertTrue(d["reached_significance"])

    # --- _parse_study_object_result mapping ---

    def test_parse_study_object_result_basic(self):
        from llm_evidence_parser import _parse_study_object_result
        from study_object import BlindingLevel, ComparatorType, FundingType, AnalysisSet, CareSetting
        data = {
            "acronym": "EFFECT",
            "title": "Titre complet",
            "publication_year": 2022,
            "registration_id": "NCT12345",
            "funding_type": "INDUSTRY",
            "study_design": "RCT",
            "is_randomized": True,
            "blinding_level": "DOUBLE_BLIND",
            "who_is_blinded": ["patient", "assessor"],
            "allocation_concealment": True,
            "has_comparator": True,
            "comparator_type": "SHAM",
            "comparator_description": "sham CPAP",
            "n_patients": 244,
            "age_min": 18.0,
            "age_max": 80.0,
            "key_inclusion_criteria": ["SAHOS sévère", "IAH > 30/h"],
            "key_exclusion_criteria": ["BPCO"],
            "device_studied": "AirSense 10",
            "care_setting": "HOME",
            "follow_up_months": 12.0,
            "longest_follow_up_months": 24.0,
            "dropout_rate_pct": 8.5,
            "endpoints": [
                {
                    "name": "IAH",
                    "is_primary": True,
                    "time_point": "3 mois",
                    "is_validated_surrogate": False,
                    "is_independently_adjudicated": False,
                    "result_direction": "IMPROVED",
                    "reached_significance": True,
                }
            ],
            "primary_analysis_set": "ITT",
            "sample_size_calculation_provided": True,
            "primary_endpoint_met": True,
            "key_safety_signals": ["inconfort masque"],
            "device_alignment": {
                "device_match_type": "EXACT_DEVICE",
                "device_description_study": "AirSense 10",
                "justification": "même dispositif",
            },
            "population_alignment": {
                "population_match_type": "EXACT_INDICATION",
                "population_description_study": "SAHOS sévère",
                "eligibility_shift": "NONE",
                "justification": "population identique",
            },
            "context_alignment": {
                "context_match_type": "SAME_HEALTHCARE_SYSTEM",
                "care_pathway_match": "YES",
                "organization_dependency": "LOW",
                "study_country": "France",
                "justification": "étude française",
            },
        }
        obj = _parse_study_object_result(data, "AirSense 10", "SAHOS sévère")
        self.assertEqual(obj.acronym, "EFFECT")
        self.assertEqual(obj.publication_year, 2022)
        self.assertEqual(obj.funding_type, FundingType.INDUSTRY)
        self.assertEqual(obj.study_design, StudyDesign.RCT)
        self.assertTrue(obj.is_randomized)
        self.assertEqual(obj.blinding_level, BlindingLevel.DOUBLE_BLIND)
        self.assertEqual(obj.who_is_blinded, ["patient", "assessor"])
        self.assertTrue(obj.allocation_concealment)
        self.assertTrue(obj.has_comparator)
        self.assertEqual(obj.comparator_type, ComparatorType.SHAM)
        self.assertEqual(obj.n_patients, 244)
        self.assertAlmostEqual(obj.age_min, 18.0)
        self.assertEqual(obj.device_studied, "AirSense 10")
        self.assertEqual(obj.care_setting, CareSetting.HOME)
        self.assertAlmostEqual(obj.follow_up_months, 12.0)
        self.assertAlmostEqual(obj.dropout_rate_pct, 8.5)
        self.assertEqual(len(obj.endpoints), 1)
        self.assertEqual(obj.endpoints[0].name, "IAH")
        self.assertTrue(obj.endpoints[0].is_primary)
        self.assertEqual(obj.primary_analysis_set, AnalysisSet.ITT)
        self.assertTrue(obj.sample_size_calculation_provided)
        self.assertTrue(obj.primary_endpoint_met)
        self.assertEqual(obj.key_safety_signals, ["inconfort masque"])
        self.assertIsNotNone(obj.device_alignment)
        self.assertIsNotNone(obj.population_alignment)
        self.assertIsNotNone(obj.context_alignment)

    def test_parse_study_object_result_new_gap_fields_mapped(self):
        from llm_evidence_parser import _parse_study_object_result
        data = {
            "concomitant_treatments_present": True,
            "concomitant_treatments_controlled": False,
            "concomitant_treatments_description": "hypnotiques non décrits",
            "performance_goal_clinically_justified": False,
            "endpoint_hierarchy_prespecified": True,
        }
        obj = _parse_study_object_result(data, "Device", "Indication")
        self.assertTrue(obj.concomitant_treatments_present)
        self.assertFalse(obj.concomitant_treatments_controlled)
        self.assertEqual(obj.concomitant_treatments_description, "hypnotiques non décrits")
        self.assertFalse(obj.performance_goal_clinically_justified)
        self.assertTrue(obj.endpoint_hierarchy_prespecified)

    def test_parse_study_object_result_empty_data(self):
        from llm_evidence_parser import _parse_study_object_result
        from study_object import BlindingLevel, ComparatorType, FundingType
        obj = _parse_study_object_result({}, "Device", "Indication")
        self.assertEqual(obj.blinding_level, BlindingLevel.UNKNOWN)
        self.assertEqual(obj.comparator_type, ComparatorType.UNKNOWN)
        self.assertEqual(obj.funding_type, FundingType.UNKNOWN)
        self.assertIsNone(obj.study_design)
        self.assertIsNone(obj.n_patients)
        self.assertEqual(obj.endpoints, [])

    # --- compare_claim_to_study ---

    def test_compare_no_gaps_exact_alignment(self):
        from study_object import compare_claim_to_study, OverallRisk, BlindingLevel
        study = self._make_study(
            blinding_level=BlindingLevel.DOUBLE_BLIND,
            is_multicentric=True,
            device_alignment=DeviceAlignment(
                device_match_type=DeviceMatchType.EXACT_DEVICE,
                device_description_claim="MyDevice",
                device_description_study="MyDevice",
            ),
            population_alignment=PopulationAlignment(
                population_match_type=PopulationMatchType.EXACT_INDICATION,
                population_description_claim="Indication",
                population_description_study="Indication",
                eligibility_shift=EligibilityShift.NONE,
            ),
            context_alignment=ContextAlignment(
                context_match_type=ContextMatchType.SAME_HEALTHCARE_SYSTEM,
                care_pathway_match=CarePathwayMatch.YES,
                organization_dependency=OrganizationDependency.LOW,
                study_country="France",
            ),
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        self.assertEqual(report.overall_risk, OverallRisk.LOW)
        device_gaps = [g for g in report.gaps if g.dimension == "device"]
        self.assertEqual(device_gaps, [])

    def test_compare_different_device_critical(self):
        from study_object import compare_claim_to_study, OverallRisk
        study = self._make_study(
            device_alignment=DeviceAlignment(
                device_match_type=DeviceMatchType.DIFFERENT_DEVICE,
                device_description_claim="MyDevice",
                device_description_study="OtherDevice",
                justification="dispositifs fondamentalement différents",
            ),
        )
        report = compare_claim_to_study(self._make_claim(), study)
        device_gaps = [g for g in report.gaps if g.dimension == "device"]
        self.assertEqual(len(device_gaps), 1)
        self.assertEqual(device_gaps[0].severity, "CRITICAL")
        self.assertEqual(report.overall_risk, OverallRisk.CRITICAL)

    def test_compare_same_family_medium_gap(self):
        from study_object import compare_claim_to_study
        study = self._make_study(
            device_alignment=DeviceAlignment(
                device_match_type=DeviceMatchType.SAME_FAMILY,
                device_description_claim="MyDevice v2",
                device_description_study="MyDevice v1",
            ),
        )
        report = compare_claim_to_study(self._make_claim(), study)
        device_gaps = [g for g in report.gaps if g.dimension == "device"]
        self.assertEqual(device_gaps[0].severity, "MEDIUM")

    def test_compare_proxy_device_high_gap(self):
        """PROXY_DEVICE (other manufacturer, analogous device) must NOT be scored
        like SAME_FAMILY. Cf. avis CNEDiMTS 7425 (SCEWO BRO / TOPCHAIR-S, different
        manufacturer, rejected — SA insuffisant) and avis INCEPTIV (Medtronic), which
        bridges freely from its own predecessor INTELLIS (SAME_FAMILY) but explicitly
        refuses to extrapolate from EVOKE (Saluda, PROXY_DEVICE) despite the same
        closed-loop mechanism."""
        from study_object import compare_claim_to_study
        study = self._make_study(
            device_alignment=DeviceAlignment(
                device_match_type=DeviceMatchType.PROXY_DEVICE,
                device_description_claim="SCEWO BRO",
                device_description_study="TOPCHAIR-S",
                justification="autre fabricant, dispositif analogue mais non extrapolable",
            ),
        )
        report = compare_claim_to_study(self._make_claim(), study)
        device_gaps = [g for g in report.gaps if g.dimension == "device"]
        self.assertEqual(len(device_gaps), 1)
        self.assertEqual(device_gaps[0].severity, "HIGH")

    def test_compare_no_comparator_high_gap_c_claim(self):
        from study_object import compare_claim_to_study
        study = self._make_study(has_comparator=False)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        no_comp_gaps = [
            g for g in report.gaps
            if g.dimension == "design" and "comparateur" in g.description.lower()
        ]
        self.assertGreater(len(no_comp_gaps), 0)
        self.assertEqual(no_comp_gaps[0].severity, "HIGH")

    def test_compare_no_comparator_silent_for_a_claim(self):
        from study_object import compare_claim_to_study
        study = self._make_study(has_comparator=False)
        claim = ClinicalClaim(
            text="Device améliore le flux sanguin",
            intervention="MyDevice",
            level=ClaimLevel.A,
            endpoints=[
                Endpoint("débit sanguin", EndpointNature.OBJECTIVE, CausalRole.MEDIATED, True),
            ],
        )
        report = compare_claim_to_study(claim, study)
        no_comp_gaps = [
            g for g in report.gaps
            if g.dimension == "design" and "comparateur" in g.description.lower()
        ]
        self.assertEqual(no_comp_gaps, [])

    def test_compare_no_comparator_downgraded_when_different_modality(self):
        """EDWARDS SAPIEN 3 pattern (avis 7873): single-arm vs. performance
        objective, only alternative is open-heart surgery — HAS did not
        penalize this as a comparator gap. Severity must drop to LOW, not HIGH.
        """
        from study_object import compare_claim_to_study
        study = self._make_study(has_comparator=False, comparator_feasibility=ComparatorFeasibility.DIFFERENT_MODALITY)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        no_comp_gaps = [
            g for g in report.gaps
            if g.dimension == "design" and "comparateur" in g.description.lower()
        ]
        self.assertGreater(len(no_comp_gaps), 0)
        self.assertEqual(no_comp_gaps[0].severity, "LOW")

    def test_compare_no_comparator_downgraded_when_no_alternative(self):
        from study_object import compare_claim_to_study
        study = self._make_study(has_comparator=False, comparator_feasibility=ComparatorFeasibility.NO_ALTERNATIVE)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        no_comp_gaps = [
            g for g in report.gaps
            if g.dimension == "design" and "comparateur" in g.description.lower()
        ]
        self.assertGreater(len(no_comp_gaps), 0)
        self.assertEqual(no_comp_gaps[0].severity, "LOW")

    def test_compare_no_comparator_still_high_when_feasible(self):
        """APTA SANS CIMENT pattern (avis 7313): single-arm, but a directly
        comparable alternative existed and wasn't used — HAS penalized this
        explicitly. Severity must remain HIGH.
        """
        from study_object import compare_claim_to_study
        study = self._make_study(has_comparator=False, comparator_feasibility=ComparatorFeasibility.FEASIBLE)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        no_comp_gaps = [
            g for g in report.gaps
            if g.dimension == "design" and "comparateur" in g.description.lower()
        ]
        self.assertGreater(len(no_comp_gaps), 0)
        self.assertEqual(no_comp_gaps[0].severity, "HIGH")

    def test_compare_exploratory_c_claim_critical(self):
        from study_object import compare_claim_to_study, OverallRisk
        study = self._make_study(study_design=StudyDesign.EXPLORATORY, has_comparator=False)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        exp_gaps = [g for g in report.gaps if "exploratoire" in g.description.lower()]
        self.assertGreater(len(exp_gaps), 0)
        self.assertEqual(exp_gaps[0].severity, "CRITICAL")
        self.assertEqual(report.overall_risk, OverallRisk.CRITICAL)

    def test_compare_single_arm_performance_goal_not_exploratory(self):
        """EDWARDS SAPIEN 3 pattern (avis 7873): 61-patient pivotal study,
        primary endpoint vs. a documented pre-specified performance objective —
        HAS accepted this (SA Suffisant, ASA II), it is not treated as
        exploratory/pilot. Must not produce a CRITICAL 'exploratoire' gap.
        """
        from study_object import compare_claim_to_study
        study = self._make_study(
            study_design=StudyDesign.SINGLE_ARM_PERFORMANCE_GOAL,
            has_comparator=False,
            comparator_feasibility=ComparatorFeasibility.DIFFERENT_MODALITY,
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        exploratory_gaps = [g for g in report.gaps if "exploratoire" in g.description.lower()]
        self.assertEqual(exploratory_gaps, [])

    def test_compare_single_arm_performance_goal_high_not_critical(self):
        from study_object import compare_claim_to_study
        study = self._make_study(
            study_design=StudyDesign.SINGLE_ARM_PERFORMANCE_GOAL,
            has_comparator=False,
            comparator_feasibility=ComparatorFeasibility.DIFFERENT_MODALITY,
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        perf_goal_gaps = [g for g in report.gaps if "objectif de performance" in g.description.lower()]
        self.assertGreater(len(perf_goal_gaps), 0)
        self.assertEqual(perf_goal_gaps[0].severity, "HIGH")

    # --- External control cohort (single-arm vs. historical/registry comparator) ---

    def test_compare_external_control_cohort_high(self):
        from study_object import compare_claim_to_study
        study = self._make_study(
            study_design=StudyDesign.EXTERNAL_CONTROL_COHORT,
            is_randomized=False,
            has_comparator=True,
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        ecc_gaps = [g for g in report.gaps if "contrôle externe" in g.description.lower()]
        self.assertGreater(len(ecc_gaps), 0)
        self.assertEqual(ecc_gaps[0].severity, "HIGH")

    def test_compare_external_control_cohort_not_double_flagged_as_generic_nonrandomized(self):
        """The dedicated external-control-cohort gap must replace, not stack with,
        the generic non-randomized-comparative-study gap."""
        from study_object import compare_claim_to_study
        study = self._make_study(
            study_design=StudyDesign.EXTERNAL_CONTROL_COHORT,
            is_randomized=False,
            has_comparator=True,
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        generic_gaps = [
            g for g in report.gaps
            if "comparative non randomisée" in g.description.lower()
        ]
        self.assertEqual(generic_gaps, [])

    def test_compare_external_control_cohort_irrelevant_for_rct(self):
        from study_object import compare_claim_to_study
        study = self._make_study(study_design=StudyDesign.RCT)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        ecc_gaps = [g for g in report.gaps if "contrôle externe" in g.description.lower()]
        self.assertEqual(ecc_gaps, [])

    def test_compare_open_label_subjective_primary_high(self):
        from study_object import compare_claim_to_study, BlindingLevel
        study = self._make_study(blinding_level=BlindingLevel.OPEN_LABEL)
        claim = ClinicalClaim(
            text="Device réduit la douleur",
            intervention="MyDevice",
            level=ClaimLevel.C,
            endpoints=[
                Endpoint("EVA douleur", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT, True),
            ],
        )
        report = compare_claim_to_study(claim, study)
        sham_gaps = [
            g for g in report.gaps
            if "subjectif" in g.description.lower() or "PRO" in g.description
        ]
        self.assertGreater(len(sham_gaps), 0)
        self.assertEqual(sham_gaps[0].severity, "HIGH")

    def test_compare_single_blind_patient_blinded_primary_medium(self):
        """MAIOREGEN PRIME pattern (avis CNEDiMTS 7282): patient blinded to allocation
        (SINGLE_BLIND) mitigates but doesn't eliminate expectation bias on a PRO —
        residual-risk MEDIUM, not the full HIGH given to a fully open design.
        """
        from study_object import compare_claim_to_study, BlindingLevel
        study = self._make_study(
            blinding_level=BlindingLevel.SINGLE_BLIND,
            who_is_blinded=["patient"],
        )
        claim = ClinicalClaim(
            text="Device réduit la douleur",
            intervention="MyDevice",
            level=ClaimLevel.C,
            endpoints=[
                Endpoint("EVA douleur", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT, True),
            ],
        )
        report = compare_claim_to_study(claim, study)
        sham_gaps = [
            g for g in report.gaps
            if "subjectif" in g.description.lower() or "PRO" in g.description
        ]
        self.assertGreater(len(sham_gaps), 0)
        self.assertEqual(sham_gaps[0].severity, "MEDIUM")

    def test_compare_single_blind_assessor_only_primary_still_high(self):
        """SINGLE_BLIND where the PATIENT is not the one blinded (e.g. only the
        assessor is) doesn't mitigate the mechanism this gap targets — stays HIGH.
        """
        from study_object import compare_claim_to_study, BlindingLevel
        study = self._make_study(
            blinding_level=BlindingLevel.SINGLE_BLIND,
            who_is_blinded=["assessor"],
        )
        claim = ClinicalClaim(
            text="Device réduit la douleur",
            intervention="MyDevice",
            level=ClaimLevel.C,
            endpoints=[
                Endpoint("EVA douleur", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT, True),
            ],
        )
        report = compare_claim_to_study(claim, study)
        sham_gaps = [
            g for g in report.gaps
            if "subjectif" in g.description.lower() or "PRO" in g.description
        ]
        self.assertGreater(len(sham_gaps), 0)
        self.assertEqual(sham_gaps[0].severity, "HIGH")

    # --- Subgroup-only significance of unconfirmed pre-specification (MAIOREGEN PRIME pattern, avis 7282) ---

    def test_compare_subgroup_only_significant_unconfirmed_high(self):
        from study_object import compare_claim_to_study
        study = self._make_study(
            subgroup_only_significant=True,
            subgroup_prespecified=None,
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        subgroup_gaps = [g for g in report.gaps if "sous-groupe" in g.description.lower()]
        self.assertGreater(len(subgroup_gaps), 0)
        self.assertEqual(subgroup_gaps[0].severity, "HIGH")

    def test_compare_subgroup_fires_when_explicitly_posthoc(self):
        from study_object import compare_claim_to_study
        study = self._make_study(
            subgroup_only_significant=True,
            subgroup_prespecified=False,
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        subgroup_gaps = [g for g in report.gaps if "sous-groupe" in g.description.lower()]
        self.assertGreater(len(subgroup_gaps), 0)
        self.assertEqual(subgroup_gaps[0].severity, "HIGH")

    def test_compare_subgroup_silent_when_prespecified(self):
        from study_object import compare_claim_to_study
        study = self._make_study(
            subgroup_only_significant=True,
            subgroup_prespecified=True,
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        subgroup_gaps = [g for g in report.gaps if "sous-groupe" in g.description.lower()]
        self.assertEqual(subgroup_gaps, [])

    def test_compare_subgroup_silent_when_no_subgroup_signal(self):
        from study_object import compare_claim_to_study
        study = self._make_study(subgroup_only_significant=False)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        subgroup_gaps = [g for g in report.gaps if "sous-groupe" in g.description.lower()]
        self.assertEqual(subgroup_gaps, [])

    # --- Confounding / uncontrolled co-intervention (SOMNIO pattern, avis 7781) ---

    def test_compare_confounding_uncontrolled_high(self):
        """SOMNIO pattern (avis CNEDiMTS 7781, SA Insuffisant): concomitant hypnotic
        treatments present in the population, neither described nor controlled — HAS's
        real objection was that the observed effect could not be attributed to the
        device, not an endpoint-validity issue.
        """
        from study_object import compare_claim_to_study
        study = self._make_study(
            concomitant_treatments_present=True,
            concomitant_treatments_controlled=False,
            concomitant_treatments_description="traitements hypnotiques concomitants non décrits",
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        confounding_gaps = [g for g in report.gaps if "confusion" in g.description.lower()]
        self.assertGreater(len(confounding_gaps), 0)
        self.assertEqual(confounding_gaps[0].severity, "HIGH")

    def test_compare_confounding_silent_when_controlled(self):
        from study_object import compare_claim_to_study
        study = self._make_study(
            concomitant_treatments_present=True,
            concomitant_treatments_controlled=True,
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        confounding_gaps = [g for g in report.gaps if "confusion" in g.description.lower()]
        self.assertEqual(confounding_gaps, [])

    def test_compare_confounding_silent_when_absent(self):
        from study_object import compare_claim_to_study
        study = self._make_study(concomitant_treatments_present=False)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        confounding_gaps = [g for g in report.gaps if "confusion" in g.description.lower()]
        self.assertEqual(confounding_gaps, [])

    # --- Baseline group imbalance (MAIOREGEN PRIME pattern, avis 7282) ---

    def test_compare_baseline_imbalance_high(self):
        from study_object import compare_claim_to_study
        study = self._make_study(
            baseline_groups_comparable=False,
            baseline_imbalance_description="plus de lésions rotuliennes dans le groupe comparateur",
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        imbalance_gaps = [g for g in report.gaps if "comparables à l'inclusion" in g.description.lower()]
        self.assertGreater(len(imbalance_gaps), 0)
        self.assertEqual(imbalance_gaps[0].severity, "HIGH")

    def test_compare_baseline_imbalance_silent_when_comparable(self):
        from study_object import compare_claim_to_study
        study = self._make_study(baseline_groups_comparable=True)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        imbalance_gaps = [g for g in report.gaps if "comparables à l'inclusion" in g.description.lower()]
        self.assertEqual(imbalance_gaps, [])

    def test_compare_baseline_imbalance_silent_when_unstated(self):
        from study_object import compare_claim_to_study
        study = self._make_study()  # baseline_groups_comparable defaults to None
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        imbalance_gaps = [g for g in report.gaps if "comparables à l'inclusion" in g.description.lower()]
        self.assertEqual(imbalance_gaps, [])

    def test_compare_baseline_imbalance_silent_when_no_comparator(self):
        from study_object import compare_claim_to_study
        study = self._make_study(has_comparator=False, baseline_groups_comparable=False)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        imbalance_gaps = [g for g in report.gaps if "comparables à l'inclusion" in g.description.lower()]
        self.assertEqual(imbalance_gaps, [])

    # --- Primary analysis set declared per-protocol rather than ITT (protocol-review stage) ---

    def test_compare_analysis_set_per_protocol_high(self):
        from study_object import compare_claim_to_study, AnalysisSet
        study = self._make_study(primary_analysis_set=AnalysisSet.PP)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        pp_gaps = [g for g in report.gaps if "intention de traiter" in g.description.lower()]
        self.assertGreater(len(pp_gaps), 0)
        self.assertEqual(pp_gaps[0].severity, "HIGH")

    def test_compare_analysis_set_silent_when_itt(self):
        from study_object import compare_claim_to_study, AnalysisSet
        study = self._make_study(primary_analysis_set=AnalysisSet.ITT)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        pp_gaps = [g for g in report.gaps if "intention de traiter" in g.description.lower()]
        self.assertEqual(pp_gaps, [])

    def test_compare_analysis_set_silent_when_unknown(self):
        from study_object import compare_claim_to_study
        study = self._make_study()  # primary_analysis_set defaults to UNKNOWN
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        pp_gaps = [g for g in report.gaps if "intention de traiter" in g.description.lower()]
        self.assertEqual(pp_gaps, [])

    def test_compare_analysis_set_silent_when_mitt(self):
        """mITT (modified ITT) is a commonly-accepted ITT-adjacent choice, not a red flag."""
        from study_object import compare_claim_to_study, AnalysisSet
        study = self._make_study(primary_analysis_set=AnalysisSet.mITT)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        pp_gaps = [g for g in report.gaps if "intention de traiter" in g.description.lower()]
        self.assertEqual(pp_gaps, [])

    def test_compare_analysis_set_silent_when_fas(self):
        """FAS (Full Analysis Set) is defined to stay maximally close to ITT (ICH E9), not a red flag."""
        from study_object import compare_claim_to_study, AnalysisSet
        study = self._make_study(primary_analysis_set=AnalysisSet.FAS)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        pp_gaps = [g for g in report.gaps if "intention de traiter" in g.description.lower()]
        self.assertEqual(pp_gaps, [])

    def test_compare_analysis_set_silent_on_mechanism_claim(self):
        from study_object import compare_claim_to_study, AnalysisSet
        study = self._make_study(primary_analysis_set=AnalysisSet.PP)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.A), study)
        pp_gaps = [g for g in report.gaps if "intention de traiter" in g.description.lower()]
        self.assertEqual(pp_gaps, [])

    # --- Endpoint multiplicity without hierarchy (ENTERRA II pattern, avis 7254) ---

    def test_compare_endpoint_multiplicity_no_hierarchy_medium(self):
        """ENTERRA II pattern (avis CNEDiMTS 7254, accepted but downgraded ASA):
        multiple co-primary endpoints without a pre-specified statistical hierarchy.
        """
        from study_object import compare_claim_to_study, StudyEndpoint
        study = self._make_study()
        study.endpoints = [
            StudyEndpoint(name="fréquence des vomissements", is_primary=True),
            StudyEndpoint(name="sévérité des symptômes GCSI", is_primary=True),
        ]
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        multiplicity_gaps = [g for g in report.gaps if "multiplicité" in g.description.lower()]
        self.assertGreater(len(multiplicity_gaps), 0)
        self.assertEqual(multiplicity_gaps[0].severity, "MEDIUM")

    def test_compare_endpoint_multiplicity_silent_with_hierarchy(self):
        from study_object import compare_claim_to_study, StudyEndpoint
        study = self._make_study(endpoint_hierarchy_prespecified=True)
        study.endpoints = [
            StudyEndpoint(name="fréquence des vomissements", is_primary=True),
            StudyEndpoint(name="sévérité des symptômes GCSI", is_primary=True),
        ]
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        multiplicity_gaps = [g for g in report.gaps if "multiplicité" in g.description.lower()]
        self.assertEqual(multiplicity_gaps, [])

    def test_compare_endpoint_multiplicity_silent_single_primary(self):
        from study_object import compare_claim_to_study, StudyEndpoint
        study = self._make_study()
        study.endpoints = [StudyEndpoint(name="mortalité", is_primary=True)]
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        multiplicity_gaps = [g for g in report.gaps if "multiplicité" in g.description.lower()]
        self.assertEqual(multiplicity_gaps, [])

    # --- Performance goal without clinical justification (SAPIEN 3/ALTERRA pattern, avis 7873) ---

    def test_compare_performance_goal_unjustified_medium(self):
        """SAPIEN 3/ALTERRA pattern (avis CNEDiMTS 7873): accepted single-arm pivotal
        design, but HAS's residual critique was the absence of documented clinical
        justification for the performance objective's threshold itself.
        """
        from study_object import compare_claim_to_study
        study = self._make_study(
            study_design=StudyDesign.SINGLE_ARM_PERFORMANCE_GOAL,
            has_comparator=False,
            comparator_feasibility=ComparatorFeasibility.DIFFERENT_MODALITY,
            performance_goal_clinically_justified=False,
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        threshold_gaps = [g for g in report.gaps if "seuil de succès" in g.description.lower()]
        self.assertGreater(len(threshold_gaps), 0)
        self.assertEqual(threshold_gaps[0].severity, "MEDIUM")

    def test_compare_performance_goal_silent_when_justified(self):
        from study_object import compare_claim_to_study
        study = self._make_study(
            study_design=StudyDesign.SINGLE_ARM_PERFORMANCE_GOAL,
            has_comparator=False,
            comparator_feasibility=ComparatorFeasibility.DIFFERENT_MODALITY,
            performance_goal_clinically_justified=True,
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        threshold_gaps = [g for g in report.gaps if "seuil de succès" in g.description.lower()]
        self.assertEqual(threshold_gaps, [])

    def test_compare_performance_goal_irrelevant_for_rct(self):
        from study_object import compare_claim_to_study
        study = self._make_study(study_design=StudyDesign.RCT)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        threshold_gaps = [g for g in report.gaps if "seuil de succès" in g.description.lower()]
        self.assertEqual(threshold_gaps, [])

    def test_compare_has_critique_always_populated(self):
        from study_object import compare_claim_to_study
        study = self._make_study()
        report = compare_claim_to_study(self._make_claim(), study)
        self.assertGreater(len(report.has_critique_simulation), 0)
        for critique in report.has_critique_simulation:
            self.assertIsInstance(critique, str)
            self.assertGreater(len(critique), 10)

    def test_compare_repair_priority_critical_first(self):
        from study_object import compare_claim_to_study
        study = self._make_study(
            has_comparator=False,
            device_alignment=DeviceAlignment(
                device_match_type=DeviceMatchType.DIFFERENT_DEVICE,
                device_description_claim="MyDevice",
                device_description_study="OtherDevice",
            ),
        )
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        self.assertGreater(len(report.repair_priority), 1)
        # CRITICAL device gap must appear before HIGH no-comparator gap
        self.assertIn("OtherDevice", report.repair_priority[0])

    def test_compare_report_to_dict_structure(self):
        from study_object import compare_claim_to_study
        study = self._make_study(has_comparator=False)
        report = compare_claim_to_study(self._make_claim(level=ClaimLevel.C), study)
        d = report.to_dict()
        self.assertIn("gaps", d)
        self.assertIn("overall_risk", d)
        self.assertIn("has_critique_simulation", d)
        self.assertIn("repair_priority", d)
        self.assertIn(d["overall_risk"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        for gap in d["gaps"]:
            self.assertIn("dimension", gap)
            self.assertIn("severity", gap)
            self.assertIn("description", gap)
            self.assertIn("has_critique", gap)

    # --- enrich_claim_with_study_object ---

    def test_enrich_claim_from_study_object(self):
        from study_object import enrich_claim_with_study_object
        from llm_evidence_parser import _parse_study_object_result
        data = {
            "study_design": "RCT",
            "n_patients": 200,
            "has_comparator": True,
            "follow_up_months": 6.0,
            "study_countries": ["France"],
            "endpoints": [
                {
                    "name": "mortalité CV",
                    "is_primary": True,
                    "is_independently_adjudicated": True,
                    "is_validated_surrogate": False,
                    "result_direction": "IMPROVED",
                }
            ],
        }
        obj = _parse_study_object_result(data, "MyDevice", "Indication")
        claim = self._make_claim()
        enrich_claim_with_study_object(claim, obj)
        self.assertEqual(claim.study_design, StudyDesign.RCT)
        self.assertEqual(claim.n_patients, 200)
        self.assertTrue(claim.has_comparator)
        self.assertAlmostEqual(claim.follow_up_months, 6.0)
        self.assertIn("France", claim.study_countries)
        self.assertTrue(claim.endpoints[0].is_independently_adjudicated)


# ===================================================================
# TestGapRepairEngine
# ===================================================================

from gap_repair_engine import (
    GapRepairEffort, GapRepairType, repair_comparison,
)
from study_object import ClaimStudyGap, ComparisonReport, OverallRisk


def _make_comparison_report(gaps: list[ClaimStudyGap], overall: OverallRisk) -> ComparisonReport:
    return ComparisonReport(
        claim_text="Test claim",
        device_studied="TestDevice",
        gaps=gaps,
        overall_risk=overall,
        has_critique_simulation=[],
        repair_priority=[g.description for g in gaps],
    )


def _gap(dimension: str, severity: str, description: str, topic: str | None = None) -> ClaimStudyGap:
    return ClaimStudyGap(dimension=dimension, severity=severity, description=description, has_critique=None, topic=topic)


class TestGapRepairEngine(unittest.TestCase):

    def _c_claim(self) -> ClinicalClaim:
        return ClinicalClaim(
            text="Device X réduit la mortalité cardiaque",
            intervention="Device X",
            domain="cardiology",
            level=ClaimLevel.C,
            endpoints=[Endpoint("mortalité", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT, is_primary=True)],
        )

    # ------------------------------------------------------------------
    # DEVICE gaps
    # ------------------------------------------------------------------

    def test_device_different_device_critical_blocking(self):
        claim = self._c_claim()
        gaps = [_gap("device", "CRITICAL", "Dispositif étudié ≠ dispositif revendiqué. Génération différente.")]
        report = _make_comparison_report(gaps, OverallRisk.CRITICAL)
        plan = repair_comparison(report, claim)
        self.assertTrue(len(plan.non_repairable_gaps) == 1)
        self.assertFalse(plan.is_fully_repairable)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.STUDY_COMMISSION, types)
        self.assertIn(GapRepairType.CLAIM_RESTRICTION, types)

    def test_device_same_family_medium_not_blocking(self):
        claim = self._c_claim()
        gaps = [_gap("device", "MEDIUM", "Dispositif même famille génération antérieure.")]
        report = _make_comparison_report(gaps, OverallRisk.MEDIUM)
        plan = repair_comparison(report, claim)
        self.assertEqual(len(plan.non_repairable_gaps), 0)
        self.assertTrue(plan.is_fully_repairable)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.BRIDGING_STUDY, types)
        self.assertIn(GapRepairType.CLAIM_RESTRICTION, types)

    def test_device_proxy_device_high_blocking(self):
        """PROXY_DEVICE (analogous device, other manufacturer) must NOT route to
        BRIDGING_STUDY like SAME_FAMILY — HAS treats it as effectively no evidence
        (cf. SCEWO BRO avis 7425, INCEPTIV/EVOKE) : a dedicated study is required,
        and the original claim is not repairable by amendment alone."""
        claim = self._c_claim()
        gaps = [_gap("device", "HIGH", "Dispositif étudié (TOPCHAIR-S) ≠ dispositif revendiqué (SCEWO BRO). Autre fabricant.")]
        report = _make_comparison_report(gaps, OverallRisk.HIGH)
        plan = repair_comparison(report, claim)
        self.assertEqual(len(plan.non_repairable_gaps), 1)
        self.assertFalse(plan.is_fully_repairable)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.STUDY_COMMISSION, types)
        self.assertIn(GapRepairType.CLAIM_RESTRICTION, types)
        self.assertNotIn(GapRepairType.BRIDGING_STUDY, types)
        study_commission = [a for a in plan.actions if a.repair_type == GapRepairType.STUDY_COMMISSION]
        self.assertEqual(study_commission[0].effort, GapRepairEffort.HIGH)

    def test_device_claim_restriction_low_effort(self):
        claim = self._c_claim()
        gaps = [_gap("device", "CRITICAL", "Dispositif différent.")]
        report = _make_comparison_report(gaps, OverallRisk.CRITICAL)
        plan = repair_comparison(report, claim)
        low_effort = [a for a in plan.actions if a.effort == GapRepairEffort.LOW]
        self.assertTrue(len(low_effort) >= 1)
        self.assertTrue(any(a.repair_type == GapRepairType.CLAIM_RESTRICTION for a in low_effort))

    # ------------------------------------------------------------------
    # POPULATION gaps
    # ------------------------------------------------------------------

    def test_population_different_high_two_actions(self):
        claim = self._c_claim()
        gaps = [_gap("population", "HIGH", "Population totalement différente.")]
        report = _make_comparison_report(gaps, OverallRisk.HIGH)
        plan = repair_comparison(report, claim)
        self.assertFalse(plan.non_repairable_gaps)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.STUDY_COMMISSION, types)
        self.assertIn(GapRepairType.CLAIM_RESTRICTION, types)

    def test_population_medium_single_restriction(self):
        claim = self._c_claim()
        gaps = [_gap("population", "MEDIUM", "Sous-groupe âge différent.")]
        report = _make_comparison_report(gaps, OverallRisk.MEDIUM)
        plan = repair_comparison(report, claim)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].repair_type, GapRepairType.CLAIM_RESTRICTION)
        self.assertEqual(plan.actions[0].effort, GapRepairEffort.LOW)

    # ------------------------------------------------------------------
    # CONTEXT gaps
    # ------------------------------------------------------------------

    def test_context_low_transposability_action(self):
        claim = self._c_claim()
        gaps = [_gap("context", "LOW", "Étude réalisée en dehors de France.")]
        report = _make_comparison_report(gaps, OverallRisk.LOW)
        plan = repair_comparison(report, claim)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.CONTEXT_TRANSPOSABILITY, types)

    def test_context_medium_adds_study_commission(self):
        claim = self._c_claim()
        gaps = [_gap("context", "MEDIUM", "Système de santé très différent.")]
        report = _make_comparison_report(gaps, OverallRisk.MEDIUM)
        plan = repair_comparison(report, claim)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.CONTEXT_TRANSPOSABILITY, types)
        self.assertIn(GapRepairType.STUDY_COMMISSION, types)

    # ------------------------------------------------------------------
    # DESIGN gaps
    # ------------------------------------------------------------------

    def test_design_exploratory_critical_blocking(self):
        claim = self._c_claim()
        gaps = [_gap("design", "CRITICAL", "Design exploratoire (série de cas / pilote) pour revendication outcome.")]
        report = _make_comparison_report(gaps, OverallRisk.CRITICAL)
        plan = repair_comparison(report, claim)
        self.assertEqual(len(plan.non_repairable_gaps), 1)
        self.assertFalse(plan.is_fully_repairable)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.DESIGN_CONFIRMATORY, types)

    def test_design_no_comparator_high_not_blocking(self):
        claim = self._c_claim()
        gaps = [_gap("design", "HIGH", "Étude sans comparateur pour revendication d'outcome (niveau C/D). Le counterfactuel n'est pas observé.")]
        report = _make_comparison_report(gaps, OverallRisk.HIGH)
        plan = repair_comparison(report, claim)
        self.assertEqual(len(plan.non_repairable_gaps), 0)
        self.assertTrue(plan.is_fully_repairable)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.CONTROL_ARM_ADDITION, types)

    def test_design_open_label_subjective_two_actions(self):
        claim = self._c_claim()
        gaps = [_gap("design", "HIGH", "Critère principal patient-rapporté (PRO/subjectif) sans aveugle ni sham.", topic="subjective_no_blinding")]
        report = _make_comparison_report(gaps, OverallRisk.HIGH)
        plan = repair_comparison(report, claim)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.DESIGN_SHAM, types)
        self.assertIn(GapRepairType.ENDPOINT_ADDITION, types)

    def test_design_patient_blinded_medium_single_action(self):
        claim = self._c_claim()
        gaps = [_gap("design", "MEDIUM", "Critère principal patient-rapporté (PRO/subjectif), patient en aveugle du traitement mais pas de sham — risque résiduel de biais d'expectation.", topic="subjective_no_blinding")]
        report = _make_comparison_report(gaps, OverallRisk.MEDIUM)
        plan = repair_comparison(report, claim)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.DESIGN_SHAM, types)
        self.assertNotIn(GapRepairType.ENDPOINT_ADDITION, types)
        self.assertEqual(plan.actions[0].effort, GapRepairEffort.MEDIUM)

    def test_design_subgroup_confirmation_high_effort(self):
        claim = self._c_claim()
        gaps = [_gap("design", "HIGH", "Critère principal non significatif sur la population analysée ; la revendication s'appuie sur un résultat significatif dans un sous-groupe dont le caractère pré-spécifié n'est pas confirmé.", topic="subgroup_only_significant")]
        report = _make_comparison_report(gaps, OverallRisk.HIGH)
        plan = repair_comparison(report, claim)
        self.assertEqual(len(plan.non_repairable_gaps), 0)
        self.assertTrue(plan.is_fully_repairable)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.SUBGROUP_CONFIRMATION, types)
        self.assertEqual(plan.actions[0].effort, GapRepairEffort.HIGH)

    def test_design_short_followup_extension(self):
        claim = self._c_claim()
        gaps = [_gap("design", "MEDIUM", "Suivi de 2.0 mois pour revendication chaîne causale complète.", topic="follow_up_insufficient")]
        report = _make_comparison_report(gaps, OverallRisk.MEDIUM)
        plan = repair_comparison(report, claim)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.FOLLOW_UP_EXTENSION, types)
        self.assertEqual(plan.actions[0].effort, GapRepairEffort.MEDIUM)

    def test_design_confounding_not_blocking_medium_effort(self):
        claim = self._c_claim()
        gaps = [_gap("design", "HIGH", "Traitements concomitants présents dans la population d'étude, non décrits ou non contrôlés (facteur de confusion).", topic="confounding_concomitant")]
        report = _make_comparison_report(gaps, OverallRisk.HIGH)
        plan = repair_comparison(report, claim)
        self.assertEqual(len(plan.non_repairable_gaps), 0)
        self.assertTrue(plan.is_fully_repairable)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.CONFOUNDER_CONTROL, types)
        self.assertEqual(plan.actions[0].effort, GapRepairEffort.MEDIUM)

    def test_design_analysis_set_per_protocol_low_effort_not_blocking(self):
        claim = self._c_claim()
        gaps = [_gap("design", "HIGH", "Analyse primaire prévue en per-protocol plutôt qu'en intention de traiter (ITT), pour une revendication d'outcome (niveau C/D).", topic="per_protocol_not_itt")]
        report = _make_comparison_report(gaps, OverallRisk.HIGH)
        plan = repair_comparison(report, claim)
        self.assertEqual(len(plan.non_repairable_gaps), 0)
        self.assertTrue(plan.is_fully_repairable)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.ANALYSIS_SET_CORRECTION, types)
        self.assertEqual(plan.actions[0].effort, GapRepairEffort.LOW)

    def test_design_performance_goal_unjustified_low_effort(self):
        claim = self._c_claim()
        gaps = [_gap("design", "MEDIUM", "Seuil de performance pré-spécifié sans justification clinique documentée pour le seuil de succès retenu.", topic="performance_goal_unjustified")]
        report = _make_comparison_report(gaps, OverallRisk.MEDIUM)
        plan = repair_comparison(report, claim)
        self.assertTrue(plan.is_fully_repairable)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.PERFORMANCE_GOAL_JUSTIFICATION, types)
        self.assertEqual(plan.actions[0].effort, GapRepairEffort.LOW)

    # ------------------------------------------------------------------
    # ENDPOINT gaps
    # ------------------------------------------------------------------

    def test_endpoint_surrogate_two_actions(self):
        claim = self._c_claim()
        gaps = [_gap("endpoint", "HIGH", "Critère principal = surrogate non validé réglementairement dans cette indication.")]
        report = _make_comparison_report(gaps, OverallRisk.HIGH)
        plan = repair_comparison(report, claim)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.ENDPOINT_REPLACEMENT, types)
        self.assertIn(GapRepairType.SURROGATE_VALIDATION, types)

    def test_endpoint_circularity_blocking(self):
        claim = self._c_claim()
        gaps = [_gap("endpoint", "CRITICAL", "Critère principal circulaire : le dispositif mesure ce qu'il traite.")]
        report = _make_comparison_report(gaps, OverallRisk.CRITICAL)
        plan = repair_comparison(report, claim)
        self.assertFalse(plan.is_fully_repairable)
        types = [a.repair_type for a in plan.actions]
        self.assertIn(GapRepairType.ENDPOINT_REPLACEMENT, types)

    def test_endpoint_adjudication_low_effort(self):
        claim = self._c_claim()
        gaps = [_gap("endpoint", "MEDIUM", "Critère objectif principal sans adjudication indépendante documentée (pas de CEC mentionné).")]
        report = _make_comparison_report(gaps, OverallRisk.MEDIUM)
        plan = repair_comparison(report, claim)
        self.assertTrue(plan.is_fully_repairable)
        adj = [a for a in plan.actions if a.repair_type == GapRepairType.ADJUDICATION_ADDITION]
        self.assertEqual(len(adj), 1)
        self.assertEqual(adj[0].effort, GapRepairEffort.LOW)

    def test_endpoint_multiplicity_low_effort(self):
        claim = self._c_claim()
        gaps = [_gap("endpoint", "MEDIUM", "Multiplicité des critères de jugement principaux (2 critères co-primaires) sans hiérarchisation statistique pré-spécifiée.")]
        report = _make_comparison_report(gaps, OverallRisk.MEDIUM)
        plan = repair_comparison(report, claim)
        self.assertTrue(plan.is_fully_repairable)
        mult = [a for a in plan.actions if a.repair_type == GapRepairType.MULTIPLICITY_CORRECTION]
        self.assertEqual(len(mult), 1)
        self.assertEqual(mult[0].effort, GapRepairEffort.LOW)

    # ------------------------------------------------------------------
    # Sorting + summary
    # ------------------------------------------------------------------

    def test_actions_sorted_low_effort_first(self):
        claim = self._c_claim()
        gaps = [
            _gap("device", "CRITICAL", "Dispositif différent."),        # LOW (restriction) + BLOCKING
            _gap("endpoint", "MEDIUM", "Critère objectif principal sans adjudication indépendante documentée (pas de CEC mentionné)."),  # LOW
        ]
        report = _make_comparison_report(gaps, OverallRisk.CRITICAL)
        plan = repair_comparison(report, claim)
        efforts = [a.effort for a in plan.actions]
        low_indices = [i for i, e in enumerate(efforts) if e == GapRepairEffort.LOW]
        blocking_indices = [i for i, e in enumerate(efforts) if e == GapRepairEffort.BLOCKING]
        if low_indices and blocking_indices:
            self.assertLess(min(low_indices), min(blocking_indices))

    def test_fully_repairable_when_no_blocking(self):
        claim = self._c_claim()
        gaps = [
            _gap("endpoint", "MEDIUM", "Critère objectif principal sans adjudication indépendante documentée (pas de CEC mentionné)."),
            _gap("design", "MEDIUM", "Suivi de 3 mois pour revendication."),
        ]
        report = _make_comparison_report(gaps, OverallRisk.MEDIUM)
        plan = repair_comparison(report, claim)
        self.assertTrue(plan.is_fully_repairable)

    def test_not_repairable_when_exploratory(self):
        claim = self._c_claim()
        gaps = [_gap("design", "CRITICAL", "Design exploratoire (série de cas) pour revendication outcome.")]
        report = _make_comparison_report(gaps, OverallRisk.CRITICAL)
        plan = repair_comparison(report, claim)
        self.assertFalse(plan.is_fully_repairable)

    def test_repair_summary_mentions_non_repairable(self):
        claim = self._c_claim()
        gaps = [_gap("device", "CRITICAL", "Dispositif différent.")]
        report = _make_comparison_report(gaps, OverallRisk.CRITICAL)
        plan = repair_comparison(report, claim)
        self.assertIn("non réparable", plan.repair_summary)

    def test_to_dict_structure(self):
        claim = self._c_claim()
        gaps = [_gap("endpoint", "MEDIUM", "Critère objectif principal sans adjudication indépendante documentée (pas de CEC mentionné).")]
        report = _make_comparison_report(gaps, OverallRisk.MEDIUM)
        plan = repair_comparison(report, claim)
        d = plan.to_dict()
        self.assertIn("actions", d)
        self.assertIn("is_fully_repairable", d)
        self.assertIn("repair_summary", d)
        self.assertIn("non_repairable_gaps", d)
        self.assertTrue(all("repair_type" in a for a in d["actions"]))


if __name__ == "__main__":
    unittest.main()

