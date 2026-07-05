"""Core game loop: ties memory, narration, and player input together."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from scenario.ravenwood import (
    NPCS_BY_ID, LOCATIONS_BY_ID, CLUES_BY_ID, FACTS_BY_ID, SOLUTION,
)
import game.memory as mem
import game.gm as gm
from game.gossip import propagate, format_gossip_report, check_contradictions, detect_contradictions

DATASET = os.environ.get("COGNEE_DATASET", "ravenwood")
IMPROVE_EVERY = 3   # run cognee.improve() every N turns

# Backend stances → the four the UI renders.
_UI_STANCE = {
    "hostile": "hostile", "wary": "wary", "suspicious": "wary",
    "cooperative": "warm", "neutral": "neutral",
}

# ── game state ────────────────────────────────────────────────────────────────

@dataclass
class GameState:
    session_id: str
    current_room: str = "loc_entrance_hall"
    visited_rooms: set = field(default_factory=set)
    player_learned_facts: list[str] = field(default_factory=list)
    player_found_clues: list[str] = field(default_factory=list)
    npc_stances: dict[str, str] = field(default_factory=dict)
    contradictions_shown: set = field(default_factory=set)
    cleared_suspects: list[str] = field(default_factory=list)
    gossip_reasons: dict[str, dict] = field(default_factory=dict)  # npc_id → causal chain for `why`
    turn: int = 0
    game_over: bool = False
    seed: int = 42
    # turn-scoped structured data for the web UI (cleared each turn)
    last_gossip: dict | None = None
    last_why_chain: list[str] | None = None
    last_contradiction: dict | None = None
    last_accusation: dict | None = None
    last_speaker: str | None = None


# ── evidence evaluation ───────────────────────────────────────────────────────

def _build_evidence_brief(accused_id: str, state: GameState) -> str:
    """Solution-chain facts the player has discovered, to ground accusation narration."""
    from scenario.ravenwood import SOLUTION
    full_chain = SOLUTION["full_chain"]
    found = set(state.player_learned_facts)
    lines = []
    for fid in full_chain:
        fact = FACTS_BY_ID.get(fid)
        if fact and fid in found:
            lines.append(f"  • {fact.statement}")
    return "\n".join(lines) if lines else ""


def _compute_rating(chain_found: int, chain_total: int) -> str:
    pct = chain_found / chain_total if chain_total else 0
    if pct == 1.0:   return "Master Detective"
    if pct >= 0.75:  return "Seasoned Inspector"
    if pct >= 0.5:   return "Competent Investigator"
    return "Lucky Intuition"


def _show_case_file(state: GameState) -> None:
    """Print the structured post-game evidence dossier."""
    from scenario.ravenwood import SOLUTION

    full_chain = SOLUTION["full_chain"]
    found_set = set(state.player_learned_facts)
    found_chain = [f for f in full_chain if f in found_set]

    motive_ids = ["f_gerald_embezzled", "f_ravenwood_discovered_gerald", "f_will_change"]
    means_ids  = ["f_foxglove_missing", "f_gerald_poisoned_decanter", "f_digitalis_in_glass"]
    opp_ids    = ["f_sophie_saw_gerald", "f_gerald_false_alibi"]

    W = 65
    print("\n" + "═" * W)
    print("   CASE FILE — A DEATH AT RAVENWOOD MANOR")
    print("─" * W)
    print("   Evidence Chain\n")

    def _section(label: str, ids: list[str]) -> None:
        print(f"   {label}")
        for fid in ids:
            fact = FACTS_BY_ID.get(fid)
            if fact:
                marker = "✓" if fid in found_set else "✗"
                stmt = (fact.statement[:57] + "…") if len(fact.statement) > 57 else fact.statement
                print(f"   {marker}  {stmt}")
        print()

    _section("MOTIVE", motive_ids)
    _section("MEANS",  means_ids)
    _section("OPPORTUNITY", opp_ids)

    print("─" * W)
    print("   Investigation Summary\n")
    print(f"   Turns taken    : {state.turn}")
    print(f"   Facts uncovered: {len(state.player_learned_facts)}/{len(FACTS_BY_ID)}")
    print(f"   Clues found    : {len(state.player_found_clues)}/{len(CLUES_BY_ID)}")
    print(f"   Rooms explored : {len(state.visited_rooms)}/{len(LOCATIONS_BY_ID)}")
    print(f"   Solution chain : {len(found_chain)}/{len(full_chain)} links proven")
    print()
    print(f"   Rating: {_compute_rating(len(found_chain), len(full_chain))}")
    print("═" * W)


# ── intent parser ─────────────────────────────────────────────────────────────

def _intent(text: str) -> tuple[str, str]:
    t = text.strip()
    tl = t.lower()

    if tl in ("quit", "exit", "q"):
        return "quit", ""
    if tl in ("help", "h", "?"):
        return "help", ""
    if tl in ("notebook", "notes", "clues", "evidence"):
        return "notebook", ""
    if tl in ("status", "progress", "map"):
        return "status", ""

    for prefix in ("accuse ", "i accuse "):
        if tl.startswith(prefix):
            return "accuse", t[len(prefix):].strip()

    if tl.startswith("why ") or tl == "why":
        return "why", t[4:].strip()

    for prefix in ("go to ", "go ", "move to ", "enter ", "walk to ", "head to "):
        if tl.startswith(prefix):
            return "go", t[len(prefix):].strip()

    for prefix in ("search ", "examine ", "look at ", "inspect ", "check "):
        if tl.startswith(prefix):
            return "search", t[len(prefix):].strip()

    talk_verbs = ("ask ", "talk to ", "speak to ", "confront ", "tell ",
                  "question ", "show ", "reveal to ")
    if any(tl.startswith(v) for v in talk_verbs):
        return "talk", t

    return "freeform", t


# ── fact tracking ─────────────────────────────────────────────────────────────

def _record_facts(
    fact_ids: list[str],
    source: str,
    state: GameState,
) -> list[str]:
    """Add new fact_ids to state, return only the newly added ones."""
    newly_learned: list[str] = []
    for fid in fact_ids:
        if fid and fid not in state.player_learned_facts and fid in FACTS_BY_ID:
            state.player_learned_facts.append(fid)
            newly_learned.append(fid)
    return newly_learned


# ── gossip integration ────────────────────────────────────────────────────────

async def _apply_gossip(
    npc_id: str,
    event_type: str | None,
    description: str,
    state: GameState,
) -> str | None:
    """Run gossip propagation and remember the event. Returns notice string or None."""
    if not event_type or event_type == "NONE":
        return None

    event = await propagate(npc_id, event_type, description, state.npc_stances)
    notice = format_gossip_report(event)

    if event.affected:
        for aid, (_old, new) in event.affected.items():
            path_ids = event.paths.get(aid, [event.source_npc_id, aid])
            state.gossip_reasons[aid] = {
                "source_name": event.source_npc_name,
                "source_id": event.source_npc_id,
                "event_type": event.event_type,
                "description": description,
                "stance": new,
                "path_ids": path_ids,
                "path_names": [
                    NPCS_BY_ID[s].name if s in NPCS_BY_ID else s for s in path_ids
                ],
            }

        # Longest path among the affected is the thread to draw on the board.
        longest = max(event.paths.values(), key=len, default=[event.source_npc_id])
        state.last_gossip = {
            "origin": event.source_npc_id,
            "chain": longest,
            "affected": [
                {"id": aid, "to": _UI_STANCE.get(new, new)}
                for aid, (_old, new) in event.affected.items()
            ],
        }

        await mem.remember_npc_event(
            npc_name=event.source_npc_name,
            event_description=description,
            stance_change=event_type.lower(),
            session_id=state.session_id,
        )

    return notice


# ── turn handlers ─────────────────────────────────────────────────────────────

async def _handle_talk(text: str, state: GameState) -> tuple[str, str | None]:
    """Returns (response_text, gossip_notice_or_None)."""
    npc_id = gm.identify_npc_in_input(text)
    if not npc_id:
        return "There is no one by that name here. Who did you wish to speak with?", None

    npc = NPCS_BY_ID[npc_id]
    context = await mem.recall_npc_context(npc.name, text, state.session_id)
    standing = state.npc_stances.get(npc_id, "neutral")

    dialogue, revealed_ids, event_type = await gm.narrate_npc_response(
        npc_id=npc_id,
        player_input=text,
        cognee_context=context,
        npc_standing=standing,
        game_state=state,
    )

    # Record facts learned from this interaction
    newly_learned = _record_facts(revealed_ids, npc.name, state)
    for fid in newly_learned:
        await mem.remember_fact_learned(
            FACTS_BY_ID[fid].statement, npc.name, state.session_id
        )

    state.last_speaker = npc.name
    response = f"{npc.name}: \"{dialogue}\""

    gossip_notice = await _apply_gossip(
        npc_id=npc_id,
        event_type=event_type,
        description=f"Detective interacted with {npc.name}: {text[:80]}",
        state=state,
    )

    return response, gossip_notice


async def _handle_search(target: str, state: GameState) -> tuple[str, None]:
    # Auto-navigate if the search target names a room different from the current one.
    # "examine the brandy glass in the study" should search the study, not the current room.
    mentioned_room = gm.identify_room_in_input(target)
    if mentioned_room and mentioned_room != state.current_room:
        state.visited_rooms.add(mentioned_room)
        state.current_room = mentioned_room

    loc = LOCATIONS_BY_ID.get(state.current_room)
    room_name = loc.name if loc else state.current_room
    room_ctx = await mem.recall_room(room_name, state.session_id)

    narration, clue_ids = await gm.narrate_search(
        room_id=state.current_room,
        search_target=target,
        cognee_context=room_ctx,
    )

    for cid in clue_ids:
        if cid not in state.player_found_clues and cid in CLUES_BY_ID:
            state.player_found_clues.append(cid)
            clue = CLUES_BY_ID[cid]
            newly = _record_facts([clue.supports_fact_id], f"clue in {room_name}", state)
            for fid in newly:
                await mem.remember_fact_learned(
                    FACTS_BY_ID[fid].statement, f"physical clue: {cid}", state.session_id
                )

    return narration, None


async def _handle_go(destination: str, state: GameState) -> tuple[str, None]:
    room_id = gm.identify_room_in_input(destination)
    if not room_id:
        return (
            "The manor has: entrance hall, study, dining room, library, east garden, "
            "kitchen, guest corridor, conservatory, and chapel. Where did you wish to go?"
        ), None

    visited = room_id in state.visited_rooms
    state.visited_rooms.add(room_id)
    state.current_room = room_id

    loc = LOCATIONS_BY_ID[room_id]
    room_ctx = await mem.recall_room(loc.name, state.session_id)
    narration = await gm.narrate_room(room_id, room_ctx, visited_before=visited)
    return narration, None


async def _handle_why(question: str, state: GameState) -> tuple[str, None]:
    # Reconstruct the causal chain from the gossip traversal path when we have one.
    chain_context = ""
    npc_id = gm.identify_npc_in_input(question)
    reason = state.gossip_reasons.get(npc_id) if npc_id else None
    if reason:
        state.last_why_chain = reason["path_ids"]
        path = " → ".join(reason["path_names"])
        npc_name = NPCS_BY_ID[npc_id].name
        chain_context = (
            "CAUSAL CHAIN (reconstructed from the social graph, do not contradict):\n"
            f"The detective's action toward {reason['source_name']} "
            f"({reason['event_type'].lower()}) travelled along social ties: {path}. "
            f"Word reached {npc_name}, who now regards the detective as "
            f"'{reason['stance']}'.\n\n"
        )

    recall_ctx = await mem.recall_why(question or "why is this happening", state.session_id)
    context = (chain_context + recall_ctx).strip()
    narration = await gm.narrate_why(question, context)
    return narration, None


async def _handle_notebook(state: GameState) -> tuple[str, None]:
    """Show the detective's current evidence notebook."""
    W = 63
    lines = ["─" * W, "  DETECTIVE'S NOTEBOOK", "─" * W, ""]

    if not state.player_learned_facts:
        lines.append("  (No facts recorded yet)")
    else:
        lines.append("  Facts Discovered:")
        for fid in state.player_learned_facts:
            fact = FACTS_BY_ID.get(fid)
            if fact:
                stmt = (fact.statement[:60] + "…") if len(fact.statement) > 60 else fact.statement
                lines.append(f"    • {stmt}")

    if state.player_found_clues:
        lines.append("")
        lines.append("  Physical Clues:")
        for cid in state.player_found_clues:
            clue = CLUES_BY_ID.get(cid)
            if clue:
                desc = (clue.description[:60] + "…") if len(clue.description) > 60 else clue.description
                lines.append(f"    • {desc}")

    if state.cleared_suspects:
        lines.append("")
        lines.append("  Cleared Suspects (false accusations):")
        for npc_id in state.cleared_suspects:
            npc = NPCS_BY_ID.get(npc_id)
            if npc:
                lines.append(f"    ✗ {npc.name} — eliminated")

    lines.extend(["", "─" * W])
    return "\n".join(lines), None


