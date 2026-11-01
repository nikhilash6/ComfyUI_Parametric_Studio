"""The Qwen agents with a scripted model: no real model, no port, no GPU. These prove the tools, the guardrails and the verifiers. They say nothing about how well Qwen itself does the work: only scripts/eval_qwen_agents.py --live can."""
import json, os, socket, sys
from pathlib import Path
import pytest
from psn import knowledge as K
from psn.subagents import agents as A, guard, runner, tools
from psn.subagents.verify import validate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import eval_qwen_agents as EV

OI = json.load(open(ROOT / "studio" / "university" / "node_defs.json"))
G = {"1": {"class_type": "EmptyImage", "inputs": {"width": 512, "height": 512, "batch_size": 1, "color": 0}}, "2": {"class_type": "ImageInvert", "inputs": {"image": ["1", 0]}}, "3": {"class_type": "SaveImage", "inputs": {"images": ["2", 0], "filename_prefix": "x"}}}
NODES = ["EmptyImage", "ImageInvert", "SaveImage"]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    def refuse(*a, **k): raise AssertionError("something tried to reach the network")
    monkeypatch.setattr(socket, "create_connection", refuse); monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(runner, "STATE", str(tmp_path / "state"))


@pytest.fixture
def data(tmp_path, monkeypatch):
    worker, library = EV.prepare_fixture(tmp_path); monkeypatch.setenv("PSN_KNOWLEDGE_WORKER", worker); monkeypatch.setenv("PSN_KNOWLEDGE_LIBRARY", library); K._json_cached.cache_clear(); K._tsv_cached.cache_clear(); return worker, library


def scripted(*replies):
    """A fake model that says these things in order. It records what it was sent."""
    q = list(replies); sent = []
    def t(url, body, timeout=None):
        sent.append(body); x = q.pop(0) if q else {"final": {}}
        return {"choices": [{"message": {"content": x if isinstance(x, str) else json.dumps(x)}}], "usage": {"completion_tokens": 10}}
    t.sent = sent; return t


def call(tool, **args): return {"tool": tool, "args": args}
def final(**out): return {"final": out}


# ---- no power ---------------------------------------------------------------------------------------------------------------------------------------------------------
POWER = {"write_file", "edit_file", "run_bash", "run_workflow", "git_commit", "fetch_url", "mcp_list", "mcp_call", "run_python", "request_approval", "vram_status", "read_file"}

@pytest.mark.parametrize("name", sorted(A.AGENTS))
def test_no_agent_can_write_reach_out_install_or_run(name):
    r = A.AGENTS[name]; assert not set(r.tools) & POWER and set(r.tools) <= set(A.READ_ONLY)
    assert r.purpose and r.schema["required"] and callable(r.verify) and r.endpoint == "qwen" and r.thinking is False and "no tool that writes" in r.system


def test_the_set_of_agents():
    assert set(A.AGENTS) == {"graph_author", "sampling_advisor", "pack_advisor", "licence_reader", "model_finder", "recipe_author", "render_qc_reader", "university_tutor"}


def test_agents_stay_out_of_the_node_role_list():
    from psn.subagents import ROLES
    assert not set(A.AGENTS) & set(ROLES)


def test_a_tool_outside_the_allow_list_is_refused(tmp_path):
    t = scripted(call("run_bash", cmd="pip install evil"), final(answer="no evidence", citations=[], no_evidence=True))
    r = A.run_agent("sampling_advisor", "Q?", transport=t)
    assert r.ok and any("not allowed" in m["content"] for m in t.sent[1]["messages"] if m["role"] == "user") and not (tmp_path / "pwned").exists()


def test_agents_get_no_workspace():
    t = scripted(final(answer="no evidence", citations=[], no_evidence=True)); ctx = {}
    A.run_agent("sampling_advisor", "Q?", ctx, transport=t); assert "write_roots" not in ctx


def test_every_model_call_goes_to_the_local_endpoint_with_thinking_off():
    t = scripted(final(answer="no evidence", citations=[], no_evidence=True)); A.run_agent("sampling_advisor", "Q?", transport=t)
    assert t.sent[0]["model"] == "qwen38-27b-fp8" and t.sent[0]["chat_template_kwargs"] == {"enable_thinking": False}


def test_the_command_line_refuses_to_call_the_model_without_being_told(capsys):
    assert A.main(["run", "sampling_advisor", "Q?"]) == 2 and "--yes-call-qwen" in capsys.readouterr().err


