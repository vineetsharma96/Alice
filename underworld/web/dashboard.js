import {WorldView} from './scene.js';

const $ = id => document.getElementById(id);
const SVG_NS = 'http://www.w3.org/2000/svg';
const COLORS = ['#b8d8bd','#d4b67a','#8fc4ca','#d6a6a0','#b8a8d7','#b7c889','#e0c28c','#9ec6d1'];
let state = null;
let selected = 'agent-1';
let view3d = null;
let viewMode = '2d';
let controlToken = null;
let controlState = null;
let refreshing = false;
let commandBusy = false;
let observed = null;
let observedRate = 0;
let rawVisible = false;

function svg(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
  return node;
}

function setText(id, value) { const el = $(id); if (el) el.textContent = value ?? '—'; }
function json(value) { return JSON.stringify(value, null, 2); }
function error(message = '') { $('error').hidden = !message; $('error').textContent = message; }
function clamp(value, low = 0, high = 1) { return Math.max(low, Math.min(high, Number(value) || 0)); }
function fmtKg(ug) { return `${(Number(ug || 0) / 1e9).toFixed(2)} kg`; }
function fmtSeconds(seconds) {
  const value = Number(seconds) || 0;
  if (value < 60) return `${value.toFixed(1)} s`;
  if (value < 3600) return `${(value / 60).toFixed(1)} min`;
  return `${(value / 3600).toFixed(2)} h`;
}
function label(value) { return String(value || 'unknown').replaceAll('_', ' '); }

async function request(url, options = {}) {
  const response = await fetch(url, { cache: 'no-store', ...options });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || response.statusText);
  return value;
}

async function pollControl() {
  try {
    const response = await fetch('/api/life-control', { cache: 'no-store' });
    const value = await response.json();
    if (!response.ok) throw new Error(value.error || response.statusText);
    controlToken = value.token;
    controlState = value;
  } catch (_) {
    controlToken = null;
    controlState = { read_only: true, paused: true, processing: false, error: '' };
  }
  renderControlState();
}

function renderControlState() {
  const s = state?.snapshot;
  const c = controlState;
  const hasJob = Boolean(c?.job);
  const jobPaused = c?.job?.state === 'paused';
  const processing = Boolean(c?.processing && !jobPaused);
  const paused = c?.paused ?? true;
  const readOnly = !controlToken;
  const runState = processing ? 'Processing' : c?.error ? 'Error' : paused ? 'Paused' : 'Running';
  setText('run-state', runState);
  setText('run-detail', hasJob ? `${c.job.kind.replaceAll('_', ' ')} · ${c.job.state} · ${c.job.completed} completed${c.job.remaining != null ? ` · ${c.job.remaining} remaining` : ''}` : readOnly ? 'Read-only observer' : 'Control channel ready');
  setText('connection', readOnly ? 'Read-only telemetry' : jobPaused ? 'Connected / job paused' : processing ? 'Processing' : paused ? 'Connected / paused' : 'Connected / running');
  $('connection').className = `status-chip ${c?.error ? 'is-error' : processing ? 'is-processing' : ''}`;
  $('pause-resume').textContent = paused ? 'Resume' : 'Pause';
  $('pause-resume').disabled = readOnly || commandBusy;
  $('step-one').disabled = readOnly || commandBusy || !paused || hasJob;
  $('step-batch').disabled = readOnly || commandBusy || !paused || hasJob;
  $('run-until-button').disabled = readOnly || commandBusy || !paused || hasJob;
  $('cancel-job').disabled = readOnly || commandBusy || !hasJob;
  $('speed').disabled = readOnly || commandBusy;
  $('time-dilation').disabled = readOnly || commandBusy;
  if (c?.time_dilation?.preset) $('time-dilation').value = c.time_dilation.preset;
  if (c?.error) error(c.error);
}

async function control(command, payload = {}) {
  if (!controlToken || commandBusy) return;
  commandBusy = true;
  try {
    await request('/api/life-control', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Life-Control': controlToken},
      body: JSON.stringify({command, ...payload}),
    });
    await refresh();
  } catch (e) {
    error(e.message);
  } finally {
    commandBusy = false;
    renderControlState();
  }
}

