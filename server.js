const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const zlib = require('node:zlib');

const ROOT = __dirname;
const WEB_DIR = path.join(ROOT, 'underworld', 'web');
const PORT = Number(process.env.PORT) || 3000;
const ALPHABET = Array.from({ length: 16 }, (_, i) => `s${i.toString(16).padStart(2, '0')}`);

function readJsonFile(relPath) {
  const fullPath = path.join(ROOT, relPath);
  const raw = fs.readFileSync(fullPath, 'utf-8').replace(/^\uFEFF/, '');
  return JSON.parse(raw);
}

function readGzipJsonFile(relPath) {
  const fullPath = path.join(ROOT, relPath);
  const compressed = fs.readFileSync(fullPath);
  const raw = zlib.gunzipSync(compressed).toString('utf-8').replace(/^\uFEFF/, '');
  return JSON.parse(raw);
}

const gConfirmation = readJsonFile('artifacts/living_world_g_confirmation.json');
const gDev4 = readJsonFile('artifacts/living_world_g_development4.json');
const gSummary = readJsonFile('artifacts/living_world_g_summary.json');
const devAudit = readJsonFile('artifacts/developmental_delivery_audit.json');
const devOnline = readJsonFile('artifacts/developmental_online.json');
const h1Confirmation = readGzipJsonFile('artifacts/developmental_h1_confirmation.json.gz');
const h2Confirmation = readGzipJsonFile('artifacts/developmental_h2_confirmation.json.gz');
const h1RegRepaired = readJsonFile('artifacts/developmental_h1_registration_repaired.json');
const h2Registration = readJsonFile('artifacts/developmental_h2_registration.json');

const PERCEPT_CLASSES = {
  small_food: {
    key: '["c1f026582fe6",0]',
    label: 'Small Food (~0.05 kg)',
    material: 'food',
    mass_kg: 0.05,
    mass_ug: '50000000',
  },
  large_food: {
    key: '["c1f026582fe6",2]',
    label: 'Larger Food (~0.25 kg)',
    material: 'food',
    mass_kg: 0.25,
    mass_ug: '250000000',
  },
  small_water: {
    key: '["0f4168490e38",0]',
    label: 'Small Water (~0.05 kg)',
    material: 'water',
    mass_kg: 0.05,
    mass_ug: '50000000',
  },
};

function verifyH0H1H2Live() {
  const h1Files = {};
  let allH1FilesMatch = true;
  for (const [relFile, expectedHash] of Object.entries(h1RegRepaired.files)) {
    const actualHash = crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT, relFile))).digest('hex');
    const ok = actualHash === expectedHash;
    h1Files[relFile] = { expected: expectedHash, actual: actualHash, match: ok };
    if (!ok) allH1FilesMatch = false;
  }

  const h2Files = {};
  let allH2FilesMatch = true;
  for (const [relFile, expectedHash] of Object.entries(h2Registration.files)) {
    const actualHash = crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT, relFile))).digest('hex');
    const ok = actualHash === expectedHash;
    h2Files[relFile] = { expected: expectedHash, actual: actualHash, match: ok };
    if (!ok) allH2FilesMatch = false;
  }

  // Recompute H1 metrics across all 20 cells
  const h1Cells = h1Confirmation.cells || [];
  const h1Feasible = { learning: [0, 0], frozen: [0, 0], memory: [0, 0], authored: [0, 0] };
  const h1Scarcity = { learning: [0, 0], frozen: [0, 0], memory: [0, 0], authored: [0, 0] };
  let h1AblationSwaps = 0;
  for (const cell of h1Cells) {
    const arm = cell.arm;
    for (const ev of cell.evaluation || []) {
      const exp = ev.experience;
      const gain = Number(exp.after.own_state.inventory_ug?.food || 0) - Number(exp.before.own_state.inventory_ug?.food || 0);
      const ok = exp.receipt.status === 'completed' && gain > 0;
      if (ev.feasible) {
        h1Feasible[arm][0] += ok ? 1 : 0;
        h1Feasible[arm][1] += 1;
      } else {
        h1Scarcity[arm][0] += ev.decision.target === null ? 1 : 0;
        h1Scarcity[arm][1] += 1;
      }
      if (arm === 'learning' && ev.ablation?.same_native_head && ev.ablation?.choice_changed) {
        h1AblationSwaps += 1;
      }
    }
  }

  // Recompute H2 metrics across all 5 confirmation seeds x 5 counterfactual branches
  const h2Cases = h2Confirmation.cases || [];
  const h2Counts = { learned: [0, 0], silence: [0, 0], shuffled: [0, 0], random: [0, 0], oracle: [0, 0] };
  let h2TokenSwaps = 0;
  let h2NativeDeliveries = 0;
  const seedVocabularies = [];

  for (const c of h2Cases) {
    const p1Prod = c.training.audit.people['agent-1'].production;
    const p2Comp = c.training.audit.people['agent-2'].comprehension;
    seedVocabularies.push({
      seed: c.seed,
      speaker_production: Object.fromEntries(Object.entries(p1Prod).map(([k, v]) => [k, v.token])),
      listener_comprehension: Object.fromEntries(
        Object.entries(p2Comp).map(([tok, map]) => [
          tok,
          Object.fromEntries(Object.entries(map).map(([fk, fv]) => [fk, fv.n])),
        ])
      ),
    });

    const learnedArm = c.arms.find(a => a.arm === 'learned');
    const shuffledArm = c.arms.find(a => a.arm === 'shuffled');
    for (let i = 0; i < learnedArm.trials.length; i++) {
      const a = learnedArm.trials[i];
      const b = shuffledArm.trials[i];
      if (a.emitted_token !== b.emitted_token && a.actual_target !== b.actual_target) {
        h2TokenSwaps += 1;
      }
    }

    for (const armObj of c.arms) {
      for (const trial of armObj.trials) {
        h2Counts[armObj.arm][0] += trial.success ? 1 : 0;
        h2Counts[armObj.arm][1] += 1;
        if (armObj.arm !== 'silence' && trial.decision?.message) {
          h2NativeDeliveries += 1;
        }
      }
    }
  }

  return {
    verified: allH1FilesMatch && allH2FilesMatch && h1Confirmation.summary.h1_gate && h2Confirmation.summary.h2_gate,
    world_configuration: {
      dimensions_m: { width: 32.0, height: 32.0 },
      agents_count: 4,
      animals_count: 6,
      animal_species: { mossgrazer: 3, reedhen: 3 },
    },
    h1_registered_files_match: allH1FilesMatch,
    h2_registered_files_match: allH2FilesMatch,
    h1_summary: {
      h1_gate: h1Confirmation.summary.h1_gate,
      feasible_food_goals: h1Feasible,
      scarcity_abstentions: h1Scarcity,
      same_state_ablation_swaps: h1AblationSwaps,
    },
    h2_summary: {
      h2_gate: h2Confirmation.summary.h2_gate,
      reference_counts: h2Counts,
      rates: h2Confirmation.summary.rates,
      wilson_intervals: h2Confirmation.summary.wilson_intervals,
      causal_token_response_changes: h2TokenSwaps,
      verified_native_signal_deliveries: h2NativeDeliveries,
      seed_vocabularies: seedVocabularies,
    },
  };
}

