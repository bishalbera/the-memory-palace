"""Session registry and progressive graph-reveal state for the web client."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from game.loop import GameState
from scenario.ravenwood import (
    NPCS_BY_ID, FACTS_BY_ID, CLUES_BY_ID, LOCATIONS_BY_ID, SOLUTION,
)


# ── Cytoscape element builders ────────────────────────────────────────────────

def _npc_node(npc_id: str) -> dict:
    npc = NPCS_BY_ID[npc_id]
    return {"data": {
        "id": npc_id,
        "label": npc.name,
        "sublabel": npc.role,
        "type": "character",
        "alibi_true": str(npc.alibi_is_true).lower(),
    }}


def _location_node(loc_id: str) -> dict:
    loc = LOCATIONS_BY_ID[loc_id]
    return {"data": {
        "id": loc_id,
        "label": loc.name,
        "type": "location",
    }}


def _fact_node(fact_id: str) -> dict:
    fact = FACTS_BY_ID[fact_id]
    label = fact.statement[:32] + "…" if len(fact.statement) > 32 else fact.statement
    return {"data": {
        "id": fact_id,
        "label": label,
        "full": fact.statement,
        "type": "fact",
        "solution": str(fact.is_solution_component).lower(),
    }}


def _edge(src: str, tgt: str, label: str) -> dict:
    return {"data": {
        "id": f"e_{src}__{tgt}__{label}",
        "source": src,
        "target": tgt,
        "label": label,
    }}


# ── GraphState ────────────────────────────────────────────────────────────────

@dataclass
class GraphState:
    node_ids: set[str] = field(default_factory=set)
    edge_ids: set[str] = field(default_factory=set)
    all_elements: list[dict] = field(default_factory=list)


def _add_node(graph: GraphState, node: dict) -> bool:
    nid = node["data"]["id"]
    if nid in graph.node_ids:
        return False
    graph.node_ids.add(nid)
    graph.all_elements.append(node)
    return True


def _add_edge(graph: GraphState, edge: dict) -> bool:
    eid = edge["data"]["id"]
    if eid in graph.edge_ids:
        return False
    src, tgt = edge["data"]["source"], edge["data"]["target"]
    if src not in graph.node_ids or tgt not in graph.node_ids:
        return False  # never add an edge to an invisible node
    graph.edge_ids.add(eid)
    graph.all_elements.append(edge)
    return True


# ── Session registry ──────────────────────────────────────────────────────────

SESSIONS: dict[str, tuple[GameState, GraphState]] = {}


def new_session(session_id: str | None = None) -> tuple[str, GameState, GraphState]:
    sid = session_id or uuid.uuid4().hex[:12]
    state = GameState(session_id=sid)
    state.visited_rooms.add(state.current_room)
    graph = GraphState()
    SESSIONS[sid] = (state, graph)
    return sid, state, graph


def get_session(session_id: str) -> tuple[GameState, GraphState] | None:
    return SESSIONS.get(session_id)


# ── Progressive reveal ────────────────────────────────────────────────────────

def update_graph(game_state: GameState, graph: GraphState) -> list[dict]:
    """Return newly revealed elements, mutating graph in-place."""
    new: list[dict] = []

    # Locations visited
    for loc_id in game_state.visited_rooms:
        if loc_id in LOCATIONS_BY_ID and _add_node(graph, _location_node(loc_id)):
            new.append(graph.all_elements[-1])

    # NPCs: anyone in stances has been interacted with (directly or via gossip)
    for npc_id in game_state.npc_stances:
        if npc_id not in NPCS_BY_ID:
            continue
        if _add_node(graph, _npc_node(npc_id)):
            new.append(graph.all_elements[-1])
        # Relationship edges to already-revealed nodes
        npc = NPCS_BY_ID[npc_id]
        for rel in npc.relationships:
            e = _edge(npc_id, rel.target_id, rel.edge_type.lower().replace("_", " "))
            if _add_edge(graph, e):
                new.append(e)

    # Reverse relationship edges (other NPCs pointing TO newly revealed nodes)
    for other_id, other_npc in NPCS_BY_ID.items():
        if other_id not in graph.node_ids:
            continue
        for rel in other_npc.relationships:
            if rel.target_id in graph.node_ids:
                e = _edge(other_id, rel.target_id, rel.edge_type.lower().replace("_", " "))
                if _add_edge(graph, e):
                    new.append(e)

    # Facts learned
    for fact_id in game_state.player_learned_facts:
        if fact_id not in FACTS_BY_ID:
            continue
        if _add_node(graph, _fact_node(fact_id)):
            new.append(graph.all_elements[-1])
        # Edge from the NPC who shared it (first revealed NPC who knows it)
        source = _find_source_npc(fact_id, graph)
        if source:
            e = _edge(source, fact_id, "disclosed")
            if _add_edge(graph, e):
                new.append(e)

    return new


def full_graph(graph: GraphState) -> list[dict]:
    return list(graph.all_elements)


def build_case_file(state: GameState) -> dict:
    """Return structured endgame case file data for the frontend."""
    full_chain = SOLUTION["full_chain"]
    found_set = set(state.player_learned_facts)
    found_chain = [f for f in full_chain if f in found_set]

    motive_ids = ["f_gerald_embezzled", "f_ravenwood_discovered_gerald", "f_will_change"]
    means_ids  = ["f_foxglove_missing", "f_gerald_poisoned_decanter", "f_digitalis_in_glass"]
    opp_ids    = ["f_sophie_saw_gerald", "f_gerald_false_alibi"]

    def _fmt(ids: list[str]) -> list[dict]:
        return [
            {"id": fid, "statement": FACTS_BY_ID[fid].statement, "found": fid in found_set}
            for fid in ids if fid in FACTS_BY_ID
        ]

    pct = len(found_chain) / len(full_chain) if full_chain else 0
    if pct == 1.0:    rating = "Master Detective"
    elif pct >= 0.75: rating = "Seasoned Inspector"
    elif pct >= 0.5:  rating = "Competent Investigator"
    else:             rating = "Lucky Intuition"

    return {
        "motive":      _fmt(motive_ids),
        "means":       _fmt(means_ids),
        "opportunity": _fmt(opp_ids),
        "chain_found": len(found_chain),
        "chain_total": len(full_chain),
        "rating":      rating,
        "turns":       state.turn,
        "facts_found": len(state.player_learned_facts),
        "total_facts": len(FACTS_BY_ID),
        "clues_found": len(state.player_found_clues),
        "total_clues": len(CLUES_BY_ID),
        "rooms":       len(state.visited_rooms),
        "total_rooms": len(LOCATIONS_BY_ID),
    }


# ── helpers ───────────────────────────────────────────────────────────────────

def _find_source_npc(fact_id: str, graph: GraphState) -> str | None:
    for npc_id in graph.node_ids:
        npc = NPCS_BY_ID.get(npc_id)
        if npc and fact_id in npc.known_facts:
            return npc_id
    return None
