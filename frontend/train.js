// ---- Train page: feed the model examples + memory ------------------------
const $ = (id) => document.getElementById(id);
let INTENTS = {};

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 1600);
}

async function loadIntents() {
  const { intents } = await (await fetch("/api/intents")).json();
  INTENTS = intents;
  const sel = $("intent");
  sel.innerHTML = "";
  for (const [key, desc] of Object.entries(intents)) {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = key;
    opt.title = desc;
    sel.appendChild(opt);
  }
  updateIntentDesc();
}
function updateIntentDesc() {
  $("intentDesc").textContent = INTENTS[$("intent").value] || "";
}
$("intent") && $("intent").addEventListener("change", updateIntentDesc);

async function loadExamples() {
  const { examples } = await (await fetch("/api/examples")).json();
  const box = $("examples");
  const seedCount = examples.filter((e) => e.is_seed).length;
  $("seedNote").textContent = seedCount
    ? `${seedCount} of these are built-in demo examples (not her) — wipe them once you've added your own.`
    : "All of this is your own data. 🔥";
  $("clearSeed").style.display = seedCount ? "inline-block" : "none";

  if (!examples.length) {
    box.innerHTML = '<p class="hint">Nothing yet. Label a few of her messages above.</p>';
    return;
  }
  box.innerHTML = examples
    .map(
      (e) => `
    <div class="item">
      <div class="row">
        <div>
          <div class="m">"${escapeHtml(e.her_message)}"
            <span class="pill">${e.intent}</span>
            ${e.is_seed ? '<span class="seed-badge">demo</span>' : ""}
          </div>
          ${e.context ? `<div class="meta">context: ${escapeHtml(e.context)}</div>` : ""}
          <div class="meta">means: ${escapeHtml(e.true_meaning)}</div>
        </div>
        <button class="x" title="delete" data-id="${e.id}">✕</button>
      </div>
    </div>`
    )
    .join("");
  box.querySelectorAll("button.x").forEach((b) =>
    b.addEventListener("click", async () => {
      await fetch(`/api/examples/${b.dataset.id}`, { method: "DELETE" });
      loadExamples();
      toast("deleted");
    })
  );
}

async function loadEvents() {
  const { events } = await (await fetch("/api/events")).json();
  const box = $("events");
  if (!events.length) {
    box.innerHTML = '<p class="hint">Nothing logged yet.</p>';
    return;
  }
  box.innerHTML = events
    .map(
      (e) => `
    <div class="item"><div class="row">
      <div>${escapeHtml(e.text)}<div class="meta">${new Date(e.created_at).toLocaleString()}</div></div>
      <button class="x" data-id="${e.id}">✕</button>
    </div></div>`
    )
    .join("");
  box.querySelectorAll("button.x").forEach((b) =>
    b.addEventListener("click", async () => {
      await fetch(`/api/events/${b.dataset.id}`, { method: "DELETE" });
      loadEvents();
      toast("forgotten");
    })
  );
}

$("addExample").addEventListener("click", async () => {
  const her = $("her").value.trim();
  const mean = $("mean").value.trim();
  if (!her || !mean) { toast("need the message + what it meant"); return; }
  await fetch("/api/examples", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      her_message: her,
      context: $("ctx").value.trim(),
      true_meaning: mean,
      intent: $("intent").value,
    }),
  });
  $("her").value = ""; $("ctx").value = ""; $("mean").value = "";
  await loadExamples();
  toast("learned it 🧠");
});

$("addEvent").addEventListener("click", async () => {
  const text = $("event").value.trim();
  if (!text) return;
  await fetch("/api/events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  $("event").value = "";
  await loadEvents();
  toast("remembered");
});

$("clearSeed").addEventListener("click", async () => {
  if (!confirm("Wipe the built-in demo examples? Your own data stays.")) return;
  const { removed } = await (await fetch("/api/examples/clear-seed", { method: "POST" })).json();
  await loadExamples();
  toast(`wiped ${removed} demo rows`);
});

(async () => {
  try {
    const h = await (await fetch("/api/health")).json();
    const dot = h.claude_enabled ? "dot on" : "dot";
    $("status").innerHTML = `<span class="${dot}"></span> ${h.example_count} examples learned`;
  } catch { $("status").innerHTML = '<span class="dot"></span> backend unreachable'; }
  await loadIntents();
  await loadExamples();
  await loadEvents();
})();