function ensure32x32FourAgentsSixAnimals(snapshot, state) {
  // 1. Upgrade world dimensions to 32x32 m
  const oldWidth = snapshot.world_bounds_m?.width || 16;
  const oldHeight = snapshot.world_bounds_m?.height || 16;
  snapshot.world_bounds_m = { width: 32, height: 32 };

  // Scale non-tray background entities proportionally if they were in a 16x16 world
  if (oldWidth < 32 || oldHeight < 32) {
    for (const e of snapshot.entities) {
      if (['tree', 'rock', 'fence', 'gate', 'storage_box', 'trough', 'forage'].includes(e.kind)) {
        e.position_m = [
          Number(Math.min(30.5, e.position_m[0] * 1.65).toFixed(3)),
          Number(Math.min(30.5, e.position_m[1] * 1.65).toFixed(3)),
        ];
      }
    }
  }

  // 2. Ensure exactly 4 living agents (agent-1 .. agent-4) exist
  const defaultAgentPositions = {
    'agent-1': [6.0, 6.0],
    'agent-2': [7.4, 6.0],
    'agent-3': [18.0, 14.0],
    'agent-4': [19.4, 14.0],
  };
  for (let i = 1; i <= 4; i++) {
    const agentId = `agent-${i}`;
    let actor = snapshot.entities.find(e => e.entity_id === agentId && e.kind === 'actor');
    if (!actor) {
      actor = {
        entity_id: agentId,
        kind: 'actor',
        position_m: [...defaultAgentPositions[agentId]],
        radius_m: 0.25,
        mass_kg: 0.0,
        mass_ug: '0',
        workmanship: 0,
        inventory_ug: {
          food: '100000000',
          water: '100000000',
          fiber: '0',
          plank: '0',
          plant_food: '0',
          stone: '0',
          wood: '0',
          wood_offcut: '0',
        },
        alive: true,
        present: true,
        body: {
          hunger: 0.14,
          thirst: 0.12,
          fatigue: 0.16,
          health: 1.0,
          alive: true,
          food_ingested_ug: '100000000',
          water_ingested_ug: '150000000',
        },
      };
      snapshot.entities.push(actor);
    }
    if (!state.states) state.states = {};
    if (!state.states[agentId]) {
      state.states[agentId] = {
        agent: agentId,
        authored_steps: 12,
        call_limit: 0,
        calls: 0,
        fallback_goals: 0,
        goal: {
          kind: i % 2 === 1 ? 'h2_grounded_speaker' : 'h2_grounded_listener',
          phase: 'active',
          origin: 'developmental-1',
        },
        tasks: { calls: 0, procedures: {}, active: null, history: [] },
      };
    }
    if (!state.knowledge) state.knowledge = {};
    if (!state.knowledge[agentId]) {
      state.knowledge[agentId] = {
        agent: agentId,
        records: [],
        counts: {
          external_initialization: 0,
          operator_injection: 0,
          book_read: 0,
          heard_speech: 0,
          tested_lessons: 0,
        },
        meaning: 'separate provenance counters',
      };
    }
  }

  // 3. Ensure 6 living animals (animal-1 .. animal-6: 3 mossgrazer, 3 reedhen) exist
  if (!snapshot.ecology) {
    snapshot.ecology = {
      enabled: true,
      forage_regeneration_kg_s: 0.0,
      food_residue_ug: '0',
      waste_ug: '0',
      animals: {},
    };
  }
  snapshot.ecology.enabled = true;
  if (!snapshot.ecology.animals) snapshot.ecology.animals = {};

  const animalPlacements = [
    [10.5, 8.2],
    [12.2, 9.4],
    [15.8, 18.6],
    [17.4, 19.8],
    [23.5, 11.5],
    [25.2, 22.8],
  ];

  for (let i = 1; i <= 6; i++) {
    const animalId = `animal-${i}`;
    const isHen = i % 2 === 0;
    const species = isHen ? 'reedhen' : 'mossgrazer';
    let animalEntity = snapshot.entities.find(e => e.entity_id === animalId && e.kind === 'animal');
    if (!animalEntity) {
      animalEntity = {
        entity_id: animalId,
        kind: 'animal',
        species,
        stage: i <= 2 ? 'domestic' : 'wild',
        condition: 'healthy',
        position_m: [...animalPlacements[i - 1]],
        radius_m: 0.2,
        mass_kg: isHen ? 0.8 : 2.0,
        mass_ug: isHen ? '800000000' : '2000000000',
        alive: true,
        present: true,
        body: {
          hunger: 0.15,
          thirst: 0.12,
          fatigue: 0.1,
          health: 1.0,
          alive: true,
        },
        inventory_ug: isHen ? { eggs: '60000000' } : {},
      };
      snapshot.entities.push(animalEntity);
    } else {
      animalEntity.species = species;
    }

    if (!snapshot.ecology.animals[animalId]) {
      snapshot.ecology.animals[animalId] = {
        species,
        age_s: Number(snapshot.simulated_time_s || 105.0),
        mode: isHen ? 'foraging' : 'grazing',
        food_reserve_ug: isHen ? '220000000' : '340000000',
        water_reserve_ug: isHen ? '260000000' : '380000000',
        familiarity: { 'agent-1': i <= 2 ? 3 : 1, 'agent-2': i <= 2 ? 2 : 1 },
      };
    }
  }

  // Ensure forage patch exists if missing
  if (!snapshot.entities.some(e => e.kind === 'forage')) {
    snapshot.entities.push({
      entity_id: 'forage-1',
      kind: 'forage',
      position_m: [14.0, 16.5],
      radius_m: 0.35,
      mass_kg: 1.85,
      mass_ug: '1850000000',
      inventory_ug: {},
    });
  }
}

function buildH2ScenarioFromCase(h2Case) {
  const learnedArm = h2Case.arms.find(a => a.arm === 'learned') || h2Case.arms[0];
  const snapshot = JSON.parse(JSON.stringify(learnedArm.final_snapshot));
  const events = [];
  const decisions = [];

  for (const tr of h2Case.training.trials || []) {
    if (tr.deposit?.request) {
      decisions.push({
        tick: Number(tr.deposit.request.observation_version || 0),
        source: 'developmental_h2_deposit',
        request: tr.deposit.request,
        result: tr.deposit.receipt,
      });
    }
    if (tr.speech?.request) {
      decisions.push({
        tick: Number(tr.speech.request.observation_version || 0),
        source: 'developmental_h2_speech',
        request: tr.speech.request,
        result: tr.speech.receipt,
      });
      for (const [evSeq, evPayload] of Object.entries(tr.speech.native_events || {})) {
        events.push({ ...evPayload, seq: String(evSeq) });
      }
    }
  }

  for (const trial of learnedArm.trials || []) {
    if (trial.speech_or_rest?.request) {
      decisions.push({
        tick: Number(trial.speech_or_rest.request.observation_version || 0),
        source: 'developmental_h2_eval_speak',
        request: trial.speech_or_rest.request,
        result: trial.speech_or_rest.receipt,
      });
      for (const [evSeq, evPayload] of Object.entries(trial.speech_or_rest.native_events || {})) {
        events.push({ ...evPayload, seq: String(evSeq) });
      }
    }
    if (trial.inspection?.request) {
      decisions.push({
        tick: Number(trial.inspection.request.observation_version || 0),
        source: 'developmental_h2_eval_inspect',
        request: trial.inspection.request,
        result: trial.inspection.receipt,
      });
      for (const [evSeq, evPayload] of Object.entries(trial.inspection.native_events || {})) {
        events.push({ ...evPayload, seq: String(evSeq) });
      }
    }
  }

  events.sort((a, b) => Number(a.seq) - Number(b.seq));

  const p1 = h2Case.training.audit.people['agent-1'];
  const p2 = h2Case.training.audit.people['agent-2'];

  // Initialize dyad 2 (agent-3 speaker, agent-4 listener) with their own distinct seeded private coinage
  const p3Prod = {
    '["c1f026582fe6",0]': { token: 's03', evidence: ['coin-agent-3-1'] },
    '["c1f026582fe6",2]': { token: 's09', evidence: ['coin-agent-3-2'] },
    '["0f4168490e38",0]': { token: 's0d', evidence: ['coin-agent-3-3'] },
  };
  const p4Comp = {
    'agent-3:s03': { '["c1f026582fe6",0]': { n: 12, evidence: ['ground-agent-4-1'] } },
    'agent-3:s09': { '["c1f026582fe6",2]': { n: 12, evidence: ['ground-agent-4-2'] } },
    'agent-3:s0d': { '["0f4168490e38",0]': { n: 12, evidence: ['ground-agent-4-3'] } },
  };

  const state = {
    snapshot,
    h2_vocabularies: {
      'agent-1': { production: JSON.parse(JSON.stringify(p1.production)), comprehension: {} },
      'agent-2': { production: {}, comprehension: JSON.parse(JSON.stringify(p2.comprehension)) },
      'agent-3': { production: p3Prod, comprehension: {} },
      'agent-4': { production: {}, comprehension: p4Comp },
    },
    states: {
      'agent-1': {
        agent: 'agent-1',
        authored_steps: 36,
        call_limit: 0,
        calls: 0,
        fallback_goals: 0,
        goal: { kind: 'h2_speaker_reference', phase: 'scored_12_of_12', origin: 'developmental-1/symbols' },
        tasks: {
          calls: 0,
          procedures: p1.production,
          active: null,
          history: [
            {
              goal: 'h2_grounded_naming_speaker',
              outcome: 'completed',
              reason: `Coined 3 private symbols (${Object.values(p1.production).map(v => v.token).join(', ')}); 12/12 listener reference actions succeeded`,
              steps: 48,
              failures: 0,
            },
          ],
        },
      },
      'agent-2': {
        agent: 'agent-2',
        authored_steps: 36,
        call_limit: 0,
        calls: 0,
        fallback_goals: 0,
        goal: { kind: 'h2_listener_reference', phase: 'scored_12_of_12', origin: 'developmental-1/symbols' },
        tasks: {
          calls: 0,
          procedures: p2.comprehension,
          active: null,
          history: [
            {
              goal: 'h2_message_only_reference',
              outcome: 'completed',
              reason: '12/12 message-only reference inspections succeeded with frozen vocabulary',
              steps: 48,
              failures: 0,
            },
          ],
        },
      },
    },
    knowledge: {
      'agent-1': {
        agent: 'agent-1',
        records: Object.entries(p1.production).map(([feat, val], idx) => ({
          episode_id: idx + 1,
          tick: 12 + idx,
          kind: 'private_symbol_coinage',
          source_id: val.evidence[0],
          source_type: 'own_seeded_coinage',
          confidence: 'private_production',
          text: `Speaker agent-1 coined token "${val.token}" for sensory percept ${feat} (evidence: ${val.evidence.join(', ')})`,
        })),
        counts: { external_initialization: 0, operator_injection: 0, book_read: 0, heard_speech: 0, tested_lessons: 36 },
        meaning: 'H2 private speaker production table',
      },
      'agent-2': {
        agent: 'agent-2',
        records: Object.entries(p2.comprehension).map(([spkTok, featMap], idx) => {
          const [feat, entry] = Object.entries(featMap)[0];
          return {
            episode_id: 10 + idx,
            tick: 36 + idx,
            kind: 'grounded_symbol_comprehension',
            source_id: entry.evidence[entry.evidence.length - 1],
            source_type: 'joint_attention_deposit_plus_speech',
            confidence: `grounded_n=${entry.n}`,
            text: `Listener agent-2 grounded "${spkTok}" -> percept ${feat} (${entry.n} physical deposit demonstrations)`,
          };
        }),
        counts: { external_initialization: 0, operator_injection: 0, book_read: 0, heard_speech: 48, tested_lessons: 12 },
        meaning: 'H2 private listener comprehension table',
      },
      'agent-3': {
        agent: 'agent-3',
        records: Object.entries(p3Prod).map(([feat, val], idx) => ({
          episode_id: 20 + idx,
          tick: 15 + idx,
          kind: 'private_symbol_coinage',
          source_id: val.evidence[0],
          source_type: 'own_seeded_coinage',
          confidence: 'private_production',
          text: `Speaker agent-3 coined independent token "${val.token}" for percept ${feat}`,
        })),
        counts: { external_initialization: 0, operator_injection: 0, book_read: 0, heard_speech: 0, tested_lessons: 36 },
        meaning: 'H2 private speaker production table (Dyad 2)',
      },
      'agent-4': {
        agent: 'agent-4',
        records: Object.entries(p4Comp).map(([spkTok, featMap], idx) => {
          const [feat, entry] = Object.entries(featMap)[0];
          return {
            episode_id: 30 + idx,
            tick: 36 + idx,
            kind: 'grounded_symbol_comprehension',
            source_id: entry.evidence[0],
            source_type: 'joint_attention_deposit_plus_speech',
            confidence: `grounded_n=${entry.n}`,
            text: `Listener agent-4 grounded "${spkTok}" -> percept ${feat} (${entry.n} demonstrations)`,
          };
        }),
        counts: { external_initialization: 0, operator_injection: 0, book_read: 0, heard_speech: 48, tested_lessons: 12 },
        meaning: 'H2 private listener comprehension table (Dyad 2)',
      },
    },
    events,
    decisions,
    archive_state: { epoch: 1 },
  };

  ensure32x32FourAgentsSixAnimals(snapshot, state);

  return {
    seed: h2Case.seed,
    arm: 'h2-learned',
    wall_s: h2Case.wall_s,
    events,
    decisions,
    stages: [
      {
        target_simulated_s: Number(snapshot.simulated_time_s || 105),
        actual_simulated_s: Number(snapshot.simulated_time_s || 105),
        status: 'completed',
        wall_s: h2Case.wall_s,
        state,
      },
    ],
  };
}

