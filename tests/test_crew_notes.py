"""The crew's state notes: labelled, citing what exists, and what a specialist can really answer from. No model here: a scripted chat stands in."""
import asyncio, json, os, re, subprocess, sys
from pathlib import Path
import pytest
from studio import crew, crew_api as C

ROOT = Path(__file__).resolve().parents[1]; NOTES = ROOT / "studio" / "crew_notes"
sys.path.insert(0, str(ROOT / "scripts"))
import check_crew_notes as CK

STUDIO = {"virtual-set": "01-Virtual-Set", "world-kit": "02-World-Kit", "characters": "03-Characters", "train": "04-Train", "sampling-lab": "05-Sampling-Lab", "res4lyf": "06-RES4LYF", "recipes": "07-Recipes", "designers": "08-Designers", "university": "09-University"}


def members(): return {m["id"]: m for m in crew.roster(str(NOTES))}


def test_every_label_and_citation_in_the_notes_is_real():
    probs = [p for f in CK.note_files(ROOT) for p in CK.check_file(ROOT, f)]; assert probs == [], probs[:20]


def test_checker_catches_what_it_should(tmp_path):
    (tmp_path / "real.py").write_text("a\nb\n"); note = tmp_path / "x.md"
    for text, word in (("A fact with no label.", "no proof label"), ("A fact. [code: nope.py:1]", "not in the repo"), ("A fact. [code: real.py:9]", "has 2 lines"), ("A fact. [code]", "names no file"), ("Runs on port :8200. [inference]", "private"), ("A TODO here. [inference]", "placeholder")):
        note.write_text(text); assert any(word in p for p in CK.check_file(tmp_path, note)), text
    note.write_text("# Heading\n\nA fact. [code: real.py:2]\n\nSaid so. [claim: author]\n\nOurs. [inference]\n"); assert CK.check_file(tmp_path, note) == []


def test_each_studio_specialist_has_notes_a_name_and_a_voice():
    m = members()
    for sid in STUDIO:
        assert m[sid]["tier"] == "studio" and m[sid]["has_dossier"] and len(m[sid]["files"]) >= 2 and m[sid]["name"] == crew.STUDIO_NAMES[sid] and sid in crew.CHARACTERS and crew.hello(sid)


def test_no_existing_member_changed_name_when_the_studio_tier_came():
    m = members()
    fixed = {"3d-trellis-hunyuan3d-sam3d-mesh": "Professor Latent", "anima": "Captain Checkpoint", "text-encoders": crew.NAMES[31], "vae": crew.NAMES[32], "vision": crew.NAMES[33], "lora": crew.NAMES[34], "controlnet": crew.NAMES[35], "upscaler": crew.NAMES[36]}
    assert {k: m[k]["name"] for k in fixed} == fixed and m["master"]["name"] == "Comfy Prime"


def test_the_six_part_members_have_their_own_notes_and_prime_holds_them():
    m = members(); prime = set(m["master"]["files"])
    for pid in ("text-encoders", "vae", "vision", "lora", "controlnet", "upscaler"):
        assert m[pid]["tier"] in ("secondary", "tertiary") and m[pid]["has_dossier"] and m[pid]["files"], pid
        assert all(f.endswith(".md") and f"parts{os.sep}{pid}{os.sep}" in f for f in m[pid]["files"]) and set(m[pid]["files"]) <= prime, pid


def test_prime_holds_every_note_but_all_families_is_nobody_else():
    m = members(); prime = set(m["master"]["files"])
    assert all(set(m[s]["files"]) <= prime for s in STUDIO) and any("_all-families" in f for f in prime) and not any(k.startswith("all-families") for k in m)