async def _handle_status(state: GameState) -> tuple[str, None]:
    """Show current investigation status and NPC stances."""
    W = 63
    loc = LOCATIONS_BY_ID.get(state.current_room)
    loc_name = loc.name if loc else state.current_room

    lines = [
        "─" * W, "  INVESTIGATION STATUS", "─" * W, "",
        f"  Location       : {loc_name}",
        f"  Turn           : {state.turn}",
        f"  Facts known    : {len(state.player_learned_facts)}/{len(FACTS_BY_ID)}",
        f"  Clues found    : {len(state.player_found_clues)}/{len(CLUES_BY_ID)}",
        f"  Rooms explored : {len(state.visited_rooms)}/{len(LOCATIONS_BY_ID)}",
    ]

    if state.npc_stances:
        lines.extend(["", "  Suspect Stances:"])
        for npc_id, stance in sorted(state.npc_stances.items()):
            npc = NPCS_BY_ID.get(npc_id)
            if npc:
                lines.append(f"    {npc.name:<26} {stance}")

    lines.extend(["", "─" * W])
    return "\n".join(lines), None


async def _handle_accuse(name: str, state: GameState) -> tuple[str, str | None]:
    if not name:
        return "Whom do you wish to accuse? Type: ACCUSE [name]", None

    # Same scoring as identify_npc_in_input: prefer longer full-name matches
    # to avoid "Ashworth" matching Lady Victoria before Colonel Gerald.
    accused_id: str | None = None
    name_lower = name.lower()
    best_score = 0
    for npc in NPCS_BY_ID.values():
        npc_name_lower = npc.name.lower()
        if npc_name_lower in name_lower:
            score = 100 + len(npc_name_lower)
        else:
            tokens = [t for t in npc_name_lower.split() if len(t) > 3]
            score = sum(1 for t in tokens if t in name_lower)
        if score > best_score:
            best_score = score
            accused_id = npc.id

    if not accused_id:
        return f"There is no suspect by the name '{name}'.", None

    accused_npc = NPCS_BY_ID[accused_id]
    is_correct_person = accused_id == SOLUTION["murderer_id"]

    required = set(SOLUTION["required_facts"])
    learned  = set(state.player_learned_facts)
    missing  = [FACTS_BY_ID[fid].statement for fid in required - learned if fid in FACTS_BY_ID]

    has_evidence = not missing
    is_win = is_correct_person and has_evidence

    evidence_brief = _build_evidence_brief(accused_id, state)

    state.game_over = is_win
    narration = await gm.narrate_accusation(
        accused_name=accused_npc.name,
        accused_id=accused_id,
        player_learned_facts=state.player_learned_facts,
        is_correct=is_win,
        missing_facts=missing,
        evidence_brief=evidence_brief,
    )

    # Public accusation propagates through accused's social network (gossip mechanic)
    gossip_notice = await _apply_gossip(
        npc_id=accused_id,
        event_type="ACCUSATION",
        description=f"Detective publicly accused {accused_npc.name} of murder",
        state=state,
    )

    await mem.remember_suspicion(
        accused_id,
        accused_npc.name,
        reason=f"formally accused at turn {state.turn}",
        session_id=state.session_id,
    )

    if not is_correct_person and accused_id not in state.cleared_suspects:
        state.cleared_suspects.append(accused_id)
        await mem.forget_cleared_suspect(accused_id, accused_npc.name, state.session_id)

    state.last_accusation = {
        "accused_id": accused_id,
        "accused_name": accused_npc.name,
        "correct": is_win,
        "correct_person": is_correct_person,
        "path_labels": _accusation_path_labels(state) if is_win else [],
    }

    return narration, gossip_notice


