"""Game Master narration layer. Dramatizes retrieved facts; never invents them."""

from __future__ import annotations

import os
import re
from typing import Any

import anthropic

from scenario.ravenwood import NPCS_BY_ID, LOCATIONS_BY_ID, FACTS_BY_ID, SOLUTION

_RAW_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-haiku-4-5-20251001")
GM_MODEL = _RAW_MODEL.replace("anthropic/", "")
GM_NARRATION_MODEL = os.environ.get("GM_MODEL", "claude-sonnet-4-6")

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(
            api_key=os.environ.get("LLM_API_KEY", ""),
        )
    return _client


_SYSTEM = """\
You are the Game Master for "A Death at Ravenwood Manor," a 1899 English country-house \
murder mystery. Lord Edmund Ravenwood was found dead in his locked study after a dinner party. \
The player is the detective.

IRONCLAD RULES:
1. You speak in period-appropriate Victorian English — formal, atmospheric, measured.
2. When generating NPC dialogue, the NPC may ONLY say things consistent with their \
   Available Knowledge below. They must not volunteer facts they do not know.
3. If a fact appears under "NPC lies about", the NPC must actively deny it or redirect.
4. If a fact appears under "NPC keeps private", be evasive — the NPC deflects unless \
   the player has clearly cornered them (note this in the context if so).
5. Never break the fourth wall. Never refer to "the game" or "the rules".
6. Keep NPC dialogue to 3-5 sentences. Room/scene descriptions up to 6 sentences.
7. End NPC responses with one subtle non-verbal cue (expression, gesture, tone shift).
8. You may not invent new characters, rooms, or facts not present in the context.\
"""


