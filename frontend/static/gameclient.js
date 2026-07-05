
const SUSPECTS = [
  {
    id: "harrington_thomas",
    name: "Mr. Harrington",
    role: "The Butler",
    hue: 38,
    standing: "neutral",
    interviewed: false,
    blurb:
      "Thirty years in service. Knows everything below stairs — and much above it.",
  },
  {
    id: "ashworth_victoria",
    name: "Lady Victoria Ashworth",
    role: "The Sister",
    hue: 330,
    standing: "neutral",
    interviewed: false,
    blurb:
      "Charming, imperious, devoted to appearances. Resented her brother\u2019s grip on the estate.",
  },
  {
    id: "ashworth_gerald",
    name: "Col. Gerald Ashworth",
    role: "The Brother-in-law",
    hue: 14,
    standing: "neutral",
    interviewed: false,
    blurb:
      "Jovial, back-slapping, a military bearing. Acts as though money is no concern.",
  },
  {
    id: "pemberton_eleanor",
    name: "Dr. Eleanor Pemberton",
    role: "The Physician",
    hue: 190,
    standing: "neutral",
    interviewed: false,
    blurb:
      "Calm, clinical, highly regarded. Observes everything and says only what she means.",
  },
  {
    id: "whitmore_agnes",
    name: "Mrs. Whitmore",
    role: "The Housekeeper",
    hue: 280,
    standing: "neutral",
    interviewed: false,
    blurb:
      "Stout, efficient, an excellent memory and an instinct for when something is wrong.",
  },
  {
    id: "calloway_james",
    name: "James Calloway",
    role: "The Business Partner",
    hue: 48,
    standing: "neutral",
    interviewed: false,
    blurb:
      "A polished merchant, all smiles — and bitter over an investment he blames on the dead man.",
  },
  {
    id: "calloway_sophie",
    name: "Sophie Calloway",
    role: "The Ward",
    hue: 150,
    standing: "warm",
    interviewed: false,
    blurb:
      "Gentle, bookish, genuinely fond of Lord Ravenwood. Desperate to help you find the truth.",
  },
  {
    id: "doyle_father",
    name: "Father Doyle",
    role: "The Confessor",
    hue: 220,
    standing: "neutral",
    interviewed: false,
    blurb:
      "Gentle, unflappable, a family friend of long standing. Listens far more than he speaks.",
  },
  {
    id: "brand_cecilia",
    name: "Cecilia Brand",
    role: "The Maid",
    hue: 12,
    standing: "wary",
    interviewed: false,
    blurb:
      "Quiet, nervous, distracted of late. Something weighs on her that she will not name.",
  },
  {
    id: "thatch_oliver",
    name: "Oliver Thatch",
    role: "The Dismissed Gardener",
    hue: 96,
    standing: "wary",
    interviewed: false,
    blurb:
      "Gruff, resentful, visibly nervous. Dismissed a month ago — yet here again tonight.",
  },
  {
    id: "dunbar_miles",
    name: "Prof. Miles Dunbar",
    role: "The Rival",
    hue: 260,
    standing: "neutral",
    interviewed: false,
    blurb:
      "Erudite, sardonic. Calls the deceased \u201Can interesting host\u201D rather than a friend.",
  },
];

const LOCATIONS = {
  study: {
    id: "study",
    name: "Lord Ravenwood\u2019s Study",
    description:
      "A locked oak-panelled room. A cold fireplace, a mahogany desk, and a brandy decanter on the sideboard. The body was found here.",
  },
  entrance: {
    id: "entrance",
    name: "The Entrance Hall",
    description:
      "Grand marble floors, a sweeping staircase, and the painted eyes of Ravenwood ancestors following you.",
  },
  dining: {
    id: "dining",
    name: "The Dining Room",
    description:
      "A long mahogany table set for twelve. The dinner party sat here when the manor still had a living master.",
  },
  garden: {
    id: "garden",
    name: "The East Garden",
    description:
      "Formal beds under a thin moon. A section of foxglove has been freshly uprooted.",
  },
  conservatory: {
    id: "conservatory",
    name: "The Conservatory",
    description:
      "Glass walls and tropical dark. Its windows give a clear view of the corridor to the study.",
  },
};

