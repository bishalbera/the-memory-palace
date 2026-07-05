
import {
  getInitialState,
  beginInvestigation,
  enterManor,
  submitAction,
  WORLD,
} from "./gameClient.js";

const REDUCED = window.matchMedia("(prefers-reduced-motion:reduce)").matches;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

let state = null; 
let renderedEntries = 0; 
let cy = null; 
let busy = false;

/* ── screen router ──────────────────────────────────────────────────────── */
function showScreen(id) {
  $$(".screen").forEach((s) => s.classList.toggle("active", s.id === id));
}

/* ═══════════ PROCEDURAL PORTRAITS (no image assets) ═══════════ */
function portraitSVG(hue, seed = 0) {
  const c1 = `hsl(${hue} 24% 30%)`,
    c2 = `hsl(${hue} 20% 14%)`;
  const skin = `hsl(${(hue + 18) % 360} 16% 26%)`;
  const gid = "g" + hue + seed;
  return `<svg viewBox="0 0 52 64" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${c1}"/><stop offset="1" stop-color="${c2}"/></linearGradient></defs>
    <rect width="52" height="64" fill="url(#${gid})"/>
    <ellipse cx="26" cy="62" rx="20" ry="16" fill="${skin}" opacity=".9"/>
    <circle cx="26" cy="24" r="12" fill="${skin}"/>
    <path d="M14 24c0-8 5-13 12-13s12 5 12 13c-2-5-6-7-12-7s-10 2-12 7z" fill="hsl(${hue} 18% 9%)"/>
    <rect width="52" height="64" fill="url(#${gid})" opacity=".18"/>
  </svg>`;
}

/* ═══════════ TITLE ═══════════ */
$("#btn-begin").addEventListener("click", async () => {
  state = await beginInvestigation();
  runIntro();
});

/* ═══════════ MURDER INTRO (cinematic, paced) ═══════════ */
const INTRO_LINES = [
  "Ravenwood Manor. Midnight. The rain has not let up in hours.",
  "Lord Edmund Ravenwood hosted eleven to dinner. At nine o\u2019clock he rose, excused himself, and walked to his study.",
  "He never walked out.",
  "The brandy on his desk was poured by a familiar hand \u2014 and laced with something patient and cruel.",
];
async function runIntro() {
  showScreen("screen-intro");
  const sceneEl = $("#intro-scene");
  const capEl = $("#intro-caption");
  const contEl = $("#btn-enter");
  const susWrap = $("#intro-suspects");
  sceneEl.textContent = "";
  capEl.classList.remove("show");
  contEl.classList.remove("show");
  susWrap.innerHTML = "";

  // silhouettes for the assembled suspects
  WORLD.SUSPECTS.forEach((s) => {
    const el = document.createElement("div");
    el.className = "intro-silhouette";
    el.innerHTML = `<svg viewBox="0 0 46 64" fill="currentColor"><ellipse cx="23" cy="60" rx="17" ry="12"/><circle cx="23" cy="20" r="11"/></svg>`;
    el.dataset.hue = s.hue;
    susWrap.appendChild(el);
  });

  if (REDUCED) {
    sceneEl.innerHTML = INTRO_LINES.map((l, i) =>
      i === 2 ? `<span class="lead">${l}</span>` : l,
    ).join(" ");
    $$(".intro-silhouette").forEach((e) => e.classList.add("lit"));
    capEl.classList.add("show");
    contEl.classList.add("show");
    return;
  }

  for (let i = 0; i < INTRO_LINES.length; i++) {
    const lead = i === 2;
    await typeInto(sceneEl, INTRO_LINES[i], { lead, append: i > 0 });
    await wait(650);
  }
  // suspects assemble one by one
  const sils = $$(".intro-silhouette");
  for (let i = 0; i < sils.length; i++) {
    sils[i].classList.add("lit");
    await wait(120);
  }
  await wait(300);
  capEl.classList.add("show");
  await wait(700);
  contEl.classList.add("show");
}
$("#btn-enter").addEventListener("click", async () => {
  state = await enterManor();
  enterPlay();
});