function drawMap(snapshot) {
  const map = $('map-svg');
  map.replaceChildren();
  const width = Number(snapshot.world_bounds_m?.width || 32);
  const height = Number(snapshot.world_bounds_m?.height || 32);
  const pad = 1.5;
  map.setAttribute('viewBox', `0 0 ${width + pad * 2} ${height + pad * 2}`);
  map.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  const background = svg('rect', {x: 0, y: 0, width: width + pad * 2, height: height + pad * 2, fill: '#243a36'});
  map.append(background);
  for (let x = 0; x <= width; x += 2) map.append(svg('line', {x1: x + pad, y1: pad, x2: x + pad, y2: height + pad, stroke: '#3d5750', 'stroke-width': .045}));
  for (let y = 0; y <= height; y += 2) map.append(svg('line', {x1: pad, y1: height - y + pad, x2: width + pad, y2: height - y + pad, stroke: '#3d5750', 'stroke-width': .045}));
  const entities = snapshot.entities || [];
  for (const entity of entities) {
    if (entity.present === false) continue;
    const x = Number(entity.position_m?.[0] || 0) + pad;
    const y = height - Number(entity.position_m?.[1] || 0) + pad;
    const actor = entity.kind === 'actor';
    const size = actor ? .34 : entity.kind === 'animal' ? .28 : entity.kind === 'tree' ? .4 : .22;
    const fill = entity.kind === 'actor' ? (entity.entity_id === selected ? '#f0d29d' : '#b8d8bd') : entity.kind === 'animal' ? '#d4b67a' : entity.kind === 'tree' || entity.kind === 'forage' ? '#709f6f' : entity.kind === 'food' || entity.kind === 'water' ? '#8fc4ca' : '#879690';
    const node = svg('circle', {cx: x, cy: y, r: size, fill, stroke: entity.entity_id === selected ? '#fff3c0' : '#132120', 'stroke-width': entity.entity_id === selected ? .12 : .06, tabindex: actor ? 0 : -1});
    const title = svg('title');
    title.textContent = actor ? `${entity.entity_id} · ${entity.alive === false ? 'dead' : 'alive'}` : `${label(entity.kind)} · ${entity.entity_id}`;
    node.append(title);
    if (actor) {
      node.setAttribute('role', 'button');
      node.setAttribute('aria-label', `Inspect ${entity.entity_id}`);
      node.addEventListener('click', () => selectAgent(entity.entity_id));
      node.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectAgent(entity.entity_id); } });
    }
    map.append(node);
  }
}

function update3d(snapshot) {
  if (!view3d) return;
  try { view3d.update(snapshot, selected); } catch (e) { setText('render-reason', e.message); }
}

function selectAgent(agent) {
  selected = agent;
  if ($('agent').value !== agent) $('agent').value = agent;
  if (view3d) view3d.select(agent);
  render();
  void refresh();
}

function renderInspector() {
  const person = state.selected_person || {};
  const native = state.selected || {};
  const own = native.own_state || {};
  const body = own.body || {};
  const identity = person.identity || {};
  setText('person-name', identity.name || selected);
  setText('person-id', `${selected} · stable native identity`);
  setText('life-stage', own.life_stage || own.stage || 'Life stage unavailable');
  const task = own.busy ? `Current task: ${label(own.action_type)}` : person.life?.last_decision?.choice?.action ? `Last decision: ${label(person.life.last_decision.choice.action)}` : 'Current task: idle / not recorded';
  setText('current-task', task);
  const needs = $('needs'); needs.replaceChildren();
  const fields = [['hunger', body.hunger], ['thirst', body.thirst], ['energy', body.fatigue == null ? null : 1 - Number(body.fatigue)], ['health', body.health], ['temperature', own.weather?.cold_burden == null ? null : 1 - Number(own.weather.cold_burden)]];
  for (const [name, value] of fields) {
    const row = document.createElement('div'); row.className = 'need-row';
    const labelEl = document.createElement('span'); labelEl.textContent = name;
    const meter = document.createElement('meter'); meter.min = 0; meter.max = 1; meter.value = value == null ? 0 : clamp(value); meter.setAttribute('aria-label', `${name} value`);
    const output = document.createElement('output'); output.textContent = value == null ? 'n/a' : `${Math.round(clamp(value) * 100)}%`;
    row.append(labelEl, meter, output); needs.append(row);
  }
  const inventory = $('inventory'); inventory.replaceChildren();
  const items = Object.entries(own.inventory_ug || {}).filter(([, value]) => Number(value) > 0);
  for (const [item, quantity] of items) {
    const row = document.createElement('div'); row.className = 'inventory-row'; row.innerHTML = `<span>${label(item)}</span><span>${fmtKg(quantity)}</span>`; inventory.append(row);
  }
  if (!items.length) { const empty = document.createElement('span'); empty.className = 'muted small'; empty.textContent = 'No carried items recorded.'; inventory.append(empty); }
  setText('inventory-note', 'Reserved items, durability and spoilage are not exposed by this runtime. Nearby storage is not treated as carried inventory.');
  const decision = person.life?.last_decision;
  if (decision) {
    const choice = decision.choice || {};
    const influence = decision.influence || {};
    setText('decision-reason', influence.reason ? `${influence.reason}.` : `Recorded action: ${label(choice.action)}. The runtime did not record a fuller explanation.`);
    $('decision-raw').textContent = json(decision);
  } else setText('decision-reason', 'No decision evidence recorded for this inhabitant yet.');
  const actions = $('recent-actions'); actions.replaceChildren();
  for (const receipt of [...(native.recent_action_results || [])].reverse().slice(0, 8)) {
    const li = document.createElement('li'); li.textContent = `${label(receipt.action_type || receipt.status)} · ${receipt.status}`;
    const small = document.createElement('small'); small.textContent = receipt.observable_effects?.description || receipt.error_code || receipt.request_id || 'Recorded native receipt'; li.append(small); actions.append(li);
  }
  if (!actions.children.length) { const li = document.createElement('li'); li.textContent = 'No action receipts recorded.'; actions.append(li); }
}

