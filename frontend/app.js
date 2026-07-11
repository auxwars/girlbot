// ---- Chat page -----------------------------------------------------------
const $ = (id) => document.getElementById(id);
const chat = $("chat");

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function toast(msg) {
  const t = $("toast"); t.textContent = msg; t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 1600);
}
function relianceText(v) {
  if (v >= 75) return "leaning hard on her data";
  if (v >= 45) return "mostly her data + some research";
  if (v >= 25) return "balanced";
  return "mostly outside research";
}
function syncReliance() { $("relianceLabel").textContent = relianceText(+$("reliance").value); }

function addMsg(role, text, cls = "") {
  const div = document.createElement("div");
  div.className = `msg ${role === "user" ? "me" : "bot"} ${cls}`.trim();
  div.textContent = text;
  chat.appendChild(div);
  window.scrollTo(0, document.body.scrollHeight);
  return div;
}
function bar(pct) { return `<div class="bar"><span style="width:${Math.round(pct * 100)}%"></span></div>`; }

function addTyping() {
  const d = document.createElement("div");
  d.className = "msg bot typing";
  d.innerHTML = "<span></span><span></span><span></span>";
  chat.appendChild(d);
  window.scrollTo(0, document.body.scrollHeight);
  return d;
}

function renderUnderTheHood(data) {
  const a = data.analysis;
  const p = ['<details class="uth"><summary>🔍 under the hood — what my read is based on</summary><div class="readout">'];
  if (a.trained && a.top_intent) {
    p.push(`<div class="kv"><b>her-model best guess:</b> <span class="pill good">${a.top_intent}</span> ${Math.round(a.confidence*100)}% sure</div>`);
    p.push(`<div class="meta">${escapeHtml(a.top_intent_desc || "")}</div>`);
    const dist = Object.entries(a.distribution).sort((x,y)=>y[1]-x[1]).slice(0,4);
    p.push('<h3>read distribution</h3>');
    for (const [k,v] of dist) { if (v < 0.02) continue; p.push(`<div class="kv">${k} — ${Math.round(v*100)}%${bar(v)}</div>`); }
    if (a.similar_cases?.length) {
      p.push('<h3>similar things she said before</h3>');
      for (const c of a.similar_cases) p.push(`<div class="case"><div class="m">"${escapeHtml(c.her_message)}" <span class="meta">(${Math.round(c.similarity*100)}% similar)</span></div><div class="mean">→ ${escapeHtml(c.true_meaning)}</div></div>`);
    }
    if (a.note) p.push(`<div class="hint">${escapeHtml(a.note)}</div>`);
  } else {
    p.push(`<div class="hint">${escapeHtml(a.note || "nothing learned about her yet — just keep talking to me (with training on).")}</div>`);
  }
  if (data.research?.length) {
    p.push('<h3>outside research pulled</h3>');
    for (const r of data.research) { const tag = r.source === "social" ? "🧵" : "📄"; p.push(`<div class="src"><div class="t">${tag} ${escapeHtml(r.title)}</div><div class="s">${escapeHtml(r.snippet || "")}</div>${r.url ? `<a href="${r.url}" target="_blank" rel="noopener">source</a>` : ""}</div>`); }
  }
  if (data.events_used?.length) {
    p.push('<h3>recent events I remembered</h3>');
    for (const e of data.events_used) p.push(`<div class="hint">• ${escapeHtml(e.text)}</div>`);
  }
  const b = data.blend;
  p.push(`<div class="hint" style="margin-top:8px">blend → ${b.ml_cases} of her cases · ${b.social} social · ${b.research} papers${data.training_on ? " · 🧠 learning on" : ""}</div>`);
  p.push('</div></details>');
  const wrap = document.createElement("div");
  wrap.className = "msg info";
  wrap.innerHTML = p.join("");
  chat.appendChild(wrap);
  window.scrollTo(0, document.body.scrollHeight);
}

async function send() {
  const q = $("q").value.trim();
  if (!q) return;
  $("send").disabled = true; $("q").value = ""; $("q").style.height = "auto";
  addMsg("user", q);
  const thinking = addTyping();
  try {
    const resp = await fetch("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: q, reliance: +$("reliance").value, use_research: $("useResearch").checked }),
    });
    if (resp.status === 401) { location.reload(); return; }
    const data = await resp.json();
    thinking.remove();
    addMsg("bot", data.reply);
    renderUnderTheHood(data);
  } catch {
    thinking.remove();
    addMsg("bot", "⚠️ couldn't reach the backend. is the server running?");
  } finally {
    $("send").disabled = false; $("q").focus();
  }
}

async function loadHistory() {
  try {
    const { messages } = await (await fetch("/api/history")).json();
    if (!messages?.length) {
      addMsg("bot", "yo wsg 👀 what'd she say / do? drop it here n i'll tell u what it prob means");
      return;
    }
    for (const m of messages) addMsg(m.role, m.content);
  } catch {}
}

// boot: check auth, then wire up
(async () => {
  let me;
  try { me = await (await fetch("/api/me")).json(); }
  catch { document.body.innerHTML = "backend unreachable"; return; }

  if (me.google_enabled && !me.authenticated) {
    $("gate").style.display = "flex";
    return;
  }
  $("appwrap").style.display = "flex";

  // apply saved defaults + status
  if (me.prefs) {
    $("reliance").value = me.prefs.reliance;
    $("useResearch").checked = me.prefs.use_research;
    const model = me.prefs.model || "";
    const on = me.prefs.has_anthropic;
    $("presence").textContent = on ? "active now" : "tap ⚙︎ to add your key";
    $("status").innerHTML =
      `<span class="dot ${on ? "on" : ""}"></span>` +
      (on ? `online · ${model}` : "no API key — see Settings") +
      ` · ${me.example_count} learned` +
      (me.prefs.training_enabled ? " · 🧠 learning on" : " · learning off");
  }
  syncReliance();
  $("reliance").addEventListener("input", syncReliance);
  $("send").addEventListener("click", send);
  $("infoBtn").addEventListener("click", () => { $("infoPanel").hidden = !$("infoPanel").hidden; });
  const ta = $("q");
  ta.addEventListener("input", () => { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 120) + "px"; });
  ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } });
  $("clearMem").addEventListener("click", async () => {
    if (!confirm("Wipe this chat history? (Your learned patterns about her stay.)")) return;
    await fetch("/api/memory/clear", { method: "POST" });
    chat.innerHTML = ""; addMsg("bot", "aight clean slate 🙏 wsg?");
    toast("chat cleared");
  });

  await loadHistory();
})();