/* ── typewriter into an element (returns when done) ── */
function typeInto(el, text, { lead = false, append = false, speed = 20 } = {}) {
  return new Promise((resolve) => {
    const span = document.createElement("span");
    if (lead) span.className = "lead";
    if (append && el.childNodes.length)
      el.appendChild(document.createTextNode(" "));
    el.appendChild(span);
    if (REDUCED) {
      span.textContent = text;
      resolve();
      return;
    }
    const caret = document.createElement("span");
    caret.className = "caret";
    el.appendChild(caret);
    let i = 0,
      last = performance.now(),
      acc = 0;
    function step(now) {
      acc += now - last;
      last = now;
      while (acc >= speed && i < text.length) {
        span.textContent += text[i++];
        acc -= speed;
      }
      const wrap = el.closest(".journal");
      if (wrap) wrap.scrollTop = wrap.scrollHeight;
      if (i < text.length) requestAnimationFrame(step);
      else {
        caret.remove();
        resolve();
      }
    }
    requestAnimationFrame(step);
  });
}

/* ═══════════ ENTER PLAY VIEW ═══════════ */
function enterPlay() {
  showScreen("screen-play");
  buildQuickActions();
  renderBoard(state);
  renderCasebar(state);
  renderJournal(state); // paints the opening narration with typewriter
}

/* ── casebar ── */
function renderCasebar(s) {
  $("#cb-location").textContent = s.location.name;
  $("#location-name").textContent = s.location.name;
  $("#cb-hour").textContent = s.stats.hour;
  $("#cb-turns").textContent = s.turn;
  $("#cb-clues").textContent = s.stats.clues;
  $("#cb-facts").textContent = s.stats.facts;
  const HOURS = ["10:15", "10:40", "11:05", "11:30", "11:55", "12:20", "12:45"];
  const idx = Math.max(0, HOURS.indexOf(s.stats.hour));
  const pct = 8 + (idx / (HOURS.length - 1)) * 88;
  $("#hour-fill").style.width = pct + "%";
  $("#hour-moon").style.left = pct + "%";
}

/* ── journal (typewriter for new entries only) ── */
async function renderJournal(s) {
  const j = $("#journal");
  const fresh = s.journal.slice(renderedEntries);
  for (const e of fresh) {
    const entry = document.createElement("div");
    entry.className = "entry";
    if (e.voice === "gm") {
      const p = document.createElement("div");
      p.className = "entry-gm" + (renderedEntries === 0 ? " drop" : "");
      entry.appendChild(p);
      j.appendChild(entry);
      await typeInto(p, e.text, { speed: 16 });
    } else {
      entry.innerHTML = `<div class="entry-npc"><div class="who">${e.speaker}</div><div class="said"></div></div>`;
      j.appendChild(entry);
      await typeInto($(".said", entry), "\u201C" + e.text + "\u201D", {
        speed: 14,
      });
    }
    const mark = document.createElement("span");
    mark.className = "turnmark";
    mark.textContent =
      e.voice === "gm"
        ? "The Case Journal · Turn " + e.turn
        : "Testimony · Turn " + e.turn;
    entry.appendChild(mark);
    renderedEntries++;
    j.scrollTop = j.scrollHeight;
  }
}

/* ═══════════ CASE BOARD ═══════════ */
function renderBoard(s) {
  renderDossiers(s);
  renderEvidence(s);
  syncGraph(s);
}

function standingLabel(st) {
  return (
    { warm: "Warm", neutral: "Neutral", wary: "Wary", hostile: "Hostile" }[
      st
    ] || st
  );
}

function renderDossiers(s) {
  const grid = $("#dossier-grid");
  grid.innerHTML = "";
  s.suspects.forEach((sp) => {
    const card = document.createElement("div");
    card.className = "dossier-card";
    card.dataset.id = sp.id;
    card.innerHTML = `
      <div class="portrait">${portraitSVG(sp.hue)}</div>
      <div class="dossier-body">
        <div class="nm">${sp.name}</div>
        <div class="rl">${sp.role}</div>
        <div class="bl">${sp.blurb}</div>
        <span class="standing" data-s="${sp.standing}"><span class="dot" style="background:currentColor"></span>${standingLabel(sp.standing)}</span>
      </div>
      ${sp.interviewed ? '<span class="interviewed-mark">interviewed</span>' : ""}`;
    card.addEventListener("click", () => openDossier(sp.id));
    grid.appendChild(card);
  });
}

