"""ComfyUI custom nodes: RSS-Driven News Video Generation (ParametricStudio).

Core logic only – no network, no LLM, no moviepy.
- PSN_RSS_Fetcher: parses RSS/Atom XML from a provided string.
- PSN_News_Script_Generator: template-based script from headlines.
- PSN_News_Thumbnail_Placeholder: a plain gradient IMAGE at the chosen resolution.
  It makes no video, writes no file and does not depend on the script.
"""

import json
import re
import xml.etree.ElementTree as ET

import torch

CAT = "ParametricStudio/NewsVideo"


def _parse_rss_xml(xml_text, max_items=10, category_filter=""):
    """Parse RSS 2.0 or Atom XML text into a list of dicts."""
    if not xml_text or not isinstance(xml_text, str):
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    items = []
    # RSS 2.0: channel/item
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        desc = (item.findtext("description") or "").strip()
        link = (item.findtext("link") or "").strip()
        cat_el = item.find("category")
        cat = (cat_el.text or "").strip() if cat_el is not None and cat_el.text else ""
        items.append({"title": title, "description": desc, "link": link, "category": cat})

    # Atom: entry
    if not items:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("a:entry", ns):
            title = (entry.findtext("a:title", namespaces=ns) or "").strip()
            summary = (entry.findtext("a:summary", namespaces=ns) or "").strip()
            link_el = entry.find("a:link", ns)
            link = link_el.get("href", "") if link_el is not None else ""
            cat_el = entry.find("a:category", ns)
            cat = cat_el.get("term", "") if cat_el is not None else ""
            items.append({"title": title, "description": summary, "link": link, "category": cat})

    # Apply category filter
    if category_filter:
        cf = category_filter.lower()
        items = [it for it in items if cf in it["category"].lower()]

    items = items[:max_items]
    return items


class PSN_RSS_Fetcher:
    """Parse RSS/Atom XML text into structured news items (no network)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "feed_xml": ("STRING", {"default": "", "multiline": True}),
                "max_items": ("INT", {"default": 10, "min": 1, "max": 100}),
                "category_filter": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("news_items", "fetch_status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, feed_xml, max_items, category_filter):
        items = _parse_rss_xml(feed_xml, max_items, category_filter)
        if not items:
            status = "error: no items parsed (invalid XML or empty feed)"
        else:
            status = "success"
        return (json.dumps(items, ensure_ascii=False), status)


def _generate_script(news_items_json, script_style="News Anchor"):
    """Template-based script generation from a JSON list of news items."""
    try:
        items = json.loads(news_items_json) if news_items_json else []
    except (json.JSONDecodeError, TypeError):
        items = []
    if not isinstance(items, list):
        items = []

    style_openers = {
        "News Anchor": "Good evening, and welcome to your daily news digest.",
        "Casual": "Hey there! Here's what's happening today.",
        "Technical": "Initializing news digest sequence. Processing items.",
    }
    opener = style_openers.get(script_style, style_openers["News Anchor"])

    lines = [opener]
    scenes = []
    for i, it in enumerate(items, 1):
        title = it.get("title", "Untitled") if isinstance(it, dict) else str(it)
        desc = it.get("description", "") if isinstance(it, dict) else ""
        lines.append(f"Story {i}: {title}. {desc}".strip())
        scenes.append({
            "scene_id": i,
            "headline": title,
            "description": desc,
            "duration_sec": 5,
        })
    lines.append("That's all for today. Stay tuned.")
    return "\n".join(lines), json.dumps(scenes, ensure_ascii=False)


class PSN_News_Script_Generator:
    """Generate a narration script and scene breakdown from news items (template-based, no LLM)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "news_items": ("STRING", {"default": "[]", "multiline": True}),
                "script_style": ("News Anchor", "Casual", "Technical"),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("video_script", "scene_breakdown")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, news_items, script_style):
        script, scenes = _generate_script(news_items, script_style)
        return (script, scenes)


class PSN_News_Thumbnail_Placeholder:
    """Build a plain diagonal gradient IMAGE sized by the chosen resolution.

    It does not render a video, write any file, or use the script text."""

    DESCRIPTION = ("Builds a plain black-to-white diagonal gradient IMAGE at "
                   "the chosen resolution. It makes no video, writes no file "
                   "and does not read the script.")

    _RESOLUTIONS = ["1920x1080", "1280x720"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "output_resolution": (cls._RESOLUTIONS,),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("thumbnail",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, output_resolution):
        w, h = (int(x) for x in output_resolution.split("x"))
        tv = torch.linspace(0.0, 1.0, h, device="cpu").view(1, h, 1, 1).expand(1, h, w, 1)
        th = torch.linspace(0.0, 1.0, w, device="cpu").view(1, 1, w, 1).expand(1, h, w, 1)
        thumb = ((tv + th) / 2.0).clamp(0.0, 1.0)
        return (thumb.expand(1, h, w, 3).clone(),)


NODE_CLASS_MAPPINGS = {
    "PSN_RSS_Fetcher": PSN_RSS_Fetcher,
    "PSN_News_Script_Generator": PSN_News_Script_Generator,
    "PSN_News_Thumbnail_Placeholder": PSN_News_Thumbnail_Placeholder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_RSS_Fetcher": "RSS Fetcher (XML)",
    "PSN_News_Script_Generator": "News Script Generator",
    "PSN_News_Thumbnail_Placeholder": "News Gradient Thumbnail (no video)",
}
