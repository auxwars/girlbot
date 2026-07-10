// ---- Settings page -------------------------------------------------------
const $ = (id) => document.getElementById(id);

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

async function loadAccount() {
  const me = await (await fetch("/api/me")).json();
  const box = $("account");
  if (!me.google_enabled) {
    box.innerHTML = `<p class="hint">Running in <b>local mode</b> — no login, single user, memory lives in the server's database file. To make memory permanent and private per person (and deploy it), set up Google sign-in (see the README).</p>`;
    return;
  }
  if (!me.authenticated) {
    box.innerHTML = `<a class="gbtn" href="/auth/login"><span class="g">G</span> Sign in with Google</a>`;
    return;
  }
  const u = me.user || {};
  box.innerHTML = `
    <div class="acct">
      ${u.picture ? `<img src="${u.picture}" class="avatar" referrerpolicy="no-referrer"/>` : ""}
      <div><div class="m">${escapeHtml(u.name || "")}</div><div class="meta">${escapeHtml(u.email || "")}</div></div>
      <a class="secondary btnlink" href="/auth/logout">Sign out</a>
    </div>
    <p class="hint">Your memory is permanent and tied to this Google account.</p>`;
}

async function loadSettings() {
  const s = await (await fetch("/api/settings")).json();
  $("anthropic_key").value = s.anthropic_key || "";
  $("exa_key").value = s.exa_key || "";
  $("openalex_mailto").value = s.openalex_mailto || "";
  $("model").value = s.model || "claude-opus-4-8";
  $("training_enabled").checked = !!s.training_enabled;
  $("use_research").checked = !!s.use_research;
  $("reliance").value = s.reliance;
  $("relianceLabel").textContent = relianceText(s.reliance);

  // hint when env already provides a key
  const ed = s.env_defaults || {};
  const holders = [
    ["anthropic_key", ed.anthropic, "server already has one"],
    ["exa_key", ed.exa, "server already has one"],
    ["openalex_mailto", ed.openalex, "server already has one"],
  ];
  for (const [id, has, txt] of holders) {
    if (has && !$(id).value) $(id).placeholder = `(${txt}) ` + $(id).placeholder;
  }
}

$("reliance").addEventListener("input", () => { $("relianceLabel").textContent = relianceText(+$("reliance").value); });

$("save").addEventListener("click", async () => {
  const body = {
    anthropic_key: $("anthropic_key").value.trim(),
    exa_key: $("exa_key").value.trim(),
    openalex_mailto: $("openalex_mailto").value.trim(),
    model: $("model").value,
    training_enabled: $("training_enabled").checked,
    use_research: $("use_research").checked,
    reliance: +$("reliance").value,
  };
  await fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  toast("saved ✅");
});

async function loadLearned() {
  const { examples } = await (await fetch("/api/examples")).json();
  const seedCount = examples.filter((e) => e.is_seed).length;
  $("learnedNote").innerHTML = examples.length
    ? `${examples.length} example(s)${seedCount ? ` · ${seedCount} are built-in demo rows (not her) — wipe them once you've built up your own` : " · all your own data 🔥"}`
    : "Nothing learned yet. Chat with me (training on) and I'll fill this in.";
  $("clearSeed").style.display = seedCount ? "inline-block" : "none";

  $("examples").innerHTML = examples.length ? examples.map((e) => `
    <div class="item"><div class="row">
      <div>
        <div class="m">"${escapeHtml(e.her_message)}" <span class="pill">${e.intent}</span>${e.is_seed ? '<span class="seed-badge">demo</span>' : ""}</div>
        ${e.context ? `<div class="meta">context: ${escapeHtml(e.context)}</div>` : ""}
        <div class="meta">means: ${escapeHtml(e.true_meaning)}</div>
      </div>
      <button class="x" data-id="${e.id}" title="delete">✕</button>
    </div></div>`).join("") : "";
  $("examples").querySelectorAll("button.x").forEach((b) => b.addEventListener("click", async () => {
    await fetch(`/api/examples/${b.dataset.id}`, { method: "DELETE" }); loadLearned(); toast("deleted");
  }));

  const { events } = await (await fetch("/api/events")).json();
  $("events").innerHTML = events.length ? events.map((e) => `
    <div class="item"><div class="row">
      <div>${escapeHtml(e.text)}<div class="meta">${new Date(e.created_at).toLocaleString()}</div></div>
      <button class="x" data-id="${e.id}">✕</button>
    </div></div>`).join("") : '<p class="hint">Nothing remembered yet.</p>';
  $("events").querySelectorAll("button.x").forEach((b) => b.addEventListener("click", async () => {
    await fetch(`/api/events/${b.dataset.id}`, { method: "DELETE" }); loadLearned(); toast("forgotten");
  }));
}

$("clearSeed").addEventListener("click", async () => {
  if (!confirm("Wipe the built-in demo examples? Your own data stays.")) return;
  const { removed } = await (await fetch("/api/examples/clear-seed", { method: "POST" })).json();
  loadLearned(); toast(`wiped ${removed} demo rows`);
});
$("clearAll").addEventListener("click", async () => {
  if (!confirm("Wipe ALL learned examples about her? This can't be undone.")) return;
  const { removed } = await (await fetch("/api/examples/clear-all", { method: "POST" })).json();
  loadLearned(); toast(`wiped ${removed} examples`);
});

(async () => {
  await loadAccount();
  await loadSettings();
  await loadLearned();
})();
