"""The tour must speak a step once: its effect can't depend on a callback the parent recreates on every render."""
import pathlib
import re

SRC = (pathlib.Path(__file__).parent.parent / "studio" / "web" / "tour.js").read_text()


def test_effect_that_speaks_depends_on_the_step_only():
    body = SRC[SRC.index("speakRef.current(step.text)"):]
    deps = re.search(r"\}, \[([^\]]*)\]\);", body).group(1)
    assert deps == "step"


def test_speak_goes_through_a_ref():
    assert "speakRef.current = speak" in SRC
    assert not re.search(r"(?<!\.)\bspeak\(step\.text\)", SRC)