function renderEvidence(s) {
  const tray = $("#evidence-tray");
  const badge = $("#ev-badge");
  if (!s.clues.length) {
    tray.innerHTML =
      '<div class="evidence-empty">No evidence yet. Search the rooms, Detective \u2014 the manor keeps its secrets in drawers and behind grates.</div>';
    badge.hidden = true;
    return;
  }
  badge.hidden = false;
  badge.textContent = s.clues.length;
  // only animate newly added clues
  const existing = new Set($$(".clue", tray).map((c) => c.dataset.id));
  if (existing.size === 0) tray.innerHTML = "";
  s.clues.forEach((c) => {
    if (existing.has(c.id)) return;
    const el = document.createElement("div");
    el.className = "clue";
    el.dataset.id = c.id;
    el.innerHTML = `
      <svg class="tag" viewBox="0 0 24 24" fill="currentColor"><path d="M21 11l-8-8H4v9l8 8 9-9zM7 8a1.5 1.5 0 110-3 1.5 1.5 0 010 3z"/></svg>
      <div>
        <div class="cn">${c.name}</div>
        <div class="cnote">${c.note}</div>
        <div class="cwhere">Found · ${c.found_at}</div>
      </div>`;
    el.addEventListener("click", () => {
      pushToast(
        `\u201C${c.name}\u201D \u2014 found in ${c.found_at}. ${c.note}`,
        "clue",
      );
    });
    tray.prepend(el);
  });
}

/* ═══════════ CORKBOARD (Cytoscape restyled) ═══════════ */
function nodeColor(t) {
  return (
    {
      detective: "#d8b25a",
      victim: "#a52a1e",
      suspect: "#efe4cb",
      clue: "#c8b184",
      event: "#8a8272",
    }[t] || "#efe4cb"
  );
}
function initCy(s) {
  if (cy || typeof cytoscape === "undefined") return;
  const els = [];
  s.graph.nodes.forEach((n) =>
    els.push({ data: { id: n.id, label: n.label, type: n.type } }),
  );
  s.graph.edges.forEach((e, i) =>
    els.push({
      data: {
        id: "e" + i,
        source: e.source,
        target: e.target,
        type: e.type,
        revealed: e.revealed,
      },
    }),
  );
  cy = cytoscape({
    container: $("#cy"),
    elements: els,
    minZoom: 0.4,
    maxZoom: 2,
    style: [
      {
        selector: "node",
        style: {
          label: "data(label)",
          width: 38,
          height: 38,
          "background-color": (n) => nodeColor(n.data("type")),
          "border-width": 3,
          "border-color": "#8a6a24",
          "border-opacity": 0.9,
          color: "#f5ecd6",
          "font-family": "IM Fell English, serif",
          "font-size": 12,
          "text-valign": "bottom",
          "text-margin-y": 5,
          "text-outline-width": 3,
          "text-outline-color": "#0b0907",
          "text-outline-opacity": 0.9,
          "text-max-width": "90px",
          "text-wrap": "wrap",
        },
      },
      {
        selector: 'node[type="victim"]',
        style: {
          width: 46,
          height: 46,
          "border-color": "#a52a1e",
          shape: "round-rectangle",
        },
      },
      {
        selector: 'node[type="detective"]',
        style: {
          width: 46,
          height: 46,
          "border-color": "#d8b25a",
          shape: "diamond",
          "background-color": "#332a22",
        },
      },
      {
        selector: 'node[type="clue"]',
        style: { shape: "round-rectangle", width: 34, height: 26 },
      },
      {
        selector: "edge",
        style: {
          "curve-style": "unbundled-bezier",
          "control-point-distances": [18],
          "control-point-weights": [0.5],
          width: 1.4,
          "line-color": "#5a4a38",
          "line-style": "dashed",
          opacity: 0.35,
          "transition-property": "line-color, width, opacity",
          "transition-duration": "400ms",
        },
      },
      {
        selector: "edge[?revealed]",
        style: {
          "line-color": "#b8892f",
          "line-style": "solid",
          width: 2,
          opacity: 0.85,
        },
      },
      {
        selector: ".string",
        style: {
          "line-color": "#a52a1e",
          "line-style": "solid",
          width: 3.4,
          opacity: 1,
        },
      },
      { selector: ".dim", style: { opacity: 0.12 } },
      {
        selector: ".pulse-node",
        style: {
          "border-color": "#c8402c",
          "border-width": 5,
          "background-color": "#c8402c",
        },
      },
      {
        selector: ".hot-node",
        style: { "border-color": "#d8b25a", "border-width": 5 },
      },
    ],
    layout: {
      name: "concentric",
      concentric: (n) =>
        n.data("type") === "detective"
          ? 3
          : n.data("type") === "victim"
            ? 2
            : 1,
      levelWidth: () => 1,
      minNodeSpacing: 34,
      padding: 24,
    },
  });
  cy.on("tap", "node", (evt) => {
    const id = evt.target.id();
    if (state.suspects.some((x) => x.id === id)) openDossier(id);
  });
}
function syncGraph(s) {
  if (!cy) return;
  s.graph.edges.forEach((e, i) => {
    const el = cy.$("#e" + i);
    if (el && e.revealed) el.data("revealed", true);
  });
}

