"""Pin Cognee's storage to the repo. Import before any `import cognee`."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_ROOT = str(REPO_ROOT / ".cognee_system")
DATA_ROOT = str(REPO_ROOT / ".cognee_data")

_configured = False


def configure_cognee() -> None:
    global _configured
    if _configured:
        return

    load_dotenv(REPO_ROOT / ".env")
    Path(SYSTEM_ROOT).mkdir(parents=True, exist_ok=True)
    Path(DATA_ROOT).mkdir(parents=True, exist_ok=True)

    # Set before importing cognee so the DB subprocess workers inherit the path.
    os.environ.setdefault("SYSTEM_ROOT_DIRECTORY", SYSTEM_ROOT)
    os.environ.setdefault("DATA_ROOT_DIRECTORY", DATA_ROOT)

    import cognee

    cognee.config.system_root_directory(os.environ["SYSTEM_ROOT_DIRECTORY"])
    cognee.config.data_root_directory(os.environ["DATA_ROOT_DIRECTORY"])

    _configured = True


def reset_graph_context() -> None:
    # Writing to a side dataset reroutes bare graph reads to it; reset to the world graph.
    try:
        from cognee.context_global_variables import graph_db_config, current_dataset_id

        graph_db_config.set(None)
        current_dataset_id.set(None)
    except Exception:
        pass


configure_cognee()
