
import asyncio
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from game.loop import run_game


def main() -> None:
    seed = 42
    if "--seed" in sys.argv:
        idx = sys.argv.index("--seed")
        try:
            seed = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            pass

    session_id = f"ravenwood-{seed}-{uuid.uuid4().hex[:8]}"
    asyncio.run(run_game(session_id=session_id, seed=seed))


if __name__ == "__main__":
    main()
