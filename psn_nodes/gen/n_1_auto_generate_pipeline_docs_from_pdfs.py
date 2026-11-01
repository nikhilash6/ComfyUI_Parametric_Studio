"""Text block splitter and Markdown formatter (pure-logic, secure-by-design).

Despite the module name, nothing here opens or parses a PDF, and no LLM or
network service is called. It does NOT open sockets, read files or import
torch. It provides:

  * PSN_Text_Block_Splitter -- checks that a path string looks like a safe
    relative .pdf name, then splits the supplied ``raw_text`` on blank lines.
    The PDF itself is never read; the text must already be extracted.
  * PSN_Text_Blocks_To_Markdown -- formats text blocks into a fixed Markdown
    template (Concise, Detailed or Tutorial). No model is involved.

All functions take plain values (strings, numbers, booleans) and return plain
values. No file, OS, network, subprocess, or eval/exec access.
"""

import re

CAT = "ParametricStudio/Docs"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SAFE_PDF_EXTENSIONS = (".pdf",)

_DOC_STYLES = ("Concise", "Detailed", "Tutorial")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_safe_pdf_path(pdf_path):
    """Return (ok, reason). ok is True only if pdf_path looks like a safe PDF path."""
    if not isinstance(pdf_path, str):
        return False, "pdf_path must be a string"
    stripped = pdf_path.strip()
    if not stripped:
        return False, "pdf_path is empty"
    # Reject path traversal and absolute paths that escape a sandbox root.
    if ".." in stripped:
        return False, "pdf_path contains path traversal ('..')"
    if stripped.startswith("/") or stripped.startswith("\\"):
        return False, "pdf_path must be relative (no absolute paths)"
    # Check extension (case-insensitive).
    lower = stripped.lower()
    if not any(lower.endswith(ext) for ext in _SAFE_PDF_EXTENSIONS):
        return False, "pdf_path must end with a safe extension (.pdf)"
    return True, "ok"


def _split_text_blocks(raw_text):
    """Split raw text into blocks on blank-line boundaries. Returns list of str."""
    if not isinstance(raw_text, str):
        return []
    # Normalise line endings.
    normalised = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    # Split on one or more blank lines.
    parts = re.split(r"\n\s*\n", normalised)
    blocks = [p.strip() for p in parts if p.strip()]
    return blocks


def _generate_markdown(blocks, doc_style):
    """Format text blocks with a fixed Markdown template."""
    lines = []
    lines.append("# Pipeline Documentation")
    lines.append("")

    if doc_style == "Tutorial":
        lines.append("## Tutorial Overview")
        lines.append("")
        lines.append("This document walks through the pipeline step by step.")
        lines.append("")

    if doc_style == "Concise":
        lines.append("## Summary")
        lines.append("")

    for idx, block in enumerate(blocks, start=1):
        if doc_style == "Concise":
            # First 200 chars only.
            snippet = block[:200]
            if len(block) > 200:
                snippet += "…"
            lines.append(f"### Section {idx}")
            lines.append("")
            lines.append(snippet)
            lines.append("")
        elif doc_style == "Tutorial":
            lines.append(f"### Step {idx}")
            lines.append("")
            lines.append(block)
            lines.append("")
        else:  # Detailed
            lines.append(f"### Section {idx}")
            lines.append("")
            lines.append(block)
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*End of document.*")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Node 1: PSN_Text_Block_Splitter
# ---------------------------------------------------------------------------

class PSN_Text_Block_Splitter:
    """Check a relative .pdf path string, then split supplied text on blank lines.

    No file I/O: the PDF is never opened. ``raw_text`` must already hold the
    extracted text; with an empty ``raw_text`` the output is empty.
    """

    DESCRIPTION = (
        "Splits the supplied raw_text on blank lines after checking that "
        "pdf_path is a safe relative .pdf name. It does not read any PDF."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pdf_path": ("STRING", {"default": "sample_pipeline.pdf", "multiline": False}),
            },
            "optional": {
                "raw_text": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text_content", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, pdf_path, raw_text=""):
        ok, reason = _is_safe_pdf_path(pdf_path)
        if not ok:
            return ("", f"ERROR: {reason}")

        blocks = _split_text_blocks(raw_text)
        text_content = "\n\n".join(blocks)
        return (text_content, f"blocks={len(blocks)}")


# ---------------------------------------------------------------------------
# Node 2: PSN_Text_Blocks_To_Markdown
# ---------------------------------------------------------------------------

class PSN_Text_Blocks_To_Markdown:
    """Format text blocks into a fixed Markdown template.

    No LLM, no network: blank-line separated blocks become numbered
    sections (Concise cuts each block to 200 characters).
    """

    DESCRIPTION = (
        "Formats text blocks into a fixed Markdown template (Concise, "
        "Detailed or Tutorial). No LLM is involved and nothing is summarised "
        "or rewritten."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "raw_text": ("STRING", {"default": "", "multiline": True}),
                "doc_style": (list(_DOC_STYLES),),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("markdown_doc",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, raw_text, doc_style):
        blocks = _split_text_blocks(raw_text)
        return (_generate_markdown(blocks, doc_style),)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Text_Block_Splitter": PSN_Text_Block_Splitter,
    "PSN_Text_Blocks_To_Markdown": PSN_Text_Blocks_To_Markdown,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Text_Block_Splitter": "Text Block Splitter",
    "PSN_Text_Blocks_To_Markdown": "Text Blocks to Markdown",
}
