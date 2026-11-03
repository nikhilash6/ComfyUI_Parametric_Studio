import assert from "node:assert";
import { groupsFor, searchLooks, togglePick, keepFor, applyLooks, phrasesOf } from "./look_picker_logic.js";

const groups = [{ id: "lighting", label: "Lighting", kind: "both", section: "light" }, { id: "grade", label: "Colour grade", kind: "both", section: "colour" }, { id: "move", label: "Camera move", kind: "video", section: "motion" }, { id: "style_video", label: "Video styles", kind: "video", section: "style" }];
const looks = [
  { id: "l1", group: "lighting", label: "Golden hour", phrase: "warm golden-hour sun", kind: "both" },
  { id: "l2", group: "lighting", label: "Blue hour", phrase: "cool blue twilight", kind: "both" },
  { id: "g1", group: "grade", label: "Teal and orange", phrase: "teal and orange grade", kind: "both" },
  { id: "m1", group: "move", label: "Slow push in", phrase: "camera slowly pushes in", kind: "video", move: true },
  { id: "v1", group: "style_video", label: "Crane rise reveal", phrase: "Crane rise reveal", kind: "video", move: true },
];
const byId = Object.fromEntries(looks.map((e) => [e.id, e]));

// pictures never see video-only groups or entries
assert.deepStrictEqual(groupsFor(groups, "image").map((g) => g.id), ["lighting", "grade"]);
assert.deepStrictEqual(searchLooks(looks, groups, "", "", "image").map((e) => e.id), ["l1", "l2", "g1"]);
assert.deepStrictEqual(searchLooks(looks, groups, "", "", "video").length, 5);
// search: label, phrase or group label; every word must match
assert.deepStrictEqual(searchLooks(looks, groups, "HOUR", "", "image").map((e) => e.id), ["l1", "l2"]);
assert.deepStrictEqual(searchLooks(looks, groups, "colour", "", "image").map((e) => e.id), ["g1"]);
assert.deepStrictEqual(searchLooks(looks, groups, "golden blue", "", "image"), []);
assert.deepStrictEqual(searchLooks(looks, groups, "", "lighting", "video").map((e) => e.id), ["l1", "l2"]);

// one per group, same pick again removes it
let p = togglePick({}, byId.l1, byId); assert.deepStrictEqual(p, { lighting: "l1" });
p = togglePick(p, byId.l2, byId); assert.deepStrictEqual(p, { lighting: "l2" });
p = togglePick(p, byId.l2, byId); assert.deepStrictEqual(p, {});
// one camera move per clip, across groups
p = togglePick(togglePick({}, byId.m1, byId), byId.v1, byId); assert.deepStrictEqual(p, { style_video: "v1" });
p = togglePick(togglePick(p, byId.g1, byId), byId.m1, byId); assert.deepStrictEqual(p, { grade: "g1", move: "m1" });
// a picture goal drops the video picks
assert.deepStrictEqual(keepFor({ grade: "g1", move: "m1" }, byId, "image"), { grade: "g1" });

// phrases come in group order; applying keeps the person's words and swaps only our phrases
assert.deepStrictEqual(phrasesOf({ grade: "g1", lighting: "l1" }, byId, groups), ["warm golden-hour sun", "teal and orange grade"]);
let t = applyLooks("a fox in snow", [], ["warm golden-hour sun"]); assert.strictEqual(t, "a fox in snow, warm golden-hour sun");
t = applyLooks(t + ", my own words", ["warm golden-hour sun"], ["cool blue twilight"]); assert.strictEqual(t, "a fox in snow, my own words, cool blue twilight");
t = applyLooks(t, ["cool blue twilight"], []); assert.strictEqual(t, "a fox in snow, my own words");
assert.strictEqual(applyLooks("", [], ["teal and orange grade"]), "teal and orange grade");
assert.strictEqual(applyLooks("Teal and orange grade on a car", [], ["teal and orange grade"]), "Teal and orange grade on a car"); // never added twice
assert.strictEqual(applyLooks("a (strange) prompt [x]", ["(strange)"], []), "a prompt [x]"); // phrases are matched literally
console.log("ok");