/* draw a red string along a chain, segment by segment */
async function animateString(chain) {
  if (!cy) return;
  for (let i = 0; i < chain.length - 1; i++) {
    const a = chain[i],
      b = chain[i + 1];
    let e = cy.edges().filter((ed) => {
      const s = ed.data("source"),
        t = ed.data("target");
      return (s === a && t === b) || (s === b && t === a);
    });
    if (e.length === 0) {
      e = cy.add({
        group: "edges",
        data: { id: "str" + a + b, source: a, target: b, type: "GOSSIP" },
      });
    }
    e.data("revealed", true);
    e.addClass("string");
    // travelling highlight on the nodes
    cy.$("#" + a).addClass("hot-node");
    cy.$("#" + b).addClass("hot-node");
    if (!REDUCED) await wait(420);
  }
}

/* ═══════════ SIGNATURE MOMENTS ═══════════ */
async function playGossip(g) {
  ensureGraphVisible();
  await animateString(g.chain);
  // flip standings with a visible tick, staggered
  for (const a of g.affected) {
    const card = $(`.dossier-card[data-id="${a.id}"]`);
    const cyNode = cy && cy.$("#" + a.id);
    if (cyNode) cyNode.addClass("pulse-node");
    if (card) {
      const st = $(".standing", card);
      st.dataset.s = a.to;
      st.querySelector(".dot").nextSibling.textContent = ""; // clear
      st.lastChild.textContent = standingLabel(a.to);
      card.classList.add("flip");
      setTimeout(() => card.classList.remove("flip"), 900);
    }
    if (!REDUCED) await wait(260);
  }
  pushToast(
    g.toast || "Word travels. It reaches those you have not yet met.",
    "ripple",
  );
}

async function playWhy(w) {
  ensureGraphVisible();
  if (cy) {
    cy.elements().addClass("dim");
    for (let i = 0; i < w.chain.length; i++) {
      const n = cy.$("#" + w.chain[i]);
      n.removeClass("dim").addClass("hot-node");
      if (i > 0) {
        const e = cy.edges().filter((ed) => {
          const s = ed.data("source"),
            t = ed.data("target");
          return (
            (s === w.chain[i - 1] && t === w.chain[i]) ||
            (s === w.chain[i] && t === w.chain[i - 1])
          );
        });
        e.removeClass("dim").addClass("string");
        e.data("revealed", true);
      }
      if (!REDUCED) await wait(380);
    }
    setTimeout(() => {
      cy.elements().removeClass("dim");
    }, 4200);
  }
  pushToast(
    "The board remembers the path. This is how the word reached her.",
    "ripple",
  );
}

