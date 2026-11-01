const test = (_name, f) => f();
import assert from "node:assert/strict";
import { statusChip, summaryOf, filterAssets, canApprove, canRetry, canMakeProp, parseTags, createPayload, stepRows, addClip, routeFor, blockers, makerRow, makerBoard, MAKERS, stepLabel, stepDone, scaleCompare, shopCounts, firstAsset, nextStep, fileUrl, exportUrl } from "./worldkit_helpers.js";

test("status chips say what state a build is in", () => {
  assert.equal(statusChip({ running: true, progress: [2, 8] }).label, "building 2/8");
  assert.match(statusChip({ build: "failed", failed_step: "rig" }).label, /failed at rig/);
  assert.match(statusChip({ build: "building" }).label, /interrupted/);
  assert.equal(statusChip({ build: "done", status: "approved" }).label, "approved");
});
test("the detail view's summary counts finished steps and ignores an optional failure", () => {
  const s = summaryOf({ status: "draft", build: { state: "done", steps: [{ status: "done" }, { status: "skipped" }, { status: "failed", note: "optional: the build continues", name: "x" }] } });
  assert.deepEqual(s.progress, [2, 3]); assert.equal(s.failed_step, "");
});
test("filters and buttons", () => {
  const list = [{ name: "Rainy block", type: "place", status: "draft", tags: ["street"] }, { name: "Chair", type: "prop", status: "approved", tags: [] }];
  assert.equal(filterAssets(list, { q: "street" }).length, 1); assert.equal(filterAssets(list, { type: "prop", status: "approved" }).length, 1);
  assert.ok(canApprove({ build: "done", status: "draft" })); assert.ok(!canApprove({ build: "done", status: "approved" })); assert.ok(canRetry({ build: "failed" }));
  assert.ok(canMakeProp({ type: "character", build: { steps: [{ name: "mesh", status: "done" }, { name: "rig", status: "failed" }] } }));
});
test("a form becomes the request the API expects", () => {
  assert.deepEqual(parseTags(" A, b ,,"), ["a", "b"]);
  assert.deepEqual(createPayload("place", { name: "x", brief: " a street ", textures: "procedural", preset: "rainy", time: "night" }).recipe, { look: { preset: "rainy", time: "night", weather: null }, textures: "procedural" });
  assert.deepEqual(createPayload("prop", { via: "mesh", mesh: "a/b.glb", size: "2" }).source, { mesh: "a/b.glb" });
  assert.equal(createPayload("prop", { via: "mesh", mesh: "a/b.glb", size: "2" }).recipe.size_m, 2);
  assert.deepEqual(createPayload("prop", { via: "text", prompt: " a chair " }).source, { prompt: "a chair" });
  assert.deepEqual(createPayload("prop", { via: "image", image: "s.png" }).source, { image: "s.png" });
  assert.deepEqual(createPayload("character", { characterId: "c" }).source, { character_id: "c" });
  assert.equal(addClip([{ name: "a", text: "1" }], "a", "2")[0].text, "2");
  assert.equal(stepRows({ build: { steps: [{ name: "rig", status: "failed", error: "e" }] } })[0].cls, "danger");
});
test("what stands in a maker's way comes from the server's own words", () => {
  const caps = { makers: { place: { ready: true, problems: [] }, prop_text: { ready: false, problems: ["SAM 3D Objects: model still downloading or missing"] } } };
  assert.equal(routeFor("prop", "text"), "prop_text"); assert.equal(routeFor("prop"), "prop_mesh"); assert.equal(routeFor("place"), "place");
  assert.deepEqual(blockers(caps, "place"), []); assert.match(blockers(caps, "prop", "text")[0], /downloading/); assert.deepEqual(blockers(null, "place"), []);
});
test("urls are encoded", () => { assert.equal(fileUrl("abc", "thumb.jpg"), "/api/worldkit/assets/abc/file/thumb.jpg"); assert.equal(exportUrl("a b.zip"), "/api/worldkit/exports/a%20b.zip"); });
test("the workshop board uses the server's own words", () => {
  const caps = { makers: { place: { ready: true, problems: [], needs: [] }, prop_image: { ready: false, problems: ["SAM 3D Objects: model still downloading or missing"], needs: [{ label: "BiRefNet", state: "ready" }, { label: "a picture-to-mesh model", state: "missing" }] }, character: { ready: false, problems: ["The character maker is off: reason.", "SAM 3D Body: missing"], needs: [{ label: "SAM 3D Body", state: "missing" }] }, look: { ready: false, problems: ["Blender was not found."], needs: [] } } };
  const row = (k) => makerBoard(caps).find((r) => r.key === k);
  assert.equal(row("place").state, "Ready"); assert.equal(row("prop_image").state, "Model not on this machine"); assert.match(row("prop_image").why, /picture-to-mesh/); assert.deepEqual(row("prop_image").more, caps.makers.prop_image.problems);
  assert.equal(row("character").state, "Off"); assert.equal(row("character").why, "The character maker is off: reason."); assert.deepEqual(row("character").more, ["SAM 3D Body: missing"]);
  assert.equal(row("look").state, "Not ready"); assert.equal(row("look").why, "Blender was not found."); assert.equal(row("prop_text").state, "Checking");
  assert.equal(makerBoard(null).length, MAKERS.length);
  assert.equal(makerRow({ makers: { character: { ready: true } } }, MAKERS[5]).state, "Ready");   // the day it is switched on, the board says so
});
test("steps in words, scale, counts, what opens first", () => {
  assert.equal(stepLabel("tex_wall2"), "Wall 2 texture"); assert.equal(stepLabel("tiles"), "Lay out the set"); assert.equal(stepLabel("some_new_step"), "Some new step");
  assert.equal(stepDone([{ status: "done" }, { status: "skipped" }, { status: "failed" }]), 2);
  assert.equal(scaleCompare(null), null); assert.equal(scaleCompare(0), null); assert.equal(scaleCompare(40).text, "40 m"); assert.equal(scaleCompare(1.234).text, "1.23 m"); assert.equal(scaleCompare(0.9).asset, 0.5); assert.equal(scaleCompare(40).asset, 1);
  const list = [{ id: "a", build: "failed", status: "draft", files: [] }, { id: "b", build: "done", status: "draft", files: ["asset.glb"] }, { id: "c", build: "done", status: "approved", files: ["asset.glb"] }, { id: "d", build: "pending", status: "draft", running: true, files: [] }];
  assert.deepEqual(shopCounts(list), { total: 4, building: 1, review: 1, approved: 1 }); assert.equal(firstAsset(list).id, "c"); assert.equal(firstAsset(list.slice(0, 2)).id, "b"); assert.equal(firstAsset(list.slice(0, 1)).id, "a"); assert.equal(firstAsset([]), null);
  assert.match(nextStep({ running: true }), /Building/); assert.match(nextStep({ build: "failed" }), /Retry/); assert.match(nextStep({ build: "done", status: "draft" }), /approve/); assert.match(nextStep({ build: "done", status: "approved" }), /Approved/);
});
console.log("ok");