function renderWeather() {
  const climate = state.climate || {};
  setText('weather-type', `${label(climate.weather || 'unknown')} weather`);
  setText('temperature', climate.ambient_c == null ? 'n/a' : `${Number(climate.ambient_c).toFixed(1)} °C`);
  setText('rainfall', climate.current?.rain_mm_h == null ? 'n/a' : `${Number(climate.current.rain_mm_h).toFixed(2)} mm/h`);
  setText('wind', Array.isArray(climate.current?.wind_m_s) ? `${climate.current.wind_m_s.map(value => Number(value).toFixed(1)).join(', ')} m/s` : 'n/a');
  setText('daylight', climate.daylight_factor == null ? 'n/a' : `${Math.round(Number(climate.daylight_factor) * 100)}%`);
  setText('season', climate.season || 'unknown');
  $('weather-mode').textContent = climate.forced ? 'Guided override' : 'Natural';
  const exposure = climate.exposure?.[selected];
  setText('exposure', exposure ? `Selected exposure: wetness ${Math.round(Number(exposure.wetness || 0) * 100)}%, cold burden ${Math.round(Number(exposure.cold_burden || 0) * 100)}%, shelter ${exposure.shelter_id || 'none'}.` : 'Exposure data unavailable.');
  const guided = state.snapshot?.mode === 'guided';
  $('apply-weather').disabled = !controlToken || !guided || !controlState?.paused || controlState?.processing;
  setText('weather-intervention-status', guided ? (climate.forced ? `Override recorded until ${Number(climate.forced_until_s || 0).toFixed(1)} simulated seconds.` : `${Object.keys(climate.forcing_history || {}).length} recorded overrides.`) : 'Closed mode: the native runtime requires an explicit guided branch for weather intervention.');
}