async function playContradiction(c) {
  ensureGraphVisible();
  [c.a, c.b].forEach((id) => {
    const card = $(`.dossier-card[data-id="${id}"]`);
    if (card) card.classList.add("contradiction-glow");
    if (cy) cy.$("#" + id).addClass("pulse-node");
    setTimeout(() => card && card.classList.remove("contradiction-glow"), 3600);
  });
  if (cy) {
    let e = cy.edges().filter((ed) => {
      const s = ed.data("source"),
        t = ed.data("target");
      return (s === c.a && t === c.b) || (s === c.b && t === c.a);
    });
    if (e.length === 0)
      e = cy.add({
        group: "edges",
        data: {
          id: "contra" + c.a,
          source: c.a,
          target: c.b,
          type: "CONFLICT",
        },
      });
    e.addClass("string");
  }
  pushToast("Their stories do not align.", "ripple");
}

function ensureGraphVisible() {
  // if on desktop, flick the board to the graph tab so the moment is seen
  switchTab("graph");
  if (window.innerWidth <= 860) {
    openDrawer(true);
  }
}

/* ═══════════ TOASTS ═══════════ */
function pushToast(text, kind = "ripple") {
  const rail = $("#toast-rail");
  const t = document.createElement("div");
  t.className = "toast";
  const ico =
    kind === "ripple"
      ? '<svg class="ripple-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="7" opacity=".6"/><circle cx="12" cy="12" r="10.5" opacity=".3"/></svg>'
      : '<svg class="ripple-ico" viewBox="0 0 24 24" fill="currentColor"><path d="M21 11l-8-8H4v9l8 8 9-9zM7 8a1.5 1.5 0 110-3 1.5 1.5 0 010 3z"/></svg>';
  t.innerHTML = ico + "<span>" + text + "</span>";
  rail.appendChild(t);
  setTimeout(() => t.remove(), 5200);
}

/* ═══════════ DOSSIER MODAL ═══════════ */
function openDossier(id) {
  const sp = state.suspects.find((x) => x.id === id);
  if (!sp) return;
  const m = $("#dossier-modal");
  const history = state.journal.filter(
    (e) => e.voice === "npc" && e.speaker === sp.name,
  );
  m.innerHTML = `
    <button class="dm-close" aria-label="Close">&times;</button>
    <div class="dm-head">
      <div class="dm-portrait">${portraitSVG(sp.hue, 1)}</div>
      <div class="dm-titles">
        <div class="nm">${sp.name}</div>
        <div class="rl">${sp.role}</div>
        <div class="dm-standing-big">
          <span class="standing" data-s="${sp.standing}"><span class="dot" style="background:currentColor"></span>${standingLabel(sp.standing)} toward you</span>
        </div>
      </div>
    </div>
    <div class="dm-body">
      <div class="dm-section"><h4>What is known</h4><p>${sp.blurb}</p></div>
      <div class="dm-section"><h4>Interview record</h4>
        <div class="dm-history">${
          history.length
            ? history
                .map(
                  (h) =>
                    `<div class="hitem">\u201C${h.text}\u201D <span style="color:var(--paper-faint)">\u2014 turn ${h.turn}</span></div>`,
                )
                .join("")
            : '<div class="hitem" style="border:none">You have not yet questioned this person.</div>'
        }</div>
      </div>
      <button class="dm-ask">Question ${sp.name.split(" ").slice(-1)[0]}</button>
    </div>`;
  m.querySelector(".dm-close").addEventListener("click", closeDossier);
  m.querySelector(".dm-ask").addEventListener("click", () => {
    closeDossier();
    doAction("ask " + sp.name + " what they saw");
  });
  $("#dossier-overlay").classList.add("active");
}
function closeDossier() {
  $("#dossier-overlay").classList.remove("active");
}
$("#dossier-overlay").addEventListener("click", (e) => {
  if (e.target.id === "dossier-overlay") closeDossier();
});

