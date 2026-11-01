"""The crew routes, with the crew module's functions faked for each test only.
This file used to assign the fakes at import time, so merely collecting it replaced crew.ask and crew.roster for every other test in the run (the crew quote and clean-clone failures)."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from studio import crew, crew_api

MEMBERS = [
    {"id": "m1", "name": "Alice", "tier": "senior", "family": "tech", "has_dossier": True},
    {"id": "m2", "name": "Bob", "tier": "junior", "family": "design", "has_dossier": False},
]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(crew, "roster", lambda kb_root: MEMBERS)
    monkeypatch.setattr(crew, "ask", lambda member, question, chat, k=4: {"answer": f"Answer from {member['name']} to: {question}"})
    monkeypatch.setattr(crew, "route", lambda question, members: members[0])
    monkeypatch.setattr(crew, "default_chat", "default")
    app = FastAPI(); app.include_router(crew_api.router)
    return TestClient(app)


def test_lists_the_roster(client):
    data = client.get("/api/crew").json()
    assert [m["id"] for m in data["members"]] == ["m1", "m2"]


def test_asks_a_named_member(client):
    resp = client.post("/api/crew/ask", json={"who": "m1", "question": "Hello there"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["member"]["id"] == "m1" and data["member"]["name"] == "Alice"
    assert data["result"]["answer"] == "Answer from Alice to: Hello there"


def test_routes_auto_to_a_member(client):
    resp = client.post("/api/crew/ask", json={"who": "auto", "question": "Auto question"})
    assert resp.status_code == 200 and resp.json()["member"]["id"] == "m1"


@pytest.mark.parametrize("question", ["Hi", "x" * 601])
def test_refuses_a_question_out_of_range(client, question):
    assert client.post("/api/crew/ask", json={"who": "m1", "question": question}).status_code == 400


def test_refuses_an_unknown_member(client):
    assert client.post("/api/crew/ask", json={"who": "unknown", "question": "Hello there"}).status_code == 404


def test_the_fakes_do_not_outlive_a_test():
    assert crew.ask.__module__ == "studio.crew" and crew.roster.__module__ == "studio.crew" and callable(crew.default_chat)
