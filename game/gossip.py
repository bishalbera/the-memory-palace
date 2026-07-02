"""
 Consequence propagation ("gossip").

When the player does something notable to NPC A (threatens, exposes a secret,
publicly accuses, or helps), this module traverses outward from A along social
edges (KNOWS / ALLIED_WITH / FAMILY_OF) up to 2 hops and updates PLAYER_STANDING
for every NPC reached.

Three scenes later, an NPC the player never spoke to may already be cold or
evasive because word travelled A→B→C through the social graph.

This is a multi-hop relationship query that cannot be done by semantic
similarity alone — it is the core demonstration of Cognee graph value.
"""

from __future__ import annotations
from dataclasses import dataclass

from scenario.ravenwood import NPCS_BY_ID

# Edge types that carry social gossip
SOCIAL_EDGES = {"KNOWS", "FAMILY_OF", "ALLIED_WITH", "BLACKMAILS"}

# How each event type affects stances at hop 1 and hop 2
STANCE_EFFECTS: dict[str, dict[int, str]] = {
    "THREAT":       {1: "hostile",   2: "wary"},
    "EXPOSURE":     {1: "hostile",   2: "wary"},
    "ACCUSATION":   {1: "wary",      2: "suspicious"},
    "CONFRONTATION":{1: "wary",      2: "suspicious"},
    "HELP":         {1: "cooperative", 2: "neutral"},
}

STANCE_SEVERITY: dict[str, int] = {
    "hostile": 5, "wary": 4, "suspicious": 3,
    "cooperative": 2, "neutral": 1,
}


@dataclass
class GossipEvent:
    source_npc_id: str
    source_npc_name: str
    event_type: str          # THREAT / EXPOSURE / ACCUSATION / CONFRONTATION / HELP
    description: str
    affected: dict[str, tuple[str, str]]   # npc_id → (old_stance, new_stance)


def get_social_network(npc_id: str, max_hops: int = 2) -> dict[str, int]:
    """
    BFS outward from npc_id along social edges.
    Returns {reached_npc_id: hop_distance}.
    """
    visited: dict[str, int] = {}
    frontier: set[str] = {npc_id}
    hop = 0

    while frontier and hop < max_hops:
        hop += 1
        next_frontier: set[str] = set()
        for current_id in frontier:
            npc = NPCS_BY_ID.get(current_id)
            if not npc:
                continue
            for rel in npc.relationships:
                tid = rel.target_id
                if rel.edge_type in SOCIAL_EDGES and tid not in visited and tid != npc_id:
                    visited[tid] = hop
                    next_frontier.add(tid)
        frontier = next_frontier

    return visited


def propagate(
    source_npc_id: str,
    event_type: str,
    event_description: str,
    npc_stances: dict[str, str],
) -> GossipEvent:
    """
    Propagate a gossip event outward from source_npc_id.
    Updates npc_stances in-place and returns a GossipEvent describing what changed.
    """
    network = get_social_network(source_npc_id, max_hops=2)
    effects = STANCE_EFFECTS.get(event_type, {})
    changes: dict[str, tuple[str, str]] = {}

    for affected_id, hop in network.items():
        new_stance = effects.get(hop)
        if not new_stance:
            continue
        old_stance = npc_stances.get(affected_id, "neutral")
        # Only escalate, never de-escalate via gossip
        if STANCE_SEVERITY.get(new_stance, 0) > STANCE_SEVERITY.get(old_stance, 0):
            npc_stances[affected_id] = new_stance
            changes[affected_id] = (old_stance, new_stance)

    source = NPCS_BY_ID.get(source_npc_id)
    return GossipEvent(
        source_npc_id=source_npc_id,
        source_npc_name=source.name if source else source_npc_id,
        event_type=event_type,
        description=event_description,
        affected=changes,
    )


def format_gossip_report(event: GossipEvent) -> str | None:
    """Return a visible notification string, or None if nothing changed."""
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


# ── Contradiction detection ───────────────────────────────────────────────────

# Pairs of facts that contradict each other.
# If the player has heard/found both sides, surface the inconsistency.
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
    """
    Return a list of contradiction notices for any pair of facts the player
    has now discovered on both sides.
    """
    learned = set(learned_facts)
    notices: list[str] = []
    for fact_a, fact_b, notice in CONTRADICTIONS:
        if fact_a in learned and fact_b in learned:
            notices.append(f"  🔎 Inconsistency noticed: {notice}")
    return notices