/* ═══════════ QUICK ACTIONS ═══════════ */
const QUICK = [
  { label: "Search the study", text: "search the study" },
  { label: "Ask the butler", text: "ask Mr. Harrington what he saw" },
  {
    label: "Confront the Colonel",
    text: "confront Colonel Ashworth about the ledger",
  },
  {
    label: "Why won\u2019t the maid meet my eye?",
    text: "why does the maid distrust me",
  },
];
function buildQuickActions() {
  const row = $("#quick-row");
  row.innerHTML = "";
  QUICK.forEach((q) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "quick";
    b.textContent = q.label;
    b.addEventListener("click", () => doAction(q.text));
    row.appendChild(b);
  });
  const acc = document.createElement("button");
  acc.type = "button";
  acc.className = "quick accuse";
  acc.textContent = "\u2620 Name the killer";
  acc.addEventListener("click", openAccusation);
  row.appendChild(acc);
}

/* ═══════════ ACTION SUBMISSION (with in-world thinking + error states) ═══════════ */
const input = $("#action-input");
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 120) + "px";
});
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    $("#action-form").requestSubmit();
  }
});
$("#action-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const v = input.value.trim();
  if (!v) return;
  input.value = "";
  input.style.height = "auto";
  doAction(v);
});

async function doAction(text) {
  if (busy) return;
  busy = true;
  setInputEnabled(false);
  // demo hook: "/error" shows the in-world failure state
  const simulateError = text.trim() === "/error";

  const beat = showBreath();
  try {
    await wait(REDUCED ? 200 : 750 + Math.random() * 350); // GM composing / network latency
    if (simulateError) throw new Error("network");
    const next = await submitAction(text);
    beat.remove();
    state = next;
    // phase transitions
    if (state.phase === "accusation") {
      renderCasebar(state);
      await renderJournal(state);
      renderBoard(state);
      playClimax(state);
      busy = false;
      setInputEnabled(true);
      return;
    }
    renderCasebar(state);
    renderBoard(state);
    await renderJournal(state);
    // signature moments (turn-scoped)
    if (state.gossip_event) await playGossip(state.gossip_event);
    if (state.why_reveal) await playWhy(state.why_reveal);
    if (state.contradiction) await playContradiction(state.contradiction);
  } catch (err) {
    beat.remove();
    showError(text);
  }
  busy = false;
  setInputEnabled(true);
}
function setInputEnabled(on) {
  input.disabled = !on;
  $("#submit-move").disabled = !on;
  if (on) input.focus();
}
function showBreath() {
  const j = $("#journal");
  const b = document.createElement("div");
  b.className = "breath";
  b.innerHTML =
    '<span class="flame"></span><span>The manor holds its breath\u2026</span>';
  j.appendChild(b);
  j.scrollTop = j.scrollHeight;
  return b;
}
function showError(lastText) {
  const banner = $("#error-banner");
  banner.classList.add("show");
  $("#error-retry").onclick = () => {
    banner.classList.remove("show");
    doAction(lastText);
  };
  setTimeout(() => banner.classList.remove("show"), 6000);
}

/* ═══════════ ACCUSATION ═══════════ */
function openAccusation() {
  showScreen("screen-accuse");
  $("#accuse-choose").style.display = "";
  $("#accuse-climax").style.display = "none";
  const grid = $("#accuse-grid");
  grid.innerHTML = "";
  state.suspects.forEach((sp) => {
    const b = document.createElement("button");
    b.className = "accuse-pick";
    b.innerHTML = `<div class="nm">${sp.name}</div><div class="rl">${sp.role}</div>`;
    b.addEventListener("click", () => commitAccusation(sp));
    grid.appendChild(b);
  });
}
$("#accuse-cancel").addEventListener("click", () => showScreen("screen-play"));

async function commitAccusation(sp) {
  showScreen("screen-play");
  await doAction("I accuse " + sp.name);
  // correct accusation routes to playClimax via phase==='accusation'
}

