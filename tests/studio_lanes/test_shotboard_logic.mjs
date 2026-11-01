import assert from 'node:assert';
import { applyPatch, cancelOpen, canRetry, stoppedStatus } from './shotboard_logic.js';

const jobs = [{ id: 'a', status: 'done' }, { id: 'b', status: 'running', job: 'p1' }, { id: 'c', status: 'queued' }, { id: 'd', status: 'error', error: 'x' }];

// Cancel stops what is open and leaves finished work alone
const off = cancelOpen(jobs);
assert.deepStrictEqual(off.map((j) => j.status), ['done', 'cancelled', 'cancelled', 'error']);
assert.ok(!off.some((j) => j.status === 'queued' || j.status === 'running'), 'nothing left to lock the board');
assert.strictEqual(off[1].error, 'Cancelled.');
assert.strictEqual(off[3].error, 'x');

// A late poll or submit cannot bring a cancelled job back
assert.strictEqual(applyPatch(off, 'b', { status: 'done' })[1].status, 'cancelled');
assert.strictEqual(applyPatch(jobs, 'b', { status: 'done' })[1].status, 'done');
assert.strictEqual(applyPatch(jobs, 'b', { status: 'done' })[2].status, 'queued');

// Every stopped job can run again; open and finished ones cannot
assert.deepStrictEqual(['error', 'lost', 'cancelled', 'done', 'queued', 'running'].map((status) => canRetry({ status })), [true, true, true, false, false, false]);

// A lost job gets its own state; any other failure stays an error
assert.strictEqual(stoppedStatus({ status: 'error', lost: true }), 'lost');
assert.strictEqual(stoppedStatus({ status: 'error' }), 'error');
console.log('shotboard logic ok');
