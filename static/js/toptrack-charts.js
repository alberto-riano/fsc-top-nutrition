/*
 * Gráficas de línea de TopTrack. Render propio sobre <canvas> (sin dependencias
 * externas) para que la app sea 100% self-hosted y funcione sin CDN.
 *
 * API:
 *   TopTrackCharts.renderBody(canvasId, dataId)   // peso + % grasa + % músculo
 *   TopTrackCharts.renderMulti(canvasId, dataId)  // varias series (fuerza/tests)
 * Los datos se leen de un <script type="application/json" id="dataId">.
 *
 * Incluye relleno degradado bajo la serie principal, el último punto
 * destacado y un tooltip al pasar el ratón (vertical guide + caja de valores).
 */
(function () {
  const PALETTE = ['#16a34a', '#f59e0b', '#2563eb', '#a855f7', '#ec4899', '#0d9488', '#eab308'];
  const GRID = 'rgba(17,24,39,0.07)';
  const AXIS = 'rgba(17,24,39,0.18)';
  const TICK = '#6b7280';
  const LEGEND = '#374151';
  const FONT = '12px Inter, system-ui, sans-serif';

  function readData(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  function hide(canvas) {
    if (!canvas) return;
    const wrap = canvas.closest('[data-chart-wrap]');
    if (wrap) { wrap.classList.add('hidden'); }
  }

  function formatNum(v) {
    if (Math.abs(v) >= 1000) return Math.round(v).toString();
    return (Math.round(v * 10) / 10).toString();
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  // Calcula escalas/posiciones a partir de las series. No dibuja nada.
  function computeState(canvas, labels, series) {
    const ratio = window.devicePixelRatio || 1;
    // Forzar que el canvas rellene su contenedor (si no, usa su ancho
    // intrínseco de 300px y las etiquetas se amontonan).
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    const cssW = canvas.clientWidth || canvas.parentElement.clientWidth || 600;
    const cssH = canvas.clientHeight || canvas.parentElement.clientHeight || 240;
    canvas.width = Math.round(cssW * ratio);
    canvas.height = Math.round(cssH * ratio);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);

    let min = Infinity, max = -Infinity;
    series.forEach(s => s.values.forEach(v => {
      if (v === null || v === undefined) return;
      if (v < min) min = v; if (v > max) max = v;
    }));
    if (!isFinite(min)) { min = 0; max = 1; }
    if (min === max) { min -= 1; max += 1; }
    const pad = (max - min) * 0.12; min -= pad; max += pad;

    const legendH = 22;
    const padL = 44, padR = 12, padT = 10 + legendH, padB = 26;
    const W = cssW - padL - padR;
    const H = cssH - padT - padB;
    const n = labels.length;

    const xFor = i => padL + (n <= 1 ? W / 2 : (W * i) / (n - 1));
    const yFor = v => padT + H - ((v - min) / (max - min)) * H;

    return { ctx, cssW, cssH, padL, padR, padT, padB, W, H, min, max, n, xFor, yFor, labels, series };
  }

  function paintBase(state) {
    const { ctx, cssW, cssH, padL, padT, W, H, n, xFor, yFor, labels, series, min, max } = state;
    ctx.clearRect(0, 0, cssW, cssH);

    // Gridlines + etiquetas Y
    ctx.font = FONT; ctx.fillStyle = TICK; ctx.strokeStyle = GRID; ctx.lineWidth = 1;
    const ticks = 4;
    for (let t = 0; t <= ticks; t++) {
      const val = min + ((max - min) * t) / ticks;
      const y = yFor(val);
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + W, y); ctx.stroke();
      ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
      ctx.fillText(formatNum(val), padL - 6, y);
    }
    // Eje X base
    ctx.strokeStyle = AXIS; ctx.beginPath();
    ctx.moveTo(padL, padT + H); ctx.lineTo(padL + W, padT + H); ctx.stroke();

    // Etiquetas X (submuestreo)
    ctx.fillStyle = TICK; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    const step = Math.ceil(n / 6) || 1;
    for (let i = 0; i < n; i++) {
      if (i % step !== 0 && i !== n - 1) continue;
      ctx.fillText(labels[i], xFor(i), padT + H + 6);
    }

    // Relleno degradado bajo la primera serie (la principal).
    const main = series[0];
    if (main && main.values.some(v => v !== null && v !== undefined)) {
      const grad = ctx.createLinearGradient(0, padT, 0, padT + H);
      grad.addColorStop(0, main.color + '33');
      grad.addColorStop(1, main.color + '00');
      ctx.fillStyle = grad;
      ctx.beginPath();
      let started = false, lastX = padL;
      main.values.forEach((v, i) => {
        if (v === null || v === undefined) return;
        const x = xFor(i), y = yFor(v);
        if (!started) { ctx.moveTo(x, padT + H); ctx.lineTo(x, y); started = true; } else { ctx.lineTo(x, y); }
        lastX = x;
      });
      if (started) { ctx.lineTo(lastX, padT + H); ctx.closePath(); ctx.fill(); }
    }

    // Series (líneas + puntos, con el último punto destacado)
    series.forEach(s => {
      ctx.strokeStyle = s.color; ctx.lineWidth = 2; ctx.beginPath();
      let started = false;
      s.values.forEach((v, i) => {
        if (v === null || v === undefined) { started = false; return; }
        const x = xFor(i), y = yFor(v);
        if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
      });
      ctx.stroke();

      let lastIdx = -1;
      s.values.forEach((v, i) => { if (v !== null && v !== undefined) lastIdx = i; });
      ctx.fillStyle = s.color;
      s.values.forEach((v, i) => {
        if (v === null || v === undefined) return;
        const r = i === lastIdx ? 4.2 : 2.6;
        ctx.beginPath(); ctx.arc(xFor(i), yFor(v), r, 0, Math.PI * 2); ctx.fill();
        if (i === lastIdx) {
          ctx.lineWidth = 2; ctx.strokeStyle = '#fff';
          ctx.beginPath(); ctx.arc(xFor(i), yFor(v), r, 0, Math.PI * 2); ctx.stroke();
        }
      });
    });

    // Leyenda
    ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
    let lx = padL, ly = 12;
    series.forEach(s => {
      const label = s.name;
      const tw = ctx.measureText(label).width;
      ctx.fillStyle = s.color;
      ctx.beginPath(); ctx.arc(lx + 4, ly, 4, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = LEGEND;
      ctx.fillText(label, lx + 12, ly);
      lx += 12 + tw + 18;
    });
  }

  function paintTooltip(state, idx) {
    if (idx === null || idx === undefined) return;
    const { ctx, cssW, padT, H, xFor, yFor, labels, series } = state;
    const x = xFor(idx);

    ctx.save();
    ctx.strokeStyle = AXIS; ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, padT + H); ctx.stroke();
    ctx.restore();

    const lines = [labels[idx]];
    series.forEach(s => {
      const v = s.values[idx];
      if (v === null || v === undefined) return;
      const y = yFor(v);
      ctx.beginPath(); ctx.fillStyle = '#fff'; ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();
      ctx.lineWidth = 2; ctx.strokeStyle = s.color;
      ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.stroke();
      lines.push(s.name + ': ' + formatNum(v));
    });
    if (lines.length < 2) return;

    ctx.font = FONT;
    const boxW = Math.max(...lines.map(l => ctx.measureText(l).width)) + 16;
    const boxH = lines.length * 16 + 10;
    let bx = x + 10;
    if (bx + boxW > cssW - 4) bx = x - boxW - 10;
    const by = padT;
    ctx.fillStyle = 'rgba(17,24,39,0.92)';
    roundRect(ctx, bx, by, boxW, boxH, 6); ctx.fill();
    ctx.textAlign = 'left'; ctx.textBaseline = 'top';
    lines.forEach((l, i) => {
      ctx.fillStyle = i === 0 ? '#d1d5db' : '#fff';
      ctx.fillText(l, bx + 8, by + 6 + i * 16);
    });
  }

  function nearestIndex(state, mouseX) {
    let idx = 0, best = Infinity;
    for (let i = 0; i < state.n; i++) {
      const d = Math.abs(state.xFor(i) - mouseX);
      if (d < best) { best = d; idx = i; }
    }
    return state.n ? idx : null;
  }

  function bindTooltip(canvas) {
    if (canvas._ttBound) return;
    canvas._ttBound = true;
    canvas.addEventListener('mousemove', e => {
      const state = canvas._chartState;
      if (!state || !state.n) return;
      const rect = canvas.getBoundingClientRect();
      const idx = nearestIndex(state, e.clientX - rect.left);
      paintBase(state);
      paintTooltip(state, idx);
    });
    canvas.addEventListener('mouseleave', () => {
      const state = canvas._chartState;
      if (state) paintBase(state);
    });
  }

  function render(canvas, labels, series) {
    const state = computeState(canvas, labels, series);
    canvas._chartState = state;
    paintBase(state);
    bindTooltip(canvas);
  }

  function renderBody(canvasId, dataId) {
    const canvas = document.getElementById(canvasId);
    const data = readData(dataId);
    if (!canvas || !data || !data.count) { hide(canvas); return; }
    const series = [{ name: 'Peso (kg)', labels: data.labels, values: data.weight, color: PALETTE[0] }];
    if (data.body_fat && data.body_fat.some(v => v !== null))
      series.push({ name: '% grasa', labels: data.labels, values: data.body_fat, color: PALETTE[1] });
    if (data.muscle && data.muscle.some(v => v !== null))
      series.push({ name: '% músculo', labels: data.labels, values: data.muscle, color: PALETTE[2] });
    const doRender = () => render(canvas, data.labels, series);
    doRender();
    bindResize(canvas, doRender);
  }

  function renderMulti(canvasId, dataId) {
    const canvas = document.getElementById(canvasId);
    const seriesData = readData(dataId);
    if (!canvas || !seriesData || !seriesData.length) { hide(canvas); return; }
    let labels = [];
    seriesData.forEach(s => { if (s.labels.length > labels.length) labels = s.labels; });
    const series = seriesData.map((s, i) => ({
      name: s.name, labels: s.labels, values: s.values, color: PALETTE[i % PALETTE.length],
    }));
    const doRender = () => render(canvas, labels, series);
    doRender();
    bindResize(canvas, doRender);
  }

  let resizeTimer = null;
  const registered = [];
  function bindResize(canvas, doRender) {
    registered.push(doRender);
    if (bindResize._bound) return;
    bindResize._bound = true;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => registered.forEach(fn => { try { fn(); } catch (e) {} }), 150);
    });
  }

  window.TopTrackCharts = { renderBody: renderBody, renderMulti: renderMulti };
})();

