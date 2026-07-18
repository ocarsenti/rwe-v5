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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from models import BiasDetection, CausalRole, CausalStructure, ClinicalClaim, DAGEdge, EndpointAnalysis

try:
    from study_object import ComparisonReport
except ImportError:  # pragma: no cover - study_object may not always be loaded
    ComparisonReport = None  # type: ignore


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
    StudyObject — quand ce module est appelé depuis analyze(), le nœud
    population reste UNKNOWN (honnête : le moteur ne voit pas encore la
    population réelle à ce stade du pipeline). Un appelant qui dispose
    d'un ComparisonReport (via study_object.compare_claim_to_study) peut
    soit le passer directement ici, soit appeler attach_comparison_report()
    après coup sur un graphe déjà construit.
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
        has_flags = len(ea.flags) > 0
        status = NodeStatus.GAP if has_flags else NodeStatus.OK
        justification = "; ".join(ea.flag_reasons.values()) if ea.flag_reasons else ea.nature_reason
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

    graph.nodes.append(_build_population_node(comparison_report))
    graph.edges.append(DAGEdge("intervention", "population"))

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

    return graph


def _build_population_node(comparison_report: "Optional[ComparisonReport]") -> GraphNode:
    if comparison_report is None:
        return GraphNode(
            "population",
            NodeType.POPULATION,
            "Non branché — comparison_report non fourni",
            status=NodeStatus.UNKNOWN,
            justification=(
                "build_review_causal_graph() a été appelé sans comparison_report : "
                "impossible de savoir si la population étudiée correspond à "
                "l'indication revendiquée sans le StudyObject réel."
            ),
        )
    population_gap = next(
        (g for g in comparison_report.gaps if g.dimension == "population"), None
    )
    if population_gap is not None:
        return GraphNode(
            "population",
            NodeType.POPULATION,
            population_gap.description,
            status=NodeStatus.GAP,
            justification=population_gap.has_critique,
        )
    return GraphNode(
        "population",
        NodeType.POPULATION,
        "Population étudiée conforme à l'indication revendiquée",
        status=NodeStatus.OK,
        justification=None,
    )


def attach_comparison_report(
    graph: ReviewCausalGraph, comparison_report: "ComparisonReport"
) -> ReviewCausalGraph:
    """Remplace le nœud population d'un graphe déjà construit, une fois un
    ComparisonReport disponible (ex: après compare_claim_to_study()).
    Mutation en place, retourne le même objet pour chaînage."""
    new_pop_node = _build_population_node(comparison_report)
    for i, n in enumerate(graph.nodes):
        if n.id == "population":
            graph.nodes[i] = new_pop_node
            break
    return graph