async def _call(system: str, user: str, max_tokens: int = 600) -> str:
    client = _get_client()
    msg = await client.messages.create(
        model=GM_NARRATION_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


# ── opening ───────────────────────────────────────────────────────────────────

async def narrate_opening() -> str:
    prompt = (
        "Narrate the opening scene. The detective has just arrived at Ravenwood Manor. "
        "It is a cold October evening in 1899. The butler, Thomas Harrington, meets them "
        "at the door and delivers the terrible news: Lord Edmund Ravenwood has been found "
        "dead in his locked study. A dinner party of eleven guests is gathered in the "
        "entrance hall, shocked. Set the scene vividly in 5-6 sentences, then tell the "
        "detective they may begin their investigation. Mention they can TALK TO suspects, "
        "SEARCH rooms, GO TO another room, type WHY [question] to understand behaviour, "
        "or ACCUSE [name] when ready."
    )
    return await _call(_SYSTEM, prompt, max_tokens=450)


# ── NPC dialogue ──────────────────────────────────────────────────────────────

async def narrate_npc_response(
    npc_id: str,
    player_input: str,
    cognee_context: str,
    npc_standing: str,
    game_state: Any,
) -> tuple[str, list[str]]:
    """Returns (dialogue, revealed_fact_ids, event_type)."""
    npc = NPCS_BY_ID.get(npc_id)
    if not npc:
        return "That person doesn't seem to be here.", [], None

    # Build fact blocks showing BOTH id and content so the LLM can echo IDs reliably
    def _fact_line(fid: str) -> str:
        fact = FACTS_BY_ID.get(fid)
        content = fact.statement if fact else fid
        return f"  - [{fid}] {content}"

    freely_text   = "\n".join(_fact_line(f) for f in npc.will_share_freely) or "  (none)"
    pressure_text = "\n".join(_fact_line(f) for f in npc.shares_under_pressure) or "  (none)"
    lies_text     = "\n".join(_fact_line(f) for f in npc.lies_about) or "  (none)"

    stance_note = npc_standing or "neutral — no prior interactions"

    all_names = ", ".join(n.name for n in NPCS_BY_ID.values())

    user_prompt = f"""\
NPC: {npc.name} ({npc.role})
Persona: {npc.public_persona}
Current stance toward detective: {stance_note}

VALID PEOPLE IN THIS SCENARIO (no others exist — do not invent names):
{all_names}

AVAILABLE KNOWLEDGE — shares freely (you may reveal these):
{freely_text}

AVAILABLE KNOWLEDGE — shares only under direct pressure:
{pressure_text}

LIES ABOUT — actively deny or redirect if asked:
{lies_text}

Additional context from world memory:
{cognee_context or "(none)"}

The detective says to {npc.name}: "{player_input}"

Respond in character as {npc.name}. Rules:
- Only reference facts from AVAILABLE KNOWLEDGE above. Invent nothing new.
- Only mention people from the VALID PEOPLE list above. Never invent guest names.
- Actively deny or misdirect anything in LIES ABOUT.
- Be evasive about "pressure only" facts unless directly cornered.
- End with exactly one non-verbal cue in italics (expression, gesture, or tone).
- Do NOT include any markdown headers, horizontal rules, or separators.

Then on a NEW LINE output exactly:
REVEALS: [comma-separated fact IDs you just disclosed, e.g. f_calloway_argument, f_thatch_fired — or NONE]
EVENT_TYPE: [NONE | THREAT | EXPOSURE | ACCUSATION | CONFRONTATION | HELP — what the detective just did to this NPC]\
"""

    raw = await _call(_SYSTEM, user_prompt, max_tokens=450)

    # Parse structured tags — search anywhere in response, not just line-start
    revealed: list[str] = []
    event_type: str | None = None
    clean_lines: list[str] = []

    for line in raw.split("\n"):
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("REVEALS:"):
            tag = stripped[8:].strip()
            if tag.upper() != "NONE":
                revealed = [r.strip() for r in tag.split(",") if r.strip()]
        elif upper.startswith("EVENT_TYPE:"):
            tag = stripped[11:].strip().upper()
            if tag != "NONE":
                event_type = tag
        else:
            # strip trailing --- separators the LLM sometimes adds
            if stripped not in ("---", "---\"", "\"---\""):
                clean_lines.append(line)

    # Fallback: auto-mark will_share_freely facts as revealed (the NPC was talking)
    if not revealed:
        revealed = list(npc.will_share_freely)

    dialogue = "\n".join(clean_lines).strip().strip('"').strip("---").strip()
    return dialogue, revealed, event_type


# ── room description ──────────────────────────────────────────────────────────

async def narrate_room(
    room_id: str,
    cognee_context: str,
    visited_before: bool,
) -> str:
    location = LOCATIONS_BY_ID.get(room_id)
    if not location:
        return "You find yourself in an unfamiliar part of the manor."

    verb = "You return to" if visited_before else "You enter"
    user_prompt = (
        f"{verb} the {location.name}.\n"
        f"Room description: {location.description}\n"
        f"Context from world memory:\n{cognee_context or '(nothing notable recalled)'}\n\n"
        "Describe what the detective observes. Mention any visible or recently revealed clues "
        "from the context. Keep it to 4-5 sentences. Do not invent new clues."
    )
    return await _call(_SYSTEM, user_prompt, max_tokens=300)


async def narrate_search(
    room_id: str,
    search_target: str,
    cognee_context: str,
) -> tuple[str, list[str]]:
    """Returns (narration, list of clue_ids found)."""
    location = LOCATIONS_BY_ID.get(room_id)
    room_name = location.name if location else room_id

    # Tell the LLM which clues are physically present so it can "find" the right ones
    from scenario.ravenwood import CLUES_BY_ID, LOCATIONS_BY_ID as LOCS
    loc = LOCS.get(room_id)
    present_clues = ""
    if loc and loc.clue_ids:
        lines = [f"  - [{cid}] {CLUES_BY_ID[cid].description}" for cid in loc.clue_ids if cid in CLUES_BY_ID]
        present_clues = "Clues physically present in this room:\n" + "\n".join(lines)

    user_prompt = (
        f"The detective searches: \"{search_target}\" in the {room_name}.\n"
        f"{present_clues}\n"
        f"World memory context:\n{cognee_context or '(nothing recalled)'}\n\n"
        "Describe what the detective finds. Be vivid and specific about physical details. "
        "If a relevant clue is present and the search target matches it, describe discovering it. "
        "3-4 sentences. Do not invent new clues beyond those listed above.\n\n"
        "Then on a NEW LINE output exactly:\n"
        "CLUES_FOUND: [comma-separated clue IDs discovered, or NONE]"
    )
    raw = await _call(_SYSTEM, user_prompt, max_tokens=350)

    clues_found: list[str] = []
    clean_lines: list[str] = []
    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped.upper().startswith("CLUES_FOUND:"):
            tag = stripped[12:].strip()
            if tag.upper() != "NONE":
                clues_found = [c.strip() for c in tag.split(",") if c.strip()]
        else:
            if stripped not in ("---", "---\""):
                clean_lines.append(line)
    return "\n".join(clean_lines).strip(), clues_found


# ── why command ───────────────────────────────────────────────────────────────

async def narrate_why(question: str, cognee_context: str) -> str:
    user_prompt = (
        f"The detective asks for an explanation: \"{question}\"\n\n"
        f"Memory context (causal chain):\n{cognee_context or '(insufficient evidence so far)'}\n\n"
        "As the Game Master (not as an NPC), narrate the causal chain that explains the "
        "behaviour or situation. Reference specific events and relationships from the context. "
        "If there isn't enough evidence yet, say so and hint what the detective might do next. "
        "3-4 sentences max."
    )
    return await _call(_SYSTEM, user_prompt, max_tokens=250)


# ── accusation ────────────────────────────────────────────────────────────────

async def narrate_accusation(
    accused_name: str,
    accused_id: str,
    player_learned_facts: list[str],
    is_correct: bool,
    missing_facts: list[str],
    evidence_brief: str = "",
) -> str:
    """Generate the accusation outcome narration."""
    solution = SOLUTION

    if is_correct:
        evidence_block = (
            f"\nEvidence the detective has assembled:\n{evidence_brief}\n"
            if evidence_brief else ""
        )
        user_prompt = (
            f"The detective accuses {accused_name} — and they are CORRECT.\n\n"
            f"Solution narrative: {solution['narrative']}\n"
            f"{evidence_block}\n"
            "Narrate the dramatic confrontation. Gerald initially denies it with bluster, "
            "but as the detective lays out the specific evidence they gathered, he falters "
            "and finally breaks. Describe his confession in 6-8 atmospheric sentences. "
            "Then narrate the aftermath: the constable is summoned, the guests react in "
            "shocked silence, and the manor finally exhales. End with a single closing "
            "line about justice being served."
        )
    elif not is_correct and accused_id == solution["murderer_id"]:
        # Right person, insufficient evidence — Gerald must repeat his real alibi, not invent one
        accused_npc = NPCS_BY_ID.get(accused_id)
        real_alibi = accused_npc.alibi if accused_npc else ""
        missing_summary = "; ".join(missing_facts[:3]) if missing_facts else "key evidence"
        all_names = ", ".join(n.name for n in NPCS_BY_ID.values())
        user_prompt = (
            f"The detective accuses {accused_name} — correct instinct, but insufficient "
            f"evidence to convict yet.\n"
            f"Evidence still needed: {missing_summary}\n"
            f"{accused_name}'s stated alibi (use this exactly — do not invent a new one): "
            f"\"{real_alibi}\"\n\n"
            f"Valid character names in this scene (use no others): {all_names}\n\n"
            "Gerald maintains his composure, repeats his stated alibi verbatim, and "
            "demands the detective produce proof. The other guests shift uncomfortably "
            "but say nothing definitive. In 4-5 sentences, describe his measured denial "
            "and the social pressure on the detective. Hint they must find the specific "
            "missing evidence listed above. The investigation continues."
        )
    else:
        correct_name = solution["murderer_name"]
        missing_summary = ", ".join(missing_facts[:3]) if missing_facts else "key evidence"
        all_names = ", ".join(n.name for n in NPCS_BY_ID.values())
        user_prompt = (
            f"The detective accuses {accused_name} — but they are WRONG.\n"
            f"The true murderer is {correct_name}.\n"
            f"The detective still needs to find: {missing_summary}\n\n"
            f"Valid character names in this scene (use no others): {all_names}\n\n"
            "The accused reacts with shock and genuine indignation — they are innocent. "
            "Only refer to people by the names in the valid list above. "
            "Witnesses murmur. The detective's credibility wavers slightly. In 4-5 "
            "sentences, describe the scene and hint (without naming the real culprit) "
            "that the detective should look elsewhere. The investigation continues."
        )
    return await _call(_SYSTEM, user_prompt, max_tokens=550)


async def narrate_epilogue(turns: int, facts_found: int, total_facts: int) -> str:
    """One-paragraph GM closing after the case is solved."""
    user_prompt = (
        f"The case is solved. The detective took {turns} turns and uncovered "
        f"{facts_found} of {total_facts} facts in the world.\n\n"
        "As the Game Master, deliver a brief atmospheric epilogue (3 sentences). "
        "Describe the manor settling back into silence after the constable departs "
        "with Gerald in custody. Do not repeat facts already stated in the confession — "
        "focus on the emotional aftermath and the weight of what justice means in this place."
    )
    return await _call(_SYSTEM, user_prompt, max_tokens=200)


# ── improve / between-scene enrichment ───────────────────────────────────────

async def run_improve(session_id: str, dataset: str) -> None:
    import cognee
    try:
        await cognee.improve(
            dataset=dataset,
            session_ids=[session_id],
            build_global_context_index=False,
            run_in_background=False,
        )
    except Exception:
        pass


# ── utility ───────────────────────────────────────────────────────────────────

def identify_npc_in_input(text: str) -> str | None:
    # Prefer full-name matches over shared tokens to avoid last-name/title collisions.
    text_lower = text.lower()
    best_id, best_score = None, 0

    for npc in NPCS_BY_ID.values():
        name_lower = npc.name.lower()
        if name_lower in text_lower:
            score = 100 + len(name_lower)
        else:
            tokens = [t for t in name_lower.split() if len(t) > 3]
            score = sum(1 for t in tokens if t in text_lower)

        if score > best_score:
            best_score = score
            best_id = npc.id

    return best_id if best_score > 0 else None


def identify_room_in_input(text: str) -> str | None:
    """Return room_id if any room name appears in the player's input."""
    text_lower = text.lower()
    for loc in LOCATIONS_BY_ID.values():
        if loc.name.lower() in text_lower:
            return loc.id
        # also match short keywords
        for word in loc.name.lower().split():
            if len(word) > 4 and word in text_lower:
                return loc.id
    return None
