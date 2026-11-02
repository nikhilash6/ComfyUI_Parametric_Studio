const test = (_name, f) => f();
import assert from "node:assert/strict";
import { EXAMPLE } from "./train_example.js";
import { averageLine, averageWindow, flowSteps, fmtClock, pictureFlag, lossTrend, lossChart, nearestPoint, fmtDuration, fmtLoss, fmtSpeed, fmtGib, statusLine, trainBlockers, jobPayload, estimateLines, abPrompt, abVerdict, curveNote, isLive } from "./train_logic.js";

test("a number that was not measured reads as not measured", () => {
  assert.equal(fmtDuration(null), "not measured yet"); assert.equal(fmtLoss(null), "not measured yet"); assert.equal(fmtSpeed(null), "not measured yet"); assert.equal(fmtGib(null), "not measured");
  assert.equal(fmtDuration(75), "1 min 15 s"); assert.equal(fmtLoss(0.12345), "0.1235"); assert.equal(fmtSpeed(0.5), "2.00 steps per s"); assert.equal(fmtSpeed(2), "2.00 s per step");
});
test("the chart draws only what it was given, over the whole planned run", () => {
  assert.equal(lossChart([], 100).empty, true); assert.equal(lossChart(null, 100).empty, true); assert.equal(lossChart([[1, null]], 100).empty, true);
  const c = lossChart([[10, 0.4], [20, 0.2]], 100, 720, 240);
  assert.equal(c.points.length, 2); assert.equal(c.xMax, 100); assert.equal(c.lo, 0.2); assert.equal(c.hi, 0.4);
  assert.ok(c.points[1].x < 720 / 2, "20 of 100 steps sits in the left part"); assert.ok(c.points[0].y < c.points[1].y, "the higher loss is drawn higher");
  assert.match(c.path, /^M[\d.]+ [\d.]+L[\d.]+ [\d.]+$/);
});
test("a missing value breaks the line, it is not bridged", () => {
  const c = lossChart([[1, 0.5], [2, null], [3, 0.3], [4, 0.2]], 4);
  assert.equal(c.points.length, 3); assert.equal((c.path.match(/M/g) || []).length, 2);
});
test("a flat curve still draws", () => { const c = lossChart([[1, 0.5], [2, 0.5]], 2); assert.ok(c.hi > c.lo); assert.ok(!c.path.includes("NaN")); });
test("the crosshair finds the nearest real point", () => { const c = lossChart([[10, 0.4], [90, 0.2]], 100); assert.equal(nearestPoint(c, c.points[1].x + 3).step, 90); });
test("the note says where the curve came from", () => {
  assert.match(curveNote({ curve_points: 0 }), /No loss value/);
  assert.match(curveNote({ curve_points: 40, curve_source: "live log", step: 80 }), /40 of 80 steps/);
  assert.match(curveNote({ curve_points: 300, curve_source: "loss_map" }), /Every step/);
});
test("the trend is two plain means of real values, and absent for a short run", () => {
  assert.equal(lossTrend([[1, 0.5]]), null);
  const t = lossTrend(Array.from({ length: 40 }, (_, i) => [i + 1, i < 4 ? 1 : i >= 36 ? 3 : 2])); assert.equal(t.first, 1); assert.equal(t.last, 3);
  assert.match(curveNote({ curve_points: 40, curve_source: "loss_map", curve: Array.from({ length: 40 }, (_, i) => [i, 0.2]) }), /first tenth 0\.2000/);
});
test("status lines", () => {
  assert.match(statusLine({ state: "queued", position: 2 }), /position 2/); assert.match(statusLine({ state: "running", step: 0 }), /No step has run yet/); assert.match(statusLine({ state: "running", step: 3, total: 9 }), /step 3 of 9/);
  assert.match(statusLine({ state: "cancelled" }), /nothing from this run was kept/); assert.match(statusLine({ unreachable: true, state: "running" }), /not answering/); assert.match(statusLine({ state: "error", error: "boom" }), /boom/);
  assert.ok(isLive({ state: "cancelling" })); assert.ok(!isLive({ state: "done" })); assert.ok(!isLive(null));
});
test("Train stays off until everything is there, and the tick is one of those things", () => {
  const ok = { report: { ready: true, blocks: 0 }, base: { id: "x" }, form: { name: "Brass", trigger: "brasslight", rights: true }, active: false };
  assert.deepEqual(trainBlockers(ok), []);
  assert.ok(trainBlockers({ ...ok, form: { ...ok.form, rights: false } }).some((x) => /rights and consent/.test(x)));
  assert.ok(trainBlockers({ ...ok, report: { ready: false, blocks: 2 } }).some((x) => /2 problems/.test(x)));
  assert.ok(trainBlockers({ ...ok, base: null }).some((x) => /No base/.test(x)));
  assert.ok(trainBlockers({ ...ok, active: true }).some((x) => /already running/.test(x)));
  assert.ok(trainBlockers({ ...ok, form: { ...ok.form, trigger: "two words" } }).some((x) => /trigger/.test(x)));
});
test("the payload sends the tick only when it is really true", () => {
  const f = { name: " A ", trigger: " b1 ", size: "1024", steps: "300", rank: "8", batch: "1", learning_rate: "0.0005", seed: "0", rights: true };
  const p = jobPayload(f, "d", "base"); assert.equal(p.rights_confirmed, true); assert.equal(p.size, 1024); assert.equal(p.name, "A"); assert.equal(p.continue_from, undefined);
  assert.equal(jobPayload({ ...f, rights: "true" }, "d", "b").rights_confirmed, false);
});
test("estimates quote the measurement, or say there is none", () => {
  const none = estimateLines({ measured: false, note: "No run on this card" }); assert.equal(none.measured, false); assert.deepEqual(none.lines, ["No run on this card"]);
  const yes = estimateLines({ measured: true, train_seconds: 150, s_per_step: 0.5, setup_seconds: 9, peak_vram_gib: 14, from: { steps: 200, date: "2026-11-01" }, note: "Measured on this card at these settings." });
  assert.match(yes.lines.join(" "), /2 min 30 s/); assert.match(yes.lines.join(" "), /14\.0 GB/); assert.match(yes.lines.join(" "), /real run of 200 steps/);
});
test("the A/B prompt starts from a real caption", () => {
  assert.equal(abPrompt("brass", { items: [{ caption: "brass, a tower" }] }), "brass, a tower"); assert.equal(abPrompt("brass", { items: [{ caption: "a tower" }] }), "brass, a tower"); assert.equal(abPrompt("brass", null), "brass");
});
test("the A/B verdict never calls a change good", () => {
  assert.equal(abVerdict({ state: "queued" }), null);
  const same = abVerdict({ state: "done", pixel_diff: 0.01, unbound_keys: 0 }); assert.ok(same[0].warn && /did nothing visible/.test(same[0].text));
  const moved = abVerdict({ state: "done", pixel_diff: 12.3, unbound_keys: 0 }); assert.ok(!moved[0].warn && /for your eye/.test(moved[0].text)); assert.ok(!moved[1].warn);
  assert.ok(abVerdict({ state: "done", pixel_diff: 12.3, unbound_keys: 5 })[1].warn); assert.ok(abVerdict({ state: "done", pixel_diff: null, unbound_keys: null }).every((b) => b.warn));
});
test("the clock keeps a null a null", () => { assert.equal(fmtClock(null), null); assert.equal(fmtClock(110), "1:50"); assert.equal(fmtClock(5), "0:05"); assert.equal(fmtClock(3725), "1:02:05"); });
test("the average line is a real mean, only once a whole window has passed, and restarts after a gap", () => {
  const c = lossChart(Array.from({ length: 40 }, (_, i) => [i + 1, i < 20 ? 0.2 : 0.4]), 100, 720, 240);
  const a = averageLine(c, 10);
  assert.equal(a.points[0].step, 10); assert.equal(a.points.length, 31); assert.ok(Math.abs(a.points[0].loss - 0.2) < 1e-9); assert.ok(Math.abs(a.points[a.points.length - 1].loss - 0.4) < 1e-9);
  assert.equal(averageLine(lossChart([], 100), 10).path, ""); assert.equal(averageLine(lossChart([[1, 0.5], [2, 0.4]], 100), 10).path, "");
  assert.equal(averageWindow(300), 25); assert.equal(averageWindow(20), 10);
});
test("the mark on a picture names its worst problem", () => {
  assert.equal(pictureFlag([]), null); assert.equal(pictureFlag(null), null);
  const f = pictureFlag([{ level: "warn", code: "small" }, { level: "block", code: "no_caption" }]); assert.equal(f.level, "block"); assert.equal(f.text, "No caption"); assert.equal(f.more, 1);
  assert.equal(pictureFlag([{ level: "warn", code: "new_code" }]).text, "Look at this");
});
test("the flow reports what is true of each step now", () => {
  const base = { arch: "SDXL", sizes: [768, 1024] }, form = { size: 1024, steps: 300 };
  let s = flowSteps({ report: null, base, form, job: null, blockers: ["a", "b"] });
  assert.deepEqual(s.map((x) => x.state), ["now", "done", "todo", "todo"]); assert.equal(s[2].note, "2 things left");
  s = flowSteps({ report: { items: [1, 2, 3], blocks: 2 }, base, form, job: null, blockers: ["a"] }); assert.equal(s[0].state, "fix"); assert.equal(s[0].note, "3 pictures, 2 to fix");
  s = flowSteps({ report: { items: [1], blocks: 0 }, base: null, form, job: null, blockers: [] }); assert.equal(s[1].state, "fix");
  s = flowSteps({ report: { items: [1, 2], blocks: 0 }, base, form, job: { state: "running", step: 121, total: 300 }, blockers: ["x"] }); assert.equal(s[2].state, "now"); assert.equal(s[2].note, "Step 121 of 300");
  s = flowSteps({ report: null, base, form, job: { state: "done", lora: {}, total: 300, ab: null }, blockers: [] }); assert.equal(s[3].state, "now"); assert.equal(s[3].note, "A/B to render");
  s = flowSteps({ report: { items: [1, 2], blocks: 0 }, base, form, job: { state: "error", total: 300 }, blockers: [] }); assert.equal(s[3].note, "Nothing yet"); assert.equal(s[2].state, "now"); assert.equal(s[2].note, "Ready");
});
test("the example is the real run: all 300 values, and the means the page quotes", () => {
  assert.equal(EXAMPLE.loss.length, EXAMPLE.steps); assert.equal(EXAMPLE.steps, 300); assert.equal(EXAMPLE.pictures, 12);
  const t = lossTrend(EXAMPLE.loss.map((v, i) => [i + 1, v])); assert.equal(t.first.toFixed(4), "0.1626"); assert.equal(t.last.toFixed(4), "0.1849");
});
// bases: badges, order and the facts line
{
  const { baseBadge, orderBases, baseFacts } = await import("./train_logic.js");
  const ok = { report: { ready: true, blocks: 0 }, base: { id: "x", trainable: true }, form: { name: "Brass", trigger: "brasslight", rights: true }, active: false };
  const f = { name: "A", trigger: "b1", size: "1024", steps: "300", rank: "8", batch: "1", learning_rate: "0.0005", seed: "0", rights: true };
  assert.equal(baseBadge({ status: "proven" }).text, "Proven");
  assert.equal(baseBadge({ status: "not_run" }).kind, "notrun");
  assert.equal(baseBadge({ status: "blocked" }).kind, "missing");
  assert.deepEqual(orderBases([{ id: "a", status: "blocked" }, { id: "b", status: "not_run" }, { id: "c", status: "proven" }, { id: "d", status: "proven" }]).map((b) => b.id), ["c", "d", "b", "a"]);
  assert.equal(baseFacts({ trainer_label: "T", licence: { name: "MIT" }, peak_gib: 12, peak_kind: "measured" }), "T · MIT · peak measured 12 GB");
  assert.ok(trainBlockers({ ...ok, base: { trainable: false, can_try: true }, form: { ...ok.form, first_run: false } }).some((x) => /first-run box/.test(x)));
  assert.deepEqual(trainBlockers({ ...ok, base: { trainable: false, can_try: true }, form: { ...ok.form, first_run: true } }), []);
  assert.equal(jobPayload({ ...f, first_run: true }, "d", "b").first_run, true);
  assert.match(statusLine({ state: "cancelled", trainer: "ai-toolkit", can_resume: true, checkpoints: ["a", "b"] }), /resume from the last one/);
  assert.match(abVerdict({ state: "done", audio: true, pixel_diff: 0.01 })[0].text, /for your ear/);
  assert.match(abVerdict({ state: "done", source: "trainer samples", pixel_diff: 30 })[1].text, /trainer's own samples/);
}

console.log("ok");
