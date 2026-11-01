const test = (_name, f) => f();
import assert from "node:assert/strict";
import { blankForm, parseMarks, marksText, parseVec3, numericParams, buildShot, formFromShot, routeName, blockers, formatProblem, poseProblem, stateChip, canRetry, qcText, moveItem, planView, fileUrl, glbUrl, modeParts, routeStatus, modeStatus, frustum, needsSync, MODE_ROUTES, MODE_NAMES } from "./vset_helpers.js";

test("marks and vectors parse from text and back", () => {
  assert.deepEqual(parseMarks("0,0; 0,-3\n2 1"), [[0, 0], [0, -3], [2, 1]]);
  assert.equal(parseMarks("0,0; nope"), null); assert.equal(parseMarks(""), null);
  assert.equal(marksText([[0, 0], [0, -3]]), "0,0; 0,-3");
  assert.deepEqual(parseVec3("1, 2,3"), [1, 2, 3]); assert.equal(parseVec3("1,2"), null);
});
const FORM = { ...blankForm(), name: "Street", place: "placeplacepl", props: [{ asset: "propproppropp", x: "1", y: "2", yaw: "30", scale: "" }], marks: "0,0; 0,-3", preset: "orbit", params: { sweep_deg: "120", easing: "linear", radius_m: "" }, mode: "A", control: "depth", engine: "h3", seed: "7", prompt: "rain falls", weather: "rain" };
test("a form becomes the shot the server validates, and a place and props alone is a whole shot", () => {
  const s = buildShot(FORM);
  assert.deepEqual(s.set.props, [{ asset: "propproppropp", pos: [1, 2, 0], rot_deg: [0, 0, 30], scale: 1 }]);
  assert.deepEqual(s.cast, []); assert.deepEqual(s.marks, [[0, 0], [0, -3]]);
  assert.deepEqual(s.camera, { preset: "orbit", params: { sweep_deg: 120, easing: "linear" } });
  assert.deepEqual(s.look, { preset: "day_clear", time: null, weather: "rain" });
  assert.deepEqual(s.mode_settings, { control: "depth", engine: "h3" });
  assert.equal(s.seed, 7); assert.equal(s.format.seconds, 5); assert.equal(s.id, undefined);
  assert.deepEqual(buildShot({ ...FORM, mode: "C", keyframes: "raw" }).mode_settings, { keyframes: "raw" });
  assert.deepEqual(buildShot({ ...FORM, mode: "B" }).mode_settings, {});
  const custom = buildShot({ ...FORM, preset: "custom", startPos: "0,-5,1.6", startLook: "0,0,1.3", endPos: "2,-3,1.6", endLook: "0,0,1.3", lens: "50" });
  assert.deepEqual(custom.camera.path.start.pos, [0, -5, 1.6]); assert.equal(custom.camera.lens_mm, 50);
  assert.equal(buildShot({ ...FORM, lookAsset: "looklooklook" }).look.asset, "looklooklook");
  assert.deepEqual(numericParams({ a: "1.5", b: "", easing: "ease_in" }), { a: 1.5, easing: "ease_in" });
});
test("a saved shot round-trips through the form", () => {
  const s = { ...buildShot(FORM), id: "shotshotshot" };
  assert.deepEqual(buildShot(formFromShot(s)), s);
  const c = { ...buildShot({ ...FORM, preset: "custom", startPos: "0,-5,1.6", startLook: "0,0,1.3", endPos: "2,-3,1.6", endLook: "0,0,1.3" }), id: "shotshotshot" };
  assert.deepEqual(buildShot(formFromShot(c)), c);
});
const CAPS = { blender: "", routes: { A: { ready: true, problems: [] }, A_wan: { ready: false, problems: ["Wan 2.2 Fun Control (high noise): model still downloading or missing"] }, C: { ready: false, problems: ["Qwen-Image 2.1 (keyframe edit): model missing"] }, C_raw: { ready: true, problems: [] } } };
test("what stands in the way is the server's own sentence", () => {
  assert.equal(routeName({ mode: "A", engine: "wan" }), "A_wan"); assert.equal(routeName({ mode: "A", engine: "ltx" }), "A_ltx"); assert.equal(routeName({ mode: "A", engine: "ltx", keyframes: "raw" }), "A_ltx_raw"); assert.equal(routeName({ mode: "C", keyframes: "raw" }), "C_raw"); assert.equal(routeName({ mode: "B" }), "B");
  assert.deepEqual(blockers(CAPS, { mode: "A", engine: "h3" }), []);
  assert.match(blockers(CAPS, { mode: "A", engine: "wan" })[0], /Wan 2.2 Fun Control/);
  assert.deepEqual(blockers(CAPS, { mode: "C", keyframes: "raw" }), []);
  assert.match(blockers({ ...CAPS, blender: "Blender is not installed" }, { mode: "A", engine: "h3" })[0], /Blender/);
  assert.deepEqual(blockers(null, { mode: "A" }), []);
});
const META = { wan: { aspects: ["9:16", "16:9"], seconds: [5] }, modes: { A: { aspects: ["9:16", "16:9", "1:1"], seconds: [5] }, C: { aspects: ["9:16", "16:9", "1:1"], seconds: [5, 8, 10] } } };
test("format limits and the pose rule give instant feedback", () => {
  assert.equal(formatProblem(META, { mode: "A", engine: "wan", aspect: "1:1", seconds: "5" }), "this mode renders 9:16, 16:9 only");
  assert.equal(formatProblem(META, { mode: "A", engine: "h3", aspect: "1:1", seconds: "8" }), "this mode renders 5 s");
  assert.equal(formatProblem(META, { mode: "C", aspect: "16:9", seconds: "10" }), "");
  assert.match(poseProblem({ mode: "A", control: "pose", cast: [] }), /depth pass/); assert.equal(poseProblem({ mode: "A", control: "pose", cast: [{ asset: "x" }] }), "");
});
test("state chips, QC text and reordering", () => {
  assert.equal(stateChip({ state: "review" }).label, "needs review");
  assert.equal(stateChip({ state: "done", running: true, progress: [1, 4] }).label, "rendering 1/4");
  assert.equal(stateChip({ state: "done", scope: "passes" }).label, "passes ready");
  assert.equal(stateChip({ state: "failed", failed_step: "video" }).label, "failed at video");
  assert.match(stateChip({ state: "building" }).label, /interrupted/); assert.equal(stateChip(null).label, "new");
  assert.ok(canRetry({ state: "failed" })); assert.ok(!canRetry({ state: "done" })); assert.ok(!canRetry({ state: "failed", running: true }));
  assert.equal(qcText({ face: null, flicker: 2.31, layout: 0.4, reasons: [] }), "flicker 2.3, layout 0.40");
  assert.deepEqual(moveItem(["a", "b", "c"], 2, 0), ["c", "a", "b"]);
});
test("the plan view fits the whole move in the box, with +Y up", () => {
  const preview = { bounds: { lo: [-6, -6, 0], hi: [6, 6, 3] }, subject: [[0, 0], [0, -3]], keys: [{ pos: [0, -8, 1.5], look: [0, 0, 1.3] }, { pos: [0, -2, 1.5], look: [0, 0, 1.3] }] };
  const v = planView(preview, 420, 280, 16);
  const [x0, y0] = v.at(0, 6), [, y1] = v.at(0, -8);
  assert.ok(x0 > 16 && x0 < 404 && y0 >= 15 && y1 <= 265 && y0 < y1);
  assert.ok(v.box.w > 0 && v.box.h > 0); assert.equal(v.camera.split(" ").length, 2);
  assert.equal(planView(null), null); assert.equal(planView({ keys: [] }), null);
});
test("urls are encoded", () => { assert.equal(fileUrl("abc", "depth"), "/api/vset/shots/abc/file/depth"); assert.equal(glbUrl("a b"), "/api/worldkit/assets/a%20b/file/asset.glb"); });
test("a mode's name and line come from the server's label", () => {
  assert.deepEqual(modeParts("B", "B: restyle (the shaded render, H3 follows its exact depth)"), { name: "restyle", what: "The shaded render, H3 follows its exact depth" });
  assert.deepEqual(modeParts("C"), { name: "keyframes", what: "" });
});
test("a route's status is read from the server, never assumed", () => {
  assert.equal(routeStatus(undefined).label, "Status unknown");
  const off = routeStatus({ ready: false, problems: ["SAM missing"], proof: { state: "passed", passed: 3 } });
  assert.equal(off.label, "Model not on this machine"); assert.equal(off.detail, "SAM missing");   // files gone beat an old pass
  assert.match(routeStatus({ ready: true }).label, /proof not reported/);
  assert.equal(routeStatus({ ready: true, proof: { state: "none" } }).label, "Ready, not yet rendered here");
  assert.equal(routeStatus({ ready: true, proof: { state: "passed", passed: 1 } }).cls, "ok"); assert.match(routeStatus({ ready: true, proof: { state: "passed", passed: 2 } }).label, /2 shots/);
  assert.equal(routeStatus({ ready: true, proof: { state: "review", review: 1 } }).cls, "warn"); assert.equal(routeStatus({ ready: true, proof: { state: "failed", failed: 1 } }).cls, "danger"); assert.match(routeStatus({ ready: true, proof: { state: "running" } }).label, /running/);
});
test("every mode lists its routes, and a card links the shot that proves one", () => {
  assert.deepEqual(Object.keys(MODE_ROUTES), Object.keys(MODE_NAMES));
  const rows = modeStatus({ routes: { C: { ready: true, proof: { state: "passed", passed: 1, shot: "abc" } }, C_raw: { ready: true, proof: { state: "none", shot: "" } } } }, "C");
  assert.deepEqual(rows.map((r) => [r.route, r.proofShot]), [["C", "abc"], ["C_raw", ""]]);
  assert.equal(modeStatus(null, "A").length, 4); assert.equal(modeStatus(null, "A")[0].label, "Status unknown");
});
test("the plan's field of view and the clip sync", () => {
  const [a, b] = frustum([0, 0], [100, 0], 36, 36, 50);
  assert.equal(a[1], -b[1]); assert.ok(a[0] > 40 && a[0] < 50);
  assert.ok(needsSync(1, 1.2)); assert.ok(!needsSync(1, 1.05));
});
console.log("ok");