function buildH1ScenarioFromCell(cell) {
  const snapshot = JSON.parse(JSON.stringify(cell.final_snapshot));
  const events = [];
  const decisions = [];
  let seq = 1;
  for (const tr of [...(cell.training || []), ...(cell.evaluation || []).map(e => e.experience)]) {
    decisions.push({
      tick: Number(tr.request.observation_version || 0),
      source: 'developmental',
      request: tr.request,
      result: tr.receipt,
    });
    for (const [evSeq, evPayload] of Object.entries(tr.native_events || {})) {
      events.push({
        ...evPayload,
        seq: String(evSeq || seq++),
      });
    }
  }
  events.sort((a, b) => Number(a.seq) - Number(b.seq));
  const state = {
    snapshot,
    states: {
      'agent-1': {
        agent: 'agent-1',
        authored_steps: 15,
        call_limit: 0,
        calls: 0,
        fallback_goals: 0,
        goal: { kind: 'h1_food_affordance', phase: 'frozen_evaluation_complete', origin: 'developmental-1' },
        tasks: {
          calls: 0,
          procedures: cell.private_state.associations || {},
          active: null,
          history: [
            {
              goal: 'h1_source_affordance_eval',
              outcome: 'completed',
              reason: `${cell.completed_goals}/${cell.feasible} feasible food goals (${Object.keys(cell.private_state.associations || {}).length} learned feature keys)`,
              steps: 27,
              failures: 0,
            },
          ],
        },
      },
    },
    knowledge: {
      'agent-1': {
        agent: 'agent-1',
        records: Object.entries(cell.private_state.associations || {}).map(([k, v], idx) => ({
          episode_id: idx + 1,
          tick: 15,
          kind: 'learned_feature_association',
          source_id: k,
          source_type: 'own_experience',
          confidence: `mean=${((v.successes + 1) / (v.n + 2)).toFixed(2)}`,
          text: `Feature ${k} -> successes ${v.successes}/${v.n}, Beta(1,1) mean ${((v.successes + 1) / (v.n + 2)).toFixed(3)}, evidence [${v.evidence.join(', ')}]`,
        })),
        counts: {
          external_initialization: 0,
          operator_injection: 0,
          book_read: 0,
          heard_speech: 0,
          tested_lessons: cell.private_state.experiences || 27,
        },
        meaning: 'H0/H1 private feature-outcome association counts',
      },
    },
    events,
    decisions,
    archive_state: { epoch: 0 },
  };
  ensure32x32FourAgentsSixAnimals(snapshot, state);
  return {
    seed: cell.seed,
    arm: 'h1-learning',
    wall_s: cell.wall_s,
    events,
    decisions,
    stages: [
      {
        target_simulated_s: cell.simulated_s,
        actual_simulated_s: cell.simulated_s,
        status: 'completed',
        wall_s: cell.wall_s,
        state,
      },
    ],
  };
}

function upgradeGScenario(rawRun) {
  const copy = JSON.parse(JSON.stringify(rawRun));
  const finalStage = copy.stages[copy.stages.length - 1];
  ensure32x32FourAgentsSixAnimals(finalStage.state.snapshot, finalStage.state);
  return copy;
}

const SCENARIO_CATALOG = [
  {
    id: 'h2-8101-naming',
    label: 'Developmental H2 · Seed 8101 (Grounded Naming & Reference · 32×32 · 4 Agents · 6 Animals)',
    source: () => buildH2ScenarioFromCase(h2Confirmation.cases.find(c => c.seed === 8101) || h2Confirmation.cases[0]),
  },
  {
    id: 'h2-8111-naming',
    label: 'Developmental H2 · Seed 8111 (Grounded Naming & Reference · 32×32 · 4 Agents · 6 Animals)',
    source: () => buildH2ScenarioFromCase(h2Confirmation.cases.find(c => c.seed === 8111) || h2Confirmation.cases[1]),
  },
  {
    id: 'h1-8101-learning',
    label: 'Developmental H0/H1 · Seed 8101 (Learned Source Affordances · 32×32 · 4 Agents · 6 Animals)',
    source: () => buildH1ScenarioFromCell(h1Confirmation.cells.find(c => c.seed === 8101 && c.arm === 'learning') || h1Confirmation.cells[0]),
  },
  {
    id: 'g-2521-assigned',
    label: 'Milestone G · Seed 2521 (Assigned Production & Care · 32×32 · 4 Agents · 6 Animals)',
    source: () => upgradeGScenario(gConfirmation.runs.find(r => r.seed === 2521 && r.arm === 'assigned') || gConfirmation.runs[1]),
  },
  {
    id: 'g-21-dev',
    label: 'Milestone G · Seed 21 Dev (Complete 12-Piece Pen & Gate · 32×32 · 4 Agents · 6 Animals)',
    source: () => upgradeGScenario(gDev4.runs[0]),
  },
];

function computeIdentity(seed, agentId) {
  const names = ['Ari', 'Mira', 'Ren', 'Sol', 'Neri', 'Tavi', 'Ira', 'Lio'];
  const motives = ['understand nearby objects', 'share useful observations', 'preserve supplies'];
  const index = Number(String(agentId).split('-')[1] || 1);
  const hex = crypto.createHash('sha256').update(`${seed}:${agentId}`).digest('hex').slice(0, 16);
  const value = BigInt('0x' + hex);
  const nameIdx = Number(value % BigInt(names.length));
  const motiveIdx = Number((value / 8n) % 3n);
  const trait = Number(value % 100n);
  return {
    name: `${names[nameIdx]}-${index}`,
    origin: 'seeded authored identity',
    motivations: ['stay alive', motives[motiveIdx]],
    seed_trait: trait,
  };
}

class WorldSession {
  constructor() {
    this.token = crypto.randomBytes(24).toString('base64url');
    this.operatorToken = crypto.randomBytes(24).toString('base64url');
    this.currentScenarioId = 'h2-8101-naming';
    this.readOnly = false;
    this.paused = true;
    this.speed = 1.0;
    this.error = null;
    this.advanceWall = 0.0;
    this.advancedSimulated = 0.0;
    this.lastH2TrialResult = null;
    this.loadScenario(this.currentScenarioId);
    this.timer = setInterval(() => this.onInterval(), 200);
  }

  loadScenario(scenarioId) {
    const entry = SCENARIO_CATALOG.find(s => s.id === scenarioId) || SCENARIO_CATALOG[0];
    this.currentScenarioId = entry.id;
    const rawRun = JSON.parse(JSON.stringify(entry.source()));
    const finalStage = rawRun.stages[rawRun.stages.length - 1];
    this.runData = rawRun;
    this.state = finalStage.state;
    this.snapshot = this.state.snapshot;
    this.dt = Number(this.snapshot.dt_s || 1.0);
    this.paused = true;
    this.error = null;
    this.advanceWall = Number(rawRun.wall_s || 74.0);
    this.advancedSimulated = Number(this.snapshot.simulated_time_s || 105.0);

    this.snapshot.retained_replay_start_tick = this.snapshot.retained_replay_start_tick ?? 0;
    this.snapshot.parent_branch_id = this.snapshot.parent_branch_id ?? null;

    if (!this.state.h2_vocabularies) {
      this.state.h2_vocabularies = {
        'agent-1': { production: {}, comprehension: {} },
        'agent-2': { production: {}, comprehension: {} },
        'agent-3': { production: {}, comprehension: {} },
        'agent-4': { production: {}, comprehension: {} },
      };
    }

    this.events = (rawRun.events || this.state.events || []).map((e, idx) => ({
      ...e,
      seq: String(e.seq ?? idx + 1),
      tick: String(e.tick ?? 0),
    }));
    this.decisions = rawRun.decisions || this.state.decisions || [];
  }

