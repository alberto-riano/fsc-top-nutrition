/*
 * Gráficas de línea de TopTrack. Render propio sobre <canvas> (sin dependencias
 * externas) para que la app sea 100% self-hosted y funcione sin CDN. Estilo
 * oscuro con el verde de marca.
 *
 * API:
 *   TopTrackCharts.renderBody(canvasId, dataId)   // peso + % grasa + % músculo
 *   TopTrackCharts.renderMulti(canvasId, dataId)  // varias series (fuerza/tests)
 * Los datos se leen de un <script type="application/json" id="dataId">.
 */
(function () {
  const PALETTE = ['#22c55e', '#f59e0b', '#3b82f6', '#a855f7', '#ec4899', '#14b8a6', '#eab308'];
  const GRID = 'rgba(255,255,255,0.07)';
  const AXIS = 'rgba(255,255,255,0.15)';
  const TICK = '#9ca3af';
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

  // series: [{ name, labels:[], values:[num|null], color }]
  function draw(canvas, labels, series) {
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
    ctx.clearRect(0, 0, cssW, cssH);

    // Rango Y
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

    // Series
    series.forEach(s => {
      ctx.strokeStyle = s.color; ctx.lineWidth = 2; ctx.beginPath();
      let started = false;
      s.values.forEach((v, i) => {
        if (v === null || v === undefined) { started = false; return; }
        const x = xFor(i), y = yFor(v);
        if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
      });
      ctx.stroke();
      // Puntos
      ctx.fillStyle = s.color;
      s.values.forEach((v, i) => {
        if (v === null || v === undefined) return;
        ctx.beginPath(); ctx.arc(xFor(i), yFor(v), 2.6, 0, Math.PI * 2); ctx.fill();
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
      ctx.fillStyle = '#d1d5db';
      ctx.fillText(label, lx + 12, ly);
      lx += 12 + tw + 18;
    });
  }

  function formatNum(v) {
    if (Math.abs(v) >= 1000) return Math.round(v).toString();
    return (Math.round(v * 10) / 10).toString();
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
    const render = () => draw(canvas, data.labels, series);
    render();
    bindResize(canvas, render);
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
    const render = () => draw(canvas, labels, series);
    render();
    bindResize(canvas, render);
  }

  let resizeTimer = null;
  const registered = [];
  function bindResize(canvas, render) {
    registered.push(render);
    if (bindResize._bound) return;
    bindResize._bound = true;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => registered.forEach(fn => { try { fn(); } catch (e) {} }), 150);
    });
  }

  window.TopTrackCharts = { renderBody: renderBody, renderMulti: renderMulti };
})();
