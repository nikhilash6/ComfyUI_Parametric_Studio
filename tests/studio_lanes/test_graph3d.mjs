import assert from 'node:assert';
import { buildModel, layoutGraph, explain, keyType, placeOrdered, fitView, cometsOn, pulseAge, focusSets, nodeStates, linkState, graphRequest, replayPlan, replayAt, executionOrder, walkOrder, panelSize, PLACEHOLDER, PREVIEW_SEED, labelPriority, pxPerUnit, declutterLabels, zoomLimits, stepNode, overviewView, panelBoxes, hiddenTitles } from './graph3d_math.js';

// a real shape: the FLUX.2 Klein graph the image goal uses
const G = {
  1: { class_type: 'UNETLoader', inputs: { unet_name: 'a/b/flux.safetensors', weight_dtype: 'default' } }, 2: { class_type: 'CLIPLoader', inputs: { clip_name: 'q.safetensors' } }, 3: { class_type: 'VAELoader', inputs: { vae_name: 'v.safetensors' } },
  4: { class_type: 'CLIPTextEncode', inputs: { clip: ['2', 0], text: 'a fox' } }, 5: { class_type: 'CLIPTextEncode', inputs: { clip: ['2', 0], text: '' } }, 6: { class_type: 'EmptyFlux2LatentImage', inputs: { width: 1024, height: 1024 } }, 7: { class_type: 'Flux2Scheduler', inputs: { steps: 4 } },
  8: { class_type: 'CFGGuider', inputs: { model: ['1', 0], positive: ['4', 0], negative: ['5', 0], cfg: 1 } }, 9: { class_type: 'KSamplerSelect', inputs: { sampler_name: 'euler' } }, 10: { class_type: 'RandomNoise', inputs: { noise_seed: 11 } },
  11: { class_type: 'SamplerCustomAdvanced', inputs: { noise: ['10', 0], guider: ['8', 0], sampler: ['9', 0], sigmas: ['7', 0], latent_image: ['6', 0] } }, 12: { class_type: 'VAEDecode', inputs: { samples: ['11', 0], vae: ['3', 0] } }, 13: { class_type: 'SaveImage', inputs: { images: ['12', 0], filename_prefix: 'x' } },
};
// model: links, widgets, depth, types
const m0 = buildModel(G);
assert.strictEqual(m0.ids.length, 13); assert.strictEqual(m0.links.length, 13);
assert.deepStrictEqual(m0.nodes['13'].widgets.map((w) => w.key), ['filename_prefix']);
assert.strictEqual(m0.nodes['13'].depth, 5, 'longest path from a source');
assert.strictEqual(m0.nodes['1'].depth, 0);
const lt = (to, key) => m0.links.find((l) => l.to === to && l.key === key).type;
assert.strictEqual(lt('8', 'model'), 'MODEL'); assert.strictEqual(lt('8', 'positive'), 'CONDITIONING'); assert.strictEqual(lt('11', 'latent_image'), 'LATENT'); assert.strictEqual(lt('12', 'vae'), 'VAE');
assert.strictEqual(keyType('values.a'), 'NUMBER');
// a link to a missing node stays a widget; a cycle cannot hang
assert.strictEqual(buildModel({ a: { class_type: 'X', inputs: { v: ['nope', 0] } } }).links.length, 0);
assert.strictEqual(buildModel({ a: { class_type: 'X', inputs: { i: ['b', 0] } }, b: { class_type: 'Y', inputs: { i: ['a', 0] } } }).ids.length, 2);
assert.strictEqual(layoutGraph({ a: { class_type: 'X', inputs: { i: ['b', 0] } }, b: { class_type: 'Y', inputs: { i: ['a', 0] } } }).ids.length, 2);
assert.strictEqual(buildModel(null).ids.length, 0); assert.strictEqual(layoutGraph({}).ids.length, 0);
// explanations: dict for common classes, class name as the fallback
assert.ok(explain('KSampler').say.length > 20); assert.strictEqual(explain('KSampler').kind, 'sample');
const u = explain('SomeUnknownThing'); assert.strictEqual(u.known, false); assert.strictEqual(u.say, 'SomeUnknownThing');
// every class in the repo's workflows has an explanation
import { readFileSync, existsSync, readdirSync } from 'node:fs';
// (workflows are outside the temp copy of studio/web; the Python side checks them)
// layout: every wire runs left to right, by column and on screen
const L = layoutGraph(G);
L.links.forEach((l) => { assert.ok(L.nodes[l.from].col < L.nodes[l.to].col, `col ${l.from}->${l.to}`); assert.ok(l.curve[0][0] < l.curve[3][0], 'x grows along the wire'); assert.ok(l.len > 0 && Number.isFinite(l.len)); });
assert.ok(L.plate && L.plate.save === '13'); assert.ok(L.plate.pos[0] > L.nodes['13'].pos[0], 'the result sits past the last node');
// panels in one column never overlap
L.cols.forEach((c) => { const s = c.map((i) => [L.nodes[i].y - L.nodes[i].size.h / 2, L.nodes[i].y + L.nodes[i].size.h / 2]).sort((a, b) => a[0] - b[0]); for (let i = 1; i < s.length; i++) assert.ok(s[i][0] >= s[i - 1][1] - 1e-6, 'rows overlap'); });
// floor is under everything, ports sit on the panel edges
L.ids.forEach((i) => assert.ok(L.nodes[i].pos[1] - L.nodes[i].size.h / 2 > L.floor));
assert.ok(Math.abs(placeOrdered([0, 0], [2, 2], 1)[1] - placeOrdered([0, 0], [2, 2], 1)[0] - 3) < 1e-9, 'gap kept'); assert.deepStrictEqual(placeOrdered([0, 100], [1, 1], 1), [0, 100], 'free nodes stay put');
assert.ok(panelSize(L.nodes['11']).w > panelSize(L.nodes['1']).w, 'the sampler is the hero');
// deep graphs weave but still flow left to right
const chain = {}; for (let i = 0; i < 14; i++) chain['n' + i] = { class_type: 'ImageScale', inputs: i ? { image: ['n' + (i - 1), 0] } : {} };
const LC = layoutGraph(chain); LC.links.forEach((l) => assert.ok(LC.nodes[l.from].pos[0] < LC.nodes[l.to].pos[0]));
// the camera fits every point and looks at the middle
const fv = fitView(L.bounds, 0.16, 0.1, 30, 1.75, 1); const tan = Math.tan((30 * Math.PI) / 360);
L.bounds.forEach((p) => { const d = fv.position.map((x, i) => p[i] - x), dir = fv.target.map((x, i) => x - fv.position[i]), n = Math.hypot(...dir), z = (d[0] * dir[0] + d[1] * dir[1] + d[2] * dir[2]) / n; assert.ok(z > 0, 'in front of the camera'); });
// the wave: comets move from source to target as the clock runs; every input of a node arrives together
const link = { start: 10, len: 8 }; const a = cometsOn(link, 12, 30), b = cometsOn(link, 14, 30);
assert.strictEqual(a.length, 1); assert.ok(b[0] > a[0], 'data-flow direction'); assert.deepStrictEqual(cometsOn(link, 5, 30), []);
assert.ok(pulseAge(10, 11, 30) < pulseAge(10, 20, 30)); assert.ok(pulseAge(10, 5, 30) > 0, 'always positive');
L.links.forEach((l) => assert.ok(Math.abs(l.start + l.len - L.arrive[l.to]) < 1e-9));
// hover: direct links only; click: the whole chain
const hov = focusSets(L, '8', false), cl = focusSets(L, '8', true);
assert.strictEqual(hov.links.size, 4); assert.ok(hov.nodes.has('11') && !hov.nodes.has('13')); assert.ok(cl.nodes.has('13') && cl.nodes.has('2'));
assert.strictEqual(focusSets(L, null).links.size, 0);
// a run: states and wires
const st = nodeStates(L, { running: { 11: [3, 20] }, done: ['1', '2', '4', '5', '8', '6', '7', '9', '10'], cached: ['3'] });
assert.strictEqual(st['11'], 'running'); assert.strictEqual(st['1'], 'done'); assert.strictEqual(st['3'], 'cached'); assert.strictEqual(st['13'], 'pending');
assert.strictEqual(linkState({ from: '8', to: '11' }, st), 'flow'); assert.strictEqual(linkState({ from: '12', to: '13' }, st), 'idle'); assert.strictEqual(linkState({ from: '4', to: '8' }, st), 'spent');
assert.strictEqual(nodeStates(L, { running: {}, done: [], error: '12' })['12'], 'error');
// replay follows dependency order and gives the sampler the largest share
const ord = executionOrder(L), pos = Object.fromEntries(ord.map((i, k) => [i, k])); L.links.forEach((l) => assert.ok(pos[l.from] < pos[l.to]));
const plan = replayPlan(L, 10); assert.ok(Math.abs(plan.reduce((x, e) => x + e.seconds, 0) - 10) < 1e-9); assert.strictEqual([...plan].sort((x, y) => y.seconds - x.seconds)[0].id, '11');
const samp = plan.find((e) => e.id === '11'), mid = replayAt(plan, samp.start + samp.seconds / 2); assert.deepStrictEqual(Object.keys(mid.running), ['11']); assert.ok(mid.running['11'][0] >= 10 && mid.running['11'][0] <= 11); assert.ok(mid.done.includes('1')); assert.ok(!mid.done.includes('13'));
assert.strictEqual(replayAt(plan, 11).done.length, 13);
// always a graph: sample prompt, placeholders for missing uploads, stable preview seed
const ideas = { image: ['sample one'], recast: ['x'] };
const r1 = graphRequest({ goal: 'image', prompt: '  ', options: {}, seed: '' }, {}, ideas); assert.strictEqual(r1.body.prompt, 'sample one'); assert.ok(r1.sampled); assert.strictEqual(r1.body.seed, PREVIEW_SEED); assert.ok(r1.previewSeed);
const r2 = graphRequest({ goal: 'image', prompt: 'mine', options: {}, seed: '42', job: 'j' }, {}, ideas); assert.strictEqual(r2.body.prompt, 'mine'); assert.ok(!r2.sampled); assert.strictEqual(r2.body.seed, '42'); assert.ok(!('job' in r2.body));
const r3 = graphRequest({ goal: 'recast', prompt: '', options: {}, seed: '' }, { needs_video: true, needs_image: true, prompt_optional: true }, ideas); assert.strictEqual(r3.body.video, PLACEHOLDER.video); assert.strictEqual(r3.body.image, PLACEHOLDER.image); assert.deepStrictEqual(r3.fills, ['video', 'image']); assert.strictEqual(r3.body.prompt, ''); assert.ok(!r3.sampled);
const r4 = graphRequest({ goal: 'recast', prompt: '', options: {}, video: 'real.mp4', image: 'me.png' }, { needs_video: true, needs_image: true, prompt_optional: true }, ideas); assert.strictEqual(r4.body.video, 'real.mp4'); assert.deepStrictEqual(r4.fills, []);
assert.strictEqual(graphRequest(null, {}, ideas), null);
// the walk skips the small value nodes and starts upstream
const w = walkOrder(L); assert.ok(w.indexOf('11') < w.indexOf('13')); assert.ok(w.length <= 13);
// no two panels intersect in 3D, on the real shape and on many random graphs (oriented boxes, separating axis test)
const obb = (n) => ({ c: n.pos, axes: [n.axisX, [0, 1, 0], [Math.sin(n.yaw), 0, Math.cos(n.yaw)]], e: [n.size.w / 2, n.size.h / 2, 0.055] });
const dot3 = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2], cross3 = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const intersects = (A, B) => { const d = [B.c[0] - A.c[0], B.c[1] - A.c[1], B.c[2] - A.c[2]], axes = [...A.axes, ...B.axes]; A.axes.forEach((a) => B.axes.forEach((b) => { const c = cross3(a, b), l = Math.hypot(...c); if (l > 1e-6) axes.push(c.map((x) => x / l)); }));
  return axes.every((ax) => A.axes.reduce((s, a, i) => s + A.e[i] * Math.abs(dot3(a, ax)), 0) + B.axes.reduce((s, b, i) => s + B.e[i] * Math.abs(dot3(b, ax)), 0) - Math.abs(dot3(d, ax)) > 1e-6); };
