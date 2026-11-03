#!/usr/bin/env python3
"""Screen-records a running studio, tab by tab, for the studio tour demo. Read-only: it only opens pages and scrolls them, it never presses Generate or posts anything.
Every tab of the shell (TABS in studio/web/app.js) and every feature page (GET /api/feature-pages) is visited in order, with a smooth scroll on the richest pages.
Frames come from Chrome's own screencast (CDP Page.startScreencast), so the text stays sharp. It writes frames/*.jpg and timeline.json (each frame's time, and when each tab opened);
scripts/build_demo_videos.py tour turns that into the video and adds the captions.
Usage: python scripts/record_studio_tour.py --url http://127.0.0.1:8310 --out DIR [--phone] [--chrome PATH]      (needs Playwright; --chrome points it at a Chromium it can use)"""
import argparse, asyncio, base64, json, re, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RICH = ("families", "recipes", "pipelines", "university", "packlab", "moe", "anatomy", "shots")      # Families, Recipes, Pipelines, University (Learn), Pack Lab, Experts, Model Anatomy, Shot Board
SCROLL = {"shots": 650}      # Shot Board's lower half is the empty job form on a fresh install
PHONE = ("create", "shots", "families", "recipes", "pipelines", "university", "music", "moe")
SCROLL_JS = """async ([px, ms]) => { const el = document.scrollingElement, top = Math.min(px, el.scrollHeight - innerHeight); if (top < 40) return 0; const t0 = performance.now();
  await new Promise((done) => { const step = (t) => { const k = Math.min(1, (t - t0) / ms), e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2; el.scrollTop = top * e; k < 1 ? requestAnimationFrame(step) : done(); }; requestAnimationFrame(step); }); return top; }"""


def shell_tabs():
    src = (ROOT / "studio" / "web" / "app.js").read_text(encoding="utf-8")
    tabs = json.loads(re.search(r"const TABS = (\[\[.*?\]\]);", src).group(1))
    titles = {k: v for k, v in re.findall(r'\b(\w+): \["([^"]+)", "', re.search(r"const TITLES = \{(.*?)\};", src).group(1))}
    subs = dict(re.findall(r'\b(\w+): \["[^"]+", "([^"]+)"', re.search(r"const TITLES = \{(.*?)\};", src).group(1)))
    return [{"tab": k, "label": l, "title": titles.get(k, l), "sub": subs.get(k, "")} for k, l in tabs]


def all_tabs(url):
    with urllib.request.urlopen(url.rstrip("/") + "/api/feature-pages", timeout=30) as r: pages = json.load(r)["pages"]
    return shell_tabs() + [{"tab": p["tab"], "label": p["label"], "title": (p.get("title") or [p["label"]])[0], "sub": (p.get("title") or ["", ""])[1] if len(p.get("title") or []) > 1 else ""} for p in pages]


async def record(url, out, phone=False, chrome=None, plain=2.6, rich=4.6, plan=None, size=None):
    """plan: {tab: seconds} records only those tabs, in that order, each held that long with a slow scroll (the narrated walkthrough cuts its shots from these)."""
    from playwright.async_api import async_playwright
    frames = out / "frames"; frames.mkdir(parents=True, exist_ok=True); stamps, marks = [], []
    tabs = all_tabs(url); tabs = [t for t in tabs if t["tab"] in PHONE] if phone else tabs
    if phone: tabs.sort(key=lambda t: PHONE.index(t["tab"]))
    if plan: by = {t["tab"]: t for t in tabs}; tabs = [by[k] for k in plan]
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=chrome) if chrome else await p.chromium.launch()
        size = {"width": 390, "height": 844} if phone else (size or {"width": 1440, "height": 900})
        ctx = await b.new_context(viewport=size, device_scale_factor=2 if phone else 1, is_mobile=phone, has_touch=phone, reduced_motion="no-preference")
        await ctx.add_init_script("try { localStorage.setItem('tour', 'done'); } catch (e) {}")      # the guided tour would cover the pages
        pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
        async def on_frame(ev):
            ts = ev["metadata"]["timestamp"]; n = len(stamps)      # seconds since the epoch, the same clock as time.time()
            (frames / f"{n:06d}.jpg").write_bytes(base64.b64decode(ev["data"])); stamps.append(round(ts, 4))
            try: await cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
            except Exception: pass
        cdp.on("Page.screencastFrame", lambda ev: asyncio.ensure_future(on_frame(ev)))
        await pg.goto(url.rstrip("/") + "/#" + tabs[0]["tab"], wait_until="networkidle"); await pg.wait_for_timeout(2500)
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": size["width"] * (2 if phone else 1), "maxHeight": size["height"] * (2 if phone else 1), "everyNthFrame": 1})
        await pg.wait_for_timeout(600); wall0 = time.time()
        for i, t in enumerate(tabs):
            if i: await pg.evaluate("(t) => { document.scrollingElement.scrollTop = 0; location.hash = t; }", t["tab"])
            start = time.time() - wall0; await pg.wait_for_timeout(350)
            try: await pg.wait_for_load_state("networkidle", timeout=1500)
            except Exception: pass
            hold = plan[t["tab"]] if plan else rich if t["tab"] in RICH and not phone else (3.0 if phone else plain); spent = time.time() - wall0 - start
            if plan:      # a slow, even scroll through the page for the whole hold, after a second and a half at the top
                await pg.wait_for_timeout(max(0, int(1500 - spent * 1000))); await pg.evaluate(SCROLL_JS, [int(110 * max(0, hold - 2.5)), int(1000 * max(0.5, hold - 2.5))])
            elif t["tab"] in RICH or phone:
                await pg.wait_for_timeout(max(0, int((1.3 if phone else 1.5) * 1000 - spent * 1000)))
                await pg.evaluate(SCROLL_JS, [1500 if phone else SCROLL.get(t["tab"], 2400), 1100 if phone else 2400])
            left = hold - (time.time() - wall0 - start)
            if left > 0: await pg.wait_for_timeout(int(left * 1000))
            marks.append({**t, "start": round(start, 3), "end": round(time.time() - wall0, 3)})
        await cdp.send("Page.stopScreencast"); await pg.wait_for_timeout(300); await b.close()
    # frame times and tab times both count from the moment the first tab was on screen
    json.dump({"phone": phone, "size": size, "frames": [round(x - wall0, 4) for x in stamps], "tabs": marks}, open(out / "timeline.json", "w"), indent=1)
    return len(stamps), marks


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("--url", default="http://127.0.0.1:8310"); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--phone", action="store_true", help="390 px wide, eight key tabs"); ap.add_argument("--chrome", help="a Chromium executable for Playwright")
    ap.add_argument("--plan", type=Path, help="JSON {tab: seconds}: record only these tabs, each held that long"); ap.add_argument("--size", default="", help="WIDTHxHEIGHT, default 1440x900"); a = ap.parse_args(argv)
    size = dict(zip(("width", "height"), map(int, a.size.split("x")))) if a.size else None
    n, marks = asyncio.run(record(a.url, a.out, a.phone, a.chrome, plan=json.loads(a.plan.read_text()) if a.plan else None, size=size)); print(f"{n} frames, {len(marks)} tabs, {marks[-1]['end']:.1f} s"); return 0


if __name__ == "__main__":
    sys.exit(main())