# ── web UI structured data ────────────────────────────────────────────────────

_ACCUSE_PATH = [
    ("MOTIVE", ["f_gerald_embezzled", "f_ravenwood_discovered_gerald", "f_will_change"]),
    ("MEANS", ["f_foxglove_missing", "f_gerald_poisoned_decanter", "f_digitalis_in_glass"]),
    ("OPPORTUNITY", ["f_sophie_saw_gerald", "f_gerald_false_alibi"]),
]


def _accusation_path_labels(state: GameState) -> list[str]:
    found = set(state.player_learned_facts)
    labels: list[str] = []
    for category, ids in _ACCUSE_PATH:
        fid = next((f for f in ids if f in found), None)
        if fid:
            stmt = FACTS_BY_ID[fid].statement
            stmt = stmt[:70] + "…" if len(stmt) > 70 else stmt
            labels.append(f"{category} — {stmt}")
    return labels


def _ui_stances(state: GameState) -> dict[str, str]:
    return {nid: _UI_STANCE.get(st, st) for nid, st in state.npc_stances.items()}


def _clue_objects(state: GameState) -> list[dict]:
    out: list[dict] = []
    for cid in state.player_found_clues:
        clue = CLUES_BY_ID.get(cid)
        if not clue:
            continue
        loc = LOCATIONS_BY_ID.get(clue.location_id)
        name = cid.replace("clue_", "").replace("_", " ").title()
        out.append({
            "id": cid,
            "name": name,
            "note": clue.description,
            "found_at": loc.name if loc else clue.location_id,
        })
    return out


