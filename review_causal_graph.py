"""Représentation explicite du raisonnement causal en mode REVIEW.

Contexte (voir échange du 2026-07-18, PROMPT_FIX_CLASSIFIER_ET_VERDICT.md) :
le moteur raisonne déjà causalement (endpoint_classifier.py,
causal_graph_builder.py, study_object.py) mais ce raisonnement est
distribué dans plusieurs modules et son seul output consolidé, côté
REVIEW, est un enum plat (CausalStructure.DIRECT/MEDIATED/CIRCULAR/
INVALID). Ce module ASSEMBLE — il ne recalcule rien — les objets déjà
produits par le pipeline existant (ClinicalClaim, EndpointAnalysis,
BiasDetection, et optionnellement ComparisonReport) en un graphe
explicite et interrogeable.

Non-breaking par construction : ajouté comme champ optionnel de plus sur
EngineOutput, sur le même modèle que manifold_position / cas_output /
methodological_risk.

Avertissement anti-régression (cf. le cas "monocentrisme compté deux fois"
dans case1_7943_share.html) : `causal_structure` est toujours un PARAMÈTRE
de build_review_causal_graph(), jamais recalculé ici. Ce module ne doit
jamais dupliquer une logique de décision déjà présente ailleurs —
uniquement l'assembler.

Couverture des dimensions de ComparisonReport.gaps (study_object.py) :
    device      -> nœud "device"
    population  -> nœud "population"
    context     -> nœud "context"
    design      -> nœud "design", à l'EXCLUSION des gaps portant
                   ClaimStudyGap.topic == "no_comparator" (déjà représentés
                   par le nœud "comparator", alimenté par
                   BiasFlag.NO_COMPARATOR — même condition de déclenchement
                   exacte des deux côtés, cf. causal_graph_builder.py:
                   162-171 vs study_object.py:_design_gaps, has_comparator
                   branch). Corrigé le 2026-07-18 : un premier filtre par
                   recherche du mot "comparateur" dans la description
                   excluait AUSSI, par erreur, deux gaps sans rapport
                   (mono-bras vs objectif de performance, mono-bras vs
                   cohorte externe) qui mentionnent ce mot en passant sans
                   être des doublons — remplacé par le champ structuré
                   `topic`, positionné uniquement sur les deux gaps qui
                   partagent réellement la condition de déclenchement de
                   NO_COMPARATOR. Le statut GAP/UNKNOWN du nœud "design"
                   lit de la même façon ClaimStudyGap.evidence_status
                   (champ structuré), pas du texte — voir EvidenceStatus
                   dans study_object.py.
    endpoint    -> NON représenté par un nœud dédié : ce sont déjà les
                   nœuds endpoint_N existants (EndpointAnalysis.flags),
                   ajouter un nœud de plus dupliquerait l'information.
Nature du graphe (précision ajoutée le 2026-07-18, suite à une question sur
la terminologie) : ReviewCausalGraph est un DAG au sens structurel strict
(dirigé, acyclique — vérifié : toutes les arêtes vont de claim vers
conclusion, aucun cycle) mais PAS un graphe causal au sens de Pearl. Une
arête comme comparator -> conclusion ne signifie pas "l'absence de
comparateur cause la conclusion" ; elle signifie "l'évaluation de
conclusion dépend de, agrège, l'évaluation de comparator". C'est une
dépendance d'ARGUMENTATION (proche d'un assurance case / goal structure,
vocabulaire GSN — Goal Structuring Notation), pas une dépendance causale
au sens formel (pas de do-calculus, pas d'ensemble d'ajustement).

Ce module réutilise la classe DAGEdge, définie à l'origine pour TargetDAG
dans models.py (utilisée par epistemic_core.infer_target_dag(), mode
DESIGN — celui-là EST authentiquement causal : chaîne intervention ->
médiateurs -> outcome). Même classe, deux sémantiques différentes selon le
graphe où elle apparaît. Vérifié le 2026-07-18 : les deux usages sont
aujourd'hui cloisonnés (aucun code ne mélange TargetDAG et
ReviewCausalGraph), mais un futur lecteur du code doit garder cette
distinction en tête — DAGEdge ne garantit par elle-même aucune des deux
sémantiques, c'est le graphe qui la porte.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from models import BiasDetection, CausalRole, CausalStructure, ClinicalClaim, DAGEdge, EndpointAnalysis

try:
    from study_object import ComparisonReport, EvidenceStatus
except ImportError:  # pragma: no cover - study_object may not always be loaded
    ComparisonReport = None  # type: ignore
    EvidenceStatus = None  # type: ignore


# ---------------------------------------------------------------------------
# Structure du graphe
# ---------------------------------------------------------------------------


class NodeType(Enum):
    CLAIM = "CLAIM"
    INTERVENTION = "INTERVENTION"
    MECHANISM = "MECHANISM"
    ENDPOINT = "ENDPOINT"
    COMPARATOR = "COMPARATOR"
    POPULATION = "POPULATION"
    DEVICE = "DEVICE"
    CONTEXT = "CONTEXT"
    DESIGN = "DESIGN"
    # Extrait de DESIGN le 2026-07-18 : le corpus HAS réel (94 avis) montre
    # que T04 (biais de mesure/aveugle) co-occurre avec T02 (design
    # inadéquat) dans 17/39 avis (44%) et avec T01 (comparateur) dans
    # 27/42 avis (64%) — fréquent, pas un cas rare. Fondre systématiquement
    # ce sujet dans le nœud design masquait une distinction que le corpus
    # traite lui-même comme une catégorie à part entière.
    MEASUREMENT_BIAS = "MEASUREMENT_BIAS"
    CONCLUSION = "CONCLUSION"


class NodeStatus(Enum):
    OK = "OK"
    GAP = "GAP"
    UNKNOWN = "UNKNOWN"  # donnée non fournie au moteur (ex: population réelle)


@dataclass
class GraphNode:
    id: str
    type: NodeType
    label: str
    status: NodeStatus = NodeStatus.OK
    # Pourquoi ce statut : ancré dans les valeurs concrètes du dossier,
    # jamais un texte générique — même exigence que BiasDetection.case_reason
    # et EndpointAnalysis.flag_reasons dans le pipeline existant.
    justification: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "label": self.label,
            "status": self.status.value,
            "justification": self.justification,
        }


@dataclass
class ReviewCausalGraph:
    claim_text: str
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[DAGEdge] = field(default_factory=list)
    # Dérivé du graphe, jamais recalculé indépendamment.
    causal_structure: Optional[CausalStructure] = None

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "causal_structure": self.causal_structure.value if self.causal_structure else None,
        }

    def _node(self, node_id: str) -> Optional[GraphNode]:
        return next((n for n in self.nodes if n.id == node_id), None)

    def _incoming(self, node_id: str) -> list[DAGEdge]:
        return [e for e in self.edges if e.target == node_id]

    def _outgoing(self, node_id: str) -> list[DAGEdge]:
        return [e for e in self.edges if e.source == node_id]

    # -- Requêtes génériques ------------------------------------------------

    def find_unjustified_nodes(self) -> list[GraphNode]:
        """Nœuds marqués GAP sans justification ancrée dans le dossier."""
        return [n for n in self.nodes if n.status == NodeStatus.GAP and not n.justification]

    def find_disconnected_nodes(self) -> list[GraphNode]:
        """Nœuds sans aucune arête entrante ni sortante."""
        connected_ids = {e.source for e in self.edges} | {e.target for e in self.edges}
        return [n for n in self.nodes if n.id not in connected_ids and n.type != NodeType.CLAIM]

    def explain_path(self, node_id: str) -> list[GraphNode]:
        """Remonte la chaîne causale depuis `node_id` jusqu'à CLAIM."""
        path: list[GraphNode] = []
        current = node_id
        visited: set[str] = set()
        while current and current not in visited:
            visited.add(current)
            node = self._node(current)
            if node is None:
                break
            path.append(node)
            incoming = self._incoming(current)
            current = incoming[0].source if incoming else None
        return list(reversed(path))

    def nodes_by_status(self, status: NodeStatus) -> list[GraphNode]:
        return [n for n in self.nodes if n.status == status]


