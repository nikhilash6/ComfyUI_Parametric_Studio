// Parses every html`...` template in the given .js files with the vendored htm itself and reports any element left open
// (htm then nests the rest of the page inside it and Preact can crash with "insertBefore parameter 1 is not of type Node")
// or closed one time too many. Usage: node htm_closed_check.mjs <htm.mjs> <file.js>...   Prints one line per problem; exit 1 if any.
import fs from "node:fs";

const [htmPath, ...files] = process.argv.slice(2);
// htm's parser returns its current frame at the end; at the root that frame's parent slot is 0, so anything else means a tag was never closed.
const src = fs.readFileSync(htmPath, "utf8");
const hook = "return p(),h}(s)";
if (!src.includes(hook)) { console.log(`htm build changed, update the hook in ${process.argv[1]}`); process.exit(2); }
const htm = (await import("data:text/javascript," + encodeURIComponent(src.replace(hook, "return p(),globalThis.__htmEnd(h),h}(s)")))).default;
let open = false;
globalThis.__htmEnd = (frame) => { open = frame[0] !== 0; };
const html = htm.bind((type, props, ...children) => ({ type, props, children }));

const REGEX_AFTER = new Set(["return", "typeof", "instanceof", "in", "of", "new", "delete", "void", "throw", "case", "do", "else", "yield", "await"]);

// A small JS lexer: enough to find tagged templates, skipping strings, comments and regex literals.
function scan(s) {
  const found = []; let i = 0;
  const line = (k) => s.slice(0, k).split("\n").length;
  const skipString = (q) => { i++; while (i < s.length && s[i] !== q) { if (s[i] === "\\") i++; i++; } i++; };
  const skipRegex = () => { i++; let cls = false; while (i < s.length) { const c = s[i]; if (c === "\\") i++; else if (c === "[") cls = true; else if (c === "]") cls = false; else if (c === "/" && !cls) break; else if (c === "\n") throw new Error(`unterminated regex at line ${line(i)}`); i++; } i++; while (/[a-z]/i.test(s[i] || "")) i++; };
  function template(tag) {
    const start = i, strings = []; let cur = ""; i++;
    while (i < s.length) {
      const c = s[i];
      if (c === "\\") { cur += c + s[i + 1]; i += 2; continue; }
      if (c === "`") { i++; strings.push(cur); if (tag) found.push({ tag, strings, line: line(start) }); return; }
      if (c === "$" && s[i + 1] === "{") { strings.push(cur); cur = ""; i += 2; code(true); i++; continue; }
      cur += c; i++;
    }
    throw new Error(`unterminated template at line ${line(start)}`);
  }
  function code(inExpr) {
    let depth = 0, prev = null;
    while (i < s.length) {
      const c = s[i];
      if (/\s/.test(c)) { i++; continue; }
      if (c === "/" && s[i + 1] === "/") { while (i < s.length && s[i] !== "\n") i++; continue; }
      if (c === "/" && s[i + 1] === "*") { i = s.indexOf("*/", i + 2); if (i < 0) i = s.length; else i += 2; continue; }
      if (c === "'" || c === '"') { skipString(c); prev = "str"; continue; }
      if (c === "`") { template(prev && /^[\w$.]+$/.test(prev) ? prev.split(".").pop() : null); prev = "str"; continue; }
      if (c === "/") { if (prev === null || (!/^[\w$.]+$/.test(prev) && prev !== ")" && prev !== "]" && prev !== "str") || REGEX_AFTER.has(prev)) { skipRegex(); prev = "str"; } else { i++; prev = "/"; } continue; }
      if (/[\w$]/.test(c)) { const m = /^[\w$]+(?:\s*\.\s*[\w$]+)*/.exec(s.slice(i, i + 200)); prev = m[0].replace(/\s+/g, ""); i += m[0].length; continue; }
      if (c === "{") depth++;
      if (c === "}") { if (depth === 0 && inExpr) return; depth--; }
      prev = c; i++;
    }
    if (inExpr) throw new Error("unterminated ${ } expression");
  }
  code(false);
  return found;
}

const cook = (raw) => (0, eval)("`" + raw + "`");
let bad = 0;
for (const f of files) {
  let temps;
  try { temps = scan(fs.readFileSync(f, "utf8")); } catch (e) { console.log(`${f}: could not read: ${e.message}`); bad++; continue; }
  for (const t of temps.filter((x) => x.tag === "html")) {
    const strings = Object.assign(t.strings.map(cook), { raw: t.strings });
    open = false;
    try { html(strings, ...strings.slice(1).map(() => "x")); } catch (e) { console.log(`${f}:${t.line}: a tag is closed that was never opened (${e.message})`); bad++; continue; }
    if (open) { console.log(`${f}:${t.line}: a tag is never closed`); bad++; }
  }
}
process.exit(bad ? 1 : 0);
