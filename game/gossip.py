"""Consequence propagation over the social graph, plus contradiction detection."""

from __future__ import annotations

import collections
from dataclasses import dataclass, field

from cognee.infrastructure.databases.graph import get_graph_engine
from cognee.modules.engine.utils import generate_node_id

from game.bootstrap import reset_graph_context
from scenario.ravenwood import NPCS_BY_ID

# Lowercase to match the edge labels Cognee stores.
SOCIAL_EDGES = {"knows", "family_of", "allied_with", "blackmails", "resents", "owes_debt_to"}

STANCE_EFFECTS: dict[str, dict[int, str]] = {
    "THREAT":        {1: "hostile",   2: "wary"},
    "EXPOSURE":      {1: "hostile",   2: "wary"},
    "ACCUSATION":    {1: "wary",      2: "suspicious"},
    "CONFRONTATION": {1: "wary",      2: "suspicious"},
    "HELP":          {1: "cooperative", 2: "neutral"},
}

STANCE_SEVERITY: dict[str, int] = {
    "hostile": 5, "wary": 4, "suspicious": 3,
    "cooperative": 2, "neutral": 1,
}


@dataclass
class GossipEvent:
    source_npc_id: str
    source_npc_name: str
    event_type: str
    description: str
    affected: dict[str, tuple[str, str]]
    paths: dict[str, list[str]] = field(default_factory=dict)
    source: str = "graph"


async def _traverse_social_graph(source_npc_id: str, max_hops: int = 2):
    reset_graph_context()
    engine = await get_graph_engine()
    seed = str(generate_node_id(source_npc_id))

    nodes, edges = await engine.get_neighborhood([seed], depth=max_hops)

    id2slug: dict[str, str] = {
        nid: props.get("character_id")
        for nid, props in nodes
        if props.get("character_id")
    }
    id2slug.setdefault(seed, source_npc_id)

    adj: dict[str, set[str]] = collections.defaultdict(set)
    for s, t, rel, _ in edges:
        if rel in SOCIAL_EDGES:
            adj[s].add(t)
            adj[t].add(s)

    return _bfs(seed, adj, id2slug, source_npc_id, max_hops)


def _traverse_scenario(source_npc_id: str, max_hops: int = 2):
    """Fallback over in-memory relationships if the graph query fails."""
    adj: dict[str, set[str]] = collections.defaultdict(set)
    for npc in NPCS_BY_ID.values():
        for rel in npc.relationships:
            if rel.edge_type.lower() in SOCIAL_EDGES and rel.target_id in NPCS_BY_ID:
                adj[npc.id].add(rel.target_id)
                adj[rel.target_id].add(npc.id)
    identity = {nid: nid for nid in NPCS_BY_ID}
    return _bfs(source_npc_id, adj, identity, source_npc_id, max_hops)


def _bfs(seed, adj, id2slug, source_slug, max_hops):
    dist = {seed: 0}
    pred: dict[str, str | None] = {seed: None}
    frontier = [seed]
    for hop in range(1, max_hops + 1):
        nxt = []
        for cur in frontier:
            for nb in adj.get(cur, ()):
                if nb not in dist:
                    dist[nb] = hop
                    pred[nb] = cur
                    nxt.append(nb)
        frontier = nxt

    hops: dict[str, int] = {}
    paths: dict[str, list[str]] = {}
    for nid, h in dist.items():
        if nid == seed:
            continue
        slug = id2slug.get(nid)
        if not slug:
            continue
        hops[slug] = h
        chain, cur = [], nid
        while cur is not None:
            chain.append(id2slug.get(cur, cur))
            cur = pred.get(cur)
        chain.reverse()
        paths[slug] = chain
    return hops, paths


async def propagate(
    source_npc_id: str,
    event_type: str,
    event_description: str,
    npc_stances: dict[str, str],
) -> GossipEvent:
    origin = "graph"
    try:
        hops, paths = await _traverse_social_graph(source_npc_id, max_hops=2)
        if not hops:
            hops, paths = _traverse_scenario(source_npc_id, max_hops=2)
            origin = "scenario"
    except Exception:
        hops, paths = _traverse_scenario(source_npc_id, max_hops=2)
        origin = "scenario"

    effects = STANCE_EFFECTS.get(event_type, {})

    direct = effects.get(1)
    if direct:
        old = npc_stances.get(source_npc_id, "neutral")
        if STANCE_SEVERITY.get(direct, 0) > STANCE_SEVERITY.get(old, 0):
            npc_stances[source_npc_id] = direct

    changes: dict[str, tuple[str, str]] = {}
    result_paths: dict[str, list[str]] = {}
    for affected_id, hop in hops.items():
        new_stance = effects.get(hop)
        if not new_stance:
            continue
        old_stance = npc_stances.get(affected_id, "neutral")
        if STANCE_SEVERITY.get(new_stance, 0) > STANCE_SEVERITY.get(old_stance, 0):
            npc_stances[affected_id] = new_stance
            changes[affected_id] = (old_stance, new_stance)
            result_paths[affected_id] = paths.get(affected_id, [source_npc_id, affected_id])

    source = NPCS_BY_ID.get(source_npc_id)
    return GossipEvent(
        source_npc_id=source_npc_id,
        source_npc_name=source.name if source else source_npc_id,
        event_type=event_type,
        description=event_description,
        affected=changes,
        paths=result_paths,
        source=origin,
    )


def format_gossip_report(event: GossipEvent) -> str | None:
    if not event.affected:
        return None
    lines = [
        f"\n  [gossip] Word of your exchange with {event.source_npc_name} "
        f"has begun to travel..."
    ]
    for npc_id, (old, new) in event.affected.items():
        npc = NPCS_BY_ID.get(npc_id)
        name = npc.name if npc else npc_id
        lines.append(f"    → {name} now regards you with {new} eyes.")
    return "\n".join(lines)


CONTRADICTIONS: list[tuple[str, str, str]] = [
    (
        "f_gerald_false_alibi",
        "f_sophie_saw_gerald",
        "Colonel Ashworth claims he was in his room from 8:40 PM — yet someone "
        "reports seeing him leave the study corridor at 9:15 PM.",
    ),
    (
        "f_foxglove_missing",
        "f_digitalis_in_glass",
        "Foxglove plants were uprooted from the manor garden — and the substance "
        "found in the brandy glass is a digitalis extract derived from foxglove.",
    ),
    (
        "f_pemberton_digitalis_missing",
        "f_digitalis_in_glass",
        "Dr. Pemberton's medical bag is missing a digitalis vial — yet digitalis "
        "was also found in the victim's brandy glass. One source may be innocent.",
    ),
]


def check_contradictions(learned_facts: list[str]) -> list[str]:
    learned = set(learned_facts)
    notices: list[str] = []
    for fact_a, fact_b, notice in CONTRADICTIONS:
        if fact_a in learned and fact_b in learned:
            notices.append(f"  🔎 Inconsistency noticed: {notice}")
    return notices