# ---------------------------------------------------------------------------
# Assembleur — construit le graphe à partir des objets DÉJÀ calculés
# ---------------------------------------------------------------------------


def build_review_causal_graph(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
    causal_structure: CausalStructure,
    bias_detections: list[BiasDetection],
    comparison_report: "Optional[ComparisonReport]" = None,
) -> ReviewCausalGraph:
    """Assemble un ReviewCausalGraph à partir du pipeline REVIEW existant.

    Ne relance AUCUNE extraction LLM et ne redécide AUCUN flag.

    comparison_report est optionnel car engine.analyze() ne reçoit pas de
    StudyObject — quand ce module est appelé depuis analyze(), les nœuds
    population/device/context/design restent UNKNOWN (honnête : le moteur
    ne voit pas encore l'étude réelle à ce stade du pipeline). Un appelant
    qui dispose d'un ComparisonReport (via study_object.compare_claim_to_
    study) peut soit le passer directement ici, soit appeler
    attach_comparison_report() après coup sur un graphe déjà construit.
    """
    graph = ReviewCausalGraph(claim_text=claim.text, causal_structure=causal_structure)

    graph.nodes.append(GraphNode("claim", NodeType.CLAIM, claim.text))

    graph.nodes.append(GraphNode("intervention", NodeType.INTERVENTION, claim.intervention))
    graph.edges.append(DAGEdge("claim", "intervention"))

    level_label = claim.level.value if claim.level else "UNKNOWN"
    graph.nodes.append(GraphNode("mechanism", NodeType.MECHANISM, level_label))
    graph.edges.append(DAGEdge("intervention", "mechanism"))

    comparator_flag = next(
        (bd for bd in bias_detections if bd.flag.value == "NO_COMPARATOR"), None
    )
    comparator_status = NodeStatus.GAP if comparator_flag else NodeStatus.OK
    comparator_label = (
        "Aucun comparateur"
        if claim.has_comparator is False
        else "Comparateur présent" if claim.has_comparator else "Non renseigné"
    )
    graph.nodes.append(
        GraphNode(
            "comparator",
            NodeType.COMPARATOR,
            comparator_label,
            status=comparator_status,
            justification=comparator_flag.case_reason if comparator_flag else None,
        )
    )
    graph.edges.append(DAGEdge("mechanism", "comparator"))

    endpoint_ids: list[str] = []
    for i, ea in enumerate(endpoint_analyses):
        node_id = f"endpoint_{i}"
        endpoint_ids.append(node_id)
        # Un endpoint peut être en gap soit via BiasFlag (qualité de la
        # mesure — ea.flags), soit via un gap de pertinence claim/endpoint
        # (le sujet de la mesure — ClaimStudyGap.endpoint_index), soit les
        # deux. Les deux sources sont combinées ici, jamais l'une au prix
        # de l'autre — évite de recréer le bug "flag écrasé" déjà vu.
        relevance_gap = None
        if comparison_report is not None:
            relevance_gap = next(
                (
                    g for g in comparison_report.gaps
                    if g.dimension == "endpoint" and g.topic == "claim_endpoint_mismatch"
                    and g.endpoint_index == i
                ),
                None,
            )
        has_flags = len(ea.flags) > 0
        justification_parts = []
        if ea.flag_reasons:
            justification_parts.append("; ".join(ea.flag_reasons.values()))
        elif ea.nature_reason:
            justification_parts.append(ea.nature_reason)
        if relevance_gap is not None:
            justification_parts.append(relevance_gap.has_critique)
        justification = "; ".join(p for p in justification_parts if p) or None

        if relevance_gap is not None and relevance_gap.evidence_status == EvidenceStatus.UNKNOWN and not has_flags:
            status = NodeStatus.UNKNOWN
        elif has_flags or (relevance_gap is not None and relevance_gap.evidence_status == EvidenceStatus.CONFIRMED):
            status = NodeStatus.GAP
        else:
            status = NodeStatus.OK

        graph.nodes.append(
            GraphNode(
                node_id,
                NodeType.ENDPOINT,
                f"{ea.endpoint.name} ({ea.nature.value}/{ea.causal_role.value})",
                status=status,
                justification=justification,
            )
        )
        source = "intervention" if ea.causal_role == CausalRole.INDEPENDENT else "mechanism"
        graph.edges.append(DAGEdge(source, node_id))

    graph.nodes.append(_build_dimension_node(comparison_report, "population", "population", NodeType.POPULATION))
    graph.edges.append(DAGEdge("intervention", "population"))

    graph.nodes.append(_build_dimension_node(comparison_report, "device", "device", NodeType.DEVICE))
    graph.edges.append(DAGEdge("intervention", "device"))

    graph.nodes.append(_build_dimension_node(comparison_report, "context", "context", NodeType.CONTEXT))
    graph.edges.append(DAGEdge("intervention", "context"))

    graph.nodes.append(_build_design_node(comparison_report))
    graph.edges.append(DAGEdge("mechanism", "design"))

    graph.nodes.append(_build_measurement_bias_node(comparison_report))
    graph.edges.append(DAGEdge("mechanism", "measurement_bias"))

    conclusion_id = "conclusion"
    graph.nodes.append(
        GraphNode(
            conclusion_id,
            NodeType.CONCLUSION,
            causal_structure.value,
            status=NodeStatus.GAP if causal_structure != CausalStructure.DIRECT else NodeStatus.OK,
            justification="; ".join(
                bd.case_reason for bd in bias_detections if bd.case_reason
            ) or None,
        )
    )
    for eid in endpoint_ids:
        graph.edges.append(DAGEdge(eid, conclusion_id))
    graph.edges.append(DAGEdge("comparator", conclusion_id))
    graph.edges.append(DAGEdge("design", conclusion_id))
    graph.edges.append(DAGEdge("measurement_bias", conclusion_id))

    return graph


