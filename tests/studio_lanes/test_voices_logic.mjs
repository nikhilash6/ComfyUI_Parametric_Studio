// Rules of the Voices page, without a browser. tests/test_node_lanes.py runs this in a copy of studio/web.
import assert from "node:assert/strict";
import { licenceWord, proofWord, board, counts, runBody, canRun, bars, byLanguage, clock } from "./voices_logic.js";

const m = (id, kind, extra = {}) => ({ id, kind, label: id, reference: "none", state: "rendered", licence: { commercial: true }, files: ["a"], proof: { audio: "x", match_pct: 90, secs: 5, peak_gib: 2 }, ...extra });

// research-only and unknown licences never read as commercial
assert.equal(licenceWord({ commercial: true })[0], "Commercial use OK");
assert.equal(licenceWord({ commercial: false })[0], "Non-commercial");
assert.equal(licenceWord({ note: "research" })[0], "Check the licence");
assert.equal(licenceWord(null)[0], "Licence unread");

// the proof label says Whisper, and a low number says only
assert.match(proofWord({ match_pct: 100 })[0], /Whisper/); assert.equal(proofWord({ match_pct: 40 })[1], "bad"); assert.equal(proofWord({ status: "not run" })[0], "Not run here");

// a clip never goes without a yes
const f5 = m("f5", "reference", { reference: "required" });
assert.equal(canRun(f5, { text: "hi" }), false);
assert.equal(canRun(f5, { text: "hi", reference: "a.wav" }), false);
assert.equal(canRun(f5, { text: "hi", reference: "a.wav", consent: "own" }), true);
assert.equal(canRun(f5, { text: "", reference: "a.wav", consent: "own" }), false);
assert.deepEqual(runBody(f5, { text: "hi", reference: "a.wav", consent: "permission", referenceText: " words " }), { model: "f5", text: "hi", reference: "a.wav", consent: "permission", reference_text: "words" });
assert.equal(runBody(m("k", "speech"), { text: "hi", reference: "a.wav", consent: "own" }).reference, undefined);

// the board shows only models that read the line, filtered and sorted
const list = [m("a", "speech", { proof: { audio: "x", match_pct: 80, secs: 9, peak_gib: 1 } }), m("b", "design", { proof: { audio: "x", match_pct: 100, secs: 2, peak_gib: 3 } }), m("c", "listen", { proof: { text: "t" } }), m("d", "speech", { state: "blocked", proof: {} })];
assert.deepEqual(board(list, "all", "match").map((x) => x.id), ["b", "a"]); assert.deepEqual(board(list, "all", "light").map((x) => x.id), ["a", "b"]); assert.deepEqual(board(list, "builtin", "name").map((x) => x.id), ["a"]);
assert.deepEqual(counts(list), { speaking: 2, tools: 1, blocked: 1, files: 3 });

assert.equal(clock(65), "1:05"); assert.equal(bars([0.1, 0.5, 0.2, 0.9], 2).length, 2); assert.deepEqual(bars(null), []);
assert.deepEqual(byLanguage({ x: { lang: "fr" }, y: { lang: "en" } }).map((g) => g[0]), ["en", "fr"]);
console.log("ok");
