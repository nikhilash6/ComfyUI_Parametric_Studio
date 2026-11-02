"""Licences a person must see: every family and goal has one, any licence that limits use says so on the tile and the page, and MODELS.md lists them.
Pure data checks: no ports, no downloads."""
import json, re
from pathlib import Path
import pytest
from studio import families_api as F, goals, licences as L, train_bases, tryon

ROOT = Path(__file__).resolve().parent.parent
STATUS = json.loads((ROOT / "studio" / "family_status.json").read_text(encoding="utf-8"))["families"]
MODELS = (ROOT / "MODELS.md").read_text(encoding="utf-8")
LIMIT_WORDS = (L.NC, L.RO, L.UNVERIFIED, "Excludes ", "Revenue cap US$", "User cap ", "Commercial use needs registration")
#: words in a licence line that mean it limits use; such a line must carry a limit
RESTRICTIVE = re.compile(r"non-commercial|research|revenue|US\$|exclude|does not apply|monthly users|visits a month|no licence|not found|unverified|names no licence", re.I)


def test_every_family_has_a_licence_entry_and_the_status_file_agrees():
    assert set(STATUS) == set(L.FAMILIES)
    for f, v in STATUS.items(): assert v["licence"] == L.FAMILIES[f]["licence"], f


@pytest.mark.parametrize("name,entry", sorted({**L.FAMILIES, **L.GOAL_FAMILIES}.items()))
def test_a_licence_that_limits_use_says_so(name, entry):
    assert entry["licence"]
    for lim in entry["limits"]: assert lim.startswith(LIMIT_WORDS), (name, lim)
    if RESTRICTIVE.search(entry["licence"]) and "commercial use allowed" not in entry["licence"]: assert entry["limits"], name
    if entry["limits"] and entry["limits"] != (L.UNVERIFIED,): assert entry["url"].startswith("https://"), name


def test_the_founders_calls_are_labelled():
    assert L.FAMILIES["Krea2"]["limits"] == (L.cap("1M"),) and "1,000,000" in L.FAMILIES["Krea2"]["licence"]
    assert L.EX_US_EU_UK_KR in L.FAMILIES["MiniMax-H3"]["limits"]
    assert L.INSIGHTFACE["limits"] == (L.NC,) and L.FAMILIES["LivePortrait"]["limits"][0].startswith(L.NC)
    assert all(not m["commercial"] for m in tryon.METHODS if m.get("family") in ("Flux.2", "Qwen-Image-2.1"))
    assert "1,000,000" in train_bases.LICENCES["krea2"]["note"]


@pytest.mark.parametrize("limits,word", [((), ""), ((L.NC,), "Non-commercial"), ((L.RO + " (Qwen-Image 2.1)",), "Research only in part"), ((L.EX_US_EU_UK_KR, L.cap("20M")), "Territory limits"), ((L.cap("1M"),), "Revenue cap")])
def test_badge_words(limits, word):
    assert L.badge(limits) == word


def test_goal_tiles_carry_the_limits_and_a_link():
    assert goals.GOALS["image"]["license_limits"] == [] and goals.GOALS["anime"]["license_badge"] == L.NC
    assert goals.GOALS["krea2"]["license_badge"] == "Revenue cap" and goals.GOALS["recast"]["license_badge"] == "Territory limits"
    assert all(g["license_url"] for g in goals.GOALS.values())


def test_the_families_api_sends_limits_with_the_licence():
    row = F._licence("Qwen-Image-2.1", STATUS["Qwen-Image-2.1"])
    assert row["licence_limits"] == [L.RO + " (Qwen-Image 2.1)"] and row["licence_badge"] == "Research only in part" and row["licence_url"].startswith("https://")
    assert F._licence("Not-A-Family", {"licence": None})["licence_limits"] == [L.UNVERIFIED]


def test_the_ui_shows_limits_where_a_model_is_picked():
    web = ROOT / "studio" / "web"
    show, app, fam = (web / "showcase.js").read_text(), (web / "app.js").read_text(), (web / "families.js").read_text()
    assert "export function LicBadge" in show and "<${LicBadge} g=${g}/>" in show and "<${LicBadge} g=${g}/>" in (web / "models_ui.js").read_text()
    assert "<${LicenceLine} g=${g}/>" in app and "f.licence_limits" in fam and "f.licence_badge" in fam
    assert "research-only licence" in (web / "virtualset.js").read_text() and "InsightFace buffalo_l" in (web / "worldkit.js").read_text()
    assert (web / "shotboard.js").read_text().count("excludes the US, EU, UK and South Korea") == 3


def test_models_md_names_every_goal_family_and_every_limited_family():
    for fam in L.GOAL_FAMILIES: assert fam in MODELS, fam
    for f, e in L.FAMILIES.items():
        assert f"| {f} |" in MODELS, f
        for lim in e["limits"]: assert lim in MODELS, (f, lim)
    assert "No partner nodes or closed-source APIs, open-weights models only." in MODELS
