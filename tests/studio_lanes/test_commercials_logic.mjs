// Rules of the Commercials page, without a browser. tests/test_node_lanes.py runs this in a copy of studio/web.
import assert from "node:assert/strict";
import { pick, segments, runBody, statusWord, heardWord, totals, clock, classWord } from "./commercials_logic.js";

const G = [{ id: "pharma", title: "Pharmaceutical-style parody", pitch: "calm montage", group: "Parody" }, { id: "car", title: "Car launch", pitch: "mountain road", group: "Premium" }, { id: "big", title: "Big Game comedy", pitch: "chaos", group: "Comedy" }];
assert.deepEqual(pick(G, "All", "").map((g) => g.id), ["pharma", "car", "big"]);
assert.deepEqual(pick(G, "Premium", "").map((g) => g.id), ["car"]);
assert.deepEqual(pick(G, "All", "ROAD").map((g) => g.id), ["car"]);
assert.deepEqual(pick(G, "Comedy", "road"), []);

// the bar covers the whole spot, with the parody card last
const s = { length: 30, tone: "calm", writer: "template", beats: [{ id: "a", start: 0, seconds: 10, vo: "one", parts: [{}] }, { id: "b", start: 10, seconds: 13.5, vo: "", parts: [{}, {}] }], end_card: { start: 23.5, seconds: 4, vo: "end" }, parody_card: { start: 27.5, seconds: 2.5 } };
const seg = segments(s);
assert.deepEqual(seg.map((x) => x.kind), ["beat", "beat", "end", "parody"]);
assert.ok(Math.abs(seg.reduce((n, x) => n + x.share, 0) - 1) < 1e-9);
assert.equal(seg[1].parts, 2);
assert.deepEqual(segments(null), []);

// the run body never sends empty fields, and sends the lines as shown
assert.deepEqual(runBody({ id: "pharma" }, { product: " Calmorex ", brand: "" }, s, "kokoro"), { genre: "pharma", brief: { product: "Calmorex" }, length: 30, tone: "calm", engine: "kokoro", vo: ["one", ""], end_vo: "end", writer: "template" });

assert.equal(statusWord("flawed")[1], "warn"); assert.equal(statusWord("nope")[0], "Not run");
assert.match(heardWord({ whisper_match: 91 })[0], /Whisper/); assert.equal(heardWord({ whisper_match: 40 })[1], "bad"); assert.equal(heardWord(null)[0], "Not measured");
assert.deepEqual(totals(G, { spots: [{ status: "passed", shots: [1, 2] }, { status: "flawed", shots: [1] }, { status: "failed" }] }), { genres: 3, rendered: 2, flawed: 1, shots: 3 });
assert.equal(clock(75), "1:15"); assert.equal(classWord("open"), "Open");
console.log("ok");
