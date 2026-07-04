#!/usr/bin/env python
"""
Proof that the world graph is real and self-hosted. Run:

    uv run python scripts/verify_cognee.py

Checks: [1] storage pinned to repo + graph populated, [2] multi-hop traversal,
[3] gossip is graph-driven (add an edge, a new NPC reacts), [4] HTML render.
Exits non-zero on any failure.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Importing `game` pins Cognee storage to <repo>/.cognee_system BEFORE cognee
# loads (see game/bootstrap.py). Must precede any cognee import.
import game  # noqa: F401
from game.bootstrap import SYSTEM_ROOT, reset_graph_context
from game.graph_models import CharacterNode
from game.gossip import propagate
from game.memory import DATASET  # world dataset name (COGNEE_DATASET, default "ravenwood")

from cognee.modules.engine.utils import generate_node_id
from cognee.tasks.storage.add_data_points import add_data_points
from cognee.infrastructure.databases.graph import get_graph_engine

ARTIFACT_DIR = Path(__file__).parent / ".artifacts"

_failures: list[str] = []


def check(cond: bool, label: str) -> bool:
    print(f"      {'✅ PASS' if cond else '❌ FAIL'}  {label}")
    if not cond:
        _failures.append(label)
    return cond


def _gid(slug: str) -> str:
    return str(generate_node_id(slug))


def _ghost(slug: str) -> CharacterNode:
    """A throwaway CharacterNode used only for verification, then deleted."""
    return CharacterNode(
        id=generate_node_id(slug), name=slug, character_id=slug,
        role="verify", public_persona="verify", alibi="verify", alibi_is_true=True,
    )


# ── [1] storage pinned + world graph populated ────────────────────────────────

async def test_storage_and_metrics() -> None:
    print("\n[1] Self-hosted storage pinned to repo + world graph populated")
    from cognee.infrastructure.databases.graph.config import get_graph_config

    graph_file = get_graph_config().graph_file_path
    print(f"      system root : {SYSTEM_ROOT}")
    print(f"      graph file  : {graph_file}")
    check(str(SYSTEM_ROOT) in str(graph_file),
          "graph persists under repo (.cognee_system), NOT inside the venv")

    reset_graph_context()
    engine = await get_graph_engine()
    metrics = await engine.get_graph_metrics()
    num_nodes = metrics.get("num_nodes", 0)
    num_edges = metrics.get("num_edges", 0)
    print(f"      get_graph_metrics() → num_nodes={num_nodes}  num_edges={num_edges}")
    check(num_nodes > 0, "world graph has nodes (num_nodes > 0)")
    check(num_edges > 0, "world graph has edges (num_edges > 0)")


# ── [2] multi-hop traversal is real ───────────────────────────────────────────

async def test_multihop_traversal() -> None:
    # Read-only proof over the REAL ingested graph, so it needs no mutation:
    #   Dr. Pemberton —KNOWS→ James Calloway —FAMILY_OF→ Sophie Calloway
    # Sophie is 2 hops from Pemberton and is NOT a direct neighbour.
    print("\n[3] Multi-hop traversal — Pemberton —KNOWS→ Calloway —FAMILY_OF→ Sophie")
    A, B, C = "pemberton_eleanor", "calloway_james", "calloway_sophie"
    reset_graph_context()
    engine = await get_graph_engine()

    n1, _ = await engine.get_neighborhood([_gid(A)], depth=1)
    n2, _ = await engine.get_neighborhood([_gid(A)], depth=2)
    reach1 = {p.get("character_id") for _, p in n1}
    reach2 = {p.get("character_id") for _, p in n2}

    check(B in reach1, "Calloway IS a direct (1-hop) neighbour of Pemberton")
    check(C not in reach1, "Sophie is NOT reachable from Pemberton in 1 hop")
    check(C in reach2, "Sophie IS reachable in 2 hops (Cognee traversed Pemberton→Calloway→Sophie)")


# ── [3] gossip is graph-driven ────────────────────────────────────────────────

async def test_gossip_is_graph_driven() -> None:
    print("\n[4] Gossip is GRAPH-DRIVEN — add one edge, a new NPC reacts (zero code change)")
    reset_graph_context()
    engine = await get_graph_engine()
    ghost_id = _gid("verify_ghost")
    try:
        baseline = await propagate("calloway_james", "ACCUSATION", "baseline", {})
        n_base = len(baseline.affected)
        print(f"      baseline: accusing Calloway ripples to {n_base} NPCs; "
              f"'verify_ghost' present? {'verify_ghost' in baseline.affected}")
        check(baseline.source == "graph", "baseline gossip traversed Cognee's graph (source=graph)")
        check("verify_ghost" not in baseline.affected, "ghost NPC is absent before we add its edge")

        # Change ONE relationship in the graph — not the code.
        await add_data_points([_ghost("verify_ghost")])
        await engine.add_edge(ghost_id, _gid("calloway_james"), "knows")

        reset_graph_context()
        after = await propagate("calloway_james", "ACCUSATION", "after", {})
        n_after = len(after.affected)
        print(f"      after add_edge(ghost—KNOWS—Calloway): {n_after} NPCs; "
              f"ghost reacts? {'verify_ghost' in after.affected} "
              f"(stance={dict(after.affected).get('verify_ghost')})")
        check(n_after == n_base + 1, f"exactly one more NPC reacts ({n_base} → {n_after})")
        check("verify_ghost" in after.affected, "the newly-connected NPC now reacts")
        check(after.source == "graph", "post-edit gossip still traversed the graph (source=graph)")
    finally:
        await engine.delete_nodes([ghost_id])
        reset_graph_context()
        restored = await propagate("calloway_james", "ACCUSATION", "restored", {})
        check("verify_ghost" not in restored.affected,
              "edge removed → ghost no longer reacts (graph restored)")


# ── [4] visualization asset ───────────────────────────────────────────────────

async def test_visualization() -> None:
    print("\n[2] Cognee renders the graph to HTML (visual proof asset)")
    import cognee

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out = ARTIFACT_DIR / "verify.html"
    if out.exists():
        out.unlink()

    reset_graph_context()
    try:
        # Access control requires an explicit dataset; DATASET is the world graph.
        await cognee.visualize_graph(str(out), dataset=DATASET)
    except Exception as exc:  # noqa: BLE001
        check(False, f"visualize_graph() raised: {exc}")
        return

    exists = out.exists()
    size = out.stat().st_size if exists else 0
    print(f"      wrote {out} ({size} bytes)")
    check(exists and size > 0, "visualize_graph() produced a non-empty HTML file")


# ── main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    print("=" * 70)
    print("  VERIFY COGNEE — proof the graph is real (self-hosted, multi-hop)")
    print("=" * 70)

    # Visualization runs right after metrics: it opens the per-dataset graph
    # file, which must not collide with a worker still holding that file from
    # the later mutation tests.
    await test_storage_and_metrics()
    await test_visualization()
    await test_multihop_traversal()
    await test_gossip_is_graph_driven()

    print("\n" + "=" * 70)
    if _failures:
        print(f"  ❌ {len(_failures)} check(s) FAILED:")
        for f in _failures:
            print(f"       - {f}")
        print("=" * 70)
        sys.exit(1)
    print("  ✅ ALL CHECKS PASSED — the graph is genuinely Cognee-backed.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