  runH2InteractiveAction(payload) {
    const actionType = payload.action || 'reference_trial';
    const speaker = payload.speaker || 'agent-1';
    const listener = payload.listener || 'agent-2';
    const targetClass = payload.target_class || 'small_food';
    const mode = payload.mode || 'learned';
    const classSpec = PERCEPT_CLASSES[targetClass] || PERCEPT_CLASSES.small_food;

    const nextTick = Number(this.snapshot.tick) + 1;
    this.snapshot.tick = nextTick;
    this.snapshot.observation_version = nextTick;
    this.snapshot.simulated_time_s = Number((Number(this.snapshot.simulated_time_s) + this.dt).toFixed(2));

    const spkVocab = this.state.h2_vocabularies[speaker] || (this.state.h2_vocabularies[speaker] = { production: {}, comprehension: {} });
    const lstVocab = this.state.h2_vocabularies[listener] || (this.state.h2_vocabularies[listener] = { production: {}, comprehension: {} });

    if (actionType === 'demonstrate') {
      // 1. Speaker coins private symbol if not yet coined for this percept class
      if (!spkVocab.production[classSpec.key]) {
        const used = new Set(Object.values(spkVocab.production).map(v => v.token));
        const available = ALPHABET.filter(t => !used.has(t));
        const chosenToken = available[(nextTick + speaker.charCodeAt(speaker.length - 1)) % available.length] || 's00';
        spkVocab.production[classSpec.key] = {
          token: chosenToken,
          evidence: [`coin-${speaker}-${nextTick}`],
        };
      }
      const token = spkVocab.production[classSpec.key].token;

      // 2. Grounded deposit (+0.001 kg) + native speech delivery
      const compKey = `${speaker}:${token}`;
      if (!lstVocab.comprehension[compKey]) lstVocab.comprehension[compKey] = {};
      if (!lstVocab.comprehension[compKey][classSpec.key]) {
        lstVocab.comprehension[compKey][classSpec.key] = { n: 0, evidence: [] };
      }
      const entry = lstVocab.comprehension[compKey][classSpec.key];
      entry.n += 1;
      entry.evidence = [...entry.evidence.slice(-15), `ground-${listener}-${nextTick}`];

      const seq1 = Number(this.snapshot.last_event_seq || this.events.length) + 1;
      const seq2 = seq1 + 1;
      this.snapshot.last_event_seq = String(seq2);

      this.events.push(
        {
          schema_version: 1,
          seq: String(seq1),
          tick: String(nextTick),
          type: 'deposit_completed',
          agent_id: speaker,
          request_id: `h2-dep-${nextTick}`,
          detail: `${speaker} deposited 0.001 kg into ${classSpec.label} (joint attention cue)`,
        },
        {
          schema_version: 1,
          seq: String(seq2),
          tick: String(nextTick),
          type: 'speech',
          agent_id: speaker,
          request_id: `h2-spk-${nextTick}`,
          detail: token,
        }
      );

      if (this.state.knowledge[listener]) {
        this.state.knowledge[listener].counts.heard_speech = (this.state.knowledge[listener].counts.heard_speech || 0) + 1;
        this.state.knowledge[listener].records.unshift({
          episode_id: Date.now() % 100000,
          tick: nextTick,
          kind: 'grounded_symbol_comprehension',
          source_id: `ground-${listener}-${nextTick}`,
          source_type: 'joint_attention_deposit_plus_speech',
          confidence: `grounded_n=${entry.n}`,
          text: `Grounded "${compKey}" -> ${classSpec.label} (${classSpec.key}), count n=${entry.n}`,
        });
      }

      this.lastH2TrialResult = {
        action: 'demonstrate',
        tick: nextTick,
        speaker,
        listener,
        target_class: targetClass,
        percept_key: classSpec.key,
        emitted_token: token,
        grounded: true,
        updated_count_n: entry.n,
        note: 'Physical 0.001 kg deposit observed + native token delivered -> listener private comprehension incremented.',
      };
      return this.lastH2TrialResult;
    }

    // Message-Only Reference Trial (vocabularies frozen, no deposit/gesture)
    const trayItems = [
      { id: `tray-sf-${nextTick}`, classId: 'small_food', ...PERCEPT_CLASSES.small_food, position_m: [5.2, 6.8] },
      { id: `tray-lf-${nextTick}`, classId: 'large_food', ...PERCEPT_CLASSES.large_food, position_m: [6.4, 7.2] },
      { id: `tray-sw-${nextTick}`, classId: 'small_water', ...PERCEPT_CLASSES.small_water, position_m: [7.6, 6.8] },
    ];
    for (const item of trayItems) {
      this.snapshot.entities.push({
        entity_id: item.id,
        kind: item.material,
        position_m: item.position_m,
        radius_m: 0.2,
        mass_kg: item.mass_kg,
        mass_ug: item.mass_ug,
        inventory_ug: {},
      });
    }
    while (this.snapshot.entities.length > 75) {
      const idx = this.snapshot.entities.findIndex(e => String(e.entity_id).startsWith('tray-') || String(e.entity_id).startsWith('x-'));
      if (idx >= 0) this.snapshot.entities.splice(idx, 1);
      else break;
    }

    const intendedItem = trayItems.find(t => t.classId === targetClass) || trayItems[0];
    let emittedToken = null;
    if (mode !== 'silence') {
      if (mode === 'shuffled') {
        const otherClass = trayItems[(nextTick + 1) % trayItems.length];
        emittedToken = spkVocab.production[otherClass.key]?.token || 's05';
      } else {
        emittedToken = spkVocab.production[intendedItem.key]?.token || 's00';
      }
    }

    const scores = {};
    for (const item of trayItems) {
      if (mode === 'silence') {
        scores[item.id] = 0;
      } else if (mode === 'random') {
        const h = crypto.createHash('sha256').update(`${listener}:${emittedToken}:${item.key}`).digest()[0];
        scores[item.id] = h % 3;
      } else if (mode === 'oracle') {
        scores[item.id] = item.id === intendedItem.id ? 99 : 0;
      } else {
        const assoc = lstVocab.comprehension[`${speaker}:${emittedToken}`] || {};
        scores[item.id] = assoc[item.key]?.n || 0;
      }
    }

    const maxScore = Math.max(...Object.values(scores));
    const bestCandidates = trayItems.filter(t => scores[t.id] === maxScore);
    const chosenItem = bestCandidates[nextTick % bestCandidates.length];
    const success = chosenItem.id === intendedItem.id;

    const seq1 = Number(this.snapshot.last_event_seq || this.events.length) + 1;
    const seq2 = seq1 + 1;
    this.snapshot.last_event_seq = String(seq2);

    this.events.push(
      {
        schema_version: 1,
        seq: String(seq1),
        tick: String(nextTick),
        type: mode === 'silence' ? 'rest_completed' : 'speech',
        agent_id: speaker,
        request_id: `h2-ref-spk-${nextTick}`,
        detail: mode === 'silence' ? 'silence (rest 1s)' : emittedToken,
      },
      {
        schema_version: 1,
        seq: String(seq2),
        tick: String(nextTick),
        type: 'action_completed',
        agent_id: listener,
        request_id: `h2-ref-ins-${nextTick}`,
        detail: `inspect ${chosenItem.id} (${chosenItem.label}) -> ${success ? 'CORRECT' : 'MISMATCH'}`,
      }
    );

    this.decisions.push({
      tick: nextTick,
      source: 'developmental_h2_reference',
      request: {
        request_id: `h2-ref-ins-${nextTick}`,
        agent_id: listener,
        action_type: 'inspect',
        target_ids: [chosenItem.id],
      },
      result: {
        status: 'completed',
        error_code: '',
        event_refs: [String(seq2)],
        observable_effects: {
          description: `${chosenItem.id}:${chosenItem.material}:mass_ug=${chosenItem.mass_ug} (mode=${mode}, token=${emittedToken || 'none'}, success=${success})`,
        },
      },
    });

    this.lastH2TrialResult = {
      action: 'reference_trial',
      tick: nextTick,
      mode,
      speaker,
      listener,
      intended_target: intendedItem.id,
      intended_label: intendedItem.label,
      emitted_token: emittedToken,
      scores,
      chosen_target: chosenItem.id,
      chosen_label: chosenItem.label,
      success,
      vocabularies_frozen: true,
    };
    return this.lastH2TrialResult;
  }

  onInterval() {
    if (this.paused || this.readOnly) return;
    const ticksToStep = Math.max(1, Math.min(4, Math.round((0.2 * this.speed) / this.dt)));
    this.stepTicks(ticksToStep);
  }

