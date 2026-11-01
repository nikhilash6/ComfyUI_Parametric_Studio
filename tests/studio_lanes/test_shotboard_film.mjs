import assert from 'node:assert';
import { clock, elapsed, totalSeconds, isStopped, stateWord, readLive, perforations, nodeName, scrubTime, miniGraph } from './shotboard_film.js';

assert.strictEqual(clock(0), '0:00'); assert.strictEqual(clock(187), '3:07'); assert.strictEqual(clock(3725), '1:02:05'); assert.strictEqual(clock(undefined), '0:00'); assert.strictEqual(clock(-4), '0:00');

// A finished take reports what it took; a running one counts from when it started; a queued one has no time yet
assert.strictEqual(elapsed({ seconds: 9, started: 1 }, 99000), 9);
assert.strictEqual(elapsed({ started: 1000 }, 11000), 10);
assert.strictEqual(elapsed({}, 11000), 0);
assert.strictEqual(totalSeconds([{ status: 'done', seconds: 5 }, { status: 'running', started: 1000 }, { status: 'queued' }, { status: 'error', seconds: 40 }], 11000), 15);

// The states the lost-job and cancel work adds are already drawn
assert.deepStrictEqual(['error', 'lost', 'cancelled', 'done', 'queued', 'running'].map(isStopped), [true, true, true, false, false, false]);
assert.strictEqual(stateWord('lost'), 'Lost'); assert.strictEqual(stateWord('cancelled'), 'Cancelled');

// Never invent progress: no live answer, someone else's job and a run without node detail all give no perforations
assert.strictEqual(readLive(null, 'a'), null);
assert.strictEqual(readLive({ running: false }, 'a'), null);
assert.deepStrictEqual(readLive({ running: true, job: 'b', pending: 2 }, 'a'), { waiting: true, pending: 2 });
assert.deepStrictEqual(perforations(readLive({ running: true, job: 'b' }, 'a')), []);
const pulse = readLive({ running: true, job: 'a', mode: 'pulse', nodes: {} }, 'a', 20);
assert.strictEqual(pulse.total, 0); assert.deepStrictEqual(perforations(pulse), []);

// With node detail, every number comes from the answer
const live = readLive({ running: true, job: 'a', mode: 'nodes', preview: 7, nodes: { done: ['1', '2'], cached: ['3'], running: { 4: [0, 0], 5: [12, 30] } } }, 'a', 8);
assert.deepStrictEqual([live.total, live.done, live.cached, live.running, live.node, live.value, live.max, live.preview], [8, 2, 1, 2, '5', 12, 30, 7]);
assert.deepStrictEqual(perforations(live), ['ran', 'ran', 'cached', 'now', 'now', 'todo', 'todo', 'todo']);
assert.strictEqual(readLive({ running: true, job: 'a', mode: 'nodes', nodes: { done: ['1', '2', '3'] } }, 'a', 0).total, 3, 'a graph not seen yet never gives a total below what finished');

assert.strictEqual(nodeName({ 5: { class_type: 'KSampler' } }, '5'), 'KSampler');
assert.strictEqual(nodeName({ 5: { class_type: 'KSampler', _meta: { title: 'Sampler' } } }, '5'), 'Sampler');
assert.strictEqual(nodeName(null, '5'), ''); assert.strictEqual(nodeName({}, '5'), '');

assert.strictEqual(scrubTime(150, 100, 100, 10), 5); assert.strictEqual(scrubTime(50, 100, 100, 10), 0); assert.strictEqual(scrubTime(900, 100, 100, 10), 10); assert.strictEqual(scrubTime(1, 0, 0, 10), 0);

const g = miniGraph({ a: { class_type: 'Load', inputs: {} }, b: { class_type: 'Text', inputs: { text: 'hi' } }, c: { class_type: 'Mix', inputs: { x: ['a', 0], y: ['b', 0], size: [1, 2] } }, d: { class_type: 'Save', inputs: { v: ['c', 0] } } });
assert.strictEqual(g.nodes.length, 4); assert.strictEqual(g.width, 3); assert.strictEqual(g.height, 2); assert.strictEqual(g.links.length, 3);
assert.strictEqual(g.nodes.find((n) => n.id === 'd').x, 2);
assert.strictEqual(miniGraph({ a: { class_type: 'A', inputs: { x: ['b', 0] } }, b: { class_type: 'B', inputs: { x: ['a', 0] } } }).nodes.length, 2, 'a loop does not hang');
assert.deepStrictEqual(miniGraph(null).nodes, []);
console.log('shotboard film ok');
