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

    graph.nodes.append(_build_dimension_node(comparison_report, "population", "population", NodeType.POPULATION))
    graph.edges.append(DAGEdge("intervention", "population"))

    graph.nodes.append(_build_dimension_node(comparison_report, "device", "device", NodeType.DEVICE))
    graph.edges.append(DAGEdge("intervention", "device"))

    graph.nodes.append(_build_dimension_node(comparison_report, "context", "context", NodeType.CONTEXT))
    graph.edges.append(DAGEdge("intervention", "context"))

    graph.nodes.append(_build_design_node(comparison_report))
    graph.edges.append(DAGEdge("mechanism", "design"))

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
    suivi, marquage CE...), à l'exclusion des gaps déjà représentés par le
    nœud "comparator" (voir avertissement en tête de fichier)."""
    if comparison_report is None:
        return GraphNode(
            "design",
            NodeType.DESIGN,
            "Non branché — comparison_report non fourni",
            status=NodeStatus.UNKNOWN,
            justification=(
                "build_review_causal_graph() a été appelé sans comparison_report : "
                "impossible d'évaluer les gaps de design sans le StudyObject réel."
            ),
        )
    design_gaps = [
        g
        for g in comparison_report.gaps
        if g.dimension == "design" and g.topic != "no_comparator"
    ]
    if design_gaps:
        # Une absence de donnée (evidence_status=UNKNOWN) n'est pas une
        # faiblesse confirmée : distinguer les deux au niveau du statut du
        # nœud, pas seulement dans le texte. Lit désormais le champ
        # structuré ClaimStudyGap.evidence_status plutôt que de chercher
        # une phrase précise dans description — corrige le couplage
        # texte/logique identifié le 2026-07-18 (le moteur ne "raisonne"
        # plus sur une formulation humaine). NOT_APPLICABLE est traité
        # comme UNKNOWN ici (ni l'un ni l'autre n'est une faiblesse
        # confirmée) ; aucun site d'appel ne l'utilise encore.
        has_confirmed_weakness = any(
            g.evidence_status == EvidenceStatus.CONFIRMED for g in design_gaps
        )
        status = NodeStatus.GAP if has_confirmed_weakness else NodeStatus.UNKNOWN
        return GraphNode(
            "design",
            NodeType.DESIGN,
            "; ".join(g.description for g in design_gaps),
            status=status,
            justification="; ".join(g.has_critique for g in design_gaps if g.has_critique) or None,
        )
    return GraphNode(
        "design",
        NodeType.DESIGN,
        "Aucun gap de design identifié (hors comparateur, traité séparément)",
        status=NodeStatus.OK,
        justification=None,
    )


def attach_comparison_report(
    graph: ReviewCausalGraph, comparison_report: "ComparisonReport"
) -> ReviewCausalGraph:
    """Remplace les nœuds population/device/context/design d'un graphe déjà
    construit, une fois un ComparisonReport disponible (ex: après
    compare_claim_to_study()). Mutation en place, retourne le même objet
    pour chaînage."""
    replacements = {
        "population": _build_dimension_node(comparison_report, "population", "population", NodeType.POPULATION),
        "device": _build_dimension_node(comparison_report, "device", "device", NodeType.DEVICE),
        "context": _build_dimension_node(comparison_report, "context", "context", NodeType.CONTEXT),
        "design": _build_design_node(comparison_report),
    }
    for i, n in enumerate(graph.nodes):
        if n.id in replacements:
            graph.nodes[i] = replacements[n.id]
    return graph