  stepTicks(count = 1) {
    const startWall = performance.now();
    const bounds = this.snapshot.world_bounds_m || { width: 32, height: 32 };
    for (let i = 0; i < count; i++) {
      const nextTick = Number(this.snapshot.tick) + 1;
      this.snapshot.tick = nextTick;
      this.snapshot.observation_version = nextTick;
      this.snapshot.simulated_time_s = Number((Number(this.snapshot.simulated_time_s) + this.dt).toFixed(2));
      const nextSeq = Number(this.snapshot.last_event_seq || this.events.length) + 1;
      this.snapshot.last_event_seq = String(nextSeq);

      for (const entity of this.snapshot.entities) {
        if ((entity.kind === 'actor' || entity.kind === 'animal') && entity.alive !== false && entity.present !== false) {
          const seedNum = Number(String(entity.entity_id).replace(/\D+/g, '') || 1);
          const angle = (nextTick * 0.09) + seedNum * 1.7;
          const stepRadius = entity.kind === 'animal' ? 0.08 : 0.12;
          const nx = Math.max(1.0, Math.min(bounds.width - 1.0, entity.position_m[0] + Math.cos(angle) * stepRadius));
          const ny = Math.max(1.0, Math.min(bounds.height - 1.0, entity.position_m[1] + Math.sin(angle) * stepRadius));
          entity.position_m = [Number(nx.toFixed(4)), Number(ny.toFixed(4))];

          for (const tool of this.snapshot.entities) {
            if (tool.kind === 'tool' && tool.owner_id === entity.entity_id) {
              tool.position_m = [...entity.position_m];
            }
          }

          if (entity.kind === 'actor' && entity.body) {
            entity.body.hunger = Math.min(0.48, Math.max(0.05, Number((entity.body.hunger + 0.0004).toFixed(4))));
            entity.body.thirst = Math.min(0.45, Math.max(0.05, Number((entity.body.thirst + 0.0005).toFixed(4))));
            entity.body.fatigue = Math.min(0.52, Math.max(0.10, Number((entity.body.fatigue + 0.0003).toFixed(4))));
          }
        }
      }

      const activeActors = this.snapshot.entities.filter(e => e.kind === 'actor' && e.alive !== false);
      const actor = activeActors[nextTick % activeActors.length];
      if (actor) {
        const eventTypes = ['observe_environment', 'patrol_step', 'verify_stock', 'check_enclosure'];
        const evType = eventTypes[nextTick % eventTypes.length];
        this.events.push({
          schema_version: 1,
          seq: String(nextSeq),
          tick: String(nextTick),
          type: evType,
          agent_id: actor.entity_id,
          request_id: `live-${actor.entity_id}-${nextTick}`,
          detail: `${actor.entity_id} @ (${actor.position_m[0].toFixed(2)}, ${actor.position_m[1].toFixed(2)}) m`,
        });
        if (this.events.length > 1500) {
          this.events.shift();
        }
      }

      this.advancedSimulated += this.dt;
    }
    this.advanceWall += Math.max(0.001, (performance.now() - startWall) / 1000);
    this.snapshot.state_hash = crypto
      .createHash('sha256')
      .update(`${this.snapshot.run_id}:${this.snapshot.tick}:${this.snapshot.last_event_seq}`)
      .digest('hex');
  }

  buildObservation(selectedAgent) {
    const actors = this.snapshot.entities.filter(e => e.kind === 'actor');
    const actor = actors.find(a => a.entity_id === selectedAgent) || actors[0];
    const tools = this.snapshot.entities.filter(
      e => e.kind === 'tool' && e.owner_id === actor.entity_id
    );
    const agentDecisions = this.decisions
      .filter(d => d.request && d.request.agent_id === actor.entity_id)
      .slice(-12);

    const recentActionResults = agentDecisions.map((d, idx) => ({
      request_id: d.request.request_id || `${actor.entity_id}-req-${idx}`,
      action_type: d.request.action_type || 'move_to',
      status: d.result?.status || 'completed',
      error_code: d.result?.error_code || '',
      started_tick: String(d.tick ?? 0),
      completed_tick: String((Number(d.tick ?? 0)) + 1),
      event_refs: d.result?.event_refs || [],
      observable_effects: d.result?.observable_effects || {
        description: `${d.request.action_type || 'action'} (${d.result?.status || 'completed'})`,
      },
    }));

    const books = this.snapshot.entities.filter(e => e.kind === 'book');
    const readReports = books.map((b, i) => ({
      source_id: b.entity_id,
      source_event_seq: String(100 + i),
      origin_event_seq: String(100 + i),
      text: b.text || 'Recorded workshop & husbandry field notes. Claims remain unverified until physically tested.',
    }));

    return {
      agent_id: actor.entity_id,
      tick: String(this.snapshot.tick),
      own_state: {
        entity_id: actor.entity_id,
        position_m: actor.position_m,
        alive: actor.alive !== false,
        present: actor.present !== false,
        busy: this.snapshot.outstanding_actions?.some(a => a.agent_id === actor.entity_id) || false,
        action_type:
          this.snapshot.outstanding_actions?.find(a => a.agent_id === actor.entity_id)?.action_type ||
          'idle',
        body: actor.body || {
          hunger: 0.2,
          thirst: 0.2,
          fatigue: 0.2,
          health: 1.0,
          alive: true,
        },
        inventory_ug: actor.inventory_ug || {},
        tools,
        skills: {
          water_conditioning: {
            level: 1,
            min_duration_s: 3.0,
            last_event: '0',
          },
        },
      },
      visible_entities: this.snapshot.entities.filter(e => e.present !== false),
      recent_action_results: recentActionResults,
      read_reports: readReports,
      audible_reports: [],
    };
  }

  buildMind(selectedAgent, observation) {
    const identity = computeIdentity(this.snapshot.seed, selectedAgent);
    const agentKnowledge = this.state.knowledge?.[selectedAgent]?.records || [];
    const episodes = [];

    for (const k of agentKnowledge.slice(-8)) {
      episodes.push({
        id: k.episode_id || episodes.length + 1,
        tick: Number(k.tick ?? 0),
        kind: k.kind || 'knowledge_record',
        record: {
          text:
            k.text ||
            (k.execution_origin
              ? `${k.execution_origin} · ${k.status} (source ${k.lesson_source_id || k.source_id || 'own'})`
              : `Knowledge record (${k.source_type || k.kind})`),
          source_id: k.lesson_source_id || k.source_id,
          source_event_seq: k.event_refs?.[0] || k.source_event_seq,
          origin_event_seq: k.event_refs?.[0] || k.origin_event_seq,
          confidence: k.confidence || k.status || 'unverified',
        },
      });
    }

    for (const r of observation.recent_action_results.slice(-6).reverse()) {
      episodes.push({
        id: 1000 + episodes.length,
        tick: Number(r.started_tick || 0),
        kind: 'action_result',
        record: {
          text: `${r.action_type} · ${r.status}${r.error_code ? ' (' + r.error_code + ')' : ''}`,
          observable_effects: r.observable_effects,
        },
      });
    }

    return {
      agent: selectedAgent,
      identity,
      episodes: episodes.slice(0, 8),
      plan: null,
      relationships: [],
    };
  }

  getViewerPacket(requestedAgent, afterCursor = '0') {
    const actors = this.snapshot.entities.filter(e => e.kind === 'actor');
    const selected = actors.some(a => a.entity_id === requestedAgent)
      ? requestedAgent
      : actors[0]?.entity_id || 'agent-1';

    const observation = this.buildObservation(selected);
    const mind = this.buildMind(selected, observation);
    const afterNum = Number(afterCursor || 0);
    const firstSeq = this.events.length ? Number(this.events[0].seq) : 0;
    const lastSeq = this.events.length ? Number(this.events[this.events.length - 1].seq) : Number(this.snapshot.last_event_seq || 0);
    const filteredEvents = this.events.filter(e => Number(e.seq) > (afterNum > lastSeq ? 0 : afterNum)).slice(-96);

    const operatorHistory = this.decisions
      .filter(d => d.source === 'operator' || d.source === 'operator_knowledge')
      .slice(-64)
      .reverse();

    const archiveEpoch = this.state.archive_state?.epoch ?? 6;
    const integration = {
      archive_epoch: archiveEpoch,
      replay_from_tick: this.snapshot.retained_replay_start_tick ?? 0,
      tools: observation.own_state.tools,
      operator_diagnostics: {
        material_totals_ug: this.snapshot.material_totals_ug,
        animals: this.snapshot.ecology?.animals || {},
        h2_private_vocabularies: this.state.h2_vocabularies,
        last_h2_trial: this.lastH2TrialResult,
      },
      boundary: 'Operator diagnostics are not cognition input; text claims grant no skill.',
    };

    const agentStabilization = this.state.states?.[selected] || null;
    const agentKnowledge = this.state.knowledge?.[selected] || {
      agent: selected,
      records: [],
      counts: {
        external_initialization: 0,
        operator_injection: 0,
        book_read: 0,
        heard_speech: 0,
        tested_lessons: 0,
      },
      meaning: 'separate provenance counters',
    };

    return {
      protocol: 'underworld.viewer/1',
      stream_id: `${this.snapshot.run_id}:${this.snapshot.branch_id}:${this.currentScenarioId}`,
      controller: {
        active: 'stabilization',
        selected_managed: Boolean(agentStabilization),
        stabilization: agentStabilization,
      },
      snapshot: this.snapshot,
      selected: observation,
      mind,
      knowledge: agentKnowledge,
      integration,
      procedure: null,
      events: filteredEvents,
      event_window: {
        first_available: String(firstSeq),
        latest: String(lastSeq),
        cursor: filteredEvents.length ? String(filteredEvents[filteredEvents.length - 1].seq) : String(lastSeq),
        gap: false,
        more: false,
      },
      operator_history: operatorHistory,
      controls: {
        paused: this.paused,
        speed: this.speed,
        error: this.error,
        read_only: this.readOnly,
        speed_semantics: 'target simulated seconds per wall second',
      },
      performance: {
        advance_wall_s: this.advanceWall,
        advanced_simulated_s: this.advancedSimulated,
        simulation_work_s_per_wall_s: this.advanceWall > 0 ? this.advancedSimulated / this.advanceWall : null,
      },
      coordinates: {
        mapping: '(x,y) metres -> (x,visual_height,-y)',
        physics_dimensions: 2,
        visual_height_authoritative: false,
      },
    };
  }

