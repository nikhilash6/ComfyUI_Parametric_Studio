import assert from "node:assert";
import { searchStyles, styleLine, cardLine, labelTags, cardTags, isStructured, applyCard, clearCard, SHORT_NOTE } from "./music_styles_logic.js";

const riddim = { id: "studio-dubstep-riddim", label: "Dubstep / Riddim (Hypnotic Loops, Sparse Drums)", cards: 3, bpm: 140, source: "studio", proof: "recipe", aliases: ["trapstep"] };
const trap = { id: "hip-hop-trap", label: "Hip-Hop / Trap", cards: 1, bpm: 140 };
const melodic = { id: "melodic-dubstep-future-bass", label: "Melodic Dubstep / Future Bass", cards: 1, bpm: 171 };
const families = [{ id: "hip-hop-rap", label: "Hip-Hop & Rap", cues: "rap, drill", styles: [trap] }, { id: "club", label: "Club & EDM", cues: "", styles: [riddim, melodic] }];
const ids = (r) => r.map((x) => x.style.id);

// search: nothing typed and no family lists nothing; a family browses; a phrase crosses families; the family filter narrows
assert.deepStrictEqual(searchStyles(families, "  "), []);
assert.deepStrictEqual(ids(searchStyles(families, "", "club")), ["studio-dubstep-riddim", "melodic-dubstep-future-bass"]);
assert.deepStrictEqual(ids(searchStyles(families, "TRAP")), ["hip-hop-trap", "studio-dubstep-riddim"]); // any case, label or alias
assert.deepStrictEqual(ids(searchStyles(families, "trapstep")), ["studio-dubstep-riddim"]);            // an alias
assert.deepStrictEqual(ids(searchStyles(families, "melodic dubstep")), ["melodic-dubstep-future-bass"]); // the phrase wins
assert.deepStrictEqual(ids(searchStyles(families, "bass melodic")), ["melodic-dubstep-future-bass"]);   // falls back to every word
assert.deepStrictEqual(ids(searchStyles(families, "drill")), ["hip-hop-trap"]);                         // the family's cues
assert.deepStrictEqual(ids(searchStyles(families, "hip-hop", "club")), []);

// the mark is on a studio-authored style and card, and never on an official one
assert.ok(styleLine(riddim).includes(SHORT_NOTE) && SHORT_NOTE === "studio-authored, untested");
assert.ok(!styleLine(trap).includes(SHORT_NOTE));
assert.strictEqual(styleLine(trap), "140 BPM");
const cs = { id: "x_0001", bpm: 140, felt_bpm: 70, key: "A minor", gender: "unknown", rap: false, instrumental_led: true, language: "English", source: "studio" };
assert.strictEqual(cardLine(cs), "140 BPM (felt 70) · A minor · instrumental-led · studio-authored, untested");
const co = { id: "y_0001", bpm: 130, key: "E major", gender: "female", rap: false, language: "Mandarin" };
assert.strictEqual(cardLine(co), "130 BPM · E major · female singer · Mandarin");

// tags
assert.deepStrictEqual(labelTags(riddim.label), ["Dubstep", "Riddim", "Hypnotic Loops", "Sparse Drums"]);
assert.deepStrictEqual(labelTags("Hip Hop / Conscious Rap with Electronic and Cinematic influences"), ["Hip Hop", "Conscious Rap with Electronic and Cinematic influences"]);
assert.deepStrictEqual(cardTags(trap, co), ["Hip-Hop", "Trap", "female vocals", "Mandarin lyrics", "E major", "130 BPM"]);
assert.deepStrictEqual(cardTags({ label: "Trap" }, { bpm: 90, key: "", gender: "male", rap: true }), ["Trap", "male rap", "90 BPM"]);
assert.deepStrictEqual(cardTags({ label: "Dubstep" }, cs), ["Dubstep", "instrumental", "A minor", "140 BPM", "half-time feel"]);
assert.deepStrictEqual(cardTags({ label: "X" }, { bpm: null, key: null, gender: null }), ["X"]);

// a card goes in front and the person's tags stay
const tags = ["Trap", "male vocals", "E minor", "140 BPM"];
let r = applyCard("rainy night, sad piano", tags);
assert.strictEqual(r.prompt, "Trap, male vocals, E minor, 140 BPM, rainy night, sad piano");
assert.deepStrictEqual(r.applied, tags);
assert.strictEqual(applyCard("", tags).prompt, "Trap, male vocals, E minor, 140 BPM");

// a new card swaps the old card's tags only
let s = applyCard(r.prompt, ["Bossa Nova", "A major", "120 BPM"], r.applied);
assert.strictEqual(s.prompt, "Bossa Nova, A major, 120 BPM, rainy night, sad piano");
assert.deepStrictEqual(s.applied, ["Bossa Nova", "A major", "120 BPM"]);

// a tag added or edited after picking is theirs and stays; picking twice does not stack
let e = applyCard(r.prompt.replace("140 BPM", "150 BPM") + ", brass", ["Trap", "male vocals", "E minor", "140 BPM"], r.applied);
assert.strictEqual(e.prompt, "Trap, male vocals, E minor, 150 BPM, rainy night, sad piano, brass");
assert.strictEqual(applyCard(r.prompt, tags, r.applied).prompt, r.prompt);

// their own BPM and key beat the card's, and a tag they already have is theirs for good
let o = applyCard("trap, 95 bpm, C minor", tags);
assert.strictEqual(o.prompt, "male vocals, trap, 95 bpm, C minor");
assert.deepStrictEqual(o.applied, ["male vocals"]);
assert.strictEqual(clearCard(o.prompt, o.applied), "trap, 95 bpm, C minor");
// "a minor" in prose is not a key
assert.ok(applyCard("a minor change", ["A major"]).prompt.startsWith("A major"));

// clearing takes out only what the card added, once each
assert.strictEqual(clearCard(r.prompt, r.applied), "rainy night, sad piano");
assert.strictEqual(clearCard("Trap, Trap", ["Trap"]), "Trap");
assert.strictEqual(clearCard("mine", []), "mine");
assert.strictEqual(clearCard("mine"), "mine");

// a full caption is never touched
const cap = "Global Metadata\nBasic Attributes: x\nVocal Details\nArrangement\nPrimary: y, z";
assert.ok(isStructured(cap) && !isStructured("Global Metadata: trap, dark"));
const c = applyCard(cap, tags, ["old"]);
assert.ok(c.structured && c.prompt === cap);
assert.deepStrictEqual(c.applied, ["old"]);
console.log("ok");
