/* Interactive chart helpers: axes, crosshair inspect, zoom/brush */
(() => {
  const PAD = { L: 8, R: 56, T: 14, B: 26 };

  function fmtPx(v) {
    if (v == null || Number.isNaN(Number(v))) return "—";
    const n = Number(v);
    if (Math.abs(n) >= 1000) return n.toFixed(2);
    if (Math.abs(n) >= 1) return n.toFixed(2);
    return n.toFixed(4);
  }

  function fmtVol(v) {
    if (v == null || Number.isNaN(Number(v))) return "—";
    const n = Number(v);
    if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
    if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
    if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
    return String(Math.round(n));
  }

  function fmtDate(t) {
    if (!t) return "—";
    const d = new Date(t);
    if (Number.isNaN(d.getTime())) return String(t).slice(0, 10);
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "2-digit" });
  }

  function clamp(n, a, b) {
    return Math.max(a, Math.min(b, n));
  }

  function viewSlice(bars, view) {
    if (!bars?.length) return { bars: [], start: 0, end: 0 };
    const n = bars.length;
    let start = view?.start ?? 0;
    let end = view?.end ?? n;
    start = clamp(Math.floor(start), 0, Math.max(0, n - 2));
    end = clamp(Math.ceil(end), start + 2, n);
    return { bars: bars.slice(start, end), start, end };
  }

  function plotBox(w, h) {
    return {
      x0: PAD.L,
      y0: PAD.T,
      x1: w - PAD.R,
      y1: h - PAD.B,
      w: Math.max(10, w - PAD.L - PAD.R),
      h: Math.max(10, h - PAD.T - PAD.B),
    };
  }

  function xAt(box, i, n) {
    if (n <= 1) return box.x0 + box.w / 2;
    return box.x0 + (i / (n - 1)) * box.w;
  }

  function idxFromX(box, x, n) {
    if (n <= 1) return 0;
    const t = (x - box.x0) / box.w;
    return clamp(Math.round(t * (n - 1)), 0, n - 1);
  }

  function yAt(box, v, min, max) {
    const span = max - min || 1;
    return box.y0 + ((max - v) / span) * box.h;
  }

  function priceFromY(box, y, min, max) {
    const span = max - min || 1;
    const t = (y - box.y0) / box.h;
    return max - t * span;
  }

  function drawingsStorageKey(symbol) {
    return `infobroker_draw_${String(symbol || "").toUpperCase()}`;
  }

  function loadStoredDrawings(symbol) {
    if (!symbol) return [];
    try {
      const raw = localStorage.getItem(drawingsStorageKey(symbol));
      const list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list : [];
    } catch {
      return [];
    }
  }

  function saveStoredDrawings(symbol, drawings) {
    if (!symbol) return;
    try {
      localStorage.setItem(drawingsStorageKey(symbol), JSON.stringify(drawings || []));
    } catch {
      /* ignore quota */
    }
  }

  function projectAbs(box, bars, viewStart, absIdx, price, min, max) {
    const n = Math.max(bars.length, 2);
    const rel = absIdx - viewStart;
    const x = box.x0 + (rel / (n - 1)) * box.w;
    const y = yAt(box, price, min, max);
    return { x, y };
  }

  function drawDrawings(ctx, box, bars, viewStart, min, max, drawings, draft) {
    const list = [...(drawings || [])];
    if (draft) list.push(draft);
    ctx.save();
    list.forEach((d) => {
      if (!d) return;
      if (d.type === "hline" && d.price != null) {
        const y = yAt(box, d.price, min, max);
        ctx.strokeStyle = d.draft ? "rgba(125, 211, 252, 0.65)" : "#7dd3fc";
        ctx.lineWidth = 1.4;
        ctx.setLineDash(d.draft ? [5, 4] : []);
        ctx.beginPath();
        ctx.moveTo(box.x0, y);
        ctx.lineTo(box.x1, y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = "#7dd3fc";
        ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
        ctx.textAlign = "left";
        ctx.textBaseline = "bottom";
        ctx.fillText(fmtPx(d.price), box.x0 + 4, y - 2);
      } else if (d.type === "trend" && d.i0 != null && d.i1 != null) {
        const a = projectAbs(box, bars, viewStart, d.i0, d.p0, min, max);
        const b = projectAbs(box, bars, viewStart, d.i1, d.p1, min, max);
        ctx.strokeStyle = d.draft ? "rgba(245, 196, 81, 0.7)" : "#f5c451";
        ctx.lineWidth = 1.6;
        ctx.setLineDash(d.draft ? [5, 4] : []);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = ctx.strokeStyle;
        [a, b].forEach((pt) => {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 3.2, 0, Math.PI * 2);
          ctx.fill();
        });
      }
    });
    ctx.restore();
  }

  function drawGrid(ctx, box, min, max, steps = 4) {
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.06)";
    ctx.fillStyle = "rgba(148,163,184,0.75)";
    ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    for (let i = 0; i <= steps; i++) {
      const v = max - ((max - min) * i) / steps;
      const y = box.y0 + (box.h * i) / steps;
      ctx.beginPath();
      ctx.moveTo(box.x0, y);
      ctx.lineTo(box.x1, y);
      ctx.stroke();
      ctx.fillText(fmtPx(v), box.x1 + 6, y);
    }
    ctx.restore();
  }

  function drawXLabels(ctx, box, bars, stepHint = 5) {
    if (!bars.length) return;
    const n = bars.length;
    const step = Math.max(1, Math.ceil(n / stepHint));
    ctx.save();
    ctx.fillStyle = "rgba(148,163,184,0.8)";
    ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (let i = 0; i < n; i += step) {
      const x = xAt(box, i, n);
      const label = fmtDate(bars[i].t || bars[i].date);
      ctx.fillText(label, x, box.y1 + 6);
    }
    ctx.restore();
  }

  function drawLastTag(ctx, box, value, min, max, color) {
    if (value == null) return;
    const y = yAt(box, value, min, max);
    ctx.save();
    ctx.fillStyle = color || "#7dd3fc";
    ctx.fillRect(box.x1 + 2, y - 8, PAD.R - 6, 16);
    ctx.fillStyle = "#0b1220";
    ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(fmtPx(value), box.x1 + (PAD.R - 4) / 2, y);
    ctx.strokeStyle = color || "#7dd3fc";
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(box.x0, y);
    ctx.lineTo(box.x1, y);
    ctx.stroke();
    ctx.restore();
  }

  function drawCrosshair(ctx, box, x, y) {
    ctx.save();
    ctx.strokeStyle = "rgba(226,232,240,0.35)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(x, box.y0);
    ctx.lineTo(x, box.y1);
    ctx.moveTo(box.x0, y);
    ctx.lineTo(box.x1, y);
    ctx.stroke();
    ctx.restore();
  }

  function drawBrush(ctx, box, x0, x1) {
    const a = Math.min(x0, x1);
    const b = Math.max(x0, x1);
    ctx.save();
    ctx.fillStyle = "rgba(94, 200, 216, 0.12)";
    ctx.strokeStyle = "rgba(94, 200, 216, 0.55)";
    ctx.fillRect(a, box.y0, b - a, box.h);
    ctx.strokeRect(a, box.y0, b - a, box.h);
    ctx.restore();
  }

  function priceExtents(bars) {
    const highs = bars.map((b) => b.h ?? b.c).filter((v) => v != null);
    const lows = bars.map((b) => b.l ?? b.c).filter((v) => v != null);
    const min = Math.min(...lows);
    const max = Math.max(...highs);
    const pad = (max - min) * 0.04 || 0.01;
    return { min: min - pad, max: max + pad };
  }

  function drawCandles(ctx, box, bars, min, max) {
    const n = bars.length;
    const slot = box.w / n;
    bars.forEach((b, i) => {
      const x = box.x0 + i * slot + slot / 2;
      const yH = yAt(box, b.h, min, max);
      const yL = yAt(box, b.l, min, max);
      const yO = yAt(box, b.o, min, max);
      const yC = yAt(box, b.c, min, max);
      const up = b.c >= b.o;
      ctx.strokeStyle = up ? "#7dce82" : "#f07178";
      ctx.fillStyle = up ? "#7dce82" : "#f07178";
      ctx.beginPath();
      ctx.moveTo(x, yH);
      ctx.lineTo(x, yL);
      ctx.stroke();
      const top = Math.min(yO, yC);
      const body = Math.max(2, Math.abs(yC - yO));
      ctx.fillRect(x - Math.max(1, slot * 0.28), top, Math.max(2, slot * 0.56), body);
    });
  }

  function drawCloseLine(ctx, box, bars, min, max) {
    const n = bars.length;
    const up = bars[n - 1].c >= bars[0].c;
    ctx.strokeStyle = up ? "#7dce82" : "#f07178";
    ctx.lineWidth = 2;
    ctx.beginPath();
    bars.forEach((b, i) => {
      const x = xAt(box, i, n);
      const y = yAt(box, b.c, min, max);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  function drawSma(ctx, box, bars, key, color, min, max) {
    const n = bars.length;
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.1;
    ctx.beginPath();
    let started = false;
    bars.forEach((b, i) => {
      const v = b[key];
      if (v == null) return;
      const x = xAt(box, i, n);
      const y = yAt(box, v, min, max);
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else ctx.lineTo(x, y);
    });
    if (started) ctx.stroke();
  }

  function drawPriceChart(canvas, bars, opts = {}) {
    if (!canvas) return null;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (!bars || bars.length < 2) {
      ctx.fillStyle = "rgba(148,163,184,0.5)";
      ctx.font = "12px sans-serif";
      ctx.fillText("No bars", 16, h / 2);
      return null;
    }
    const box = plotBox(w, h);
    const { min, max } = priceExtents(bars);
    drawGrid(ctx, box, min, max, 4);
    drawXLabels(ctx, box, bars);
    if (opts.mode === "line") drawCloseLine(ctx, box, bars, min, max);
    else drawCandles(ctx, box, bars, min, max);
    if (opts.smas) {
      drawSma(ctx, box, bars, "sma20", "#7dd3fc", min, max);
      drawSma(ctx, box, bars, "sma50", "#f5c451", min, max);
      drawSma(ctx, box, bars, "sma200", "#c4b5fd", min, max);
    }
    const last = bars[bars.length - 1].c;
    drawLastTag(ctx, box, last, min, max, bars[bars.length - 1].c >= bars[0].c ? "#7dce82" : "#f07178");
    if (opts.drawings || opts.draft) {
      drawDrawings(
        ctx,
        box,
        bars,
        opts.viewStart ?? 0,
        min,
        max,
        opts.drawings,
        opts.draft
      );
    }
    if (opts.hoverIdx != null && opts.hoverIdx >= 0 && opts.hoverIdx < bars.length) {
      const b = bars[opts.hoverIdx];
      const x = xAt(box, opts.hoverIdx, bars.length);
      const y = yAt(box, b.c, min, max);
      drawCrosshair(ctx, box, x, y);
    }
    if (opts.brush) {
      const n = bars.length;
      const x0 = xAt(box, opts.brush.a, n);
      const x1 = xAt(box, opts.brush.b, n);
      drawBrush(ctx, box, x0, x1);
    }
    return { box, min, max };
  }

  function drawVolumeChart(canvas, bars, opts = {}) {
    if (!canvas) return null;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (!bars?.length) return null;
    const box = plotBox(w, h);
    const vols = bars.map((b) => b.v || 0);
    const max = Math.max(...vols) || 1;
    drawGrid(ctx, box, 0, max, 3);
    const slot = box.w / bars.length;
    const bw = Math.max(1, slot * 0.7);
    bars.forEach((b, i) => {
      const x = box.x0 + i * slot + (slot - bw) / 2;
      const bh = ((b.v || 0) / max) * box.h;
      ctx.fillStyle = b.c >= b.o ? "rgba(125, 211, 252, 0.55)" : "rgba(240, 113, 120, 0.55)";
      ctx.fillRect(x, box.y1 - bh, bw, bh);
    });
    drawLastTag(ctx, box, vols[vols.length - 1], 0, max, "#7dd3fc");
    if (opts.hoverIdx != null && opts.hoverIdx >= 0) {
      const x = xAt(box, opts.hoverIdx, bars.length);
      drawCrosshair(ctx, box, x, box.y0 + box.h / 2);
    }
    return { box, min: 0, max };
  }

  function drawRsiChart(canvas, bars, opts = {}) {
    if (!canvas) return null;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (!bars?.length) return null;
    const box = plotBox(w, h);
    const min = 0;
    const max = 100;
    drawGrid(ctx, box, min, max, 4);
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.12)";
    [30, 70].forEach((lvl) => {
      const y = yAt(box, lvl, min, max);
      ctx.beginPath();
      ctx.moveTo(box.x0, y);
      ctx.lineTo(box.x1, y);
      ctx.stroke();
    });
    ctx.restore();
    const n = bars.length;
    ctx.strokeStyle = "#f5c451";
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    let started = false;
    bars.forEach((b, i) => {
      if (b.rsi == null) return;
      const x = xAt(box, i, n);
      const y = yAt(box, b.rsi, min, max);
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else ctx.lineTo(x, y);
    });
    if (started) ctx.stroke();
    const lastRsi = [...bars].reverse().find((b) => b.rsi != null)?.rsi;
    drawLastTag(ctx, box, lastRsi, min, max, "#f5c451");
    if (opts.hoverIdx != null && opts.hoverIdx >= 0 && bars[opts.hoverIdx]?.rsi != null) {
      const x = xAt(box, opts.hoverIdx, n);
      const y = yAt(box, bars[opts.hoverIdx].rsi, min, max);
      drawCrosshair(ctx, box, x, y);
    }
    return { box, min, max };
  }

  function drawMacdChart(canvas, bars, opts = {}) {
    if (!canvas) return null;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (!bars?.length) return null;
    const box = plotBox(w, h);
    const vals = bars.flatMap((b) => [b.macd, b.macd_hist, b.macd_signal].filter((v) => v != null));
    const abs = Math.max(...vals.map(Math.abs), 0.01);
    const min = -abs;
    const max = abs;
    drawGrid(ctx, box, min, max, 4);
    const n = bars.length;
    const slot = box.w / n;
    const bw = Math.max(1, slot * 0.65);
    const mid = yAt(box, 0, min, max);
    bars.forEach((b, i) => {
      if (b.macd_hist == null) return;
      const x = box.x0 + i * slot + (slot - bw) / 2;
      const y = yAt(box, b.macd_hist, min, max);
      ctx.fillStyle = b.macd_hist >= 0 ? "rgba(125, 211, 252, 0.7)" : "rgba(240, 113, 120, 0.7)";
      if (y <= mid) ctx.fillRect(x, y, bw, mid - y);
      else ctx.fillRect(x, mid, bw, y - mid);
    });
    const strokeKey = (key, color) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.1;
      ctx.beginPath();
      let started = false;
      bars.forEach((b, i) => {
        if (b[key] == null) return;
        const x = xAt(box, i, n);
        const y = yAt(box, b[key], min, max);
        if (!started) {
          ctx.moveTo(x, y);
          started = true;
        } else ctx.lineTo(x, y);
      });
      if (started) ctx.stroke();
    };
    strokeKey("macd", "#f5c451");
    strokeKey("macd_signal", "#c4b5fd");
    const last = [...bars].reverse().find((b) => b.macd != null)?.macd;
    drawLastTag(ctx, box, last, min, max, "#f5c451");
    if (opts.hoverIdx != null && opts.hoverIdx >= 0) {
      const x = xAt(box, opts.hoverIdx, n);
      drawCrosshair(ctx, box, x, mid);
    }
    return { box, min, max };
  }

  function inspectHtml(bar, absIndex) {
    if (!bar) return "";
    const chg = bar.o ? ((bar.c - bar.o) / bar.o) * 100 : null;
    const chgCls = chg == null ? "" : chg >= 0 ? "up" : "down";
    return `<div class="inspect-row"><span>Date</span><strong>${fmtDate(bar.t || bar.date)}</strong></div>
      <div class="inspect-row"><span>O</span><strong class="mono">${fmtPx(bar.o)}</strong></div>
      <div class="inspect-row"><span>H</span><strong class="mono">${fmtPx(bar.h)}</strong></div>
      <div class="inspect-row"><span>L</span><strong class="mono">${fmtPx(bar.l)}</strong></div>
      <div class="inspect-row"><span>C</span><strong class="mono">${fmtPx(bar.c)}</strong></div>
      <div class="inspect-row"><span>Chg</span><strong class="mono ${chgCls}">${chg == null ? "—" : `${chg >= 0 ? "+" : ""}${chg.toFixed(2)}%`}</strong></div>
      <div class="inspect-row"><span>Vol</span><strong class="mono">${fmtVol(bar.v)}</strong></div>
      ${bar.rsi != null ? `<div class="inspect-row"><span>RSI</span><strong class="mono">${Number(bar.rsi).toFixed(1)}</strong></div>` : ""}
      ${bar.sma20 != null ? `<div class="inspect-row"><span>SMA20</span><strong class="mono">${fmtPx(bar.sma20)}</strong></div>` : ""}
      <div class="inspect-meta mono">bar #${absIndex + 1}</div>`;
  }

  /**
   * Shared inspect/zoom/draw controller for symbol chart canvases.
   * Tools: inspect (zoom/brush), trend (2-click line), hline (price level).
   */
  function createController({
    primaryCanvas,
    tooltipEl,
    onRender,
    getBars,
    symbol = null,
    onDrawingsChange = null,
  }) {
    const state = {
      view: null,
      hoverAbs: null,
      brush: null,
      dragging: false,
      dragStartX: 0,
      tool: "inspect", // inspect | trend | hline
      drawings: loadStoredDrawings(symbol),
      draft: null,
      symbol: symbol || null,
      lastGeom: null, // {box,min,max,start,bars}
    };

    function barsAll() {
      return getBars() || [];
    }

    function persist() {
      if (state.symbol) saveStoredDrawings(state.symbol, state.drawings);
      if (typeof onDrawingsChange === "function") onDrawingsChange(state.drawings);
    }

    function ensureView() {
      const n = barsAll().length;
      if (!n) {
        state.view = { start: 0, end: 0 };
        return state.view;
      }
      if (!state.view) state.view = { start: 0, end: n };
      state.view.start = clamp(state.view.start, 0, Math.max(0, n - 2));
      state.view.end = clamp(state.view.end, state.view.start + 2, n);
      return state.view;
    }

    function visible() {
      return viewSlice(barsAll(), ensureView());
    }

    function updateCursor() {
      primaryCanvas.style.cursor =
        state.tool === "inspect" ? "crosshair" : "cell";
    }

    function redraw() {
      const vis = visible();
      const hoverRel =
        state.hoverAbs == null
          ? null
          : state.hoverAbs >= vis.start && state.hoverAbs < vis.end
            ? state.hoverAbs - vis.start
            : null;
      const payload = {
        bars: vis.bars,
        start: vis.start,
        end: vis.end,
        hoverIdx: state.tool === "inspect" ? hoverRel : hoverRel,
        brush: state.tool === "inspect" ? state.brush : null,
        view: ensureView(),
        drawings: state.drawings,
        draft: state.draft,
        viewStart: vis.start,
        tool: state.tool,
      };
      const geom = onRender(payload);
      if (geom && geom.box) state.lastGeom = { ...geom, start: vis.start, bars: vis.bars };
      if (tooltipEl) {
        const showTip = state.tool === "inspect" && hoverRel != null && vis.bars[hoverRel];
        if (showTip) {
          tooltipEl.hidden = false;
          tooltipEl.innerHTML = inspectHtml(vis.bars[hoverRel], vis.start + hoverRel);
        } else {
          tooltipEl.hidden = true;
        }
      }
    }

    function localXY(ev) {
      const rect = primaryCanvas.getBoundingClientRect();
      const scaleX = primaryCanvas.width / rect.width;
      const scaleY = primaryCanvas.height / rect.height;
      return {
        x: (ev.clientX - rect.left) * scaleX,
        y: (ev.clientY - rect.top) * scaleY,
      };
    }

    function absFromEvent(ev) {
      const vis = visible();
      if (!vis.bars.length) return null;
      const box = plotBox(primaryCanvas.width, primaryCanvas.height);
      const { x } = localXY(ev);
      const rel = idxFromX(box, x, vis.bars.length);
      return vis.start + rel;
    }

    function priceFromEvent(ev) {
      const geom = state.lastGeom;
      const box = geom?.box || plotBox(primaryCanvas.width, primaryCanvas.height);
      let min = geom?.min;
      let max = geom?.max;
      if (min == null || max == null) {
        const vis = visible();
        const ext = priceExtents(vis.bars);
        min = ext.min;
        max = ext.max;
      }
      const { y } = localXY(ev);
      return priceFromY(box, y, min, max);
    }

    function onMove(ev) {
      const abs = absFromEvent(ev);
      if (abs == null) return;
      state.hoverAbs = abs;
      if (state.tool === "inspect" && state.dragging) {
        const vis = visible();
        const box = plotBox(primaryCanvas.width, primaryCanvas.height);
        const a = idxFromX(box, state.dragStartX, vis.bars.length);
        const b = idxFromX(box, localXY(ev).x, vis.bars.length);
        state.brush = { a: Math.min(a, b), b: Math.max(a, b) };
      } else if (state.tool === "trend" && state.draft?.type === "trend") {
        state.draft = {
          ...state.draft,
          i1: abs,
          p1: priceFromEvent(ev),
          draft: true,
        };
      } else if (state.tool === "hline" && state.dragging) {
        state.draft = {
          type: "hline",
          price: priceFromEvent(ev),
          draft: true,
        };
      }
      redraw();
    }

    function onLeave() {
      state.hoverAbs = null;
      if (!state.dragging && state.tool === "inspect") state.brush = null;
      if (!state.dragging) state.draft = null;
      redraw();
    }

    function onDown(ev) {
      if (ev.button !== 0) return;
      const abs = absFromEvent(ev);
      if (abs == null) return;
      state.dragging = true;
      primaryCanvas.setPointerCapture?.(ev.pointerId);

      if (state.tool === "inspect") {
        state.dragStartX = localXY(ev).x;
        state.brush = null;
        return;
      }
      if (state.tool === "hline") {
        state.draft = { type: "hline", price: priceFromEvent(ev), draft: true };
        redraw();
        return;
      }
      if (state.tool === "trend") {
        if (!state.draft) {
          const p = priceFromEvent(ev);
          state.draft = { type: "trend", i0: abs, p0: p, i1: abs, p1: p, draft: true };
        }
        redraw();
      }
    }

    function onUp(ev) {
      if (!state.dragging && state.tool !== "trend") return;
      const wasDragging = state.dragging;
      state.dragging = false;
      try {
        primaryCanvas.releasePointerCapture?.(ev.pointerId);
      } catch {
        /* ignore */
      }

      if (state.tool === "inspect") {
        const vis = visible();
        if (state.brush && Math.abs(state.brush.b - state.brush.a) >= 2) {
          const start = vis.start + state.brush.a;
          const end = vis.start + state.brush.b + 1;
          state.view = { start, end: Math.min(end, barsAll().length) };
        }
        state.brush = null;
        redraw();
        return;
      }

      if (state.tool === "hline" && wasDragging && state.draft?.type === "hline") {
        state.drawings.push({ type: "hline", price: Number(state.draft.price) });
        state.draft = null;
        persist();
        redraw();
        return;
      }

      if (state.tool === "trend" && state.draft?.type === "trend") {
        const abs = absFromEvent(ev);
        const p = priceFromEvent(ev);
        if (abs != null) {
          state.draft.i1 = abs;
          state.draft.p1 = p;
        }
        // Complete on second release if endpoints differ
        if (
          state.draft.i0 !== state.draft.i1 ||
          Math.abs((state.draft.p0 || 0) - (state.draft.p1 || 0)) > 1e-9
        ) {
          state.drawings.push({
            type: "trend",
            i0: state.draft.i0,
            p0: state.draft.p0,
            i1: state.draft.i1,
            p1: state.draft.p1,
          });
          state.draft = null;
          persist();
        }
        redraw();
      }
    }

    function onWheel(ev) {
      if (state.tool !== "inspect") return;
      ev.preventDefault();
      const all = barsAll();
      if (all.length < 4) return;
      const view = ensureView();
      const span = view.end - view.start;
      const abs = absFromEvent(ev) ?? Math.floor((view.start + view.end) / 2);
      const factor = ev.deltaY > 0 ? 1.25 : 0.8;
      let next = Math.round(span * factor);
      next = clamp(next, 8, all.length);
      const leftRatio = (abs - view.start) / Math.max(span, 1);
      let start = Math.round(abs - leftRatio * next);
      let end = start + next;
      if (start < 0) {
        start = 0;
        end = next;
      }
      if (end > all.length) {
        end = all.length;
        start = Math.max(0, end - next);
      }
      state.view = { start, end };
      redraw();
    }

    function onDbl(ev) {
      ev.preventDefault();
      if (state.tool !== "inspect") {
        state.draft = null;
        redraw();
        return;
      }
      state.view = { start: 0, end: barsAll().length };
      state.brush = null;
      redraw();
    }

    primaryCanvas.addEventListener("pointermove", onMove);
    primaryCanvas.addEventListener("pointerleave", onLeave);
    primaryCanvas.addEventListener("pointerdown", onDown);
    primaryCanvas.addEventListener("pointerup", onUp);
    primaryCanvas.addEventListener("wheel", onWheel, { passive: false });
    primaryCanvas.addEventListener("dblclick", onDbl);
    updateCursor();

    return {
      redraw,
      resetView() {
        state.view = { start: 0, end: barsAll().length };
        state.hoverAbs = null;
        state.brush = null;
        state.draft = null;
        redraw();
      },
      setView(start, end) {
        state.view = { start, end };
        redraw();
      },
      setTool(tool) {
        const t = ["inspect", "trend", "hline"].includes(tool) ? tool : "inspect";
        state.tool = t;
        state.draft = null;
        state.brush = null;
        state.dragging = false;
        updateCursor();
        redraw();
      },
      getTool() {
        return state.tool;
      },
      clearDrawings() {
        state.drawings = [];
        state.draft = null;
        persist();
        redraw();
      },
      undoDrawing() {
        state.drawings.pop();
        persist();
        redraw();
      },
      setSymbol(sym) {
        state.symbol = sym || null;
        state.drawings = loadStoredDrawings(state.symbol);
        state.draft = null;
        redraw();
      },
      getDrawings() {
        return [...state.drawings];
      },
      destroy() {
        primaryCanvas.removeEventListener("pointermove", onMove);
        primaryCanvas.removeEventListener("pointerleave", onLeave);
        primaryCanvas.removeEventListener("pointerdown", onDown);
        primaryCanvas.removeEventListener("pointerup", onUp);
        primaryCanvas.removeEventListener("wheel", onWheel);
        primaryCanvas.removeEventListener("dblclick", onDbl);
      },
    };
  }

  window.InfobrokerCharts = {
    drawPriceChart,
    drawVolumeChart,
    drawRsiChart,
    drawMacdChart,
    createController,
    viewSlice,
    loadStoredDrawings,
    saveStoredDrawings,
    fmtPx,
    fmtVol,
    fmtDate,
  };
})();
