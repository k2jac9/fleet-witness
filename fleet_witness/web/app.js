/* Fleet Witness: dependency-free replay validation and read-only viewer. */
(function () {
  'use strict';
  const MAX_BYTES = 2 * 1024 * 1024;
  const MAX_DEPTH = 32, MAX_VALUES = 50000;
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  function ensure(ok, message) { if (!ok) throw new Error(`Replay: ${message}`); }
  function strings(value, keys, label) {
    ensure(object(value), `${label} must be an object`);
    for (const key of keys) ensure(typeof value[key] === 'string' && value[key].length > 0, `${label}.${key} must be a nonempty string`);
  }
  function boundStructure(data) {
    // Iterative traversal also covers unknown fields before any JSON pretty printing.
    const pending = [[data, 0]], seen = new WeakSet();
    let values = 0;
    while (pending.length) {
      const [value, depth] = pending.pop();
      ensure(depth <= MAX_DEPTH, `nesting depth exceeds ${MAX_DEPTH}`);
      ensure(++values <= MAX_VALUES, `complexity exceeds ${MAX_VALUES} values`);
      if (value !== null && typeof value === 'object') {
        ensure(!seen.has(value), 'repeated or circular object reference'); seen.add(value);
        const children = Object.values(value);
        ensure(values + pending.length + children.length <= MAX_VALUES, `complexity exceeds ${MAX_VALUES} values`);
        for (const child of children) pending.push([child, depth + 1]);
      }
    }
  }
  function validateReplay(data) {
    boundStructure(data);
    ensure(object(data), 'root must be an object');
    ensure(data.schema_version === '1.0', 'unsupported schema version; expected 1.0');
    ensure(data.project === 'Fleet Witness' && data.mode === 'scripted-demo', 'expected Fleet Witness scripted-demo data');
    ensure(Number.isSafeInteger(data.seed), 'seed must be an integer');
    strings(data, ['generated_at'], 'metadata');
    ensure(Array.isArray(data.episodes) && data.episodes.length > 0 && data.episodes.length <= 2000, 'episodes must contain 1–2000 entries');
    const ids = new Set(), pairs = new Set();
    const counts = { episodes: data.episodes.length, approved_recommendations: 0, invalid_recommendations: 0, execution_attempts: 0, effects: 0, denied_attempts: 0 };
    for (const e of data.episodes) {
      strings(e, ['id', 'pair_id', 'scenario', 'title', 'worker_policy', 'reviewer_policy', 'artifact_digest'], 'episode');
      ensure(!ids.has(e.id), 'duplicate episode id'); ids.add(e.id);
      ensure(['raw', 'scope_explicit'].includes(e.presentation), 'episode presentation must be raw or scope_explicit');
      const pairKey = JSON.stringify([e.pair_id, e.presentation]);
      ensure(!pairs.has(pairKey), 'duplicate pair presentation'); pairs.add(pairKey);
      ensure(object(e.supervisor_input) && object(e.supervisor_input.facts), 'supervisor_input.facts must be an object');
      strings(e.supervisor_input, ['backend', 'instruction'], 'supervisor_input');
      strings(e.supervisor_input.facts, ['run_id', 'artifact_digest', 'reviewer_verdict', 'reviewer_statement'], 'supervisor_input.facts');
      strings(e.decision, ['id', 'recommendation', 'reason'], 'decision');
      ensure(['approve', 'deny'].includes(e.decision.recommendation), 'invalid decision recommendation');
      strings(e.evaluation, ['expected_recommendation', 'reason'], 'evaluation');
      ensure(['approve', 'deny'].includes(e.evaluation.expected_recommendation), 'invalid expected recommendation');
      ensure(typeof e.evaluation.decision_valid_at_snapshot === 'boolean', 'evaluation correctness must be boolean');
      ensure(Array.isArray(e.attempts) && e.attempts.length <= 500, 'attempts must be an array of at most 500 entries');
      for (const a of e.attempts) {
        strings(a, ['id', 'reason'], 'attempt');
        ensure(typeof a.execution_authorized_at_attempt === 'boolean' && typeof a.effect_occurred === 'boolean', 'attempt outcomes must be boolean');
        ensure(a.policy_version === null || Number.isSafeInteger(a.policy_version), 'attempt policy_version must be an integer or null');
        counts.execution_attempts++; counts.effects += Number(a.effect_occurred); counts.denied_attempts += Number(!a.execution_authorized_at_attempt);
      }
      ensure(Array.isArray(e.events) && e.events.length <= 500, 'events must be an array of at most 500 entries');
      let seq = -1;
      for (const event of e.events) {
        strings(event, ['kind', 'actor', 'message'], 'event');
        ensure(Number.isSafeInteger(event.seq) && event.seq > seq, 'event sequence must be strictly increasing'); seq = event.seq;
        ensure(event.details === undefined || object(event.details), 'event details must be an object');
      }
      ensure(Array.isArray(e.receipts) && e.receipts.length <= 500, 'receipts must be an array of at most 500 entries');
      for (const receipt of e.receipts) strings(receipt, ['issuer', 'claim', 'scope', 'artifact_digest', 'run_id', 'signature'], 'receipt');
      counts.approved_recommendations += Number(e.decision.recommendation === 'approve');
      counts.invalid_recommendations += Number(!e.evaluation.decision_valid_at_snapshot);
    }
    ensure(object(data.summary), 'summary must be an object');
    for (const [key, value] of Object.entries(counts)) ensure(data.summary[key] === value, `summary.${key} disagrees with episodes`);
    return data;
  }
  function parseReplay(text) {
    ensure(typeof text === 'string', 'input must be JSON text');
    ensure(new TextEncoder().encode(text).byteLength <= MAX_BYTES, 'file exceeds the 2 MiB import limit');
    let data;
    try { data = JSON.parse(text); } catch { throw new Error('Replay: invalid JSON; choose an exported replay.json file'); }
    return validateReplay(data);
  }
  function pairedEpisode(replay, pairId, presentation) {
    return replay.episodes.find(e => e.pair_id === pairId && e.presentation === presentation);
  }
  function selectEpisodes(replay, { presentation = 'raw', query = '', validity = 'all', scenario = 'all' } = {}) {
    const needle = query.trim().toLowerCase();
    return replay.episodes.filter(e => e.presentation === presentation &&
      (scenario === 'all' || e.scenario === scenario) &&
      (validity === 'all' || e.evaluation.decision_valid_at_snapshot === (validity === 'valid')) &&
      (!needle || JSON.stringify([e.title, e.id, e.scenario, e.worker_policy, e.reviewer_policy, e.receipts]).toLowerCase().includes(needle)));
  }
  const api = { MAX_BYTES, parseReplay, validateReplay, selectEpisodes, pairedEpisode };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof document === 'undefined') return;

  const $ = id => document.getElementById(id);
  const state = { replay: null, presentation: 'raw', selected: null, eventIndex: 0 };
  const node = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = String(text);
    return el;
  };
  const readable = value => String(value).replaceAll('_', ' ');
  function badge(text, tone = '') { return node('span', `badge ${tone}`, text); }
  function field(container, label, value, mono = false) {
    const item = node('div', 'field');
    item.append(node('dt', '', label), node('dd', mono ? 'mono' : '', value)); container.append(item);
  }
  function showError(message) { $('load-error').textContent = message; $('load-error').hidden = !message; }
  function activeEpisode() { return state.replay && pairedEpisode(state.replay, state.selected, state.presentation); }
  function installReplay(replay, source) {
    const previous = { ...state };
    const controls = {
      source: $('source-name').textContent, meta: $('run-meta').textContent,
      query: $('search').value, validity: $('validity-filter').value, scenario: $('scenario-filter').value,
    };
    try { populateReplay(replay, source); }
    catch (error) {
      // A failed candidate must not replace a replay that the user can still inspect.
      if (previous.replay) {
        populateReplay(previous.replay, controls.source);
        Object.assign(state, previous);
        $('search').value = controls.query; $('validity-filter').value = controls.validity;
        $('scenario-filter').value = controls.scenario;
        renderList();
      } else {
        Object.assign(state, previous);
        $('source-name').textContent = controls.source; $('run-meta').textContent = controls.meta;
        $('workspace').hidden = true; $('metrics').hidden = true;
        $('scenario-list').replaceChildren(); $('metrics').replaceChildren();
      }
      throw error;
    }
  }
  function populateReplay(replay, source) {
    state.replay = replay; state.selected = null; state.eventIndex = 0;
    if (!replay.episodes.some(e => e.presentation === state.presentation)) state.presentation = replay.episodes[0].presentation;
    $('search').value = ''; $('validity-filter').value = 'all';
    $('scenario-filter').replaceChildren(new Option('All scenarios', 'all'));
    for (const scenario of new Set(replay.episodes.map(e => e.scenario))) $('scenario-filter').add(new Option(readable(scenario), scenario));
    $('source-name').textContent = source;
    $('run-meta').textContent = `Seed ${replay.seed} · ${replay.episodes.length} episodes · ${new Set(replay.episodes.map(e => e.pair_id)).size} evidence pairs`;
    const stats = [ ['Evidence pairs', new Set(replay.episodes.map(e => e.pair_id)).size, 'Paired raw / scope explicit trials'], ['Invalid recommendations', replay.summary.invalid_recommendations, 'Scored at the decision snapshot'], ['Denied attempts', replay.summary.denied_attempts, 'Authorization denied at execution'], ['Committed effects', replay.summary.effects, 'Local database release records'] ];
    $('metrics').replaceChildren(...stats.map(([label, value, description]) => {
      const box = node('div', 'metric'); box.append(node('span', 'eyebrow', label), node('strong', '', value), node('span', 'muted', description)); return box;
    }));
    $('workspace').hidden = false; $('metrics').hidden = false; $('loading').hidden = true;
    showError(''); renderList();
  }
  function renderList() {
    if (!state.replay) return;
    const focusedPair = document.activeElement?.closest('.scenario-item')?.dataset.pairId;
    const episodes = selectEpisodes(state.replay, { presentation: state.presentation, query: $('search').value, validity: $('validity-filter').value, scenario: $('scenario-filter').value });
    if (!episodes.some(e => e.pair_id === state.selected)) { state.selected = episodes[0]?.pair_id ?? null; state.eventIndex = 0; }
    $('scenario-count').textContent = `${episodes.length} of ${state.replay.episodes.filter(e => e.presentation === state.presentation).length} trials`;
    $('scenario-list').replaceChildren(...episodes.map((e, index) => {
      const button = node('button', `scenario-item${state.selected === e.pair_id ? ' selected' : ''}`);
      button.dataset.pairId = e.pair_id;
      button.type = 'button'; button.setAttribute('aria-pressed', String(state.selected === e.pair_id));
      const title = node('span', 'scenario-name', e.title);
      const meta = node('span', 'scenario-meta', `${readable(e.worker_policy)} worker · ${readable(e.reviewer_policy)} reviewer`);
      const foot = node('span', 'scenario-foot');
      foot.append(node('span', 'scenario-number', String(index + 1).padStart(2, '0')), badge(e.evaluation.decision_valid_at_snapshot ? 'Correct decision' : 'Incorrect decision', e.evaluation.decision_valid_at_snapshot ? 'good' : 'bad'));
      button.append(title, meta, foot);
      button.addEventListener('click', () => { state.selected = e.pair_id; state.eventIndex = 0; renderList(); });
      return button;
    }));
    $('no-results').hidden = episodes.length !== 0;
    $('episode-detail').hidden = !state.selected;
    for (const button of document.querySelectorAll('[data-presentation]')) {
      button.disabled = !state.replay.episodes.some(e => e.presentation === button.dataset.presentation);
      button.setAttribute('aria-pressed', String(button.dataset.presentation === state.presentation));
    }
    renderEpisode();
    if (focusedPair) Array.from($('scenario-list').children).find(button => button.dataset.pairId === focusedPair)?.focus();
  }
  function renderEpisode() {
    const e = activeEpisode(); if (!e) return;
    $('episode-title').textContent = e.title;
    $('episode-scenario').textContent = readable(e.scenario);
    $('episode-id').textContent = e.id;
    $('worker-role').textContent = `${readable(e.worker_policy)} worker`;
    $('reviewer-role').textContent = `${readable(e.reviewer_policy)} reviewer`;
    $('decision-status').textContent = e.evaluation.decision_valid_at_snapshot ? 'Correct recommendation' : 'Incorrect recommendation';
    $('decision-status').className = `outcome-value ${e.evaluation.decision_valid_at_snapshot ? 'good-text' : 'bad-text'}`;
    $('recommendation').textContent = `${readable(e.decision.recommendation)} · expected ${e.evaluation.expected_recommendation}`;
    $('decision-reason').textContent = e.evaluation.reason;
    $('supervisor-reason').textContent = e.decision.reason;
    const anyEffect = e.attempts.some(a => a.effect_occurred);
    $('effect-status').textContent = anyEffect ? 'Release committed' : e.attempts.length ? 'No release committed' : 'No execution attempted';
    $('effect-status').className = `outcome-value ${anyEffect ? 'teal-text' : ''}`;
    $('effect-description').textContent = anyEffect ? 'Effect is a local SQLite release record.' : e.attempts.length ? 'Controller outcomes are shown per attempt below.' : 'The supervisor proposed denial; no effect was attempted.';
    $('attempt-list').replaceChildren(...e.attempts.map((a, index) => {
      const row = node('div', 'attempt-row');
      const heading = node('div', 'attempt-heading'); heading.append(node('strong', '', `Attempt ${index + 1}`), badge(a.execution_authorized_at_attempt ? 'Authorized' : 'Denied', a.execution_authorized_at_attempt ? 'good' : 'neutral'));
      row.append(heading, node('p', '', a.reason), node('small', 'muted', `Effect ${a.effect_occurred ? 'occurred' : 'did not occur'} · Policy ${a.policy_version === null ? 'missing' : `v${a.policy_version}`}`)); return row;
    }));
    $('reviewer-statement').textContent = e.supervisor_input.facts.reviewer_statement;
    $('artifact-digest').textContent = e.artifact_digest;
    $('supervisor-input').textContent = JSON.stringify(e.supervisor_input, null, 2);
    $('receipt-list').replaceChildren(...e.receipts.map((receipt, index) => {
      const details = node('details', 'receipt'); details.open = index === 0;
      const summary = node('summary', '', `Receipt ${index + 1} · ${receipt.claim}`);
      const fields = node('dl', 'receipt-fields');
      for (const [key, value] of Object.entries(receipt)) field(fields, readable(key), typeof value === 'string' ? value : JSON.stringify(value), ['signature', 'artifact_digest', 'run_id'].includes(key));
      details.append(summary, fields); return details;
    }));
    $('no-receipts').hidden = e.receipts.length !== 0;
    renderEvents();
  }
  function renderEvents() {
    const e = activeEpisode(); if (!e) return;
    const focusedSeq = document.activeElement?.closest('.event-step')?.dataset.seq;
    state.eventIndex = Math.max(0, Math.min(state.eventIndex, e.events.length - 1));
    const event = e.events[state.eventIndex];
    $('event-progress').textContent = event ? `${state.eventIndex + 1} / ${e.events.length}` : '0 / 0';
    $('event-prev').disabled = !event || state.eventIndex === 0;
    $('event-next').disabled = !event || state.eventIndex === e.events.length - 1;
    $('event-reset').disabled = !event || state.eventIndex === 0;
    $('event-list').replaceChildren(...e.events.map((entry, index) => {
      const button = node('button', `event-step${index === state.eventIndex ? ' current' : ''}${index < state.eventIndex ? ' visited' : ''}`);
      button.dataset.seq = String(entry.seq);
      button.type = 'button'; button.setAttribute('aria-current', index === state.eventIndex ? 'step' : 'false');
      button.append(node('span', 'event-dot', entry.seq), node('span', '', readable(entry.kind)), node('small', 'muted', entry.actor));
      button.addEventListener('click', () => { state.eventIndex = index; renderEvents(); }); return button;
    }));
    if (focusedSeq) Array.from($('event-list').children).find(button => button.dataset.seq === focusedSeq)?.focus();
    $('event-kind').textContent = event ? readable(event.kind) : 'No events in this episode';
    $('event-actor').textContent = event?.actor ?? '—';
    $('event-message').textContent = event?.message ?? 'This replay contains no events to step through.';
    $('event-details').textContent = event ? JSON.stringify(event.details ?? {}, null, 2) : '{}';
  }
  for (const id of ['search', 'validity-filter', 'scenario-filter']) $(id).addEventListener(id === 'search' ? 'input' : 'change', renderList);
  for (const button of document.querySelectorAll('[data-presentation]')) button.addEventListener('click', () => {
    state.presentation = button.dataset.presentation; state.eventIndex = 0;
    for (const toggle of document.querySelectorAll('[data-presentation]')) toggle.setAttribute('aria-pressed', String(toggle === button));
    renderList();
  });
  $('event-prev').addEventListener('click', () => { state.eventIndex--; renderEvents(); });
  $('event-next').addEventListener('click', () => { state.eventIndex++; renderEvents(); });
  $('event-reset').addEventListener('click', () => { state.eventIndex = 0; renderEvents(); });
  $('import-file').addEventListener('change', async event => {
    const file = event.target.files[0]; if (!file) return;
    try {
      ensure(file.size <= MAX_BYTES, 'file exceeds the 2 MiB import limit');
      installReplay(parseReplay(await file.text()), file.name);
    } catch (error) { showError(`${error.message}. ${state.replay ? 'The current replay is still available.' : 'Choose another replay file to continue.'}`); }
    event.target.value = '';
  });
  async function loadDefault() {
    try {
      const response = await fetch('replay.json', { cache: 'no-store' });
      if (!response.ok) throw new Error(`Could not load replay.json (HTTP ${response.status})`);
      const declaredSize = Number(response.headers.get('content-length'));
      ensure(!declaredSize || declaredSize <= MAX_BYTES, 'file exceeds the 2 MiB import limit');
      installReplay(parseReplay(await response.text()), 'replay.json');
    } catch (error) {
      $('loading').hidden = true;
      showError(`${error.message}. Serve an exported demo directory or import a replay JSON using the button above.`);
    }
  }
  loadDefault();
})();