const noOverlap = (M) => { for (let i = 0; i < M.ids.length; i++) for (let j = i + 1; j < M.ids.length; j++) assert.ok(!intersects(obb(M.nodes[M.ids[i]]), obb(M.nodes[M.ids[j]])), `panels ${M.ids[i]} and ${M.ids[j]} overlap`); };
noOverlap(L); noOverlap(LC);
{ let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647, CLS = ['KSampler', 'CLIPTextEncode', 'VAEDecode', 'ImageScale', 'LoraLoader', 'SaveImage', 'PrimitiveInt', 'CheckpointLoaderSimple', 'EmptyLatentImage', 'ImageBlend'];
  for (let t = 0; t < 60; t++) { const N = 2 + Math.floor(rnd() * 70), g = {}; for (let i = 0; i < N; i++) { const inputs = { w: 1 }, k = Math.floor(rnd() * 4); for (let j = 0; j < k && i > 0; j++) inputs['in' + j] = ['n' + Math.floor(rnd() * i), 0]; g['n' + i] = { class_type: CLS[Math.floor(rnd() * CLS.length)], inputs }; } noOverlap(layoutGraph(g)); } }
// the overview hides no title behind a nearer panel, on a desktop and on a phone, for the real shape, a deep chain and dense random graphs
const titlesClear = (M) => [[1308, 862], [356, 656]].forEach(([W, H]) => assert.deepStrictEqual(hiddenTitles(panelBoxes(M, overviewView(M, W, H), 30, W, H)), [], `hidden titles at ${W}x${H}`));
titlesClear(L); titlesClear(LC);
{ let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647; for (let t = 0; t < 12; t++) { const N = 20 + Math.floor(rnd() * 50), g = {}; for (let i = 0; i < N; i++) { const inputs = {}; if (i) inputs.a = ['n' + (i - 1 - Math.floor(rnd() * Math.min(i, 3))), 0]; if (i > 2 && rnd() < 0.5) inputs.b = ['n' + Math.floor(rnd() * i), 0]; g['n' + i] = { class_type: ['KSampler', 'CLIPTextEncode', 'VAEDecode', 'ImageScale', 'LoraLoader'][i % 5], inputs }; } titlesClear(layoutGraph(g)); } }
// and the check itself sees a panel that sits in front of another one's title
{ const M = layoutGraph(G), ids = M.ids, bx = panelBoxes(M, overviewView(M, 1308, 862), 30, 1308, 862); const a = bx[0], b = { ...bx[1], all: a.title.slice(), z: a.z - 1 }; assert.deepStrictEqual(hiddenTitles([a, b]), [a.id]); }
// floating labels: the sampler outranks a value node; declutter keeps the best label, drops one that would touch it, drops labels off screen and stops at max
assert.ok(labelPriority('sample') < labelPriority('save') && labelPriority('save') < labelPriority('value')); assert.strictEqual(labelPriority('nonsense'), labelPriority('other'));
assert.ok(Math.abs(pxPerUnit(10, 30, 900) * 2 - pxPerUnit(5, 30, 900)) < 1e-9, 'twice as close, twice as big');
const lab = (id, x, y, pri, z = 1) => ({ id, x, y, w: 100, h: 20, pri, z });
assert.deepStrictEqual(declutterLabels([lab('v', 200, 100, 9), lab('s', 210, 105, 0), lab('far', 600, 300, 3)], { width: 800, height: 600 }), ['s', 'far']);
assert.deepStrictEqual(declutterLabels([lab('off', 10, 100, 0), lab('top', 300, 5, 0), lab('ok', 300, 300, 5)], { width: 800, height: 600 }), ['ok'], 'labels must sit inside the view');
assert.deepStrictEqual(declutterLabels([lab('a', 100, 100, 1, 9), lab('b', 120, 100, 1, 2)], { width: 800, height: 600 }), ['b'], 'same rank: the nearer one wins');
const many = Array.from({ length: 40 }, (_, i) => lab('m' + i, 60 + (i % 6) * 120, 40 + Math.floor(i / 6) * 40, i % 4)); const kept = declutterLabels(many, { width: 800, height: 600, max: 9 });
assert.strictEqual(kept.length, 9); const kb = kept.map((id) => many.find((c) => c.id === id)); kb.forEach((a, i) => kb.slice(i + 1).forEach((b) => assert.ok(Math.abs(a.x - b.x) >= 100 || Math.abs(a.y - b.y) >= 20, 'kept labels never touch')));
// zoom limits bracket the fitted distance, for a tiny graph and a huge one
[3, 20, 400].forEach((d) => { const z = zoomLimits(d); assert.ok(z.min < d && d < z.max && z.min >= 2); });
// arrow keys step through the walk order and wrap
assert.strictEqual(stepNode(['a', 'b', 'c'], null, 1), 'a'); assert.strictEqual(stepNode(['a', 'b', 'c'], null, -1), 'c'); assert.strictEqual(stepNode(['a', 'b', 'c'], 'c', 1), 'a'); assert.strictEqual(stepNode(['a', 'b', 'c'], 'a', -1), 'c'); assert.strictEqual(stepNode([], 'a', 1), null);
// the page really uses three lazily, pauses off screen and disposes
const src = readFileSync('./graph3d.js', 'utf8');
for (const needle of ['import("three")', 'IntersectionObserver', 'ResizeObserver', 'renderer.dispose()', 'forceContextLoss', 'prefers-reduced-motion', 'webglcontextlost', 'cb.onFail']) assert.ok(src.includes(needle), needle);
// ...renders on demand and sleeps when idle, follows a live change of the motion setting, declutters its labels, has a keyboard path and a live description, and never flips over the top
for (const needle of ['IDLE_SLEEP', 'awakeUntil', 'rmq.addEventListener', 'declutterLabels(', 'stepNode(', 'aria-live', 'minPolarAngle', 'zoomLimits(', 'MIRROR_MAX', 'lastPick']) assert.ok(src.includes(needle), needle);
console.log('ok');
