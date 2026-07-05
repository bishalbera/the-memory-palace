"""Build the world graph once if it's missing. Runs at container startup."""

import asyncio

import game  # noqa: F401  — pins Cognee storage paths before cognee imports


async def main() -> None:
    from cognee.infrastructure.databases.graph import get_graph_engine

    nodes = 0
    try:
        metrics = await (await get_graph_engine()).get_graph_metrics()
        nodes = metrics.get("num_nodes", 0) or 0
    except Exception:
        nodes = 0

    if nodes > 0:
        print(f"[ensure_graph] world graph present ({nodes} nodes) — skipping ingest")
        return

    print("[ensure_graph] no graph found — ingesting the world (one-time)...")
    from game.ingest import ingest_world

    await ingest_world(clean=True)
    print("[ensure_graph] ingest complete")


if __name__ == "__main__":
    asyncio.run(main())