_DIMENSION_OK_LABELS = {
    "population": "Population étudiée conforme à l'indication revendiquée",
    "device": "Dispositif étudié conforme au dispositif revendiqué",
    "context": "Contexte de l'étude conforme au système de santé cible",
}


def _build_dimension_node(
    comparison_report: "Optional[ComparisonReport]",
    dimension: str,
    node_id: str,
    node_type: NodeType,
) -> GraphNode:
    """Construit un nœud générique à partir d'un ClaimStudyGap de
    ComparisonReport.gaps, pour les dimensions à statut simple (0 ou 1 gap
    possible) : population, device, context. `design` a sa propre fonction
    car plusieurs gaps peuvent coexister sur cette dimension."""
    if comparison_report is None:
        return GraphNode(
            node_id,
            node_type,
            "Non branché — comparison_report non fourni",
            status=NodeStatus.UNKNOWN,
            justification=(
                f"build_review_causal_graph() a été appelé sans comparison_report : "
                f"impossible d'évaluer la dimension '{dimension}' sans le StudyObject réel."
            ),
        )
    gap = next((g for g in comparison_report.gaps if g.dimension == dimension), None)
    if gap is not None:
        return GraphNode(node_id, node_type, gap.description, status=NodeStatus.GAP, justification=gap.has_critique)
    return GraphNode(
        node_id, node_type, _DIMENSION_OK_LABELS[dimension], status=NodeStatus.OK, justification=None
    )


