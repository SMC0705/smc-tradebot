// Live-Ansichten der App: Zentrale (isometrisch), Orbit (offene Trades), Rat (Abstimmungen), Kugel (alle Märkte).
// Nur Anzeige – liest ausschließlich status.json. Animationen stoppen, wenn die App im Hintergrund ist, und
// laufen gar nicht, wenn am Handy "Bewegung reduzieren" eingeschaltet ist.
const LIVE = (() => {
  let sub = "zentrale", raf = 0, offs = [];
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // Team-Farben: geprüfte Kategorie-Palette (dunkler Modus), Reihenfolge fest – jede Farbe hat zusätzlich ein Text-Label
  const TEAM_COL = {krypto: "#3987e5", meme: "#d95926", markt: "#199e70", makro: "#c98500", fokus: "#d55181"};
  // Noten-Skala (sequenziell, ein Farbton): niedrig = dunkel, hoch = hell
  const RAMP = ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"];
  const rampCol = s => RAMP[Math.max(0, Math.min(RAMP.length - 1, Math.round(s * (RAMP.length - 1))))];
  const SUBS = [["zentrale", "Zentrale"], ["orbit", "Orbit"], ["rat", "Rat"], ["kugel", "Kugel"]];
  const pct0 = v => `${v > 0 ? "+" : ""}${(v ?? 0).toLocaleString("de-DE", {maximumFractionDigits: 1})} %`;
  const num2 = v => (v ?? 0).toLocaleString("de-DE", {minimumFractionDigits: 2, maximumFractionDigits: 2});

  function on(el, ev, fn, opt) { el.addEventListener(ev, fn, opt); offs.push(() => el.removeEventListener(ev, fn, opt)); }
  function loop(step) {
    if (reduce) { step(0); return; }
    const t0 = performance.now();
    const tick = now => { if (!document.hidden) step((now - t0) / 1000); raf = requestAnimationFrame(tick); };
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
  const teamOf = (data, id) => data.bots[id].team;
  const teamName = (data, tid) => (data.teams && data.teams[tid] ? data.teams[tid].name : tid);

  // ---------------------------------------------------------------------------------------------
  function view(data) {
    const seg = `<div class="seg">${SUBS.map(([k, l]) => `<button data-sub="${k}" class="${k === sub ? "on" : ""}">${l}</button>`).join("")}</div>`;
    const body = sub === "orbit" ? viewOrbit(data) : sub === "rat" ? viewRat(data) : sub === "kugel" ? viewKugel(data) : viewZentrale(data);
    return seg + body;
  }
  function mount(data) {
    unmount();
    const el = document.getElementById("viz");
    if (!el) return;
    if (sub === "zentrale") mountZentrale(el, data);
    else if (sub === "orbit") mountOrbit(el, data);
    else if (sub === "kugel") mountKugel(el, data);
    else if (sub === "rat") mountRat(el, data);
  }

  // --- 1) Zentrale: isometrische Bot-Zentrale ---------------------------------------------------
  const ROOMS = [["krypto", 0, 0], ["meme", 1, 0], ["makro", 0, 1], ["markt", 2, 0], ["fokus", 1, 1], ["tresor", 2, 1]];
  const RW = 7, RD = 5.2, GAP = 0.9, S = 11.2;                 // Raumgröße (Welt-Einheiten), Abstand, Maßstab
  const iso = (x, y, z = 0) => [ (x - y) * 0.866 * S + 126, (x + y) * 0.5 * S - z * S + 46 ];
  const pts = a => a.map(p => iso(...p).map(v => v.toFixed(1)).join(",")).join(" ");

  function viewZentrale(data) {
    return `<div class="card" style="padding:10px"><div id="viz" class="vbox"><svg viewBox="0 0 364 252" class="vsvg"></svg><div class="vtip"></div></div>
      <div class="vleg"><span><i class="dot" style="background:var(--up)"></i>handelt (Bildschirm grün/rot = im Plus/Minus)</span>
      <span><i class="dot" style="background:#8a90a0"></i>wartet auf ein Signal</span><span>💤 ausgeschaltet</span></div>
      <div class="lbl" style="margin-top:6px">Jeder Roboter ist ein Bot. Antippen für Details.</div></div>`;
  }
  function room(tid, gx, gy) {
    const x0 = gx * (RW + GAP), y0 = gy * (RD + GAP), x1 = x0 + RW, y1 = y0 + RD, H = 1.1;
    const col = TEAM_COL[tid] || "#8a90a0";
    return {tid, x0, y0, x1, y1, svg: `
      <polygon points="${pts([[x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0]])}" fill="${col}" fill-opacity=".16" stroke="${col}" stroke-opacity=".5"/>
      <polygon points="${pts([[x0, y0, 0], [x1, y0, 0], [x1, y0, H], [x0, y0, H]])}" fill="${col}" fill-opacity=".28"/>
      <polygon points="${pts([[x0, y0, 0], [x0, y1, 0], [x0, y1, H], [x0, y0, H]])}" fill="${col}" fill-opacity=".38"/>`};
  }
  function desk(x, y, glow) {
    const b = [[x - .35, y - .25, 0], [x + .35, y - .25, 0], [x + .35, y + .25, 0], [x - .35, y + .25, 0]];
    const top = b.map(p => [p[0], p[1], .45]);
    const [sx, sy] = iso(x - .05, y - .15, .75);
    return `<polygon points="${pts(top)}" fill="#2c3140"/><polygon points="${pts([b[1], b[2], top[2], top[1]])}" fill="#22262f"/>
      <polygon points="${pts([b[2], b[3], top[3], top[2]])}" fill="#1b1e25"/>
      <rect x="${(sx - 6).toFixed(1)}" y="${(sy - 5).toFixed(1)}" width="12" height="8" rx="1.5" fill="${glow || "#3a4050"}" ${glow ? 'class="vglow"' : ""}/>`;
  }
  function robot(col, off) {
    return `<g class="rb"><ellipse cx="0" cy="1" rx="5" ry="2" fill="#000" opacity=".35"/>
      <g class="rbb"><rect x="-4.5" y="-12" width="9" height="9" rx="3" fill="${off ? "#5b6070" : col}"/>
      <rect x="-3.5" y="-20" width="7" height="7" rx="2.5" fill="${off ? "#6b7080" : "#e8eaf0"}"/>
      <circle cx="-1.4" cy="-16.5" r="1" fill="#0f1115"/><circle cx="1.4" cy="-16.5" r="1" fill="#0f1115"/>
      <line x1="0" y1="-20" x2="0" y2="-23" stroke="${off ? "#6b7080" : col}" stroke-width="1.2"/><circle cx="0" cy="-23.5" r="1.3" fill="${off ? "#6b7080" : col}"/>
      ${off ? '<text x="6" y="-20" font-size="8" fill="#8a90a0">z</text>' : ""}</g></g>`;
  }
  function mountZentrale(el, data) {
    const svg = el.querySelector("svg"), B = data.bots, P = data.pool;
    const byTeam = {};
    Object.keys(B).forEach(id => (byTeam[teamOf(data, id)] = byTeam[teamOf(data, id)] || []).push(id));
    // Räume von hinten nach vorne – jeder Raum ist eine eigene Ebene mit Boden, Wänden, Tischen, Schild und Robotern,
    // damit vordere Räume (samt Schild) nie von Robotern dahinter verdeckt werden
    const rooms = [...ROOMS].sort((p, q) => (p[1] + p[2]) - (q[1] + q[2])).map(([tid, gx, gy]) => room(tid, gx, gy));
    const actors = [];
    let html = "";
    rooms.forEach((r, ri) => {
      let inner = r.svg;
      if (r.tid === "tresor") {
        const [cx, cy] = iso((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2 + .3, 0);
        inner += `<g transform="translate(${cx.toFixed(1)},${cy.toFixed(1)})">
          ${[0, 1, 2, 3].map(i => `<ellipse cx="0" cy="${-i * 4}" rx="11" ry="5" fill="#c98500" stroke="#0f1115" stroke-width=".8"/>`).join("")}
          <text x="0" y="-27" text-anchor="middle" font-size="10.5" font-weight="700" fill="#e8eaf0" paint-order="stroke" stroke="#0f1115" stroke-width="3">${esc(eur(P.equity))}</text>
          <text x="0" y="-16" text-anchor="middle" font-size="9" font-weight="600" fill="${P.pnl_pct >= 0 ? "#22c55e" : "#ef4444"}" paint-order="stroke" stroke="#0f1115" stroke-width="3">${esc(pc(P.pnl_pct))}</text></g>`;
      }
      const ids = r.tid === "tresor" ? [] : (byTeam[r.tid] || []);
      ids.forEach((id, i) => {   // Tische an der hinteren Wand, je Reihe 4
        const b = B[id], dx = r.x0 + 1.0 + (i % 4) * 1.5, dy = r.y0 + 1.9 + Math.floor(i / 4) * 1.6;
        const holding = b.positions.length > 0, pnl = b.positions.reduce((a, p) => a + p.pnl_pct, 0);
        inner += desk(dx, dy, holding ? (pnl >= 0 ? "#22c55e" : "#ef4444") : null);
        actors.push({id, b, ri, col: TEAM_COL[r.tid], off: !b.enabled, holding, room: r, home: [dx + .15, dy + .75],
                     pos: [dx + .15, dy + .75], goal: null, wait: Math.random() * 3});
      });
      const [lx, ly] = iso(r.x0 + RW / 2, r.y0, 2.6);
      const name = r.tid === "tresor" ? "Sammelkonto" : teamName(data, r.tid);
      const sign = `<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="middle" font-size="9.5" font-weight="700" fill="#e8eaf0"
        paint-order="stroke" stroke="#0f1115" stroke-width="3" stroke-linejoin="round">${esc(name)}</text>`;
      inner += `<g class="actors" data-room="${ri}">${actors.filter(a => a.ri === ri).map(a => `<g data-bot="${esc(a.id)}" class="act" style="cursor:pointer">
        <rect x="-12" y="-28" width="24" height="32" fill="transparent"/>${robot(a.col, a.off)}
        ${a.holding ? `<g transform="translate(6,-26)"><circle r="5.5" fill="#0f1115" stroke="${a.col}"/><text y="3" text-anchor="middle" font-size="7.5" fill="#e8eaf0">${a.b.positions.length}</text></g>` : ""}</g>`).join("")}</g>`;
      html += `<g>${inner}${sign}</g>`;   // Schild zuletzt: liegt über den Robotern des eigenen Raums
    });
    svg.innerHTML = html;
    const nodes = {};
    svg.querySelectorAll(".act").forEach(n => nodes[n.dataset.bot] = n);
    const place = (a, t) => {
      const [x, y] = iso(a.pos[0], a.pos[1], 0);
      const bob = a.off || reduce ? 0 : Math.sin(t * 4 + a.home[0]) * 1.2;
      nodes[a.id].setAttribute("transform", `translate(${x.toFixed(1)},${(y + bob).toFixed(1)})`);
    };
    const order = () => {   // innerhalb eines Raums: wer weiter vorne steht, wird später gezeichnet
      [...actors].sort((p, q) => (p.pos[0] + p.pos[1]) - (q.pos[0] + q.pos[1])).forEach(a => nodes[a.id].parentNode.appendChild(nodes[a.id]));
    };
    let last = 0;
    loop(t => {
      const dt = Math.min(0.1, t - last); last = t;
      actors.forEach(a => {
        if (!a.off && !a.holding && !reduce) {   // wartende Bots laufen im Raum herum
          if (!a.goal) {
            a.wait -= dt;
            if (a.wait <= 0) a.goal = [a.room.x0 + .7 + Math.random() * (RW - 1.4), a.room.y0 + 2.2 + Math.random() * (RD - 2.8)];
          } else {
            const vx = a.goal[0] - a.pos[0], vy = a.goal[1] - a.pos[1], d = Math.hypot(vx, vy), sp = 0.8 * dt;
            if (d < sp) { a.pos = a.goal; a.goal = null; a.wait = 1 + Math.random() * 3; }
            else a.pos = [a.pos[0] + vx / d * sp, a.pos[1] + vy / d * sp];
          }
        }
        place(a, t);
      });
      order();
    });
    on(svg, "pointermove", e => {
      const g = e.target.closest(".act"), box = el.getBoundingClientRect();
      if (!g) return tip(el, null);
      const b = B[g.dataset.bot];
      tip(el, `<b>${esc(b.name)}</b><span>${esc(b.style)} · ${b.enabled ? pc(b.pnl_pct) : "aus"} · ${b.positions.length} offen</span>`,
          e.clientX - box.left, e.clientY - box.top);
    });
    on(svg, "pointerleave", () => tip(el, null));
  }

  // --- 2) Orbit: offene Trades zwischen Stop (außen) und Ziel (innen) ---------------------------
  function viewOrbit(data) {
    const all = [];
    for (const [id, b] of Object.entries(data.bots)) b.positions.forEach(p => all.push({...p, bot: b.name, id, team: b.team}));
    all.sort((a, b) => b.progress - a.progress);
    return `<div class="card" style="padding:10px"><div id="viz" class="vbox"><canvas class="vcan" style="height:340px"></canvas><div class="vtip"></div></div>
      <div class="vleg"><span><i class="dot" style="background:var(--up)"></i>im Plus</span><span><i class="dot" style="background:var(--down)"></i>im Minus</span>
      <span>innen = nah am Ziel · außen = nah am Stop</span><span>Größe = Wert</span></div></div>
      <h2>Offene Trades (${all.length})</h2><div class="card">${all.length ? all.map(p => `
        <div class="row"><div class="l"><b>${esc(p.pair)}</b><span>${esc(p.bot)} · ${p.progress != null ? Math.round(p.progress * 100) + " % zum Ziel" : ""}</span></div>
        <div class="r"><b class="${cls(p.pnl_pct)}">${pc(p.pnl_pct)}</b><span>${eur(p.value)}</span></div></div>`).join("")
        : '<div class="empty">Gerade keine offenen Trades</div>'}</div>`;
  }
  function canvasFit(cv) {
    const r = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
    cv.width = w * r; cv.height = h * r;
    const g = cv.getContext("2d"); g.setTransform(r, 0, 0, r, 0, 0);
    return [g, w, h];
  }
  function mountOrbit(el, data) {
    const cv = el.querySelector("canvas"), [g, W, H] = canvasFit(cv);
    const cx = W / 2, cy = H / 2, R1 = Math.min(W, H) / 2 - 30, R0 = R1 * 0.38;
    const teams = Object.keys(data.teams || {}).filter(t => data.teams[t].members.length);
    const per = {};
    for (const [id, b] of Object.entries(data.bots)) b.positions.forEach(p => (per[b.team] = per[b.team] || []).push({...p, bot: b.name}));
    const planets = [];
    teams.forEach((tid, ti) => {
      const list = per[tid] || [], a0 = ti / teams.length * Math.PI * 2 - Math.PI / 2, span = Math.PI * 2 / teams.length;
      list.forEach((p, i) => planets.push({p, tid, a: a0 + span * (i + 0.5) / list.length, span, a0,
        r: R1 - (p.progress ?? 0.5) * (R1 - R0), size: 4 + Math.min(9, Math.sqrt(Math.max(p.value, 1)) / 3)}));
    });
    const pool = data.pool;
    let hover = null;
    const draw = t => {
      g.clearRect(0, 0, W, H);
      teams.forEach((tid, ti) => {   // Sektoren je Team
        const a0 = ti / teams.length * Math.PI * 2 - Math.PI / 2, a1 = a0 + Math.PI * 2 / teams.length;
        g.beginPath(); g.moveTo(cx, cy); g.arc(cx, cy, R1, a0, a1); g.closePath();
        g.fillStyle = TEAM_COL[tid] + "14"; g.fill();
        g.strokeStyle = "#262a33"; g.lineWidth = 1; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.cos(a0) * R1, cy + Math.sin(a0) * R1); g.stroke();
        const am = (a0 + a1) / 2, label = teamName(data, tid);
        g.fillStyle = "#8a90a0"; g.font = "600 10px system-ui"; g.textAlign = "center";
        const tw = g.measureText(label).width, lx = Math.max(tw / 2 + 2, Math.min(W - tw / 2 - 2, cx + Math.cos(am) * (R1 + 14)));
        g.fillText(label, lx, cy + Math.sin(am) * (R1 + 14) + 3);
      });
      [[R1, "Stop", -1], [(R1 + R0) / 2, "", 0], [R0, "Ziel", 1]].forEach(([r, l, side]) => {   // Ringe
        g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.strokeStyle = "#2c3140"; g.lineWidth = 1; g.stroke();
        if (l) { g.fillStyle = "#8a90a0"; g.font = "9px system-ui"; g.textAlign = "center"; g.fillText(l, cx, side < 0 ? cy - r + 11 : cy + r - 4); }
      });
      g.fillStyle = "#e8eaf0"; g.font = "700 15px system-ui"; g.textAlign = "center";   // Mitte: Sammelkonto
      g.fillText(eur(pool.equity), cx, cy + 2);
      g.fillStyle = pool.pnl_pct >= 0 ? "#22c55e" : "#ef4444"; g.font = "600 11px system-ui"; g.fillText(pc(pool.pnl_pct), cx, cy + 17);
      planets.forEach(o => {   // Planeten kreisen langsam in ihrem Team-Sektor
        const drift = reduce ? 0 : Math.sin(t * 0.25 + o.r) * o.span * 0.18;
        o.x = cx + Math.cos(o.a + drift) * o.r; o.y = cy + Math.sin(o.a + drift) * o.r;
        g.beginPath(); g.arc(o.x, o.y, o.size + 2, 0, Math.PI * 2); g.fillStyle = "#181b22"; g.fill();
        g.beginPath(); g.arc(o.x, o.y, o.size, 0, Math.PI * 2); g.fillStyle = o.p.pnl_pct >= 0 ? "#22c55e" : "#ef4444"; g.fill();
        if (o === hover) { g.beginPath(); g.arc(o.x, o.y, o.size + 4, 0, Math.PI * 2); g.strokeStyle = "#e8eaf0"; g.lineWidth = 2; g.stroke(); }
      });
      if (!planets.length) { g.fillStyle = "#8a90a0"; g.font = "11px system-ui"; g.fillText("keine offenen Trades", cx, cy + 40); }
    };
    loop(draw);
    const pick = e => {
      const b = cv.getBoundingClientRect(), x = e.clientX - b.left, y = e.clientY - b.top;
      let best = null, bd = 24;
      planets.forEach(o => { const d = Math.hypot(o.x - x, o.y - y); if (d < bd) { bd = d; best = o; } });
      hover = best;
      if (reduce) draw(0);
      if (!best) return tip(el, null);
      const p = best.p;
      tip(el, `<b>${esc(pc(p.pnl_pct))} · ${esc(p.pair)}</b><span>${esc(p.bot)} · ${Math.round((p.progress ?? 0) * 100)} % zum Ziel</span>
        <span>Kauf ${px(p.entry)} · jetzt ${px(p.price)} · Stop ${px(p.stop)}</span>`, x, y);
    };
    on(cv, "pointermove", pick); on(cv, "pointerdown", pick); on(cv, "pointerleave", () => { hover = null; tip(el, null); });
  }

  // --- 3) Rat: wie das Team über jeden Kauf abstimmt ---------------------------------------------
  const FACES = {analyst: "📈", news: "📰", trend: "🧭", muster: "🔍", kollegen: "🤝", risiko: "🛡️"};
  let ratPick = 0;
  const vote = f => f == null ? ["–", "nicht gefragt", "#5b6070"] : f <= 0 ? ["✕", "Nein", "#ef4444"]
    : f < 1 ? ["!", "Bedenken", "#f59e0b"] : ["✓", f > 1 ? "Klares Ja" : "Ja", "#22c55e"];
  function viewRat(data) {
    const C = data.council;
    if (!C || !C.recent.length) return '<div class="card"><div class="empty">Noch keine Abstimmungen – kommen mit dem nächsten Kaufsignal.</div></div>';
    ratPick = Math.min(ratPick, C.recent.length - 1);
    const d = C.recent[ratPick], ids = Object.keys(C.members);
    const accs = C.accuracy.filter(a => a.votes);
    return `<div class="card" style="padding:10px"><div id="viz" class="vbox"><svg viewBox="0 0 360 230" class="vsvg"></svg></div>
      <div style="text-align:center;margin-top:2px"><b>${esc(d.pair)}</b> · ${esc(d.bot)} · ${when(d.t)}</div>
      <div style="text-align:center;margin-top:4px" class="${d.m > 0 ? "up" : "down"}"><b>${d.m > 0 ? `✓ Gekauft mit Risiko x${num2(d.m)}` : "✕ Abgelehnt"}</b></div>
      ${d.reason ? `<div class="lbl" style="text-align:center">${esc(d.reason)}</div>` : ""}</div>
      <h2>Wer lag richtig?</h2><div class="card">${accs.length ? accs.map(a => `
        <div class="vbar"><span>${FACES[a.id]} ${esc(a.name)}</span><div class="trk"><div style="width:${a.pct}%"></div></div><b>${a.pct} %</b><small>${a.votes}</small></div>`).join("")
        : '<div class="empty">Noch keine abgeschlossenen Trades mit Abstimmung</div>'}
        <div class="lbl" style="margin-top:8px">Richtig = Bedenken und der Trade ging schief – oder Ja und er ging gut. Zahl rechts: Anzahl Stimmen.</div></div>
      <h2>Letzte Abstimmungen</h2><div class="card">${C.recent.map((c, i) => `
        <div class="row" data-rat="${i}" style="cursor:pointer${i === ratPick ? ";background:#22262f;margin:0 -8px;padding-left:8px;padding-right:8px;border-radius:8px" : ""}">
        <div class="l"><b>${esc(c.pair)} · ${esc(c.bot)}</b><span>${ids.map(k => { const [s, , col] = vote(c.votes[k]); return `<span style="color:${col}">${s}</span>`; }).join(" ")} · ${when(c.t)}</span></div>
        <div class="r"><b class="${c.m > 0 ? "up" : "down"}">${c.m > 0 ? "x" + num2(c.m) : "Nein"}</b></div></div>`).join("")}</div>`;
  }
  function mountRat(el, data) {
    const C = data.council, svg = el.querySelector("svg");
    if (!svg) return;
    const d = C.recent[ratPick], ids = Object.keys(C.members), cx = 180, cy = 150;
    let html = `<ellipse cx="${cx}" cy="${cy + 8}" rx="120" ry="40" fill="#22262f"/><ellipse cx="${cx}" cy="${cy}" rx="112" ry="34" fill="#2c3140"/>
      <text x="${cx}" y="${cy + 5}" text-anchor="middle" font-size="12" font-weight="700" fill="#e8eaf0">${esc(d.pair)}</text>`;
    ids.forEach((k, i) => {
      const a = Math.PI * (1.05 + 0.9 * i / (ids.length - 1)), x = cx + Math.cos(a) * 140, y = cy + Math.sin(a) * 105;
      const [s, label, col] = vote(d.votes[k]);
      html += `<g class="memb" style="--d:${i * 0.12}s" transform="translate(${x.toFixed(1)},${y.toFixed(1)})">
        <circle r="19" fill="#22262f" stroke="${col}" stroke-width="2"/><text y="6" text-anchor="middle" font-size="17">${FACES[k]}</text>
        <g transform="translate(14,-15)"><circle r="8" fill="${col}"/><text y="3.5" text-anchor="middle" font-size="10" font-weight="800" fill="#0f1115">${s}</text></g>
        <text y="31" text-anchor="middle" font-size="8.5" fill="#e8eaf0">${esc(C.members[k])}</text>
        <text y="41" text-anchor="middle" font-size="8" fill="#8a90a0">${label}</text></g>`;
    });
    svg.innerHTML = html;
    on(el.closest("main") || document, "click", e => {
      const r = e.target.closest("[data-rat]");
      if (!r) return;
      ratPick = +r.dataset.rat;
      if (typeof render === "function") render();
    });
  }

  // --- 4) Kugel: alle Märkte als Punkte, Note = Farbe, Kaufsignal = großer Punkt, Nr. 1 = Ring ----
  function viewKugel(data) {
    const F = data.bots.focus && data.bots.focus.board, M = data.markets || [];
    const items = F ? F.items : [];
    const top = [...M].sort((a, b) => b.score - a.score);
    return `<div class="card" style="padding:10px"><div id="viz" class="vbox"><canvas class="vcan" style="height:330px;touch-action:none"></canvas><div class="vtip"></div></div>
      <div class="vleg"><span class="scale">${RAMP.map(c => `<i style="background:${c}"></i>`).join("")}</span><span>Note 0 → 1 (Trend, Schwung, Bewegung, Liquidität)</span>
      <span><i class="dot big"></i>Kaufsignal jetzt</span><span><i class="dot ring"></i>Nr. 1 der Rangliste</span></div>
      <div class="lbl" style="margin-top:4px">${M.length} Märkte · ziehen zum Drehen · antippen für Details</div></div>
      ${F ? `<h2>Fokus-Bot</h2><div class="card"><div class="lbl">Mindestnote ${num2(F.min_score)} · ${when(F.t)}</div><div style="margin-top:4px">${esc(F.status || "")}</div></div>` : ""}
      <h2>Rangliste (frische Kaufsignale)</h2><div class="card">${items.length ? items.map((e, i) => `
        <div class="row"><div class="l"><b>${i + 1}. ${esc(e.name)}</b><span>${esc(e.bot_name)} · Bilanz ${esc(e.edge)}${e.rr ? " · Chance/Risiko " + num2(e.rr) : ""}</span>
          ${e.block ? `<span class="down">✕ ${esc(e.block)}</span>` : e.taken ? '<span class="up">✓ vom Fokus-Bot gekauft</span>' : ""}</div>
        <div class="r" style="min-width:86px"><b>${num2(e.score)}</b><div class="trk sm"><div style="width:${Math.round(e.score * 100)}%;background:${rampCol(e.score)}"></div></div></div></div>`).join("")
        : '<div class="empty">In diesem Lauf gab es kein frisches Kaufsignal</div>'}</div>
      <details class="card"><summary>Alle Märkte als Tabelle</summary>${top.map(m => `
        <div class="row"><div class="l"><b>${esc(m.name)}</b><span>${esc(m.group)} · ${esc(m.trend)} · RSI ${m.rsi} · ${esc(m.venue)}</span></div>
        <div class="r"><b>${num2(m.score)}</b><span>${m.signal ? "Signal " + num2(m.setup) : ""}</span></div></div>`).join("")}</details>`;
  }
  function mountKugel(el, data) {
    const M = data.markets || [], cv = el.querySelector("canvas");
    if (!cv) return;
    const [g, W, H] = canvasFit(cv), R = Math.min(W - 84, H - 30) / 2, cx = 70 + (W - 70) / 2, cy = H / 2 + 4;
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
      g.clearRect(0, 0, W, H);
      const grd = g.createRadialGradient(cx - R * .3, cy - R * .3, R * .1, cx, cy, R);
      grd.addColorStop(0, "#1e2433"); grd.addColorStop(1, "#12151c");
      g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.fillStyle = grd; g.fill(); g.strokeStyle = "#2c3140"; g.stroke();
      bands.forEach(([gname, y]) => {   // Gruppen-Bänder links beschriftet
        const yy = cy - y * R;
        g.fillStyle = "#8a90a0"; g.font = "9px system-ui"; g.textAlign = "left";
        g.fillText(gname, 4, yy + 3);
      });
      const cs = Math.cos(rot), sn = Math.sin(rot);
      pts3.forEach(p => { p.px = cx + (p.x * cs + p.z * sn) * R; p.pz = -p.x * sn + p.z * cs; p.py = cy - p.y * R; });
      [...pts3].sort((a, b) => a.pz - b.pz).forEach(p => {
        const front = p.pz > 0, m = p.m, size = (m.signal ? 6 : 3.5) * (front ? 1 : 0.75);
        g.globalAlpha = front ? 1 : 0.35;
        g.beginPath(); g.arc(p.px, p.py, size + 2, 0, Math.PI * 2); g.fillStyle = "#12151c"; g.fill();
        g.beginPath(); g.arc(p.px, p.py, size, 0, Math.PI * 2); g.fillStyle = rampCol(m.signal ? m.setup : m.score); g.fill();
        if (m.top) {
          const pulse = reduce ? 0 : (Math.sin(t * 3) + 1) * 2;
          g.beginPath(); g.arc(p.px, p.py, size + 5 + pulse, 0, Math.PI * 2); g.strokeStyle = "#e8eaf0"; g.lineWidth = 2; g.stroke();
          if (front) { g.fillStyle = "#e8eaf0"; g.font = "700 11px system-ui"; g.textAlign = "center"; g.fillText("Nr. 1: " + m.name, p.px, p.py - size - 12); }
        }
        if (p === hover) { g.beginPath(); g.arc(p.px, p.py, size + 4, 0, Math.PI * 2); g.strokeStyle = "#e8eaf0"; g.lineWidth = 1.5; g.stroke(); }
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
    setSub(k) { if (SUBS.some(s => s[0] === k)) sub = k; },
  };
})();
