
from __future__ import annotations

import os
import cognee

DATASET = os.environ.get("COGNEE_DATASET", "ravenwood")


# ── recall helpers ────────────────────────────────────────────────────────────

async def recall_npc_context(npc_name: str, query: str, session_id: str) -> str:
    """
    Recall everything relevant to an NPC interaction:
    the NPC's known facts + relationships from the world graph,
    plus anything the player has already said/learned this session.
    """
    full_query = f"{npc_name}: {query}"
    try:
        results = await cognee.recall(
            query_text=full_query,
            datasets=[DATASET],
            session_id=session_id,
            only_context=True,   # raw context, not LLM answer — GM does the LLM step
        )
        return _flatten(results)
    except Exception as exc:
        return f"[memory unavailable: {exc}]"


async def recall_room(room_name: str, session_id: str) -> str:
    """Recall clues and events associated with a location."""
    try:
        results = await cognee.recall(
            query_text=f"clues and evidence in the {room_name}",
            datasets=[DATASET],
            session_id=session_id,
            only_context=True,
        )
        return _flatten(results)
    except Exception as exc:
        return f"[memory unavailable: {exc}]"


async def recall_player_progress(query: str, session_id: str) -> str:
    """What has the player already learned that's relevant to this query?"""
    try:
        results = await cognee.recall(
            query_text=query,
            session_id=session_id,
            only_context=True,
        )
        return _flatten(results)
    except Exception as exc:
        return f"[memory unavailable: {exc}]"


async def recall_npc_standing(npc_name: str, session_id: str) -> str:
    """Retrieve the current relationship between player and an NPC."""
    try:
        results = await cognee.recall(
            query_text=f"player relationship and standing with {npc_name}",
            session_id=session_id,
            only_context=True,
        )
        return _flatten(results)
    except Exception as exc:
        return ""


async def recall_why(question: str, session_id: str) -> str:
    """
    Explainable memory — used by the `why` command.
    Retrieves the causal chain behind an NPC's current behaviour.
    """
    try:
        results = await cognee.recall(
            query_text=question,
            datasets=[DATASET],
            session_id=session_id,
            only_context=True,
        )
        return _flatten(results)
    except Exception as exc:
        return f"[memory unavailable: {exc}]"


# ── remember helpers ──────────────────────────────────────────────────────────

async def remember_turn(
    turn: int,
    player_action: str,
    gm_response: str,
    session_id: str,
) -> None:
    """Record a completed turn so future recalls are session-aware."""
    text = (
        f"[TURN {turn}]\n"
        f"Detective: {player_action}\n"
        f"GM: {gm_response}"
    )
    try:
        await cognee.remember(text, session_id=session_id, dataset_name=DATASET)
    except Exception:
        pass  # memory failure must never crash the game


async def remember_fact_learned(fact_statement: str, source: str, session_id: str) -> None:
    """Record a specific fact the player has now uncovered."""
    text = f"[PLAYER_LEARNED] Detective discovered: {fact_statement} (source: {source})"
    try:
        await cognee.remember(text, session_id=session_id, dataset_name=DATASET)
    except Exception:
        pass


async def recall_accusation_evidence(accused_name: str, session_id: str) -> str:
    """Pull everything the player has discovered specifically about the accused."""
    try:
        results = await cognee.recall(
            query_text=f"evidence against {accused_name} motive means opportunity alibi",
            datasets=[DATASET],
            session_id=session_id,
            only_context=True,
        )
        return _flatten(results)
    except Exception:
        return ""


async def forget_cleared_suspect(npc_name: str, session_id: str) -> None:
    """
    After a false accusation, prune the red-herring thread for this suspect
    from session memory so future recalls aren't polluted by dead ends.
    Demonstrates cognee.forget() — the fourth pillar of the CRUD memory API.
    """
    try:
        await cognee.forget(
            text=f"Detective suspected {npc_name} of murder",
            session_id=session_id,
        )
    except Exception:
        pass  # forget failure must never crash the game


async def remember_npc_event(
    npc_name: str,
    event_description: str,
    stance_change: str,
    session_id: str,
) -> None:
    """
    Record a notable player–NPC event for gossip propagation (Phase 4).
    stance_change: 'hostile' | 'wary' | 'cooperative' | 'neutral'
    """
    text = (
        f"[NPC_EVENT] {npc_name}: {event_description}. "
        f"Stance toward detective: {stance_change}"
    )
    try:
        await cognee.remember(text, session_id=session_id, dataset_name=DATASET)
    except Exception:
        pass


# ── util ──────────────────────────────────────────────────────────────────────

def _flatten(results) -> str:
    """Collapse recall() results to a single context string."""
    if not results:
        return ""
    parts = []
    for r in results:
        text = getattr(r, "text", getattr(r, "answer", getattr(r, "context", str(r))))
        if text:
            parts.append(str(text).strip())
    return "\n\n".join(parts)
