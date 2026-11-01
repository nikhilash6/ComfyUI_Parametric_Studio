"""Builds the sample sites on the Site Builder page with the real builder (psn.sitebuilder.build_site), so its checks and colour rules all run.
The briefs are invented and say so on the page. The words are hand-written from those facts, passed through the same check the local AI's copy has to pass, because the local AI was asleep when these were made. The pictures are this studio's own showcase renders dropped into the builder's picture slots.
Run with the studio's venv from the repo root. It needs Playwright for the screenshots, and it touches no live port."""
import asyncio, json, pathlib, re, shutil, sys
from PIL import Image
ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from psn.sitebuilder import build_site, check_site
from psn.subagents.roles import v_site_copy
from psn.subagents.runner import Result
OUT = ROOT / "studio/web/site_examples"; ART = ROOT / "studio/web/showcase"
CHROME = pathlib.Path.home() / ".cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell"

def sec(i, h, b, alt, art): return {"id": i, "heading": h, "body": b, "alt": alt, "image_prompt": alt, "_art": art}
SITES = [
 dict(slug="golden-crumb", label="Bakery", scheme="light", brief=dict(name="Golden Crumb", voice="warm, handmade", brand="#b5651d", pages=["Home", "Visit"], facts={"Hours": "Tuesday to Sunday, 7 to 3", "Known for": "Sourdough baked before dawn", "Where": "Corner of Pine and 4th"}),
  pages=[("home", "Home", "A small bakery known for sourdough baked before dawn.", [sec("welcome", "Baked before dawn", "Golden Crumb is known for one thing above all: sourdough baked before dawn, so the first loaves are ready when the door opens.\n\nCome by, have a look, and take one home.", "A green glazed teapot on a mossy rock in soft golden light", "p_teapot.webp")]), ("visit", "Visit", "Where and when to find Golden Crumb.", [sec("when", "Find us", "We are on the corner of Pine and 4th, open Tuesday to Sunday, from 7 to 3.", "A green glazed teapot in soft light", "p_teapot.webp")])]),
 dict(slug="night-shift", label="Band", scheme="dark", brief=dict(name="The Night Shift", voice="dark, loud", brand="#27e07f", pages=["Home", "Shows"], facts={"Sound": "Three-piece synth rock", "Next show": "Friday at the Old Mill", "Booking": "Use the contact form"}),
  pages=[("home", "Home", "The Night Shift, a three-piece synth rock band.", [sec("sound", "Three people. A lot of synth.", "The Night Shift is a three-piece synth rock band. It is dark and it is loud, and that is the whole idea.", "A record cover with a golden sun over green waves, leaning on a black vinyl disc", "a_score.webp")]), ("shows", "Shows", "The next show from The Night Shift.", [sec("next", "Friday at the Old Mill", "The next show is on Friday at the Old Mill. To book the band, use the contact form.", "A record cover with a golden sun over green waves", "a_score.webp")])]),
 dict(slug="parallel-frame", label="Film studio", scheme="dark", brief=dict(name="Parallel Frame", voice="minimal, cinematic", brand="#d9a900", pages=["Home", "Work"], facts={"What we do": "Short films and product videos", "Team": "Two directors and an editor", "Turnaround": "Two weeks"}),
  pages=[("home", "Home", "Parallel Frame makes short films and product videos.", [sec("what", "Short films. Product videos.", "Parallel Frame is two directors and an editor. We make short films and product videos, with a turnaround of two weeks.", "An old man in a pointed hat rowing a small boat through a flooded city at night", "short_film.webp")]), ("work", "Work", "How Parallel Frame works.", [sec("how", "Two weeks, start to finish", "Two directors and an editor take your film or product video from start to finish in two weeks.", "A lone traveller walking across a white salt flat at dusk", "director_wide.webp")])]),
 dict(slug="verdant-glass", label="Plant nursery", scheme="light", brief=dict(name="Verdant Glass", voice="calm, green", brand="#0f9d55", pages=["Home", "Visit"], facts={"What we grow": "Ferns and climbing plants", "Where": "The old glasshouse on Mill Lane", "Open": "Weekends, 9 to 5"}),
  pages=[("home", "Home", "A nursery for ferns and climbing plants.", [sec("grow", "Ferns and climbers, under glass", "Verdant Glass grows ferns and climbing plants in the old glasshouse on Mill Lane.", "A huge glass greenhouse glowing green at night", "s_greenhouse.webp")]), ("visit", "Visit", "When to visit Verdant Glass.", [sec("open", "Open at weekends", "Come and walk the rows at weekends, from 9 to 5, at the old glasshouse on Mill Lane.", "A huge glass greenhouse glowing green at night", "s_greenhouse.webp")])]),
 dict(slug="fine-movement", label="Watch repair", scheme="light", brief=dict(name="Fine Movement", voice="precise, quiet", brand="#7a5c1e", pages=["Home", "Repairs"], facts={"What we do": "Mechanical watch repair", "Where": "Upstairs at 12 Clock Yard", "Booking": "By appointment"}),
  pages=[("home", "Home", "Mechanical watch repair at 12 Clock Yard.", [sec("repair", "Mechanical watches, repaired", "Fine Movement repairs mechanical watches, upstairs at 12 Clock Yard.", "The gold gears and purple jewels of an open mechanical watch movement", "s_watch.webp")]), ("repairs", "Repairs", "How to book a watch repair.", [sec("book", "By appointment", "Repairs are by appointment. Find us upstairs at 12 Clock Yard.", "The gold gears of an open mechanical watch movement", "s_watch.webp")])]),
 dict(slug="stride-lab", label="Running shop", scheme="dark", brief=dict(name="Stride Lab", voice="fast, bright", brand="#5b8def", pages=["Home", "Fitting"], facts={"What we sell": "Running shoes", "Service": "Free gait check with every fitting", "Where": "Station Road"}),
  pages=[("home", "Home", "Running shoes on Station Road.", [sec("shoes", "Shoes for running", "Stride Lab sells running shoes on Station Road, with a free gait check at every fitting.", "A black and gold running shoe splashing through still water", "s_sneaker.webp")]), ("fitting", "Fitting", "What happens at a fitting.", [sec("gait", "A free gait check", "Every fitting comes with a free gait check, so you leave with a shoe that suits how you run.", "A black and gold running shoe splashing through still water", "s_sneaker.webp")])]),
]