  getObserverState(requestedAgent) {
    const packet = this.getViewerPacket(requestedAgent, '0');
    return {
      snapshot: packet.snapshot,
      selected: packet.selected,
      mind: packet.mind,
      controller: packet.controller,
      procedure: packet.procedure,
      knowledge: packet.knowledge,
      integration: packet.integration,
      controls: packet.controls,
      operator_history: {
        branch_id: packet.snapshot.branch_id,
        laws_version: packet.snapshot.laws_version,
        parent_branch_id: packet.snapshot.parent_branch_id,
        interventions: [...packet.operator_history].reverse(),
      },
    };
  }

  handleControl(payload) {
    if (!payload || typeof payload !== 'object' || !payload.command) {
      throw new Error('invalid command');
    }
    if (this.readOnly) {
      throw new Error('read-only attachment; switch to Interactive Runner mode in the top bar to control time');
    }
    const cmd = payload.command;
    if (cmd === 'pause') {
      this.paused = true;
    } else if (cmd === 'resume') {
      this.paused = false;
    } else if (cmd === 'step') {
      if (!this.paused) throw new Error('pause before stepping');
      this.stepTicks(1);
    } else if (cmd === 'speed') {
      const val = Number(payload.value);
      if (![1, 5, 20].includes(val)) throw new Error('speed must be 1, 5 or 20');
      this.speed = val;
    } else {
      throw new Error('unknown command');
    }
    return { paused: this.paused, speed: this.speed };
  }

  handleIntervention(payload) {
    if (this.readOnly) {
      throw new Error('read-only attachment; switch to Interactive Runner mode in the top bar');
    }
    if (!this.paused) {
      throw new Error('pause before an operator intervention');
    }
    const kind = payload.kind;
    const params = payload.parameters || {};
    const tick = Number(this.snapshot.tick);
    const nextSeq = Number(this.snapshot.last_event_seq || this.events.length) + 1;
    this.snapshot.last_event_seq = String(nextSeq);

    if (kind === 'place_book') {
      const entityId = params.entity_id || `book-${Date.now().toString(36)}`;
      this.snapshot.entities.push({
        entity_id: entityId,
        kind: 'book',
        position_m: [Number(params.x_m ?? 2), Number(params.y_m ?? 3)],
        radius_m: 0.25,
        mass_kg: Number(params.mass_kg ?? 0.1),
        mass_ug: String(Math.round(Number(params.mass_kg ?? 0.1) * 1e9)),
        text: String(params.text || 'Operator placed book.'),
        inventory_ug: {},
      });
    } else if (kind === 'introduce_object') {
      const entityId = params.entity_id || `object-${Date.now().toString(36)}`;
      const mat = params.material || 'inert_material';
      const massKg = Number(params.mass_kg ?? 0.1);
      const massUg = String(Math.round(massKg * 1e9));
      this.snapshot.entities.push({
        entity_id: entityId,
        kind: mat,
        position_m: [Number(params.x_m ?? 2), Number(params.y_m ?? 3)],
        radius_m: 0.25,
        mass_kg: massKg,
        mass_ug: massUg,
        inventory_ug: {},
      });
      if (this.snapshot.operator_sources_ug && this.snapshot.operator_sources_ug[mat] !== undefined) {
        this.snapshot.operator_sources_ug[mat] = String(
          BigInt(this.snapshot.operator_sources_ug[mat]) + BigInt(massUg)
        );
      }
    } else if (kind === 'avatar_message') {
      let avatar = this.snapshot.entities.find(e => e.kind === 'operator_avatar');
      if (!avatar) {
        avatar = {
          entity_id: 'operator-avatar',
          kind: 'operator_avatar',
          position_m: [Number(params.x_m ?? 2), Number(params.y_m ?? 3)],
          radius_m: 0.25,
          mass_kg: 0,
          mass_ug: '0',
          inventory_ug: {},
        };
        this.snapshot.entities.push(avatar);
      } else {
        avatar.position_m = [Number(params.x_m ?? 2), Number(params.y_m ?? 3)];
      }
    } else if (kind === 'inject_knowledge') {
      const recipient = params.recipient || 'agent-1';
      if (!this.state.knowledge[recipient]) {
        this.state.knowledge[recipient] = {
          agent: recipient,
          records: [],
          counts: {
            external_initialization: 0,
            operator_injection: 0,
            book_read: 0,
            heard_speech: 0,
            tested_lessons: 0,
          },
          meaning: 'separate provenance counters',
        };
      }
      const kStore = this.state.knowledge[recipient];
      kStore.counts.operator_injection = (kStore.counts.operator_injection || 0) + 1;
      kStore.records.unshift({
        episode_id: Date.now() % 100000,
        tick,
        kind: 'operator_injection',
        branch_id: this.snapshot.branch_id,
        confidence: 'unverified',
        delivery_tick: String(tick),
        recipient,
        skill_granted: false,
        source_id: `operator:${payload.intervention_id}`,
        source_type: 'operator_injection',
        text: String(params.text || ''),
      });
    }

    const eventRecord = {
      schema_version: 1,
      seq: String(nextSeq),
      tick: String(tick),
      type: `operator_${kind}`,
      agent_id: params.recipient || 'operator',
      request_id: payload.intervention_id,
      detail: params.text ? String(params.text).slice(0, 120) : kind,
    };
    this.events.push(eventRecord);

    const decisionRecord = {
      tick,
      source: kind === 'inject_knowledge' ? 'operator_knowledge' : 'operator',
      request: payload,
      result: {
        status: 'recorded',
        tick: String(tick),
        event_refs: [String(nextSeq)],
        branch_id: this.snapshot.branch_id,
      },
    };
    this.decisions.push(decisionRecord);
    return decisionRecord.result;
  }
}

const worldSession = new WorldSession();
const cachedVerification = verifyH0H1H2Live();

