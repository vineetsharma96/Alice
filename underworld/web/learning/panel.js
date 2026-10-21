'use strict';
let data;
const byId = id => document.getElementById(id);
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function render() {
  const agent = byId('person').value;
  const p = data.people[agent];
  const o = p.observation;
  byId('caution').textContent = data.caution;
  const body = o.own_state.body;
  const actions = o.recent_action_results.slice(-3).map(r=>
    `${r.request_id}: ${r.status}${r.error_code ? ' · '+r.error_code : ''} · ${r.observable_effects?.description || ''}`);
  byId('current').textContent = [
    `${agent} · native tick ${o.tick} · ${o.own_state.busy ? 'busy' : 'idle'}`,
    `Health ${body.health.toFixed(3)} · hunger ${body.hunger.toFixed(3)} · thirst ${body.thirst.toFixed(3)}`,
    `Carried material (micrograms): ${JSON.stringify(o.own_state.inventory_ug)}`,
    ...actions,
    `Pending attention: ${p.pending_attention?.id ?? 'none'} · pending message: ${p.pending_message ?? 'none'}`
  ].join('\n');
  byId('observation').textContent = JSON.stringify(o,null,2);
  byId('counts').replaceChildren(...Object.entries(p.counters).map(([key, value]) => {
    const item = element('div', key.replaceAll('_', ' '), 'count');
    item.append(element('strong', String(value))); return item;
  }));
  const meanings = p.hypotheses.map(h => {
    const item = element('div', undefined, 'meaning');
    item.append(element('code', h.channel), element('p', `${h.count} exposures · ${h.uncertainty}`),
      element('p', `Inferred features: ${h.inferred_features.join(' or ') || 'no consistent hypothesis'}`),
      element('small', `Memory sources: ${h.evidence.join(', ')}`)); return item;
  });
  byId('meanings').replaceChildren(...(meanings.length ? meanings : [element('p', 'No learned H5 meanings for this inhabitant.')]));
  byId('vocab').replaceChildren(...Object.entries(data.people).map(([id, person]) => {
    const item = element('details', undefined, 'vocabulary');
    item.append(element('summary', `${id} · ${Object.keys(person.production).length} privately coined factors`),
      element('pre', JSON.stringify(person.production, null, 2))); return item;
  }));
  byId('history').replaceChildren(...p.recent_records.map(r => {
    const item = element('details');
    const payload = r.payload;
    const actual = payload.text || payload.message?.text || '';
    item.append(element('summary', `${r.kind} · ${actual} · ${payload.target || r.id}`),
      element('pre', JSON.stringify(payload, null, 2))); return item;
  }));
  byId('status').textContent = `Read-only snapshot · ${data.simulated_s} simulated seconds · ${agent}`;
}
async function refresh() {
  byId('refresh').disabled = true;
  try {
    const response = await fetch('/api/learning', {cache: 'no-store'});
    if (!response.ok) throw new Error(`Evidence unavailable (${response.status}). No inferred data is substituted.`);
    data = await response.json();
    const selected = byId('person').value;
    byId('person').replaceChildren(...Object.keys(data.people).map(id => {
      const option = element('option', id); option.value = id; return option;
    }));
    if (data.people[selected]) byId('person').value = selected;
    render();
  } catch (error) {
    data = undefined;
    for (const id of ['current', 'observation', 'counts', 'meanings', 'vocab', 'history']) byId(id).replaceChildren();
    byId('status').textContent = error.message;
  } finally { byId('refresh').disabled = false; }
}
byId('person').addEventListener('change', () => { if (data) render(); });
byId('refresh').addEventListener('click', refresh);
refresh();
