"""Manifest + fixed-key HMAC embedding (pure-logic).

This is NOT C2PA.  It writes no C2PA/JUMBF structure and no X.509 signature,
uses no ``c2pa`` library, and writes no file.  It is also not tamper-proof:
the HMAC key is a constant in this source file, so anyone can produce a
matching manifest and HMAC.  It only shows that a manifest dict still matches
the hash and HMAC stored beside it.

What it does, using only the Python standard library:

* Build a small JSON manifest (author, tool, media format) from plain values.
* Compute a stable manifest hash (SHA-256 over canonical JSON).
* Compute an HMAC-SHA256 of the manifest with the fixed key.
* Add the manifest + HMAC as a base64 string under the ``psn_manifest`` key of
  a media dict's ``metadata``, leaving ``pixels`` untouched.  Nothing is
  written into a PNG or MP4 file.
* Read that entry back and recompute the hash and HMAC.

The media is represented as a plain dict:
    {"format": "png"|"mp4", "pixels": <opaque>, "metadata": {...}}
``pixels`` is passed through untouched; only ``metadata`` is extended.

Node classes are named ``PSN_`` + CamelCase and expose the standard
ComfyUI-style ``INPUT_TYPES`` / ``RETURN_TYPES`` / ``run`` surface.
"""

import base64
import hashlib
import hmac
import json
import re

CAT = "ParametricStudio/Provenance"

# Fixed HMAC key.  It is public (it is in this source file), so the HMAC shows
# consistency only, not authorship or tamper resistance.
_DEFAULT_KEY = b"psn-manifest-fixed-public-hmac-key"

# Maximum allowed length for free-text fields (author / tool / override).
_MAX_TEXT_LEN = 4096

# Allowed media container formats.
_ALLOWED_FORMATS = ("png", "mp4")

# Metadata key holding the embedded manifest payload.
_MANIFEST_TAG = "psn_manifest"


def _canonical_json(obj):
    """Return a canonical, deterministic JSON string for *obj*.

    Keys are sorted and separators are fixed so the same logical manifest
    always serialises to the same byte string (and therefore the same hash).
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _b64encode(data):
    """Base64-encode bytes into an ASCII string (no padding surprises)."""
    return base64.b64encode(data).decode("ascii")


def _b64decode(text):
    """Base64-decode an ASCII string back into bytes."""
    return base64.b64decode(text.encode("ascii"))


def _validate_text(value, name):
    """Validate a free-text field: must be a str, non-empty, bounded length."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string" % name)
    if len(value) == 0:
        raise ValueError("%s must not be empty" % name)
    if len(value) > _MAX_TEXT_LEN:
        raise ValueError("%s exceeds maximum length of %d" % (name, _MAX_TEXT_LEN))
    return value


def _validate_media(media):
    """Validate the media dict shape and return a normalised copy."""
    if not isinstance(media, dict):
        raise ValueError("media must be a dict")
    fmt = media.get("format")
    if fmt not in _ALLOWED_FORMATS:
        raise ValueError("media format must be one of %s" % (_ALLOWED_FORMATS,))
    if "pixels" not in media:
        raise ValueError("media must contain a 'pixels' field")
    metadata = media.get("metadata")
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError("media metadata must be a dict")
    return fmt, media["pixels"], metadata


def build_manifest(author, tool, media_format, manifest_override=None):
    """Build a small manifest dict from plain values.

    ``manifest_override`` (optional JSON text) is merged *on top of* the
    generated claims so callers can inject extra provenance fields.  The
    override must be valid JSON object text; anything else raises.
    """
    author = _validate_text(author, "author")
    tool = _validate_text(tool, "tool")
    if media_format not in _ALLOWED_FORMATS:
        raise ValueError("media format must be one of %s" % (_ALLOWED_FORMATS,))

    manifest = {
        "manifest_version": "1",
        "claim_generator": "PSN_Manifest_HMAC_Embed",
        "creation": {
            "author": author,
            "tool": tool,
            "media_format": media_format,
        },
        "software_agent": {
            "name": "ParametricStudio",
            "role": "generator",
        },
        "provenance_chain": [
            {"step": "created", "by": author, "tool": tool},
        ],
    }

    if manifest_override is not None and manifest_override != "":
        if not isinstance(manifest_override, str):
            raise ValueError("manifest override must be a JSON string")
        try:
            override = json.loads(manifest_override)
        except (ValueError, TypeError) as exc:
            raise ValueError("manifest override is not valid JSON: %s" % exc)
        if not isinstance(override, dict):
            raise ValueError("manifest override must be a JSON object")
        # Shallow merge: override wins on conflicting top-level keys.
        manifest.update(override)

    return manifest


def manifest_hash(manifest):
    """Return the SHA-256 hex digest of the canonical manifest JSON."""
    return hashlib.sha256(_canonical_json(manifest).encode("utf-8")).hexdigest()


def sign_manifest(manifest, key=_DEFAULT_KEY):
    """Return a deterministic HMAC-SHA256 (hex) of the manifest.

    The default key is public, so this is a consistency check only, not a
    signature in the asymmetric sense.
    """
    if not isinstance(key, (bytes, bytearray)):
        raise ValueError("signing key must be bytes")
    payload = _canonical_json(manifest).encode("utf-8")
    return hmac.new(bytes(key), payload, hashlib.sha256).hexdigest()


