import assert from 'node:assert';
import { filterEntries, score, familyCounts, whereOf, curvePoints, toPath, assignSlots, togglePick, MAX_SERIES, benchRows, sortBench, groupRenders, baselineFor, runRequest, canRun } from './samplinglab_logic.js';

const E = [
  { id: 'a', name: 'DPM++ 2M', family: 'sampler', in_core: true, plain: 'second order multistep', core_ref: { sampler_name: 'dpmpp_2m' } },
  { id: 'b', name: 'Pink noise', family: 'noise', plain: 'power law spectrum' },
  { id: 'c', name: 'TeaCache', family: 'patch', live: true, plain: 'skips steps' },
  { id: 'd', name: 'Multistep helper', family: 'sampler', plain: 'dpm++ variant' },
];
assert.deepStrictEqual(filterEntries(E, { q: 'pink' }).map((x) => x.id), ['b']);
assert.deepStrictEqual(filterEntries(E, { family: 'sampler' }).map((x) => x.id), ['a', 'd']);
assert.deepStrictEqual(filterEntries(E, { where: 'live' }).map((x) => x.id), ['c']);
assert.deepStrictEqual(filterEntries(E, { where: 'pack', family: 'noise' }).map((x) => x.id), ['b']);
assert.strictEqual(filterEntries(E, { q: 'pink nothing' }).length, 0, 'every word must hit');
assert.strictEqual(filterEntries(E, { q: 'multistep' })[0].id, 'd', 'a name match beats a text match');
assert.ok(score(E[0], 'dpm') > score(E[3], 'dpm'));
assert.strictEqual(whereOf(E[0]), 'core'); assert.strictEqual(whereOf(E[2]), 'live'); assert.strictEqual(whereOf(E[1]), 'pack');
assert.deepStrictEqual(familyCounts(E), { sampler: 2, noise: 1, patch: 1 });
assert.deepStrictEqual(filterEntries(null), []);

// curves: log leaves out the final sigma of 0; linear keeps it and ends at the bottom
const sig = [10, 1, 0.1, 0];
assert.strictEqual(curvePoints(sig, { log: true }).length, 3);
const lin = curvePoints(sig, {}); assert.strictEqual(lin.length, 4); assert.strictEqual(lin[0][1], 0); assert.strictEqual(lin[3][1], 100);
assert.strictEqual(curvePoints([1]).length, 0);
assert.ok(toPath(lin).startsWith('M0.00 0.00L'));

// colour follows the series: dropping one never repaints the others
let s = assignSlots({}, ['a', 'b', 'c']); assert.deepStrictEqual(s, { a: 0, b: 1, c: 2 });
s = assignSlots(s, ['a', 'c']); assert.deepStrictEqual(s, { a: 0, c: 2 });
s = assignSlots(s, ['a', 'c', 'd']); assert.strictEqual(s.d, 1); assert.strictEqual(s.c, 2);
let p = []; for (let i = 0; i < MAX_SERIES + 3; i++) p = togglePick(p, 'k' + i); assert.strictEqual(p.length, MAX_SERIES);
assert.ok(!togglePick(['x'], 'x').includes('x'));

// bench: a stochastic sampler is never given a distance-to-exact number
const rows = benchRows({ euler: { eps: { calls: { 20: 20 }, same_answer_with_other_noise_seed: true, rmse_to_exact: { 5: 1, 10: 2, 20: 3, 40: 4 }, variance_error: { 20: 0.1 } } }, sde: { eps: { calls: { 20: 39 }, same_answer_with_other_noise_seed: false, rmse_to_exact: { 20: 1.3 }, variance_error: { 20: 0.2 } } }, bad: { eps: { error: 'boom' } } });
assert.strictEqual(rows[0].rmse, 3); assert.strictEqual(rows[1].rmse, null); assert.strictEqual(rows[1].perStep, 1.95); assert.strictEqual(rows[2].error, 'boom');
assert.strictEqual(sortBench(rows, 'calls20', -1)[0].name, 'sde'); assert.strictEqual(sortBench(rows, 'rmse', 1)[0].name, 'euler');

