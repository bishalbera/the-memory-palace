"""FastAPI web backend for A Death at Ravenwood Manor."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import game.gm as gm
from game.loop import process_turn, HELP_TEXT
from api.session import new_session, get_session, update_graph, full_graph, build_case_file

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="Ravenwood Manor", docs_url=None, redoc_url=None)

STATIC_DIR = Path(__file__).parent.parent / "frontend" / "static"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
async def health():
    return {"status": "ok", "game": "A Death at Ravenwood Manor"}


@app.post("/api/start")
async def start_game():
    sid, state, graph = new_session()
    opening = await gm.narrate_opening()
    elements = update_graph(state, graph)
    return JSONResponse({
        "session_id": sid,
        "opening": opening,
        "help": HELP_TEXT,
        "graph_elements": elements,
    })


@app.get("/api/graph/{session_id}")
async def get_graph(session_id: str):
    pair = get_session(session_id)
    if not pair:
        return JSONResponse({"error": "session not found"}, status_code=404)
    _, graph = pair
    return JSONResponse({"elements": full_graph(graph)})


# ── WebSocket game loop ────────────────────────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def ws_game(websocket: WebSocket, session_id: str):
    await websocket.accept()

    pair = get_session(session_id)
    if not pair:
        await websocket.send_json({
            "type": "error",
            "message": "Session not found. Refresh the page to start a new game.",
        })
        await websocket.close()
        return

    state, graph = pair

    try:
        while True:
            data = await websocket.receive_json()
            raw = (data.get("action") or "").strip()
            if not raw:
                continue

            result = await process_turn(state, raw)
            new_elements = update_graph(state, graph)

            payload: dict = {
                "type": "turn_result",
                "response": result.response,
                "gossip": result.gossip,
                "contradictions": result.contradictions,
                "game_over": result.game_over,
                "improved": result.improved,
                "turn": result.turn,
                "stats": {
                    "facts": result.facts_count,
                    "total_facts": result.total_facts,
                    "clues": result.clues_count,
                    "total_clues": result.total_clues,
                },
                "graph_delta": new_elements,
                "intent_type": result.intent_type,
                "is_free": result.is_free_action,
                "speaker": result.speaker,
                "stances": result.stances,
                "gossip_event": result.gossip_event,
                "why_chain": result.why_chain,
                "contradiction": result.contradiction,
                "accusation": result.accusation,
                "clues": result.clues,
                "location": result.location,
            }

            if result.game_over:
                epilogue = await gm.narrate_epilogue(
                    turns=result.turn,
                    facts_found=result.facts_count,
                    total_facts=result.total_facts,
                )
                payload["epilogue"] = epilogue
                payload["case_file"] = build_case_file(state)
                # Reveal full graph on victory
                payload["graph_delta"] = full_graph(graph)

            await websocket.send_json(payload)

            if result.game_over or result.intent_type == "quit":
                break

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
