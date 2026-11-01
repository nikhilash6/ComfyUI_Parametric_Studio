"""The Auto page: every control stays, and offline it says that no job can start."""
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "studio" / "web" / "pages2.js").read_text()


def test_auto_keeps_its_controls_and_says_what_is_true():
    body = JS[JS.index("export function Schedules()"):JS.index("export function CalibrateCard()")]
    for word in ("Add schedule", "run-now", "Pause", "Delete", "Most per day", "no job can start until ComfyUI is back", "our own renders, not yours"):
        assert word in body, word


def test_week_comes_from_the_rule_and_samples_are_labelled():
    body = JS[JS.index("const WEEKDAY"):JS.index("export function CalibrateCard()")]
    for word in ("/api/schedules/week", "Sample, not scheduled", "Nothing is scheduled yet", "not yours", "role=\"timer\"", "Past runs are never drawn"):
        assert word in body, word
    assert "Math.random" not in body


def test_fires_are_real_and_inside_the_week():
    import time
    from studio import schedule
    now = time.mktime((2026, 11, 2, 7, 30, 0, 0, 0, -1))
    got = schedule.fires("every morning at 8", now)
    assert len(got) == 7 and all(now < t <= now + 7 * 86400 for t in got)
    assert time.localtime(got[0]).tm_hour == 8 and time.localtime(got[0]).tm_mday == 2
    assert len(schedule.fires("every Monday at 9", now)) == 1
    assert len(schedule.fires("every hour", now)) == 168


def test_week_route_lists_only_enabled_jobs(monkeypatch):
    from studio import schedule
    monkeypatch.setattr(schedule, "load", lambda: [{"id": "a", "cron": "0 8 * * *", "enabled": True}, {"id": "b", "cron": "0 8 * * *", "enabled": False}])
    w = schedule.sched_week()
    assert list(w["jobs"]) == ["a"] and "every hour" in w["presets"] and w["now"] > 0


def test_weekdays_mean_what_cron_means():
    import time
    from studio import schedule
    now = time.mktime((2026, 11, 2, 7, 30, 0, 0, 0, -1))   # a Monday
    day = lambda cron: [time.localtime(t).tm_wday for t in schedule.fires(cron, now)]     # Monday is 0 here
    assert day("every Monday at 9") == [0]
    assert day("every Friday at 5") == [4]
    assert sorted(day("every weekend morning")) == [5, 6]
    assert day("0 9 * * 1-5") == [0, 1, 2, 3, 4] and day("0 9 * * 0") == [6] and day("0 9 * * 7") == [6]
    assert schedule._named_days("0 9 * * */2") == "0 9 * * */2"


def test_presets_with_capitals_can_be_added():
    from studio import schedule
    for name in schedule.PRESETS:
        d = schedule.validate({"cron": name, "goal": "image", "prompt": "a lighthouse at dawn"})
        assert d["cron"] == schedule.PRESETS[name]