const g = groupRenders([{ set: 's', status: 'rendered', id: 1 }, { set: 's', status: 'failed', id: 2 }, { set: 's', status: 'rendered', id: 3, baseline: true }]);
assert.strictEqual(g.s.length, 2); assert.strictEqual(baselineFor(g.s).id, 3); assert.strictEqual(baselineFor([]), null);
assert.deepStrictEqual(runRequest({ core_ref: { scheduler: 'beta' } }, 'sdxl'), { model: 'sdxl', scheduler: 'beta', sampler: 'dpmpp_2m' });
assert.deepStrictEqual(runRequest({ core_ref: { node: 'x' }, run_patch: 'APG' }, 'sd15'), { model: 'sd15', patch: 'APG' });
assert.ok(canRun({ in_core: true, core_ref: { sampler_name: 'euler' } })); assert.ok(!canRun({ in_core: false, core_ref: { sampler_name: 'euler' } })); assert.ok(!canRun({ in_core: true, core_ref: {} }));

// ---- the look ----
const L = await import('./samplinglab_logic.js');
assert.deepStrictEqual(L.parseRoute('sampling'), { view: 'methods', id: null, rest: [] });
assert.deepStrictEqual(L.parseRoute('sampling/curves'), { view: 'curves', id: null, rest: [] });
assert.deepStrictEqual(L.parseRoute('sampling/renders/flow/a/b'), { view: 'renders', id: null, rest: ['flow', 'a', 'b'] });
assert.strictEqual(L.parseRoute('sampling/core-euler').id, 'core-euler');
// a virtual list draws only what is near the view, and never runs off either end
assert.deepStrictEqual(L.windowRange(0, 900, 92, 720, 8), [0, 18]);
assert.deepStrictEqual(L.windowRange(-500, 900, 92, 720, 0), [0, 5]);
assert.deepStrictEqual(L.windowRange(92 * 719, 900, 92, 720, 2), [717, 720]);
assert.deepStrictEqual(L.windowRange(0, 900, 0, 720), [0, 0]);
// the treemap is exact: areas in proportion, nothing outside the box
const rects = L.squarify([174, 164, 114, 91, 86, 79, 12], 1000, 400); const area = rects.reduce((a, r) => a + r.w * r.h, 0);
assert.ok(Math.abs(area - 400000) < 1); assert.ok(Math.abs(rects[6].w * rects[6].h / 400000 - 12 / 720) < 1e-9);
for (const r of rects) assert.ok(r.x >= -1e-6 && r.y >= -1e-6 && r.x + r.w <= 1000.001 && r.y + r.h <= 400.001);
// the map holds every method at every width, with squares big enough to see
const fams = [174, 164, 114, 91, 86, 79, 12].map((n, i) => ({ k: 'f' + i, n }));
for (let W = 280; W <= 2600; W += 37) { const m = L.mapLayout(fams, W); assert.ok(m.dot >= 8, 'dot at ' + W); for (const t of m.tiles) { const rows = Math.ceil(t.n / t.cols); assert.ok(t.dotY + rows * m.dot <= t.h + 1, `${t.k} fits at ${W}`); assert.ok(t.cols * m.dot <= t.w - 20 + 1 || m.stacked, `${t.k} width at ${W}`); } }
// each method is exactly one kind of square
const K = [{ rendered: true, in_core: true }, { in_core: true }, { live: true }, {}];
assert.deepStrictEqual(K.map(L.dotKind), ['rendered', 'core', 'live', 'pack']); assert.deepStrictEqual(L.dotCounts(K), { rendered: 1, core: 1, live: 1, pack: 1 });
assert.deepStrictEqual(L.dotsOf([{ name: 'a' }, { name: 'b', in_core: true }, { name: 'c', rendered: true }]).map((x) => x.name), ['c', 'b', 'a']);
// filters: proof and order
assert.deepStrictEqual(L.filterEntries([{ id: 1, name: 'a', label: 'inference' }, { id: 2, name: 'b', label: 'from code', rendered: true }], { proof: 'rendered' }).map((x) => x.id), [2]);
assert.deepStrictEqual(L.filterEntries([{ id: 1, name: 'b', providers_n: 1 }, { id: 2, name: 'a', providers_n: 9 }], { sort: 'name' }).map((x) => x.id), [2, 1]);
assert.deepStrictEqual(L.filterEntries([{ id: 1, name: 'a', providers_n: 1 }, { id: 2, name: 'b', providers_n: 9 }], { sort: 'packs' }).map((x) => x.id), [2, 1]);
// maths: setting never changes what the atlas says
for (const line of ["x'=x+d·(σ'−σ).", 'σ_i = (σmax^(1/ρ) + r_i·(σmin^(1/ρ) − σmax^(1/ρ)))^ρ, then 0.', 'x ← e^{−h_η}x + v₁ where v₁ blends (1−e^{−h_η})·x0.', 'Clamp |d| at 1000(1+σ/10) via torch.manual_seed(seed+1000·b+i) and compute_ratio(h,i,N)', 'φ₃=(e^{−h_η}−1)/h_η+1']) assert.strictEqual(L.flatten(L.mathTokens(line)), line, line);
const kinds = (s) => L.mathTokens(s).filter((t) => t.t !== 'ws').map((t) => t.t);
assert.deepStrictEqual(kinds('x_pred'), ['v', 'sub']); assert.deepStrictEqual(kinds('compute_ratio'), ['code']); assert.deepStrictEqual(kinds('σmax'), ['v', 'sub']); assert.deepStrictEqual(kinds('e^{−h}'), ['v', 'sup']); assert.deepStrictEqual(kinds('v₁'), ['v', 'sub']);
assert.deepStrictEqual(kinds('gets a fresh tensor'), ['word', 'word', 'word', 'word']); assert.deepStrictEqual(kinds('a = b'), ['v', 'op', 'v']);
const parts = L.mathParts("Symbols: x current latent; σ=sigmas[i]; D=denoised (x0 prediction). \nx'=x+d·dt.\nSame as Euler for every other reason given here somewhere.");
assert.deepStrictEqual(parts.symbols, [['x', 'current latent'], ['σ', 'sigmas[i]'], ['D', 'denoised (x0 prediction)']]); assert.strictEqual(parts.lines.length, 2); assert.ok(parts.lines[0].eq); assert.ok(!parts.lines[1].eq);
// labels light only for what the page really holds
const on = (e, o) => Object.fromEntries(L.proofFacets(e, o).map((f) => [f.key, f.on]));
assert.deepStrictEqual(on({ label: 'from code', evidence: [{}] }), { 'from code': true, 'from pack README claim': false, 'measured here': false, inference: false });
assert.strictEqual(on({ label: 'from code', rendered_ids: ['a'] })['measured here'], true); assert.strictEqual(on({ label: 'from code' }, { curve: true })['measured here'], true);
assert.strictEqual(on({ label: 'inference' }).inference, true); assert.strictEqual(on({ label: 'inference' })['from code'], false);
assert.strictEqual(on({ label: 'from code', claims: [{ label: 'from pack README claim' }] })['from pack README claim'], true);
// nothing outside core reads as proven
assert.strictEqual(L.runsHere({ in_core: true, rendered: true }).tone, 'proven'); assert.ok(/unproven/i.test(L.runsHere({ live: true }).word)); assert.ok(/unproven/i.test(L.runsHere({}).word)); assert.ok(!/unproven/i.test(L.runsHere({ in_core: true }).word));
assert.deepStrictEqual(L.curveStats([10, 2, .5, 0]), { start: 10, last: .5, end: 0, steps: 3 }); assert.strictEqual(L.curveStats([]), null);
// evidence cards take every number from the data, and drop out rather than invent
const rend = { renders: ['sampler-euler', 'sampler-ddim'].map((id) => ({ id, status: 'rendered', sha256: 'abc', diff_to_base: 0, seen: 'same' })) };
const cards = L.evidenceCards(rend, {}); assert.deepStrictEqual(cards.map((c) => c.key), ['ddim']); assert.strictEqual(cards[0].stat, '0.0'); assert.ok(cards[0].more.includes('abc'));
rend.renders[1].sha256 = 'zzz'; assert.deepStrictEqual(L.evidenceCards(rend, {}), [], 'ddim=euler is only claimed when the files match'); assert.deepStrictEqual(L.evidenceCards(null, null), []);
// difference: zero for identical, the real mean otherwise, brightened picture stays opaque
const A = new Uint8ClampedArray([10, 20, 30, 255, 0, 0, 0, 255]), B = new Uint8ClampedArray([13, 20, 30, 255, 0, 0, 0, 255]), O = new Uint8ClampedArray(8);
assert.strictEqual(L.diffPixels(A, A), 0); assert.strictEqual(L.diffPixels(A, B, 4, O), 0.5); assert.deepStrictEqual([...O], [12, 0, 0, 255, 0, 0, 0, 255]);
// credit wording stays honest about what is unknown
assert.strictEqual(L.authorWord({ pack: 'x' }), 'author not recorded here'); assert.strictEqual(L.authorWord({ pack: 'x', author: 'me' }), 'me'); assert.strictEqual(L.packName('owner__repo.disabled'), 'repo'); assert.strictEqual(L.licenceWord('none-found'), 'no licence file found');
const wall = L.creditWall([{ pack: 'a', author: 'x', methods: 2 }, { pack: 'b', author: 'x', methods: 3 }, { pack: 'c', author: 'y', methods: 9 }, { pack: 'd', author: '', methods: 1 }]);
assert.deepStrictEqual(wall.authors.map((a) => [a.name, a.packs, a.methods]), [['y', 1, 9], ['x', 2, 5]]); assert.deepStrictEqual(wall.unknown.map((c) => c.pack), ['d']);
assert.deepStrictEqual(L.licenceCounts([{ licence: 'MIT' }, { licence: 'GPL-3.0' }, { licence: 'GPL' }, { licence: '' }, { licence: 'none-found' }, { licence: 'other:LICENSE' }]), [['GPL', 2], ['No licence file found', 2], ['MIT', 1], ['Other', 1]]);
assert.strictEqual(L.tidyText('It clips to 0..1 and quantises to 8 bits, ``.'), 'It clips to 0..1 and quantises to 8 bits.'); assert.strictEqual(L.tidyText('Reads a value. `x` stays.'), 'Reads a value. `x` stays.');
assert.deepStrictEqual(L.whereFirst('a/b.py:1 c/d.py:2 e'), { first: 'a/b.py:1', more: 2 }); assert.deepStrictEqual(L.whereFirst(''), { first: '', more: 0 });
const list = [{ id: 'a', family: 'f', subfamily: 's' }, { id: 'b', family: 'f', subfamily: 's' }, { id: 'c', family: 'g', subfamily: 's' }];
const nb = L.neighbours(list, list, list[1]); assert.strictEqual(nb.prev.id, 'a'); assert.strictEqual(nb.next.id, 'c'); assert.deepStrictEqual(nb.siblings.map((x) => x.id), ['a']);
const solv = { d: { eps: { same_answer_with_other_noise_seed: true, calls: { 5: 5, 10: 10, 20: 20, 40: 40 }, rmse_to_exact: { 5: .4, 10: .2, 20: .1, 40: .05 }, slope_vs_calls: -1 } }, s: { eps: { same_answer_with_other_noise_seed: false, calls: { 20: 20 } } }, e: { eps: { error: 'x' } } };
assert.deepStrictEqual(L.convergence(solv).map((r) => r.name), ['d'], 'stochastic solvers have no exact path to measure against'); assert.strictEqual(L.convergence(solv)[0].pts.length, 4);
assert.deepStrictEqual(L.hilite('Karras churn', 'kar'), [['Kar', true], ['ras churn', false]]); assert.deepStrictEqual(L.hilite('abc', ''), [['abc', false]]);
console.log('ok');
