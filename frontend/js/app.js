// UI controller: renders server state and forwards player intents.
const $ = id => document.getElementById(id);
const state = { meta: null, character: null, poll: null };

function show(screen) {
  for (const s of document.querySelectorAll(".screen")) s.hidden = s.id !== `screen-${screen}`;
  if (state.poll && screen !== "world") { clearInterval(state.poll); state.poll = null; }
}

let toastTimer;
function toast(msg, isError = false) {
  const t = $("toast");
  t.textContent = msg; t.className = isError ? "error" : ""; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), 3500);
}

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

async function guarded(fn) {
  try { return await fn(); }
  catch (e) {
    if (e.status === 401) { Api.setToken(null); return boot(); }
    toast(e.message, true);
  }
}

// ---- auth --------------------------------------------------------------
$("auth-form").addEventListener("submit", ev => {
  ev.preventDefault();
  const mode = ev.submitter?.dataset.mode || "login";
  const f = new FormData(ev.target);
  guarded(async () => {
    const body = { username: f.get("username").trim(), passphrase: f.get("passphrase") };
    const res = await Api.post(mode === "register" ? "/accounts" : "/sessions", body);
    Api.setToken(res.token);
    ev.target.reset();
    await boot();
  });
});

$("logout").addEventListener("click", () => guarded(async () => {
  await Api.del("/sessions").catch(() => {});
  Api.setToken(null);
  await boot();
}));

// ---- characters ----------------------------------------------------------
async function showCharacters() {
  const chars = await Api.get("/characters");
  const list = $("character-list");
  list.replaceChildren(...chars.map(c => el("li", {},
    el("span", {}, el("strong", { textContent: c.name }), ` — Level ${c.level} ${c.class_name}`),
    el("button", { textContent: "Play", onclick: () => guarded(() => enterWorld(c.id)) }))));
  $("no-characters").hidden = chars.length > 0;
  show("characters");
}

$("create-form").addEventListener("submit", ev => {
  ev.preventDefault();
  const f = new FormData(ev.target);
  guarded(async () => {
    const c = await Api.post("/characters", { name: f.get("name").trim(), class_id: f.get("class_id") });
    ev.target.reset();
    toast(`${c.name} has arrived in Ashenhold.`);
    await showCharacters();
  });
});

function renderClassOptions() {
  const fs = $("class-options");
  Object.entries(state.meta.classes).forEach(([id, c], i) => fs.append(el("label", {},
    el("input", { type: "radio", name: "class_id", value: id, required: true, checked: i === 0 }),
    el("span", {}, el("strong", { textContent: c.name }), ` — ${c.role}. Signature: ${c.signature}.`))));
}

// ---- world ---------------------------------------------------------------
async function enterWorld(id) {
  state.character = await Api.post(`/characters/${id}/select`);
  show("world");
  await refreshWorld();
  state.poll = setInterval(() => guarded(refreshWorld), 5000); // see partner's changes
}

async function refreshWorld() {
  const id = state.character.id;
  const [c, world, inv, chron] = await Promise.all([
    Api.get(`/characters/${id}`), Api.get("/world"),
    Api.get(`/characters/${id}/inventory`), Api.get("/chronicle?limit=30")]);
  state.character = c;
  const locs = state.meta.locations, loc = locs[c.location_id];
  const defense = world.state.ashenhold_defense.value;

  $("char-name").textContent = c.name;
  $("char-summary").textContent = `Level ${c.level} ${c.class_name} · ${c.experience} XP`;
  $("loc-name").textContent = loc.name;
  $("loc-desc").textContent = loc.description;

  const actions = [];
  if (c.location_id === "ashenhold")
    actions.push(el("button", { textContent: "Reinforce the walls", disabled: defense >= 100,
      onclick: () => act(() => Api.post("/world/actions",
        { character_id: id, action: "fortify", expected_version: world.state.ashenhold_defense.version }),
        r => `Defenses now ${r.value}.`) }));
  if (c.location_id !== "ashenhold")
    actions.push(el("button", { textContent: "Gather resources",
      onclick: () => act(() => Api.post(`/characters/${id}/gather`), r => `Gathered 1 ${r.item_name}.`) }));
  $("actions").replaceChildren(...actions);

  $("travel").replaceChildren(...Object.entries(locs).filter(([k]) => k !== c.location_id).map(([k, l]) => {
    const locked = l.requires && (world.state[l.requires[0]]?.value ?? 0) < l.requires[1];
    return el("button", { className: "secondary", textContent: locked ? `${l.name} (locked)` : l.name,
      title: locked ? `Requires Ashenhold defenses ≥ ${l.requires[1]}` : "",
      onclick: () => act(() => Api.post(`/characters/${id}/travel`,
        { location_id: k, expected_version: c.version }), () => `You travel to ${l.name}.`) });
  }));

  $("inventory").replaceChildren(...(inv.length ? inv.map(i => el("li", {},
    el("span", { textContent: i.name }), el("span", { textContent: `×${i.quantity}` })))
    : [el("li", { className: "muted", textContent: "Empty" })]));

  $("defense-val").textContent = `${defense} / 100`;
  $("defense-bar").value = defense;
  $("ashenhold-status").textContent = `Status: ${world.state.ashenhold_status.value}` +
    (defense >= 50 ? " · The road to the Hollow Bastion is secure." : "");
  $("adventurers").replaceChildren(...world.adventurers.map(a => el("li", {},
    el("span", { textContent: `${a.name}${a.id === id ? " (you)" : ""}` }),
    el("span", { className: "muted", textContent: `${a.class_name} · ${locs[a.location_id]?.name ?? a.location_id}` }))));
  $("chronicle").replaceChildren(...chron.map(e => el("li", {},
    el("time", { textContent: new Date(e.occurred_at).toLocaleString() }), e.description)));
}

async function act(call, describe) {
  await guarded(async () => {
    try { toast(describe(await call())); }
    catch (e) { if (e.status === 409) toast("The world changed while you were deciding — refreshed.", true); else throw e; }
    await refreshWorld();
  });
}

$("back").addEventListener("click", () => guarded(showCharacters));

// ---- boot ----------------------------------------------------------------
async function boot() {
  if (!state.meta) { state.meta = await Api.get("/meta"); renderClassOptions(); }
  if (!Api.hasToken()) { $("whoami").hidden = true; return show("auth"); }
  const me = await Api.get("/me").catch(e => { if (e.status === 401) Api.setToken(null); else throw e; });
  if (!me) return boot();
  $("username").textContent = me.username; $("whoami").hidden = false;
  if (me.selected_character_id) {
    try { return await enterWorld(me.selected_character_id); } catch { /* fall through */ }
  }
  await showCharacters();
}

boot().catch(e => toast(e.message, true));