async def _handle_freeform(text: str, state: GameState) -> tuple[str, str | None]:
    npc_id = gm.identify_npc_in_input(text)
    if npc_id:
        return await _handle_talk(text, state)
    room_id = gm.identify_room_in_input(text)
    if room_id:
        return await _handle_go(text, state)
    return await _handle_search(text, state)


# ── help ──────────────────────────────────────────────────────────────────────

HELP_TEXT = """\
┌─────────────────────────────────────────────────────────────────┐
│  RAVENWOOD MANOR — DETECTIVE COMMANDS                           │
├─────────────────────────────────────────────────────────────────┤
│  TALK TO [name] / ASK [name] about ...  — interview a suspect  │
│  SEARCH [target]                        — examine something     │
│  GO TO [room]                           — move to another room  │
│  WHY [question]                         — explain behaviour     │
│  ACCUSE [name]                          — make your accusation  │
│  NOTEBOOK                               — review your evidence  │
│  STATUS                                 — stances & progress    │
│  HELP                                   — show this message     │
│  QUIT                                   — end the session       │
├─────────────────────────────────────────────────────────────────┤
│  Rooms: entrance hall · study · dining room · library           │
│         east garden · kitchen · guest corridor                  │
│         conservatory · chapel                                   │
└─────────────────────────────────────────────────────────────────┘"""