def build_one(s):
    d = OUT / s["slug"]; shutil.rmtree(d, ignore_errors=True)
    copy = {"pages": [{"slug": sl, "title": t, "description": de, "sections": [{k: v for k, v in x.items() if k != "_art"} for x in se]} for sl, t, de, se in s["pages"]]}
    bad = v_site_copy(copy, {"brief": s["brief"]})
    if bad: raise SystemExit(f"{s['slug']} copy failed the check: {bad}")
    r = build_site(s["brief"], str(d), runner=lambda role, task, ctx=None, **kw: Result(True, role, copy, attempts=1))
    if not r["ok"]: raise SystemExit(f"{s['slug']}: {r['problems']}")
    z = pathlib.Path(r["zip"]); z.unlink(missing_ok=True)
    for sl, t, de, se in s["pages"]:
        page = d / ("index.html" if sl == "home" else f"{sl}.html"); h = page.read_text()
        for x in se:
            name = f"{sl}-{x['id']}"; im = Image.open(ART / x["_art"]).convert("RGB"); im.thumbnail((880, 880)); im.save(d / f"assets/{name}.webp", quality=74, method=6)
            (d / f"assets/{name}.svg").unlink(); h = h.replace(f'assets/{name}.svg', f'assets/{name}.webp')
        page.write_text(h)
    (d / "images_todo.json").unlink()
    probs = check_site(str(d), copy)
    if probs: raise SystemExit(f"{s['slug']} after pictures: {probs}")

async def stills():
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=str(CHROME))
        for s in SITES:
            url = (OUT / s["slug"] / "index.html").as_uri()
            for name, w, h in (("desktop", 1280, 800), ("phone", 390, 780)):
                c = await b.new_context(viewport={"width": w, "height": h}, color_scheme=s["scheme"]); p = await c.new_page(); await p.goto(url); await p.wait_for_timeout(200)
                f = OUT / f"{s['slug']}_{name}.png"; await p.screenshot(path=str(f), full_page=True); await c.close()
                im = Image.open(f).convert("RGB"); im.thumbnail((640 if name == "desktop" else 300, 1400)); im.save(f.with_suffix(".webp"), quality=78, method=6); f.unlink()
        await b.close()

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for s in SITES: build_one(s)
    asyncio.run(stills())
    (OUT / "index.json").write_text(json.dumps([{"slug": s["slug"], "label": s["label"], "name": s["brief"]["name"], "voice": s["brief"]["voice"], "brand": s["brief"]["brand"], "pages": ", ".join(s["brief"]["pages"]).lower(), "facts": s["brief"]["facts"]} for s in SITES], indent=1) + "\n")
    print("built", len(SITES), "sites into", OUT)
main()
