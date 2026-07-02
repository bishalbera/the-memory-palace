
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from game.ingest import ingest_world, verify_graph


async def main() -> None:
    verify_only = "--verify" in sys.argv

    if not verify_only:
        print("\n=== Phase 2: World graph ingestion ===\n")
        await ingest_world(clean=True)
    else:
        print("\n=== Phase 2: Verification only (skipping rebuild) ===\n")

    await verify_graph()


if __name__ == "__main__":
    asyncio.run(main())