# ── main loop ─────────────────────────────────────────────────────────────────

# ── Web API interface ─────────────────────────────────────────────────────────

@dataclass
class TurnResult:
    response: str
    gossip: str | None
    contradictions: list[str]
    game_over: bool
    improved: bool
    turn: int
    facts_count: int
    total_facts: int
    clues_count: int
    total_clues: int
    intent_type: str
    is_free_action: bool = False
    speaker: str | None = None
    stances: dict = field(default_factory=dict)
    gossip_event: dict | None = None
    why_chain: list | None = None
    contradiction: dict | None = None
    accusation: dict | None = None
    clues: list = field(default_factory=list)
    location: str = ""


async def process_turn(state: GameState, raw: str) -> TurnResult:
    """Process one player input and return a TurnResult (used by the web backend)."""
    intent_type, remainder = _intent(raw)
    is_free = intent_type in ("help", "notebook", "status", "quit")

    # Clear turn-scoped structured data.
    state.last_gossip = None
    state.last_why_chain = None
    state.last_contradiction = None
    state.last_accusation = None
    state.last_speaker = None

    if not is_free:
        state.turn += 1

    gossip_notice: str | None = None

    if intent_type == "quit":
        response = "You close your notebook. The mystery of Ravenwood Manor remains unsolved."
    elif intent_type == "help":
        response = HELP_TEXT
    elif intent_type == "notebook":
        response, _ = await _handle_notebook(state)
    elif intent_type == "status":
        response, _ = await _handle_status(state)
    elif intent_type == "accuse":
        response, gossip_notice = await _handle_accuse(remainder, state)
    elif intent_type == "why":
        response, _ = await _handle_why(remainder, state)
    elif intent_type == "go":
        response, _ = await _handle_go(remainder, state)
    elif intent_type == "search":
        response, _ = await _handle_search(remainder, state)
    elif intent_type == "talk":
        response, gossip_notice = await _handle_talk(remainder, state)
    else:
        response, gossip_notice = await _handle_freeform(raw, state)

    # Strip the 'Name: "..."' wrapper for NPC dialogue; the UI adds the speaker.
    if state.last_speaker:
        prefix = f'{state.last_speaker}: "'
        if response.startswith(prefix) and response.endswith('"'):
            response = response[len(prefix):-1]

    # Contradiction detection (structured for the UI + notice strings).
    new_contradictions: list[str] = []
    if not is_free:
        for c in detect_contradictions(state.player_learned_facts):
            notice = f"  🔎 Inconsistency noticed: {c['notice']}"
            if notice in state.contradictions_shown:
                continue
            state.contradictions_shown.add(notice)
            new_contradictions.append(notice)
            if state.last_contradiction is None and c["pair"]:
                a, b = c["pair"]
                state.last_contradiction = {"a": a, "b": b, "text": c["notice"]}

    # Persist turn + maybe improve
    improved = False
    if not is_free:
        await mem.remember_turn(state.turn, raw, response, state.session_id)
        if state.turn > 0 and state.turn % IMPROVE_EVERY == 0:
            await gm.run_improve(state.session_id, DATASET)
            improved = True

    return TurnResult(
        response=response,
        gossip=gossip_notice,
        contradictions=new_contradictions,
        game_over=state.game_over,
        improved=improved,
        turn=state.turn,
        facts_count=len(state.player_learned_facts),
        total_facts=len(FACTS_BY_ID),
        clues_count=len(state.player_found_clues),
        total_clues=len(CLUES_BY_ID),
        intent_type=intent_type,
        is_free_action=is_free,
        speaker=state.last_speaker,
        stances=_ui_stances(state),
        gossip_event=state.last_gossip,
        why_chain=state.last_why_chain,
        contradiction=state.last_contradiction,
        accusation=state.last_accusation,
        clues=_clue_objects(state),
        location=(LOCATIONS_BY_ID[state.current_room].name
                  if state.current_room in LOCATIONS_BY_ID else ""),
    )


