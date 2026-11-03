"""The Pool 51 set: the catalogue Pack Lab shows, the patches it ships and install.py --packs pool51. No network, no git, no ComfyUI: the installer's steps are stubbed."""
import json, re, sys
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import install
from studio import feature_packlab as L

CAT = json.loads((ROOT / "studio" / "pool51_catalogue.json").read_text(encoding="utf-8"))
PATCHES = ROOT / "studio" / "pool51_patches"
RENAMED = {"Fannovel16__comfyui_controlnet_aux": "comfyui_controlnet_aux"}     # other packs import it by this folder name


def test_all_51_sections_are_listed_in_order():
    assert [s["id"] for s in CAT["sections"]] == [f"{i:02d}" for i in range(1, 52)]
    assert all(s["name"] for s in CAT["sections"])
    assert sum(1 for s in CAT["sections"] if s["packs"]) >= 40
    for s in CAT["sections"]:
        if not s["packs"]: assert s.get("empty_why") or s["id"] not in ("05", "15", "18", "23", "32", "41", "42"), s["id"]


def test_every_pack_is_pinned_and_sits_in_one_home_section():
    names = {p["pack"] for p in CAT["packs"]}; homes = [k for s in CAT["sections"] for k in s["packs"]]
    assert sorted(homes) == sorted(names), "each pack is listed once, under its first section"
    for p in CAT["packs"]:
        owner, repo = p["repo"].split("/")
        assert p["pack"] == f"{owner}__{repo}" and p["url"] == f"https://github.com/{p['repo']}", p["pack"]
        assert re.fullmatch(r"[0-9a-f]{40}", p["commit"]), p["pack"]
        assert p["folder"] == RENAMED.get(p["pack"], p["pack"])
        assert p["licence"] and p["node_count"] == len(p["nodes"]) > 0
        assert p["sections"][0] in {s["id"] for s in CAT["sections"]} and p["pack"] in next(s for s in CAT["sections"] if s["id"] == p["sections"][0])["packs"]
    assert len({p["folder"] for p in CAT["packs"]}) == len(CAT["packs"])


def test_no_two_packs_register_the_same_node():
    seen = {}
    for p in CAT["packs"]:
        for n in p["nodes"]:
            assert n not in seen, f"{n}: {seen.get(n)} and {p['pack']}"
            seen[n] = p["pack"]


def test_the_catalogue_names_no_private_folder_or_person():
    text = json.dumps(CAT)
    assert not re.search(r"/mnt/|/home/|~/|nodepack_library|camp-?b|[Ff]ounder|\b8200\b", text)
    assert not re.search(r"\b(is|are|it's) safe\b|safe to install|verified safe", text, re.I) and "not the same as safe" in CAT["about"]


def test_patches_ship_for_exactly_the_patched_packs():
    want = {p["patch"] for p in CAT["packs"] + CAT["optional"] if p["patch"]}
    assert want == {f.name for f in PATCHES.glob("*.diff")} and len(want) >= 4
    for f in PATCHES.glob("*.diff"):
        t = f.read_text(encoding="utf-8")
        assert t.startswith("diff --git a/") and not re.search(r"/mnt/|/home/", t)
        assert all(l.startswith(("--- a/", "--- /dev/null")) for l in t.splitlines() if l.startswith("--- "))
    depth = (PATCHES / "spacepxl__ComfyUI-Depth-Pro.diff").read_text()
    assert '+            depth_model_path = hf_hub_download(repo_id="apple/DepthPro"' in depth and '-                repo_id="spacepxl/ml-depth-pro",' in depth


def test_depth_pro_says_its_weights_are_research_only():
    p = next(p for p in CAT["packs"] if p["pack"] == "spacepxl__ComfyUI-Depth-Pro")
    assert p["weights_licence"] == "Apple ML Research licence, research use only" and "research" in p["licence"]
    assert "p.weights_licence" in (Path(L.__file__).parent / "web" / "packlab.js").read_text() and 'p.get("weights_licence")' in (ROOT / "install.py").read_text()


def test_closed_or_unlicensed_dependencies_stay_out_of_the_open_set():
    opt = {o["pack"]: o for o in CAT["optional"]}; names = {p["pack"] for p in CAT["packs"]}
    assert {"Comfy-Org__ComfyUI_Nvidia_VFX_Nodes", "tritant__ComfyUI_NVIDIA_RTX_VSR_Long_Video"} <= set(opt) and not set(opt) & names
    assert all(o["why"] and re.fullmatch(r"[0-9a-f]{40}", o["commit"]) for o in opt.values())
    assert not any(k in s["packs"] + s["also"] for s in CAT["sections"] for k in opt), "optional packs are not counted in any section"
    assert not any(x.startswith("nvidia-vfx") for p in CAT["packs"] for x in p["pip"])
    cmds = install.pack_commands(CAT, "/x/ComfyUI", "/x/venv/bin/python")
    assert not any(c[0] == "pack" and Path(c[3]).name in opt for c in cmds) and "nvidia-vfx" not in " ".join(map(str, sum(cmds, [])))
    assert "not part of the open edition" in CAT["optional_about"].lower() or "not part of the open edition" in (Path(L.__file__).parent / "web" / "packlab.js").read_text()


def test_pip_lines_are_pinned_and_never_onnxruntime_or_torch():
    for p in CAT["packs"]:
        for x in p["pip"]:
            assert re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.]*", x), (p["pack"], x)
            assert not re.match(r"(onnxruntime|torch|numpy|scipy|pillow)\b", x, re.I), (p["pack"], x)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(L, "_run", lambda *a, **k: pytest.fail("no Docker here"))
    app = FastAPI(); app.include_router(L.router); return TestClient(app)