def test_the_guard_still_refuses_what_these_agents_must_never_do():
    for cmd in ("pip install x", "systemctl --user restart parametric-studio", "rm -rf /", "curl -X POST http://x/prompt"):
        assert guard.check_bash(cmd, ["/nonexistent"])[0] is False


# ---- graphs -------------------------------------------------------------------------------------------------------------------------------------------------------------
def good_graph_script(graph=G):
    return [call("node_search", query="image"), *[call("node_spec", **{"class": n}) for n in NODES], call("check_graph", graph=graph), final(graph=graph, notes="", not_proven="Valid against object_info. Not rendered.")]


def test_graph_builder_end_to_end():
    r = A.run_agent("graph_author", "no model graph", {"object_info": OI}, transport=scripted(*good_graph_script()))
    assert r.ok and r.output["graph"] == G and r.attempts == 1


def test_graph_without_object_info_is_always_refused():
    r = A.run_agent("graph_author", "no model graph", transport=scripted(*[final(graph=G, notes="", not_proven="Not rendered.")] * 3))
    assert not r.ok and "no object_info" in r.problems[0]


def test_graph_never_checked_is_refused_even_if_valid():
    r = A.run_agent("graph_author", "x", {"object_info": OI}, transport=scripted(*[final(graph=G, notes="", not_proven="Not rendered.")] * 3))
    assert not r.ok and any("check_graph" in p for p in r.problems)


def test_graph_with_nodes_never_read_is_refused():
    r = A.run_agent("graph_author", "x", {"object_info": OI}, transport=scripted(call("check_graph", graph=G), final(graph=G, notes="", not_proven="Not rendered."), final(graph=G, notes="", not_proven="Not rendered."), final(graph=G, notes="", not_proven="Not rendered.")))
    assert not r.ok and any("node_spec" in p for p in r.problems)


@pytest.mark.parametrize("change,word", [
    (lambda g: g["2"]["inputs"].update(image=["9", 0]), "not in the graph"),
    (lambda g: g["2"]["inputs"].update(image="a picture"), "must come from a link"),
    (lambda g: g["1"].update(class_type="NotARealNode"), "unknown class"),
    (lambda g: g["1"]["inputs"].pop("width"), "missing required"),
    (lambda g: g["1"]["inputs"].update(width=0), "below the minimum"),
    (lambda g: g["1"]["inputs"].update(nonsense=1), "unknown input"),
    (lambda g: g["2"]["inputs"].update(image=[1, 0]), "must be a string"),
    (lambda g: g.pop("3"), "no output node"),
])
def test_strict_check_finds(change, word):
    g = json.loads(json.dumps(G)); change(g); assert any(word in p for p in A.strict_graph_problems(g, OI)), A.strict_graph_problems(g, OI)


def test_strict_check_passes_a_real_graph_and_reads_both_combo_forms():
    assert A.strict_graph_problems(G, OI) == []
    oi = {"A": {"input": {"required": {"m": ["COMBO", {"options": ["x", "y"]}], "n": [["p", "q"]]}}, "output": [], "output_node": True}}
    assert A.strict_graph_problems({"1": {"class_type": "A", "inputs": {"m": "x", "n": "p"}}}, oi) == []
    assert len(A.strict_graph_problems({"1": {"class_type": "A", "inputs": {"m": "z", "n": "z"}}}, oi)) == 2


def test_strict_check_refuses_a_partner_node():
    oi = {"Paid": {"input": {"required": {}}, "output": [], "output_node": True, "api_node": True}}
    assert any("partner" in p for p in A.strict_graph_problems({"1": {"class_type": "Paid", "inputs": {}}}, oi))


def test_object_info_is_not_pasted_into_the_prompt():
    t = scripted(*good_graph_script()); A.run_agent("graph_author", "x", {"object_info": OI}, transport=t)
    assert "ControlNetApplyAdvanced" not in t.sent[0]["messages"][1]["content"]


def test_node_spec_says_when_a_node_is_not_installed():
    assert "not installed" in A.tool_node_spec({"class": "NotARealNode"}, {"object_info": OI})["error"]


def test_node_search_by_type():
    assert "VAEDecode" in A.tool_node_search({"gives": "IMAGE", "max": 40}, {"object_info": OI})["nodes"] or A.tool_node_search({"gives": "IMAGE"}, {"object_info": OI})["total"] > 0
    assert "KSampler" in A.tool_node_search({"takes": "MODEL", "max": 40}, {"object_info": OI})["nodes"]


