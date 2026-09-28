document.querySelectorAll('.ops-chart-panel').forEach(panel => {
  const chart = panel.querySelector('[data-trend-chart]');
  const rows = [...panel.querySelectorAll('[data-chart-day]')];
  const inspector = panel.querySelector('.ops-inspector');
  if (!chart || !rows.length || !inspector) return;
  const slider = inspector.querySelector('input');
  const output = inspector.querySelector('output');
  const labels = [...panel.querySelectorAll('.ops-legend span')].map(el => el.textContent);
  const cursor = chart.querySelector('.ops-crosshair');
  function show(index) {
    index = Math.max(0, Math.min(rows.length - 1, index));
    slider.value = index;
    const day = rows[index].dataset;
    output.textContent = `${day.date} · ${labels[0]}: ${day.first} · ${labels[1]}: ${day.second} · Active members: ${day.active} · Registered members: ${day.registered}`;
    slider.setAttribute('aria-valuetext', output.textContent);
    const x = 48 + index * 704 / (rows.length - 1);
    cursor.setAttribute('x1', x);
    cursor.setAttribute('x2', x);
    cursor.removeAttribute('hidden');
  }
  function point(event) {
    const matrix = chart.getScreenCTM();
    if (!matrix) return;
    const p = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
    show(Math.round((p.x - 48) / 704 * (rows.length - 1)));
  }
  chart.addEventListener('pointermove', point);
  chart.addEventListener('pointerdown', point);
  slider.addEventListener('input', () => show(Number(slider.value)));
  inspector.hidden = false;
  show(rows.length - 1);
});
