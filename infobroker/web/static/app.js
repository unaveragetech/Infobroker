/* Infobroker dashboard client */
(() => {
  const state = {
    selected: null,
    highlights: null,
    dayTab: "gainers",
    weekTab: "gainers",
    watchlist: [],
    chartMode: "line",
    ohlc: [],
    studioBars: [],
    refreshTimer: null,
    liveTimer: null,
    liveQuotes: {},
    liveItems: [],
    liveMeta: null,
    liveFetchId: 0,
    liveSymbol: null,
    liveOhlc: [],
    liveCtrl: null,
    liveEs: null,
    liveTickTimer: null,
    liveChartTf: "live1m",
    liveMarketFocus: "us",
    marketClocks: null,
    clockTimer: null,
    clockSyncTimer: null,
    tradingItems: [],
    tradingPosSnapshot: {},
    tradingActivity: [],
    universeOffset: 0,
    universeLimit: 80,
    universeTotal: 0,
    scanScope: "universe",
    detailCtrl: null,
    studioCtrl: null,
  };

  const Charts = () => window.InfobrokerCharts;

  const $ = (id) => document.getElementById(id);

  function toast(msg, ms = 2800) {
    const el = $("toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("show"), ms);
  }

  async function api(path, opts = {}) {
    const attempts = opts.retries ?? (opts.method && opts.method !== "GET" ? 1 : 3);
    let lastErr = null;
    for (let i = 0; i < attempts; i++) {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), opts.timeoutMs || 90000);
        let res;
        try {
          res = await fetch(path, {
            headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
            ...opts,
            signal: opts.signal || controller.signal,
          });
        } finally {
          clearTimeout(timer);
        }
        let data = null;
        const text = await res.text();
        try {
          data = text ? JSON.parse(text) : null;
        } catch {
          data = { detail: text };
        }
        if (!res.ok) {
          const detail = data?.detail;
          const msg =
            typeof detail === "string"
              ? detail
              : detail?.blockers?.join("; ") ||
                detail?.message ||
                JSON.stringify(detail || data) ||
                res.statusText;
          const err = new Error(msg);
          err.status = res.status;
          err.payload = data;
          // retry transient 5xx
          if (res.status >= 500 && i < attempts - 1) {
            await new Promise((r) => setTimeout(r, 400 * (i + 1)));
            lastErr = err;
            continue;
          }
          throw err;
        }
        return data;
      } catch (e) {
        lastErr = e;
        const retryable =
          e.name === "AbortError" ||
          /failed to fetch|networkerror|load failed/i.test(String(e.message || e));
        if (!retryable || i >= attempts - 1) throw e;
        await new Promise((r) => setTimeout(r, 500 * (i + 1)));
      }
    }
    throw lastErr || new Error("request failed");
  }

  function pctClass(v) {
    if (v == null || Number.isNaN(v)) return "flat";
    if (v > 0) return "up";
    if (v < 0) return "down";
    return "flat";
  }

  function fmtPct(v) {
    if (v == null || Number.isNaN(Number(v))) return "—";
    const n = Number(v);
    return `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
  }

  function fmtPx(v) {
    if (v == null || Number.isNaN(Number(v))) return "—";
    return Number(v).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function fmtMoney(v) {
    if (v == null || Number.isNaN(Number(v))) return "—";
    return `$${Number(v).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }

  function normalizeSymbol(raw) {
    return String(raw || "")
      .trim()
      .toUpperCase()
      .replace(/\s+/g, "")
      .replace(/^\$/, "");
  }

  function drawCandles(canvas, bars) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (!bars || bars.length < 2) {
      drawSpark(canvas, []);
      return;
    }
    const highs = bars.map((b) => b.h);
    const lows = bars.map((b) => b.l);
    const min = Math.min(...lows);
    const max = Math.max(...highs);
    const span = max - min || 1;
    const slot = (w - 8) / bars.length;
    bars.forEach((b, i) => {
      const x = 4 + i * slot + slot / 2;
      const yH = 6 + ((max - b.h) / span) * (h - 12);
      const yL = 6 + ((max - b.l) / span) * (h - 12);
      const yO = 6 + ((max - b.o) / span) * (h - 12);
      const yC = 6 + ((max - b.c) / span) * (h - 12);
      const up = b.c >= b.o;
      ctx.strokeStyle = up ? "#7dce82" : "#f07178";
      ctx.fillStyle = up ? "#7dce82" : "#f07178";
      ctx.beginPath();
      ctx.moveTo(x, yH);
      ctx.lineTo(x, yL);
      ctx.stroke();
      const top = Math.min(yO, yC);
      const body = Math.max(2, Math.abs(yC - yO));
      ctx.fillRect(x - Math.max(1, slot * 0.3), top, Math.max(2, slot * 0.6), body);
    });
  }

  function drawSpark(canvas, values, upColor = "#7dce82", downColor = "#f07178") {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (!values || values.length < 2) {
      ctx.strokeStyle = "#243041";
      ctx.beginPath();
      ctx.moveTo(0, h / 2);
      ctx.lineTo(w, h / 2);
      ctx.stroke();
      return;
    }
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const up = values[values.length - 1] >= values[0];
    ctx.strokeStyle = up ? upColor : downColor;
    ctx.lineWidth = 2;
    ctx.beginPath();
    values.forEach((v, i) => {
      const x = (i / (values.length - 1)) * (w - 4) + 2;
      const y = h - 4 - ((v - min) / span) * (h - 8);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  function miniSparkSvg(values) {
    if (!values || values.length < 2) {
      return `<svg class="spark" viewBox="0 0 72 28"><path d="M2 14 H70" stroke="#243041" fill="none"/></svg>`;
    }
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const up = values[values.length - 1] >= values[0];
    const color = up ? "#7dce82" : "#f07178";
    const pts = values
      .map((v, i) => {
        const x = (i / (values.length - 1)) * 68 + 2;
        const y = 26 - ((v - min) / span) * 22;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
    return `<svg class="spark" viewBox="0 0 72 28"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.8"/></svg>`;
  }

  function selectSymbol(sym, opts = {}) {
    const s = normalizeSymbol(sym);
    if (!s) return;
    state.selected = s;
    $("ord-symbol").value = s;
    $("bt-symbol").value = s;
    if ($("st-symbol")) $("st-symbol").value = s;
    if ($("cs-symbol")) $("cs-symbol").value = s;
    $("detail-sym").textContent = s;
    loadDetail(s);
    document.querySelectorAll("#tracked-body tr").forEach((tr) => {
      tr.classList.toggle("selected", tr.dataset.symbol === s);
      tr.classList.toggle("active", tr.dataset.symbol === s);
    });
    if (opts.goDetail) {
      switchDeskTab("markets", "symbol");
    }
  }

  function renderMoverList(el, rows, pctKey) {
    if (!el) return;
    if (!rows || !rows.length) {
      el.innerHTML = `<div class="empty">No data yet</div>`;
      return;
    }
    el.innerHTML = rows
      .map((r) => {
        const pct = r[pctKey];
        return `<div class="row" data-symbol="${r.symbol}">
          <span class="sym">${r.symbol}</span>
          <span class="mono ${pctClass(pct)}">${fmtPct(pct)}</span>
          <span class="mono muted">${fmtPx(r.price)}</span>
        </div>`;
      })
      .join("");
    el.querySelectorAll("[data-symbol]").forEach((node) => {
      node.addEventListener("click", () => selectSymbol(node.dataset.symbol, { goDetail: true }));
    });
  }

  async function loadHealth() {
    const h = await api("/api/health");
    $("chip-broker").textContent = `broker: ${h.broker}`;
    $("chip-data").textContent = `data: ${h.data}`;
    const mode = $("chip-mode");
    if (h.live) {
      mode.textContent = "mode: LIVE";
      mode.className = "chip live";
    } else {
      mode.textContent = "mode: paper/sim";
      mode.className = "chip ok";
    }
    const ol = $("chip-ollama");
    if (ol) {
      if (h.ollama?.ok && h.ollama?.model_present !== false) {
        ol.textContent = `ollama: ${String(h.ollama.model || "ok").split(":")[0]}`;
        ol.className = "chip ok";
      } else if (h.ollama?.ok) {
        ol.textContent = "ollama: model missing";
        ol.className = "chip warn";
      } else {
        ol.textContent = "ollama: down";
        ol.className = "chip live";
      }
    }
    const mcpChip = $("svc-mcp-chip");
    if (mcpChip) {
      if (h.mcp?.running) {
        mcpChip.textContent = `online · pid ${h.mcp.pid}`;
        mcpChip.className = "mono muted";
        mcpChip.style.color = "var(--lime)";
      } else {
        mcpChip.textContent = "offline";
        mcpChip.className = "mono muted";
        mcpChip.style.color = "var(--rose)";
      }
    }
    const olChip = $("svc-ollama-chip");
    if (olChip) {
      olChip.textContent = h.ollama?.ok
        ? `${String(h.ollama.model || "").split(":")[0]} · ok`
        : "down";
    }
  }

  function clearFollowups() {
    document.querySelectorAll(".gv-followups").forEach((el) => el.remove());
  }

  function appendFollowups(questions) {
    const box = $("assistant-chat");
    if (!box) return;
    clearFollowups();
    const list = (questions || []).map((q) => String(q || "").trim()).filter(Boolean).slice(0, 4);
    if (!list.length) return;
    const wrap = document.createElement("div");
    wrap.className = "gv-followups";
    wrap.setAttribute("aria-label", "Suggested follow-ups");
    const label = document.createElement("div");
    label.className = "gv-followups-label";
    label.textContent = "Suggested";
    wrap.appendChild(label);
    const row = document.createElement("div");
    row.className = "gv-followups-row";
    list.forEach((q) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "gv-followup";
      btn.textContent = q;
      btn.title = q;
      btn.addEventListener("click", () => {
        clearFollowups();
        sendAssistant(q, false);
      });
      row.appendChild(btn);
    });
    wrap.appendChild(row);
    box.appendChild(wrap);
    box.scrollTop = box.scrollHeight;
  }

  function appendChat(role, text, opts = {}) {
    const box = $("assistant-chat");
    if (!box) return;
    if (role === "user") clearFollowups();
    const div = document.createElement("div");
    const extra = opts.className ? ` ${opts.className}` : "";
    div.className = `msg ${role}${role === "assistant" ? " gv-bubble" : ""}${extra}`;
    const who = opts.who || (role === "user" ? "You" : "Grapevine");
    div.innerHTML = `<div class="who">${escapeHtml(who)}</div>${escapeHtml(text).replace(/\n/g, "<br/>")}`;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
    return div;
  }

  function appendCoachCard(step) {
    const title = step.title || "Look here";
    const msg = step.message || "";
    const color = step.color || "cyan";
    appendChat("assistant", `${title}\n${msg}`, {
      className: `coach-card color-${color}`,
      who: "Coach tip",
    });
  }

  function getActiveDeskTab() {
    const btn = document.querySelector("[data-desk-tab].active");
    return btn?.dataset?.deskTab || "markets";
  }

  function getActiveSubTab(group) {
    try {
      return localStorage.getItem(`infobroker_subtab_${group}`) || null;
    } catch {
      return null;
    }
  }

  function buildUiContext() {
    const tab = getActiveDeskTab();
    return {
      active_tab: tab,
      markets_sub: getActiveSubTab("markets"),
      learning_sub: getActiveSubTab("learning"),
      selected_symbol: state.selected || null,
      live_market_focus: state.liveMarketFocus || "us",
      us_open: !!(state.marketClocks && state.marketClocks.us_open),
    };
  }

  function chatHistoryPayload(limit = 8) {
    const box = $("assistant-chat");
    if (!box) return [];
    const msgs = [...box.querySelectorAll(".msg")].slice(-limit);
    return msgs
      .map((el) => {
        const role = el.classList.contains("user") ? "user" : "assistant";
        const who = el.querySelector(".who");
        let text = el.textContent || "";
        if (who) text = text.slice(who.textContent.length).trim();
        return { role, content: text.slice(0, 1500) };
      })
      .filter((m) => m.content);
  }

  function updateGrapevinePulse(snap) {
    const dot = $("gv-pulse-dot");
    const text = $("gv-pulse-text");
    if (!dot || !text) return;
    const open = snap?.us_open;
    const hint = snap?.us_hint || "";
    const g = (snap?.gainers || [])[0];
    const l = (snap?.losers || [])[0];
    dot.classList.remove("open", "closed");
    if (open === true) dot.classList.add("open");
    else if (open === false) dot.classList.add("closed");
    const bits = [];
    bits.push(open ? "US open" : open === false ? "US closed" : "Desk");
    if (hint && !open) bits.push(hint);
    if (g?.symbol) bits.push(`↑ ${g.symbol}`);
    if (l?.symbol) bits.push(`↓ ${l.symbol}`);
    text.textContent = bits.join(" · ");
  }

  /* —— Grapevine coach overlay (circle / arrow / highlight) —— */
  const coachState = {
    active: false,
    steps: [],
    index: 0,
    timer: null,
    gen: 0,
    target: null,
  };

  function coachTargetEl(target) {
    if (!target) return null;
    return document.querySelector(`[data-tour="${target}"]`);
  }

  function clearCoachHighlight() {
    document.querySelectorAll(".coach-highlight").forEach((el) => el.classList.remove("coach-highlight"));
    coachState.target = null;
  }

  function endCoach() {
    coachState.active = false;
    coachState.steps = [];
    coachState.index = 0;
    coachState.gen += 1;
    if (coachState.timer) {
      clearTimeout(coachState.timer);
      coachState.timer = null;
    }
    clearCoachHighlight();
    const root = $("coach-root");
    if (root) root.hidden = true;
    document.body.classList.remove("coach-open");
    const stopBtn = $("btn-coach-stop");
    if (stopBtn) stopBtn.hidden = true;
    const ring = $("coach-ring");
    if (ring) {
      ring.className = "coach-ring";
      ring.style.cssText = "";
    }
    const arrow = $("coach-arrow");
    if (arrow) {
      arrow.className = "coach-arrow";
      arrow.hidden = true;
    }
    const dim = $("coach-dim");
    if (dim) dim.style.clipPath = "";
  }

  function positionCoachUI(step) {
    const el = coachTargetEl(step.target);
    const ring = $("coach-ring");
    const arrow = $("coach-arrow");
    const bubble = $("coach-bubble");
    const dim = $("coach-dim");
    if (!ring || !bubble) return;

    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const pad = step.shape === "circle" ? 18 : 10;
    let rect = el ? el.getBoundingClientRect() : null;
    if (!rect || rect.width < 2 || rect.height < 2) {
      rect = { top: vh * 0.25, left: vw / 2 - 120, width: 240, height: 80 };
    }

    let top = Math.max(8, rect.top - pad);
    let left = Math.max(8, rect.left - pad);
    let width = Math.min(vw - left - 8, rect.width + pad * 2);
    let height = Math.min(vh - top - 8, rect.height + pad * 2);

    if (step.shape === "circle") {
      const side = Math.max(width, height, 72);
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      width = side;
      height = side;
      left = Math.max(8, Math.min(vw - side - 8, cx - side / 2));
      top = Math.max(8, Math.min(vh - side - 8, cy - side / 2));
    }

    const color = step.color || "cyan";
    const shape = step.shape || "rect";
    ring.className = `coach-ring shape-${shape} color-${color}`;
    ring.style.top = `${top}px`;
    ring.style.left = `${left}px`;
    ring.style.width = `${width}px`;
    ring.style.height = `${height}px`;

    if (dim) {
      const x1 = left;
      const y1 = top;
      const x2 = left + width;
      const y2 = top + height;
      dim.style.clipPath = `polygon(evenodd, 0px 0px, ${vw}px 0px, ${vw}px ${vh}px, 0px ${vh}px, 0px 0px, ${x1}px ${y1}px, ${x1}px ${y2}px, ${x2}px ${y2}px, ${x2}px ${y1}px, ${x1}px ${y1}px)`;
    }

    if (arrow) {
      const dir = step.arrow || "none";
      if (!dir || dir === "none") {
        arrow.hidden = true;
      } else {
        arrow.hidden = false;
        arrow.className = `coach-arrow dir-${dir} color-${color}`;
        const midY = top + height / 2;
        const midX = left + width / 2;
        if (dir === "left") {
          arrow.style.top = `${midY - 12}px`;
          arrow.style.left = `${Math.max(4, left - 28)}px`;
        } else if (dir === "right") {
          arrow.style.top = `${midY - 12}px`;
          arrow.style.left = `${Math.min(vw - 28, left + width + 6)}px`;
        } else if (dir === "top") {
          arrow.style.top = `${Math.max(4, top - 28)}px`;
          arrow.style.left = `${midX - 12}px`;
        } else {
          arrow.style.top = `${Math.min(vh - 28, top + height + 6)}px`;
          arrow.style.left = `${midX - 12}px`;
        }
      }
    }

    // Place bubble near target, prefer right then left then below
    const bw = Math.min(320, vw - 24);
    const bh = bubble.offsetHeight || 140;
    let bx = left + width + 16;
    let by = top;
    if (bx + bw > vw - 12) bx = left - bw - 16;
    if (bx < 12) bx = Math.max(12, (vw - bw) / 2);
    if (by + bh > vh - 12) by = Math.max(12, vh - bh - 16);
    if (by < 12) by = 12;
    bubble.style.left = `${bx}px`;
    bubble.style.top = `${by}px`;
  }

  async function showCoachStep(index) {
    if (!coachState.active || index < 0 || index >= coachState.steps.length) {
      endCoach();
      return;
    }
    const gen = ++coachState.gen;
    coachState.index = index;
    const step = coachState.steps[index];

    if (typeof tourState !== "undefined" && tourState.active) endTour(false);

    // Avoid heavy tab reloads unless the target is on another desk section
    const curTab = getActiveDeskTab();
    if (step.tab && step.tab !== curTab) {
      switchDeskTab(step.tab, step.sub || undefined);
    } else if (step.sub && curTab === "markets") {
      const curSub = getActiveSubTab("markets");
      if (step.sub !== curSub) switchSubTab("markets", step.sub);
    }

    if ($("coach-step-label")) {
      $("coach-step-label").textContent = `${index + 1} / ${coachState.steps.length}`;
    }
    if ($("coach-title")) $("coach-title").textContent = step.title || "Look here";
    if ($("coach-message")) $("coach-message").textContent = step.message || "";
    const nextBtn = $("btn-coach-next");
    if (nextBtn) {
      nextBtn.textContent = index >= coachState.steps.length - 1 ? "Done" : "Next";
    }

    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    if (!coachState.active || gen !== coachState.gen) return;

    clearCoachHighlight();
    const el = coachTargetEl(step.target);
    if (el) {
      try {
        el.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "auto" });
      } catch {
        /* ignore */
      }
      el.classList.add("coach-highlight");
      coachState.target = el;
    }
    if (!coachState.active || gen !== coachState.gen) return;
    positionCoachUI(step);
    requestAnimationFrame(() => {
      if (coachState.active && gen === coachState.gen) positionCoachUI(step);
    });

    // Manual Next only — auto-advance caused overlay thrash / tab freezes
    if (coachState.timer) {
      clearTimeout(coachState.timer);
      coachState.timer = null;
    }
  }

  function coachNext() {
    if (!coachState.active) return;
    if (coachState.index >= coachState.steps.length - 1) {
      endCoach();
      return;
    }
    showCoachStep(coachState.index + 1);
  }

  function runCoachSequence(steps) {
    const list = (steps || []).filter((s) => s && s.target);
    if (!list.length) return;
    endCoach();
    coachState.active = true;
    coachState.steps = list;
    coachState.index = 0;
    const root = $("coach-root");
    if (root) root.hidden = false;
    document.body.classList.add("coach-open");
    const stopBtn = $("btn-coach-stop");
    if (stopBtn) stopBtn.hidden = false;
    list.forEach((s) => appendCoachCard(s));
    showCoachStep(0);
  }

  function handleCoachResponse(res) {
    if (res?.desk_snapshot) updateGrapevinePulse(res.desk_snapshot);
    if (Array.isArray(res?.coach) && res.coach.length) {
      runCoachSequence(res.coach);
    }
  }

  function renderActionFeed(actions) {
    const feed = $("action-feed");
    if (!feed) return;
    const rows = actions || [];
    if (!rows.length) {
      feed.innerHTML = `<div class="empty">No tool calls yet</div>`;
      return;
    }
    feed.innerHTML = rows
      .slice(0, 40)
      .map((a) => {
        const cls = a.ok ? "ok" : "bad";
        const args = a.args && Object.keys(a.args).length ? ` ${JSON.stringify(a.args)}` : "";
        return `<div class="action-item ${cls}">
          <strong>${escapeHtml(a.tool)}</strong>${escapeHtml(args)}<br/>
          <span class="muted">${escapeHtml(a.summary || a.error || "")}</span>
        </div>`;
      })
      .join("");
  }

  async function captureDeskPngB64() {
    if (typeof html2canvas !== "function") return null;
    // Capture active desk column only — full document.body freezes the tab
    const target =
      document.querySelector(".desk-tab-panel:not([hidden])") ||
      document.querySelector("main") ||
      document.body;
    const canvas = await html2canvas(target, {
      backgroundColor: "#0c1117",
      scale: 0.32,
      useCORS: true,
      logging: false,
      ignoreElements: (el) =>
        el?.id === "coach-root" ||
        el?.id === "tour-root" ||
        el?.classList?.contains("assistant-column"),
      windowWidth: Math.min(1200, target.scrollWidth || 1200),
      windowHeight: Math.min(800, target.scrollHeight || 800),
    });
    const dataUrl = canvas.toDataURL("image/jpeg", 0.55);
    const b64 = dataUrl.split(",")[1] || null;
    // Drop oversized vision payloads that stall Ollama
    if (b64 && b64.length > 280000) return null;
    return b64;
  }

  async function sendAssistant(message, withShot = false) {
    const text = (message || "").trim();
    if (!text) return;
    appendChat("user", text);
    $("assistant-input").value = "";
    toast(withShot ? "Grapevine reading desk view…" : "Grapevine thinking…");
    let image_b64 = null;
    if (withShot) {
      try {
        image_b64 = await captureDeskPngB64();
      } catch (e) {
        toast(`Screenshot failed: ${e.message}`);
      }
    }
    const history = chatHistoryPayload(4).slice(0, -1);
    try {
      const res = await api("/api/assistant/chat", {
        method: "POST",
        timeoutMs: 75000,
        body: JSON.stringify({
          message: text,
          image_b64,
          history,
          ui_context: buildUiContext(),
        }),
      });
      appendChat("assistant", res.reply || "(no reply)");
      appendFollowups(res.followups);
      renderActionFeed(res.actions?.length ? res.actions : res.action_log || []);
      handleCoachResponse(res);
      if (!res.ok) toast(res.reply || "Assistant error", 4000);
      // Refresh account only when tools may have mutated state
      if ((res.actions || []).some((a) => a.ok && /order|watch|stop/i.test(a.tool || ""))) {
        await Promise.all([loadAccount(), loadOrders(), loadWatchlist()].map((p) => p.catch(() => {})));
      }
    } catch (e) {
      appendChat("assistant", `Error: ${e.message}`);
      appendFollowups(["Is the market open?", "Show top gainers", "Show my watchlist prices", "How do I trade?"]);
      toast(e.message);
    }
  }

  let huntBusy = false;
  let autoHuntTimer = null;

  async function huntTrades({ quiet = false } = {}) {
    if (huntBusy) {
      if (!quiet) toast("Hunt already running…");
      return;
    }
    huntBusy = true;
    if (!quiet) appendChat("user", "Find careful paper-trade opportunities on my desk.");
    toast(quiet ? "Auto-hunt running…" : "Hunting with Grapevine…");
    try {
      const res = await api("/api/assistant/hunt", {
        method: "POST",
        timeoutMs: 90000,
        body: JSON.stringify({ ui_context: buildUiContext() }),
      });
      appendChat("assistant", res.reply || "(no reply)");
      if (!quiet) appendFollowups(res.followups);
      renderActionFeed(res.actions?.length ? res.actions : res.action_log || []);
      // Quiet auto-hunt: text only — no coach overlays
      if (!quiet) handleCoachResponse(res);
      else if (res?.desk_snapshot) updateGrapevinePulse(res.desk_snapshot);
    } catch (e) {
      appendChat("assistant", `Hunt error: ${e.message}`);
      if (!quiet) {
        appendFollowups(["Show top gainers", "Show my watchlist prices", "How do I trade?"]);
      }
      toast(e.message);
    } finally {
      huntBusy = false;
    }
  }

  function setupAutoHunt() {
    if (autoHuntTimer) {
      clearInterval(autoHuntTimer);
      autoHuntTimer = null;
    }
    if ($("auto-hunt")?.checked) {
      autoHuntTimer = setInterval(() => huntTrades({ quiet: true }), 5 * 60 * 1000);
    }
  }

  async function refreshActionFeed() {
    try {
      const data = await api("/api/assistant/actions?limit=30");
      renderActionFeed(data.actions || []);
    } catch {
      /* ignore */
    }
  }

  async function loadKeyLinks() {
    const box = $("key-links-box");
    if (!box) return;
    try {
      const data = await api("/api/key-links");
      const providers = data.providers || {};
      const rows = Object.values(providers)
        .map((p) => {
          const parts = [];
          if (p.signup) parts.push(`<a href="${p.signup}" target="_blank" rel="noopener">${escapeHtml(p.label)} signup</a>`);
          if (p.keys) parts.push(`<a href="${p.keys}" target="_blank" rel="noopener">${escapeHtml(p.label)} keys</a>`);
          return parts.join(" ");
        })
        .join(" ");
      box.innerHTML = `
        <div class="muted" style="font-size:0.72rem;letter-spacing:0.08em;text-transform:uppercase">Get API keys</div>
        <div class="row-links">${rows}</div>`;
    } catch {
      /* keep static fallback links in HTML */
    }
  }

  async function showMissingKeys() {
    try {
      const s = await api("/api/settings");
      const secrets = s.secrets || {};
      const need = [];
      const tips = [];
      if (s.broker === "alpaca" && !secrets.ALPACA_API_KEY?.configured) need.push("Alpaca");
      if (s.broker === "public" && !secrets.PUBLIC_PERSONAL_SECRET?.configured) need.push("Public");
      if (s.broker === "tradier" && !secrets.TRADIER_ACCESS_TOKEN?.configured) need.push("Tradier");
      if (s.data_provider === "finnhub" && !secrets.FINNHUB_API_KEY?.configured) need.push("Finnhub");
      if (s.data_provider === "alphavantage" && !secrets.ALPHAVANTAGE_API_KEY?.configured)
        need.push("Alpha Vantage");
      if (!secrets.FINNHUB_API_KEY?.configured && s.data_provider !== "finnhub")
        tips.push("Finnhub (backup quotes)");
      if (!secrets.ALPHAVANTAGE_API_KEY?.configured && s.data_provider !== "alphavantage")
        tips.push("Alpha Vantage (backup history)");
      const banner = $("missing-keys-banner");
      if (!banner) return;
      if (!need.length && !tips.length) {
        banner.hidden = true;
        return;
      }
      banner.hidden = false;
      banner.className = "banner warn";
      const parts = [];
      if (need.length) parts.push(`Required now: <strong>${need.join(", ")}</strong>`);
      if (tips.length) parts.push(`Optional reliability: ${tips.join(", ")}`);
      banner.innerHTML = `${parts.join(". ")}. Use the Get API keys links above.`;
    } catch {
      /* ignore */
    }
  }

  async function loadAccount() {
    try {
      const a = await api("/api/account");
      $("acct-broker").textContent = a.broker_name || a.broker;
      $("acct-cash").textContent = fmtMoney(a.cash);
      $("acct-equity").textContent = fmtMoney(a.equity);
      $("acct-bp").textContent = fmtMoney(a.buying_power);
      $("acct-pos-count").textContent = String(a.positions?.length || 0);
      const box = $("positions-box");
      const stopBtn = $("btn-process-stops");
      if (stopBtn) stopBtn.hidden = !a.supports_stop_processing;
      if (!a.positions?.length) {
        box.innerHTML = `<div class="empty">No open positions</div>`;
      } else {
        box.innerHTML = a.positions
          .map(
            (p) => `<div class="row">
            <span class="sym" data-symbol="${p.symbol}" style="cursor:pointer">${p.symbol}</span>
            <span class="mono">${p.qty}</span>
            <span class="mono ${pctClass(p.unrealized_pl)}">${fmtMoney(p.unrealized_pl)}</span>
            <button class="btn ghost danger" type="button" data-sell="${p.symbol}" data-qty="${p.qty}" style="padding:0.15rem 0.4rem;font-size:0.68rem">Sell</button>
          </div>`
          )
          .join("");
        box.querySelectorAll("[data-symbol]").forEach((n) =>
          n.addEventListener("click", () => selectSymbol(n.dataset.symbol, { goDetail: true }))
        );
        box.querySelectorAll("[data-sell]").forEach((btn) => {
          btn.addEventListener("click", (ev) => {
            ev.stopPropagation();
            $("ord-symbol").value = btn.dataset.sell;
            $("ord-side").value = "sell";
            $("ord-qty").value = btn.dataset.qty;
            selectSymbol(btn.dataset.sell);
            toast(`Sell ticket loaded for ${btn.dataset.sell}`);
          });
        });
      }
    } catch (e) {
      $("acct-cash").textContent = "—";
      $("positions-box").innerHTML = `<div class="banner error">${escapeHtml(e.message)}</div>`;
    }
  }

  async function loadWatchlist() {
    const w = await api("/api/watchlist");
    state.watchlist = w.symbols || [];
    const box = $("watch-list");
    if (!state.watchlist.length) {
      box.innerHTML = `<div class="empty">Watchlist empty — add a ticker</div>`;
      return;
    }
    box.innerHTML = state.watchlist
      .map(
        (s) => `<div class="row">
        <span class="sym" data-symbol="${s}" style="cursor:pointer">${s}</span>
        <button class="btn ghost danger" data-remove="${s}" type="button" style="padding:0.15rem 0.45rem;font-size:0.7rem">Remove</button>
      </div>`
      )
      .join("");
    box.querySelectorAll("[data-symbol]").forEach((n) =>
      n.addEventListener("click", () => selectSymbol(n.dataset.symbol, { goDetail: true }))
    );
    box.querySelectorAll("[data-remove]").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        try {
          await api(`/api/watchlist/${encodeURIComponent(btn.dataset.remove)}`, {
            method: "DELETE",
          });
          toast(`Removed ${btn.dataset.remove}`);
          await refreshMarket();
        } catch (e) {
          toast(e.message);
        }
      });
    });
  }

  async function loadTracked() {
    const err = $("tracked-error");
    err.hidden = true;
    try {
      const data = await api("/api/tracked");
      const items = data.items || [];
      const body = $("tracked-body");
      if (!items.length) {
        body.innerHTML = `<tr><td colspan="8"><div class="empty">No tracked quotes — add symbols or check data source</div></td></tr>`;
        return;
      }
      body.innerHTML = items
        .map((r) => {
          const sel = state.selected === r.symbol ? "selected" : "";
          const chg = r.change_abs_day;
          const range =
            r.low != null && r.high != null ? `${fmtPx(r.low)}–${fmtPx(r.high)}` : "—";
          return `<tr class="${sel}" data-symbol="${r.symbol}">
            <td class="sym-cell">${escapeHtml(r.symbol)}</td>
            <td class="mono chg-cell">${fmtPx(r.price)}</td>
            <td class="mono chg-cell ${pctClass(chg)}">${chg == null ? "—" : (chg > 0 ? "+" : "") + Number(chg).toFixed(2)}</td>
            <td class="mono ${pctClass(r.change_pct_day)}">${fmtPct(r.change_pct_day)}</td>
            <td class="mono ${pctClass(r.change_pct_week)}">${fmtPct(r.change_pct_week)}</td>
            <td class="mono">${r.rel_volume != null ? r.rel_volume.toFixed(2) + "x" : "—"}</td>
            <td class="mono muted" style="font-size:0.7rem">${range}</td>
            <td>${miniSparkSvg(r.sparkline || [])}</td>
          </tr>`;
        })
        .join("");
      body.querySelectorAll("tr[data-symbol]").forEach((tr) => {
        tr.addEventListener("click", () => selectSymbol(tr.dataset.symbol, { goDetail: true }));
      });
      $("tracked-asof").textContent = new Date().toLocaleTimeString();
    } catch (e) {
      err.hidden = false;
      err.textContent = e.message;
      $("tracked-body").innerHTML = "";
    }
  }

  function renderIndices(indices) {
    const box = $("indices");
    if (!indices?.length) {
      box.innerHTML = `<div class="empty">Index quotes unavailable</div>`;
      return;
    }
    box.innerHTML = indices
      .map(
        (r) => `<div class="index-card" data-symbol="${r.symbol}">
        <div class="sym">${r.symbol}</div>
        <div class="px">${fmtPx(r.price)}</div>
        <div class="mono ${pctClass(r.change_pct_day)}">${fmtPct(r.change_pct_day)}</div>
      </div>`
      )
      .join("");
    box.querySelectorAll("[data-symbol]").forEach((n) =>
      n.addEventListener("click", () => selectSymbol(n.dataset.symbol, { goDetail: true }))
    );
  }

  async function loadHighlights() {
    try {
      const h = await api("/api/highlights");
      state.highlights = h;
      updateGrapevinePulse({
        us_open: !!(state.marketClocks && state.marketClocks.us_open),
        us_hint: state.marketClocks?.us_next_open_label || state.marketClocks?.us_hint,
        gainers: h?.stocks_of_day?.gainers || [],
        losers: h?.stocks_of_day?.losers || [],
      });
      $("tracked-asof").textContent = h.as_of
        ? `as of ${new Date(h.as_of).toLocaleTimeString()}`
        : "—";
      if (h.error) toast(h.error, 4000);
      renderIndices(h.indices || []);
      renderMoverList($("notable-tracked"), h.tracked_notable || [], "change_pct_day");
      renderMoverList($("volume-leaders"), h.volume_leaders || [], "rel_volume");
      // volume leaders show rvol — patch labels
      const volBox = $("volume-leaders");
      if (h.volume_leaders?.length) {
        volBox.innerHTML = h.volume_leaders
          .map(
            (r) => `<div class="row" data-symbol="${r.symbol}">
            <span class="sym">${r.symbol}</span>
            <span class="mono">${r.rel_volume != null ? r.rel_volume.toFixed(2) + "x" : "—"}</span>
            <span class="mono ${pctClass(r.change_pct_day)}">${fmtPct(r.change_pct_day)}</span>
          </div>`
          )
          .join("");
        volBox.querySelectorAll("[data-symbol]").forEach((n) =>
          n.addEventListener("click", () => selectSymbol(n.dataset.symbol, { goDetail: true }))
        );
      }
      renderDayWeek();
    } catch (e) {
      toast(`Highlights: ${e.message}`);
      $("notable-tracked").innerHTML = `<div class="banner error">${e.message}</div>`;
    }
  }

  function renderDayWeek() {
    const h = state.highlights;
    if (!h) return;
    const day = h.stocks_of_day?.[state.dayTab] || [];
    const week = h.stocks_of_week?.[state.weekTab] || [];
    renderMoverList($("stocks-day"), day, "change_pct_day");
    renderMoverList($("stocks-week"), week, "change_pct_week");
  }

  function setDetailTool(tool) {
    const ctrl = ensureDetailController();
    ctrl?.setTool(tool);
    document.querySelectorAll("[data-detail-tool]").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.detailTool === tool);
    });
    const tip = $("detail-tip");
    if (!tip) return;
    if (tool === "trend") tip.textContent = "Trend: click-drag between two points. Undo / Clear removes lines.";
    else if (tool === "hline") tip.textContent = "H-Line: click a price level to pin a horizontal line.";
    else tip.textContent = "Inspect: hover OHLC · drag zoom · wheel zoom · double-click reset. Switch to Trend / H-Line to draw.";
  }

  function ensureDetailController() {
    const C = Charts();
    const canvas = $("detail-spark");
    if (!C || !canvas) return null;
    if (state.detailCtrl) return state.detailCtrl;
    state.detailCtrl = C.createController({
      primaryCanvas: canvas,
      tooltipEl: $("detail-inspect"),
      getBars: () => state.ohlc || [],
      symbol: state.selected,
      onRender: ({ bars, hoverIdx, brush, drawings, draft, viewStart }) =>
        C.drawPriceChart(canvas, bars, {
          mode: state.chartMode === "candle" ? "candle" : "line",
          hoverIdx,
          brush,
          drawings,
          draft,
          viewStart,
        }),
    });
    return state.detailCtrl;
  }

  function renderDetailChart() {
    const tip = $("detail-tip");
    if (!Charts()) {
      const canvas = $("detail-spark");
      if (state.chartMode === "candle") drawCandles(canvas, state.ohlc);
      else drawSpark(canvas, (state.ohlc || []).map((b) => b.c));
      return;
    }
    const ctrl = ensureDetailController();
    ctrl?.redraw();
    if (tip && (!ctrl || ctrl.getTool() === "inspect")) {
      tip.textContent =
        "Inspect: hover OHLC · drag zoom · wheel zoom. Use Trend / H-Line to draw; lines save per ticker.";
    }
  }

  async function loadDetail(sym) {
    $("detail-empty").hidden = true;
    $("detail-body").hidden = false;
    $("detail-price").textContent = "…";
    $("detail-fund").textContent = "";
    $("detail-tip").textContent = "";
    try {
      const [q, f, ohlc] = await Promise.all([
        api(`/api/quote/${encodeURIComponent(sym)}`),
        api(`/api/fundamentals/${encodeURIComponent(sym)}`).catch(() => null),
        api(`/api/ohlc/${encodeURIComponent(sym)}?days=90`).catch(() => ({ bars: [] })),
      ]);
      $("detail-price").textContent = fmtPx(q.Price ?? q.price);
      $("detail-hl").textContent = `${fmtPx(q["Daily High"])} / ${fmtPx(q["Daily Low"])}`;
      $("detail-vol").textContent =
        q.Volume != null && q.Volume !== "N/A"
          ? Number(q.Volume).toLocaleString()
          : "—";
      $("detail-provider").textContent = q.provider || "yahoo";
      state.ohlc = ohlc.bars || [];
      const ctrl = ensureDetailController();
      ctrl?.setSymbol(sym);
      ctrl?.resetView();
      setDetailTool(ctrl?.getTool() || "inspect");
      renderDetailChart();
      if (f) {
        $("detail-fund").textContent = [
          f["Company Name"] || "",
          `Sector: ${f.Sector ?? "—"}`,
          `PE: ${f["PE Ratio"] ?? "—"}  EPS: ${f.EPS ?? "—"}`,
          `Mkt Cap: ${f["Market Cap"] ?? "—"}  Beta: ${f.Beta ?? "—"}`,
        ].join("\n");
      }
    } catch (e) {
      $("detail-empty").hidden = false;
      $("detail-body").hidden = true;
      $("detail-empty").textContent = e.message;
    }
  }

  async function loadOrders() {
    const box = $("orders-box");
    if (!box) return;
    try {
      const data = await api("/api/orders?limit=30");
      const orders = data.orders || [];
      if (!orders.length) {
        box.innerHTML = `<div class="empty">No orders yet</div>`;
        return;
      }
      box.innerHTML = orders
        .map((o) => {
          const canCancel = ["open", "pending"].includes(o.status);
          return `<div class="blotter-row">
            <span class="sym" data-symbol="${escapeHtml(o.symbol)}" style="cursor:pointer">${escapeHtml(o.symbol)}</span>
            <span class="mono ${o.side === "buy" ? "up" : "down"}">${o.side}</span>
            <span class="mono">${escapeHtml(o.status)}</span>
            <div class="meta">${escapeHtml(o.order_type)} qty ${o.qty}${
              o.stop_price != null ? ` stop ${fmtPx(o.stop_price)}` : ""
            }${o.filled_avg_price != null ? ` fill ${fmtPx(o.filled_avg_price)}` : ""}
            ${canCancel ? `<button class="btn ghost danger" data-cancel="${o.id}" type="button" style="margin-left:0.4rem;padding:0.1rem 0.35rem;font-size:0.65rem">Cancel</button>` : ""}
            </div>
          </div>`;
        })
        .join("");
      box.querySelectorAll("[data-symbol]").forEach((n) =>
        n.addEventListener("click", () => selectSymbol(n.dataset.symbol))
      );
      box.querySelectorAll("[data-cancel]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          try {
            await api(`/api/orders/${encodeURIComponent(btn.dataset.cancel)}`, {
              method: "DELETE",
            });
            toast("Order canceled");
            await loadOrders();
          } catch (e) {
            toast(e.message);
          }
        });
      });
    } catch (e) {
      box.innerHTML = `<div class="banner error">${escapeHtml(e.message)}</div>`;
    }
  }

  function currentScanScope() {
    const checked = document.querySelector('input[name="scan-scope"]:checked');
    return checked?.value || state.scanScope || "universe";
  }

  async function runScan(opts = {}) {
    const box = $("scan-box");
    box.innerHTML = `<div class="skeleton"></div><div class="skeleton"></div>`;
    try {
      const scope = opts.scope || currentScanScope();
      state.scanScope = scope;
      const data = await api(`/api/scan?scope=${encodeURIComponent(scope)}`);
      const scopeLabel = data.scope || scope;
      $("scan-asof").textContent = data.as_of
        ? `${scopeLabel} · ${data.hits}/${data.scanned} · ${new Date(data.as_of).toLocaleTimeString()}`
        : "—";
      if (!data.items?.length) {
        box.innerHTML = `<div class="empty">No strong signals in the ${escapeHtml(scopeLabel)} scan right now</div>`;
        if (opts.goScanner) switchDeskTab("markets", "scanner");
        return;
      }
      box.innerHTML = data.items
        .map(
          (item) => `<article class="signal-card" data-symbol="${item.symbol}">
          <div class="title">
            <span>${escapeHtml(item.symbol)}</span>
            <span class="mono ${pctClass(item.change_pct_day)}">${fmtPct(item.change_pct_day)} · ${fmtPx(item.price)}</span>
          </div>
          <ul class="signals">${(item.signals || [])
            .map((s) => `<li>${escapeHtml(s)}</li>`)
            .join("")}</ul>
          <p class="tip">${escapeHtml(item.tip || "")}</p>
        </article>`
        )
        .join("");
      box.querySelectorAll("[data-symbol]").forEach((n) =>
        n.addEventListener("click", () => selectSymbol(n.dataset.symbol, { goDetail: true }))
      );
      if (opts.goScanner) switchDeskTab("markets", "scanner");
    } catch (e) {
      box.innerHTML = `<div class="banner error">${escapeHtml(e.message)}</div>`;
    }
  }

  const lessonState = {
    ids: [],
    current: null,
    page: 0,
    data: null,
    tutorPage: 0,
  };

  function lessonCardHtml(l) {
    const pages = l.page_count ? `${l.page_count} pages` : "";
    return `<button type="button" class="lesson-card" data-lesson="${escapeHtml(l.id)}" aria-label="Open lesson ${escapeHtml(l.title)}">
      <div class="lesson-card-top">
        <h3>${escapeHtml(l.title)}</h3>
        <span class="level">${escapeHtml(l.level || "")}</span>
      </div>
      <p class="teaser">${escapeHtml(l.body)}</p>
      <div class="topics">${(l.topics || [])
        .slice(0, 4)
        .map((t) => `<span class="topic">${escapeHtml(t)}</span>`)
        .join("")}
        ${pages ? `<span class="topic">${pages}</span>` : ""}
      </div>
    </button>`;
  }

  async function loadLessons() {
    try {
      const data = await api("/api/lessons");
      const lessons = Array.isArray(data) ? data : data.lessons || [];
      const tutor = Array.isArray(data) ? null : data.tutor;
      lessonState.ids = lessons.map((l) => l.id);
      if (tutor?.id && !lessonState.ids.includes(tutor.id)) {
        lessonState.ids = [tutor.id, ...lessonState.ids];
      }
      const rail = $("lessons-box");
      if (rail) {
        rail.innerHTML = lessons.slice(0, 6).map(lessonCardHtml).join("");
        rail.querySelectorAll("[data-lesson]").forEach((btn) => {
          btn.addEventListener("click", () => {
            switchDeskTab("learning", "lessons");
            openLesson(btn.dataset.lesson, 0);
          });
        });
      }
      renderLearningLessonGrid(lessons);
      if (tutor) renderTutorList(tutor);
    } catch (e) {
      if ($("lessons-box")) {
        $("lessons-box").innerHTML = `<div class="banner error">${escapeHtml(e.message)}</div>`;
      }
    }
  }

  function renderLearningLessonGrid(lessons) {
    const grid = $("learning-lesson-grid");
    if (!grid) return;
    if (!lessons?.length) {
      grid.innerHTML = `<div class="empty">No skill lessons loaded.</div>`;
      return;
    }
    grid.innerHTML = lessons
      .map(
        (l) => `<div class="strategy-card" data-open-lesson="${escapeHtml(l.id)}">
          <h3>${escapeHtml(l.title)}</h3>
          <p>${escapeHtml(l.body)}</p>
          <p class="muted" style="margin-top:0.35rem">${l.page_count || "?"} pages · ${escapeHtml(l.level || "")}</p>
        </div>`
      )
      .join("");
    grid.querySelectorAll("[data-open-lesson]").forEach((el) => {
      el.addEventListener("click", () => openLesson(el.dataset.openLesson, 0));
    });
  }

  async function renderTutorList(summary) {
    const box = $("tutor-page-list");
    if (!box) return;
    try {
      const tutor = await api("/api/learn/tutor");
      if ($("tutor-blurb")) $("tutor-blurb").textContent = tutor.overview || tutor.body || "";
      box.innerHTML = (tutor.pages || [])
        .map(
          (p, i) => `<button type="button" class="tutor-page-item" data-tutor-page="${i}">
            <span>${escapeHtml(p.title)}</span>
            <span class="n">${i + 1}/${tutor.pages.length}</span>
          </button>`
        )
        .join("");
      box.querySelectorAll("[data-tutor-page]").forEach((btn) => {
        btn.addEventListener("click", () => openLesson("ways_to_trade", Number(btn.dataset.tutorPage)));
      });
      lessonState.tutorPages = tutor.pages?.length || 0;
    } catch {
      box.innerHTML = summary
        ? `<button type="button" class="tutor-page-item" data-tutor-page="0"><span>Open tutor</span><span class="n">${summary.page_count || ""}</span></button>`
        : "";
    }
  }

  async function loadTradeStories() {
    const box = $("trade-stories");
    const sum = $("stories-summary");
    if (!box) return;
    try {
      const data = await api("/api/learn/trade-stories?limit=40");
      if (sum) sum.textContent = data.summary?.message || `${data.summary?.count || 0} trades`;
      const stories = data.stories || [];
      if (!stories.length) {
        box.innerHTML = `<div class="empty">No trades yet — place a paper order, then reload.</div>`;
        return;
      }
      box.innerHTML = stories
        .map((s) => {
          const demo = s.demo ? " demo" : "";
          const fill =
            s.fill != null
              ? fmtPx(s.fill)
              : s.limit_price != null
                ? `limit ${fmtPx(s.limit_price)}`
                : "—";
          return `<article class="story-card${demo}">
            <header>
              <h3>${escapeHtml(s.title || `${s.side} ${s.symbol}`)}</h3>
              <span class="style">${escapeHtml(s.style || "")}</span>
            </header>
            <div class="meta">${escapeHtml(s.order_type)} · ${escapeHtml(s.status)} · fill ${fill}${s.stop_price != null ? ` · stop ${fmtPx(s.stop_price)}` : ""}${s.demo ? " · DEMO" : ""}</div>
            <p class="idea">${escapeHtml(s.idea || "")}</p>
            <p class="idea" style="font-size:0.78rem">${escapeHtml(s.tutor_tip || "")}</p>
            ${s.risk_note ? `<p class="meta">${escapeHtml(s.risk_note)}</p>` : ""}
            <div class="story-actions">
              <button class="btn" type="button" data-story-lesson="${escapeHtml(s.lesson_id || "playbook")}">Open related lesson</button>
              <button class="btn ghost" type="button" data-story-symbol="${escapeHtml(s.symbol)}">Chart ${escapeHtml(s.symbol)}</button>
            </div>
          </article>`;
        })
        .join("");
      box.querySelectorAll("[data-story-lesson]").forEach((btn) => {
        btn.addEventListener("click", () => openLesson(btn.dataset.storyLesson, 0));
      });
      box.querySelectorAll("[data-story-symbol]").forEach((btn) => {
        btn.addEventListener("click", () => {
          selectSymbol(btn.dataset.storySymbol);
          switchDeskTab("charts");
        });
      });
    } catch (e) {
      box.innerHTML = `<div class="banner error">${escapeHtml(e.message)}</div>`;
    }
  }

  function closeLessonModal() {
    $("lesson-modal")?.classList.remove("open");
    document.querySelectorAll(".lesson-card.active").forEach((c) => c.classList.remove("active"));
  }

  async function openLesson(id, pageIndex = 0) {
    const modal = $("lesson-modal");
    if (!modal) return;
    modal.classList.add("open");
    $("lesson-body").innerHTML = `<div class="skeleton"></div>`;
    document.querySelectorAll(".lesson-card").forEach((c) => {
      c.classList.toggle("active", c.dataset.lesson === id);
    });
    try {
      const l = await api(`/api/lessons/${encodeURIComponent(id)}`);
      lessonState.current = l.id;
      lessonState.data = l;
      lessonState.page = Math.max(0, Math.min(pageIndex, (l.pages || []).length - 1 || 0));
      if (l.id === "ways_to_trade") {
        try {
          localStorage.setItem("infobroker_tutor_page", String(lessonState.page));
        } catch {
          /* ignore */
        }
      }
      $("lesson-title").textContent = l.title;
      renderLessonPage();
    } catch (e) {
      $("lesson-body").innerHTML = `<div class="banner error">${escapeHtml(e.message)}</div>`;
    }
  }

  function renderLessonPage() {
    const l = lessonState.data;
    if (!l) return;
    const pages = l.pages || [];
    const page = pages[lessonState.page] || {
      title: l.title,
      sections: l.sections,
      overview: l.overview,
      chart: l.chart,
      terms: l.terms,
      examples: l.examples,
      takeaways: l.takeaways,
      practice: l.practice,
    };
    const total = Math.max(pages.length, 1);
    $("lesson-meta").textContent = [
      l.level,
      `page ${lessonState.page + 1}/${total}`,
      page.title,
      ...(l.topics || []).slice(0, 3),
    ]
      .filter(Boolean)
      .join(" · ");
    if ($("lesson-page-label")) {
      $("lesson-page-label").textContent = `${lessonState.page + 1} / ${total}`;
    }
    const prog = $("lesson-progress");
    if (prog) {
      prog.innerHTML = pages
        .map(
          (p, i) =>
            `<button type="button" class="${i === lessonState.page ? "active" : ""}" data-jump-page="${i}">${i + 1}. ${escapeHtml((p.title || "").replace(/^\d+\s*·\s*/, "").slice(0, 28))}</button>`
        )
        .join("");
      prog.querySelectorAll("[data-jump-page]").forEach((btn) => {
        btn.addEventListener("click", () => {
          lessonState.page = Number(btn.dataset.jumpPage);
          renderLessonPage();
        });
      });
    }

    const sections = (page.sections || [])
      .map(
        (s) => `<section class="lesson-section"><h3>${escapeHtml(s.heading)}</h3><p>${escapeHtml(s.text)}</p></section>`
      )
      .join("");
    const terms = (page.terms || l.terms || [])
      .map((t) => `<li><strong>${escapeHtml(t.term)}</strong> — ${escapeHtml(t.def)}</li>`)
      .join("");
    const examples = (page.examples || [])
      .map((ex) => `<li><strong>${escapeHtml(ex.title)}</strong><br/>${escapeHtml(ex.detail)}</li>`)
      .join("");
    const takeaways = (page.takeaways || []).map((t) => `<li>${escapeHtml(t)}</li>`).join("");
    const practice = (page.practice || []).map((t) => `<li>${escapeHtml(t)}</li>`).join("");
    const chart = page.chart || l.chart || {};
    const quiz = page.quiz
      ? `<details class="lesson-quiz"><summary>Tutor check — reveal answer</summary>
          <p style="margin:0.5rem 0 0.25rem"><strong>Q:</strong> ${escapeHtml(page.quiz.q)}</p>
          <p style="margin:0"><strong>A:</strong> ${escapeHtml(page.quiz.a)}</p>
        </details>`
      : "";

    $("lesson-body").innerHTML = `
      <h3 style="margin:0 0 0.5rem;color:var(--amber)">${escapeHtml(page.title || l.title)}</h3>
      ${page.insight ? `<p class="lesson-insight">${escapeHtml(page.insight)}</p>` : ""}
      ${page.sections || page.overview || chart.type ? `<div class="lesson-chart-block">
        <canvas id="lesson-chart" width="780" height="220"></canvas>
        <p class="caption">${escapeHtml(chart.caption || "")}</p>
      </div>` : ""}
      ${page.overview && !page.sections?.length ? `<p class="lesson-overview">${escapeHtml(page.overview)}</p>` : ""}
      ${sections}
      ${terms ? `<div class="lesson-h">Key terms</div><ul class="lesson-terms">${terms}</ul>` : ""}
      ${examples ? `<div class="lesson-h">Examples</div><ul class="lesson-examples">${examples}</ul>` : ""}
      ${takeaways ? `<div class="lesson-h">Takeaways</div><ul class="lesson-takeaways">${takeaways}</ul>` : ""}
      ${practice ? `<div class="lesson-h">Practice</div><ul class="lesson-practice">${practice}</ul>` : ""}
      ${quiz}
      <div class="inline" style="margin-top:1rem">
        <button class="btn" type="button" id="btn-lesson-charts">Open Chart studio</button>
        <button class="btn" type="button" id="btn-lesson-learning">Learning tab</button>
        <button class="btn primary" type="button" id="btn-lesson-ask">Ask Grapevine</button>
      </div>`;
    drawLessonChart($("lesson-chart"), chart.type || l.id);
    $("btn-lesson-charts")?.addEventListener("click", () => {
      closeLessonModal();
      switchDeskTab("charts");
      toast("Practice this page on a real ticker");
    });
    $("btn-lesson-learning")?.addEventListener("click", () => {
      closeLessonModal();
      switchDeskTab("learning", l.id === "ways_to_trade" ? "tutor" : "lessons");
    });
    $("btn-lesson-ask")?.addEventListener("click", () => {
      closeLessonModal();
      const msg = `You are my trading tutor. Teach page "${page.title}" from lesson "${l.title}" (${l.id}). Then ask one quiz question and wait for my answer.`;
      sendAssistant(msg, false);
      toast("Sent to Grapevine");
    });
    if ($("btn-page-prev")) $("btn-page-prev").disabled = lessonState.page <= 0;
    if ($("btn-page-next")) $("btn-page-next").disabled = lessonState.page >= total - 1;
  }

  function stepPage(delta) {
    const pages = lessonState.data?.pages || [];
    if (!pages.length) return;
    const next = lessonState.page + delta;
    if (next < 0 || next >= pages.length) return;
    lessonState.page = next;
    if (lessonState.current === "ways_to_trade") {
      try {
        localStorage.setItem("infobroker_tutor_page", String(lessonState.page));
      } catch {
        /* ignore */
      }
    }
    renderLessonPage();
  }

  function stepLesson(delta) {
    const ids = lessonState.ids;
    if (!ids.length) return;
    let idx = ids.indexOf(lessonState.current);
    if (idx < 0) idx = 0;
    idx = (idx + delta + ids.length) % ids.length;
    openLesson(ids[idx], 0);
  }

  function drawLessonChart(canvas, type) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#0a1018";
    ctx.fillRect(0, 0, w, h);
    const drawers = {
      candles_demo: drawLessonCandles,
      candles: drawLessonCandles,
      trend_ma: drawLessonTrend,
      trend: drawLessonTrend,
      rsi_demo: drawLessonRsi,
      rsi: drawLessonRsi,
      risk_demo: drawLessonRisk,
      risk: drawLessonRisk,
      chase_demo: drawLessonChase,
      chase: drawLessonChase,
      levels_demo: drawLessonLevels,
      support_resistance: drawLessonLevels,
      volume_demo: drawLessonVolume,
      volume: drawLessonVolume,
      stops_demo: drawLessonStops,
      stops: drawLessonStops,
      macd_demo: drawLessonMacdEdu,
      macd: drawLessonMacdEdu,
      playbook_demo: drawLessonPlaybook,
      playbook: drawLessonPlaybook,
    };
    (drawers[type] || drawLessonCandles)(ctx, w, h);
  }

  function _lcandle(ctx, x, c, o, hi, lo, bull) {
    const mid = x;
    ctx.strokeStyle = bull ? "#7dd3fc" : "#f07178";
    ctx.fillStyle = bull ? "rgba(125,211,252,0.35)" : "rgba(240,113,120,0.35)";
    ctx.beginPath();
    ctx.moveTo(mid, hi);
    ctx.lineTo(mid, lo);
    ctx.stroke();
    const top = Math.min(o, c);
    const bot = Math.max(o, c);
    ctx.fillRect(mid - 8, top, 16, Math.max(3, bot - top));
    ctx.strokeRect(mid - 8, top, 16, Math.max(3, bot - top));
  }

  function drawLessonCandles(ctx, w, h) {
    ctx.fillStyle = "#9aa8bc";
    ctx.font = "12px IBM Plex Mono, monospace";
    ctx.fillText("Hammer at support", 24, 22);
    ctx.fillText("Shooting star at resistance", w / 2 + 10, 22);
    ctx.strokeStyle = "rgba(245,196,81,0.45)";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(20, h * 0.72);
    ctx.lineTo(w / 2 - 20, h * 0.72);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(w / 2 + 10, h * 0.32);
    ctx.lineTo(w - 20, h * 0.32);
    ctx.stroke();
    ctx.setLineDash([]);
    // left sequence ending hammer
    const base = [
      [0.55, 0.5, 0.42, 0.6, true],
      [0.5, 0.48, 0.4, 0.58, false],
      [0.48, 0.52, 0.35, 0.7, true], // hammer: open/close high, long lower wick
    ];
    base.forEach((b, i) => {
      const x = 50 + i * 55;
      _lcandle(ctx, x, h * b[0], h * b[1], h * b[2], h * b[3], b[4]);
    });
    ctx.fillStyle = "#f5c451";
    ctx.fillText("support", 40, h * 0.72 + 14);
    // right shooting star
    const right = [
      [0.45, 0.5, 0.4, 0.55, true],
      [0.42, 0.38, 0.28, 0.5, true],
      [0.4, 0.48, 0.22, 0.5, false], // star
    ];
    right.forEach((b, i) => {
      const x = w / 2 + 50 + i * 55;
      _lcandle(ctx, x, h * b[0], h * b[1], h * b[2], h * b[3], b[4]);
    });
    ctx.fillStyle = "#f07178";
    ctx.fillText("resistance", w / 2 + 40, h * 0.32 - 8);
  }

  function drawLessonTrend(ctx, w, h) {
    const pts = [];
    for (let i = 0; i < 40; i++) {
      const wave = Math.sin(i / 4) * 12;
      pts.push(h * 0.7 - i * 2.2 + wave);
    }
    const sma50 = pts.map((p, i) => {
      const slice = pts.slice(Math.max(0, i - 8), i + 1);
      return slice.reduce((a, b) => a + b, 0) / slice.length + 8;
    });
    const sma200 = pts.map((_, i) => h * 0.78 - i * 1.4);
    const line = (arr, color, width = 1.5) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = width;
      ctx.beginPath();
      arr.forEach((y, i) => {
        const x = 20 + (i / (arr.length - 1)) * (w - 40);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    };
    line(sma200, "#c4b5fd", 1.5);
    line(sma50, "#f5c451", 1.5);
    line(pts, "#7dd3fc", 2);
    ctx.fillStyle = "#9aa8bc";
    ctx.font = "11px IBM Plex Mono, monospace";
    ctx.fillText("price", 24, 20);
    ctx.fillStyle = "#f5c451";
    ctx.fillText("SMA50", 80, 20);
    ctx.fillStyle = "#c4b5fd";
    ctx.fillText("SMA200", 140, 20);
    // mark pullback
    const i = 28;
    const x = 20 + (i / 39) * (w - 40);
    ctx.strokeStyle = "rgba(245,196,81,0.8)";
    ctx.beginPath();
    ctx.arc(x, pts[i], 6, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = "#f5c451";
    ctx.fillText("pullback", x + 10, pts[i] - 8);
  }

  function drawLessonRsi(ctx, w, h) {
    const mid = h * 0.42;
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.beginPath();
    ctx.moveTo(0, mid);
    ctx.lineTo(w, mid);
    ctx.stroke();
    // price declining
    ctx.strokeStyle = "#7dd3fc";
    ctx.beginPath();
    for (let i = 0; i < 50; i++) {
      const x = 20 + (i / 49) * (w - 40);
      const y = 30 + i * 1.6 + Math.sin(i / 3) * 6;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.fillStyle = "#9aa8bc";
    ctx.font = "11px IBM Plex Mono, monospace";
    ctx.fillText("price still lower", 24, 22);
    // RSI panel
    const top = mid + 10;
    const bot = h - 16;
    const yAt = (rsi) => top + ((100 - rsi) / 100) * (bot - top);
    ctx.strokeStyle = "rgba(240,113,120,0.35)";
    ctx.setLineDash([3, 3]);
    [30, 70].forEach((lvl) => {
      const y = yAt(lvl);
      ctx.beginPath();
      ctx.moveTo(20, y);
      ctx.lineTo(w - 20, y);
      ctx.stroke();
      ctx.fillStyle = "#9aa8bc";
      ctx.fillText(String(lvl), w - 36, y - 2);
    });
    ctx.setLineDash([]);
    ctx.strokeStyle = "#f5c451";
    ctx.beginPath();
    for (let i = 0; i < 50; i++) {
      const rsi = 28 + Math.sin(i / 2.5) * 8;
      const x = 20 + (i / 49) * (w - 40);
      const y = yAt(rsi);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.fillStyle = "#f5c451";
    ctx.fillText("RSI stuck ‘oversold’", 24, mid + 24);
  }

  function drawLessonRisk(ctx, w, h) {
    const y = h * 0.55;
    ctx.strokeStyle = "#7dd3fc";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(40, y + 30);
    ctx.lineTo(w * 0.35, y);
    ctx.lineTo(w * 0.55, y - 10);
    ctx.lineTo(w * 0.85, y - 50);
    ctx.stroke();
    const mark = (x, label, color, yy) => {
      ctx.strokeStyle = color;
      ctx.beginPath();
      ctx.moveTo(x, 40);
      ctx.lineTo(x, h - 30);
      ctx.stroke();
      ctx.fillStyle = color;
      ctx.font = "11px IBM Plex Mono, monospace";
      ctx.fillText(label, x + 4, yy);
    };
    mark(w * 0.35, "entry", "#7dd3fc", 36);
    mark(w * 0.28, "stop (−1R)", "#f07178", h - 18);
    mark(w * 0.75, "target (+2R)", "#f5c451", 36);
    ctx.fillStyle = "#9aa8bc";
    ctx.fillText("shares = risk$ / (entry − stop)", 40, h - 8);
  }

  function drawLessonChase(ctx, w, h) {
    ctx.strokeStyle = "#7dd3fc";
    ctx.lineWidth = 2;
    ctx.beginPath();
    const pts = [];
    for (let i = 0; i < 30; i++) {
      let y = h * 0.65 - i * 1.2;
      if (i > 18 && i < 24) y -= (i - 18) * 12; // spike
      if (i >= 24) y = h * 0.35 + (i - 24) * 8;
      pts.push(y);
      const x = 30 + (i / 29) * (w - 60);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.fillStyle = "#f07178";
    ctx.font = "11px IBM Plex Mono, monospace";
    ctx.fillText("chase zone", w * 0.55, h * 0.18);
    ctx.strokeStyle = "rgba(240,113,120,0.5)";
    ctx.strokeRect(w * 0.52, h * 0.12, w * 0.2, h * 0.2);
    ctx.fillStyle = "#f5c451";
    ctx.fillText("retest entry", w * 0.62, h * 0.48);
    ctx.beginPath();
    ctx.arc(30 + (26 / 29) * (w - 60), pts[26], 5, 0, Math.PI * 2);
    ctx.strokeStyle = "#f5c451";
    ctx.stroke();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = "rgba(245,196,81,0.5)";
    ctx.beginPath();
    ctx.moveTo(30, h * 0.42);
    ctx.lineTo(w - 30, h * 0.42);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#9aa8bc";
    ctx.fillText("breakout level", 34, h * 0.42 - 6);
  }

  function drawLessonLevels(ctx, w, h) {
    ctx.setLineDash([5, 4]);
    ctx.strokeStyle = "rgba(240,113,120,0.55)";
    ctx.beginPath();
    ctx.moveTo(30, h * 0.3);
    ctx.lineTo(w - 30, h * 0.3);
    ctx.stroke();
    ctx.strokeStyle = "rgba(125,211,252,0.55)";
    ctx.beginPath();
    ctx.moveTo(30, h * 0.7);
    ctx.lineTo(w - 30, h * 0.7);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#f07178";
    ctx.font = "11px IBM Plex Mono, monospace";
    ctx.fillText("resistance → broken", 36, h * 0.3 - 8);
    ctx.fillStyle = "#7dd3fc";
    ctx.fillText("support", 36, h * 0.7 + 14);
    ctx.strokeStyle = "#e8eef7";
    ctx.lineWidth = 2;
    ctx.beginPath();
    const path = [0.6, 0.55, 0.5, 0.35, 0.28, 0.32, 0.4, 0.38, 0.36, 0.33];
    path.forEach((p, i) => {
      const x = 40 + (i / (path.length - 1)) * (w - 80);
      const y = h * p;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    // fake wick
    ctx.strokeStyle = "#f07178";
    ctx.beginPath();
    ctx.moveTo(w * 0.78, h * 0.7);
    ctx.lineTo(w * 0.78, h * 0.82);
    ctx.stroke();
    ctx.fillText("liquidity grab", w * 0.7, h * 0.88);
    ctx.fillStyle = "#f5c451";
    ctx.fillText("retest as support", w * 0.45, h * 0.3 + 18);
  }

  function drawLessonVolume(ctx, w, h) {
    const mid = h * 0.45;
    ctx.strokeStyle = "#7dd3fc";
    ctx.beginPath();
    for (let i = 0; i < 36; i++) {
      const x = 20 + (i / 35) * (w - 40);
      let y = mid - i * 1.5;
      if (i === 22) y -= 25;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    const maxV = 1;
    for (let i = 0; i < 36; i++) {
      let v = 0.25 + (i % 5) * 0.05;
      if (i === 22) v = 1;
      if (i > 22 && i < 28) v = 0.2;
      const x = 20 + (i / 35) * (w - 40);
      const bh = v * (h - mid - 20);
      ctx.fillStyle = i === 22 ? "rgba(245,196,81,0.75)" : "rgba(125,211,252,0.35)";
      ctx.fillRect(x - 3, h - 12 - bh, 6, bh);
    }
    ctx.fillStyle = "#f5c451";
    ctx.font = "11px IBM Plex Mono, monospace";
    ctx.fillText("volume confirms break", w * 0.45, 24);
  }

  function drawLessonStops(ctx, w, h) {
    drawLessonRisk(ctx, w, h);
    ctx.fillStyle = "#9aa8bc";
    ctx.font = "11px IBM Plex Mono, monospace";
    ctx.fillText("stop under swing low = invalidation", 40, 28);
  }

  function drawLessonMacdEdu(ctx, w, h) {
    const mid = h / 2;
    ctx.strokeStyle = "rgba(255,255,255,0.1)";
    ctx.beginPath();
    ctx.moveTo(0, mid);
    ctx.lineTo(w, mid);
    ctx.stroke();
    for (let i = 0; i < 40; i++) {
      const hist = Math.sin(i / 3.5) * 28;
      const x = 20 + (i / 39) * (w - 40);
      ctx.fillStyle = hist >= 0 ? "rgba(125,211,252,0.55)" : "rgba(240,113,120,0.55)";
      ctx.fillRect(x - 3, mid - Math.max(0, hist), 6, Math.abs(hist));
    }
    ctx.strokeStyle = "#f5c451";
    ctx.beginPath();
    for (let i = 0; i < 40; i++) {
      const y = mid - Math.sin(i / 3.5) * 40 - 8;
      const x = 20 + (i / 39) * (w - 40);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.strokeStyle = "#c4b5fd";
    ctx.beginPath();
    for (let i = 0; i < 40; i++) {
      const y = mid - Math.sin(i / 3.5 - 0.4) * 40;
      const x = 20 + (i / 39) * (w - 40);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.fillStyle = "#9aa8bc";
    ctx.font = "11px IBM Plex Mono, monospace";
    ctx.fillText("MACD (amber) vs signal (violet) + histogram", 24, 20);
  }

  function drawLessonPlaybook(ctx, w, h) {
    const steps = ["Scan", "Chart", "Lesson", "Risk", "Ticket"];
    const gap = (w - 60) / steps.length;
    steps.forEach((s, i) => {
      const x = 30 + i * gap + gap / 2;
      const y = h / 2;
      ctx.fillStyle = i === 2 ? "rgba(245,196,81,0.25)" : "rgba(125,211,252,0.12)";
      ctx.strokeStyle = i === 2 ? "#f5c451" : "#7dd3fc";
      ctx.beginPath();
      ctx.arc(x, y, 34, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = "#e8eef7";
      ctx.font = "12px Sora, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(s, x, y + 4);
      if (i < steps.length - 1) {
        ctx.strokeStyle = "rgba(255,255,255,0.2)";
        ctx.beginPath();
        ctx.moveTo(x + 36, y);
        ctx.lineTo(x + gap - 36, y);
        ctx.stroke();
      }
    });
    ctx.textAlign = "left";
    ctx.fillStyle = "#9aa8bc";
    ctx.font = "11px IBM Plex Mono, monospace";
    ctx.fillText("Skip a box → playbook breaks", 30, h - 16);
  }

  async function loadBrokers() {
    try {
      const brokers = await api("/api/brokers");
      $("brokers-box").innerHTML = brokers
        .map(
          (b) => `<div class="lesson">
          <h3>#${b.rank} ${escapeHtml(b.name)}</h3>
          <p>speed ${b.speed}/10 · reliability ${b.reliability}/10<br/>${escapeHtml(b.cost)}</p>
        </div>`
        )
        .join("");
    } catch (e) {
      $("brokers-box").innerHTML = `<div class="banner error">${escapeHtml(e.message)}</div>`;
    }
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function secretLabel(el, info) {
    if (!el) return;
    if (info?.configured) {
      el.textContent = `set · ${info.masked || "••••"}`;
      el.className = "secret-status configured";
    } else {
      el.textContent = "not set";
      el.className = "secret-status";
    }
  }

  async function openKeysModal() {
    const s = await api("/api/settings");
    $("set-broker").value = s.broker || "paper";
    $("set-data").value = s.data_provider || "yahoo";
    $("set-alpaca-paper").checked = !!s.flags?.ALPACA_PAPER;
    $("set-tradier-sandbox").checked = !!s.flags?.TRADIER_SANDBOX;
    // Never echo secrets/account IDs into inputs — paste only to update
    [
      "set-alpaca-key",
      "set-alpaca-secret",
      "set-public-secret",
      "set-public-acct",
      "set-tradier-token",
      "set-tradier-acct",
      "set-finnhub",
      "set-av",
    ].forEach((id) => {
      if ($(id)) $(id).value = "";
    });
    secretLabel($("st-alpaca-key"), s.secrets?.ALPACA_API_KEY);
    secretLabel($("st-alpaca-secret"), s.secrets?.ALPACA_API_SECRET);
    secretLabel($("st-public"), s.secrets?.PUBLIC_PERSONAL_SECRET);
    secretLabel($("st-public-acct"), s.secrets?.PUBLIC_ACCOUNT_ID);
    secretLabel($("st-tradier"), s.secrets?.TRADIER_ACCESS_TOKEN);
    secretLabel($("st-tradier-acct"), s.secrets?.TRADIER_ACCOUNT_ID);
    secretLabel($("st-finnhub"), s.secrets?.FINNHUB_API_KEY);
    secretLabel($("st-av"), s.secrets?.ALPHAVANTAGE_API_KEY);
    $("keys-banner").hidden = true;
    $("keys-modal").classList.add("open");
  }

  function closeKeysModal() {
    $("keys-modal").classList.remove("open");
  }

  async function saveKeys() {
    const payload = {
      broker: $("set-broker").value,
      data_provider: $("set-data").value,
      alpaca_paper: $("set-alpaca-paper").checked,
      tradier_sandbox: $("set-tradier-sandbox").checked,
    };
    const maybe = (id, key) => {
      const v = $(id).value.trim();
      // Never submit mask placeholders
      if (v && !v.includes("•")) payload[key] = v;
    };
    maybe("set-alpaca-key", "alpaca_api_key");
    maybe("set-alpaca-secret", "alpaca_api_secret");
    maybe("set-public-secret", "public_personal_secret");
    maybe("set-public-acct", "public_account_id");
    maybe("set-tradier-token", "tradier_access_token");
    maybe("set-tradier-acct", "tradier_account_id");
    maybe("set-finnhub", "finnhub_api_key");
    maybe("set-av", "alphavantage_api_key");

    try {
      await api("/api/settings", { method: "PUT", body: JSON.stringify(payload) });
      const banner = $("keys-banner");
      banner.hidden = false;
      banner.className = "banner ok";
      banner.textContent = "Saved. Provider cache reloaded.";
      toast("Settings saved");
      await loadHealth();
      await loadAccount();
      closeKeysModal();
    } catch (e) {
      const banner = $("keys-banner");
      banner.hidden = false;
      banner.className = "banner error";
      banner.textContent = e.message;
    }
  }

  async function addWatch() {
    const err = $("watch-error");
    err.hidden = true;
    const symbol = normalizeSymbol($("watch-input").value);
    if (!symbol) {
      err.hidden = false;
      err.textContent = "Enter a ticker symbol";
      return;
    }
    try {
      await api("/api/watchlist", {
        method: "POST",
        body: JSON.stringify({ symbol }),
      });
      $("watch-input").value = "";
      toast(`Tracking ${symbol}`);
      await refreshMarket();
      selectSymbol(symbol);
    } catch (e) {
      err.hidden = false;
      err.textContent = e.message;
    }
  }

  function buildOrderBody() {
    const symbol = normalizeSymbol($("ord-symbol").value);
    const qty = Number($("ord-qty").value);
    const order_type = $("ord-type")?.value || "market";
    const numOrNull = (id) => {
      const v = $(id)?.value;
      if (v == null || v === "") return null;
      const n = Number(v);
      return Number.isNaN(n) ? NaN : n;
    };
    const limit_price = numOrNull("ord-limit");
    const stopEntry = numOrNull("ord-stop-entry");
    const stopLoss = numOrNull("ord-stop");
    const take_profit = numOrNull("ord-tp");
    // Market brackets use protective stop; stop/stop_limit use stop entry price
    const stop_price =
      order_type === "market" || order_type === "limit" ? stopLoss : stopEntry ?? stopLoss;
    return {
      symbol,
      side: $("ord-side").value,
      qty,
      order_type,
      limit_price,
      stop_price,
      take_profit,
    };
  }

  async function previewOrder() {
    const banner = $("order-banner");
    banner.hidden = true;
    const body = buildOrderBody();
    if (!body.symbol) {
      banner.hidden = false;
      banner.className = "banner error";
      banner.textContent = "Symbol required";
      return;
    }
    if (!(body.qty > 0) || Number.isNaN(body.qty)) {
      banner.hidden = false;
      banner.className = "banner error";
      banner.textContent = "Quantity must be a positive number";
      return;
    }
    for (const k of ["limit_price", "stop_price", "take_profit"]) {
      if (body[k] != null && Number.isNaN(body[k])) {
        banner.hidden = false;
        banner.className = "banner error";
        banner.textContent = `${k} is not a valid number`;
        return;
      }
    }
    try {
      const p = await api("/api/orders/preview", {
        method: "POST",
        body: JSON.stringify(body),
      });
      $("order-checklist").innerHTML = (p.checklist || [])
        .map((c) => `<li>${escapeHtml(c)}</li>`)
        .join("");
      banner.hidden = false;
      if (!p.allowed) {
        banner.className = "banner error";
        banner.textContent = (p.blockers || []).join("; ") || "Blocked";
      } else if (p.warnings?.length) {
        banner.className = "banner warn";
        banner.textContent = `OK with warnings: ${p.warnings.join("; ")} · last ${fmtPx(p.last)} · ${p.order_type || body.order_type}`;
      } else {
        banner.className = "banner ok";
        banner.textContent = `Risk OK · ${p.order_type || body.order_type} · last ${fmtPx(p.last)}${p.live ? " · LIVE MODE" : ""}`;
      }
      return p;
    } catch (e) {
      banner.hidden = false;
      banner.className = "banner error";
      banner.textContent = e.message;
      return null;
    }
  }

  async function submitOrder() {
    const p = await previewOrder();
    if (!p?.allowed) return;
    if (p.live && !confirm("This is LIVE trading mode. Submit real order?")) return;
    try {
      const body = buildOrderBody();
      const result = await api("/api/orders", {
        method: "POST",
        body: JSON.stringify(body),
      });
      toast(`Order submitted: ${JSON.stringify(result)}`);
      await Promise.all([loadAccount(), loadOrders()]);
    } catch (e) {
      const banner = $("order-banner");
      banner.hidden = false;
      banner.className = "banner error";
      banner.textContent = e.message;
    }
  }

  async function processStops() {
    try {
      const data = await api("/api/orders/process-stops", { method: "POST", body: "{}" });
      toast(`Triggered ${data.triggered} stop(s)`);
      await Promise.all([loadAccount(), loadOrders()]);
    } catch (e) {
      toast(e.message);
    }
  }

  async function runBacktest() {
    const symbol = normalizeSymbol($("bt-symbol").value);
    const start = $("bt-start").value;
    const end = $("bt-end").value;
    const box = $("bt-result");
    if (!symbol || !start || !end) {
      box.textContent = "Symbol, start, and end are required";
      return;
    }
    if (start > end) {
      box.textContent = "Start date must be before end date";
      return;
    }
    box.textContent = "Running…";
    try {
      const r = await api(
        `/api/backtest/${encodeURIComponent(symbol)}?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`
      );
      box.innerHTML = `<strong class="mono">${escapeHtml(r.symbol)}</strong><br/>
        Return <span class="${pctClass(r.total_return_pct)}">${fmtPct(r.total_return_pct)}</span><br/>
        Max DD <span class="down">${fmtPct(r.max_drawdown_pct)}</span><br/>
        Trades: ${r.trades}`;
    } catch (e) {
      box.textContent = e.message;
    }
  }

  function fmtVol(v) {
    if (v == null || Number.isNaN(Number(v))) return "—";
    const n = Number(v);
    if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
    if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
    if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
    return String(Math.round(n));
  }

  async function loadUniverseStatus() {
    const st = await api("/api/universe/status");
    const worker = st.worker?.running ? "engine on" : "engine off";
    const err = st.worker?.last_error ? ` · ${st.worker.last_error}` : "";
    $("universe-stats").textContent =
      `${st.total?.toLocaleString?.() ?? st.total} listed · ${st.quoted?.toLocaleString?.() ?? st.quoted} quoted · ${worker}${err}`;
    if (st.listings_as_of || st.quotes_as_of) {
      const bits = [];
      if (st.listings_as_of) bits.push(`listings ${new Date(st.listings_as_of).toLocaleString()}`);
      if (st.quotes_as_of) bits.push(`quotes ${new Date(st.quotes_as_of).toLocaleString()}`);
      $("universe-asof").textContent = bits.join(" · ");
    }
    return st;
  }

  async function loadUniverse(opts = {}) {
    const errEl = $("universe-error");
    if (errEl) errEl.hidden = true;
    if (opts.reset) state.universeOffset = 0;
    const q = ($("universe-q")?.value || "").trim();
    const exchange = $("universe-exchange")?.value || "";
    const assetClass = $("universe-class")?.value || "";
    const hasQuote = $("universe-quoted-only")?.checked ? "true" : "";
    const params = new URLSearchParams({
      limit: String(state.universeLimit),
      offset: String(state.universeOffset),
    });
    if (q) params.set("q", q);
    if (exchange) params.set("exchange", exchange);
    if (assetClass) params.set("asset_class", assetClass);
    if (hasQuote) params.set("has_quote", hasQuote);

    const body = $("universe-body");
    if (body && !opts.silent) {
      body.innerHTML = `<tr><td colspan="7"><div class="skeleton"></div></td></tr>`;
    }
    try {
      const [data] = await Promise.all([
        api(`/api/universe?${params}`),
        loadUniverseStatus().catch(() => null),
      ]);
      state.universeTotal = data.total || 0;
      const items = data.items || [];
      $("universe-page").textContent = state.universeTotal
        ? `${state.universeOffset + 1}–${Math.min(state.universeOffset + items.length, state.universeTotal)} of ${state.universeTotal.toLocaleString()}`
        : "0 symbols";
      if (!items.length) {
        body.innerHTML = `<tr><td colspan="7"><div class="empty">No symbols match — sync listings if the universe is empty.</div></td></tr>`;
        return;
      }
      body.innerHTML = items
        .map((row) => {
          const name = (row.name || "").slice(0, 42);
          return `<tr data-symbol="${escapeHtml(row.symbol)}" class="${state.selected === row.symbol ? "selected" : ""}">
            <td class="sym-cell mono">${escapeHtml(row.symbol)}</td>
            <td title="${escapeHtml(row.name || "")}">${escapeHtml(name)}</td>
            <td class="muted">${escapeHtml(row.exchange || "—")}</td>
            <td class="mono">${row.price != null ? fmtPx(row.price) : "—"}</td>
            <td class="mono ${pctClass(row.change_pct_day)}">${row.change_pct_day != null ? fmtPct(row.change_pct_day) : "—"}</td>
            <td class="mono muted">${fmtVol(row.volume)}</td>
            <td><button type="button" class="btn ghost btn-xs" data-track="${escapeHtml(row.symbol)}">Track</button></td>
          </tr>`;
        })
        .join("");
      body.querySelectorAll("tr[data-symbol]").forEach((tr) => {
        tr.addEventListener("click", (ev) => {
          if (ev.target.closest("[data-track]")) return;
          selectSymbol(tr.dataset.symbol, { goDetail: true });
        });
      });
      body.querySelectorAll("[data-track]").forEach((btn) => {
        btn.addEventListener("click", async (ev) => {
          ev.stopPropagation();
          try {
            await api("/api/watchlist", {
              method: "POST",
              body: JSON.stringify({ symbol: btn.dataset.track }),
            });
            toast(`Tracking ${btn.dataset.track}`);
            await loadWatchlist();
          } catch (e) {
            toast(e.message);
          }
        });
      });
    } catch (e) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = e.message;
      }
      if (body) body.innerHTML = `<tr><td colspan="7"><div class="banner error">${escapeHtml(e.message)}</div></td></tr>`;
    }
  }

  async function refreshMarket() {
    await Promise.all([
      loadWatchlist(),
      loadTracked(),
      loadHighlights(),
      loadUniverse({ silent: true }).catch(() => {}),
      loadAccount(),
      loadOrders(),
    ]);
  }

  function setDefaultDates() {
    const end = new Date();
    const start = new Date();
    start.setFullYear(end.getFullYear() - 1);
    $("bt-end").value = end.toISOString().slice(0, 10);
    $("bt-start").value = start.toISOString().slice(0, 10);
  }

  function setupAutoRefresh() {
    if (state.refreshTimer) {
      clearInterval(state.refreshTimer);
      state.refreshTimer = null;
    }
    if ($("auto-refresh")?.checked) {
      state.refreshTimer = setInterval(() => {
        // Quiet refresh — skip toast noise
        loadHealth().catch(() => {});
        refreshMarket().catch(() => {});
      }, 60000);
    }
  }

  function bind() {
    $("btn-refresh").addEventListener("click", async () => {
      try {
        await loadHealth();
        await refreshMarket();
        toast("Dashboard refreshed");
      } catch (e) {
        toast(e.message);
      }
    });
    $("btn-scan")?.addEventListener("click", () => runScan({ goScanner: true }));
    $("btn-hunt")?.addEventListener("click", () => huntTrades());
    $("btn-assistant-hunt")?.addEventListener("click", () => huntTrades());
    $("btn-assistant-send")?.addEventListener("click", () =>
      sendAssistant($("assistant-input").value, false)
    );
    $("btn-assistant-shot")?.addEventListener("click", () => {
      const msg = $("assistant-input").value.trim() || "Review this desk screenshot and suggest the best careful trade.";
      sendAssistant(msg, true);
    });
    $("assistant-input")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendAssistant($("assistant-input").value, false);
    });
    $("auto-hunt")?.addEventListener("change", setupAutoHunt);
    $("btn-orders-refresh")?.addEventListener("click", () => loadOrders());
    $("btn-process-stops")?.addEventListener("click", () => processStops());
    $("auto-refresh")?.addEventListener("change", setupAutoRefresh);
    $("btn-tour")?.addEventListener("click", () => startTour());
    $("btn-tour-sidebar")?.addEventListener("click", () => startTour());
    $("btn-tour-next")?.addEventListener("click", () => tourNext());
    $("btn-tour-back")?.addEventListener("click", () => tourBack());
    $("btn-tour-done")?.addEventListener("click", () => endTour());
    $("btn-coach-stop")?.addEventListener("click", () => endCoach());
    $("btn-coach-dismiss")?.addEventListener("click", () => endCoach());
    $("btn-coach-skip")?.addEventListener("click", () => endCoach());
    $("btn-coach-next")?.addEventListener("click", () => coachNext());
    window.addEventListener("resize", () => {
      if (coachState.active && coachState.steps[coachState.index]) {
        positionCoachUI(coachState.steps[coachState.index]);
      }
    });
    $("btn-keys").addEventListener("click", () =>
      openKeysModal()
        .then(() => Promise.all([loadKeyLinks(), showMissingKeys()]))
        .catch((e) => toast(e.message))
    );
    $("btn-keys-close").addEventListener("click", closeKeysModal);
    $("btn-keys-cancel").addEventListener("click", closeKeysModal);
    $("btn-keys-save").addEventListener("click", saveKeys);
    $("keys-modal").addEventListener("click", (e) => {
      if (e.target === $("keys-modal")) closeKeysModal();
    });
    $("btn-lesson-close")?.addEventListener("click", closeLessonModal);
    $("btn-lesson-prev")?.addEventListener("click", () => stepLesson(-1));
    $("btn-lesson-next")?.addEventListener("click", () => stepLesson(1));
    $("btn-page-prev")?.addEventListener("click", () => stepPage(-1));
    $("btn-page-next")?.addEventListener("click", () => stepPage(1));
    $("btn-start-tutor")?.addEventListener("click", () => openLesson("ways_to_trade", 0));
    $("btn-tutor-continue")?.addEventListener("click", () => {
      let p = 0;
      try {
        p = Number(localStorage.getItem("infobroker_tutor_page") || "0") || 0;
      } catch {
        p = 0;
      }
      openLesson("ways_to_trade", p);
    });
    $("btn-refresh-stories")?.addEventListener("click", () => loadTradeStories());
    $("lesson-modal")?.addEventListener("click", (e) => {
      if (e.target === $("lesson-modal")) closeLessonModal();
    });
    document.addEventListener("keydown", (e) => {
      if (tourState.active) {
        if (e.key === "Escape") {
          e.preventDefault();
          endTour();
          return;
        }
        if (e.key === "ArrowRight" || e.key === "Enter") {
          e.preventDefault();
          tourNext();
          return;
        }
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          tourBack();
          return;
        }
      }
      if (e.key === "Escape") {
        closeLessonModal();
        closeKeysModal();
      }
      if ($("lesson-modal")?.classList.contains("open")) {
        if (e.key === "ArrowLeft") stepPage(-1);
        if (e.key === "ArrowRight") stepPage(1);
      }
    });
    window.addEventListener("resize", () => {
      if (tourState.active) positionTourUI();
    });
    window.addEventListener(
      "scroll",
      () => {
        if (tourState.active) positionTourUI();
      },
      true
    );

    $("btn-watch-add").addEventListener("click", addWatch);
    $("watch-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") addWatch();
    });
    $("watch-input").addEventListener("input", () => {
      const err = $("watch-error");
      if (err) err.hidden = true;
    });

    $("btn-preview").addEventListener("click", previewOrder);
    $("btn-submit").addEventListener("click", submitOrder);
    $("btn-backtest").addEventListener("click", runBacktest);
    $("btn-trade-selected")?.addEventListener("click", () => {
      if (!state.selected) return;
      $("ord-symbol").value = state.selected;
      $("ord-side").value = "buy";
      toast(`Buy ticket loaded for ${state.selected}`);
    });
    $("chart-mode-line")?.addEventListener("click", () => {
      state.chartMode = "line";
      $("chart-mode-line").classList.add("active");
      $("chart-mode-candle").classList.remove("active");
      renderDetailChart();
    });
    $("chart-mode-candle")?.addEventListener("click", () => {
      state.chartMode = "candle";
      $("chart-mode-candle").classList.add("active");
      $("chart-mode-line").classList.remove("active");
      renderDetailChart();
    });
    $("btn-detail-reset-zoom")?.addEventListener("click", () => {
      state.detailCtrl?.resetView();
      renderDetailChart();
    });
    document.querySelectorAll("[data-detail-tool]").forEach((btn) => {
      btn.addEventListener("click", () => setDetailTool(btn.dataset.detailTool));
    });
    $("btn-detail-undo-draw")?.addEventListener("click", () => {
      ensureDetailController()?.undoDrawing();
    });
    $("btn-detail-clear-draw")?.addEventListener("click", () => {
      ensureDetailController()?.clearDrawings();
      toast("Cleared chart lines");
    });
    $("btn-cs-reset-zoom")?.addEventListener("click", () => {
      state.studioCtrl?.resetView();
      renderChartStudio();
    });
    document.querySelectorAll("[data-cs-tool]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tool = btn.dataset.csTool;
        ensureStudioController()?.setTool(tool);
        document.querySelectorAll("[data-cs-tool]").forEach((b) => {
          b.classList.toggle("active", b.dataset.csTool === tool);
        });
      });
    });
    $("btn-cs-undo-draw")?.addEventListener("click", () => ensureStudioController()?.undoDrawing());
    $("btn-cs-clear-draw")?.addEventListener("click", () => {
      ensureStudioController()?.clearDrawings();
      toast("Cleared chart lines");
    });
    $("btn-live-refresh")?.addEventListener("click", () => loadLiveBoard({ forceRefresh: true }));
    $("btn-live-fill")?.addEventListener("click", () => fillLiveQuotes());
    $("live-chart-tf")?.addEventListener("change", () => {
      state.liveChartTf = $("live-chart-tf").value || "live1m";
      if (state.liveSymbol) openLiveChart(state.liveSymbol);
    });
    $("live-stream")?.addEventListener("change", () => {
      if ($("live-stream").checked && state.liveSymbol) startLiveTickStream(state.liveSymbol);
      else stopLiveTickStream();
    });
    $("live-mode")?.addEventListener("change", () => {
      startLivePoll();
      loadLiveBoard({ forceRefresh: true });
    });
    $("live-class")?.addEventListener("change", () => {
      startLivePoll();
      loadLiveBoard({ forceRefresh: true });
    });
    $("live-sort")?.addEventListener("change", () => {
      if ((state.liveMarketFocus || "us") !== "us") {
        loadLiveBoard({ quiet: true });
      } else {
        applyLiveSortAndRender();
      }
    });
    $("live-view")?.addEventListener("change", () => {
      renderLiveBoardView(state.liveItems || [], state.liveMeta || {});
    });
    $("live-mkt-pills")?.addEventListener("click", (ev) => {
      const btn = ev.target.closest("[data-mkt-focus]");
      if (!btn) return;
      setLiveMarketFocus(btn.dataset.mktFocus);
    });
    $("live-auto")?.addEventListener("change", () => {
      if ($("live-auto").checked) startLivePoll();
      else stopLivePoll();
    });
    $("btn-portfolio-refresh")?.addEventListener("click", () => {
      loadPortfolio().catch((e) => toast(e.message));
      loadAutoTrack().catch(() => {});
    });
    $("btn-trading-refresh")?.addEventListener("click", () => loadTradingBoard());
    $("tr-scope")?.addEventListener("change", () => loadTradingBoard());
    $("btn-tr-clear-log")?.addEventListener("click", () => {
      state.tradingActivity = [];
      renderTradingActivity();
    });
    $("btn-at-save")?.addEventListener("click", () => saveAutoTrack());
    $("btn-at-scan")?.addEventListener("click", () => runAutoTrackScan());
    document.querySelectorAll("[data-live-tool]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tool = btn.dataset.liveTool;
        ensureLiveChartController()?.setTool(tool);
        document.querySelectorAll("[data-live-tool]").forEach((b) => {
          b.classList.toggle("active", b.dataset.liveTool === tool);
        });
      });
    });
    $("btn-live-undo-draw")?.addEventListener("click", () => {
      ensureLiveChartController()?.undoDrawing();
    });
    $("btn-live-clear-draw")?.addEventListener("click", () => {
      ensureLiveChartController()?.clearDrawings();
      toast("Cleared chart lines");
    });

    document.querySelectorAll("[data-day-tab]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.dayTab = btn.dataset.dayTab;
        document.querySelectorAll("[data-day-tab]").forEach((b) => b.classList.toggle("active", b === btn));
        renderDayWeek();
      });
    });
    document.querySelectorAll("[data-week-tab]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.weekTab = btn.dataset.weekTab;
        document.querySelectorAll("[data-week-tab]").forEach((b) => b.classList.toggle("active", b === btn));
        renderDayWeek();
      });
    });

    document.querySelectorAll("[data-desk-tab]").forEach((btn) => {
      btn.addEventListener("click", () => switchDeskTab(btn.dataset.deskTab));
    });
    document.querySelectorAll("[data-subtab-group]").forEach((nav) => {
      nav.querySelectorAll("[data-sub-tab]").forEach((btn) => {
        btn.addEventListener("click", () => switchSubTab(nav.dataset.subtabGroup, btn.dataset.subTab));
      });
    });
    $("btn-goto-learning")?.addEventListener("click", () => switchDeskTab("learning", "tutor"));
    $("btn-goto-tutor")?.addEventListener("click", () => {
      switchDeskTab("learning", "tutor");
      openLesson("ways_to_trade", 0);
    });
    $("btn-symbol-to-charts")?.addEventListener("click", () => {
      if (state.selected) $("cs-symbol").value = state.selected;
      switchDeskTab("charts");
    });
    $("btn-strategy-run")?.addEventListener("click", runStrategyBacktest);
    $("btn-chart-pack")?.addEventListener("click", loadChartStudio);
    $("btn-ollama-status")?.addEventListener("click", () => ollamaAction("status"));
    $("btn-ollama-warm")?.addEventListener("click", () => ollamaAction("warm"));
    $("btn-ollama-unload")?.addEventListener("click", () => ollamaAction("unload"));
    $("btn-ollama-models")?.addEventListener("click", () => ollamaAction("list_models"));
    $("btn-mcp-start")?.addEventListener("click", () => mcpAction("start"));
    $("btn-mcp-stop")?.addEventListener("click", () => mcpAction("stop"));
    $("btn-mcp-restart")?.addEventListener("click", () => mcpAction("restart"));
    $("btn-mcp-status")?.addEventListener("click", () => mcpAction("status"));
    $("btn-asst-ollama-warm")?.addEventListener("click", () => ollamaAction("warm"));
    $("btn-asst-mcp-restart")?.addEventListener("click", () => mcpAction("restart"));
    $("btn-asst-goto-services")?.addEventListener("click", () => switchDeskTab("services", "ollama"));
    $("btn-settings")?.addEventListener("click", () => switchDeskTab("settings", "docs"));
    $("btn-settings-keys")?.addEventListener("click", () =>
      openKeysModal()
        .then(() => Promise.all([loadKeyLinks(), showMissingKeys()]))
        .catch((e) => toast(e.message))
    );
    $("btn-settings-services")?.addEventListener("click", () => switchDeskTab("services", "ollama"));
    $("btn-settings-data-doc")?.addEventListener("click", () => {
      switchDeskTab("settings", "docs");
      openDoc("data-pipeline").catch((e) => toast(e.message));
    });
    $("btn-settings-refresh-health")?.addEventListener("click", () => loadSettingsAbout());
    $("assistant-chat")?.querySelectorAll("[data-followup]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const q = btn.getAttribute("data-followup") || btn.textContent;
        clearFollowups();
        sendAssistant(q, false);
      });
    });
    $("btn-open-keys-from-svc")?.addEventListener("click", () =>
      openKeysModal()
        .then(() => Promise.all([loadKeyLinks(), showMissingKeys(), loadAcquireKeys()]))
        .catch((e) => toast(e.message))
    );

    $("btn-universe-search")?.addEventListener("click", () => loadUniverse({ reset: true }));
    $("universe-q")?.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") loadUniverse({ reset: true });
    });
    $("universe-exchange")?.addEventListener("change", () => loadUniverse({ reset: true }));
    $("universe-class")?.addEventListener("change", () => loadUniverse({ reset: true }));
    $("universe-quoted-only")?.addEventListener("change", () => loadUniverse({ reset: true }));
    $("btn-universe-prev")?.addEventListener("click", () => {
      state.universeOffset = Math.max(0, state.universeOffset - state.universeLimit);
      loadUniverse();
    });
    $("btn-universe-next")?.addEventListener("click", () => {
      if (state.universeOffset + state.universeLimit < state.universeTotal) {
        state.universeOffset += state.universeLimit;
        loadUniverse();
      }
    });
    $("btn-universe-listings")?.addEventListener("click", async () => {
      toast("Syncing exchange listings…");
      try {
        const r = await api("/api/universe/refresh-listings", { method: "POST" });
        toast(`Listings: ${(r.count || 0).toLocaleString()} symbols`);
        await loadUniverse({ reset: true });
      } catch (e) {
        toast(e.message);
      }
    });
    $("btn-universe-quotes")?.addEventListener("click", async () => {
      toast("Refreshing quote batch…");
      try {
        const r = await api("/api/universe/refresh-quotes?batch=120", { method: "POST" });
        toast(`Quotes updated ${r.updated}/${r.batch_size} · cache ${r.quoted}/${r.total}`);
        await loadUniverse();
      } catch (e) {
        toast(e.message);
      }
    });
    $("btn-scan-here")?.addEventListener("click", () => runScan({ goScanner: true }));
    document.querySelectorAll('input[name="scan-scope"]').forEach((el) => {
      el.addEventListener("change", () => {
        state.scanScope = el.value;
      });
    });
  }

  function setLiveFocus(on) {
    document.body.classList.toggle("live-focus", !!on);
  }

  function switchSubTab(group, name) {
    const nav = document.querySelector(`[data-subtab-group="${group}"]`);
    if (!nav) return;
    nav.querySelectorAll("[data-sub-tab]").forEach((b) => {
      b.classList.toggle("active", b.dataset.subTab === name);
    });
    document.querySelectorAll(`[data-sub-panel^="${group}-"]`).forEach((panel) => {
      const key = panel.dataset.subPanel.slice(group.length + 1);
      panel.hidden = key !== name;
    });
    try {
      localStorage.setItem(`infobroker_subtab_${group}`, name);
    } catch {
      /* ignore */
    }
    if (group === "learning" && name === "journal") {
      loadTradeStories().catch(() => {});
    }
    if (group === "markets" && name === "universe") {
      loadUniverse().catch(() => {});
    }
    if (group === "markets" && name === "live") {
      setLiveFocus(true);
      loadLiveBoard().catch(() => {});
      startLivePoll();
      if (state.liveSymbol && $("live-stream")?.checked) startLiveTickStream(state.liveSymbol);
    } else if (group === "markets") {
      setLiveFocus(false);
      stopLivePoll();
      stopLiveTickStream();
    }
    if (group === "settings" && name === "docs") {
      loadDocsNav().catch(() => {});
    }
    if (group === "settings" && name === "about") {
      loadSettingsAbout().catch(() => {});
    }
  }

  function switchDeskTab(name, sub) {
    document.querySelectorAll("[data-desk-tab]").forEach((b) => {
      b.classList.toggle("active", b.dataset.deskTab === name);
    });
    ["markets", "trading", "portfolio", "learning", "strategies", "charts", "services", "settings"].forEach((id) => {
      const el = $(`tab-${id}`);
      if (el) el.hidden = id !== name;
    });
    const defaults = { markets: "live", learning: "tutor", services: "ollama", settings: "docs" };
    let subName = sub;
    if (!subName && defaults[name]) {
      try {
        subName = localStorage.getItem(`infobroker_subtab_${name}`) || defaults[name];
      } catch {
        subName = defaults[name];
      }
    }
    if (subName && defaults[name]) switchSubTab(name, subName);
    if (name === "strategies") loadStrategies().catch(() => {});
    if (name === "learning") {
      loadLessons().catch(() => {});
      if (subName === "journal") loadTradeStories().catch(() => {});
    }
    if (name === "services") {
      loadAcquireKeys().catch(() => {});
      loadHealth().catch(() => {});
    }
    if (name === "settings") {
      if ((subName || "docs") === "docs") loadDocsNav().catch(() => {});
      if (subName === "about") loadSettingsAbout().catch(() => {});
    }
    if (name === "portfolio") {
      loadPortfolio().catch(() => {});
      loadAutoTrack().catch(() => {});
    }
    if (name === "trading") {
      loadTradingBoard().catch(() => {});
    }
    if (name === "charts" && state.selected) {
      $("cs-symbol").value = state.selected;
    }
    if (name !== "markets") {
      stopLivePoll();
      setLiveFocus(false);
    } else {
      setLiveFocus(subName === "live");
    }
  }

  function renderTradingActivity() {
    const box = $("tr-activity");
    if (!box) return;
    const rows = state.tradingActivity || [];
    if (!rows.length) {
      box.innerHTML = `<div class="empty">No portfolio changes yet</div>`;
      return;
    }
    box.innerHTML = rows
      .slice(0, 40)
      .map(
        (a) => `<div class="tr-activity-item ${escapeHtml(a.kind)}">
          <strong class="mono">${escapeHtml(a.symbol)}</strong>
          <span>${escapeHtml(a.text)}</span>
          <div class="mono muted">${escapeHtml(a.at)}</div>
        </div>`
      )
      .join("");
  }

  function pushTradingActivity(kind, symbol, text) {
    state.tradingActivity = [
      {
        kind,
        symbol,
        text,
        at: new Date().toLocaleTimeString(),
      },
      ...(state.tradingActivity || []),
    ].slice(0, 80);
    renderTradingActivity();
  }

  function diffTradingPositions(nextMap) {
    const prev = state.tradingPosSnapshot || {};
    const syms = new Set([...Object.keys(prev), ...Object.keys(nextMap || {})]);
    for (const sym of syms) {
      const a = Number(prev[sym] || 0);
      const b = Number((nextMap || {})[sym] || 0);
      if (a === b) continue;
      if (a <= 0 && b > 0) pushTradingActivity("add", sym, `Opened position · ${b} shares`);
      else if (a > 0 && b <= 0) pushTradingActivity("remove", sym, `Closed position · was ${a} shares`);
      else if (b > a) pushTradingActivity("change", sym, `Added · ${a} → ${b} shares`);
      else pushTradingActivity("change", sym, `Reduced · ${a} → ${b} shares`);
    }
    state.tradingPosSnapshot = { ...(nextMap || {}) };
  }

  function renderTradingBoard(items) {
    const tbody = $("tr-body");
    if (!tbody) return;
    if (!items.length) {
      tbody.innerHTML = `<tr><td colspan="8"><div class="empty">No symbols — add to watchlist or wait for live quotes.</div></td></tr>`;
      return;
    }
    tbody.innerHTML = items
      .map((r) => {
        const tags = [];
        if (r.in_watchlist) tags.push(`<span class="tr-tag watch" title="On your watchlist">W</span>`);
        if ((r.lists || []).includes("live")) tags.push(`<span class="tr-tag live" title="From live universe">L</span>`);
        if ((r.position_qty || 0) > 0) tags.push(`<span class="tr-tag pos" title="Open position">P</span>`);
        const qtyDefault = (r.position_qty || 0) > 0 ? r.position_qty : 1;
        return `<tr data-symbol="${escapeHtml(r.symbol)}">
          <td class="sym-cell mono">
            <strong style="cursor:pointer" data-tr-sym="${escapeHtml(r.symbol)}" title="Open symbol detail">${escapeHtml(r.symbol)}</strong>
            <span class="tr-tags">${tags.join("")}</span>
            <div class="muted" style="font-size:0.65rem;max-width:10rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml((r.name || "").slice(0, 28))}</div>
          </td>
          <td class="mono" title="Bid (buyers)">${fmtPx(r.bid)}</td>
          <td class="mono" title="Ask (sellers)">${fmtPx(r.ask)}</td>
          <td class="mono" title="Last trade">${fmtPx(r.price)}</td>
          <td class="mono ${pctClass(r.change_pct_day)}">${fmtPct(r.change_pct_day)}</td>
          <td class="mono" title="Shares held">${r.position_qty || 0}</td>
          <td>
            <div class="tr-actions">
              <input type="number" min="0.0001" step="1" value="${qtyDefault}" data-tr-qty="${escapeHtml(r.symbol)}" title="Order quantity" aria-label="Quantity for ${escapeHtml(r.symbol)}" />
            </div>
          </td>
          <td>
            <div class="tr-actions">
              <button type="button" class="btn btn-xs btn-buy" data-tr-buy="${escapeHtml(r.symbol)}" title="Market buy ${escapeHtml(r.symbol)} at about ask ${fmtPx(r.ask)}">Buy</button>
              <button type="button" class="btn btn-xs btn-sell" data-tr-sell="${escapeHtml(r.symbol)}" title="Market sell ${escapeHtml(r.symbol)} at about bid ${fmtPx(r.bid)}" ${(r.position_qty || 0) <= 0 ? "disabled" : ""}>Sell</button>
            </div>
          </td>
        </tr>`;
      })
      .join("");

    tbody.querySelectorAll("[data-tr-sym]").forEach((el) => {
      el.addEventListener("click", () => selectSymbol(el.dataset.trSym, { goDetail: true }));
    });
    tbody.querySelectorAll("[data-tr-buy]").forEach((btn) => {
      btn.addEventListener("click", () => quickTrade(btn.dataset.trBuy, "buy"));
    });
    tbody.querySelectorAll("[data-tr-sell]").forEach((btn) => {
      btn.addEventListener("click", () => quickTrade(btn.dataset.trSell, "sell"));
    });
  }

  async function quickTrade(symbol, side) {
    const sym = normalizeSymbol(symbol);
    if (!sym) return;
    const qtyInput = document.querySelector(`[data-tr-qty="${sym}"]`);
    const qty = Number(qtyInput?.value || 1);
    if (!(qty > 0) || Number.isNaN(qty)) {
      toast("Enter a valid quantity");
      return;
    }
    const body = {
      symbol: sym,
      side,
      qty,
      order_type: "market",
      limit_price: null,
      stop_price: null,
      take_profit: null,
    };
    try {
      const preview = await api("/api/orders/preview", { method: "POST", body: JSON.stringify(body) });
      if (!preview.allowed) {
        toast((preview.blockers || []).join("; ") || "Order blocked");
        return;
      }
      if (preview.live && !confirm(`LIVE ${side.toUpperCase()} ${qty} ${sym}?`)) return;
      await api("/api/orders", { method: "POST", body: JSON.stringify(body) });
      toast(`${side.toUpperCase()} ${qty} ${sym} submitted`);
      // Sync ticket for visibility
      if ($("ord-symbol")) $("ord-symbol").value = sym;
      if ($("ord-side")) $("ord-side").value = side;
      if ($("ord-qty")) $("ord-qty").value = String(qty);
      await loadTradingBoard({ afterTrade: true });
      await loadAccount().catch(() => {});
      await loadOrders().catch(() => {});
      await loadPortfolio().catch(() => {});
    } catch (e) {
      toast(e.message);
    }
  }

  async function loadTradingBoard(opts = {}) {
    const err = $("tr-error");
    if (err) err.hidden = true;
    const scope = $("tr-scope")?.value || "both";
    try {
      const data = await api(`/api/trading/board?scope=${encodeURIComponent(scope)}&limit=160`, {
        timeoutMs: 120000,
      });
      const items = data.items || [];
      state.tradingItems = items;
      $("tr-equity").textContent = fmtMoney(data.equity);
      $("tr-cash").textContent = fmtMoney(data.cash);
      $("tr-bp").textContent = fmtMoney(data.buying_power);
      $("tr-pos-count").textContent = String(data.position_count ?? 0);
      $("tr-board-count").textContent = String(data.count ?? items.length);
      $("tr-broker").textContent = data.broker_name || data.broker || "—";
      $("tr-asof").textContent = data.as_of ? new Date(data.as_of).toLocaleTimeString() : "—";

      const posMap = {};
      for (const r of items) {
        if ((r.position_qty || 0) > 0) posMap[r.symbol] = r.position_qty;
      }
      // Also include positions that dropped off the board
      if (opts.afterTrade || Object.keys(state.tradingPosSnapshot || {}).length) {
        diffTradingPositions(posMap);
      } else {
        state.tradingPosSnapshot = posMap;
      }

      renderTradingBoard(items);
      renderTradingActivity();
    } catch (e) {
      if (err) {
        err.hidden = false;
        err.textContent = e.message;
      }
      $("tr-body").innerHTML = `<tr><td colspan="8"><div class="banner error">${escapeHtml(e.message)}</div></td></tr>`;
    }
  }

  function applyButtonTooltips() {
    const tips = {
      "btn-refresh": "Refresh account, watchlist, and market snapshots",
      "btn-scan": "Run the signal scanner on the current scope",
      "btn-hunt": "Ask Grapevine to hunt for a careful paper trade idea",
      "btn-tour": "Start the guided desk tour",
      "btn-keys": "Open API keys and broker settings",
      "btn-watch-add": "Add the typed ticker to your watchlist",
      "btn-preview": "Preview risk and teaching checklist without submitting",
      "btn-submit": "Submit the order to the selected broker (paper or live)",
      "btn-orders-refresh": "Reload the order blotter",
      "btn-live-refresh": "Refresh the Live board quotes",
      "btn-live-fill": "Pull a larger quote batch for unmapped tickers",
      "btn-trading-refresh": "Refresh trading board quotes and positions",
      "btn-tr-clear-log": "Clear the portfolio activity log",
      "btn-portfolio-refresh": "Refresh positions, orders, and auto-track status",
      "btn-at-save": "Save auto-track gainer rules",
      "btn-at-scan": "Scan the universe now and add gainers to the watchlist",
      "btn-backtest": "Run SMA crossover backtest on the ticket symbol",
      "auto-refresh": "Toggle automatic desk refresh every 60 seconds",
    };
    document.querySelectorAll("button").forEach((btn) => {
      if (btn.getAttribute("title")) return;
      if (btn.id && tips[btn.id]) {
        btn.title = tips[btn.id];
        return;
      }
      const aria = btn.getAttribute("aria-label");
      if (aria) {
        btn.title = aria;
        return;
      }
      const tip = btn.getAttribute("data-tip");
      if (tip) {
        btn.title = tip;
        return;
      }
      const text = (btn.textContent || "").trim().replace(/\s+/g, " ");
      if (text && text.length > 0 && text.length < 48) btn.title = text;
    });
    document.querySelectorAll("select").forEach((el) => {
      if (el.getAttribute("title")) return;
      const aria = el.getAttribute("aria-label");
      if (aria) el.title = aria;
    });
    document.querySelectorAll("input[type='checkbox']").forEach((el) => {
      if (el.getAttribute("title") || !el.id) return;
      if (tips[el.id]) el.title = tips[el.id];
    });
  }

  async function loadPortfolio() {
    try {
      const p = await api("/api/portfolio");
      const s = p.summary || {};
      $("pf-equity").textContent = fmtMoney(p.equity);
      $("pf-cash").textContent = fmtMoney(p.cash);
      $("pf-bp").textContent = fmtMoney(p.buying_power);
      const upl = s.unrealized_pl;
      const uplEl = $("pf-upl");
      uplEl.textContent =
        upl == null
          ? "—"
          : `${fmtMoney(upl)}${s.unrealized_pl_pct != null ? ` (${fmtPct(s.unrealized_pl_pct)})` : ""}`;
      uplEl.className = `mono ${pctClass(upl)}`;
      $("pf-mv").textContent = fmtMoney(s.positions_market_value);
      $("pf-broker").textContent = p.broker_name || p.broker || "—";
      $("pf-pos-count").textContent = `${s.position_count || 0} open`;
      $("pf-orders-count").textContent = `${s.open_orders || 0} open · ${s.filled_orders || 0} filled`;

      const tbody = $("pf-positions-body");
      const positions = p.positions || [];
      if (!positions.length) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="empty">No open positions</div></td></tr>`;
      } else {
        tbody.innerHTML = positions
          .map(
            (row) => `<tr data-symbol="${escapeHtml(row.symbol)}">
              <td class="sym-cell mono">${escapeHtml(row.symbol)}</td>
              <td class="mono">${row.qty}</td>
              <td class="mono">${fmtPx(row.avg_entry)}</td>
              <td class="mono">${fmtMoney(row.market_value)}</td>
              <td class="mono ${pctClass(row.unrealized_pl)}">${fmtMoney(row.unrealized_pl)}</td>
              <td class="mono ${pctClass(row.unrealized_pl_pct)}">${fmtPct(row.unrealized_pl_pct)}</td>
              <td><button type="button" class="btn ghost btn-xs" data-pf-sell="${escapeHtml(row.symbol)}" data-qty="${row.qty}">Sell</button></td>
            </tr>`
          )
          .join("");
        tbody.querySelectorAll("tr[data-symbol]").forEach((tr) => {
          tr.addEventListener("click", (ev) => {
            if (ev.target.closest("[data-pf-sell]")) return;
            selectSymbol(tr.dataset.symbol, { goDetail: true });
          });
        });
        tbody.querySelectorAll("[data-pf-sell]").forEach((btn) => {
          btn.addEventListener("click", (ev) => {
            ev.stopPropagation();
            $("ord-symbol").value = btn.dataset.pfSell;
            $("ord-side").value = "sell";
            $("ord-qty").value = btn.dataset.qty;
            selectSymbol(btn.dataset.pfSell);
            toast(`Sell ticket loaded for ${btn.dataset.pfSell}`);
          });
        });
      }

      const obox = $("pf-orders-box");
      const orders = p.orders || [];
      if (!orders.length) {
        obox.innerHTML = `<div class="empty">No orders yet</div>`;
      } else {
        obox.innerHTML = orders
          .slice(0, 40)
          .map((o) => {
            const canCancel = ["open", "pending"].includes(o.status);
            return `<article class="signal-card" style="cursor:default">
              <div class="title">
                <span class="mono" data-symbol="${escapeHtml(o.symbol)}" style="cursor:pointer">${escapeHtml(o.symbol)}</span>
                <span class="mono muted">${escapeHtml(o.side)} ${o.qty} · ${escapeHtml(o.order_type)}</span>
              </div>
              <p class="tip">${escapeHtml(o.status)}${o.filled_avg_price ? ` · fill ${fmtPx(o.filled_avg_price)}` : ""}${o.submitted_at ? ` · ${escapeHtml(String(o.submitted_at).slice(0, 19))}` : ""}</p>
              ${canCancel ? `<button type="button" class="btn ghost btn-xs" data-pf-cancel="${escapeHtml(o.id)}">Cancel</button>` : ""}
            </article>`;
          })
          .join("");
        obox.querySelectorAll("[data-symbol]").forEach((n) =>
          n.addEventListener("click", () => selectSymbol(n.dataset.symbol, { goDetail: true }))
        );
        obox.querySelectorAll("[data-pf-cancel]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            try {
              await api(`/api/orders/${encodeURIComponent(btn.dataset.pfCancel)}`, { method: "DELETE" });
              toast("Order canceled");
              await loadPortfolio();
              await loadOrders();
            } catch (e) {
              toast(e.message);
            }
          });
        });
      }
    } catch (e) {
      $("pf-equity").textContent = "—";
      $("pf-positions-body").innerHTML = `<tr><td colspan="7"><div class="banner error">${escapeHtml(e.message)}</div></td></tr>`;
    }
  }

  function renderAutoTrackAdded(rows) {
    const box = $("at-added");
    if (!box) return;
    if (!rows?.length) {
      box.innerHTML = `<div class="empty">No new gainers added yet</div>`;
      return;
    }
    box.innerHTML = rows
      .map(
        (r) => `<div class="row" data-symbol="${escapeHtml(r.symbol)}" style="cursor:pointer">
          <span class="sym">${escapeHtml(r.symbol)}</span>
          <span class="mono ${pctClass(r.change_pct_day)}">${fmtPct(r.change_pct_day)}</span>
          <span class="mono muted">${fmtPx(r.price)}</span>
        </div>`
      )
      .join("");
    box.querySelectorAll("[data-symbol]").forEach((n) =>
      n.addEventListener("click", () => selectSymbol(n.dataset.symbol, { goDetail: true }))
    );
  }

  async function loadAutoTrack() {
    const s = await api("/api/auto-track");
    $("at-enabled").checked = !!s.enabled;
    $("at-threshold").value = s.min_change_pct ?? 5;
    $("at-poll").value = s.poll_sec ?? 60;
    $("at-max").value = s.max_adds_per_scan ?? 12;
    $("at-exchanges").value = (s.exchanges || []).join(", ");
    const classes = s.asset_classes || [];
    $("at-stocks").checked = !classes.length || classes.includes("stock") || classes.includes("adr");
    $("at-etf").checked = !!s.include_etf || classes.includes("etf");
    $("at-status").textContent = s.enabled
      ? `on · ≥${s.min_change_pct}% · every ${s.poll_sec}s`
      : "off";
    const last = s.last_run
      ? `Last scan ${new Date(s.last_run).toLocaleString()} · ${s.last_hits || 0} candidates`
      : "No scans yet";
    $("at-last").textContent = s.last_error ? `${last} · error: ${s.last_error}` : last;
    renderAutoTrackAdded(s.last_added || []);
  }

  async function saveAutoTrack() {
    const classes = [];
    if ($("at-stocks").checked) classes.push("stock", "adr");
    if ($("at-etf").checked) classes.push("etf");
    const payload = {
      enabled: $("at-enabled").checked,
      min_change_pct: Number($("at-threshold").value),
      poll_sec: Number($("at-poll").value),
      max_adds_per_scan: Number($("at-max").value),
      exchanges: $("at-exchanges").value,
      asset_classes: classes,
      include_etf: $("at-etf").checked,
    };
    const banner = $("at-banner");
    try {
      await api("/api/auto-track", { method: "PUT", body: JSON.stringify(payload) });
      banner.hidden = false;
      banner.className = "banner ok";
      banner.textContent = "Auto-track rules saved.";
      toast("Auto-track saved");
      await loadAutoTrack();
      await loadWatchlist();
    } catch (e) {
      banner.hidden = false;
      banner.className = "banner error";
      banner.textContent = e.message;
    }
  }

  async function runAutoTrackScan() {
    const banner = $("at-banner");
    banner.hidden = false;
    banner.className = "banner ok";
    banner.textContent = "Scanning universe for gainers…";
    try {
      // Ensure rules saved first
      await saveAutoTrack();
      const r = await api("/api/auto-track/scan?force=true", { method: "POST", timeoutMs: 120000 });
      const n = r.added?.length || 0;
      banner.textContent = r.skipped
        ? "Auto-track is disabled — enable it, then scan."
        : `Scan done · ${r.hits || 0} over threshold · added ${n}`;
      toast(n ? `Auto-tracked ${n} gainers` : "No new gainers to add");
      await loadAutoTrack();
      await loadWatchlist();
    } catch (e) {
      banner.className = "banner error";
      banner.textContent = e.message;
    }
  }

  function setStudioDates() {
    const end = new Date();
    const start = new Date();
    start.setFullYear(end.getFullYear() - 1);
    const iso = (d) => d.toISOString().slice(0, 10);
    ["st-start", "cs-start"].forEach((id) => {
      if ($(id) && !$(id).value) $(id).value = iso(start);
    });
    ["st-end", "cs-end"].forEach((id) => {
      if ($(id) && !$(id).value) $(id).value = iso(end);
    });
  }

  async function loadStrategies() {
    const data = await api("/api/strategies");
    const list = data.strategies || [];
    const sel = $("st-strategy");
    const cards = $("strategy-cards");
    if (sel && !sel.options.length) {
      sel.innerHTML = list
        .map((s) => `<option value="${s.id}">${escapeHtml(s.name)}</option>`)
        .join("");
    }
    if (cards) {
      cards.innerHTML = list
        .map(
          (s) => `<div class="strategy-card" data-id="${s.id}">
          <h3>${escapeHtml(s.name)}</h3>
          <p>${escapeHtml(s.description)}</p>
          <p class="muted" style="margin-top:0.35rem">${escapeHtml(s.cost || "Free")}</p>
        </div>`
        )
        .join("");
      cards.querySelectorAll(".strategy-card").forEach((card) => {
        card.addEventListener("click", () => {
          cards.querySelectorAll(".strategy-card").forEach((c) => c.classList.remove("active"));
          card.classList.add("active");
          if (sel) sel.value = card.dataset.id;
        });
      });
    }
  }

  async function runStrategyBacktest() {
    const symbol = normalizeSymbol($("st-symbol").value);
    const strategy = $("st-strategy").value || "sma_crossover";
    const start = $("st-start").value;
    const end = $("st-end").value;
    const box = $("st-result");
    if (!symbol || !start || !end) {
      box.textContent = "Ticker, strategy, start, and end required";
      return;
    }
    toast("Running free yfinance backtest…");
    try {
      const r = await api("/api/strategies/backtest", {
        method: "POST",
        body: JSON.stringify({ symbol, strategy, start, end }),
        timeoutMs: 120000,
      });
      box.innerHTML = `<strong>${escapeHtml(r.strategy_name)}</strong> on ${escapeHtml(r.symbol)}<br/>
        Return <span class="${pctClass(r.total_return_pct)}">${fmtPct(r.total_return_pct)}</span>
        · Max DD ${r.max_drawdown_pct}% · Trades ${r.trades}<br/>
        Buy&amp;hold ${fmtPct(r.buy_hold_return_pct)} · vs BH ${fmtPct(r.vs_buy_hold_pct)}<br/>
        <span class="muted">${escapeHtml(r.data_source || "")}</span>`;
      drawSeries(
        $("st-equity"),
        (r.equity || []).map((p) => p.v),
        "#f5c451"
      );
    } catch (e) {
      box.textContent = e.message;
    }
  }

  function drawSeries(canvas, values, color) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (!values?.length) return;
    const nums = values.filter((v) => v != null && !Number.isNaN(v));
    if (nums.length < 2) return;
    const min = Math.min(...nums);
    const max = Math.max(...nums);
    const span = max - min || 1;
    ctx.strokeStyle = color || "#7dd3fc";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    nums.forEach((v, i) => {
      const x = (i / (nums.length - 1)) * (w - 8) + 4;
      const y = h - 4 - ((v - min) / span) * (h - 8);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  function drawVolume(canvas, bars) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (!bars?.length) return;
    const vols = bars.map((b) => b.v || 0);
    const max = Math.max(...vols) || 1;
    const bw = Math.max(1, (w - 8) / bars.length - 1);
    bars.forEach((b, i) => {
      const x = 4 + i * ((w - 8) / bars.length);
      const bh = ((b.v || 0) / max) * (h - 6);
      ctx.fillStyle = b.c >= b.o ? "rgba(125, 211, 252, 0.55)" : "rgba(240, 113, 120, 0.55)";
      ctx.fillRect(x, h - 3 - bh, bw, bh);
    });
  }

  function drawMacd(canvas, bars) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const hist = bars.map((b) => b.macd_hist).filter((v) => v != null);
    if (hist.length < 2) return;
    const max = Math.max(...hist.map(Math.abs), ...bars.map((b) => Math.abs(b.macd || 0))) || 1;
    const mid = h / 2;
    const bw = Math.max(1, (w - 8) / bars.length - 1);
    bars.forEach((b, i) => {
      if (b.macd_hist == null) return;
      const x = 4 + i * ((w - 8) / bars.length);
      const bh = (b.macd_hist / max) * (mid - 4);
      ctx.fillStyle = b.macd_hist >= 0 ? "rgba(125, 211, 252, 0.7)" : "rgba(240, 113, 120, 0.7)";
      if (bh >= 0) ctx.fillRect(x, mid - bh, bw, bh);
      else ctx.fillRect(x, mid, bw, -bh);
    });
    ctx.strokeStyle = "#f5c451";
    ctx.lineWidth = 1;
    ctx.beginPath();
    let started = false;
    bars.forEach((b, i) => {
      if (b.macd == null) return;
      const x = 4 + (i / Math.max(1, bars.length - 1)) * (w - 8);
      const y = mid - (b.macd / max) * (mid - 4);
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else ctx.lineTo(x, y);
    });
    if (started) ctx.stroke();
  }

  function ensureStudioController() {
    const C = Charts();
    const canvas = $("cs-price");
    if (!C || !canvas) return null;
    if (state.studioCtrl) return state.studioCtrl;
    state.studioCtrl = C.createController({
      primaryCanvas: canvas,
      tooltipEl: $("cs-inspect"),
      getBars: () => state.studioBars || [],
      symbol: normalizeSymbol($("cs-symbol")?.value || ""),
      onRender: ({ bars, hoverIdx, brush, drawings, draft, viewStart }) => {
        C.drawPriceChart($("cs-price"), bars, {
          mode: "candle",
          smas: true,
          hoverIdx,
          brush,
          drawings,
          draft,
          viewStart,
        });
        C.drawVolumeChart($("cs-vol"), bars, { hoverIdx });
        C.drawRsiChart($("cs-rsi"), bars, { hoverIdx });
        C.drawMacdChart($("cs-macd"), bars, { hoverIdx });
      },
    });
    return state.studioCtrl;
  }

  function renderChartStudio() {
    const C = Charts();
    if (!C) return;
    const ctrl = ensureStudioController();
    ctrl?.redraw();
  }

  async function loadChartStudio() {
    const symbol = normalizeSymbol($("cs-symbol").value);
    const start = $("cs-start").value;
    const end = $("cs-end").value;
    if (!symbol || !start || !end) {
      toast("Ticker and date range required");
      return;
    }
    toast("Loading chart pack…");
    try {
      const pack = await api("/api/charts/pack", {
        method: "POST",
        body: JSON.stringify({ symbol, start, end }),
        timeoutMs: 120000,
      });
      const bars = pack.bars || [];
      const s = pack.summary || {};
      state.studioBars = bars;
      $("cs-summary").textContent = `${pack.symbol} · last ${fmtPx(s.last)} · period ${fmtPct(s.change_pct)} · RSI ${s.rsi ?? "—"} · ${s.bars || 0} bars · ${s.data_source || ""}`;
      const ctrl = ensureStudioController();
      ctrl?.setSymbol(symbol);
      ctrl?.resetView();
      renderChartStudio();
      toast(`Loaded ${bars.length} bars for ${symbol}`);
    } catch (e) {
      toast(e.message);
    }
  }

  function heatClass(pct) {
    if (pct == null || Number.isNaN(Number(pct))) return "flat";
    const n = Number(pct);
    if (n >= 3) return "up-strong";
    if (n >= 0.15) return "up";
    if (n <= -3) return "down-strong";
    if (n <= -0.15) return "down";
    return "flat";
  }

  function stopLivePoll() {
    if (state.liveTimer) {
      clearInterval(state.liveTimer);
      state.liveTimer = null;
    }
  }

  function startLivePoll() {
    stopLivePoll();
    if (!$("live-auto")?.checked) return;
    const mode = $("live-mode")?.value || "universe";
    const ms = mode === "universe" ? 20000 : 8000;
    state.liveTimer = setInterval(() => {
      const panel = document.querySelector('[data-sub-panel="markets-live"]');
      if (panel && !panel.hidden) loadLiveBoard({ quiet: true }).catch(() => {});
    }, ms);
  }

  function renderLiveTape(items) {
    const tape = $("live-tape");
    if (!tape) return;
    const movers = [...(items || [])]
      .filter((r) => r.price != null)
      .sort((a, b) => Math.abs(b.change_pct_day || 0) - Math.abs(a.change_pct_day || 0))
      .slice(0, 24);
    if (!movers.length) {
      tape.innerHTML = `<span class="live-tape-item muted">Waiting for market action…</span>`;
      return;
    }
    const html = movers
      .map((r) => {
        const pct = r.change_pct_day;
        const dir = (pct || 0) >= 0 ? "up" : "down";
        return `<span class="live-tape-item ${dir}"><span class="sym">${escapeHtml(r.symbol)}</span><span>${fmtPx(r.price)}</span><span class="chg">${fmtPct(pct)}</span></span>`;
      })
      .join("");
    // Duplicate for seamless marquee loop
    tape.innerHTML = html + html;
  }

  function ensureLiveChartController() {
    const C = Charts();
    const canvas = $("live-chart-canvas");
    if (!C || !canvas) return null;
    if (state.liveCtrl) return state.liveCtrl;
    state.liveCtrl = C.createController({
      primaryCanvas: canvas,
      tooltipEl: $("live-chart-inspect"),
      getBars: () => state.liveOhlc || [],
      symbol: state.liveSymbol,
      onRender: ({ bars, hoverIdx, brush, drawings, draft, viewStart }) =>
        C.drawPriceChart(canvas, bars, {
          mode: "candle",
          hoverIdx,
          brush,
          drawings,
          draft,
          viewStart,
        }),
    });
    return state.liveCtrl;
  }

  function stopLiveTickStream() {
    if (state.liveEs) {
      try {
        state.liveEs.close();
      } catch {
        /* ignore */
      }
      state.liveEs = null;
    }
    if (state.liveTickTimer) {
      clearInterval(state.liveTickTimer);
      state.liveTickTimer = null;
    }
    const chip = $("live-stream-chip");
    if (chip) {
      chip.hidden = true;
      chip.classList.remove("live");
    }
    if ($("live-stream-status")) $("live-stream-status").textContent = "stream off";
  }

  function applyLiveTick(tick) {
    if (!tick || !tick.ok || !state.liveSymbol) return;
    if (normalizeSymbol(tick.symbol) !== normalizeSymbol(state.liveSymbol)) return;

    if ($("live-chart-px") && tick.price != null) {
      $("live-chart-px").textContent = fmtPx(tick.price);
    }
    const chgEl = $("live-chart-chg");
    if (chgEl && tick.change_pct != null) {
      chgEl.textContent = fmtPct(tick.change_pct);
      chgEl.className = `mono ${pctClass(tick.change_pct)}`;
    }
    if ($("live-chart-summary")) {
      $("live-chart-summary").textContent = `${tick.symbol} · ${fmtPx(tick.price)} · ${fmtPct(tick.change_pct)}`;
    }

    const banner = $("live-session-banner");
    if (banner) {
      const stateLabel = tick.market_state || (tick.us_open ? "REGULAR" : "CLOSED");
      if (!tick.us_open || ["CLOSED", "PREPRE", "POSTPOST"].includes(String(stateLabel).toUpperCase())) {
        banner.hidden = false;
        banner.className = "banner";
        banner.textContent = `US cash session closed (${stateLabel}). Showing last trade · stream slowed to ~${Math.round(tick.poll_sec || 12)}s.`;
        document.body.classList.add("market-closed");
        document.body.classList.remove("market-open");
      } else {
        banner.hidden = false;
        banner.className = "banner ok";
        banner.textContent = `Live · ${stateLabel}${tick.exchange ? ` · ${tick.exchange}` : ""} · tick ~${(tick.poll_sec || 1).toFixed(1)}s (shared cache)`;
        document.body.classList.add("market-open");
        document.body.classList.remove("market-closed");
      }
    }

    const status = $("live-stream-status");
    if (status) {
      const t = new Date(tick.as_of || Date.now()).toLocaleTimeString();
      status.textContent = tick.cached ? `cache · ${t}` : `live · ${t}`;
    }
    const chip = $("live-stream-chip");
    if (chip) {
      chip.hidden = false;
      chip.textContent = tick.us_open ? "LIVE" : "SLOW";
      chip.classList.toggle("live", !!tick.us_open);
    }

    // Update / extend last intraday bar when in live TF
    const tf = state.liveChartTf || $("live-chart-tf")?.value || "live1m";
    if ((tf === "live1m" || tf === "live5m") && tick.price != null && state.liveOhlc?.length) {
      const bars = state.liveOhlc;
      const last = bars[bars.length - 1];
      const px = Number(tick.price);
      const barSec = tf === "live5m" ? 300 : 60;
      const tickSec = tick.bar_time || Math.floor(Date.now() / 1000);
      const lastSec = last?.t ? Math.floor(new Date(last.t).getTime() / 1000) : 0;
      const bucket = Math.floor(tickSec / barSec) * barSec;
      const lastBucket = Math.floor(lastSec / barSec) * barSec;
      if (bucket > lastBucket) {
        bars.push({
          t: new Date(bucket * 1000).toISOString(),
          o: px,
          h: px,
          l: px,
          c: px,
          v: tick.volume || 0,
        });
        if (bars.length > 500) bars.splice(0, bars.length - 500);
      } else {
        last.c = px;
        last.h = Math.max(Number(last.h) || px, px);
        last.l = Math.min(Number(last.l) || px, px);
        if (tick.volume != null) last.v = tick.volume;
      }
      ensureLiveChartController()?.redraw();
    }
  }

  function startLiveTickStream(sym) {
    const s = normalizeSymbol(sym);
    if (!s || !$("live-stream")?.checked) {
      stopLiveTickStream();
      return;
    }
    stopLiveTickStream();
    if ($("live-stream-status")) $("live-stream-status").textContent = "connecting…";

    if (typeof EventSource !== "undefined") {
      const es = new EventSource(`/api/stream/tick/${encodeURIComponent(s)}`);
      state.liveEs = es;
      es.onmessage = (ev) => {
        try {
          applyLiveTick(JSON.parse(ev.data));
        } catch {
          /* ignore bad frame */
        }
      };
      es.onerror = () => {
        // Fall back to poll if SSE drops
        if (state.liveEs === es) {
          try {
            es.close();
          } catch {
            /* ignore */
          }
          state.liveEs = null;
          state.liveTickTimer = setInterval(() => {
            api(`/api/tick/${encodeURIComponent(s)}`)
              .then(applyLiveTick)
              .catch(() => {});
          }, 1000);
          if ($("live-stream-status")) $("live-stream-status").textContent = "poll fallback";
        }
      };
      return;
    }

    state.liveTickTimer = setInterval(() => {
      api(`/api/tick/${encodeURIComponent(s)}`)
        .then(applyLiveTick)
        .catch(() => {});
    }, 1000);
  }

  async function openLiveChart(sym, row = null) {
    const s = normalizeSymbol(sym);
    if (!s) return;
    state.liveSymbol = s;
    state.selected = s;
    if ($("cs-symbol")) $("cs-symbol").value = s;
    if ($("ord-symbol")) $("ord-symbol").value = s;

    const chartPanel = $("live-collapse-chart");
    if (chartPanel) chartPanel.open = true;
    $("live-chart-empty").hidden = true;
    $("live-chart-body").hidden = false;
    $("live-chart-dock")?.classList.add("open");
    $("live-chart-sym").textContent = s;
    $("live-chart-name").textContent = row?.name || "";
    $("live-chart-px").textContent = row?.price != null ? fmtPx(row.price) : "…";
    if ($("live-chart-summary")) {
      $("live-chart-summary").textContent = `${s}${row?.change_pct_day != null ? ` · ${fmtPct(row.change_pct_day)}` : ""}`;
    }
    const chgEl = $("live-chart-chg");
    if (chgEl) {
      chgEl.textContent = fmtPct(row?.change_pct_day);
      chgEl.className = `mono ${pctClass(row?.change_pct_day)}`;
    }

    document.querySelectorAll("#live-heat [data-symbol]").forEach((el) => {
      el.classList.toggle("active", el.dataset.symbol === s);
    });

    const tf = $("live-chart-tf")?.value || state.liveChartTf || "live1m";
    state.liveChartTf = tf;

    try {
      let bars = [];
      if (tf === "daily90") {
        const ohlc = await api(`/api/ohlc/${encodeURIComponent(s)}?days=90`).catch(() => ({ bars: [] }));
        bars = ohlc.bars || [];
      } else {
        const interval = tf === "live5m" ? "5m" : "1m";
        const pack = await api(
          `/api/ohlc/${encodeURIComponent(s)}/intraday?interval=${interval}&range=1d`
        ).catch(() => ({ bars: [] }));
        bars = pack.bars || [];
        if (!bars.length) {
          const ohlc = await api(`/api/ohlc/${encodeURIComponent(s)}?days=90`).catch(() => ({ bars: [] }));
          bars = ohlc.bars || [];
          $("live-chart-name").textContent = `${row?.name || s} · intraday empty, showing daily`;
        }
      }
      state.liveOhlc = bars;
      if (!state.liveOhlc.length) {
        $("live-chart-name").textContent = `${row?.name || s} · chart unavailable (thin/unmapped)`;
      }
      const ctrl = ensureLiveChartController();
      ctrl?.setSymbol(s);
      ctrl?.resetView();
      ctrl?.redraw();
      const tool = ctrl?.getTool() || "inspect";
      document.querySelectorAll("[data-live-tool]").forEach((b) => {
        b.classList.toggle("active", b.dataset.liveTool === tool);
      });
      if ($("live-stream")?.checked) startLiveTickStream(s);
      else stopLiveTickStream();
    } catch (e) {
      $("live-chart-name").textContent = e.message;
    }
  }

  function formatClockInTz(timeZone) {
    try {
      return new Intl.DateTimeFormat(undefined, {
        timeZone,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      }).format(new Date());
    } catch {
      return "—";
    }
  }

  function sessionToFocus(sessionId) {
    const map = {
      nyse: "us",
      london: "london",
      frankfurt: "frankfurt",
      tokyo: "tokyo",
      hongkong: "hongkong",
      sydney: "sydney",
    };
    return map[sessionId] || "us";
  }

  function renderWorldClocks(data) {
    const box = $("world-clocks");
    if (!box || !data) return;
    const localEl = $("brand-local-time");
    if (localEl) {
      localEl.textContent = new Intl.DateTimeFormat(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      }).format(new Date());
    }
    const usChip = $("brand-us-status");
    const usOpens = $("brand-us-opens");
    if (usChip) {
      if (data.us_open) {
        usChip.textContent = "US open";
        usChip.className = "chip open";
        usChip.title = `NYSE cash session ${data.us_hours || "09:30–16:00"} ET`;
      } else {
        const when = data.us_next_open_label || data.us_hint || "opens Mon 09:30 ET";
        usChip.textContent = "US closed";
        usChip.className = "chip closed";
        usChip.title = `US cash closed · ${when}`;
      }
    }
    if (usOpens) {
      if (data.us_open) {
        usOpens.hidden = false;
        usOpens.className = "mono muted";
        usOpens.textContent = `until 16:00 ET`;
      } else {
        usOpens.hidden = false;
        usOpens.className = "mono open-soon";
        usOpens.textContent = data.us_next_open_label || data.us_hint || "opens Mon 09:30 ET";
      }
    }
    document.body.classList.toggle("market-open", !!data.us_open);
    document.body.classList.toggle("market-closed", !data.us_open);
    updateGrapevinePulse({
      us_open: !!data.us_open,
      us_hint: data.us_next_open_label || data.us_hint,
      gainers: state.highlights?.stocks_of_day?.gainers || [],
      losers: state.highlights?.stocks_of_day?.losers || [],
    });

    const focus = state.liveMarketFocus || "us";
    box.innerHTML = (data.markets || [])
      .map((m) => {
        const t = formatClockInTz(m.timezone);
        const mFocus = sessionToFocus(m.id);
        const cls = `${m.is_open ? "open" : "closed"}${mFocus === focus ? " active" : ""}`;
        const stateTxt = m.is_open ? "open" : "closed";
        const title = m.is_open
          ? `${m.name} OPEN · ${m.hours} ${m.tz_abbr || ""} · click to switch board`
          : `${m.name} CLOSED · ${m.hint || m.next_open_label || ""} · click to switch board`;
        return `<button type="button" class="mkt-clock ${cls}" data-mkt-focus="${escapeHtml(mFocus)}" title="${escapeHtml(title)}">
          <span class="mkt-dot" aria-hidden="true"></span>
          <span class="mkt-name">${escapeHtml(m.short)}</span>
          <span class="mkt-time">${escapeHtml(t)}</span>
          <span class="mkt-state">${stateTxt}</span>
        </button>`;
      })
      .join("");
    box.onclick = (ev) => {
      const btn = ev.target.closest("[data-mkt-focus]");
      if (!btn) return;
      setLiveMarketFocus(btn.dataset.mktFocus);
      // Jump to Live if user clicked from header
      switchDeskTab("markets", "live");
    };
    syncMarketPillsOpenState(data.focuses);
  }

  async function syncMarketClocks() {
    try {
      const data = await api("/api/markets/clocks");
      state.marketClocks = data;
      renderWorldClocks(data);
    } catch {
      /* keep last */
    }
  }

  function startMarketClocks() {
    if (state.clockTimer) clearInterval(state.clockTimer);
    if (state.clockSyncTimer) clearInterval(state.clockSyncTimer);
    syncMarketClocks();
    state.clockTimer = setInterval(() => {
      if (state.marketClocks) renderWorldClocks(state.marketClocks);
    }, 1000);
    state.clockSyncTimer = setInterval(syncMarketClocks, 20000);
  }

  function bindLiveBoardClicks(box, items) {
    box.onclick = (ev) => {
      const el = ev.target.closest("[data-symbol]");
      if (!el) return;
      const row = items.find((x) => x.symbol === el.dataset.symbol);
      openLiveChart(el.dataset.symbol, row);
    };
  }

  function sortLiveItemsClient(items, sortKey) {
    const key = (sortKey || "abs_change").trim().toLowerCase();
    const rows = [...(items || [])];
    const num = (v, fallback) => (v == null || Number.isNaN(Number(v)) ? fallback : Number(v));
    if (key === "change_desc" || key === "change_pct" || key === "gainers") {
      rows.sort((a, b) => num(b.change_pct_day, -9999) - num(a.change_pct_day, -9999));
    } else if (key === "change_asc" || key === "losers") {
      rows.sort((a, b) => num(a.change_pct_day, 9999) - num(b.change_pct_day, 9999));
    } else if (key === "volume" || key === "vol") {
      rows.sort((a, b) => num(b.volume, 0) - num(a.volume, 0));
    } else if (key === "rel_volume" || key === "rvol") {
      rows.sort((a, b) => num(b.rel_volume, 0) - num(a.rel_volume, 0));
    } else if (key === "price") {
      rows.sort((a, b) => num(b.price, 0) - num(a.price, 0));
    } else if (key === "symbol") {
      rows.sort((a, b) => String(a.symbol || "").localeCompare(String(b.symbol || "")));
    } else if (key === "week" || key === "change_week") {
      rows.sort((a, b) => num(b.change_pct_week, -9999) - num(a.change_pct_week, -9999));
    } else {
      rows.sort((a, b) => Math.abs(num(b.change_pct_day, 0)) - Math.abs(num(a.change_pct_day, 0)));
    }
    return rows;
  }

  function applyLiveSortAndRender() {
    const sortKey = $("live-sort")?.value || "abs_change";
    const sorted = sortLiveItemsClient(state.liveItems || [], sortKey);
    state.liveItems = sorted;
    if (state.liveMeta) state.liveMeta.sort = sortKey;
    renderLiveBoardView(sorted, state.liveMeta || {});
  }

  function liveDisplayCap(view) {
    if (view === "blocks") return 240;
    if (view === "bubbles") return 160;
    if (view === "table") return 600;
    if (view === "markets") return 1200;
    return 500; // tiles — keep DOM light on full universe
  }

  function renderLiveTiles(items, { blocks = false } = {}) {
    const prev = state.liveQuotes || {};
    const next = {};
    const huge = items.length > 400;
    const parts = new Array(items.length);
    for (let idx = 0; idx < items.length; idx++) {
      const r = items[idx];
      const pct = r.change_pct_day;
      const cls = heatClass(pct);
      const name = (r.name || "").slice(0, blocks ? 28 : 22);
      const hot = !huge && Math.abs(pct || 0) >= 3 ? " hot" : "";
      const oldPx = prev[r.symbol];
      let tick = "";
      let flash = "";
      if (!huge && oldPx != null && r.price != null && Number(oldPx) !== Number(r.price)) {
        flash = " flash";
        tick = Number(r.price) > Number(oldPx) ? " tick-up" : " tick-down";
      }
      next[r.symbol] = r.price;
      const active = state.liveSymbol === r.symbol ? " active" : "";
      const delay = huge ? "" : ` style="animation-delay:${Math.min(idx, 40) * 12}ms"`;
      const spark = blocks ? miniSparkSvg(r.sparkline || []) : "";
      const meta = blocks
        ? `<span class="live-meta"><span>${fmtVol(r.volume)}</span><span>${r.exchange || ""}</span></span>${spark}`
        : `<span class="live-name">${escapeHtml(name)}</span>`;
      parts[idx] = `<button type="button" class="live-tile ${cls}${hot}${flash}${tick}${active}" data-symbol="${escapeHtml(r.symbol)}"${delay} title="${escapeHtml(r.name || r.symbol)}">
          <span class="live-sym mono">${escapeHtml(r.symbol)}</span>
          <span class="live-px mono">${fmtPx(r.price)}</span>
          <span class="live-chg mono">${fmtPct(pct)}</span>
          ${meta}
        </button>`;
    }
    state.liveQuotes = next;
    return parts.join("");
  }

  function mosaicSizeClass(vol, maxV) {
    if (!maxV) return "sz-1";
    const ratio = Math.log10((Number(vol) || 1) + 1) / Math.log10(maxV + 1);
    if (ratio >= 0.92) return "sz-5";
    if (ratio >= 0.78) return "sz-4";
    if (ratio >= 0.58) return "sz-3";
    if (ratio >= 0.35) return "sz-2";
    return "sz-1";
  }

  function renderLiveBubbles(items) {
    // Finviz-style volume mosaic (flat heat cells) — not circle pack
    const capped = items.slice(0, 160);
    const vols = capped.map((r) => Number(r.volume) || 0);
    const maxV = Math.max(...vols, 1);
    return capped
      .map((r) => {
        const pct = r.change_pct_day;
        const cls = heatClass(pct);
        const sz = mosaicSizeClass(r.volume, maxV);
        const active = state.liveSymbol === r.symbol ? " active" : "";
        const showPx = sz === "sz-4" || sz === "sz-5" || sz === "sz-3";
        return `<button type="button" class="live-mosaic ${cls} ${sz}${active}" data-symbol="${escapeHtml(r.symbol)}"
          title="${escapeHtml(r.name || r.symbol)} · ${fmtPct(pct)} · vol ${fmtVol(r.volume)}${r.exchange ? ` · ${r.exchange}` : ""}">
          <span class="live-sym mono">${escapeHtml(r.symbol)}</span>
          <span class="live-chg mono">${fmtPct(pct)}</span>
          ${showPx ? `<span class="live-px mono">${fmtPx(r.price)}</span>` : ""}
        </button>`;
      })
      .join("");
  }

  function setLiveMarketFocus(focus, opts = {}) {
    const key = (focus || "us").toLowerCase();
    state.liveMarketFocus = key;
    const usMap = { us: "", nasdaq: "NASDAQ", nyse: "NYSE", arca: "NYSE Arca", amex: "NYSE American" };
    if ($("live-exchange")) $("live-exchange").value = usMap[key] ?? "";
    document.querySelectorAll("[data-mkt-focus]").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.mktFocus === key);
    });
    document.querySelectorAll(".mkt-clock[data-mkt-focus]").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.mktFocus === key);
    });
    if (opts.reload !== false) {
      startLivePoll();
      loadLiveBoard({ forceRefresh: key === "us" });
    }
  }

  async function loadFocusedMarketBoard(opts = {}) {
    const box = $("live-heat");
    const err = $("live-error");
    if (!box) return;
    if (err) err.hidden = true;
    const focus = state.liveMarketFocus || "us";
    const fetchId = ++state.liveFetchId;
    const sortKey = $("live-sort")?.value || "volume";
    try {
      const data = await api(
        `/api/markets/board?focus=${encodeURIComponent(focus)}&limit=220&sort=${encodeURIComponent(sortKey)}`,
        { timeoutMs: 90000 }
      );
      if (fetchId !== state.liveFetchId) return;
      const items = sortLiveItemsClient(data.items || [], $("live-sort")?.value || sortKey);
      state.liveItems = items;
      state.liveMeta = { ...data, markets: data.markets };
      if ($("live-stats")) $("live-stats").textContent = items.length.toLocaleString();
      const breadth = data.breadth || {};
      if ($("live-up")) $("live-up").textContent = String(breadth.up ?? "—");
      if ($("live-down")) $("live-down").textContent = String(breadth.down ?? "—");
      if ($("live-board-count")) {
        $("live-board-count").textContent = items.length ? `· ${items.length.toLocaleString()}` : "";
      }
      if ($("live-asof")) {
        $("live-asof").textContent = `${data.label || focus}${data.is_open ? " · open" : " · closed"} · ${
          data.as_of ? new Date(data.as_of).toLocaleTimeString() : ""
        }`;
      }
      const note = $("live-market-note");
      if (note) {
        note.hidden = false;
        note.textContent = data.note || "";
        if (data.session?.local_time) {
          note.textContent += ` · local ${data.session.local_time}${data.session.hint ? ` · ${data.session.hint}` : ""}`;
        }
      }
      syncMarketPillsOpenState(data.focuses || state.marketClocks?.focuses);
      renderLiveTape(items);
      renderLiveBoardView(items, data);
    } catch (e) {
      if (fetchId !== state.liveFetchId) return;
      if (err) {
        err.hidden = false;
        err.textContent = e.message;
      }
      if (!opts.quiet) box.innerHTML = `<div class="banner error">${escapeHtml(e.message)}</div>`;
    }
  }

  function syncMarketPillsOpenState(focuses) {
    if (!focuses?.length) return;
    const openIds = new Set(focuses.filter((f) => f.is_open).map((f) => f.id));
    // US venues share NY session
    const usOpen = openIds.has("us") || openIds.has("nasdaq") || focuses.some((f) => f.session_id === "nyse" && f.is_open);
    document.querySelectorAll("[data-mkt-focus]").forEach((btn) => {
      const id = btn.dataset.mktFocus;
      const isUs = ["us", "nasdaq", "nyse", "arca", "amex"].includes(id);
      btn.classList.toggle("open-dot", isUs ? usOpen : openIds.has(id));
    });
  }

  function renderLiveTable(items) {
    const rows = items
      .slice(0, 600)
      .map((r) => {
        const active = state.liveSymbol === r.symbol ? " active" : "";
        return `<tr class="${active}" data-symbol="${escapeHtml(r.symbol)}">
          <td class="mono"><strong>${escapeHtml(r.symbol)}</strong></td>
          <td>${escapeHtml((r.name || "").slice(0, 28))}</td>
          <td class="mono">${fmtPx(r.price)}</td>
          <td class="mono ${pctClass(r.change_pct_day)}">${fmtPct(r.change_pct_day)}</td>
          <td class="mono ${pctClass(r.change_pct_week)}">${fmtPct(r.change_pct_week)}</td>
          <td class="mono">${fmtVol(r.volume)}</td>
          <td class="mono">${r.rel_volume != null ? Number(r.rel_volume).toFixed(2) : "—"}</td>
          <td class="muted">${escapeHtml(r.exchange || "—")}</td>
          <td>${miniSparkSvg(r.sparkline || [])}</td>
        </tr>`;
      })
      .join("");
    return `<table class="live-table">
      <thead><tr>
        <th>Sym</th><th>Name</th><th>Last</th><th>Day %</th><th>Week %</th><th>Vol</th><th>RVol</th><th>Mkt</th><th></th>
      </tr></thead>
      <tbody>${rows || `<tr><td colspan="9"><div class="empty">No rows</div></td></tr>`}</tbody>
    </table>`;
  }

  function renderLiveMarkets(items, markets) {
    const groups = {};
    for (const r of items) {
      const ex = r.exchange || "Unknown";
      (groups[ex] || (groups[ex] = [])).push(r);
    }
    const order = (markets || [])
      .map((m) => m.exchange)
      .filter((ex) => groups[ex]?.length);
    for (const ex of Object.keys(groups)) {
      if (!order.includes(ex)) order.push(ex);
    }
    if (!order.length) return `<div class="empty">No market groups yet</div>`;
    return `<div class="live-markets">${order
      .map((ex) => {
        const rows = groups[ex] || [];
        const vol = rows.reduce((a, r) => a + (Number(r.volume) || 0), 0);
        const avg =
          rows.reduce((a, r) => a + (Number(r.change_pct_day) || 0), 0) / Math.max(1, rows.length);
        const tiles = renderLiveTiles(rows.slice(0, 48));
        return `<section class="live-market-group">
          <div class="live-market-head">
            <strong>${escapeHtml(ex)}</strong>
            <span class="muted mono">${rows.length} · vol ${fmtVol(vol)} · avg ${fmtPct(avg)}</span>
          </div>
          <div class="live-market-tiles">${tiles}</div>
        </section>`;
      })
      .join("")}</div>`;
  }

  function renderLiveBoardView(items, meta = {}) {
    const box = $("live-heat");
    if (!box) return;
    const view = $("live-view")?.value || "tiles";
    const sortKey = $("live-sort")?.value || meta.sort || "abs_change";
    const sorted = sortLiveItemsClient(items || [], sortKey);
    box.className = `live-heat view-${view}`;
    if (!sorted.length) {
      box.innerHTML = `<div class="empty">Waiting for quotes — use Fill quotes to map more tickers, or Sync listings on Universe.</div>`;
      return;
    }
    const cap = liveDisplayCap(view);
    const shown = view === "markets" ? sorted : sorted.slice(0, cap);
    let html = "";
    try {
      if (view === "blocks") html = renderLiveTiles(shown, { blocks: true });
      else if (view === "bubbles") html = renderLiveBubbles(shown);
      else if (view === "table") html = renderLiveTable(shown);
      else if (view === "markets") html = renderLiveMarkets(shown, meta.markets || []);
      else html = renderLiveTiles(shown);
    } catch (e) {
      box.innerHTML = `<div class="banner error">View render failed: ${escapeHtml(e.message || String(e))}</div>`;
      return;
    }
    const note =
      sorted.length > shown.length && view !== "markets"
        ? `<div class="muted live-view-note">Showing top ${shown.length.toLocaleString()} of ${sorted.length.toLocaleString()} · change Sort to reshuffle</div>`
        : "";
    box.innerHTML = note + html;
    bindLiveBoardClicks(box, sorted);
  }

  async function fillLiveQuotes() {
    toast("Filling quote coverage…");
    try {
      const r = await api("/api/universe/refresh-quotes?batch=320", {
        method: "POST",
        timeoutMs: 180000,
      });
      toast(`Mapped ${r.updated}/${r.batch_size} · cache ${r.quoted}/${r.total}${r.bulk_hits != null ? ` · bulk ${r.bulk_hits}` : ""}`);
      await loadLiveBoard({ forceRefresh: true });
    } catch (e) {
      toast(e.message);
    }
  }

  async function loadLiveBoard(opts = {}) {
    const box = $("live-heat");
    const err = $("live-error");
    const newsEl = $("live-news");
    if (!box) return;
    if (err) err.hidden = true;

    const focus = state.liveMarketFocus || "us";
    if (focus !== "us") {
      const note = $("live-market-note");
      if (note && focus !== "us") note.hidden = false;
      return loadFocusedMarketBoard(opts);
    }
    const noteEl = $("live-market-note");
    if (noteEl) {
      noteEl.hidden = true;
      noteEl.textContent = "";
    }

    const mode = $("live-mode")?.value || "universe";
    const fullUniverse = mode === "universe";
    const fetchId = ++state.liveFetchId;
    const sortKey = $("live-sort")?.value || "abs_change";
    try {
      if (!opts.quiet) {
        const batch = fullUniverse ? 220 : 80;
        api(`/api/universe/refresh-quotes?batch=${batch}`, { method: "POST" }).catch(() => {});
      }
      const params = new URLSearchParams({
        mode: fullUniverse ? "universe" : mode,
        limit: fullUniverse ? "0" : mode === "heat" ? "180" : "120",
        // Full-universe enrich is too slow and races with sort/view changes
        enrich: opts.quiet || fullUniverse ? "false" : "true",
        sort: sortKey,
        asset_class: $("live-class")?.value || "",
        exchange: $("live-exchange")?.value || "",
      });
      const data = await api(`/api/live?${params}`, { timeoutMs: 120000 });
      if (fetchId !== state.liveFetchId) return; // stale response — a newer load won

      const items = sortLiveItemsClient(data.items || [], $("live-sort")?.value || sortKey);
      state.liveItems = items;
      state.liveMeta = data;

      const cov = data.coverage || {};
      const quoted = cov.quoted ?? data.quoted_universe ?? items.length;
      const total = cov.total || 0;
      $("live-asof").textContent = data.as_of
        ? `${quoted.toLocaleString()} quoted · ${new Date(data.as_of).toLocaleTimeString()}`
        : "—";
      if ($("live-stats")) $("live-stats").textContent = items.length.toLocaleString();
      const breadth = data.breadth || {};
      if ($("live-up")) $("live-up").textContent = (breadth.up ?? "—").toLocaleString?.() ?? String(breadth.up ?? "—");
      if ($("live-down")) $("live-down").textContent = (breadth.down ?? "—").toLocaleString?.() ?? String(breadth.down ?? "—");
      if ($("live-coverage-fill")) {
        $("live-coverage-fill").style.width = `${Math.min(100, cov.pct || 0)}%`;
      }
      if ($("live-coverage-label")) {
        $("live-coverage-label").textContent = total
          ? `${quoted.toLocaleString()} / ${total.toLocaleString()} (${cov.pct ?? 0}%)`
          : `${quoted.toLocaleString()} quoted`;
      }
      if ($("live-board-count")) {
        $("live-board-count").textContent = items.length ? `· ${items.length.toLocaleString()}` : "";
      }
      const chip = $("live-mkt-chip");
      if (chip && data.market_status) {
        chip.hidden = false;
        chip.textContent = data.market_status.is_open ? "US open" : "US closed";
        chip.className = data.market_status.is_open ? "chip live" : "chip";
      }
      syncMarketPillsOpenState(state.marketClocks?.focuses);

      renderLiveTape(items);
      renderLiveBoardView(items, data);

      if (state.liveSymbol) {
        const row = items.find((x) => x.symbol === state.liveSymbol);
        if (row) {
          $("live-chart-px").textContent = fmtPx(row.price);
          const chgEl = $("live-chart-chg");
          if (chgEl) {
            chgEl.textContent = fmtPct(row.change_pct_day);
            chgEl.className = `mono ${pctClass(row.change_pct_day)}`;
          }
        }
      }

      if (newsEl) {
        const news = data.news || [];
        if (news.length) {
          newsEl.innerHTML = news
            .slice(0, 10)
            .map((n, i) => {
              const href = n.url || "#";
              return `<a class="live-news-item" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer" style="animation-delay:${i * 40}ms">
                <strong>${escapeHtml(n.headline || "")}</strong>
                <span class="muted">${escapeHtml(n.source || "Finnhub")}</span>
              </a>`;
            })
            .join("");
        } else if (!opts.quiet) {
          newsEl.innerHTML = `<div class="live-news-empty">Add a Finnhub key for live headlines.</div>`;
        }
      }
    } catch (e) {
      if (fetchId !== state.liveFetchId) return;
      if (err) {
        err.hidden = false;
        err.textContent = e.message;
      }
      if (!opts.quiet) box.innerHTML = `<div class="banner error">${escapeHtml(e.message)}</div>`;
    }
  }

  let docsNavLoaded = false;
  let docsActiveId = null;

  async function loadDocsNav() {
    const nav = $("docs-nav");
    if (!nav) return;
    try {
      const data = await api("/api/docs");
      const docs = data.docs || [];
      const groups = {};
      docs.forEach((d) => {
        const g = d.group || "Docs";
        if (!groups[g]) groups[g] = [];
        groups[g].push(d);
      });
      nav.innerHTML = Object.entries(groups)
        .map(([group, rows]) => {
          const items = rows
            .map((d) => {
              const miss = d.exists === false ? " muted" : "";
              const active = d.id === docsActiveId ? " active" : "";
              return `<button type="button" class="docs-nav-item${active}${miss}" data-doc-id="${escapeHtml(d.id)}">${escapeHtml(d.title)}</button>`;
            })
            .join("");
          return `<div class="docs-nav-group"><div class="docs-nav-label">${escapeHtml(group)}</div>${items}</div>`;
        })
        .join("");
      nav.querySelectorAll("[data-doc-id]").forEach((btn) => {
        btn.addEventListener("click", () => openDoc(btn.dataset.docId));
      });
      docsNavLoaded = true;
      if (!docsActiveId && docs[0]) {
        await openDoc(docs[0].id);
      } else if (docsActiveId) {
        await openDoc(docsActiveId);
      }
    } catch (e) {
      nav.innerHTML = `<div class="banner error">${escapeHtml(e.message)}</div>`;
    }
  }

  async function openDoc(docId) {
    if (!docId) return;
    docsActiveId = docId;
    document.querySelectorAll(".docs-nav-item").forEach((b) => {
      b.classList.toggle("active", b.dataset.docId === docId);
    });
    const title = $("docs-title");
    const meta = $("docs-meta");
    const body = $("docs-content");
    if (body) body.innerHTML = `<div class="skeleton" style="height:8rem"></div>`;
    try {
      const doc = await api(`/api/docs/${encodeURIComponent(docId)}`);
      if (title) title.textContent = doc.title || docId;
      if (meta) {
        const bits = [doc.group, doc.source];
        if (doc.path) bits.push(doc.path);
        meta.textContent = bits.filter(Boolean).join(" · ");
      }
      if (body) body.innerHTML = doc.html || `<pre class="docs-pre">${escapeHtml(doc.markdown || "")}</pre>`;
    } catch (e) {
      if (body) body.innerHTML = `<div class="banner error">${escapeHtml(e.message)}</div>`;
    }
  }

  async function loadSettingsAbout() {
    const log = $("settings-health-log");
    if (!log) return;
    try {
      const h = await api("/api/health");
      log.textContent = JSON.stringify(
        {
          broker: h.broker,
          data_provider: h.data_provider,
          live: h.live,
          ollama: h.ollama,
          mcp: h.mcp,
          us_open: h.us_open ?? h.market?.us_open,
        },
        null,
        2
      );
    } catch (e) {
      log.textContent = e.message;
    }
  }

  async function ollamaAction(action) {
    const log = $("svc-ollama-log");
    if (log) log.textContent = `Running ${action}…`;
    toast(`Ollama: ${action}…`);
    try {
      const res = await api("/api/services/ollama", {
        method: "POST",
        body: JSON.stringify({ action }),
        timeoutMs: action === "warm" ? 180000 : 30000,
      });
      if (log) log.textContent = JSON.stringify(res, null, 2);
      toast(res.message || res.error || `Ollama ${action} done`);
      await loadHealth();
    } catch (e) {
      if (log) log.textContent = e.message;
      toast(e.message);
    }
  }

  async function mcpAction(action) {
    const log = $("svc-mcp-log");
    if (log) log.textContent = `Running ${action}…`;
    toast(`MCP: ${action}…`);
    try {
      const res = await api(`/api/services/mcp/${encodeURIComponent(action)}`, {
        method: "POST",
        body: "{}",
      });
      let text = JSON.stringify(res, null, 2);
      if (res.log_tail) text += `\n\n--- log ---\n${res.log_tail}`;
      if (log) log.textContent = text;
      if (res.ok === false) toast(res.message || `MCP ${action} failed`, 5000);
      else toast(res.message || `MCP ${action}`);
      await loadHealth();
    } catch (e) {
      if (log) log.textContent = e.message;
      toast(e.message);
    }
  }

  async function loadAcquireKeys() {
    const box = $("acquire-keys");
    if (!box) return;
    const [links, settings] = await Promise.all([api("/api/key-links"), api("/api/settings")]);
    const providers = links.providers || {};
    const secrets = settings.secrets || {};
    const map = {
      alpaca: "ALPACA_API_KEY",
      public: "PUBLIC_PERSONAL_SECRET",
      tradier: "TRADIER_ACCESS_TOKEN",
      finnhub: "FINNHUB_API_KEY",
      alphavantage: "ALPHAVANTAGE_API_KEY",
    };
    box.innerHTML = Object.entries(providers)
      .map(([id, p]) => {
        const configured = !!secrets[map[id]]?.configured;
        return `<div class="acquire-card">
          <strong>${escapeHtml(p.label)}</strong>
          <span class="muted">${configured ? "configured" : "missing — get a key"}</span>
          <a class="btn primary" href="${p.signup}" target="_blank" rel="noopener">Sign up</a>
          <a class="btn" href="${p.keys}" target="_blank" rel="noopener">Get keys</a>
        </div>`;
      })
      .join("");
  }

  const tourState = {
    active: false,
    index: 0,
    target: null,
    pad: 10,
    gen: 0,
    busy: false,
    pending: null, // "next" | "back" | null
  };

  const TOUR_STEPS = [
    {
      target: "brand",
      title: "Welcome to Infobroker",
      body: "This is your technical trading desk — paper or live brokers, market data, lessons, and Grapevine. We’ll walk every major area. Use Back, Next, or Done anytime.",
    },
    {
      target: "status-chips",
      title: "Status chips",
      body: "Quick health check: which broker is executing, which data source is quoting, paper vs live mode, and whether Ollama (Grapevine) is reachable.",
    },
    {
      target: "top-actions",
      title: "Refresh · Scan · Hunt",
      body: "Refresh reloads quotes and account. Scan scores your watchlist for setups. Hunt asks Grapevine to look for careful paper trades.",
    },
    {
      target: "api-keys-btn",
      title: "API Keys",
      body: "Open the keys modal to paste Alpaca, Public, Tradier, or optional Finnhub / Alpha Vantage credentials. Secrets stay in local .env.",
    },
    {
      target: "account",
      title: "Account",
      body: "Cash, equity, buying power, and open positions. Click a symbol to inspect it; Sell pre-fills the order ticket.",
    },
    {
      target: "watchlist",
      title: "Watchlist",
      body: "Add tickers you care about. Everything in Markets Board, Scanner, and Hunt draws from this list.",
    },
    {
      target: "learn-rail",
      title: "Learn shortcuts",
      body: "Jump into the Learning tab or start the tutor path from here. A short lesson rail opens multi-page readers without cluttering the desk.",
    },
    {
      target: "desk-tabs",
      title: "Desk pages",
      body: "Markets starts on Live (Finviz-style heat board), then Universe, Board, Movers, Scanner, Symbol. Chart studio charts are inspectable — hover, drag-zoom, wheel.",
      tab: "markets",
      sub: "board",
    },
    {
      target: "markets-subtabs",
      title: "Markets sections",
      body: "Board = your tracked table. Movers = who is moving. Scanner = signal results. Symbol = one-ticker deep dive.",
      tab: "markets",
      sub: "board",
    },
    {
      target: "markets-board",
      title: "Board",
      body: "Indices plus every tracked ticker with day/week %, relative volume, and a sparkline. Click a row to open Symbol.",
      tab: "markets",
      sub: "board",
    },
    {
      target: "markets-movers",
      title: "Movers",
      body: "Notable names in your list, volume leaders, and day/week gainers & losers. Use this to decide what deserves a closer look.",
      tab: "markets",
      sub: "movers",
    },
    {
      target: "markets-scanner",
      title: "Scanner",
      body: "Press Scan in the top bar; results land here with setup tips. Tap a card to open that symbol’s detail.",
      tab: "markets",
      sub: "scanner",
    },
    {
      target: "markets-symbol",
      title: "Symbol detail",
      body: "Quote, line or candle chart, tip, and fundamentals. Trade this loads the ticket; Chart studio opens the full pack.",
      tab: "markets",
      sub: "symbol",
    },
    {
      target: "learning-subtabs",
      title: "Learning pages",
      body: "Tutor first (ways to trade), then Trade journal (your annotated history), then Skill lessons (candles, risk, indicators…).",
      tab: "learning",
      sub: "tutor",
    },
    {
      target: "learning-tutor",
      title: "Tutor path",
      body: "A teacher-style 10-page path through market, limit, stop, brackets, styles, and risk. Start or Continue; progress is remembered.",
      tab: "learning",
      sub: "tutor",
    },
    {
      target: "learning-journal",
      title: "Trade journal",
      body: "Real blotter orders with the idea behind each trade and a tutor tip. Demo stories appear until you place paper orders.",
      tab: "learning",
      sub: "journal",
    },
    {
      target: "learning-lessons",
      title: "Skill lessons",
      body: "Multi-page lessons with insights, practice, and quizzes. Arrow keys step pages; Ask Grapevine continues as your tutor.",
      tab: "learning",
      sub: "lessons",
    },
    {
      target: "strategies",
      title: "Strategies",
      body: "Pick a base educational strategy, set dates, run a free yfinance backtest, and read the equity curve before sizing risk.",
      tab: "strategies",
    },
    {
      target: "charts",
      title: "Chart studio",
      body: "Load price + SMAs, volume, RSI, and MACD for one ticker. Use this when Symbol’s mini-chart isn’t enough.",
      tab: "charts",
    },
    {
      target: "services",
      title: "Services & keys",
      body: "Warm Ollama, start/stop MCP, and acquire missing API keys. Keep Grapevine healthy from the Ollama / MCP / Keys sub-tabs.",
      tab: "services",
      sub: "ollama",
    },
    {
      target: "order-ticket",
      title: "Order ticket",
      body: "Market, limit, stop, stop-limit, plus optional stop-loss / take-profit brackets. Always Preview risk before Submit — especially on paper.",
      tab: "markets",
      sub: "board",
    },
    {
      target: "order-blotter",
      title: "Order blotter",
      body: "Working and recent orders. Cancel open ones here; filled trades also show up annotated in Learning → Trade journal.",
      tab: "markets",
      sub: "board",
    },
    {
      target: "quick-backtest",
      title: "Quick backtest",
      body: "Fast SMA crossover check from the trade rail. For more strategies and a fuller equity chart, use the Strategies page.",
      tab: "markets",
      sub: "board",
    },
    {
      target: "brokers",
      title: "Brokers",
      body: "Which execution venues are configured. Switch the active broker from API Keys; paper is the safe default while you learn.",
      tab: "markets",
      sub: "board",
    },
    {
      target: "assistant",
      title: "Grapevine assistant",
      body: "Your multimodal desk agent. Find trades, Send view (screenshot), chat, and watch tool calls in the action stream. Prefer paper until you’re comfortable.",
      tab: "markets",
      sub: "board",
    },
    {
      target: "btn-tour",
      title: "You’re ready",
      body: "That’s the desk. Re-run this tour anytime with Tour. Next: start the tutor path in Learning, or add a watchlist ticker and Scan.",
      tab: "learning",
      sub: "tutor",
    },
  ];

  function tourTargetEl(step) {
    if (!step?.target) return null;
    if (step.target === "btn-tour") return $("btn-tour");
    return document.querySelector(`[data-tour="${step.target}"]`);
  }

  function clearTourHighlight() {
    document.querySelectorAll(".tour-highlight").forEach((el) => el.classList.remove("tour-highlight"));
    tourState.target = null;
  }

  function endTour(markDone = true) {
    tourState.active = false;
    tourState.busy = false;
    tourState.pending = null;
    tourState.gen += 1;
    clearTourHighlight();
    const root = $("tour-root");
    if (root) root.hidden = true;
    document.body.classList.remove("tour-open");
    const overlay = $("tour-overlay");
    if (overlay) overlay.style.clipPath = "";
    if (markDone) {
      try {
        localStorage.setItem("infobroker_tour_done", "1");
      } catch {
        /* ignore */
      }
    }
  }

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function positionTourUI() {
    const step = TOUR_STEPS[tourState.index];
    const el = tourTargetEl(step);
    const spot = $("tour-spotlight");
    const sheet = $("tour-sheet");
    if (!spot || !sheet) return;

    const pad = tourState.pad;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const sheetRect = sheet.getBoundingClientRect();
    // Keep spotlight entirely above the bottom sheet + gap
    const maxBottom = Math.max(120, (sheetRect.top || vh * 0.62) - 16);

    let rect = el ? el.getBoundingClientRect() : null;
    if (!rect || rect.width < 2 || rect.height < 2) {
      rect = {
        top: vh * 0.2,
        left: vw / 2 - 140,
        width: 280,
        height: 72,
      };
    }

    let top = clamp(rect.top - pad, 8, maxBottom - 48);
    let left = clamp(rect.left - pad, 8, vw - 48);
    let width = clamp(rect.width + pad * 2, 40, vw - left - 8);
    let height = clamp(rect.height + pad * 2, 40, maxBottom - top);

    // Tall targets: spotlight the visible top band only
    if (height > maxBottom - top) height = Math.max(48, maxBottom - top);
    if (height > vh * 0.42) height = vh * 0.42;

    spot.style.top = `${top}px`;
    spot.style.left = `${left}px`;
    spot.style.width = `${width}px`;
    spot.style.height = `${height}px`;

    const overlay = $("tour-overlay");
    if (overlay) {
      const x1 = left;
      const y1 = top;
      const x2 = left + width;
      const y2 = top + height;
      overlay.style.clipPath = `polygon(evenodd, 0px 0px, ${vw}px 0px, ${vw}px ${vh}px, 0px ${vh}px, 0px 0px, ${x1}px ${y1}px, ${x1}px ${y2}px, ${x2}px ${y2}px, ${x2}px ${y1}px, ${x1}px ${y1}px)`;
    }
  }

  async function showTourStep(index) {
    if (!tourState.active || index < 0 || index >= TOUR_STEPS.length) return;
    const gen = ++tourState.gen;
    tourState.index = index;
    const step = TOUR_STEPS[index];
    const isFirst = index === 0;
    const isLast = index === TOUR_STEPS.length - 1;

    closeLessonModal();
    closeKeysModal();
    if (step.tab) switchDeskTab(step.tab, step.sub);
    else if (step.sub) switchSubTab("markets", step.sub);

    if ($("tour-step")) $("tour-step").textContent = `${index + 1} / ${TOUR_STEPS.length}`;
    $("tour-title").textContent = step.title;
    $("tour-body").textContent = step.body;
    if ($("btn-tour-back")) $("btn-tour-back").disabled = isFirst;
    if ($("btn-tour-next")) {
      $("btn-tour-next").textContent = isLast ? "Finish" : "Next";
      $("btn-tour-next").disabled = false;
    }

    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    if (!tourState.active || gen !== tourState.gen) return;

    clearTourHighlight();
    const el = tourTargetEl(step);
    if (el) {
      try {
        // Prefer centering so there is room above/below for the popup
        el.scrollIntoView({ block: "center", inline: "nearest", behavior: "auto" });
      } catch {
        el.scrollIntoView(true);
      }
      el.classList.add("tour-highlight");
      tourState.target = el;
    }
    if (!tourState.active || gen !== tourState.gen) return;
    positionTourUI();
    // Reposition after layout settles (fonts / scroll)
    requestAnimationFrame(() => {
      if (tourState.active && gen === tourState.gen) positionTourUI();
    });
  }

  function startTour() {
    const root = $("tour-root");
    if (!root) return;
    tourState.active = true;
    tourState.index = 0;
    tourState.pending = null;
    tourState.busy = false;
    root.hidden = false;
    document.body.classList.add("tour-open");
    const overlay = $("tour-overlay");
    if (overlay) overlay.style.clipPath = "";
    showTourStep(0);
  }

  function tourNext() {
    if (!tourState.active) return;
    if (tourState.index >= TOUR_STEPS.length - 1) {
      endTour(true);
      toast("Tour complete — open Learning → Tutor when you’re ready");
      return;
    }
    showTourStep(tourState.index + 1);
  }

  function tourBack() {
    if (!tourState.active || tourState.index <= 0) return;
    showTourStep(tourState.index - 1);
  }

  async function init() {
    bind();
    applyButtonTooltips();
    setDefaultDates();
    setStudioDates();
    setupAutoRefresh();
    startMarketClocks();
    try {
      await loadHealth();
      await Promise.all([loadLessons(), loadBrokers(), refreshMarket(), loadStrategies().catch(() => {})]);
      try {
        const sub = localStorage.getItem("infobroker_subtab_markets") || "live";
        switchSubTab("markets", sub);
      } catch {
        switchSubTab("markets", "live");
      }
      if (state.watchlist[0]) selectSymbol(state.watchlist[0]);
      runScan().catch(() => {});
      refreshActionFeed().catch(() => {});
      loadAcquireKeys().catch(() => {});
    } catch (e) {
      toast(`Init failed: ${e.message}`, 5000);
    }
  }

  init();
})();
