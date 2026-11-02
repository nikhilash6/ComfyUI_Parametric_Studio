"""Every htm element opened in studio/web must be closed: one missing <//> blanked the whole app in the demo.
The check parses each html`...` template with the vendored htm itself (tests/htm_closed_check.mjs), so it sees exactly what the browser sees."""
import pathlib, shutil, subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB = ROOT / "studio" / "web"
CHECK = ROOT / "tests" / "htm_closed_check.mjs"
NODE = shutil.which("node")


def run(*files):
    return subprocess.run([NODE, str(CHECK), str(WEB / "vendor" / "htm.mjs"), *map(str, files)], capture_output=True, text=True, timeout=120)


@pytest.mark.skipif(not NODE, reason="needs node")
def test_components_are_closed():
    files = sorted(f for f in WEB.glob("*.js") if "html`" in f.read_text(errors="replace"))
    assert len(files) > 40, files
    r = run(*files)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(not NODE, reason="needs node")
def test_the_check_catches_an_open_component(tmp_path):
    bad = tmp_path / "bad.js"
    bad.write_text('const re = /`[^`]*`/g;\nexport const A = () => html`<section><${Head} n="06" title="Every node"><p>x ${"a"}</p>\n<${List}/></section>`;\n')
    r = run(bad)
    assert r.returncode == 1 and "bad.js:2: a tag is never closed" in r.stdout, r.stdout + r.stderr
    bad.write_text('export const A = () => html`<section><${Head} n="06">t<//><p>${html`<b>x</b>`}</p></section>`;\n')
    assert run(bad).returncode == 0
    bad.write_text("export const A = () => html`<p>x</p><//>`;\n")
    assert "never opened" in run(bad).stdout
