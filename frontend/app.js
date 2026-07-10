// ---- Ask page: the chat with the bot ------------------------------------
const $ = (id) => document.getElementById(id);
const chat = $("chat");
const history = []; // {role, content} kept client-side for short-term memory

function relianceText(v) {
  if (v >= 75) return "leaning hard on HER data";
  if (v >= 45) return "mostly her data + some research";
  if (v >= 25) return "balanced";
  return "mostly outside research";
}

function syncReliance() {
  $("relianceLabel").textContent = relianceText(+$("reliance").value);
}
$("reliance").addEventListener("input", syncReliance);
syncReliance();

function addMsg(role, text, cls = "") {
  const div = document.createElement("div");
  div.className = `msg ${role === "user" ? "me" : "bot"} ${cls}`.trim();
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollIntoView(false);
  window.scrollTo(0, document.body.scrollHeight);
  return div;
}

function bar(pct) {
  return `<div class="bar"><span style="width:${Math.round(pct * 100)}%"></span></div>`;
}

function renderUnderTheHood(data) {
  const a = data.analysis;
  const parts = [];

  parts.push('<details class="uth" open><summary>🔍 under the hood — what my read is based on</summary><div class="readout">');

  // ML section
  if (a.trained && a.top_intent) {
    parts.push(`<div class="kv"><b>Her-model best guess:</b> <span class="pill good">${a.top_intent}</span> ${Math.round(a.confidence*100)}% sure</div>`);
    parts.push(`<div class="meta" style="color:var(--muted);font-size:.8rem">${a.top_intent_desc || ""}</div>`);
    const dist = Object.entries(a.distribution).sort((x,y)=>y[1]-x[1]).slice(0,4);
    parts.push('<h3>read distribution</h3>');
    for (const [k,v] of dist) {
      if (v < 0.02) continue;
      parts.push(`<div class="kv">${k} — ${Math.round(v*100)}%${bar(v)}</div>`);
    }
    if (a.similar_cases && a.similar_cases.length) {
      parts.push('<h3>similar things she said before</h3>');
      for (const c of a.similar_cases) {
        parts.push(`<div class="case"><div class="m">"${escapeHtml(c.her_message)}" <span class="meta">(${Math.round(c.similarity*100)}% similar)</span></div><div class="mean">→ ${escapeHtml(c.true_meaning)}</div></div>`);
      }
    }
    if (a.note) parts.push(`<div class="hint">${escapeHtml(a.note)}</div>`);
  } else {
    parts.push(`<div class="hint">${escapeHtml(a.note || "No data learned about her yet — head to Train.")}</div>`);
  }

  // research section
  if (data.research && data.research.length) {
    parts.push('<h3>outside research pulled</h3>');
    for (const r of data.research) {
      const tag = r.source === "social" ? "🧵" : "📄";
      parts.push(`<div class="src"><div class="t">${tag} ${escapeHtml(r.title)}</div><div class="s">${escapeHtml(r.snippet || "")}</div>${r.url ? `<a href="${r.url}" target="_blank" rel="noopener">source</a>` : ""}</div>`);
    }
  }

  // events section
  if (data.events_used && data.events_used.length) {
    parts.push('<h3>recent events I remembered</h3>');
    for (const e of data.events_used) parts.push(`<div class="hint">• ${escapeHtml(e.text)}</div>`);
  }

  const b = data.blend;
  parts.push(`<div class="hint" style="margin-top:8px">blend used → ${b.ml_cases} of her cases · ${b.social} social · ${b.research} papers</div>`);
  parts.push('</div></details>');

  const wrap = document.createElement("div");
  wrap.className = "msg bot";
  wrap.style.maxWidth = "92%";
  wrap.innerHTML = parts.join("");
  chat.appendChild(wrap);
  window.scrollTo(0, document.body.scrollHeight);
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function send() {
  const q = $("q").value.trim();
  if (!q) return;
  $("send").disabled = true;
  $("q").value = "";
  addMsg("user", q);
  history.push({ role: "user", content: q });
  const thinking = addMsg("bot", "reading the room…", "thinking");

  try {
    const resp = await fetch("/api/advice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: q,
        reliance: +$("reliance").value,
        use_research: $("useResearch").checked,
        history: history.slice(0, -1), // everything before this turn
      }),
    });
    const data = await resp.json();
    thinking.remove();
    addMsg("bot", data.reply);
    history.push({ role: "assistant", content: data.reply });
    renderUnderTheHood(data);
  } catch (e) {
    thinking.remove();
    addMsg("bot", "⚠️ couldn't reach the backend. is the server running?");
  } finally {
    $("send").disabled = false;
    $("q").focus();
  }
}

$("send").addEventListener("click", send);
$("q").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});

// status line
(async () => {
  try {
    const h = await (await fetch("/api/health")).json();
    const dot = h.claude_enabled ? "dot on" : "dot";
    $("status").innerHTML =
      `<span class="${dot}"></span> ` +
      (h.claude_enabled ? `bot online (${h.model})` : "bot offline — add ANTHROPIC_API_KEY") +
      ` · ${h.example_count} examples learned` +
      (h.exa_enabled ? " · web research on" : " · web research off (no Exa key)");
  } catch {
    $("status").innerHTML = '<span class="dot"></span> backend unreachable';
  }
})();