def embed_manifest(media, manifest, signature):
    """Embed manifest + signature into the media container metadata.

    The pixel data is returned unchanged.  The manifest and signature are
    stored base64-encoded under the ``psn_manifest`` metadata key of the
    returned dict.  Nothing is written into a PNG or MP4 file.
    """
    fmt, pixels, metadata = _validate_media(media)
    payload = {
        "manifest": manifest,
        "signature": signature,
        "hash": manifest_hash(manifest),
    }
    encoded = _b64encode(_canonical_json(payload).encode("utf-8"))
    new_metadata = dict(metadata)
    new_metadata[_MANIFEST_TAG] = encoded
    return {"format": fmt, "pixels": pixels, "metadata": new_metadata}


def extract_manifest(media):
    """Extract the embedded manifest payload from media metadata.

    Returns a dict with keys ``manifest``, ``signature``, ``hash``.
    Raises ValueError if no manifest is present or it is malformed.
    """
    _fmt, _pixels, metadata = _validate_media(media)
    encoded = metadata.get(_MANIFEST_TAG)
    if encoded is None:
        raise ValueError("no embedded manifest in media")
    if not isinstance(encoded, str):
        raise ValueError("embedded manifest payload is malformed")
    try:
        raw = _b64decode(encoded)
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise ValueError("embedded manifest payload is not valid: %s" % exc)
    if not isinstance(payload, dict):
        raise ValueError("embedded manifest payload must be an object")
    for key in ("manifest", "signature", "hash"):
        if key not in payload:
            raise ValueError("embedded manifest payload missing '%s'" % key)
    return payload


def verify_manifest(media):
    """Check the embedded manifest against its stored hash and the fixed-key HMAC.

    Returns a tuple ``(hmac_matches, details_json, error)`` where:
      * ``hmac_matches`` is a bool (True only says the hash and HMAC match),
      * ``details_json`` is a JSON string describing the manifest (or "" on
        failure),
      * ``error`` is a human-readable reason (or "" on success).
    """
    try:
        payload = extract_manifest(media)
    except ValueError as exc:
        return (False, "", str(exc))

    manifest = payload["manifest"]
    signature = payload["signature"]
    stored_hash = payload["hash"]

    # 1) Integrity: recompute the manifest hash and compare.
    recomputed_hash = manifest_hash(manifest)
    if recomputed_hash != stored_hash:
        return (False, "", "manifest hash mismatch (content tampered)")

    # 2) Signature: recompute the keyed signature and compare.
    expected_signature = sign_manifest(manifest)
    if not hmac.compare_digest(expected_signature, signature):
        return (False, "", "HMAC mismatch (tampered or different key)")

    details = {
        "hmac_matches": True,
        "hash": recomputed_hash,
        "author": manifest.get("creation", {}).get("author", ""),
        "tool": manifest.get("creation", {}).get("tool", ""),
        "media_format": manifest.get("creation", {}).get("media_format", ""),
        "claim_generator": manifest.get("claim_generator", ""),
    }
    return (True, _canonical_json(details), "")


# ---------------------------------------------------------------------------
# ComfyUI-style node wrappers
# ---------------------------------------------------------------------------

class PSN_Manifest_HMAC_Embed:
    """Add a JSON manifest with a fixed-key HMAC to a media dict's metadata.

    Not C2PA and not tamper-proof (the key is public).  Builds the manifest,
    computes the HMAC, and returns a new media dict; pixels are untouched and
    no file is written.
    """

    DESCRIPTION = (
        "Adds a JSON provenance manifest with a fixed-key HMAC to a media "
        "dict's metadata. Not C2PA, not tamper-proof (the key is public), "
        "and it writes no file."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "media": ("MEDIA",),
                "author": ("STRING", {"default": "Anonymous", "multiline": False}),
                "tool": ("STRING", {"default": "ParametricStudio", "multiline": False}),
                "add_hmac": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "manifest_override": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("MEDIA", "STRING")
    RETURN_NAMES = ("media_with_manifest", "manifest_hash")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, media, author, tool, add_hmac, manifest_override=""):
        manifest = build_manifest(author, tool, media.get("format"), manifest_override)
        if add_hmac:
            signature = sign_manifest(manifest)
        else:
            # No HMAC: store an empty one; the check will report a mismatch
            # but the hash is still recorded.
            signature = ""
        embedded = embed_manifest(media, manifest, signature)
        return (embedded, manifest_hash(manifest))


class PSN_Manifest_HMAC_Check:
    """Recompute the hash and fixed-key HMAC of the manifest in a media dict.

    Not C2PA validation: a match shows only that the manifest still equals the
    hash and HMAC stored beside it, and anyone can make such a pair.
    """

    DESCRIPTION = (
        "Recomputes the hash and fixed-key HMAC of the manifest embedded in a "
        "media dict. Not C2PA validation; a match proves only consistency."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "media": ("MEDIA",),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("hmac_matches", "details", "error")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, media):
        matches, details, error = verify_manifest(media)
        return (matches, details, error)


NODE_CLASS_MAPPINGS = {
    "PSN_Manifest_HMAC_Embed": PSN_Manifest_HMAC_Embed,
    "PSN_Manifest_HMAC_Check": PSN_Manifest_HMAC_Check,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Manifest_HMAC_Embed": "Manifest HMAC Embed (not C2PA)",
    "PSN_Manifest_HMAC_Check": "Manifest HMAC Check (not C2PA)",
}
