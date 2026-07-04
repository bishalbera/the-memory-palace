<div align="center">

# 🕯️ The Memory Palace

### A murder mystery where the world *never forgets* — powered by [Cognee](https://github.com/topoteretes/cognee)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Cognee](https://img.shields.io/badge/Memory-Cognee-6E56CF)](https://www.cognee.ai/)
[![Hackathon](https://img.shields.io/badge/WeMakeDevs-The%20Hangover%20Part%20AI-E4405F)](https://www.wemakedevs.org/hackathons/cognee)
[![License](https://img.shields.io/badge/License-MIT-000000)](LICENSE)

<em>An AI Game Master that runs a living murder mystery — where a single word to the wrong suspect can turn the whole manor against you three rooms later.</em>

<!-- TODO: drop your hero GIF here. See the "Shot list" section at the bottom for exactly what to record. -->
<!-- ![The Memory Palace — live demo](docs/hero.gif) -->

</div>

---

## 🎲 First, picture a Game Master

If you've seen *Stranger Things*, you've watched a Game Master at work: one kid sits at the head of the table running the Dungeons & Dragons campaign, describing the torch-lit dungeon, voicing every monster, and remembering that the rogue insulted a merchant two sessions ago. The **Game Master** is the living memory of the whole world. The magic of the game is that *nothing you do is forgotten* — every choice ripples forward.

Now try to build that Game Master out of an AI.

## 🧠 The problem: AI Game Masters have a hangover

Ask an LLM to run a long story and it wakes up with amnesia every few thousand tokens. It forgets who's already dead. It contradicts an alibi it invented an hour ago. It loses track of who told whom what. This isn't a prompt-engineering bug — it's **context collapse**, the wall every long-running AI narrative hits when the world outgrows the context window. (It's exactly what Cognee's [BEAM benchmark](https://github.com/topoteretes/cognee#benchmarks) measures: can a system keep track of a story *as it changes*?)

## 🕯️ The solution: give the manor a memory

**The Memory Palace** is an AI-driven murder mystery where the entire world — every suspect, secret, grudge, alibi, and whispered rumor — lives in a **knowledge graph** managed by [Cognee](https://github.com/topoteretes/cognee), not in the prompt. The Game Master doesn't *remember* the story in its context window; it **queries a graph** that persists and evolves.

The name is a double meaning. A *memory palace* is the ancient technique of storing knowledge by placing it in the rooms of an imagined mansion — which is exactly what we do, except the mansion is a crime scene and the memories are motives.

> **The game is the proof.** If the graph can keep a twelve-suspect murder mystery internally consistent across an hour of free-text play, it can keep your agent consistent across a thousand sessions.

---

## ✨ The moment that matters

Most "AI with memory" demos show the bot recalling your name. That's a lookup — any vector store does it. Here's what a **graph** does that a vector store cannot:

Early in the game, you corner the **Butler** and threaten to expose his gambling debt. You never speak to the gardener. But two scenes later, in a completely different wing of the manor, the **Gardener** goes cold and stops answering your questions. Ask *"why won't you talk to me?"* and the Game Master traces the actual chain:

```mermaid
graph LR
    P([🕵️ You]) -- "threaten (scene 1)" --> B[🎩 Butler]
    B -- KNOWS --> C[🍳 Cook]
    C -- FAMILY_OF --> G[🌿 Gardener]
    G -. "distrusts you (scene 3)" .-> P

    style P fill:#6E56CF,color:#fff
    style B fill:#8B0000,color:#fff
    style G fill:#2F4F4F,color:#fff
```

Word traveled **Butler → Cook → Gardener** along the social graph. That's a **multi-hop relationship traversal** — "who is within 2 hops of the person I just wronged?" — a question semantic similarity structurally *cannot* answer. This is the heart of the project, and it runs through Cognee's graph layer, not an `if` statement.

---

## 🧩 How it works

```mermaid
flowchart TD
    subgraph Player
      A[Free-text action<br/>“ask the maid about 9pm”]
    end
    A --> B{FastAPI<br/>Game Loop}
    B -- "recall()" --> COG[(🧠 Cognee<br/>Graph + Vector Memory)]
    COG -- "what this NPC knows,<br/>their standing, relevant clues" --> B
    B --> LLM[[LLM Narrator<br/>voices the NPC]]
    LLM --> B
    B -- "remember() the outcome" --> COG
    B --> UI[💬 Chat + 🕸️ Live case graph]

    COG -. "improve() between scenes:<br/>propagate gossip, catch contradictions" .-> COG
    COG -. "forget() dead threads<br/>& resolved red herrings" .-> COG
```

The narrator (the LLM) never invents facts — it can only dramatize what it **retrieves from the graph**. Memory and narration are cleanly separated, which is why the story stays consistent.

### 🔑 Where Cognee's memory lifecycle powers the game

| Cognee op | In the story | Why it's load-bearing |
|-----------|--------------|-----------------------|
| **`remember()`** | Seeds the world graph (suspects, relationships, secrets, clues) and records every player action | The entire case lives in the graph, not the prompt |
| **`recall()`** | Fetches what an NPC knows + their current standing before they speak; answers your deductions | Auto-routes between similarity *and* multi-hop graph traversal |
| **`improve()` / memify** | Between scenes: propagates rumors along social edges and **flags contradictory alibis** | Turns raw memories into evolving, self-correcting world state |
| **`forget()`** | Prunes exhausted dialogue and resolved red herrings | Keeps the working memory lean across a long session |

### 🕸️ The query a vector store can't do

```python
# When you wrong an NPC, the consequence spreads along real relationships.
# This is graph traversal, not similarity search.
witnesses = await cognee.recall(
    "characters within 2 hops of {npc} via KNOWS / FAMILY_OF / ALLIED_WITH"
)
for c in witnesses:
    update_standing(c, toward="player", reason=event_id)   # gossip ripples outward
```

---

## 🛠️ Tech stack

- **Memory:** [Cognee](https://github.com/topoteretes/cognee) (Cloud) — hybrid **graph + vector** knowledge store
- **Backend:** FastAPI + Uvicorn (Python 3.11+)
- **Narration:** LLM via API (configurable provider)
- **Frontend:** Chat panel + a **live case graph** that reveals nodes as you discover them
- **Scenario:** a single, internally-consistent mystery defined as structured data in `scenario/`

```
the-memory-palace/
├── api/          # FastAPI app + game-loop endpoints
├── game/         # core loop, Cognee memory layer, gossip + accusation logic
├── scenario/     # the murder mystery: suspects, relationships, clues, solution
├── frontend/     # chat UI + live graph visualization
├── scripts/      # Cognee smoke test, demo seeding
└── main.py       # uvicorn entrypoint
```

---

## 🚀 Quickstart

**Prerequisites:** Python 3.11+, a Cognee Cloud account ([free Developer plan](https://platform.cognee.ai/sign-in), promo code `COGNEE-35`), and an LLM API key.

```bash
# 1. Clone
git clone https://github.com/bishalbera/the-memory-palace.git
cd the-memory-palace

# 2. Install (uv recommended)
uv sync            # or: pip install -e .

# 3. Configure secrets
cp .env.template .env
#   LLM_API_KEY=sk-...
#   COGNEE_BASE_URL=https://your-instance.cognee.ai
#   COGNEE_API_KEY=ck_...

# 4. (recommended) prove the memory layer works
python scripts/verify_cognee.py

# 5. Play
python main.py     # → http://localhost:8000
```

## 🌐 Play it live

<!-- TODO: paste your deployed URL here once it's up -->
**▶️ Live demo:** _coming soon_ — [play in your browser](#)

---

## 🎥 Demo

<!-- TODO: embed your 60–90s demo GIF/video here -->

**Shot list for the demo GIF (record these beats):**
1. **Setup** — the manor, the body, the twelve suspects appear on the case graph.
2. **The wrong word** — you threaten the Butler about his debt.
3. **The ripple** — scenes later, an NPC you never met turns cold.
4. **The reveal** — you ask *"why?"* and the Game Master traces the Butler → Cook → Gardener chain on the graph.
5. **A contradiction caught** — `improve()` flags two suspects whose alibis don't line up.
6. **The accusation** — you name the killer, and the motive → means → opportunity path lights up.

---

## 🏆 Built for the WeMakeDevs × Cognee Hackathon

**"The Hangover Part AI: Where's My Context?"** — the challenge: *build AI that doesn't wake up with no memory of last night.* The Memory Palace answers it by making persistent, relationship-aware, self-correcting memory the core mechanic of a game you can actually play.

## 🗺️ Roadmap

- [ ] Multiple mysteries / procedurally generated cases
- [ ] Persistent detective across cases (your reputation follows you)
- [ ] Multiplayer parlor — several detectives, one shared graph
- [ ] Voice narration

## 📜 License

MIT — see [LICENSE](LICENSE).

<div align="center">
<br/>
<em>What happens in the manor stays in the graph.</em>
</div>