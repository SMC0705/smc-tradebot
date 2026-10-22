// Live-Ansichten der App im Weltraum-Look (Vorbild: Raumschiff-Video): Raumschiff (isometrisch), Orbit, Rat, Kugel.
// Nur Anzeige – liest ausschließlich status.json. Animationen stoppen, wenn die App im Hintergrund ist, und
// laufen gar nicht, wenn am Handy "Bewegung reduzieren" eingeschaltet ist.
const LIVE = (() => {
  let sub = "schiff", raf = 0, offs = [], focusRoom = null;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // Team-Farben (Neon auf dunklem Grund), jede Farbe hat zusätzlich ein Text-Label
  const TEAM_COL = {krypto: "#5aa2ff", meme: "#ff8a4c", markt: "#2fd39a", makro: "#ffc23d", fokus: "#ff6fb5"};
  // Noten-Skala (sequenziell): niedrig = dunkles Violett, hoch = helles Cyan
  const RAMP = ["#3b2a7a", "#5b3fc4", "#7c5cff", "#38bdf8", "#7dd3fc", "#e0f2fe"];
  const rampCol = s => RAMP[Math.max(0, Math.min(RAMP.length - 1, Math.round(s * (RAMP.length - 1))))];
  const SUBS = [["schiff", "Raumschiff"], ["orbit", "Orbit"], ["rat", "Rat"], ["kugel", "Kugel"]];
  const num2 = v => (v ?? 0).toLocaleString("de-DE", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const MONO = "JetBrains Mono, ui-monospace, monospace", SANS = "Space Grotesk, system-ui, sans-serif";

  function on(el, ev, fn, opt) { el.addEventListener(ev, fn, opt); offs.push(() => el.removeEventListener(ev, fn, opt)); }
  function every(ms, fn) { const h = setInterval(() => { if (!document.hidden) fn(); }, ms); offs.push(() => clearInterval(h)); }
  function loop(step) {
    if (reduce) { step(0, 0); return; }
    const t0 = performance.now();
    let last = 0;
    const tick = now => { const t = (now - t0) / 1000; if (!document.hidden) step(t, Math.min(0.1, t - last)); last = t; raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
  }
  function unmount() { cancelAnimationFrame(raf); raf = 0; offs.forEach(f => f()); offs = []; }
  function tip(box, html, x, y) {
    const t = box.querySelector(".vtip");
    if (!html) { t.style.display = "none"; return; }
    t.innerHTML = html; t.style.display = "block";
    const w = box.clientWidth, tw = t.offsetWidth;
    t.style.left = Math.max(4, Math.min(w - tw - 4, x - tw / 2)) + "px"; t.style.top = Math.max(4, y - t.offsetHeight - 14) + "px";
  }
  const teamName = (data, tid) => (data.teams && data.teams[tid] ? data.teams[tid].name : tid);
  function seeded(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }
  function totals(data) {
    const B = Object.values(data.bots), n = B.reduce((a, b) => a + (b.stats.trades || 0), 0);
    const wins = B.reduce((a, b) => a + (b.stats.winrate != null ? b.stats.winrate * b.stats.trades / 100 : 0), 0);
    let sig = 0, bought = 0;
    B.forEach(b => { const d = b.checks && b.checks.day; if (d) { sig += d.signals || 0; bought += d.bought || 0; } });
    return {n, win: n ? Math.round(wins / n * 100) : null, sig, bought, open: B.reduce((a, b) => a + b.positions.length, 0),
            pnl: data.pool.equity - data.pool.start};
  }
  function sceneHead(data, title) {
    const T = totals(data);
    return `<div class="scene-h"><div class="lbl">${title}</div>
      <div class="hero-n ${T.pnl >= 0 ? "glow-up" : "glow-down"}" style="font-size:30px">${eurS(T.pnl)} <span style="font-size:14px" class="${cls(data.pool.pnl_pct)}">${pc(data.pool.pnl_pct)}</span></div>
      <div class="kpis" style="grid-template-columns:repeat(3,1fr);margin-top:10px"><div><b>${T.win == null ? "–" : T.win + " %"}</b><span>Treffer&shy;quote</span></div>
      <div><b>${T.bought}</b><span>Käufe 24 Std.</span></div><div><b>${T.sig}</b><span>Signale 24 Std.</span></div></div></div>`;
  }

  // ---------------------------------------------------------------------------------------------
  function view(data) {
    const seg = `<div class="seg">${SUBS.map(([k, l]) => `<button data-sub="${k}" class="${k === sub ? "on" : ""}">${l}</button>`).join("")}</div>`;
    const body = sub === "orbit" ? viewOrbit(data) : sub === "rat" ? viewRat(data) : sub === "kugel" ? viewKugel(data) : viewSchiff(data);
    return seg + body;
  }
  function mount(data) {
    unmount();
    const el = document.getElementById("viz");
    if (!el) return;
    if (sub === "schiff") mountSchiff(el, data);
    else if (sub === "orbit") mountOrbit(el, data);
    else if (sub === "kugel") mountKugel(el, data);
    else if (sub === "rat") mountRat(el, data);
  }

  // --- 1) Raumschiff: isometrisches Deck, jeder Bot ein Roboter in seinem Raum --------------------
  const S = 11.2, OX = 161, OY = 44, VW = 360, VH = 232;
  const iso = (x, y, z = 0) => [(x - y) * 0.866 * S + OX, (x + y) * 0.5 * S - z * S + OY];
  const P = (...pts) => pts.map(p => iso(...p).map(v => v.toFixed(1)).join(",")).join(" ");
  const poly = (pts, fill, extra = "") => `<polygon points="${P(...pts)}" fill="${fill}" ${extra}/>`;
  const ROOMS = [
    {id: "test", name: "Testkammer", short: "Test", kind: "test", x0: 0, y0: 0, x1: 4.5, y1: 4.5},
    {id: "krypto", short: "Krypto", team: "krypto", x0: 5, y0: 0, x1: 10.5, y1: 4.5},
    {id: "markt", short: "Börse", team: "markt", x0: 11, y0: 0, x1: 16, y1: 4.5},
    {id: "makro", short: "Krise", team: "makro", x0: 0, y0: 5, x1: 4.5, y1: 8},
    {id: "rat", name: "Brücke (Rat)", short: "Brücke", kind: "rat", x0: 5, y0: 5, x1: 10.5, y1: 8},
    {id: "fokus", short: "Fokus", team: "fokus", x0: 11, y0: 5, x1: 16, y1: 8},
    {id: "bank", name: "Ersatzbank", short: "Bank", kind: "bank", x0: 0, y0: 8.5, x1: 4.5, y1: 12},
    {id: "meme", short: "Meme", team: "meme", x0: 5, y0: 8.5, x1: 10.5, y1: 12},
    {id: "tresor", name: "Tresor", short: "Tresor", kind: "tresor", x0: 11, y0: 8.5, x1: 16, y1: 12},
  ];
  const STAGE_F = {bank: 0, probe: 0.25, halb: 0.5, voll: 1};

  function box(x, y, z, w, d, h, top, left, right, extra = "") {
    const a = [x, y + d, z], b = [x + w, y + d, z], c = [x + w, y, z];
    return poly([[x, y, z + h], [x + w, y, z + h], [x + w, y + d, z + h], [x, y + d, z + h]], top, extra)
      + poly([a, b, [x + w, y + d, z + h], [x, y + d, z + h]], left, extra)
      + poly([b, c, [x + w, y, z + h], [x + w, y + d, z + h]], right, extra);
  }
  function viewSchiff(data) {
    return `<div class="card scene">${sceneHead(data, "Gesamt seit Start · alle Bots")}
      <div id="viz" class="vbox"><div class="room-pop"><button data-ship>‹ Ganzes Schiff</button></div>
        <svg viewBox="0 0 ${VW} ${VH}" class="vsvg" role="img" aria-label="Raumschiff mit allen Bots"></svg><div class="vtip"></div></div>
      <div id="roompanel"></div></div>`;
  }
  function shipBackdrop() {
    const r = seeded(11);
    let stars = "";
    for (let i = 0; i < 70; i++) {
      const x = r() * VW, y = r() * VH, s = r() > 0.9 ? 1.1 : 0.45 + r() * 0.4;
      stars += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${s.toFixed(2)}" fill="${r() > 0.75 ? "#c4b5fd" : "#fff"}" opacity="${(0.35 + r() * 0.6).toFixed(2)}"
        ${!reduce && r() > 0.7 ? `class="vglow" style="animation-delay:${(r() * 2).toFixed(2)}s"` : ""}/>`;
    }
    return `<defs>
      <radialGradient id="neb1" cx=".8" cy=".1" r=".6"><stop offset="0" stop-color="#7c3aed" stop-opacity=".55"/><stop offset="1" stop-color="#7c3aed" stop-opacity="0"/></radialGradient>
      <radialGradient id="neb2" cx=".1" cy=".9" r=".55"><stop offset="0" stop-color="#c026d3" stop-opacity=".35"/><stop offset="1" stop-color="#c026d3" stop-opacity="0"/></radialGradient>
      <radialGradient id="planet" cx=".35" cy=".3" r=".75"><stop offset="0" stop-color="#e9d5ff"/><stop offset=".35" stop-color="#a855f7"/><stop offset="1" stop-color="#2e1065"/></radialGradient>
      <linearGradient id="flame" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#fff"/><stop offset=".25" stop-color="#f0abfc"/><stop offset=".6" stop-color="#a855f7" stop-opacity=".6"/><stop offset="1" stop-color="#7c3aed" stop-opacity="0"/></linearGradient>
      <radialGradient id="holo" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#a5f3fc" stop-opacity=".9"/><stop offset="1" stop-color="#22d3ee" stop-opacity="0"/></radialGradient>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    </defs>
    <rect width="${VW}" height="${VH}" fill="#0a0618"/><rect width="${VW}" height="${VH}" fill="url(#neb1)"/><rect width="${VW}" height="${VH}" fill="url(#neb2)"/>${stars}
    <circle cx="26" cy="214" r="52" fill="url(#planet)" opacity=".9"/>
    <ellipse cx="26" cy="216" rx="84" ry="13" fill="none" stroke="#e879f9" stroke-opacity=".45" stroke-width="2" transform="rotate(-14 26 216)"/>`;
  }
  function hull() {
    const pts = [[-0.7, -0.7, 0], [16.7, -0.7, 0], [16.7, 3.6, 0], [19.8, 6.5, 0], [16.7, 9.4, 0], [16.7, 12.7, 0], [-0.7, 12.7, 0]];
    const low = pts.map(p => [p[0], p[1], -0.9]);
    // sichtbare Seitenflächen: rechts (+x) und vorne (+y)
    let sides = "";
    for (let i = 1; i < pts.length; i++) {
      const a = pts[i - 1], b = pts[i];
      if (b[1] >= a[1] || b[0] >= 16.7) sides += poly([a, b, low[i], low[i - 1]], i < 6 ? "#241848" : "#1a1136");
    }
    sides += poly([pts[5], pts[6], low[6], low[5]], "#2a1d55");
    const glowPts = P(...pts);
    return `<ellipse cx="${iso(8, 6)[0].toFixed(1)}" cy="${(iso(8, 6)[1] + 14).toFixed(1)}" rx="170" ry="52" fill="#7c3aed" opacity=".16"/>
      ${[3, 9].map(y => `<polygon class="${reduce ? "" : "flick"}" points="${P([-0.7, y - 0.9, 0.5], [-0.7, y + 0.9, 0.5], [-5.6, y + 0.15, 0.5], [-5.6, y - 0.15, 0.5])}" fill="url(#flame)"/>
        <polygon points="${P([-0.7, y - 0.9, 0.5], [-0.7, y + 0.9, 0.5], [-2.2, y + 0.2, 0.5], [-2.2, y - 0.2, 0.5])}" fill="#fff" opacity=".85" filter="url(#glow)"/>`).join("")}
      ${sides}
      <polygon points="${glowPts}" fill="#2b1f58" stroke="#a78bfa" stroke-width="1.3" stroke-opacity=".9" filter="url(#glow)"/>
      ${poly([[16.2, 4.1, 0.02], [19.1, 6.5, 0.02], [16.2, 8.9, 0.02]], "#67e8f9", 'opacity=".22"')}
      <polyline points="${P([16.2, 4.1, 0.05], [19.1, 6.5, 0.05], [16.2, 8.9, 0.05])}" fill="none" stroke="#67e8f9" stroke-width="1.2" filter="url(#glow)"/>`;
  }
  function roomShell(r) {
    const col = r.team ? TEAM_COL[r.team] : r.kind === "tresor" ? "#fcd34d" : r.kind === "rat" ? "#a78bfa" : r.kind === "bank" ? "#9285b8" : "#67e8f9";
    const H = 1.25, {x0, y0, x1, y1} = r;
    return `<polygon data-room="${r.id}" points="${P([x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0])}" fill="#d8d0f4" style="cursor:pointer"/>
      <polygon points="${P([x0, y0, 0.01], [x1, y0, 0.01], [x1, y1, 0.01], [x0, y1, 0.01])}" fill="${col}" opacity=".13" pointer-events="none"/>
      ${poly([[x0, y0, 0], [x1, y0, 0], [x1, y0, H], [x0, y0, H]], "#b6a9ea", 'pointer-events="none"')}
      ${poly([[x0, y0, 0], [x0, y1, 0], [x0, y1, H], [x0, y0, H]], "#9d8fdc", 'pointer-events="none"')}
      <polyline points="${P([x0, y1, 0.02], [x1, y1, 0.02], [x1, y0, 0.02])}" fill="none" stroke="${col}" stroke-width="1.1" opacity=".9" pointer-events="none"/>
      <polyline points="${P([x0, y1, H], [x0, y0, H], [x1, y0, H])}" fill="none" stroke="#ede9fe" stroke-width=".8" opacity=".8" pointer-events="none"/>`;
  }
  function desk(x, y, glow) {
    const [sx, sy] = iso(x + 0.05, y - 0.05, 0.95);
    return box(x - 0.4, y - 0.28, 0, 0.8, 0.56, 0.42, "#4c3d8f", "#3a2e70", "#2d2459")
      + `<rect x="${(sx - 5.5).toFixed(1)}" y="${(sy - 4).toFixed(1)}" width="11" height="7" rx="1.2" fill="${glow || "#5b4aa8"}" ${glow ? `class="vglow" filter="url(#glow)"` : ""}/>`;
  }
  function props(r, data) {
    const {x0, y0, x1, y1} = r, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    if (r.kind === "test") {   // drei Testkapseln = Schatten-Varianten A, B, C
      return ["A", "B", "C"].map((l, i) => { const [px, py] = iso(x0 + 1 + i * 1.3, y0 + 1.6, 0);
        return `<g transform="translate(${px.toFixed(1)},${py.toFixed(1)})"><ellipse rx="6" ry="3" fill="#2d2459"/><rect x="-5" y="-17" width="10" height="17" fill="#67e8f9" opacity=".35"/>
          <rect x="-5" y="-17" width="10" height="17" fill="none" stroke="#a5f3fc" stroke-width=".7"/><ellipse cy="-17" rx="5" ry="2.5" fill="#cffafe" ${reduce ? "" : `class="vglow" style="animation-delay:${i * .4}s"`}/>
          <text y="-6" text-anchor="middle" font-size="6.5" font-weight="700" fill="#0b0618" font-family="${MONO}">${l}</text></g>`; }).join("");
    }
    if (r.kind === "rat") {    // runder Tisch mit Hologramm
      const [tx, ty] = iso(cx, cy + 0.2, 0);
      const seats = ["#ffb020", "#5aa2ff", "#2fd39a", "#c084fc", "#67e8f9", "#fb7185"].map((c, i) => {
        const a = Math.PI * (0.95 + i * 0.22), sx = tx + Math.cos(a) * 19, sy = ty + Math.sin(a) * 9.5 - 1;
        return `<circle cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="2.6" fill="${c}"/>`; }).join("");
      return `<g transform="translate(${tx.toFixed(1)},${ty.toFixed(1)})"><ellipse rx="15" ry="7.5" fill="#2d2459" stroke="#a78bfa" stroke-width="1"/>
        <ellipse cy="-1" rx="13" ry="6.2" fill="#1c1640"/><ellipse cy="-12" rx="9" ry="13" fill="url(#holo)" opacity=".75"/>
        <ellipse cy="-9" rx="8" ry="3.5" fill="none" stroke="#a5f3fc" stroke-width=".8" stroke-dasharray="3 2" ${reduce ? "" : 'class="spin"'}/></g>${seats}`;
    }
    if (r.kind === "tresor") {
      const [vx, vy] = iso(x0 + 0.05, cy, 0.7), [gx, gy] = iso(cx + 0.7, cy + 0.6, 0);
      return `<g transform="translate(${vx.toFixed(1)},${vy.toFixed(1)}) skewY(30) scale(.62,1)"><circle r="8.5" fill="#57534e" stroke="#fcd34d" stroke-width="1.4"/><circle r="4" fill="none" stroke="#fcd34d" stroke-width="1"/>
        <path d="M-6 0h12M0-6v12" stroke="#fcd34d" stroke-width=".8"/></g>
        <g transform="translate(${gx.toFixed(1)},${gy.toFixed(1)})">${[0, 1, 2, 3].map(i => `<ellipse cy="${-i * 3}" rx="9" ry="4" fill="#fbbf24" stroke="#92400e" stroke-width=".6"/>`).join("")}
          ${[0, 1].map(i => `<ellipse cx="13" cy="${2 - i * 3}" rx="6" ry="2.8" fill="#fcd34d" stroke="#92400e" stroke-width=".6"/>`).join("")}</g>`;
    }
    if (r.kind === "bank") return box(x0 + 0.7, y1 - 1.5, 0, 3.1, 0.55, 0.35, "#6b5fa3", "#544888", "#45396f");
    if (r.team === "makro") {
      const [bx, by] = iso(x0 + 0.05, cy - 0.3, 0.75);
      return `<g transform="translate(${bx.toFixed(1)},${by.toFixed(1)}) skewY(30) scale(.62,1)"><rect x="-10" y="-6" width="20" height="12" rx="1.5" fill="#1c1640"/>
        ${[[-6, -2], [-2, 1], [3, -1], [6, 2], [0, -3]].map(([a, b]) => `<circle cx="${a}" cy="${b}" r="1.1" fill="#fbbf24"/>`).join("")}</g>
        <circle cx="${iso(x1 - 0.6, y0 + 0.6, 1.6)[0].toFixed(1)}" cy="${iso(x1 - 0.6, y0 + 0.6, 1.6)[1].toFixed(1)}" r="3" fill="#ef4444" ${reduce ? "" : 'class="vglow"'} filter="url(#glow)"/>`;
    }
    if (r.team === "meme") {
      return [0, 1, 2].map(i => { const [fx, fy] = iso(x1 - 0.7, y0 + 0.8 + i * 0.9, 0.42);
        return `<g transform="translate(${fx.toFixed(1)},${fy.toFixed(1)})"><path d="M-2 -7h4v3l3 6h-10l3-6z" fill="#86efac" opacity=".85"/><circle cy="-9" r="1" fill="#bbf7d0" ${reduce ? "" : `class="vglow" style="animation-delay:${i * .5}s"`}/></g>`; }).join("");
    }
    return "";
  }
  function robot(col, frac, off, bench) {
    const C = 2 * Math.PI * 6;
    const body = off || bench ? "#7c7398" : col;
    return `<g class="rb"><ellipse rx="5" ry="2.3" fill="#000" opacity=".3"/>
      <circle r="6" fill="none" stroke="#1b1236" stroke-opacity=".35" stroke-width="2" transform="scale(1 .5)"/>
      ${frac > 0 ? `<circle r="6" fill="none" stroke="${col}" stroke-width="2.2" stroke-dasharray="${(frac * C).toFixed(1)} ${C.toFixed(1)}" transform="scale(1 .5) rotate(90)" ${frac === 1 ? 'filter="url(#glow)"' : ""}/>` : ""}
      <g class="rbb"><rect x="-4.3" y="-11.5" width="8.6" height="8.6" rx="3" fill="${body}"/>
      <rect x="-3.8" y="-19" width="7.6" height="7" rx="2.7" fill="${off || bench ? "#a59cc4" : "#f5f3ff"}"/>
      <rect x="-2.8" y="-17.2" width="5.6" height="2.8" rx="1.3" fill="#1b1236"/>
      ${off || bench ? '<path d="M-2 -15.8h1.4M.6 -15.8h1.4" stroke="#8f86b0" stroke-width=".7"/>' : '<circle cx="-1.2" cy="-15.8" r=".8" fill="#67e8f9"/><circle cx="1.2" cy="-15.8" r=".8" fill="#67e8f9"/>'}
      <line x1="0" y1="-19" x2="0" y2="-21.6" stroke="${body}" stroke-width="1"/><circle cx="0" cy="-22.2" r="1.2" fill="${body}" ${off || bench ? "" : 'filter="url(#glow)"'}/>
      ${off || bench ? `<text x="5" y="-20" font-size="6" font-weight="700" fill="#c4b5fd" font-family="${SANS}">z</text>` : ""}</g>
      <g class="bub" opacity="0"></g></g>`;
  }
  function events(b) {
    const out = [], now = Date.now() / 1000;
    b.positions.forEach(p => out.push({txt: `${p.pair} ${pc(p.pnl_pct)}`, col: p.pnl_pct >= 0 ? "#4ade80" : "#fb7185"}));
    const t = b.trades[0];
    if (t && now - t.closed_t < 72 * 3600) out.push({txt: `${t.pair}: ${t.result} ${eurS(t.pnl)}`, col: t.pnl >= 0 ? "#4ade80" : "#fb7185"});
    const n = b.checks && b.checks.notes && b.checks.notes[0];
    if (n && now - n[0] < 6 * 3600) out.push({txt: n[1].length > 34 ? n[1].slice(0, 33) + "…" : n[1], col: "#a78bfa"});
    if (b.ladder && b.ladder.stage === "bank") out.push({txt: "Ersatzbank – Varianten üben", col: "#9285b8"});
    return out;
  }
  function roomOf(data, id) {
    const b = data.bots[id];
    if (b.ladder && b.ladder.stage === "bank") return "bank";
    return ROOMS.some(r => r.team === b.team) ? b.team : "krypto";
  }
  function roomPanel(data, rid) {
    const box = document.getElementById("roompanel");
    if (!box) return;
    if (!rid) {
      box.innerHTML = `<div class="vleg"><span><i class="dot" style="background:var(--acc)"></i>Ring = Stufe der Leiter (¼, ½, voll)</span>
        <span><i class="dot" style="background:var(--up)"></i>Bildschirm grün/rot = Position im Plus/Minus</span>
        <span>läuft herum = wartet auf ein Signal</span><span>Ersatzbank = pausiert durch den Decay-Check</span>
        <span style="color:var(--txt)">Raum antippen zum Hineinzoomen</span></div>`;
      return;
    }
    const r = ROOMS.find(x => x.id === rid), ids = Object.keys(data.bots).filter(id => roomOf(data, id) === rid);
    let body = "";
    if (r.kind === "tresor") {
      const P = data.pool;
      body = `<div class="row"><div class="l"><b>Sammelkonto</b><span>Start ${eur(P.start)} · nicht zugeteilt ${eur(P.unallocated)}</span></div>
        <div class="r"><b>${eur(P.equity)}</b><span class="${cls(P.pnl_pct)}">${pc(P.pnl_pct)}</span></div></div>`;
    } else if (r.kind === "test") {
      const ns = Object.values(data.bots).reduce((a, b) => a + b.learning.variants.reduce((x, v) => x + v.trades, 0), 0);
      body = `<div class="lbl">Hier üben je Bot drei Varianten (A, B, C) mit Schatten-Geld: ${ns.toLocaleString("de-DE")} Schatten-Trades bisher.
        Die beste übernimmt, wenn der Decay-Check einen Bot zurückstuft.</div>`;
    } else if (r.kind === "rat") {
      const C = data.council && data.council.recent && data.council.recent[0];
      body = `<div class="lbl">Hier stimmt der Rat über jeden Kauf ab.${C ? ` Zuletzt: ${esc(C.pair)} (${esc(C.bot)}) – ${C.m > 0 ? "gekauft mit Risiko ×" + num2(C.m) : "abgelehnt"}.` : ""}</div>
        <button class="btn sec" data-sub="rat">Zum Rat</button>`;
    } else {
      body = ids.length ? ids.map(id => botRow(id)).join("") : `<div class="empty">${r.kind === "bank" ? "Niemand auf der Ersatzbank – alle Bots handeln." : "Kein Bot in diesem Raum"}</div>`;
    }
    const name = r.name || teamName(data, r.team);
    box.innerHTML = `<div style="padding:12px 16px 16px"><div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:6px">
      <b style="font-size:16px">${esc(name)}</b><span class="lbl">${ids.length ? ids.length + (ids.length === 1 ? " Bot" : " Bots") : ""}</span></div>${body}</div>`;
  }
  function mountSchiff(el, data) {
    const svg = el.querySelector("svg"), B = data.bots, pop = el.querySelector(".room-pop");
    const rnd = seeded(5);
    const byRoom = {};
    Object.keys(B).forEach(id => (byRoom[roomOf(data, id)] = byRoom[roomOf(data, id)] || []).push(id));
    const actors = [], crews = [];
    let html = shipBackdrop() + hull(), labels = "";
    const order = [...ROOMS].sort((p, q) => (p.x0 + p.y0) - (q.x0 + q.y0));
    order.forEach(r => {
      const ids = byRoom[r.id] || [];
      let stat = "";
      const W = r.x1 - r.x0, D = r.y1 - r.y0;
      if (r.team || r.kind === "bank") {
        const cols = Math.min(4, Math.max(1, ids.length)), rows = Math.ceil(ids.length / cols);
        const deskY = i => r.y0 + 1.05 + Math.floor(i / cols) * Math.min(1.5, (D - 1.6) / Math.max(1, rows - 0.4));
        const ya = Math.max(r.y0 + D * 0.55, deskY(ids.length - 1) + 0.75);
        const crew = {list: [], max: ids.length >= 4 ? 2 : 1, t: rnd() * 2, walk: [r.x0 + 0.5, r.x1 - 0.5, ya, r.y1 - 0.3]};
        if (r.team) crews.push(crew);
        ids.forEach((id, i) => {
          const b = B[id], bench = r.kind === "bank";
          const cx = r.x0 + (i % cols + 0.5) * W / cols, cy = bench ? r.y1 - 1.0 : deskY(i);
          const holding = b.positions.length > 0, pnl = b.positions.reduce((a, p) => a + p.pnl_pct, 0);
          if (!bench) stat += `<g data-depth="${(cx + cy).toFixed(2)}">${desk(cx, cy, holding ? (pnl >= 0 ? "#4ade80" : "#fb7185") : null)}</g>`;
          const L = b.ladder || {stage: "voll"};
          const a = {id, b, room: r, col: TEAM_COL[b.team] || "#a78bfa", frac: STAGE_F[L.stage] ?? 1, off: !b.enabled, bench, holding,
                     home: [cx + 0.05, cy + (bench ? 0.2 : 0.62)], pos: [cx + 0.05, cy + (bench ? 0.2 : 0.62)], goal: null,
                     phase: "home", ev: events(b), name: b.name};
          actors.push(a); crew.list.push(a);
        });
      }
      const [lx, ly] = iso((r.x0 + r.x1) / 2, r.y0 + 0.15, 2.15);
      const col = r.team ? TEAM_COL[r.team] : r.kind === "tresor" ? "#fcd34d" : r.kind === "bank" ? "#9285b8" : r.kind === "rat" ? "#a78bfa" : "#67e8f9";
      const txt = r.kind === "tresor" ? `${r.short} ${eur(data.pool.equity).replace(/,\d\d\s/, " ")}` : r.short + (ids.length ? " " + ids.length : "");
      const w = txt.length * 5.1 + 16;
      labels += `<g class="rlab" data-room="${r.id}" transform="translate(${lx.toFixed(1)},${ly.toFixed(1)})" style="cursor:pointer">
        <rect x="${(-w / 2).toFixed(1)}" y="-7.5" width="${w.toFixed(1)}" height="15" rx="7.5" fill="#130c27" fill-opacity=".9" stroke="${col}" stroke-width="1"/>
        <circle cx="${(-w / 2 + 8).toFixed(1)}" cy="0" r="2.4" fill="${col}"/>
        <text x="${(-w / 2 + 13).toFixed(1)}" y="3.3" font-size="9" font-weight="600" fill="#f1ecff" font-family="${SANS}">${esc(txt)}</text></g>`;
      html += `<g class="room" data-rid="${r.id}">${roomShell(r)}<g pointer-events="none">${props(r, data)}</g><g class="stage">${stat}</g></g>`;
    });
    svg.innerHTML = html + `<g class="names">${actors.map(a => `<text class="rn" data-n="${a.id}" y="8" text-anchor="middle" font-size="4.2" font-weight="600" fill="#f5f3ff"
      paint-order="stroke" stroke="#130c27" stroke-width="1.2" font-family="${SANS}">${esc(a.name)}</text>`).join("")}</g><g class="labels">${labels}</g>`;
    // Roboter in die Bühne ihres Raums setzen
    actors.forEach(a => {
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("class", "act");
      g.dataset.id = a.id;
      g.innerHTML = robot(a.col, a.frac, a.off, a.bench);
      svg.querySelector(`.room[data-rid="${a.room.id}"] .stage`).appendChild(g);
      a.node = g; a.bub = g.querySelector(".bub"); a.rn = svg.querySelector(`.names [data-n="${a.id}"]`);
    });
    const stages = [...svg.querySelectorAll(".stage")];
    const place = (a, t) => {
      const [x, y] = iso(a.pos[0], a.pos[1], 0);
      const bob = a.off || a.bench || reduce ? 0 : Math.sin(t * 5 + a.home[0] * 3) * (a.goal ? 1.1 : 0.4);
      a.node.setAttribute("transform", `translate(${x.toFixed(1)},${(y + bob).toFixed(1)})`);
      if (focusRoom === a.room.id) a.rn.setAttribute("transform", `translate(${x.toFixed(1)},${y.toFixed(1)})`);
      a.node.dataset.depth = (a.pos[0] + a.pos[1]).toFixed(2);
    };
    const sortStages = () => stages.forEach(s => [...s.children].sort((p, q) => p.dataset.depth - q.dataset.depth).forEach(n => s.appendChild(n)));
    const declutter = () => {   // im Zoom: Namen, die sich überdecken würden, kurz ausblenden (vorne gewinnt)
      const shown = [];
      actors.filter(a => a.room.id === focusRoom).sort((p, q) => (q.pos[0] + q.pos[1]) - (p.pos[0] + p.pos[1])).forEach(a => {
        const [x, y] = iso(a.pos[0], a.pos[1], 0), w = a.name.length * 2.3 + 3;
        const hit = shown.some(o => Math.abs(o.x - x) * 2 < o.w + w && Math.abs(o.y - y) < 5.5);
        a.rn.style.visibility = hit ? "hidden" : "";
        if (!hit) shown.push({x, y, w});
      });
    };
    // Sprechblasen mit echten Ereignissen (offene Positionen, letzter Trade, Prüfprotokoll)
    let evi = 0;
    const speakers = () => actors.filter(a => a.ev.length && (!focusRoom || a.room.id === focusRoom));
    const say = () => {
      const list = speakers();
      if (!list.length) return;
      const a = list[evi % list.length], e = a.ev[Math.floor(evi / list.length) % a.ev.length];
      evi++;
      const v = to || vb, k = Math.sqrt(VW / v[2]), sc = 1.15 / k, w = Math.min(150, e.txt.length * 4.4 + 12);
      const ax = iso(a.pos[0], a.pos[1])[0], lo = (v[0] + 4 - ax) / sc, hi = (v[0] + v[2] - 4 - ax) / sc;
      const bx = Math.max(lo + w / 2, Math.min(hi - w / 2, 0));
      a.bub.innerHTML = `<g transform="translate(0,${(-24 - 10 * sc).toFixed(1)}) scale(${sc.toFixed(3)})"><rect x="${(bx - w / 2).toFixed(1)}" y="-8" width="${w.toFixed(1)}" height="13" rx="6.5" fill="#130c27" fill-opacity=".94" stroke="${e.col}" stroke-width=".9"/>
        <path d="M-3 5l3 4 3-4z" fill="#130c27" stroke="${e.col}" stroke-width=".9"/><rect x="-3.6" y="3.6" width="7.2" height="1.8" fill="#130c27"/>
        <text x="${bx.toFixed(1)}" y="1.3" text-anchor="middle" font-size="7.6" font-weight="600" fill="#f1ecff" font-family="${SANS}">${esc(e.txt)}</text></g>`;
      a.bub.style.transition = "opacity .3s"; a.bub.setAttribute("opacity", "1");
      a.node.parentNode.appendChild(a.node);
      setTimeout(() => a.bub.setAttribute("opacity", "0"), 3200);
    };
    // Kamera: Raum antippen -> hineinzoomen
    const base = [0, 0, VW, VH];
    let vb = [...base], from = null, to = null, t0 = 0;
    const roomBox = r => {
      const pts = [[r.x0, r.y0, 2.3], [r.x1, r.y0, 0], [r.x1, r.y1, 0], [r.x0, r.y1, 0], [r.x0, r.y0, 0]].map(p => iso(...p));
      let x0 = Math.min(...pts.map(p => p[0])) - 4, x1 = Math.max(...pts.map(p => p[0])) + 4;
      let y0 = Math.min(...pts.map(p => p[1])) - 12, y1 = Math.max(...pts.map(p => p[1])) + 7;
      let w = x1 - x0, h = y1 - y0;
      if (w / h < VW / VH) { const nw = h * VW / VH; x0 -= (nw - w) / 2; w = nw; } else { const nh = w * VH / VW; y0 -= (nh - h) / 2; h = nh; }
      return [x0, y0, w, h];
    };
    const setVB = v => svg.setAttribute("viewBox", v.map(n => n.toFixed(1)).join(" "));
    const zoom = rid => {
      focusRoom = rid;
      from = [...vb]; to = rid ? roomBox(ROOMS.find(r => r.id === rid)) : [...base]; t0 = performance.now();
      if (reduce) { vb = to; setVB(vb); to = null; }
      svg.classList.toggle("zoomed", !!rid);
      svg.querySelectorAll(".room").forEach(g => g.classList.toggle("dim", !!rid && g.dataset.rid !== rid));
      pop.style.display = rid ? "block" : "none";
      actors.forEach(a => {
        const mine = !!rid && a.room.id === rid;
        if (mine) a.node.dataset.bot = a.rn.dataset.bot = a.id; else { delete a.node.dataset.bot; delete a.rn.dataset.bot; }
        a.rn.style.display = mine ? "inline" : "none";
        if (mine) { const [x, y] = iso(a.pos[0], a.pos[1], 0); a.rn.setAttribute("transform", `translate(${x.toFixed(1)},${y.toFixed(1)})`); }
      });
      roomPanel(data, rid);
      if (rid) declutter();
    };
    on(svg, "click", e => {
      if (e.target.closest("[data-bot]")) return;   // Roboter im Zoom -> Bot-Details (index.html)
      const r = e.target.closest("[data-room],[data-rid]"), rid = r && (r.dataset.room || r.dataset.rid);
      if (rid && rid !== focusRoom) zoom(rid);   // im Zoom führt nur „Ganzes Schiff“ zurück
    });
    on(pop, "click", e => { if (e.target.closest("[data-ship]")) zoom(null); });
    if (focusRoom && !ROOMS.some(r => r.id === focusRoom)) focusRoom = null;
    zoom(focusRoom);
    if (focusRoom) { vb = roomBox(ROOMS.find(r => r.id === focusRoom)); setVB(vb); to = null; }
    if (!reduce) { say(); every(3600, say); }
    let frame = 0;
    loop((t, dt) => {
      if (to) {
        const k = Math.min(1, (performance.now() - t0) / 650), e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
        vb = from.map((v, i) => v + (to[i] - v) * e); setVB(vb);
        if (k >= 1) to = null;
      }
      if (!reduce) crews.forEach(R => {   // je Raum drehen höchstens 1–2 wartende Bots eine Runde und gehen zurück an den Tisch
        R.t -= dt;
        const idle = R.list.filter(a => a.phase === "home" && !a.off && !a.holding);
        if (R.t <= 0 && R.list.filter(a => a.phase !== "home").length < R.max && idle.length) {
          const a = idle[Math.floor(Math.random() * idle.length)], [xa, xb, y0, y1] = R.walk;
          a.goal = [xa + Math.random() * (xb - xa), y0 + Math.random() * (y1 - y0)]; a.phase = "out";
          R.t = 1.2 + Math.random() * 2.5;
        }
      });
      actors.forEach(a => {
        if (a.phase === "pause" && (a.wait -= dt) <= 0) { a.goal = a.home; a.phase = "back"; }
        if (a.goal) {
          const vx = a.goal[0] - a.pos[0], vy = a.goal[1] - a.pos[1], d = Math.hypot(vx, vy), sp = 0.75 * dt;
          if (d < sp) { a.pos = a.goal; a.goal = null; if (a.phase === "out") { a.phase = "pause"; a.wait = 1 + Math.random() * 2; } else a.phase = "home"; }
          else a.pos = [a.pos[0] + vx / d * sp, a.pos[1] + vy / d * sp];
        }
        place(a, t);
      });
      if (frame++ % 8 === 0) { sortStages(); if (focusRoom) declutter(); }
    });
    on(svg, "pointermove", e => {
      const g = e.target.closest(".act"), box = el.getBoundingClientRect();
      if (!g) return tip(el, null);
      const b = B[g.dataset.id], L = b.ladder;
      tip(el, `<b>${esc(b.name)}</b><span>${esc(b.style)} · ${b.enabled ? pc(b.pnl_pct) : "aus"} · ${b.positions.length} offen</span>
        ${L ? `<span>Leiter: ${esc(L.name)} (${L.share === "1" ? "volles" : L.share} Risiko) · ${esc(L.health_text)}</span>` : ""}`, e.clientX - box.left, e.clientY - box.top);
    });
    on(svg, "pointerleave", () => tip(el, null));
  }

  // --- 2) Orbit: offene Trades als Planeten zwischen Stop (außen) und Ziel (innen), Signale als Kometen --
  function viewOrbit(data) {
    const all = [];
    for (const [id, b] of Object.entries(data.bots)) b.positions.forEach(p => all.push({...p, bot: b.name, id, team: b.team}));
    all.sort((a, b) => b.progress - a.progress);
    return `<div class="card scene">${sceneHead(data, "Orbit · offene Trades und die letzten Entscheidungen")}
      <div id="viz" class="vbox"><canvas class="vcan" style="height:380px"></canvas><div class="vtip"></div></div>
      <div class="vleg"><span><i class="dot" style="background:var(--up)"></i>Planet im Plus</span><span><i class="dot" style="background:var(--down)"></i>im Minus</span>
      <span>innen = nah am Ziel · außen = nah am Stop</span><span>Komet = Entscheidung des Rats (grün gekauft, rot abgelehnt)</span></div></div>
      <h2>Offene Trades <small>${all.length}</small></h2><div class="card">${all.length ? all.map(p => `
        <div class="row"><div class="l"><b>${esc(p.pair)}</b><span>${esc(p.bot)} · ${p.progress != null ? Math.round(p.progress * 100) + " % zum Ziel" : ""}</span></div>
        <div class="r"><b class="${cls(p.pnl_pct)}">${pc(p.pnl_pct)}</b><span>${eur(p.value)}</span></div></div>`).join("")
        : '<div class="empty">Gerade keine offenen Trades</div>'}</div>`;
  }
  function canvasFit(cv) {
    const r = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
    cv.width = w * r; cv.height = h * r;
    const g = cv.getContext("2d"); g.setTransform(r, 0, 0, r, 0, 0);
    return [g, w, h, r];
  }
  function starLayer(W, H, r, seed, n) {
    const off = document.createElement("canvas"); off.width = W * r; off.height = H * r;
    const g = off.getContext("2d"); g.setTransform(r, 0, 0, r, 0, 0);
    g.fillStyle = "#0a0618"; g.fillRect(0, 0, W, H);
    [[W * 0.85, H * 0.1, W * 0.6, "#7c3aed59"], [W * 0.1, H * 0.85, W * 0.55, "#c026d340"], [W * 0.5, H * 0.5, W * 0.45, "#1e3a8a40"]].forEach(([x, y, rad, c]) => {
      const gr = g.createRadialGradient(x, y, 0, x, y, rad); gr.addColorStop(0, c); gr.addColorStop(1, "#00000000");
      g.fillStyle = gr; g.fillRect(0, 0, W, H);
    });
    const rnd = seeded(seed);
    for (let i = 0; i < n; i++) {
      g.globalAlpha = 0.3 + rnd() * 0.6; g.fillStyle = rnd() > 0.8 ? "#c4b5fd" : "#fff";
      g.beginPath(); g.arc(rnd() * W, rnd() * H, rnd() > 0.93 ? 1.2 : 0.5 + rnd() * 0.4, 0, Math.PI * 2); g.fill();
    }
    g.globalAlpha = 1;
    return off;
  }
  function mountOrbit(el, data) {
    const cv = el.querySelector("canvas"), [g, W, H, dpr] = canvasFit(cv);
    const cx = W / 2, cy = H / 2 + 4, R1 = Math.min(W, H) / 2 - 44, R0 = R1 * 0.34;
    const bg = starLayer(W, H, dpr, 9, Math.round(W * H / 900));
    const teams = Object.keys(data.teams || {}).filter(t => data.teams[t].members.length);
    const span = Math.PI * 2 / Math.max(1, teams.length), a0 = tid => teams.indexOf(tid) * span - Math.PI / 2;
    const per = {};
    for (const b of Object.values(data.bots)) b.positions.forEach(p => (per[b.team] = per[b.team] || []).push({...p, bot: b.name}));
    const planets = [];
    teams.forEach(tid => (per[tid] || []).forEach((p, i, list) => planets.push({p, tid, a: a0(tid) + span * (i + 0.5) / list.length,
      r: R1 - (p.progress ?? 0.5) * (R1 - R0), size: 4 + Math.min(8, Math.sqrt(Math.max(p.value, 1)) / 3.2)})));
    const byName = Object.fromEntries(Object.values(data.bots).map(b => [b.name, b.team]));
    const recent = ((data.council && data.council.recent) || []).filter(c => teams.includes(byName[c.bot]));
    const comets = [];
    let ci = 0;
    const spawn = () => {
      if (!recent.length) return;
      const c = recent[ci++ % recent.length], tid = byName[c.bot];
      const a = a0(tid) + span * (0.2 + Math.random() * 0.6), bend = (Math.random() - 0.5) * 0.9;
      comets.push({c, a, bend, t: 0, ok: c.m > 0});
    };
    if (!reduce) { spawn(); every(1700, spawn); }
    const pool = data.pool, pnl = pool.equity - pool.start;
    let hover = null;
    const draw = (t, dt) => {
      g.drawImage(bg, 0, 0, W, H);
      const placed = [{x: cx, y: cy + 21, w: 108, h: 32}];   // freie Plätze für Beschriftungen
      const free = (x, y, w, h, self) => x - w / 2 >= 2 && x + w / 2 <= W - 2 && y - h / 2 >= 2 && y + h / 2 <= H - 2
        && !placed.some(q => q.o !== self && Math.abs(q.x - x) * 2 < q.w + w + 4 && Math.abs(q.y - y) * 2 < q.h + h + 2);
      // Radar-Sweep
      if (!reduce && g.createConicGradient) {
        const sw = g.createConicGradient(t * 0.5, cx, cy);
        sw.addColorStop(0, "#67e8f900"); sw.addColorStop(0.8, "#67e8f900"); sw.addColorStop(1, "#67e8f926");
        g.fillStyle = sw; g.beginPath(); g.arc(cx, cy, R1, 0, Math.PI * 2); g.fill();
      }
      for (let k = 0; k <= 3; k++) {   // Umlaufbahnen
        const r = R0 + (R1 - R0) * k / 3;
        g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2);
        g.strokeStyle = k === 3 ? "#fb718566" : k === 0 ? "#4ade8066" : "#67e8f92e"; g.lineWidth = k % 3 ? 1 : 1.4; g.stroke();
      }
      g.font = `600 9px ${SANS}`; g.textAlign = "center"; g.fillStyle = "#fb7185"; g.fillText("Stop", cx, cy - R1 + 11);
      g.fillStyle = "#4ade80"; g.fillText("Ziel", cx, cy - R0 + 11);
      const tags = [];
      teams.forEach(tid => {   // Sektoren je Team als leuchtende Bögen
        const s = a0(tid), e = s + span, col = TEAM_COL[tid] || "#a78bfa";
        g.save(); g.shadowColor = col; g.shadowBlur = 10;
        g.beginPath(); g.arc(cx, cy, R1 + 12, s + 0.05, e - 0.05); g.strokeStyle = col; g.lineWidth = 4; g.lineCap = "round"; g.stroke(); g.restore();
        g.strokeStyle = "#ffffff12"; g.lineWidth = 1; g.beginPath(); g.moveTo(cx + Math.cos(s) * R0, cy + Math.sin(s) * R0); g.lineTo(cx + Math.cos(s) * R1, cy + Math.sin(s) * R1); g.stroke();
        const am = s + span / 2, label = teamName(data, tid);
        g.font = `600 10px ${SANS}`;
        const tw = g.measureText(label).width + 12, lx = Math.max(tw / 2 + 2, Math.min(W - tw / 2 - 2, cx + Math.cos(am) * (R1 + 28)));
        tags.push({label, col, x: lx, y: cy + Math.sin(am) * (R1 + 28), w: tw});
        placed.push({x: lx, y: cy + Math.sin(am) * (R1 + 28), w: tw, h: 16});
      });
      // Kern: leuchtende Sonne mit dem Gesamtergebnis
      const pulse = reduce ? 1 : 1 + Math.sin(t * 1.6) * 0.04, cr = R0 * 0.92 * pulse;
      const sun = g.createRadialGradient(cx, cy, 0, cx, cy, cr * 1.6);
      sun.addColorStop(0, "#ffffff"); sun.addColorStop(0.22, "#dbeafe"); sun.addColorStop(0.5, "#60a5fa99"); sun.addColorStop(1, "#3b82f600");
      g.fillStyle = sun; g.beginPath(); g.arc(cx, cy, cr * 1.6, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#130c27e0"; const bw = 104; g.beginPath(); g.roundRect ? g.roundRect(cx - bw / 2, cy + 6, bw, 30, 9) : g.rect(cx - bw / 2, cy + 6, bw, 30); g.fill();
      g.fillStyle = "#ab9fcd"; g.font = `500 9px ${SANS}`; g.fillText("Gesamt", cx, cy + 17);
      g.font = `700 12px ${MONO}`; g.fillStyle = pnl >= 0 ? "#4ade80" : "#fb7185"; g.fillText(eurS(pnl), cx, cy + 31);
      // Planeten
      planets.forEach(o => {
        const drift = reduce ? 0 : Math.sin(t * 0.22 + o.r) * span * 0.16;
        o.x = cx + Math.cos(o.a + drift) * o.r; o.y = cy + Math.sin(o.a + drift) * o.r;
        const col = o.p.pnl_pct >= 0 ? "#4ade80" : "#fb7185";
        g.save(); g.shadowColor = col; g.shadowBlur = 16;
        const pg = g.createRadialGradient(o.x - o.size * 0.35, o.y - o.size * 0.35, 0, o.x, o.y, o.size);
        pg.addColorStop(0, "#ffffff"); pg.addColorStop(0.35, col); pg.addColorStop(1, o.p.pnl_pct >= 0 ? "#14532d" : "#881337");
        g.fillStyle = pg; g.beginPath(); g.arc(o.x, o.y, o.size, 0, Math.PI * 2); g.fill(); g.restore();
        if (o === hover) { g.beginPath(); g.arc(o.x, o.y, o.size + 4, 0, Math.PI * 2); g.strokeStyle = "#f1ecff"; g.lineWidth = 1.5; g.stroke(); }
        placed.push({x: o.x, y: o.y, w: o.size * 2, h: o.size * 2, o});
      });
      // Beschriftung über oder unter dem Planeten, wo Platz ist – sonst keine (antippen zeigt alles)
      if (planets.length <= 14) planets.forEach(o => {
        const txt = `${o.p.pair} ${pc(o.p.pnl_pct)}`;
        g.font = `600 9.5px ${SANS}`;
        const tw = g.measureText(txt).width + 10, dys = [-(o.size + 9), o.size + 10, -(o.size + 24), o.size + 25];
        for (const k of o.slot == null ? [0, 1, 2, 3] : [o.slot, 0, 1, 2, 3]) {
          const tx = Math.max(tw / 2 + 2, Math.min(W - tw / 2 - 2, o.x)), ty = o.y + dys[k];
          if (!free(tx, ty, tw, 14, o)) continue;
          o.slot = k; placed.push({x: tx, y: ty, w: tw, h: 14});
          g.fillStyle = "#130c27d9"; g.beginPath(); g.roundRect ? g.roundRect(tx - tw / 2, ty - 7, tw, 14, 7) : g.rect(tx - tw / 2, ty - 7, tw, 14); g.fill();
          g.fillStyle = "#f1ecff"; g.fillText(txt, tx, ty + 3.5);
          return;
        }
        o.slot = null;
      });
      if (!planets.length) { g.fillStyle = "#ab9fcd"; g.font = `500 11px ${SANS}`; g.fillText("keine offenen Trades", cx, cy + R0 + 26); }
      tags.forEach(o => {   // Team-Namen zuletzt, damit kein Planet sie verdeckt
        g.font = `600 10px ${SANS}`; g.fillStyle = "#0a0618e0"; g.beginPath();
        g.roundRect ? g.roundRect(o.x - o.w / 2, o.y - 8, o.w, 16, 8) : g.rect(o.x - o.w / 2, o.y - 8, o.w, 16); g.fill();
        g.strokeStyle = o.col + "99"; g.lineWidth = 1; g.stroke();
        g.fillStyle = "#f1ecff"; g.fillText(o.label, o.x, o.y + 3.5);
      });
      // Kometen: fliegen von außen auf die Stop-Bahn ihres Teams zu
      for (let i = comets.length - 1; i >= 0; i--) {
        const k = comets[i];
        k.t += dt / 1.9;
        if (k.t > 1.6) { comets.splice(i, 1); continue; }
        const col = k.ok ? "#4ade80" : "#fb7185";
        const pos = u => { const rr = R1 + 90 - (90 + (k.ok ? 4 : -6)) * Math.min(1, u), aa = k.a + k.bend * (1 - Math.min(1, u)); return [cx + Math.cos(aa) * rr, cy + Math.sin(aa) * rr]; };
        if (k.t <= 1) {
          const [hx, hy] = pos(k.t), [sx, sy] = pos(Math.max(0, k.t - 0.28));
          const tail = g.createLinearGradient(sx, sy, hx, hy); tail.addColorStop(0, col + "00"); tail.addColorStop(1, col);
          g.strokeStyle = tail; g.lineWidth = 2.4; g.lineCap = "round"; g.beginPath(); g.moveTo(sx, sy); g.lineTo(hx, hy); g.stroke();
          g.save(); g.shadowColor = col; g.shadowBlur = 12; g.fillStyle = "#fff"; g.beginPath(); g.arc(hx, hy, 2.4, 0, Math.PI * 2); g.fill(); g.restore();
        } else {
          const [hx, hy] = pos(1), f = (k.t - 1) / 0.6;
          g.globalAlpha = 1 - f; g.strokeStyle = col; g.lineWidth = 1.5; g.beginPath(); g.arc(hx, hy, 3 + f * 14, 0, Math.PI * 2); g.stroke();
          g.font = `600 9.5px ${SANS}`; g.fillStyle = col;
          g.fillText(`${k.c.pair} ${k.ok ? "Kauf ×" + num2(k.c.m) : "abgelehnt"}`, Math.max(50, Math.min(W - 50, hx)), hy - 12 - f * 6);
          g.globalAlpha = 1;
        }
      }
    };
    loop(draw);
    const pick = e => {
      const b = cv.getBoundingClientRect(), x = e.clientX - b.left, y = e.clientY - b.top;
      let best = null, bd = 24;
      planets.forEach(o => { const d = Math.hypot(o.x - x, o.y - y); if (d < bd) { bd = d; best = o; } });
      hover = best;
      if (reduce) draw(0, 0);
      if (!best) return tip(el, null);
      const p = best.p;
      tip(el, `<b>${esc(pc(p.pnl_pct))} · ${esc(p.pair)}</b><span>${esc(p.bot)} · ${Math.round((p.progress ?? 0) * 100)} % zum Ziel</span>
        <span>Kauf ${px(p.entry)} · jetzt ${px(p.price)} · Stop ${px(p.stop)}</span>`, x, y);
    };
    on(cv, "pointermove", pick); on(cv, "pointerdown", pick); on(cv, "pointerleave", () => { hover = null; tip(el, null); });
  }

  // --- 3) Rat: sechs Figuren stimmen am runden Tisch über jeden Kauf ab -----------------------------
  const MEMB = {analyst: "#ffb020", news: "#5aa2ff", trend: "#2fd39a", muster: "#c084fc", kollegen: "#67e8f9", risiko: "#fb7185"};
  let ratPick = 0, ratAuto = true;
  const vote = f => f == null ? ["–", "nicht gefragt", "#6b6290"] : f <= 0 ? ["NEIN", "Nein", "#fb7185"]
    : f < 1 ? ["HM", "Bedenken", "#fbbf24"] : [f > 1 ? "JA!" : "JA", f > 1 ? "Klares Ja" : "Ja", "#4ade80"];
  function quote(id, f, reason) {   // was jedes Mitglied sagt – direkt aus seiner Stimme abgeleitet
    if (f == null) return null;
    if (f <= 0) return reason || {analyst: "Marktlage passt nicht", news: "Nachrichten-Sperre", kollegen: "Kollege hatte hier Stop-Loss", risiko: "Zu viel Risiko"}[id] || "Nein";
    const Q = {analyst: ["Markt schwach – weniger Risiko", "Markt passt", "Markt passt"], news: ["Unruhige Nachrichtenlage", "Nachrichten ruhig", "Nachrichten ruhig"],
               trend: ["Großer Trend dagegen", "Großer Trend passt", "Großer Trend passt"], muster: ["Warnmuster im Chart", "Keine Auffälligkeit", "Gelerntes Muster bestätigt"],
               kollegen: ["Bedenken", "Kein Einwand", "Kollege liegt hier im Plus"], risiko: ["Risiko knapp", "Risiko im Rahmen", "Risiko im Rahmen"]}[id];
    return Q ? Q[f < 1 ? 0 : f > 1 ? 2 : 1] : null;
  }
  function figure(id, col) {   // gezeichnete Figuren (kein Emoji), Füße bei 0,0
    const eyes = (y, dx = 4) => `<circle cx="${-dx}" cy="${y}" r="3.2" fill="#fff"/><circle cx="${dx}" cy="${y}" r="3.2" fill="#fff"/>
      <circle cx="${-dx + 0.8}" cy="${y + 0.6}" r="1.5" fill="#130c27"/><circle cx="${dx + 0.8}" cy="${y + 0.6}" r="1.5" fill="#130c27"/>`;
    const feet = `<ellipse cx="-5" cy="-1" rx="4" ry="2" fill="#130c27"/><ellipse cx="5" cy="-1" rx="4" ry="2" fill="#130c27"/>`;
    switch (id) {
      case "analyst": return `${feet}<circle cy="-17" r="15" fill="${col}"/><circle cx="-5" cy="-21" r="5" fill="none" stroke="#130c27" stroke-width="1.6"/>
        <circle cx="5" cy="-21" r="5" fill="none" stroke="#130c27" stroke-width="1.6"/>${eyes(-21, 5)}<path d="M-8 -9l4-3 3 2 5-5" fill="none" stroke="#130c27" stroke-width="1.6" stroke-linecap="round"/>`;
      case "news": return `${feet}<rect x="-12" y="-38" width="24" height="36" rx="5" fill="${col}"/><path d="M0 -38v-6" stroke="${col}" stroke-width="2"/><circle cy="-45" r="2.2" fill="#fff"/>
        ${eyes(-28)}<path d="M-7 -17h14M-7 -13h14M-7 -9h9" stroke="#130c27" stroke-width="1.4" opacity=".7"/>`;
      case "trend": return `${feet}<path d="M0 -44L15 -2H-15z" fill="${col}"/>${eyes(-18, 4.2)}<path d="M-6 -8l5-4 4 2 5-5" fill="none" stroke="#130c27" stroke-width="1.6" stroke-linecap="round"/>
        <path d="M0 -44l-3 -6h6z" fill="#fff"/>`;
      case "muster": return `${feet}<circle cy="-18" r="16" fill="${col}"/><circle cy="-21" r="7" fill="#fff"/><circle cx="1" cy="-20" r="3.4" fill="#130c27"/>
        <circle cx="13" cy="-8" r="5" fill="none" stroke="#fff" stroke-width="1.8"/><path d="M16 -4l4 4" stroke="#fff" stroke-width="2" stroke-linecap="round"/>`;
      case "kollegen": return `${feet}<rect x="-14" y="-24" width="28" height="22" rx="8" fill="${col}"/><circle cx="-7" cy="-30" r="8" fill="${col}"/><circle cx="7" cy="-31" r="8" fill="${col}"/>
        <circle cx="-7" cy="-31" r="2.4" fill="#fff"/><circle cx="7" cy="-32" r="2.4" fill="#fff"/><circle cx="-6.4" cy="-30.6" r="1.2" fill="#130c27"/><circle cx="7.6" cy="-31.6" r="1.2" fill="#130c27"/>`;
      case "risiko": return `${feet}<path d="M-14 -36h28v14c0 10-6 17-14 20c-8-3-14-10-14-20z" fill="${col}"/><rect x="-11" y="-32" width="22" height="7" rx="3.5" fill="#130c27"/>
        <circle cx="-4" cy="-28.5" r="1.6" fill="#fb7185"/><circle cx="4" cy="-28.5" r="1.6" fill="#fb7185"/><path d="M-6 -16h12M0 -22v12" stroke="#fff" stroke-width="2"/>`;
      default: return `${feet}<rect x="-15" y="-40" width="30" height="38" rx="10" fill="#f1ecff"/><path d="M-12 -40l4-8 4 6 4-8 4 8 4-6 4 8z" fill="#fcd34d"/>${eyes(-27, 5)}
        <rect x="14" y="-30" width="4" height="16" rx="1" fill="#92400e"/><rect x="10" y="-34" width="12" height="6" rx="2" fill="#a16207"/>`;
    }
  }
  function viewRat(data) {
    const C = data.council;
    if (!C || !C.recent.length) return '<div class="card"><div class="empty">Noch keine Abstimmungen – kommen mit dem nächsten Kaufsignal.</div></div>';
    ratPick = Math.min(ratPick, C.recent.length - 1);
    const ids = Object.keys(C.members), accs = C.accuracy.filter(a => a.votes);
    return `<div class="card scene"><div id="viz" class="vbox"><svg viewBox="0 0 360 300" class="vsvg" role="img" aria-label="Der Rat stimmt ab"></svg></div>
      <div id="ratcap" style="padding:4px 16px 16px;text-align:center"></div></div>
      <h2>Wer lag richtig?</h2><div class="card">${accs.length ? accs.map(a => `
        <div class="vbar"><span class="who" style="--c:${MEMB[a.id] || "#a78bfa"}"><i></i>${esc(a.name)}</span><div class="trk" style="--c:${MEMB[a.id] || "#a78bfa"}"><div style="width:${a.pct}%"></div></div><b>${a.pct} %</b><small>${a.votes}</small></div>`).join("")
        : '<div class="empty">Noch keine abgeschlossenen Trades mit Abstimmung</div>'}
        <div class="lbl" style="margin-top:8px">Richtig = Bedenken und der Trade ging schief – oder Ja und er ging gut. Zahl rechts: Anzahl Stimmen.</div></div>
      <h2>Letzte Abstimmungen <small>antippen zum Ansehen</small></h2><div class="card" id="ratlist">${C.recent.map((c, i) => `
        <div class="row" data-rat="${i}" style="cursor:pointer;border-radius:10px">
        <div class="l"><b>${esc(c.pair)} · ${esc(c.bot)}</b><span>${ids.map(k => { const [s, , col] = vote(c.votes[k]); return `<span style="color:${col};font-weight:700;font-size:11px">${s}</span>`; }).join(" ")} · ${when(c.t)}</span></div>
        <div class="r"><b class="${c.m > 0 ? "up" : "down"}">${c.m > 0 ? "×" + num2(c.m) : "Nein"}</b></div></div>`).join("")}</div>`;
  }
  function mountRat(el, data) {
    const C = data.council, svg = el.querySelector("svg");
    if (!svg) return;
    const ids = Object.keys(C.members), cx = 180, cy = 212;
    const back = `<defs><radialGradient id="lamp" cx=".5" cy="0" r="1"><stop offset="0" stop-color="#c4b5fd" stop-opacity=".35"/><stop offset="1" stop-color="#c4b5fd" stop-opacity="0"/></radialGradient>
        <radialGradient id="holo2" cx=".5" cy="1" r="1"><stop offset="0" stop-color="#a5f3fc" stop-opacity=".75"/><stop offset="1" stop-color="#22d3ee" stop-opacity="0"/></radialGradient>
        <linearGradient id="room" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d1040"/><stop offset="1" stop-color="#0b0618"/></linearGradient>
        <filter id="g2" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
      <rect width="360" height="300" fill="url(#room)"/>
      ${[[22, 14], [98, 6], [262, 6], [300, 18]].map(([x, y], i) => `<rect x="${x}" y="${y}" width="${i === 1 || i === 2 ? 70 : 44}" height="36" rx="3" fill="#0b0618" stroke="#3d2d6e"/>
        <polyline points="${Array.from({length: 8}, (_, k) => `${x + 4 + k * ((i === 1 || i === 2 ? 70 : 44) - 8) / 7},${y + 26 - Math.abs(Math.sin(k * 1.7 + i)) * 18}`).join(" ")}" fill="none" stroke="${["#4ade80", "#67e8f9", "#e879f9", "#fbbf24"][i]}" stroke-width="1.4" ${reduce ? "" : `class="vglow" style="animation-delay:${i * .3}s"`}/>`).join("")}
      <ellipse cx="180" cy="150" rx="170" ry="110" fill="url(#lamp)"/>`;
    const show = i => {
      ratPick = i;
      const d = C.recent[i];
      // Mitglieder hinter dem Tisch, im Halbkreis
      const pos = ids.map((k, j) => { const a = Math.PI * (1.14 + 0.72 * j / (ids.length - 1)); return [cx + Math.cos(a) * 138, cy - 18 + Math.sin(a) * 62]; });
      let members = "", signs = "";
      ids.forEach((k, j) => {
        const [x, y] = pos[j], [s, label, col] = vote(d.votes[k]);
        members += `<g class="memb" style="--d:${j * 0.1}s"><g transform="translate(${x.toFixed(1)},${y.toFixed(1)})">${figure(k, MEMB[k] || "#a78bfa")}</g></g>`;
        const w = s.length * 7 + 12;
        signs += `<g class="memb" style="--d:${0.5 + j * 0.12}s"><g transform="translate(${x.toFixed(1)},${(y - 62).toFixed(1)})">
          <line x1="0" y1="7" x2="0" y2="14" stroke="#c4b5fd" stroke-width="1.4"/>
          <rect x="${-w / 2}" y="-8" width="${w}" height="16" rx="5" fill="${col}" ${d.votes[k] != null ? 'filter="url(#g2)"' : ""}/>
          <text y="4" text-anchor="middle" font-size="10" font-weight="800" fill="#130c27" font-family="${SANS}">${s}</text></g>
          <text x="${x.toFixed(1)}" y="${(y + 12).toFixed(1)}" text-anchor="middle" font-size="9" font-weight="600" fill="#f1ecff" paint-order="stroke" stroke="#0b0618" stroke-width="3" font-family="${SANS}">${esc(C.members[k])}</text></g>`;
      });
      const okv = d.m > 0, verdict = okv ? `GENEHMIGT ×${num2(d.m)}` : "ABGELEHNT";
      const table = `<ellipse cx="${cx}" cy="${cy + 10}" rx="128" ry="40" fill="#120a26"/><ellipse cx="${cx}" cy="${cy}" rx="124" ry="36" fill="#22164a" stroke="#a78bfa" stroke-width="1.6" filter="url(#g2)"/>
        <ellipse cx="${cx}" cy="${cy}" rx="104" ry="28" fill="none" stroke="#67e8f9" stroke-opacity=".25" stroke-dasharray="2 4"/>
        <ellipse cx="${cx}" cy="${cy - 30}" rx="34" ry="44" fill="url(#holo2)" opacity=".7"/>
        <ellipse cx="${cx}" cy="${cy - 4}" rx="30" ry="9" fill="none" stroke="#a5f3fc" stroke-width="1.2" stroke-dasharray="5 3" ${reduce ? "" : 'class="spin"'}/>
        <text x="${cx}" y="${cy - 30}" text-anchor="middle" font-size="15" font-weight="700" fill="#ecfeff" font-family="${MONO}" filter="url(#g2)">${esc(d.pair)}</text>
        <text x="${cx}" y="${cy - 15}" text-anchor="middle" font-size="9.5" fill="#a5f3fc" font-family="${SANS}">${esc(d.bot)}</text>`;
      const chair = `<g transform="translate(316,286)">${figure("chair")}</g>
        <text x="316" y="296" text-anchor="middle" font-size="9" font-weight="600" fill="#f1ecff" font-family="${SANS}">Vorsitz</text>
        <g class="memb" style="--d:1.3s"><g transform="translate(${okv ? 214 : 222},282) rotate(-8)"><rect x="-62" y="-13" width="124" height="24" rx="4" fill="#0b0618" fill-opacity=".85" stroke="${okv ? "#4ade80" : "#fb7185"}" stroke-width="2.2" filter="url(#g2)"/>
          <text y="4" text-anchor="middle" font-size="12.5" font-weight="800" fill="${okv ? "#4ade80" : "#fb7185"}" font-family="${MONO}">${verdict}</text></g></g>`;
      svg.innerHTML = back + members + table + signs + chair + '<g id="bubble"></g>';
      const cap = document.getElementById("ratcap");
      const tally = {ja: 0, hm: 0, nein: 0};
      ids.forEach(k => { const f = d.votes[k]; if (f == null) return; if (f <= 0) tally.nein++; else if (f < 1) tally.hm++; else tally.ja++; });
      if (cap) cap.innerHTML = `<div><b>${esc(d.pair)}</b> · ${esc(d.bot)} · ${when(d.t)}</div>
        <div style="margin-top:4px" class="n"><span class="up">JA ${tally.ja}</span> · <span class="warnc">BEDENKEN ${tally.hm}</span> · <span class="down">NEIN ${tally.nein}</span></div>
        ${d.reason ? `<div class="lbl" style="margin-top:2px">${esc(d.reason)}</div>` : ""}
        <div class="lbl" style="margin-top:6px">${C.recent.map((_, j) => `<span style="display:inline-block;width:6px;height:6px;border-radius:50%;margin:0 2px;background:${j === i ? "#a78bfa" : "#3d2d6e"}"></span>`).join("")}</div>`;
      document.querySelectorAll("#ratlist [data-rat]").forEach(r => r.style.background = +r.dataset.rat === i ? "#a78bfa1f" : "");
      // Sprechblasen: nacheinander, was jedes Mitglied zu seiner Stimme sagt
      const lines = ids.map((k, j) => ({j, q: quote(k, d.votes[k], d.votes[k] <= 0 ? d.reason : null)})).filter(x => x.q);
      let bi = 0;
      const bubble = () => {
        const b = svg.querySelector("#bubble");
        if (!b || !lines.length) return;
        const {j, q} = lines[bi++ % lines.length], [x, y] = pos[j];
        const w = Math.min(220, q.length * 6.2 + 18), bx = Math.max(w / 2 + 4, Math.min(356 - w / 2, x));
        b.innerHTML = `<g class="memb" style="--d:0s"><line x1="${x.toFixed(1)}" y1="58" x2="${x.toFixed(1)}" y2="${(y - 71).toFixed(1)}" stroke="#f1ecff" stroke-opacity=".6" stroke-dasharray="2 2"/>
          <rect x="${(bx - w / 2).toFixed(1)}" y="34" width="${w.toFixed(1)}" height="23" rx="11.5" fill="#f1ecff"/>
          <path d="M${(x - 4).toFixed(1)} 56l4 5 4-5z" fill="#f1ecff"/>
          <text x="${bx.toFixed(1)}" y="49.5" text-anchor="middle" font-size="11" font-weight="600" fill="#130c27" font-family="${SANS}">${esc(q)}</text></g>`;
      };
      bubble();
      clearInterval(show.h);
      if (!reduce) show.h = setInterval(() => { if (!document.hidden) bubble(); }, 1600);
    };
    offs.push(() => clearInterval(show.h));
    show(Math.min(ratPick, C.recent.length - 1));
    every(7000, () => { if (ratAuto) show((ratPick + 1) % C.recent.length); });
    const list = document.getElementById("ratlist");
    if (list) on(list, "click", e => { const r = e.target.closest("[data-rat]"); if (r) { ratAuto = false; show(+r.dataset.rat); } });
  }

  // --- 4) Kugel: alle Märkte als Punkte, Note = Farbe, Kaufsignal = großer Punkt, Nr. 1 = Ring ----
  function viewKugel(data) {
    const F = data.bots.focus && data.bots.focus.board, M = data.markets || [];
    const items = F ? F.items : [];
    const top = [...M].sort((a, b) => b.score - a.score);
    return `<div class="card scene"><div class="scene-h"><div class="lbl">Kugel · ${M.length} Märkte · ziehen zum Drehen</div></div>
      <div id="viz" class="vbox"><canvas class="vcan" style="height:340px;touch-action:none"></canvas><div class="vtip"></div></div>
      <div class="vleg"><span class="scale">${RAMP.map(c => `<i style="background:${c}"></i>`).join("")}</span><span>Note 0 → 1 (Trend, Schwung, Bewegung, Liquidität)</span>
      <span><i class="dot" style="width:12px;height:12px;background:#7dd3fc"></i>Kaufsignal jetzt</span><span><i class="dot" style="background:none;border:2px solid #e879f9"></i>Nr. 1 der Rangliste</span></div></div>
      ${F ? `<h2>Fokus-Bot</h2><div class="card"><div class="lbl">Mindestnote ${num2(F.min_score)} · ${when(F.t)}</div><div style="margin-top:4px">${esc(F.status || "")}</div></div>` : ""}
      <h2>Rangliste <small>frische Kaufsignale</small></h2><div class="card">${items.length ? items.map((e, i) => `
        <div class="row"><div class="l"><b>${i + 1}. ${esc(e.name)}</b><span>${esc(e.bot_name)} · Bilanz ${esc(e.edge)}${e.rr ? " · Chance/Risiko " + num2(e.rr) : ""}</span>
          ${e.block ? `<span class="down">Gesperrt: ${esc(e.block)}</span>` : e.taken ? '<span class="up">Vom Fokus-Bot gekauft</span>' : ""}</div>
        <div class="r" style="min-width:86px"><b>${num2(e.score)}</b><div class="trk sm" style="--c:${rampCol(e.score)}"><div style="width:${Math.round(e.score * 100)}%"></div></div></div></div>`).join("")
        : '<div class="empty">In diesem Lauf gab es kein frisches Kaufsignal</div>'}</div>
      <details class="card"><summary>Alle Märkte als Tabelle</summary>${top.map(m => `
        <div class="row"><div class="l"><b>${esc(m.name)}</b><span>${esc(m.group)} · ${esc(m.trend)} · RSI ${m.rsi} · ${esc(m.venue)}</span></div>
        <div class="r"><b>${num2(m.score)}</b><span>${m.signal ? "Signal " + num2(m.setup) : ""}</span></div></div>`).join("")}</details>`;
  }
  function mountKugel(el, data) {
    const M = data.markets || [], cv = el.querySelector("canvas");
    if (!cv) return;
    const [g, W, H, dpr] = canvasFit(cv), R = Math.min(W - 84, H - 30) / 2, cx = 70 + (W - 70) / 2, cy = H / 2 + 4;
    const bg = starLayer(W, H, dpr, 21, Math.round(W * H / 1000));
    // Fibonacci-Kugel, nach Gruppe sortiert -> Gruppen liegen in Breitengrad-Bändern
    const groups = [...new Set(M.map(m => m.group))];
    const pts3 = [...M].sort((a, b) => groups.indexOf(a.group) - groups.indexOf(b.group)).map((m, i, arr) => {
      const y = 1 - (i + 0.5) / arr.length * 2, r = Math.sqrt(1 - y * y), th = i * 2.399963;
      return {m, x: Math.cos(th) * r, y, z: Math.sin(th) * r};
    });
    const first = pts3.find(p => p.m.top);
    const bands = groups.map(gname => { const ys = pts3.filter(p => p.m.group === gname).map(p => p.y); return [gname, (Math.max(...ys) + Math.min(...ys)) / 2]; });
    let rot = first ? Math.atan2(-first.x, first.z) : 0, rotOff = rot, lastT = 0, drag = null, hover = null;   // Nr. 1 vorne
    const draw = t => {
      lastT = t;
      if (!reduce && !drag) rot = t * 0.18 + rotOff;
      g.drawImage(bg, 0, 0, W, H);
      const atm = g.createRadialGradient(cx, cy, R * 0.9, cx, cy, R * 1.25);
      atm.addColorStop(0, "#7c3aed55"); atm.addColorStop(1, "#7c3aed00");
      g.fillStyle = atm; g.beginPath(); g.arc(cx, cy, R * 1.25, 0, Math.PI * 2); g.fill();
      const grd = g.createRadialGradient(cx - R * .35, cy - R * .35, R * .1, cx, cy, R);
      grd.addColorStop(0, "#2a1b5c"); grd.addColorStop(1, "#0e0920");
      g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.fillStyle = grd; g.fill(); g.strokeStyle = "#a78bfa66"; g.lineWidth = 1; g.stroke();
      [-0.5, 0, 0.5].forEach(y => { g.beginPath(); g.ellipse(cx, cy - y * R, R * Math.sqrt(1 - y * y), R * 0.12 * Math.sqrt(1 - y * y), 0, 0, Math.PI * 2); g.strokeStyle = "#a78bfa22"; g.stroke(); });
      bands.forEach(([gname, y]) => {   // Gruppen-Bänder links beschriftet
        g.fillStyle = "#ab9fcd"; g.font = `500 9.5px ${SANS}`; g.textAlign = "left";
        g.fillText(gname, 4, cy - y * R + 3);
      });
      const cs = Math.cos(rot), sn = Math.sin(rot);
      pts3.forEach(p => { p.px = cx + (p.x * cs + p.z * sn) * R; p.pz = -p.x * sn + p.z * cs; p.py = cy - p.y * R; });
      [...pts3].sort((a, b) => a.pz - b.pz).forEach(p => {
        const front = p.pz > 0, m = p.m, size = (m.signal ? 6 : 3.4) * (front ? 1 : 0.75), col = rampCol(m.signal ? m.setup : m.score);
        g.globalAlpha = front ? 1 : 0.3;
        if (front && m.signal) { g.save(); g.shadowColor = col; g.shadowBlur = 12; }
        g.beginPath(); g.arc(p.px, p.py, size, 0, Math.PI * 2); g.fillStyle = col; g.fill();
        if (front && m.signal) g.restore();
        if (m.top) {
          const pulse = reduce ? 0 : (Math.sin(t * 3) + 1) * 2;
          g.beginPath(); g.arc(p.px, p.py, size + 5 + pulse, 0, Math.PI * 2); g.strokeStyle = "#e879f9"; g.lineWidth = 2; g.stroke();
          if (front) { g.fillStyle = "#f1ecff"; g.font = `700 11px ${SANS}`; g.textAlign = "center"; g.fillText("Nr. 1: " + m.name, p.px, p.py - size - 12); }
        }
        if (p === hover) { g.beginPath(); g.arc(p.px, p.py, size + 4, 0, Math.PI * 2); g.strokeStyle = "#f1ecff"; g.lineWidth = 1.5; g.stroke(); }
        g.globalAlpha = 1;
      });
    };
    loop(draw);
    const at = e => { const b = cv.getBoundingClientRect(); return [e.clientX - b.left, e.clientY - b.top]; };
    on(cv, "pointerdown", e => { drag = {x: at(e)[0], rot}; cv.setPointerCapture(e.pointerId); pick(e); });
    on(cv, "pointermove", e => {
      if (drag) { rot = drag.rot + (at(e)[0] - drag.x) / R; rotOff = rot - lastT * 0.18; if (reduce) draw(0); }
      pick(e);
    });
    on(cv, "pointerup", () => { drag = null; });
    on(cv, "pointerleave", () => { drag = null; hover = null; tip(el, null); });
    function pick(e) {
      const [x, y] = at(e);
      let best = null, bd = 22;
      pts3.forEach(p => { if (p.pz > 0) { const d = Math.hypot(p.px - x, p.py - y); if (d < bd) { bd = d; best = p; } } });
      hover = best;
      if (!best) return tip(el, null);
      const m = best.m;
      tip(el, `<b>${num2(m.score)} · ${esc(m.name)}</b><span>${esc(m.group)} · ${esc(m.trend)} · RSI ${m.rsi} · Bewegung ${String(m.move).replace(".", ",")} %</span>
        <span>${esc(m.venue)}${m.signal ? ` · Kaufsignal (${esc(m.setup_bot)}) Note ${num2(m.setup)}${m.blocked ? " – gesperrt" : ""}` : ""}</span>`, x, y);
    }
  }

  return {
    view, mount, unmount,
    setSub(k) { if (k === "zentrale") k = "schiff"; if (SUBS.some(s => s[0] === k)) sub = k; },
  };
})();
