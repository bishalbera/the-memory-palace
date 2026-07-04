from __future__ import annotations

import os
import cognee

from game.bootstrap import reset_graph_context

DATASET = os.environ.get("COGNEE_DATASET", "ravenwood")


# ── recall ────────────────────────────────────────────────────────────────────

async def recall_npc_context(npc_name: str, query: str, session_id: str) -> str:
    try:
        results = await cognee.recall(
            query_text=f"{npc_name}: {query}",
            datasets=[DATASET],
            session_id=session_id,
            only_context=True,
        )
        return _flatten(results)
    except Exception as exc:
        return f"[memory unavailable: {exc}]"


async def recall_room(room_name: str, session_id: str) -> str:
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
    try:
        results = await cognee.recall(
            query_text=f"player relationship and standing with {npc_name}",
            session_id=session_id,
            only_context=True,
        )
        return _flatten(results)
    except Exception:
        return ""


async def recall_why(question: str, session_id: str) -> str:
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


async def recall_accusation_evidence(accused_name: str, session_id: str) -> str:
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


# ── remember ──────────────────────────────────────────────────────────────────

async def remember_turn(turn: int, player_action: str, gm_response: str, session_id: str) -> None:
    text = f"[TURN {turn}]\nDetective: {player_action}\nGM: {gm_response}"
    try:
        await cognee.remember(text, session_id=session_id, dataset_name=DATASET)
    except Exception:
        pass


async def remember_fact_learned(fact_statement: str, source: str, session_id: str) -> None:
    text = f"[PLAYER_LEARNED] Detective discovered: {fact_statement} (source: {source})"
    try:
        await cognee.remember(text, session_id=session_id, dataset_name=DATASET)
    except Exception:
        pass


async def remember_npc_event(
    npc_name: str,
    event_description: str,
    stance_change: str,
    session_id: str,
) -> None:
    text = (
        f"[NPC_EVENT] {npc_name}: {event_description}. "
        f"Stance toward detective: {stance_change}"
    )
    try:
        await cognee.remember(text, session_id=session_id, dataset_name=DATASET)
    except Exception:
        pass


# ── forget: scoped per-suspect dead-end threads ───────────────────────────────

def _deadend_dataset(npc_id: str) -> str:
    return f"deadend_{npc_id}"


async def remember_suspicion(npc_id: str, npc_name: str, reason: str, session_id: str) -> None:
    text = (
        f"[SUSPICION] The detective is building a case against {npc_name} "
        f"as the murderer of Lord Ravenwood. Reason: {reason}"
    )
    try:
        # No session_id: session distillation on a new dataset trips access control (422/403).
        await cognee.remember(text, dataset_name=_deadend_dataset(npc_id), self_improvement=False)
    except Exception:
        pass
    finally:
        reset_graph_context()


async def forget_cleared_suspect(npc_id: str, npc_name: str, session_id: str) -> dict | None:
    try:
        return await cognee.forget(dataset=_deadend_dataset(npc_id))
    except Exception:
        return None
    finally:
        reset_graph_context()


# ── util ──────────────────────────────────────────────────────────────────────

def _flatten(results) -> str:
    # 1.2.2 recall entries carry text in content / answer / context depending on type.
    if not results:
        return ""
    parts = []
    for r in results:
        text = None
        for attr in ("content", "answer", "context", "text"):
            val = getattr(r, attr, None)
            if val:
                text = val
                break
        if text:
            parts.append(str(text).strip())
    return "\n\n".join(parts)