function renderCharts() {
  const chart = $('mood-chart'); chart.replaceChildren();
  const measure = $('chart-measure').value; const selectedHistory = state.mood_history?.[selected] || [];
  const windowValue = $('chart-window').value; const limit = windowValue === 'all' ? selectedHistory.length : Number(windowValue); const history = selectedHistory.slice(-limit);
  const width = 760, height = 235, pad = {left: 34, right: 16, top: 15, bottom: 28};
  chart.setAttribute('viewBox', `0 0 ${width} ${height}`);
  for (let i = 0; i <= 4; i++) { const y = pad.top + (height - pad.top - pad.bottom) * i / 4; chart.append(svg('line', {x1: pad.left, y1: y, x2: width - pad.right, y2: y, stroke: '#304743', 'stroke-width': 1})); const t = svg('text', {x: 4, y: y + 4, fill: '#80968d', 'font-size': 10}); t.textContent = measure === 'valence' ? (1 - i * .5).toFixed(1) : (1 - i * .25).toFixed(2); chart.append(t); }
  const allHistories = Object.entries(state.mood_history || {});
  const ticks = history.map(item => Number(item.tick));
  const firstTick = ticks[0] ?? 0; const lastTick = ticks[ticks.length - 1] ?? firstTick + 1;
  const xForTick = tick => pad.left + (width - pad.left - pad.right) * (lastTick === firstTick ? .5 : (Number(tick) - firstTick) / (lastTick - firstTick));
  const xFor = index => xForTick(ticks[index]);
  const yFor = value => pad.top + (height - pad.top - pad.bottom) * (1 - (measure === 'valence' ? (Number(value) + 1) / 2 : Number(value)));
  const valuesFor = hist => { const byTick = new Map(hist.map(item => [Number(item.tick), Number(item[measure])])); return ticks.map(tick => { const value = byTick.get(tick); return Number.isFinite(value) ? value : null; }); };
  const series = allHistories.map(([agent, hist]) => [agent, valuesFor(hist)]);
  const stats = ticks.map((_, index) => { const values = series.map(([, values]) => values[index]).filter(value => Number.isFinite(value)); return values.length ? {mean: values.reduce((sum, value) => sum + value, 0) / values.length, min: Math.min(...values), max: Math.max(...values), count: values.length} : null; });
  const drawLine = (values, color, widthValue = 2, dash = '') => { let segment = []; const flush = () => { if (segment.length > 1) { const line = svg('polyline', {points: segment.join(' '), fill: 'none', stroke: color, 'stroke-width': widthValue}); if (dash) line.setAttribute('stroke-dasharray', dash); chart.append(line); } segment = []; }; values.forEach((value, index) => { if (value == null) return flush(); segment.push(`${xFor(index)},${yFor(value)}`); }); flush(); };
  const drawRange = values => { let segment = []; const flush = () => { if (segment.length > 1) { const polygon = svg('polygon', {points: [...segment.map(item => `${xFor(item.index)},${yFor(item.max)}`), ...segment.slice().reverse().map(item => `${xFor(item.index)},${yFor(item.min)}`)].join(' '), fill: '#e5eee7', opacity: .08}); chart.append(polygon); } segment = []; }; values.forEach((value, index) => { if (!value) return flush(); segment.push({...value, index}); }); flush(); };
  drawRange(stats); for (const [index, [agent, values]] of series.entries()) drawLine(values, agent === selected ? '#f0d29d' : COLORS[index % COLORS.length], agent === selected ? 3 : 1.2);
  drawLine(stats.map(item => item?.mean ?? null), '#e5eee7', 1, '4 4');
  const daySeconds = Number(state.calendar?.day_length_s || 86400); const dt = Number(state.snapshot?.dt_s || .25); const startSeconds = firstTick * dt; const endSeconds = lastTick * dt;
  if (daySeconds > 0) for (let seconds = Math.ceil(startSeconds / daySeconds) * daySeconds; seconds < endSeconds; seconds += daySeconds) { const marker = svg('line', {x1: xForTick(seconds / dt), y1: pad.top, x2: xForTick(seconds / dt), y2: height - pad.bottom, stroke: '#61766c', 'stroke-dasharray': '2 5', 'stroke-width': 1}); const title = svg('title'); title.textContent = `Day boundary at ${fmtSeconds(seconds)}`; marker.append(title); chart.append(marker); }
  for (const event of state.events || []) { const tick = Number(event.tick); if (!Number.isFinite(tick) || tick < firstTick || tick > lastTick) continue; const marker = svg('circle', {cx: xForTick(tick), cy: pad.top + 7, r: 3, fill: event.type === 'death' ? '#e2a49a' : '#8fc4ca'}); const title = svg('title'); title.textContent = `${label(event.type)} · ${event.detail || 'Recorded event'}`; marker.append(title); chart.append(marker); }
  const axis = svg('line', {x1: pad.left, y1: height - pad.bottom, x2: width - pad.right, y2: height - pad.bottom, stroke: '#759187', 'stroke-width': 1}); chart.append(axis);
  if (!history.length) { const text = svg('text', {x: width / 2 - 90, y: height / 2, fill: '#91a59d', 'font-size': 12}); text.textContent = 'No retained mood samples'; chart.append(text); }
  const legend = $('chart-legend'); legend.replaceChildren();
  for (const [index, [agent, hist]] of allHistories.entries()) { const key = document.createElement('span'); key.className = 'chart-key'; key.style.setProperty('--key', agent === selected ? '#f0d29d' : COLORS[index % COLORS.length]); key.textContent = `${agent}${agent === selected ? ' · selected' : ''}`; legend.append(key); }
  const meanKey = document.createElement('span'); meanKey.className = 'chart-key'; meanKey.style.setProperty('--key', '#e5eee7'); meanKey.textContent = `Population mean (${stats.filter(Boolean).length} tick-aligned samples)`; legend.append(meanKey);
  const rangeKey = document.createElement('span'); rangeKey.className = 'chart-key'; rangeKey.style.setProperty('--key', '#e5eee7'); rangeKey.textContent = 'Population range'; legend.append(rangeKey);
  setText('chart-explanation', `${measure === 'stress' ? 'Slow stress' : measure === 'valence' ? 'Mood valence' : 'Immediate arousal'} is plotted from recorded operation updates. The dotted trace and shaded band are tick-aligned same-measure population statistics; missing records remain gaps and no unrelated dimensions are combined.`);
}

