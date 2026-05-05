'use strict';

const REFRESH_MS = 5000;
let currentTab = 'summary';
let currentService = '';

// --- Tab navigation ---
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
    currentTab = btn.dataset.tab;
    document.getElementById(`tab-${currentTab}`).classList.add('active');
    refresh();
  });
});

// --- Service filter ---
document.getElementById('filter-service').addEventListener('change', e => {
  currentService = e.target.value;
  loadMetrics();
});

// --- Send form ---
document.getElementById('metric-form').addEventListener('submit', async e => {
  e.preventDefault();
  const result = document.getElementById('send-result');
  result.textContent = 'enviando…';
  result.className = '';
  const payload = {
    service: document.getElementById('f-service').value.trim(),
    metric_name: document.getElementById('f-metric').value,
    value: parseFloat(document.getElementById('f-value').value),
  };
  try {
    const res = await fetch('/ingest/metric', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (res.ok) {
      result.textContent = `✓ En cola: ${payload.service}/${payload.metric_name}=${payload.value}`;
      result.className = 'send-ok';
    } else {
      result.textContent = `Error ${res.status}: ${data.error || JSON.stringify(data)}`;
      result.className = 'send-err';
    }
  } catch (err) {
    result.textContent = `Error de red: ${err.message}`;
    result.className = 'send-err';
  }
});

// --- Data loaders ---
async function apiFetch(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function setStatus(ok) {
  const badge = document.getElementById('status-badge');
  badge.textContent = ok ? 'conectado' : 'sin conexión';
  badge.className = `badge ${ok ? 'badge-ok' : 'badge-error'}`;
  document.getElementById('last-update').textContent =
    `Actualizado: ${new Date().toLocaleTimeString()}`;
}

async function loadSummary() {
  const grid = document.getElementById('summary-grid');
  try {
    const rows = await apiFetch('/query/summary');
    setStatus(true);
    if (!rows.length) {
      grid.innerHTML = '<p style="color:var(--muted);grid-column:1/-1">Sin datos en los últimos 5 minutos. Envía métricas desde la pestaña "Enviar métrica".</p>';
      return;
    }
    grid.innerHTML = rows.map(r => `
      <div class="card">
        <div class="card-service">${esc(r.service)}</div>
        <div class="card-metric">${esc(r.metric_name)}</div>
        <div class="card-value">${r.avg_value}</div>
        <div class="card-sub">max ${r.max_value} · min ${r.min_value} · ${r.total} muestras</div>
      </div>`).join('');
  } catch {
    setStatus(false);
  }
}

async function loadMetrics() {
  const tbody = document.getElementById('metrics-tbody');
  const path = currentService
    ? `/query/metrics/${encodeURIComponent(currentService)}`
    : '/query/metrics';
  try {
    const rows = await apiFetch(path);
    setStatus(true);
    await loadServices();
    tbody.innerHTML = rows.map(r => `
      <tr>
        <td>${fmtDate(r.recorded_at)}</td>
        <td><span class="tag">${esc(r.service)}</span></td>
        <td>${esc(r.metric_name)}</td>
        <td>${r.value}</td>
      </tr>`).join('') || '<tr><td colspan="4" style="color:var(--muted)">Sin datos</td></tr>';
  } catch {
    setStatus(false);
  }
}

async function loadServices() {
  try {
    const services = await apiFetch('/query/services');
    const sel = document.getElementById('filter-service');
    const current = sel.value;
    sel.innerHTML = '<option value="">Todos</option>' +
      services.map(s => `<option value="${esc(s)}" ${s === current ? 'selected' : ''}>${esc(s)}</option>`).join('');
  } catch {}
}

async function loadAlerts() {
  const tbody = document.getElementById('alerts-tbody');
  const count = document.getElementById('alert-count');
  try {
    const rows = await apiFetch('/query/alerts');
    setStatus(true);
    count.textContent = rows.length ? `${rows.length} alerta(s) registrada(s)` : '';
    tbody.innerHTML = rows.map(r => `
      <tr>
        <td>${fmtDate(r.triggered_at)}</td>
        <td><span class="tag">${esc(r.service)}</span></td>
        <td>${esc(r.metric_name)}</td>
        <td style="color:var(--danger);font-weight:600">${r.value}</td>
        <td>${r.threshold}</td>
      </tr>`).join('') || '<tr><td colspan="5" style="color:var(--muted)">Sin alertas</td></tr>';
  } catch {
    setStatus(false);
  }
}

// --- Helpers ---
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('es-ES', {
    day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

// --- Refresh loop ---
function refresh() {
  if (currentTab === 'summary') loadSummary();
  else if (currentTab === 'metrics') loadMetrics();
  else if (currentTab === 'alerts') loadAlerts();
}

refresh();
setInterval(refresh, REFRESH_MS);