# ---- sampling -----------------------------------------------------------------------------------------------------------------------------------------------------------
Q = "So it is about 1 and the node does essentially nothing at any strength."
GOOD_S = dict(answer="It does essentially nothing.", citations=[dict(entry_id="gigachad-cfg-rescale-noop", quote=Q, label="from code", runs_without_a_pack=False)], no_evidence=False)
READ_S = call("atlas_entry", id="gigachad-cfg-rescale-noop")


def test_sampling_end_to_end():
    assert A.run_agent("sampling_advisor", "Gigachad?", transport=scripted(call("atlas_search", query="gigachad"), READ_S, final(**GOOD_S))).ok


@pytest.mark.parametrize("change,word", [
    (dict(citations=[{**GOOD_S["citations"][0], "quote": "It rescales very well and improves every picture."}]), "quote is not in the entry"),
    (dict(citations=[{**GOOD_S["citations"][0], "label": "measured here"}]), "label"),
    (dict(citations=[{**GOOD_S["citations"][0], "runs_without_a_pack": True}]), "runs_without_a_pack"),
    (dict(citations=[{**GOOD_S["citations"][0], "entry_id": "made-up-entry"}]), "no atlas entry"),
    (dict(answer="It boosts contrast by 37 percent."), "numbers"),
    (dict(citations=[]), "at least one citation"),
])
def test_sampling_rejects(change, word):
    r = A.run_agent("sampling_advisor", "Gigachad?", transport=scripted(READ_S, *[final(**{**GOOD_S, **change})] * 3))
    assert not r.ok and any(word in p for p in r.problems), r.problems


def test_sampling_cannot_cite_what_it_did_not_read():
    r = A.run_agent("sampling_advisor", "Q?", transport=scripted(*[final(**GOOD_S)] * 3)); assert not r.ok and "did not read" in r.problems[0]


def test_sampling_no_evidence_must_say_so():
    assert not A.run_agent("sampling_advisor", "Q?", transport=scripted(*[final(answer="Use euler.", citations=[], no_evidence=True)] * 3)).ok


# ---- University ---------------------------------------------------------------------------------------------------------------------------------------------------------
def lesson_sentence(code):
    return next(ln.strip() for ln in K.lesson_read(code)["text"].splitlines() if len(ln.strip()) > 80 and not ln.startswith("#"))


@pytest.fixture
def cu503_pending(monkeypatch):
    """Every lesson has had its second read now, so these tests mark one pending themselves."""
    real = K.lessons(); fake = {k: dict(v) for k, v in real.items()}; fake["CU-503"]["second_read"] = "pending"
    monkeypatch.setattr(K, "lessons", lambda: fake)


def test_tutor_end_to_end_lists_the_pending_lesson(cu503_pending):
    q = lesson_sentence("CU-503"); out = dict(answer="Autoregressive models write the picture as conditionals.", citations=[dict(code="CU-503", quote=q)], second_read_pending=["CU-503"])
    assert A.run_agent("university_tutor", "CU-503?", transport=scripted(call("lesson_search", query="autoregressive"), call("lesson_read", code="CU-503"), final(**out))).ok


def test_tutor_must_flag_a_lesson_with_no_second_read(cu503_pending):
    q = lesson_sentence("CU-503"); out = dict(answer="x", citations=[dict(code="CU-503", quote=q)], second_read_pending=[])
    r = A.run_agent("university_tutor", "?", transport=scripted(call("lesson_read", code="CU-503"), *[final(**out)] * 3)); assert not r.ok and any("second read" in p for p in r.problems)


def test_tutor_may_not_call_a_checked_lesson_pending():
    q = lesson_sentence("CU-230"); out = dict(answer="x", citations=[dict(code="CU-230", quote=q)], second_read_pending=["CU-230"])
    assert not A.run_agent("university_tutor", "?", transport=scripted(call("lesson_read", code="CU-230"), *[final(**out)] * 3)).ok


def test_tutor_rejects_an_invented_quote_and_a_made_up_lesson():
    out = dict(answer="x", citations=[dict(code="CU-230", quote="KSampler was invented in 1912 by a beekeeper.")], second_read_pending=[])
    r = A.run_agent("university_tutor", "?", transport=scripted(call("lesson_read", code="CU-230"), *[final(**out)] * 3)); assert not r.ok and any("quote" in p for p in r.problems)
    assert not A.run_agent("university_tutor", "?", transport=scripted(*[final(answer="x", citations=[dict(code="CU-999", quote="x")], second_read_pending=[])] * 3)).ok