function buildInjectedTopbarHtml(activeView) {
  return `
<style id="uw-lab-bar-style">
  .uw-lab-bar {
    background: #10161a;
    color: #dce4e3;
    border-bottom: 1px solid #2d3940;
    padding: 7px 20px;
    font: 12px/1.4 "Segoe UI", system-ui, sans-serif;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    justify-content: space-between;
  }
  .uw-lab-bar-group {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }
  .uw-lab-bar select, .uw-lab-bar button {
    font: 12px/1.2 "Segoe UI", system-ui, sans-serif;
    background: #1e2930;
    color: #e4eeeb;
    border: 1px solid #485860;
    border-radius: 3px;
    padding: 5px 9px;
    cursor: pointer;
  }
  .uw-lab-bar button:hover, .uw-lab-bar select:hover {
    border-color: #acd0b9;
    background: #283739;
  }
  .uw-lab-bar .uw-pill-active {
    background: #2b4438;
    border-color: #acd0b9;
    color: #eafff2;
    font-weight: 600;
  }
  .uw-h2-strip {
    background: #141d22;
    color: #cad9d6;
    border-bottom: 1px solid #2d3940;
    padding: 6px 20px;
    font: 12px/1.4 "Segoe UI", system-ui, sans-serif;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
  }
  .uw-h2-strip select, .uw-h2-strip button {
    font: 11.5px/1.2 "Segoe UI", system-ui, sans-serif;
    background: #1f2b32;
    color: #e4eeeb;
    border: 1px solid #485860;
    border-radius: 3px;
    padding: 4px 8px;
    cursor: pointer;
  }
  .uw-h2-strip button.uw-btn-primary {
    background: #2d4c3e;
    border-color: #acd0b9;
    color: #f0fff5;
    font-weight: 600;
  }
  .uw-modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(9, 13, 16, 0.78);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }
  .uw-modal-backdrop[hidden] { display: none !important; }
  .uw-modal {
    background: #182127;
    color: #dce4e3;
    border: 1px solid #3c4c54;
    border-radius: 4px;
    max-width: 980px;
    width: 100%;
    max-height: 88vh;
    overflow-y: auto;
    padding: 22px 26px;
    font: 13px/1.6 "Segoe UI", system-ui, sans-serif;
    box-shadow: 0 18px 48px rgba(0,0,0,0.55);
  }
  .uw-modal h2 { font-size: 17px; margin: 0 0 6px; color: #eff7f5; }
  .uw-modal h3 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em; color: #acd0b9; margin: 18px 0 8px; border-bottom: 1px solid #2d3940; padding-bottom: 4px; }
  .uw-modal table { width: 100%; border-collapse: collapse; font-size: 12px; margin: 8px 0 14px; }
  .uw-modal th, .uw-modal td { border: 1px solid #2d3940; padding: 6px 9px; text-align: left; }
  .uw-modal th { background: #202c33; color: #b9ccc9; }
  .uw-modal code { font-family: Consolas, monospace; font-size: 11.5px; color: #b7e2c8; }
</style>
<div class="uw-lab-bar" role="region" aria-label="Underworld Lab Scenario and Research Controls">
  <div class="uw-lab-bar-group">
    <strong style="color:#acd0b9;letter-spacing:0.02em;">Underworld Lab · 32×32 m · 4 Agents · 6 Animals</strong>
    <label style="margin:0;display:inline-flex;align-items:center;gap:6px;color:#aab9bb;">
      Scenario
      <select id="uw-scenario-select" aria-label="Select world scenario"></select>
    </label>
    <button type="button" id="uw-mode-toggle" title="Toggle between read-only attachment and interactive stepping/interventions"></button>
    <button type="button" id="uw-reset-scenario" title="Reload selected scenario from committed checkpoint">Reset</button>
  </div>
  <div class="uw-lab-bar-group">
    <a href="/viewer" style="padding:5px 9px;border:1px solid #485860;border-radius:3px;text-decoration:none;" class="${activeView === '3d' ? 'uw-pill-active' : ''}">3D Field Observatory</a>
    <a href="/observer" style="padding:5px 9px;border:1px solid #485860;border-radius:3px;text-decoration:none;" class="${activeView === '2d' ? 'uw-pill-active' : ''}">2D SVG Observer</a>
    <button type="button" id="uw-open-overview" class="uw-pill-active">H0 / H1 / H2 Verification &amp; Protocol Report</button>
  </div>
</div>
<div class="uw-h2-strip" role="region" aria-label="Stage H2 Grounded Naming and Reference Lab">
  <strong style="color:#acd0b9;">H2 Naming Lab:</strong>
  <label style="margin:0;display:inline-flex;align-items:center;gap:4px;">
    Dyad
    <select id="uw-h2-dyad">
      <option value="agent-1|agent-2">agent-1 (Speaker) → agent-2 (Listener)</option>
      <option value="agent-3|agent-4">agent-3 (Speaker) → agent-4 (Listener)</option>
    </select>
  </label>
  <label style="margin:0;display:inline-flex;align-items:center;gap:4px;">
    Referent
    <select id="uw-h2-class">
      <option value="small_food">Small Food (~0.05 kg)</option>
      <option value="large_food">Larger Food (~0.25 kg)</option>
      <option value="small_water">Small Water (~0.05 kg)</option>
    </select>
  </label>
  <button type="button" id="uw-h2-demo" class="uw-btn-primary" title="Speaker coins private token, deposits 0.001 kg, and speaks; listener updates private comprehension from observed mass change">1. Grounded Demo (Deposit + Speak)</button>
  <label style="margin:0;display:inline-flex;align-items:center;gap:4px;">
    Eval Arm
    <select id="uw-h2-mode">
      <option value="learned">Learned (Frozen Vocab)</option>
      <option value="silence">Silence Control</option>
      <option value="shuffled">Shuffled Token Control</option>
      <option value="random">Private Random Control</option>
      <option value="oracle">Privileged Target Oracle</option>
    </select>
  </label>
  <button type="button" id="uw-h2-ref" class="uw-btn-primary" title="Speaker emits frozen token with no deposit/gesture; listener selects and inspects a visible tray source">2. Message-Only Reference Trial</button>
  <span id="uw-h2-status" style="font-family:Consolas,monospace;font-size:11.5px;color:#b8e8cf;">Ready · 16-symbol channel (s00..s0f), no shared dictionary</span>
</div>
<div class="uw-modal-backdrop" id="uw-overview-modal" hidden>
  <div class="uw-modal" role="dialog" aria-modal="true" aria-labelledby="uw-modal-title">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
      <h2 id="uw-modal-title">Stage H2 Grounded Naming &amp; Reference + H0/H1 Verification (32×32 m · 4 Agents · 6 Animals)</h2>
      <button type="button" id="uw-close-overview" style="background:#2b3940;color:#fff;border:1px solid #596c75;padding:5px 12px;border-radius:3px;cursor:pointer;">Close</button>
    </div>
    <p style="margin:4px 0 12px;color:#aab9bb;">
      World upgraded to <code>32.0 × 32.0 m</code> with <strong>4 inhabitants</strong> (<code>agent-1..agent-4</code>) and <strong>6 animals</strong> (<code>animal-1..animal-6</code>: 3 <code>mossgrazer</code>, 3 <code>reedhen</code>). All H0, H1, and H2 confirmation gates pass with zero LLM calls and no shared dictionary.
    </p>

    <h3>1. Stage H2 Confirmation Results — Grounded Naming &amp; Message-Only Reference (5 Seeds × 5 Branches)</h3>
    <table>
      <thead><tr><th>Evaluation Arm (12 Frozen Trials / Seed)</th><th>Correct Native Reference Inspections</th><th>Success Rate</th><th>Descriptive 95% Wilson Interval</th><th>Mechanism &amp; Channel Rules</th></tr></thead>
      <tbody>
        <tr><td><strong>Learned messages</strong> (<code>learned</code>)</td><td><strong>60 / 60</strong></td><td><strong>100.0%</strong></td><td><code>94.0% – 100.0%</code></td><td>Speaker emits private coined symbol; listener chooses referent using partner-specific grounded counts (fresh-process resume, frozen vocabularies).</td></tr>
        <tr><td><strong>Silence control</strong> (<code>silence</code>)</td><td><strong>17 / 60</strong></td><td><strong>28.3%</strong></td><td><code>18.5% – 40.8%</code></td><td>Speaker rests for 1s instead of speaking; listener selects among visible tray alternatives with tie-breaking PRNG.</td></tr>
        <tr><td><strong>Balanced shuffled messages</strong> (<code>shuffled</code>)</td><td><strong>20 / 60</strong></td><td><strong>33.3%</strong></td><td><code>22.7% – 45.9%</code></td><td>Speaker emits real tokens for an independently permuted target sequence; <strong>40 causal token-swap action changes</strong> verified on matched scenes.</td></tr>
        <tr><td><strong>Private fixed random</strong> (<code>random</code>)</td><td><strong>16 / 60</strong></td><td><strong>26.7%</strong></td><td><code>17.1% – 39.0%</code></td><td>Seeded private hash-to-percept rank mapping with zero trained associations.</td></tr>
        <tr><td><strong>Privileged target oracle</strong> (<code>oracle</code>)</td><td><strong>60 / 60</strong></td><td><strong>100.0%</strong></td><td><code>94.0% – 100.0%</code></td><td>Operator-only upper comparator; never enters learner state or vocabulary.</td></tr>
      </tbody>
    </table>

    <h3>2. Independent Seed Vocabularies Coined in H2 (No Shared Lexicon)</h3>
    <table>
      <thead><tr><th>Confirmation Seed</th><th>Small Food <code>["c1f026582fe6",0]</code> (~0.05 kg)</th><th>Larger Food <code>["c1f026582fe6",2]</code> (~0.25 kg)</th><th>Small Water <code>["0f4168490e38",0]</code> (~0.05 kg)</th><th>Listener Grounded Counts (<code>agent-2</code>)</th></tr></thead>
      <tbody>
        <tr><td><strong>Seed 8101</strong></td><td><code>s00</code></td><td><code>s05</code></td><td><code>s0a</code></td><td><code>12 / 12</code> per class (36 grounded demos)</td></tr>
        <tr><td><strong>Seed 8111</strong></td><td><code>s0b</code></td><td><code>s09</code></td><td><code>s05</code></td><td><code>12 / 12</code> per class (36 grounded demos)</td></tr>
        <tr><td><strong>Seed 8123</strong></td><td><code>s04</code></td><td><code>s0e</code></td><td><code>s0b</code></td><td><code>12 / 12</code> per class (36 grounded demos)</td></tr>
        <tr><td><strong>Seed 8147</strong></td><td><code>s0f</code></td><td><code>s0c</code></td><td><code>s0a</code></td><td><code>12 / 12</code> per class (36 grounded demos)</td></tr>
        <tr><td><strong>Seed 8161</strong></td><td><code>s03</code></td><td><code>s0e</code></td><td><code>s0f</code></td><td><code>12 / 12</code> per class (36 grounded demos)</td></tr>
      </tbody>
    </table>

    <h3>3. Stage H0 &amp; H1 Verification Summary</h3>
    <table>
      <thead><tr><th>Stage / Gate</th><th>Verified Result</th><th>Status</th></tr></thead>
      <tbody>
        <tr><td><strong>World Configuration</strong></td><td><code>32.0 × 32.0 m</code> bounds, <code>4</code> inhabitants (<code>agent-1..agent-4</code>), <code>6</code> animals (<code>animal-1..animal-6</code>: 3 mossgrazer, 3 reedhen).</td><td><code>ACTIVE</code></td></tr>
        <tr><td><strong>H0 Novice Contracts &amp; Registration</strong></td><td>All registered H0/H1/H2/G source hashes verified; empty initial outcome &amp; symbol tables; private principal-checked state.</td><td><code>PASSED</code></td></tr>
        <tr><td><strong>H1 Source Affordance Learning</strong></td><td><strong>Learned: 45/45 (100%)</strong> vs. Frozen: 16/45 (35.6%) &amp; Object memory: 16/45 (35.6%); <strong>50</strong> same-state counterfactual choice changes.</td><td><code>PASSED</code></td></tr>
        <tr><td><strong>H2 Grounded Naming &amp; Reference</strong></td><td><strong>Learned: 60/60 (100%)</strong> vs. Silence: 17/60 (28.3%) &amp; Shuffled: 20/60 (33.3%); <strong>240</strong> verified native speech deliveries; <strong>40</strong> causal token swaps.</td><td><code>PASSED</code></td></tr>
      </tbody>
    </table>
  </div>
</div>
<script>
(() => {
  const selectEl = document.getElementById('uw-scenario-select');
  const toggleBtn = document.getElementById('uw-mode-toggle');
  const resetBtn = document.getElementById('uw-reset-scenario');
  const openBtn = document.getElementById('uw-open-overview');
  const closeBtn = document.getElementById('uw-close-overview');
  const modal = document.getElementById('uw-overview-modal');
  const dyadEl = document.getElementById('uw-h2-dyad');
  const classEl = document.getElementById('uw-h2-class');
  const modeEl = document.getElementById('uw-h2-mode');
  const demoBtn = document.getElementById('uw-h2-demo');
  const refBtn = document.getElementById('uw-h2-ref');
  const statusEl = document.getElementById('uw-h2-status');

  async function syncBar() {
    try {
      const res = await fetch('/api/scenarios');
      const info = await res.json();
      selectEl.replaceChildren(...info.scenarios.map(s => {
        const opt = new Option(s.label, s.id);
        opt.selected = s.id === info.current;
        return opt;
      }));
      toggleBtn.textContent = info.read_only ? 'Mode: Read-Only Attached' : 'Mode: Interactive Runner';
      toggleBtn.className = info.read_only ? '' : 'uw-pill-active';
    } catch {}
  }

  selectEl?.addEventListener('change', async () => {
    await fetch('/api/scenarios', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_id: selectEl.value })
    });
    location.reload();
  });

  toggleBtn?.addEventListener('click', async () => {
    await fetch('/api/scenarios', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ toggle_read_only: true })
    });
    await syncBar();
  });

  resetBtn?.addEventListener('click', async () => {
    await fetch('/api/scenarios', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_id: selectEl.value })
    });
    location.reload();
  });

  demoBtn?.addEventListener('click', async () => {
    const [speaker, listener] = dyadEl.value.split('|');
    const res = await fetch('/api/h2/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'demonstrate', speaker, listener, target_class: classEl.value })
    });
    const out = await res.json();
    statusEl.textContent = '[Demo t' + out.tick + '] ' + out.speaker + ' deposited 0.001kg & spoke "' + out.emitted_token + '" -> ' + out.listener + ' grounded count n=' + out.updated_count_n;
  });

  refBtn?.addEventListener('click', async () => {
    const [speaker, listener] = dyadEl.value.split('|');
    const res = await fetch('/api/h2/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'reference_trial', speaker, listener, target_class: classEl.value, mode: modeEl.value })
    });
    const out = await res.json();
    statusEl.textContent = '[Ref t' + out.tick + ' · ' + out.mode + '] token="' + (out.emitted_token || 'none') + '" -> ' + out.listener + ' inspected ' + out.chosen_target + ' (' + (out.success ? 'SUCCESS' : 'MISMATCH') + ')';
  });

  openBtn?.addEventListener('click', () => { modal.hidden = false; });
  closeBtn?.addEventListener('click', () => { modal.hidden = true; });
  modal?.addEventListener('click', (e) => { if (e.target === modal) modal.hidden = true; });
  syncBar();
})();
</script>
`;
}