function renderTimeline() {
  const filters = [...document.querySelectorAll('.event-filter:checked')].map(input => input.value);
  const search = String($('event-search').value || '').trim().toLowerCase();
  const list = $('timeline'); list.replaceChildren();
  const events = (state.events || []).filter(event => (filters.includes('all') || filters.includes(event.type) || (filters.includes('mood_update') && event.type === 'mood_update')) && (!search || json(event).toLowerCase().includes(search)));
  for (const event of events.slice().reverse().slice(0, 80)) {
    const row = document.createElement('div'); row.className = 'timeline-item';
    const time = document.createElement('time'); time.textContent = `Day ${Math.floor(Number(event.seconds || 0) / (state.calendar.day_length_s || 86400)) + 1} · t${event.tick}`;
    const type = document.createElement('span'); type.className = 'event-type'; type.textContent = label(event.type);
    const detail = document.createElement('span'); detail.className = 'event-detail'; detail.textContent = `${event.agent_id ? `${event.agent_id} · ` : ''}${event.detail || 'Recorded event; no plain-language detail was emitted.'}`;
    row.append(time, type, detail);
    if (event.agent_id && Object.prototype.hasOwnProperty.call(state.people || {}, event.agent_id)) {
      row.tabIndex = 0; row.classList.add('is-focusable'); row.setAttribute('aria-label', `Focus ${event.agent_id} from ${label(event.type)} event`);
      const focus = () => selectAgent(event.agent_id); row.addEventListener('click', focus); row.addEventListener('keydown', key => { if (key.key === 'Enter' || key.key === ' ') { key.preventDefault(); focus(); } });
    }
    list.append(row);
  }
  if (!list.children.length) { const empty = document.createElement('p'); empty.className = 'muted small'; empty.textContent = 'No events match the current filters.'; list.append(empty); }
}

function renderPopulation() {
  const p = state.population || {}; const metrics = $('population-metrics'); metrics.replaceChildren();
  const values = [['Living inhabitants', p.living_inhabitants], ['Animals', p.animals], ['Plants', p.plants], ['Total entities', p.total_entities]];
  for (const [name, value] of values) { const card = document.createElement('div'); card.className = 'population-metric'; card.innerHTML = `<strong>${value == null ? 'n/a' : value}</strong><span>${name}</span>`; metrics.append(card); }
  const bars = $('population-bars'); bars.replaceChildren(); const max = Math.max(1, p.total_entities || 1);
  for (const [name, value] of [['inhabitants', p.inhabitants], ['animals', p.animals], ['plants', p.plants]]) { const row = document.createElement('div'); row.className = 'bar-row'; row.innerHTML = `<span>${name}</span><span class="bar-track"><span class="bar-fill" style="width:${Math.min(100, Number(value || 0) / max * 100)}%"></span></span><span>${value ?? 'n/a'}</span>`; bars.append(row); }
  setText('population-warning', p.microbial_note || '');
}