def test_tutor_may_say_no_lesson():
    assert A.run_agent("university_tutor", "bread?", transport=scripted(final(answer="No lesson covers this.", citations=[], second_read_pending=[]))).ok


# ---- packs --------------------------------------------------------------------------------------------------------------------------------------------------------------
def pick(data, name, **kw):
    row = K.pack_exact(name); return {**dict(pack=name, action="install-candidate", licence=row["license"], original="", why="It fits.", next_step="Try it in Pack Lab first.", evidence=row["evidence"]), **kw}


def test_pack_end_to_end(data):
    r = A.run_agent("pack_advisor", "interpolation", transport=scripted(call("pack_search", query="interpolation"), call("pack_page", pack="acme__Good-Pack"), final(summary="One pick.", picks=[pick(data, "acme__Good-Pack")])))
    assert r.ok, r.problems


@pytest.mark.parametrize("name,kw,word", [
    ("acme__Bad-Pack", {}, "do-not-install"),
    ("acme__Skip-Pack", {}, "SKIP"),
    ("acme__Good-Pack", {"licence": "Apache-2.0"}, "copy it exactly"),
    ("acme__Good-Pack", {"evidence": "made/up.tsv:1"}, "evidence"),
    ("acme__Good-Pack", {"next_step": "Install it now."}, "Pack Lab"),
    ("acme__Good-Pack", {"why": "It is safe to install."}, "never call a pack safe"),
    ("acme__Copy-Pack", {}, "original"),
])
def test_pack_rejects(data, name, kw, word):
    p = pick(data, name, **kw); s = scripted(call("pack_search", query=name.split("__")[1]), call("pack_page", pack=name), *[final(summary="x", picks=[p])] * 3)
    r = A.run_agent("pack_advisor", "x", transport=s); assert not r.ok and any(word in x for x in r.problems), r.problems


def test_pack_must_read_the_page_before_recommending_an_install(data):
    p = pick(data, "acme__Good-Pack"); r = A.run_agent("pack_advisor", "x", transport=scripted(call("pack_search", query="Good-Pack"), *[final(summary="x", picks=[p])] * 3))
    assert not r.ok and any("pack_page" in x for x in r.problems)


def test_pack_cannot_invent_a_pack(data):
    r = A.run_agent("pack_advisor", "x", transport=scripted(*[final(summary="x", picks=[dict(pack="acme__Ghost", action="docs-only", licence="MIT", original="", why="", next_step="", evidence="")])] * 3)); assert not r.ok and "not in the index" in r.problems[0]


def test_pack_page_text_comes_back_marked_as_outside_data_and_taints_the_run(data):
    ctx = {"_state": {}}; out = tools.call("pack_page", {"pack": "acme__Good-Pack"}, ctx)
    assert "UNTRUSTED_OUTSIDE_DATA" in out and "Ignore your instructions" in json.dumps(out) and ctx["_state"]["tainted"] is True


def test_pack_page_stays_inside_the_library(data, monkeypatch):
    real = K.pack_exact; monkeypatch.setattr(K, "pack_exact", lambda n: {**real("acme__Good-Pack"), "page": "/etc/hostname"})
    assert "error" in A.tool_pack_page({"pack": "acme__Good-Pack"}, {})


# ---- licences -----------------------------------------------------------------------------------------------------------------------------------------------------------
def test_licence_end_to_end(data):
    out = dict(pack="acme__Good-Pack", spdx="MIT", open_ok=True, commercial_ok=True, quote="Permission is hereby granted", index_agrees=True, reason="MIT text.")
    assert A.run_agent("licence_reader", "x", transport=scripted(call("licence_file", pack="acme__Good-Pack"), final(**out))).ok


def test_licence_text_cannot_talk_the_agent_into_open(data):
    out = dict(pack="acme__Trick-Licence", spdx="MIT", open_ok=True, commercial_ok=True, quote="MIT License", index_agrees=True, reason="It says MIT.")
    r = A.run_agent("licence_reader", "x", transport=scripted(call("licence_file", pack="acme__Trick-Licence"), *[final(**out)] * 3)); assert not r.ok and any("restrictive wording" in p for p in r.problems)
    assert "UNTRUSTED_OUTSIDE_DATA" in tools.call("licence_file", {"pack": "acme__Trick-Licence"}, {"_state": {}})