def _build_design_node(comparison_report: "Optional[ComparisonReport]") -> GraphNode:
    """Agrège les gaps dimension="design" (dossier réglementaire au sens
    large : exploratoire vs. outcome, non-randomisé, mono-bras, durée de
    suivi, marquage CE...), à l'exclusion des gaps déjà représentés par les
    nœuds "comparator" (topic="no_comparator") et "measurement_bias"
    (topic="subjective_no_blinding", extrait le 2026-07-18 — voir
    MEASUREMENT_BIAS ci-dessus)."""
    return _build_aggregated_gap_node(
        comparison_report,
        node_id="design",
        node_type=NodeType.DESIGN,
        excluded_topics={"no_comparator", "subjective_no_blinding"},
        empty_label="Aucun gap de design identifié (hors comparateur et biais de mesure, traités séparément)",
        no_report_label="Non branché — comparison_report non fourni",
        no_report_justification=(
            "build_review_causal_graph() a été appelé sans comparison_report : "
            "impossible d'évaluer les gaps de design sans le StudyObject réel."
        ),
    )


def _build_measurement_bias_node(comparison_report: "Optional[ComparisonReport]") -> GraphNode:
    """Isole le gap topic="subjective_no_blinding" (critère principal
    patient-rapporté sans aveugle ni sham) dans son propre nœud. Extrait de
    "design" le 2026-07-18 : sur 94 avis CNEDiMTS réels, T04 (biais de
    mesure/aveugle — la catégorie du corpus la plus proche) co-occurre avec
    T02 (design) dans 44% des avis qui ont l'un ou l'autre, et avec T01
    (comparateur) dans 64% des cas — fréquent, pas un cas marginal."""
    return _build_aggregated_gap_node(
        comparison_report,
        node_id="measurement_bias",
        node_type=NodeType.MEASUREMENT_BIAS,
        included_topics={"subjective_no_blinding"},
        empty_label="Aucun biais de mesure identifié",
        no_report_label="Non branché — comparison_report non fourni",
        no_report_justification=(
            "build_review_causal_graph() a été appelé sans comparison_report : "
            "impossible d'évaluer le biais de mesure sans le StudyObject réel."
        ),
    )