// nodes/edges for the corkboard. type: suspect | clue | victim | event
const GRAPH = {
  nodes: [
    { id: "you", type: "detective", label: "You" },
    { id: "ravenwood_lord", type: "victim", label: "Lord Ravenwood" },
    ...SUSPECTS.map((s) => ({
      id: s.id,
      type: "suspect",
      label: s.name.replace(/^(Mr\.|Mrs\.|Dr\.|Col\.|Lady|Father|Prof\.) /, ""),
    })),
  ],
  edges: [
    {
      source: "ravenwood_lord",
      target: "ashworth_victoria",
      type: "FAMILY_OF",
      revealed: true,
    },
    {
      source: "ashworth_victoria",
      target: "ashworth_gerald",
      type: "FAMILY_OF",
      revealed: true,
    },
    {
      source: "calloway_james",
      target: "calloway_sophie",
      type: "FAMILY_OF",
      revealed: true,
    },
    {
      source: "harrington_thomas",
      target: "whitmore_agnes",
      type: "ALLIED_WITH",
      revealed: true,
    },
    {
      source: "whitmore_agnes",
      target: "brand_cecilia",
      type: "KNOWS",
      revealed: true,
    },
    {
      source: "harrington_thomas",
      target: "ashworth_gerald",
      type: "KNOWS",
      revealed: true,
    },
    {
      source: "harrington_thomas",
      target: "calloway_sophie",
      type: "KNOWS",
      revealed: false,
    },
    {
      source: "calloway_james",
      target: "brand_cecilia",
      type: "BLACKMAILS",
      revealed: false,
    },
    {
      source: "calloway_james",
      target: "ashworth_gerald",
      type: "KNOWS",
      revealed: false,
    },
    {
      source: "thatch_oliver",
      target: "harrington_thomas",
      type: "RESENTS",
      revealed: false,
    },
    {
      source: "doyle_father",
      target: "dunbar_miles",
      type: "KNOWS",
      revealed: false,
    },
    {
      source: "calloway_sophie",
      target: "ashworth_gerald",
      type: "WITNESSED",
      revealed: false,
    },
  ],
};

// clues, revealed as the player finds them
const CLUE_LIB = {
  brandy_glass: {
    id: "brandy_glass",
    name: "The Brandy Glass",
    found_at: "study",
    note: "A crystal glass with a faint bitter residue. Consistent, a physician would say, with digitalis.",
  },
  thatch_letter: {
    id: "thatch_letter",
    name: "A Crumpled Letter",
    found_at: "study",
    note: "Signed only \u201CO.T.\u201D, found behind the fireplace grate: \u201CYou will regret what you have done to me.\u201D",
  },
  foxglove: {
    id: "foxglove",
    name: "Uprooted Foxglove",
    found_at: "garden",
    note: "Several plants torn from the east bed. Foxglove is the source of digitalis.",
  },
  ledger: {
    id: "ledger",
    name: "The Altered Ledger",
    found_at: "guest room",
    note: "Cloth-bound, hidden beneath a floorboard in Col. Ashworth\u2019s room. The trust figures have been systematically altered.",
  },
  sophie_vantage: {
    id: "sophie_vantage",
    name: "Sophie\u2019s Vantage",
    found_at: "conservatory",
    note: "From the conservatory window, the study corridor is in plain view. Sophie sat here at 9:15.",
  },
  toxicology_book: {
    id: "toxicology_book",
    name: "A Toxicology Volume",
    found_at: "library",
    note: "Left open at the chapter on cardiac glycosides. No name in the borrowing register.",
  },
};

// ── Mock session state ──────────────────────────────────────────────────────

function freshState() {
  return {
    phase: "title", // title | intro | investigating | accusation | verdict
    location: LOCATIONS.study,
    turn: 0,
    stats: {
      facts: 0,
      total_facts: 22,
      clues: 0,
      total_clues: 8,
      hour: "10:15",
      tension: 0,
    },
    journal: [], // { voice:'gm'|'npc', speaker, text, turn }
    suspects: SUSPECTS.map((s) => ({ ...s, history: [] })),
    clues: [], // filled from CLUE_LIB as found
    graph: {
      nodes: GRAPH.nodes.map((n) => ({ ...n })),
      edges: GRAPH.edges.map((e) => ({ ...e })),
    },
    gossip_event: null, // turn-scoped
    why_reveal: null, // turn-scoped { chain:[ids], text }
    contradiction: null, // turn-scoped { a, b, text }
    accusation_result: null, // verdict-scoped
  };
}

let S = freshState();
const HOURS = ["10:15", "10:40", "11:05", "11:30", "11:55", "12:20", "12:45"];