function renderRelationships() {
  const host = $('relationship-graph'); host.replaceChildren();
  const people = Object.keys(state.people || {}); const edges = state.relationships || []; const measure = $('relationship-measure').value;
  const positions = new Map(); const cx = 50, cy = 50, radius = Math.min(36, 12 + people.length * 5);
  people.forEach((agent, index) => { const angle = -Math.PI / 2 + index * 2 * Math.PI / Math.max(1, people.length); positions.set(agent, {x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius}); });
  for (const edge of edges) {
    const from = positions.get(edge.from), to = positions.get(edge.to); if (!from || !to) continue;
    const value = Number(edge[measure]); if (!Number.isFinite(value)) continue;
    const dx = to.x - from.x, dy = to.y - from.y, length = Math.hypot(dx, dy) * 2.3; const line = document.createElement('span'); line.className = 'relationship-line'; line.style.left = `${from.x}%`; line.style.top = `${from.y}%`; line.style.width = `${length}%`; line.style.transform = `rotate(${Math.atan2(dy, dx)}rad)`; line.style.opacity = String(.35 + clamp(Math.abs(value)) * .65); host.append(line);
    const arrow = document.createElement('span'); arrow.className = 'relationship-arrow'; arrow.style.left = `${to.x}%`; arrow.style.top = `${to.y}%`; arrow.style.transform = `translate(-50%,-50%) rotate(${Math.atan2(dy, dx)}rad)`; host.append(arrow);
    line.addEventListener('click', () => renderRelationshipDetail(edge));
  }
  people.forEach(agent => { const pos = positions.get(agent); const node = document.createElement('button'); node.className = `relationship-node ${agent === selected ? 'selected' : ''}`; node.style.left = `${pos.x}%`; node.style.top = `${pos.y}%`; node.textContent = agent; node.addEventListener('click', () => selectAgent(agent)); host.append(node); });
  setText('relationship-note', edges.length ? `${edges.length} directed evidence-backed edge${edges.length === 1 ? '' : 's'} retained. Select an edge to compare direction.` : 'No directional relationship evidence is currently recorded.');
  if (edges.length) renderRelationshipDetail(edges[0]); else $('relationship-detail').textContent = '';
}

function renderRelationshipDetail(edge) {
  const reverse = (state.relationships || []).find(item => item.from === edge.to && item.to === edge.from);
  const measure = $('relationship-measure').value;
  $('relationship-detail').textContent = `${edge.from} → ${edge.to}: ${Number(edge[measure] ?? 0).toFixed(3)} ${measure}; evidence ${edge.evidence?.length || 0}. ${reverse ? `${edge.to} → ${edge.from}: ${Number(reverse[measure] ?? 0).toFixed(3)} ${measure}.` : `Reverse direction has no recorded ${measure} value.`}`;
}

function renderStatus() {
  const snapshot = state.snapshot; const calendar = state.calendar || {}; const previous = observed; const now = performance.now();
  if (previous) { const elapsed = Math.max(.001, (now - previous.time) / 1000); const delta = Number(snapshot.simulated_time_s) - previous.seconds; observedRate = delta >= 0 ? delta / elapsed : 0; }
  observed = {time: now, seconds: Number(snapshot.simulated_time_s)};
  setText('world-label', `${snapshot.mode || 'world'} · branch ${String(snapshot.branch_id || '').slice(0, 10)}`);
  setText('seed', snapshot.seed ?? 'unknown'); setText('laws', snapshot.laws_version || 'laws unavailable'); setText('elapsed', fmtSeconds(snapshot.simulated_time_s));
  setText('calendar', `Day ${calendar.day_number || '—'} · ${calendar.time_of_day_label || '—'} · ${calendar.season || 'season unavailable'}`);
  setText('tick', snapshot.tick); setText('tick-rate', `configured ${Number(snapshot.dt_s || 0).toFixed(2)} s / tick`);
  const p = state.population || {}; setText('population-total', `${p.living_inhabitants ?? '—'} living`); setText('population-detail', `${p.animals ?? '—'} animals · ${p.plants ?? '—'} plants`); setText('observed-speed', `${observedRate.toFixed(2)}×`);
  setText('map-source', `Native hash ${String(state.state_hash || '').slice(0, 12)} · tick ${snapshot.tick}`);
}

function render() {
  if (!state) return;
  renderStatus();
  const actors = (state.snapshot.entities || []).filter(entity => entity.kind === 'actor');
  if (!$('agent').options.length || $('agent').options.length !== actors.length) $('agent').replaceChildren(...actors.map(entity => new Option(`${entity.entity_id} · ${entity.alive === false ? 'dead' : 'alive'}`, entity.entity_id)));
  if (!actors.some(entity => entity.entity_id === selected)) selected = actors[0]?.entity_id || selected;
  $('agent').value = selected;
  drawMap(state.snapshot); update3d(state.snapshot); renderInspector(); renderWeather(); renderCharts(); renderTimeline(); renderPopulation(); renderRelationships();
  if (rawVisible) $('raw-json').textContent = json(state.raw ?? state);
  renderControlState();
}