def test_the_route_lists_the_set_and_does_not_guess_what_is_installed(client, monkeypatch):
    monkeypatch.setattr(L, "_setting", lambda name: "")
    d = client.get("/api/packlab/pool51").json()
    assert len(d["sections"]) == 51 and len(d["packs"]) == len(CAT["packs"]) and d["checked_here"] is False and all(p["installed"] is None for p in d["packs"])


def test_the_route_marks_packs_found_in_this_comfyui(client, monkeypatch, tmp_path):
    (tmp_path / "custom_nodes" / CAT["packs"][0]["folder"]).mkdir(parents=True)
    monkeypatch.setattr(L, "_setting", lambda name: str(tmp_path) if name == "STUDIO_COMFY_ROOT" else "")
    d = client.get("/api/packlab/pool51").json(); got = {p["pack"]: p["installed"] for p in d["packs"]}
    assert d["checked_here"] is True and got[CAT["packs"][0]["pack"]] is True and sum(got.values()) == 1


def test_the_page_shows_the_set():
    js = (Path(L.__file__).parent / "web" / "packlab.js").read_text()
    assert "/api/packlab/pool51" in js and "The installed set, in 51 sections" in js and "<${Pool51}/>" in js


# ---------- install.py --packs pool51
def test_packs_are_off_unless_asked():
    assert install.parse_args([]).packs == "none" and install.parse_args(["--packs", "pool51"]).packs == "pool51"
    with pytest.raises(SystemExit): install.parse_args(["--packs", "everything"])


def test_pack_steps_pin_each_commit_and_its_patch():
    cmds = install.pack_commands(CAT, "/x/ComfyUI", "/x/venv/bin/python"); packs = [c for c in cmds if c[0] == "pack"]
    assert len(packs) == len(CAT["packs"])
    for c, p in zip(packs, CAT["packs"]):
        assert c[1] == p["url"] + ".git" and c[2] == p["commit"] and Path(c[3]) == Path("/x/ComfyUI/custom_nodes") / p["folder"]
        assert (c[4] == "") == (not p["patch"]) and (not c[4] or Path(c[4]).is_file())
    pips = [c for c in cmds if "pip" in c]; flat = [x for c in pips for x in c]
    assert all(x in flat for p in CAT["packs"] for x in p["pip"]) and any("--no-deps" in c for c in pips)
    assert install.step_label(packs[0]).startswith("Node pack ")


def test_build_commands_adds_the_set_only_when_asked():
    profile = {"os": "linux", "gpus": [{"name": "x", "vram_gb": 24.0, "vendor": "nvidia"}], "ram_gb": 64.0, "disk_free_gb": 500.0, "backend": "cuda", "caps": []}
    gm = install.load_json(ROOT / "studio" / "models_manifest.json"); pm = install.to_plan_manifest(gm); ch = install.load_json(ROOT / "channels.json")
    r = install.plan(profile, pm, ["image"])
    assert not [c for c in install.build_commands(r, pm, ch, "stable", "/x", "cuda") if c[0] == "pack"]
    assert len([c for c in install.build_commands(r, pm, ch, "stable", "/x", "cuda", pack_sets=["pool51"]) if c[0] == "pack"]) == len(CAT["packs"])


def test_install_pack_fetches_the_commit_with_hooks_off_then_patches(tmp_path, monkeypatch):
    ran = []; monkeypatch.setattr(install, "already_cloned", lambda d: False)
    assert install.install_pack("https://github.com/o/r.git", "a" * 40, str(tmp_path / "r"), "/p.diff", step=lambda c: ran.append(c) or True)
    assert all(c[:3] == ["git", "-c", "core.hooksPath=" + install.os.devnull] for c in ran)
    assert ["fetch", "--depth", "1", "https://github.com/o/r.git", "a" * 40] == ran[1][-5:] and ran[2][-2:] == ["-q", "FETCH_HEAD"] and ran[3][-3:] == ["apply", "--ignore-whitespace", "/p.diff"]
    ran.clear(); monkeypatch.setattr(install, "already_cloned", lambda d: True)
    assert install.install_pack("u", "c", "d", "", step=lambda c: ran.append(c) or True) and ran == []


def test_a_pack_that_needs_its_submodule_gets_it_and_others_do_not(monkeypatch):
    usdu = next(p for p in CAT["packs"] if p["pack"] == "ssitu__ComfyUI_UltimateSDUpscale")
    assert usdu.get("submodules") is True and sum(1 for p in CAT["packs"] if p.get("submodules")) == 1
    c = next(c for c in install.pack_commands(CAT, "/x/ComfyUI", "py") if c[0] == "pack" and c[3].endswith(usdu["folder"])); assert c[5] is True
    ran = []; monkeypatch.setattr(install, "already_cloned", lambda d: False)
    assert install.install_pack("u", "c", "d", "", True, step=lambda x: ran.append(x) or True)
    assert any("submodule" in x and "--recursive" in x for x in ran) and "protocol.file.allow=never" in ran[3]
    ran.clear(); install.install_pack("u", "c", "d", "", False, step=lambda x: ran.append(x) or True); assert not any("submodule" in x for x in ran)


def test_a_failed_fetch_stops_before_checkout(monkeypatch):
    ran = []; monkeypatch.setattr(install, "already_cloned", lambda d: False)
    assert not install.install_pack("u", "c", "d", "", step=lambda c: ran.append(c) or "fetch" not in c)
    assert not any("checkout" in c for c in ran)


def test_the_windows_installer_passes_packs_through():
    ps1 = (ROOT / "scripts" / "install_windows.ps1").read_text(encoding="utf-8")
    assert '[ValidateSet("none", "pool51")][string]$Packs = "none"' in ps1 and '$installArgs += @("--packs", $Packs)' in ps1
