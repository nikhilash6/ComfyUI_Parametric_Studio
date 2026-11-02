"""A merge marker inside a template string is still valid JavaScript, so nothing else catches it. Tracked text files must not hold one."""
import re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARK = re.compile(r"^(<{7} |={7}$|>{7} |\|{7} )", re.M)


def test_no_tracked_source_holds_a_merge_marker():
    names = subprocess.run(["git", "ls-files", "*.js", "*.py", "*.html", "*.css"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    if not names: names = [str(p.relative_to(ROOT)) for x in ("js", "py", "html", "css") for p in ROOT.rglob(f"*.{x}") if ".git" not in p.parts]
    bad = [n for n in names if (ROOT / n).is_file() and MARK.search((ROOT / n).read_text(errors="ignore"))]
    assert not bad, bad
