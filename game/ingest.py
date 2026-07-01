"""
Phase 2 — World graph ingestion.

Loads scenario/ravenwood.py into Cognee, builds all nodes and edges,
and exposes verification helpers used by scripts/ingest_world.py.

Strategy:
  1. prune any stale data
  2. setup() to initialise Kuzu / LanceDB / SQLite
  3. Build all DataPoint nodes from scenario data
  4. Wire edges (typed relationships) between nodes
  5. add_data_points() → persists everything to the graph + vector index
  6. Also remember() one rich-text summary per character so recall()
     has semantic content to route through
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import cognee
from cognee.infrastructure.engine import DataPoint
from cognee.modules.engine.operations.setup import setup
from cognee.modules.engine.utils import generate_node_id
from cognee.tasks.storage.add_data_points import add_data_points

from scenario.ravenwood import (
    NPCS, NPCS_BY_ID,
    FACTS, FACTS_BY_ID,
    LOCATIONS, LOCATIONS_BY_ID,
    CLUES, CLUES_BY_ID,
    EVENTS, EVENTS_BY_ID,
    SOLUTION,
    Relationship,
)
from game.graph_models import (
    CharacterNode, FactNode, LocationNode, ClueNode, EventNode,
)

DATASET = "ravenwood"

# ── helpers ───────────────────────────────────────────────────────────────────

def _node_id(slug: str):
    """Deterministic UUID from a human-readable slug."""
    return generate_node_id(slug)


def _make_fact_nodes() -> dict[str, FactNode]:
    return {
        f.id: FactNode(
            id=_node_id(f.id),
            name=f.id,
            statement=f.statement,
            is_solution=f.is_solution_component,
        )
        for f in FACTS
    }


def _make_location_nodes() -> dict[str, LocationNode]:
    return {
        loc.id: LocationNode(
            id=_node_id(loc.id),
            name=loc.name,
            description=loc.description,
        )
        for loc in LOCATIONS
    }


def _make_event_nodes() -> dict[str, EventNode]:
    return {
        ev.id: EventNode(
            id=_node_id(ev.id),
            name=ev.id,
            description=ev.description,
            time=ev.time,
        )
        for ev in EVENTS
    }


def _make_clue_nodes(
    loc_nodes: dict[str, LocationNode],
    fact_nodes: dict[str, FactNode],
) -> dict[str, ClueNode]:
    nodes: dict[str, ClueNode] = {}
    for c in CLUES:
        node = ClueNode(
            id=_node_id(c.id),
            name=c.id,
            description=c.description,
        )
        if c.location_id in loc_nodes:
            node.located_in = loc_nodes[c.location_id]
        if c.supports_fact_id in fact_nodes:
            node.supports_fact = fact_nodes[c.supports_fact_id]
        nodes[c.id] = node
    return nodes


def _make_character_nodes() -> dict[str, CharacterNode]:
    return {
        npc.id: CharacterNode(
            id=_node_id(npc.id),
            name=npc.name,
            character_id=npc.id,
            role=npc.role,
            public_persona=npc.public_persona,
            alibi=npc.alibi,
            alibi_is_true=npc.alibi_is_true,
        )
        for npc in NPCS
    }


def _wire_character_edges(
    char_nodes: dict[str, CharacterNode],
    fact_nodes: dict[str, FactNode],
) -> None:
    """Set all typed edges on CharacterNodes from scenario relationship data."""
    edge_type_map = {
        "KNOWS": "knows",
        "FAMILY_OF": "family_of",
        "ALLIED_WITH": "allied_with",
        "RESENTS": "resents",
        "OWES_DEBT_TO": "owes_debt_to",
        "BLACKMAILS": "blackmails",
        "MURDERED": "knows",      # store as knows — murderer relationship handled in solution
        "EMPLOYED_BY": "knows",
        "WITNESSED": "knows",
    }

    for npc in NPCS:
        node = char_nodes[npc.id]

        # character → character edges
        for rel in npc.relationships:
            if rel.target_id not in char_nodes:
                continue
            field = edge_type_map.get(rel.edge_type, "knows")
            target = char_nodes[rel.target_id]
            existing = getattr(node, field) or []
            if not isinstance(existing, list):
                existing = [existing]
            existing.append(target)
            setattr(node, field, existing)

        # character → fact edges (knows_fact)
        knows_targets = [fact_nodes[fid] for fid in npc.known_facts if fid in fact_nodes]
        if knows_targets:
            node.knows_fact = knows_targets

        # character → fact edges (lies_about_fact)
        lies_targets = [fact_nodes[fid] for fid in npc.lies_about if fid in fact_nodes]
        if lies_targets:
            node.lies_about_fact = lies_targets


# ── rich-text summaries for recall() ─────────────────────────────────────────

def _character_summary(npc) -> str:
    """
    Build a dense text description per NPC so that recall() has
    semantic content to route through. This is ingested alongside the
    structured graph nodes.
    """
    rel_lines = "\n".join(
        f"  - {r.edge_type} {NPCS_BY_ID[r.target_id].name}: {r.note}"
        for r in npc.relationships
        if r.target_id in NPCS_BY_ID
    )
    known_lines = "\n".join(
        f"  - {FACTS_BY_ID[fid].statement}"
        for fid in npc.will_share_freely
        if fid in FACTS_BY_ID
    )
    return (
        f"[CHARACTER] {npc.name} — {npc.role}\n"
        f"Persona: {npc.public_persona}\n"
        f"Alibi: {npc.alibi} (truthful: {npc.alibi_is_true})\n"
        f"Social connections:\n{rel_lines or '  (none listed)'}\n"
        f"Will share freely:\n{known_lines or '  (nothing)'}\n"
        f"Private secret: {npc.private_secret}\n"
    )


def _location_summary(loc) -> str:
    clue_descs = [
        CLUES_BY_ID[cid].description
        for cid in loc.clue_ids
        if cid in CLUES_BY_ID
    ]
    clue_block = "\n".join(f"  - {d}" for d in clue_descs) or "  (no clues yet found)"
    return (
        f"[LOCATION] {loc.name}\n"
        f"Description: {loc.description}\n"
        f"Clues present:\n{clue_block}\n"
    )


# ── main ingestion ─────────────────────────────────────────────────────────────

async def ingest_world(*, clean: bool = True) -> None:
    """
    Full world ingestion. Set clean=False to skip prune (faster re-runs
    when only verifying, not rebuilding).
    """
    if clean:
        print("  Pruning previous data...")
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)

    print("  Running setup()...")
    await setup()

    # ── Build all nodes ───────────────────────────────────────────────────────
    print("  Building DataPoint nodes...")
    fact_nodes   = _make_fact_nodes()
    loc_nodes    = _make_location_nodes()
    event_nodes  = _make_event_nodes()
    clue_nodes   = _make_clue_nodes(loc_nodes, fact_nodes)
    char_nodes   = _make_character_nodes()

    _wire_character_edges(char_nodes, fact_nodes)

    # ── Persist structured graph ──────────────────────────────────────────────
    all_points: list[DataPoint] = (
        list(fact_nodes.values())
        + list(loc_nodes.values())
        + list(event_nodes.values())
        + list(clue_nodes.values())
        + list(char_nodes.values())
    )
    print(f"  Inserting {len(all_points)} DataPoint nodes into graph...")
    await add_data_points(all_points)
    print(f"  [{len(all_points)} nodes inserted]")

    # ── Also remember() rich text per character and location ─────────────────
    # This gives recall() semantic text content to work with alongside the graph.
    print("  Ingesting character summaries via remember()...")
    for npc in NPCS:
        summary = _character_summary(npc)
        await cognee.remember(summary, dataset_name=DATASET)

    print("  Ingesting location summaries via remember()...")
    for loc in LOCATIONS:
        summary = _location_summary(loc)
        await cognee.remember(summary, dataset_name=DATASET)

    # Solution chain — stored so the GM can retrieve it for endgame evaluation
    solution_text = (
        f"[SOLUTION] The murderer is {SOLUTION['murderer_name']}. "
        f"Narrative: {SOLUTION['narrative']}"
    )
    await cognee.remember(solution_text, dataset_name=DATASET)

    print("  World ingestion complete.\n")


# ── verification queries ───────────────────────────────────────────────────────

async def verify_graph() -> None:
    """Run a set of traversal and recall queries to confirm the graph is usable."""
    queries = [
        ("Butler's social connections",
         "Who does Thomas Harrington the butler know, and who are they connected to?"),
        ("Colonel Ashworth facts",
         "What does Colonel Gerald Ashworth know about the finances and the trust?"),
        ("Motive chain",
         "Who has a financial motive to want Lord Ravenwood dead?"),
        ("Sophie's evidence",
         "What did Sophie Calloway witness from the conservatory?"),
        ("Means — poison",
         "What poison was used and where did it come from?"),
    ]

    print("=== Graph verification queries ===\n")
    for label, q in queries:
        print(f"[{label}]\nQ: {q}")
        try:
            results = await cognee.recall(query_text=q, datasets=[DATASET])
            if results:
                for r in results[:2]:   # show top 2 results
                    text = getattr(r, "text", getattr(r, "answer", str(r)))
                    print(f"  → {text[:300]}")
            else:
                print("  → (no results)")
        except Exception as exc:
            print(f"  → [ERROR] {exc}")
        print()
    print("=== End verification ===")
