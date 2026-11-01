"""The Crew page: every tier and the way to ask stays."""
from pathlib import Path

EX = (Path(__file__).resolve().parents[1] / "studio" / "web" / "extras.js").read_text()


def test_crew_keeps_its_parts():
    body = EX[EX.index("export function Crew()"):EX.index("/* ---------- Site builder ---------- */")]
    for word in ("crew-talk", "question for the crew", "show the exact quote", "Model specialists", "Shared experts", "Fine-tuning experts", "setTier"):
        assert word in body, word