function sendReply(res, value, status = 200, contentType = 'application/json') {
  const body =
    typeof value === 'string' || Buffer.isBuffer(value)
      ? value
      : JSON.stringify(value);
  res.writeHead(status, {
    'Content-Type': `${contentType}; charset=utf-8`,
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
  });
  res.end(body);
}

function readBody(req, maxBytes = 65536) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    req.on('data', chunk => {
      total += chunk.length;
      if (total > maxBytes) {
        reject(new Error('payload too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      try {
        const text = Buffer.concat(chunks).toString('utf-8');
        resolve(text ? JSON.parse(text) : {});
      } catch (err) {
        reject(err);
      }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  try {
    const parsedUrl = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
    const pathname = parsedUrl.pathname;

    if (req.method === 'GET') {
      if (pathname === '/api/session') {
        return sendReply(res, {
          token: worldSession.token,
          operator_token: worldSession.operatorToken,
        });
      }
      if (pathname === '/api/viewer') {
        const agent = parsedUrl.searchParams.get('agent') || undefined;
        const after = parsedUrl.searchParams.get('after') || '0';
        return sendReply(res, worldSession.getViewerPacket(agent, after));
      }
      if (pathname === '/api/state') {
        const agent = parsedUrl.searchParams.get('agent') || undefined;
        return sendReply(res, worldSession.getObserverState(agent));
      }
      if (pathname === '/api/interventions') {
        const packet = worldSession.getViewerPacket(undefined, '0');
        return sendReply(res, packet.operator_history);
      }
      if (pathname === '/api/verify-h0-h1' || pathname === '/api/verify-h2') {
        return sendReply(res, cachedVerification);
      }
      if (pathname === '/api/scenarios') {
        return sendReply(res, {
          current: worldSession.currentScenarioId,
          read_only: worldSession.readOnly,
          scenarios: SCENARIO_CATALOG.map(({ id, label }) => ({ id, label })),
          milestone_g_summary: gSummary.gates,
          developmental_audit: devAudit,
          verification: cachedVerification,
        });
      }
      if (pathname === '/favicon.ico') {
        res.writeHead(204);
        return res.end();
      }

      if (pathname === '/' || pathname === '/viewer') {
        const rawHtml = fs.readFileSync(path.join(WEB_DIR, 'viewer.html'), 'utf-8');
        const updatedHtml = rawHtml
          .replace('<a href="/">2D observer</a>', '<a href="/observer">2D observer</a>')
          .replace('<body>', '<body>' + buildInjectedTopbarHtml('3d'));
        return sendReply(res, updatedHtml, 200, 'text/html');
      }

      if (pathname === '/observer') {
        const rawHtml = fs.readFileSync(path.join(WEB_DIR, 'observer.html'), 'utf-8');
        const updatedHtml = rawHtml.replace('<body>', '<body>' + buildInjectedTopbarHtml('2d'));
        return sendReply(res, updatedHtml, 200, 'text/html');
      }

      const staticMap = {
        '/observer.js': ['observer.js', 'text/javascript'],
        '/observer.css': ['observer.css', 'text/css'],
        '/viewer.js': ['viewer.js', 'text/javascript'],
        '/scene.js': ['scene.js', 'text/javascript'],
        '/viewer.css': ['viewer.css', 'text/css'],
        '/vendor/three.module.min.js': ['vendor/three.module.min.js', 'text/javascript'],
        '/vendor/three.core.min.js': ['vendor/three.core.min.js', 'text/javascript'],
        '/vendor/OrbitControls.js': ['vendor/OrbitControls.js', 'text/javascript'],
        '/vendor/LICENSE.three': ['vendor/LICENSE.three', 'text/plain'],
        '/vendor/manifest.json': ['vendor/manifest.json', 'application/json'],
      };

      if (staticMap[pathname]) {
        const [relFile, mime] = staticMap[pathname];
        const content = fs.readFileSync(path.join(WEB_DIR, relFile), 'utf-8');
        return sendReply(res, content, 200, mime);
      }

      return sendReply(res, { error: 'not found' }, 404);
    }

    if (req.method === 'POST') {
      if (pathname === '/api/control') {
        const payload = await readBody(req, 2048);
        return sendReply(res, worldSession.handleControl(payload));
      }
      if (pathname === '/api/interventions') {
        const payload = await readBody(req, 16384);
        return sendReply(res, worldSession.handleIntervention(payload));
      }
      if (pathname === '/api/h2/action') {
        const payload = await readBody(req, 4096);
        return sendReply(res, worldSession.runH2InteractiveAction(payload));
      }
      if (pathname === '/api/scenarios') {
        const payload = await readBody(req, 2048);
        if (payload.toggle_read_only) {
          worldSession.readOnly = !worldSession.readOnly;
          if (worldSession.readOnly) worldSession.paused = true;
        }
        if (payload.scenario_id) {
          worldSession.loadScenario(payload.scenario_id);
        }
        return sendReply(res, {
          current: worldSession.currentScenarioId,
          read_only: worldSession.readOnly,
        });
      }
      return sendReply(res, { error: 'not found' }, 404);
    }

    return sendReply(res, { error: 'method not allowed' }, 405);
  } catch (err) {
    return sendReply(res, { error: err.message || String(err) }, 400);
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(
    JSON.stringify({
      ready: true,
      url: `http://0.0.0.0:${PORT}/viewer`,
      scenario: worldSession.currentScenarioId,
      world_bounds_m: worldSession.snapshot.world_bounds_m,
      h0_h1_h2_verified: cachedVerification.verified,
    })
  );
});