async function refresh() {
  if (refreshing) return;
  refreshing = true;
  try { state = await request(`/api/dashboard?agent=${encodeURIComponent(selected)}${rawVisible ? '&detail=advanced' : ''}`); error(''); render(); }
  catch (e) { error(`Telemetry unavailable: ${e.message}. The last rendered snapshot remains visible.`); }
  finally { refreshing = false; }
}

function setView(mode) {
  viewMode = mode; $('map-2d').hidden = mode !== '2d'; $('map-3d').hidden = mode !== '3d'; $('view-2d').classList.toggle('active', mode === '2d'); $('view-3d').classList.toggle('active', mode === '3d'); $('view-2d').setAttribute('aria-pressed', String(mode === '2d')); $('view-3d').setAttribute('aria-pressed', String(mode === '3d')); view3d?.setActive(mode === '3d'); if (mode === '3d') { view3d?.resize(); if (state) update3d(state.snapshot); } }

function setup3d() {
  try { view3d = new WorldView($('viewport'), id => { if ((state?.snapshot.entities || []).some(entity => entity.entity_id === id && entity.kind === 'actor')) selectAgent(id); }, () => {}); }
  catch (e) { $('render-error').hidden = false; setText('render-reason', e.message); }
}

 $('pause-resume').addEventListener('click', () => control(controlState?.paused ? 'resume' : 'pause'));
$('step-one').addEventListener('click', () => control('tick'));
$('speed').addEventListener('change', event => control('speed', {value: Number(event.target.value)}));
$('time-dilation').addEventListener('change', event => control('time_dilation', {preset: event.target.value}));
$('step-batch').addEventListener('click', () => control('step_batch', {ticks: Number($('batch-ticks').value)}));
$('run-until-button').addEventListener('click', () => control('run_until', {simulated_s: Number($('run-until').value)}));
$('cancel-job').addEventListener('click', () => control('cancel_step'));
$('agent').addEventListener('change', event => selectAgent(event.target.value));
$('view-2d').addEventListener('click', () => setView('2d')); $('view-3d').addEventListener('click', () => setView('3d'));
$('focus-selected').addEventListener('click', () => view3d?.focus(selected));
$('chart-measure').addEventListener('change', renderCharts); $('chart-window').addEventListener('change', renderCharts); $('relationship-measure').addEventListener('change', renderRelationships);
document.querySelectorAll('.event-filter').forEach(input => input.addEventListener('change', renderTimeline));
 $('event-search').addEventListener('input', renderTimeline);
 $('advanced-toggle').addEventListener('click', async () => { rawVisible = !rawVisible; $('advanced-toggle').setAttribute('aria-pressed', String(rawVisible)); document.querySelectorAll('.advanced-only').forEach(el => el.classList.toggle('visible', rawVisible)); if (rawVisible && state) await refresh(); });
 $('copy-raw').addEventListener('click', async () => { if (state) await navigator.clipboard?.writeText(json(state.raw ?? state)); });
 $('download-raw').addEventListener('click', () => { if (!state) return; const blob = new Blob([json(state.raw ?? state)], {type: 'application/json'}); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `alice-dashboard-${state.snapshot.tick}.json`; link.click(); URL.revokeObjectURL(link.href); });
$('apply-weather').addEventListener('click', () => {
  const id = `dashboard-${Date.now()}`;
  control('force_weather', {parameters: {id, observation_version: String(state.snapshot.tick), duration_s: Number($('weather-duration').value), temperature_c: Number($('weather-temperature').value), rain_mm_h: Number($('weather-rain').value), cloud_fraction: Number($('weather-cloud').value), wind_x_m_s: Number($('weather-wind-x').value), wind_y_m_s: Number($('weather-wind-y').value)}});
});

setup3d();
setView('2d');
(async function boot() { await pollControl(); await refresh(); setInterval(pollControl, 800); setInterval(refresh, 1500); })();
addEventListener('pagehide', () => view3d?.dispose(), {once: true});