function snapshot() {
  return structuredClone(S);
}
function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function addJournal(voice, speaker, text) {
  S.journal.push({ voice, speaker, text, turn: S.turn });
}
function setStanding(id, to) {
  const s = S.suspects.find((x) => x.id === id);
  if (s) s.standing = to;
}
function revealEdge(source, target) {
  const e = S.graph.edges.find(
    (e) =>
      (e.source === source && e.target === target) ||
      (e.source === target && e.target === source),
  );
  if (e) e.revealed = true;
}
function setInterviewed(name) {
  const s = S.suspects.find((x) => x.name === name);
  if (s) s.interviewed = true;
}
function cleanNarration(text) {
  // strip markdown headings / horizontal rules the GM sometimes emits
  return (text || "")
    .replace(/^\s*#{1,6}\s.*$/gm, "")
    .replace(/^\s*-{3,}\s*$/gm, "")
    .trim();
}

// ── Backend transport (POST /api/start + WebSocket turn loop) ────────────────

let ws = null;
let sessionId = null;
let opening = "";
let pending = null;

function connectWS(sid) {
  return new Promise((resolve, reject) => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws/${sid}`);
    ws.onopen = () => resolve();
    ws.onerror = () => reject(new Error("Connection to the manor failed."));
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (pending) {
        const p = pending;
        pending = null;
        p.resolve(msg);
      }
    };
    ws.onclose = () => {
      if (pending) {
        const p = pending;
        pending = null;
        p.reject(new Error("The line to the manor went quiet."));
      }
    };
  });
}

function sendAction(text) {
  return new Promise((resolve, reject) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      reject(new Error("Not connected."));
      return;
    }
    pending = { resolve, reject };
    ws.send(JSON.stringify({ action: text }));
  });
}

// ── Public API ──────────────────────────────────────────────────────────────

async function startSession() {
  if (ws) {
    try {
      ws.close();
    } catch {}
    ws = null;
  }
  const res = await fetch("/api/start", { method: "POST" });
  if (!res.ok) {
    let m = "The manor would not open its doors.";
    try {
      m = (await res.json()).error || m;
    } catch {}
    const e = new Error(m);
    e.kind = res.status === 429 ? "rate_limit" : "error";
    throw e;
  }
  const data = await res.json();
  sessionId = data.session_id;
  opening = cleanNarration(data.opening);
}

export async function getInitialState() {
  S = freshState();
  sessionId = null;
  await startSession();
  return snapshot();
}

// advance from title -> intro -> investigating
export async function beginInvestigation() {
  S.phase = "intro";
  return snapshot();
}

export async function enterManor() {
  if (!sessionId) await startSession(); // recover if the first start was rate-limited
  // Open the turn-loop socket right before play so it isn't idle through the intro.
  await connectWS(sessionId);
  S.phase = "investigating";
  S.location = LOCATIONS.study;
  if (opening) addJournal("gm", null, opening);
  return snapshot();
}

/**
 * submitAction(text) -> Promise<GameState>
 * Sends the action over the WebSocket and maps the server's turn_result
 * into the GameState the UI renders. No game logic lives here.
 */
export async function submitAction(text) {
  S.gossip_event = null;
  S.why_reveal = null;
  S.contradiction = null;

  const msg = await sendAction(text);
  if (msg.type === "error") {
    const e = new Error(msg.message || "The manor faltered.");
    e.kind = msg.kind || "error";
    throw e;
  }
  applyTurn(msg);
  return snapshot();
}

function applyTurn(msg) {
  if (typeof msg.turn === "number") S.turn = msg.turn;
  S.stats.hour = HOURS[Math.min(HOURS.length - 1, Math.floor(S.turn / 2))];

  if (msg.stats) {
    S.stats.facts = msg.stats.facts;
    S.stats.total_facts = msg.stats.total_facts;
    S.stats.clues = msg.stats.clues;
    S.stats.total_clues = msg.stats.total_clues;
  }
  if (msg.location) S.location = { id: "", name: msg.location };

  // journal — NPC line if a speaker is set, else GM narration
  const text = cleanNarration(msg.response);
  if (text) {
    if (msg.speaker) addJournal("npc", msg.speaker, text);
    else addJournal("gm", null, text);
  }
  if (msg.speaker) setInterviewed(msg.speaker);

  // clues — server sends the full discovered list
  if (Array.isArray(msg.clues)) {
    S.clues = msg.clues.map((c) => ({
      id: c.id,
      name: c.name,
      note: c.note,
      found_at: c.found_at,
    }));
  }

  // standings — server maps stances to warm|neutral|wary|hostile
  if (msg.stances) {
    for (const [id, st] of Object.entries(msg.stances)) setStanding(id, st);
  }

  // gossip ripple — chain + affected from the real graph traversal
  if (msg.gossip_event) {
    const ge = msg.gossip_event;
    const chain = ge.chain || [];
    S.gossip_event = {
      origin: ge.origin,
      chain,
      affected: (ge.affected || []).map((a) => ({ id: a.id, to: a.to })),
      toast: "Word travels the manor — and reaches those you have not yet met.",
    };
    for (let i = 0; i < chain.length - 1; i++) revealEdge(chain[i], chain[i + 1]);
  }

  // why reveal — the reconstructed causal path
  if (Array.isArray(msg.why_chain) && msg.why_chain.length > 1) {
    S.why_reveal = { chain: msg.why_chain, text: "gossip" };
    for (let i = 0; i < msg.why_chain.length - 1; i++)
      revealEdge(msg.why_chain[i], msg.why_chain[i + 1]);
  }

  // contradiction — paired suspects to glow
  if (msg.contradiction) {
    S.contradiction = {
      a: msg.contradiction.a,
      b: msg.contradiction.b,
      text: msg.contradiction.text,
    };
    revealEdge(msg.contradiction.a, msg.contradiction.b);
  }

  // accusation — a correct one drives the climax + verdict
  if (msg.accusation && msg.accusation.correct) {
    const ac = msg.accusation;
    S.phase = "accusation";
    S.accusation_result = {
      accused: ac.accused_id,
      accused_name: ac.accused_name,
      correct: true,
      path: [],
      pathLabels: ac.path_labels || [],
    };
  }
}

// expose libs for the graph styling layer
export const WORLD = { SUSPECTS, LOCATIONS, GRAPH, CLUE_LIB };
