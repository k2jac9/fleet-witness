import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
// A missing viewer is an unimplemented boundary, not a test-loader error.
let viewer = {};
try { viewer = require('../fleet_witness/web/app.js'); } catch (error) {
  if (error.code !== 'MODULE_NOT_FOUND') throw error;
}
const temp = mkdtempSync(join(tmpdir(), 'witness-viewer-'));
let fixtureText;
try {
  execFileSync('python', ['-m', 'fleet_witness', 'demo', '--output', join(temp, 'demo'), '--seed', '42'], { cwd: new URL('..', import.meta.url) });
  fixtureText = readFileSync(join(temp, 'demo', 'replay.json'), 'utf8');
} finally { rmSync(temp, { recursive: true, force: true }); }
const fixture = JSON.parse(fixtureText);

test('imports real producer exports at both safe integer seed boundaries', () => {
  const boundaryTemp = mkdtempSync(join(tmpdir(), 'witness-seed-boundaries-'));
  try {
    for (const seed of ['-9007199254740991', '9007199254740991']) {
      const output = join(boundaryTemp, seed);
      execFileSync('python', ['-m', 'fleet_witness', 'demo', '--output', output, '--seed', seed], { cwd: new URL('..', import.meta.url) });
      const replay = viewer.parseReplay(readFileSync(join(output, 'replay.json'), 'utf8'));
      assert.equal(replay.seed, Number(seed));
      assert.equal(replay.schema_version, '1.0');
      assert.equal(replay.episodes.length, 20);
    }
  } finally { rmSync(boundaryTemp, { recursive: true, force: true }); }
});

test('imports the real replay and retains each decision and execution outcome', () => {
  assert.equal(typeof viewer.parseReplay, 'function', 'replay import is implemented');
  const replay = viewer.parseReplay(fixtureText);
  assert.equal(replay.episodes.length, 20);
  const revoked = replay.episodes.find(e => e.scenario === 'revocation');
  assert.equal(revoked.evaluation.decision_valid_at_snapshot, true);
  assert.equal(revoked.attempts[0].execution_authorized_at_attempt, false);
  assert.equal(revoked.attempts[0].effect_occurred, false);
});

test('rejects unknown schemas, empty episodes, malformed nested fields, and contradictory summary counts', () => {
  assert.equal(typeof viewer.parseReplay, 'function', 'replay import is implemented');
  for (const change of [
    x => { x.schema_version = '9.0'; },
    x => { x.episodes = []; },
    x => { x.episodes[0].attempts[0].effect_occurred = 'false'; },
    x => { x.episodes[0].events[0].message = null; },
    x => { x.episodes[0].receipts[0].scope = {}; },
    x => { x.summary.effects += 1; },
    x => { x.episodes[1].id = x.episodes[0].id; },
    x => { x.episodes[0].events[1].seq = 1; },
  ]) {
    const changed = structuredClone(fixture); change(changed);
    assert.throws(() => viewer.parseReplay(JSON.stringify(changed)), /Replay|schema|episodes|attempt|event|receipt|summary|duplicate|sequence/i);
  }
  assert.throws(() => viewer.parseReplay('{'), /JSON/i);
  assert.throws(() => viewer.parseReplay(' '.repeat(2 * 1024 * 1024 + 1)), /2 MiB/i);
});

test('pairs by pair_id, searches role and receipt data, and filters correctness in the chosen presentation', () => {
  assert.equal(typeof viewer.selectEpisodes, 'function', 'pair selection is implemented');
  const raw = viewer.selectEpisodes(fixture, { presentation: 'raw' });
  assert.equal(raw.length, 10);
  assert.equal(new Set(raw.map(x => x.pair_id)).size, 10);
  const invalid = viewer.selectEpisodes(fixture, { presentation: 'raw', validity: 'invalid' });
  assert.equal(invalid.length, 6);
  assert.ok(invalid.every(e => !e.evaluation.decision_valid_at_snapshot));
  assert.equal(viewer.selectEpisodes(fixture, { presentation: 'scope_explicit', validity: 'invalid' }).length, 1);
  assert.ok(viewer.selectEpisodes(fixture, { presentation: 'raw', query: 'build-issuer' }).length > 0);
  assert.equal(viewer.selectEpisodes(fixture, { presentation: 'raw', scenario: 'revocation' }).length, 1);
  const pair = viewer.pairedEpisode(fixture, raw[3].pair_id, 'scope_explicit');
  assert.equal(pair.pair_id, raw[3].pair_id);
  assert.deepEqual(pair.receipts, raw[3].receipts);
});

test('rejects deeply nested and excessively complex replay extras before rendering', () => {
  // Removing the structural bound must admit these otherwise schema-valid exports.
  const nested = '{"child":'.repeat(10000) + 'null' + '}'.repeat(10000);
  const deepText = fixtureText.replace('"supervisor_input": {', `"supervisor_input": {"extra":${nested},`);
  assert.notEqual(deepText, fixtureText, 'deep value is inserted into a rendered object');
  assert.ok(Buffer.byteLength(deepText) < viewer.MAX_BYTES);
  assert.throws(() => viewer.parseReplay(deepText), /nesting|depth/i);
  const complex = structuredClone(fixture);
  complex.episodes[0].supervisor_input.extra = Array(60000).fill(null);
  const complexText = JSON.stringify(complex);
  assert.ok(Buffer.byteLength(complexText) < viewer.MAX_BYTES);
  assert.throws(() => viewer.parseReplay(complexText), /complexity|values/i);
  const ordinaryExtra = structuredClone(fixture);
  ordinaryExtra.episodes[0].supervisor_input.extra = { notes: ['additional', 'safe', 'metadata'] };
  assert.equal(viewer.parseReplay(JSON.stringify(ordinaryExtra)).episodes.length, 20);
});