@pytest.mark.parametrize("question,who", [
    ("How do I export from World Kit?", "world-kit"), ("What does the virtual set page do?", "virtual-set"), ("Which recipes have rendered?", "recipes"),
    ("How do I train a LoRA here?", "train"), ("What does the Sampling Lab show?", "sampling-lab"), ("Why does the RES4LYF page need a licence note?", "res4lyf"),
    ("Who are the designers?", "designers"), ("Which University lesson covers CLIP?", "university"), ("Can I save a character?", "characters"),
    ("How do I set the guidance scale on MiniMax-H3?", "minimax-h3"), ("Is AnimateDiff wired up?", "cogvideox-mochi-cosmos-svd-animatediff-older-video"), ("Which Trellis model is best?", "3d-trellis-hunyuan3d-sam3d-mesh"),
    ("Tell me a joke", "master"),
])
def test_routing(question, who):
    assert crew.route(question, crew.roster(str(NOTES))) == who


def reply(answer, *quotes): return lambda messages: json.dumps({"answer": answer, "quotes": [{"file": "x", "quote": q} for q in quotes]})


def first_sentence(path):
    for para in Path(path).read_text().split("\n\n"):
        if not para.startswith("#") and len(para) > 60: return re.split(r"(?<=[.!?])\s", para.strip())[0]
    raise AssertionError(path)


@pytest.mark.parametrize("sid", sorted(STUDIO))
def test_a_real_quote_comes_back_with_a_real_file(sid):
    m = members()[sid]; path = next(f for f in m["files"] if f.endswith("PLAYBOOK.md")); s = first_sentence(path); r = crew.ask(m, s, reply("From my notes.", s))
    assert r["supported"] and r["quotes"], r
    label = r["quotes"][0]["file"]; assert label.endswith(".md") and any(f.endswith(label) for f in m["files"])


def test_family_state_is_quoted_from_its_own_file():
    m = members()["minimax-h3"]; r = crew.ask(m, "last recorded render h3 template", reply("It ran.", "MiniMax-H3 last recorded render: template h3_t2v_api"))
    assert r["supported"] and r["quotes"][0]["file"].endswith("STATE.md")


def test_invented_quote_and_invented_number_are_refused():
    m = members()["minimax-h3"]
    assert not crew.ask(m, "last recorded render h3", reply("It ran.", "H3 renders a feature film in one second on a phone."))["supported"]
    r = crew.ask(m, "last recorded render h3 template", reply("It took 9999 seconds.", "MiniMax-H3 last recorded render: template h3_t2v_api"))
    assert not r["supported"] and "can't back" in r["answer"] and any("number" in p for p in r["problems"])


def test_numbered_list_markers_are_not_invented_numbers():
    m = members()["minimax-h3"]; r = crew.ask(m, "last recorded render h3 template", reply("7. It ran.", "MiniMax-H3 last recorded render: template h3_t2v_api")); assert r["supported"]


def test_the_api_shows_the_label_and_not_the_path():
    t = C.public_text("Trains for 300 steps. [run: studio/train_measured.json]"); assert t == "Trains for 300 steps. [run]"
    assert C.public_text("It reads a file. [code: studio/vset/api.py:12, studio/vset/qc.py:3]") == "It reads a file. [code]"


def test_a_clean_clone_answers_a_studio_question_with_no_model(monkeypatch):
    monkeypatch.setattr(C, "KB_ROOT", str(NOTES))
    def no_llm(messages): raise RuntimeError("no language model is running")
    monkeypatch.setattr(crew, "default_chat", no_llm)
    r = asyncio.run(C.ask_crew(C.AskRequest(who="auto", question="How do I train a LoRA on the Train page?")))
    assert r["member"]["id"] == "train" and r["result"]["from_notes_only"] and r["result"]["supported"] and "/" + "mnt" not in str(r)


def test_evidence_file_holds_no_path_and_every_family_it_names_is_known():
    rows = (NOTES / "evidence" / "model_proof_2026-11-01.tsv").read_text().splitlines()
    assert rows[0].split("\t") == ["family", "file", "gb", "function", "status", "proof"] and len(rows) > 50 and not any("/" + "mnt" in r or "/" + "home" in r for r in rows)