async def run_game(session_id: str, seed: int = 42) -> None:
    state = GameState(session_id=session_id, seed=seed)
    state.visited_rooms.add(state.current_room)

    print("\n" + "═" * 65)
    print("   A DEATH AT RAVENWOOD MANOR")
    print("   An AI Murder Mystery — powered by Cognee")
    print("═" * 65 + "\n")

    print("Retrieving world memory and setting the scene...\n")
    opening = await gm.narrate_opening()
    print(opening)
    print(f"\n{HELP_TEXT}\n")

    while not state.game_over:
        print()
        try:
            raw = input("❯ ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nThe investigation is suspended. Farewell.")
            break

        if not raw:
            continue

        intent_type, remainder = _intent(raw)
        state.turn += 1

        if intent_type == "quit":
            print("\nYou close your notebook. The mystery of Ravenwood Manor remains unsolved.")
            break

        if intent_type == "help":
            print(HELP_TEXT)
            state.turn -= 1
            continue

        if intent_type in ("notebook", "status"):
            state.turn -= 1
            if intent_type == "notebook":
                nb, _ = await _handle_notebook(state)
            else:
                nb, _ = await _handle_status(state)
            print(f"\n{nb}")
            continue

        print("\n" + "─" * 65)

        # Dispatch
        gossip_notice: str | None = None
        if intent_type == "accuse":
            response, gossip_notice = await _handle_accuse(remainder, state)
        elif intent_type == "why":
            response, _ = await _handle_why(remainder, state)
        elif intent_type == "go":
            response, _ = await _handle_go(remainder, state)
        elif intent_type == "search":
            response, _ = await _handle_search(remainder, state)
        elif intent_type == "talk":
            response, gossip_notice = await _handle_talk(remainder, state)
        else:
            response, gossip_notice = await _handle_freeform(raw, state)

        print(f"\n{response}")

        if gossip_notice:
            print(gossip_notice)

        new_contradictions = [
            c for c in check_contradictions(state.player_learned_facts)
            if c not in state.contradictions_shown
        ]
        for notice in new_contradictions:
            state.contradictions_shown.add(notice)
            print(f"\n{notice}")

        await mem.remember_turn(state.turn, raw, response, state.session_id)

        if state.turn % IMPROVE_EVERY == 0:
            print("  [memory] Consolidating discoveries into world graph...", end=" ", flush=True)
            await gm.run_improve(session_id, DATASET)
            print("done.")

        known = len(state.player_learned_facts)
        clues = len(state.player_found_clues)
        print(
            f"\n  [memory · turn {state.turn} · "
            f"facts: {known}/{len(FACTS_BY_ID)} · "
            f"clues: {clues}/{len(CLUES_BY_ID)}]"
        )

        if state.game_over:
            _show_case_file(state)
            print("\n  [Composing epilogue...]\n")
            epilogue = await gm.narrate_epilogue(
                turns=state.turn,
                facts_found=len(state.player_learned_facts),
                total_facts=len(FACTS_BY_ID),
            )
            print(epilogue)
            print("\n" + "═" * 65)
            print("   Thank you for playing A Death at Ravenwood Manor.")
            print("   Powered by Cognee — AI-native memory for LLM applications.")
            print("═" * 65)