def _build_aggregated_gap_node(
    comparison_report: "Optional[ComparisonReport]",
    node_id: str,
    node_type: NodeType,
    empty_label: str,
    no_report_label: str,
    no_report_justification: str,
    excluded_topics: "Optional[set[str]]" = None,
    included_topics: "Optional[set[str]]" = None,
) -> GraphNode:
    """Factorise la logique commune à _build_design_node() et
    _build_measurement_bias_node() : agréger plusieurs ClaimStudyGap de
    dimension="design" en un seul nœud, avec la même distinction
    GAP/UNKNOWN basée sur evidence_status que partout ailleurs dans ce
    module. `excluded_topics` XOR `included_topics` selon qu'on définit le
    nœud par ce qu'il exclut (design = tout sauf X) ou par ce qu'il inclut
    (measurement_bias = seulement X)."""
    if comparison_report is None:
        return GraphNode(
            node_id, node_type, no_report_label,
            status=NodeStatus.UNKNOWN, justification=no_report_justification,
        )
    gaps = [g for g in comparison_report.gaps if g.dimension == "design"]
    if included_topics is not None:
        gaps = [g for g in gaps if g.topic in included_topics]
    if excluded_topics is not None:
        gaps = [g for g in gaps if g.topic not in excluded_topics]
    if gaps:
        # Une absence de donnée (evidence_status=UNKNOWN) n'est pas une
        # faiblesse confirmée : distinguer les deux au niveau du statut du
        # nœud, pas seulement dans le texte — cf. échange du 2026-07-18.
        has_confirmed_weakness = any(g.evidence_status == EvidenceStatus.CONFIRMED for g in gaps)
        status = NodeStatus.GAP if has_confirmed_weakness else NodeStatus.UNKNOWN
        return GraphNode(
            node_id, node_type,
            "; ".join(g.description for g in gaps),
            status=status,
            justification="; ".join(g.has_critique for g in gaps if g.has_critique) or None,
        )
    return GraphNode(node_id, node_type, empty_label, status=NodeStatus.OK, justification=None)


def _update_endpoint_node_with_relevance(
    node: GraphNode, comparison_report: "ComparisonReport"
) -> GraphNode:
    """Complète un nœud endpoint_N déjà construit (avant que le
    ComparisonReport n'existe, ex: dans engine.analyze()) avec le gap de
    pertinence claim/endpoint, une fois disponible. N'écrase jamais le
    statut/justification déjà posé par les BiasFlag — les combine.
    Pré-attach, un statut GAP ne peut venir que de BiasFlag (relevance_gap
    n'était jamais disponible avant cet appel), donc `had_flags_gap` peut
    être déduit du statut actuel sans information supplémentaire.
    """
    idx = int(node.id.split("_")[1])
    relevance_gap = next(
        (
            g for g in comparison_report.gaps
            if g.dimension == "endpoint" and g.topic == "claim_endpoint_mismatch"
            and g.endpoint_index == idx
        ),
        None,
    )
    if relevance_gap is None:
        return node

    had_flags_gap = node.status == NodeStatus.GAP
    justification_parts = [node.justification] if node.justification else []
    if relevance_gap.has_critique:
        justification_parts.append(relevance_gap.has_critique)
    new_justification = "; ".join(justification_parts) or None

    if relevance_gap.evidence_status == EvidenceStatus.UNKNOWN and not had_flags_gap:
        new_status = NodeStatus.UNKNOWN
    elif had_flags_gap or relevance_gap.evidence_status == EvidenceStatus.CONFIRMED:
        new_status = NodeStatus.GAP
    else:
        new_status = NodeStatus.OK

    return GraphNode(node.id, node.type, node.label, status=new_status, justification=new_justification)


def attach_comparison_report(
    graph: ReviewCausalGraph, comparison_report: "ComparisonReport"
) -> ReviewCausalGraph:
    """Remplace les nœuds population/device/context/design/measurement_bias,
    et complète les nœuds endpoint_N, d'un graphe déjà construit, une fois
    un ComparisonReport disponible (ex: après compare_claim_to_study()).
    Mutation en place, retourne le même objet pour chaînage."""
    replacements = {
        "population": _build_dimension_node(comparison_report, "population", "population", NodeType.POPULATION),
        "device": _build_dimension_node(comparison_report, "device", "device", NodeType.DEVICE),
        "context": _build_dimension_node(comparison_report, "context", "context", NodeType.CONTEXT),
        "design": _build_design_node(comparison_report),
        "measurement_bias": _build_measurement_bias_node(comparison_report),
    }
    for i, n in enumerate(graph.nodes):
        if n.id in replacements:
            graph.nodes[i] = replacements[n.id]
        elif n.type == NodeType.ENDPOINT:
            graph.nodes[i] = _update_endpoint_node_with_relevance(n, comparison_report)
    return graph