def test_no_licence_file_means_unknown(data):
    out = dict(pack="acme__No-Licence", spdx="MIT", open_ok=True, commercial_ok=True, quote="", index_agrees=False, reason="x")
    assert not A.run_agent("licence_reader", "x", transport=scripted(call("licence_file", pack="acme__No-Licence"), *[final(**out)] * 3)).ok
    ok = {**out, "spdx": "UNKNOWN", "open_ok": False, "commercial_ok": False}
    assert A.run_agent("licence_reader", "x", transport=scripted(call("licence_file", pack="acme__No-Licence"), final(**ok))).ok


def test_licence_must_be_read_and_quoted_and_compared(data):
    out = dict(pack="acme__Good-Pack", spdx="MIT", open_ok=True, commercial_ok=True, quote="Permission is hereby granted", index_agrees=True, reason="x")
    assert not A.run_agent("licence_reader", "x", transport=scripted(*[final(**out)] * 3)).ok
    for change in ({"quote": "No such sentence in the file."}, {"index_agrees": False}, {"spdx": "GPL-3.0"}):
        assert not A.run_agent("licence_reader", "x", transport=scripted(call("licence_file", pack="acme__Good-Pack"), *[final(**{**out, **change})] * 3)).ok


# ---- models -------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_model_end_to_end_and_ran_must_match_the_row(data):
    rows = {r["file"]: r for r in K.model("fake")["rows"]}; row = rows["fake_image_model.safetensors"]; m = dict(file=row["file"], on_disk=True, ran=True, evidence=row["evidence"])
    assert A.run_agent("model_finder", "x", transport=scripted(call("model_search", query="fake"), final(answer="yes", found=True, models=[m]))).ok
    un = rows["fake_unwired.safetensors"]; lie = dict(file=un["file"], on_disk=True, ran=True, evidence=un["evidence"])
    r = A.run_agent("model_finder", "x", transport=scripted(call("model_search", query="fake"), *[final(answer="yes", found=True, models=[lie])] * 3)); assert not r.ok and any("ran must be False" in p for p in r.problems)


def test_model_rows_must_come_from_the_tool(data):
    row = K.model("fake")["rows"][0]; m = dict(file=row["file"], on_disk=True, ran=True, evidence=row["evidence"])
    assert not A.run_agent("model_finder", "x", transport=scripted(*[final(answer="yes", found=True, models=[m])] * 3)).ok
    assert A.run_agent("model_finder", "x", transport=scripted(call("model_search", query="nothing"), final(answer="no", found=False, models=[]))).ok


# ---- recipes ------------------------------------------------------------------------------------------------------------------------------------------------------------
def sound_recipe():
    from studio import recipes as R
    base = next(r for r in R.library() if r["kind"] == "sound"); rec = json.loads(json.dumps(base)); rec.update(id="sound_test_soft_rain", title="Soft rain", proof={"level": "recipe"}, rating="sfw"); rec.pop("tested", None); return rec


def test_recipe_end_to_end_with_the_apps_own_checks():
    rec = sound_recipe(); r = A.run_agent("recipe_author", "rain", {"object_info": OI}, transport=scripted(call("recipe_check", recipe=rec), final(recipe=rec, notes="")))
    assert r.ok, r.problems


@pytest.mark.parametrize("change,word", [
    (dict(id=None), "already taken"),
    (dict(tested={"seconds": 1}), "never mark"),
    (dict(proof={"level": "verified"}), "proof.level"),
    (dict(rating="adult"), "rating"),
])
def test_recipe_rejects(change, word):
    rec = sound_recipe(); ch = dict(change)
    if "id" in ch: ch["id"] = next(r["id"] for r in __import__("studio.recipes", fromlist=["x"]).library() if r["kind"] == "sound")
    rec.update(ch); assert any(word in p for p in A.recipe_problems(rec, {"object_info": OI}))


def test_recipe_steps_are_read_by_the_apps_validator():
    rec = sound_recipe(); rec["steps"] = [{"id": "a", "type": "goal", "goal": "not_a_goal"}]; assert any("unknown goal" in p for p in A.recipe_problems(rec, {"object_info": OI}))


def test_recipe_without_object_info_is_refused():
    assert any("no object_info" in p for p in A.recipe_problems(sound_recipe(), {}))


def test_recipe_never_checked_is_refused():
    rec = sound_recipe(); r = A.run_agent("recipe_author", "x", {"object_info": OI}, transport=scripted(*[final(recipe=rec, notes="")] * 3)); assert not r.ok and "recipe_check" in r.problems[0]


