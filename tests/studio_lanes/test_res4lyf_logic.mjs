import assert from 'node:assert';
import { stagesOf, modelCalls, flatten, filterSamplers, filterNames, filterNodes, stateCounts, sourceUrl, STATE_LABEL, betaPpf, betaSchedule, countBelow, curvePath, exampleUrl } from './res4lyf_logic.js';
import { DATA } from './res4lyf_data.js';

// The README's naming rule
assert.strictEqual(stagesOf('euler'), 1);
assert.strictEqual(stagesOf('res_2m'), 1);
assert.strictEqual(stagesOf('deis_4m'), 1);
assert.strictEqual(stagesOf('res_3s'), 3);
assert.strictEqual(stagesOf('res_16s'), 16);
assert.strictEqual(stagesOf('res_3s_non-monotonic'), 3);
assert.strictEqual(stagesOf('gauss-legendre_4s_alternating_a'), 4);
assert.strictEqual(stagesOf('etdrk3_a_3s'), 3);
assert.strictEqual(stagesOf('pec433_2h3s'), 3);
assert.strictEqual(stagesOf('lawson45-gen-mod_4h4s'), 4);
assert.strictEqual(stagesOf('nothing'), null);
assert.strictEqual(modelCalls(20, 3), 60);

// Every sampler the page lists has a count, so the cost lab can never show NaN
const all = flatten(DATA.families);
assert.strictEqual(all.length, 118);
for (const s of all) assert.ok(s.stages >= 1, s.name);
assert.strictEqual(new Set(all.map((s) => s.name)).size, all.length);

// Filters
assert.strictEqual(filterSamplers(all, 'all', '').length, all.length);
assert.ok(filterSamplers(all, 'multistep', '').every((s) => s.family === 'multistep'));
assert.deepStrictEqual(filterSamplers(all, 'all', ' RES_16S ').map((s) => s.name), ['res_16s']);
assert.strictEqual(filterSamplers(all, 'multistep', 'radau').length, 0);
assert.deepStrictEqual(filterNames(['ClownGuide_Beta', 'SharkSampler'], 'shark'), ['SharkSampler']);

// Node directory
const rows = [{ n: 'ClownGuide_Beta', d: 'pulls toward a guide', g: 'Guides', s: 'rendered' }, { n: 'Sigmas Math1', d: 'runs a formula', g: 'Formulas', s: 'error' }];
assert.deepStrictEqual(filterNodes(rows, 'all', 'all', '').length, 2);
assert.deepStrictEqual(filterNodes(rows, 'Formulas', 'all', '').map((r) => r.n), ['Sigmas Math1']);
assert.deepStrictEqual(filterNodes(rows, 'all', 'rendered', '').map((r) => r.n), ['ClownGuide_Beta']);
assert.deepStrictEqual(filterNodes(rows, 'all', 'all', 'FORMULA').map((r) => r.n), ['Sigmas Math1']);
assert.deepStrictEqual(stateCounts(rows), { rendered: 1, error: 1 });
assert.ok(sourceUrl('abc', 'beta/x.py', '12').endsWith('/blob/abc/beta/x.py#L12'));
for (const k of ['rendered', 'ran', 'error', 'rejected', 'needs', 'skipped', 'timeout', 'untested']) assert.ok(STATE_LABEL[k], k);

// Quantiles against scipy.stats.beta.ppf
const near = (a, b) => assert.ok(Math.abs(a - b) < 2e-3, `${a} vs ${b}`);
[[0.1, 0.015648], [0.25, 0.096177], [0.5, 0.361084], [0.75, 0.719286], [0.9, 0.918835]].forEach(([p, x]) => near(betaPpf(p, 0.5, 0.7), x));
[[0.1, 0.039584], [0.5, 0.5], [0.9, 0.960416]].forEach(([p, x]) => near(betaPpf(p, 0.6, 0.6), x));
assert.strictEqual(betaPpf(0, 0.5, 0.7), 0);
assert.strictEqual(betaPpf(1, 0.5, 0.7), 1);

// The schedule starts at the noisiest end and only falls; beta57 keeps more steps low than the default
const s57 = betaSchedule(20, 0.5, 0.7), plain = betaSchedule(20, 0.6, 0.6);
assert.strictEqual(s57.length, 20);
assert.strictEqual(s57[0], 1);
for (let i = 1; i < s57.length; i++) assert.ok(s57[i] < s57[i - 1]);
assert.ok(countBelow(s57, 0.25) > countBelow(plain, 0.25));

// Drawing
assert.ok(!curvePath(s57, 320, 170).includes('NaN'));
assert.ok(curvePath(s57, 320, 170).startsWith('M0.0 0.0'));
assert.strictEqual(curvePath([1], 320, 170), 'M0.0 0.0');

// File names with spaces and brackets survive in a link
assert.ok(exampleUrl('flux regional redux (3 zone, overlapping)').endsWith('/example_workflows/flux%20regional%20redux%20(3%20zone%2C%20overlapping).json'));

console.log('ok');
