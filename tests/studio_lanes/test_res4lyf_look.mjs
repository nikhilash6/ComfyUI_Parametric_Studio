import assert from 'node:assert';
import { phi1, phi2, toySigmas, toyPath, toyExact, TOY_METHODS, nodeMap, NODE_REGIONS, findRender, storiesFor, modelCalls } from './res4lyf_logic.js';
import { NODES } from './res4lyf_nodes.js';

// The phi weights: known limits and values
assert.ok(Math.abs(phi1(1) - (1 - Math.exp(-1))) < 1e-12);
assert.strictEqual(phi1(0), 1);
assert.ok(Math.abs(phi2(1) - Math.exp(-1)) < 1e-12);
assert.strictEqual(phi2(0), 0.5);

// The schedule runs from one sigma to the other
const sig = toySigmas(6, 3, 0.03);
assert.strictEqual(sig.length, 7);
assert.ok(Math.abs(sig[6] - 0.03) < 1e-12 && sig[0] === 3);

// A budget of calls buys the steps the page says it does
assert.strictEqual(toyPath('euler', 0.3, 8, 3, 0.03).length, 9);
assert.strictEqual(toyPath('res_2s', 0.3, 8, 3, 0.03).length, 5);
assert.strictEqual(toyPath('heun_2s', 0.3, 8, 3, 0.03).length, 5);
assert.deepStrictEqual(Object.keys(TOY_METHODS).map((k) => TOY_METHODS[k].calls), [1, 2, 2]);

// The reference answer really has settled, and every method closes on it as it gets more calls
const exact = toyExact(0.3, 3, 0.03), answer = exact[exact.length - 1][1];
const finer = toyExact(0.3, 3, 0.03, 24000);
assert.ok(Math.abs(answer - finer[finer.length - 1][1]) < 1e-6);
for (const k of Object.keys(TOY_METHODS)) {
  const gap = (calls) => { const p = toyPath(k, 0.3, calls, 3, 0.03); return Math.abs(p[p.length - 1][1] - answer); };
  assert.ok(gap(400) < gap(8), k);
  assert.ok(gap(4000) < 1e-3, k);
}
// The res_2s step with a still guess lands exactly: for one fixed denoised value the exponential weights solve the walk. Checked with sigma far from the fold, where tanh is flat at 1.
const still = toyPath('res_2s', 1, 2, 0.02, 0.01);
assert.ok(Math.abs(still[1][1] - 1) < 1e-9);

// The map places every node exactly once, and a new group can't fall off it
const map = nodeMap(NODES);
assert.strictEqual(map.reduce((a, r) => a + r.count, 0), NODES.length);
const seen = map.flatMap((r) => r.groups.map((g) => g.name));
assert.strictEqual(new Set(seen).size, seen.length);
assert.ok(map.every((r) => r.t !== 'Everything else'), 'every group in the notes has a region');
const extra = nodeMap([...NODES, { n: 'x', g: 'Brand new', s: 'ran', d: '' }]);
assert.strictEqual(extra[extra.length - 1].t, 'Everything else');
assert.strictEqual(extra.reduce((a, r) => a + r.count, 0), NODES.length + 1);
const rendered = map.flatMap((r) => r.groups).reduce((a, g) => a + g.rendered, 0);
assert.strictEqual(rendered, NODES.filter((n) => n.s === 'rendered').length);
assert.strictEqual(new Set(NODE_REGIONS.flatMap((r) => r.g)).size, NODE_REGIONS.flatMap((r) => r.g).length);

// A comparison is only offered when both renders exist for that model
const g = [{ family: 'A', name: 'x' }, { family: 'A', name: 'y' }, { family: 'B', name: 'x' }];
assert.strictEqual(findRender(g, 'A', 'y'), g[1]);
assert.strictEqual(findRender(g, 'B', 'y'), undefined);
assert.deepStrictEqual(storiesFor([{ id: 1, a: 'x', b: 'y' }], g, 'B'), []);
assert.strictEqual(storiesFor([{ id: 1, a: 'x', b: 'y' }], g, 'A').length, 1);
assert.strictEqual(modelCalls(20, 2), 40);
console.log('ok');