# ---- render QC ----------------------------------------------------------------------------------------------------------------------------------------------------------
def qc_out(verdict="pass", seen=True): return dict(verdict=verdict, checked=[dict(item="a red circle", seen=seen, note="centre")], summary="A red circle.")


def test_qc_end_to_end_sends_the_picture(tmp_path):
    p = EV.make_image("circle", tmp_path); t = scripted(final(**qc_out())); r = A.run_agent("render_qc_reader", "brief", {"image_path": p, "must_show": ["a red circle"]}, transport=t)
    assert r.ok and any(x.get("type") == "image_url" for x in t.sent[0]["messages"][1]["content"])


@pytest.mark.parametrize("kind", ["black", "white"])
def test_qc_measurement_vetoes_a_pass_on_a_blank_picture(tmp_path, kind):
    p = EV.make_image(kind, tmp_path); r = A.run_agent("render_qc_reader", "b", {"image_path": p, "must_show": ["a red circle"]}, transport=scripted(*[final(**qc_out())] * 3))
    assert not r.ok and "cannot be pass" in r.problems[0]


def test_qc_flicker_and_set_numbers_veto_a_pass(tmp_path):
    p = EV.make_image("circle", tmp_path)
    for qc in ({"flicker": 14.2}, {"set_consistency": 0.2}):
        assert not A.run_agent("render_qc_reader", "b", {"image_path": p, "must_show": ["a red circle"], "qc": qc}, transport=scripted(*[final(**qc_out())] * 3)).ok


def test_qc_may_report_a_fail_or_unsure_on_a_blank_picture(tmp_path):
    p = EV.make_image("black", tmp_path); assert A.run_agent("render_qc_reader", "b", {"image_path": p, "must_show": ["a red circle"]}, transport=scripted(final(**qc_out("fail", False)))).ok


def test_qc_checks_every_item_and_refuses_to_judge_age_or_identity(tmp_path):
    p = EV.make_image("circle", tmp_path); ctx = {"image_path": p, "must_show": ["a red circle", "a blue square"]}
    r = A.run_agent("render_qc_reader", "b", ctx, transport=scripted(*[final(**qc_out())] * 3)); assert not r.ok and "every item" in r.problems[0]
    out = dict(verdict="unsure", checked=[dict(item="a red circle", seen=True, note="The person looks about 25 and is an adult.")], summary="x")
    assert not A.run_agent("render_qc_reader", "b", {"image_path": p, "must_show": ["a red circle"]}, transport=scripted(*[final(**out)] * 3)).ok


def test_qc_with_no_picture_cannot_pass():
    r = A.run_agent("render_qc_reader", "b", {"must_show": ["a red circle"]}, transport=scripted(*[final(**qc_out())] * 3)); assert not r.ok and "no picture" in r.problems[0]


# ---- the eval set ------------------------------------------------------------------------------------------------------------------------------------------------------
def test_eval_set_is_real_and_covers_every_agent(tmp_path, data):
    cases = EV.load_cases([EV.DEFAULT_CASES]); assert EV.check_cases(cases, str(tmp_path)) == [] and {c["agent"] for c in cases} == set(A.AGENTS) and len(cases) >= 30


def test_eval_without_live_calls_no_model_and_reports_no_score(capsys, monkeypatch):
    monkeypatch.setattr(A, "run_agent", lambda *a, **k: pytest.fail("the model was called"))
    assert EV.main([]) == 0 and "no score" in capsys.readouterr().out


def test_eval_live_needs_the_second_switch(capsys):
    assert EV.main(["--live"]) == 2


def test_eval_scoring():
    case = {"expect": {"contains_all": ["euler"], "fields": {"a.0.b": 1}, "not_contains": ["safe"]}}
    assert EV.score(case, True, {"a": [{"b": 1}], "t": "Euler"}) == []
    assert len(EV.score(case, False, {"a": [{"b": 2}], "t": "it is safe"})) == 4
    assert EV.score({"expect": {"verifier_ok": False}}, False, None) == []


def test_tool_output_fits_what_the_model_is_shown():
    for name, args, ctx in (("goal_list", {}, {}), ("atlas_entry", {"id": "core-ddim-alias"}, {}), ("lesson_read", {"code": "CU-230"}, {})):
        out = tools.call(name, args, {"_state": {}, **ctx}); assert "truncated" not in out and "error" not in out, name