async function playClimax(s) {
  const r = s.accusation_result;
  if (!r) {
    return;
  }
  showScreen("screen-accuse");
  $("#accuse-choose").style.display = "none";
  $("#accuse-climax").style.display = "";
  $("#climax-name").textContent = "The case against " + r.accused_name;
  const box = $("#climax-steps");
  box.innerHTML = "";
  r.pathLabels.forEach((lbl, i) => {
    const parts = lbl.split(" \u2014 ");
    const step = document.createElement("div");
    step.className = "climax-step";
    step.innerHTML = `<span class="climax-pin"></span><span class="lbl"><b>${parts[0]}</b>${parts[1] || ""}</span>`;
    box.appendChild(step);
  });
  const steps = $$(".climax-step", box);
  for (let i = 0; i < steps.length; i++) {
    await wait(REDUCED ? 150 : 900);
    steps[i].classList.add("lit");
  }
  await wait(REDUCED ? 300 : 1300);
  renderVerdict(r);
}

/* ═══════════ VERDICT ═══════════ */
function renderVerdict(r) {
  showScreen("screen-verdict");
  const stamp = $("#verdict-stamp");
  stamp.className = "verdict-stamp " + (r.correct ? "win" : "lose");
  stamp.textContent = r.correct ? "SOLVED" : "ACQUITTED";
  $("#verdict-headline").textContent = r.correct
    ? "You named " + r.accused_name + " — and you were right."
    : "The wrong soul stood accused.";
  $("#verdict-prose").textContent = r.correct
    ? "The ledger, the foxglove, and the maid\u2019s trembling account close like a trap around the Colonel. Motive, means, and opportunity \u2014 the manor gives up its killer. Justice, tonight, is served at Ravenwood."
    : "The true killer smiles into their brandy. By morning the household has closed ranks, the trail gone cold, and Lord Ravenwood\u2019s death will pass into the manor\u2019s long memory unavenged.";
}
$("#verdict-review").addEventListener("click", () => {
  showScreen("screen-play");
  switchTab("graph");
  if (cy) {
    cy.elements().removeClass("dim");
    cy.fit(undefined, 30);
  }
});
$("#verdict-restart").addEventListener("click", async () => {
  state = await getInitialState();
  renderedEntries = 0;
  $("#journal").innerHTML = "";
  cy = null;
  $("#cy").innerHTML = "";
  showScreen("screen-title");
});

/* ═══════════ BOARD TABS + MOBILE DRAWER ═══════════ */
function switchTab(name) {
  $$(".board-tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.tab === name),
  );
  $$(".board-panel").forEach((p) =>
    p.classList.toggle("active", p.dataset.panel === name),
  );
  if (name === "graph") {
    initCy(state);
    if (cy) {
      setTimeout(() => {
        cy.resize();
        cy.fit(undefined, 30);
      }, 60);
    }
  }
}
$$(".board-tab").forEach((t) =>
  t.addEventListener("click", () => switchTab(t.dataset.tab)),
);

function openDrawer(open) {
  const b = $("#case-board");
  b.classList.toggle("drawer-open", open);
}
$("#board-toggle").addEventListener("click", () =>
  openDrawer(!$("#case-board").classList.contains("drawer-open")),
);
$("#drawer-grabber").addEventListener("click", () => openDrawer(false));

/* ═══════════ TRUE GRAPH TOGGLE ═══════════ */
let trueGraph = false;
$("#truegraph-btn").addEventListener("click", () => {
  if (!cy) return;
  trueGraph = !trueGraph;
  cy.edges().forEach((e) =>
    e.data(
      "revealed",
      trueGraph
        ? true
        : (state.graph.edges.find((x, i) => "e" + i === e.id())?.revealed ??
            e.hasClass("string")),
    ),
  );
  $("#truegraph-btn").textContent = trueGraph
    ? "Hide hidden threads"
    : "View the true case graph";
  cy.fit(undefined, 30);
});

/* ═══════════ BOOT ═══════════ */
(async function boot() {
  state = await getInitialState();
  showScreen("screen-title");
})();
