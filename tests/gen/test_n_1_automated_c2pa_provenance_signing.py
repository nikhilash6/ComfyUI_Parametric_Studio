"""Tests for the manifest + fixed-key HMAC embed/check nodes (not C2PA)."""

import base64
import hashlib
import hmac
import json

import pytest

import psn_nodes.gen.n_1_automated_c2pa_provenance_signing as mod

from psn_nodes.gen.n_1_automated_c2pa_provenance_signing import (
    PSN_Manifest_HMAC_Embed,
    PSN_Manifest_HMAC_Check,
    build_manifest,
    embed_manifest,
    extract_manifest,
    manifest_hash,
    sign_manifest,
    verify_manifest,
)


def _media(fmt="png", pixels="PIXELDATA", metadata=None):
    return {"format": fmt, "pixels": pixels, "metadata": metadata or {}}


def test_sign_then_verify_roundtrip_is_valid():
    signer = PSN_Manifest_HMAC_Embed()
    verifier = PSN_Manifest_HMAC_Check()
    media = _media("png", pixels="abc123")
    signed, mhash = signer.run(media, "Alice", "PSN", True)
    # Pixel data must be untouched.
    assert signed["pixels"] == "abc123"
    # Manifest must be embedded.
    assert "psn_manifest" in signed["metadata"]
    assert "c2pa_manifest" not in signed["metadata"]
    # Hash is a 64-char hex string.
    assert len(mhash) == 64
    valid, details, error = verifier.run(signed)
    assert valid is True
    assert error == ""
    parsed = json.loads(details)
    assert parsed["author"] == "Alice"
    assert parsed["tool"] == "PSN"
    assert parsed["hash"] == mhash
    assert parsed["hmac_matches"] is True and "valid" not in parsed
    assert parsed["claim_generator"] == "PSN_Manifest_HMAC_Embed"


def test_tampering_pixel_data_does_not_break_manifest_but_hash_still_matches():
    # Tampering the *pixels* does not change the manifest (manifest is
    # metadata-only), so the manifest itself still verifies.  This documents
    # that the pure-logic layer protects the manifest, not the pixels.
    signer = PSN_Manifest_HMAC_Embed()
    verifier = PSN_Manifest_HMAC_Check()
    signed, _ = signer.run(_media("png", "orig"), "Bob", "T", True)
    tampered = dict(signed)
    tampered["pixels"] = "CHANGED"
    valid, _details, error = verifier.run(tampered)
    # Manifest is intact, so it still verifies.
    assert valid is True
    assert error == ""


def test_tampering_manifest_payload_fails_verification():
    signer = PSN_Manifest_HMAC_Embed()
    verifier = PSN_Manifest_HMAC_Check()
    signed, _ = signer.run(_media("png", "orig"), "Bob", "T", True)
    # Decode, alter the author, re-encode -> hash + signature now mismatch.
    raw = base64.b64decode(signed["metadata"]["psn_manifest"])
    payload = json.loads(raw.decode("utf-8"))
    payload["manifest"]["creation"]["author"] = "Mallory"
    signed["metadata"]["psn_manifest"] = base64.b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    valid, _details, error = verifier.run(signed)
    assert valid is False
    assert error != ""


def test_unsigned_manifest_fails_signature_check():
    signer = PSN_Manifest_HMAC_Embed()
    verifier = PSN_Manifest_HMAC_Check()
    signed, _ = signer.run(_media("mp4", "vid"), "Carol", "T", False)
    valid, _details, error = verifier.run(signed)
    assert valid is False
    assert "hmac" in error.lower()


def test_manifest_override_merges_and_is_reflected_in_details():
    signer = PSN_Manifest_HMAC_Embed()
    verifier = PSN_Manifest_HMAC_Check()
    override = json.dumps({"extra_field": "value42"})
    signed, _ = signer.run(_media("png", "x"), "Dave", "T", True, override)
    valid, details, error = verifier.run(signed)
    assert valid is True
    assert error == ""
    # The override is part of the manifest, so its hash differs from a
    # manifest built without it.
    base_manifest = build_manifest("Dave", "T", "png")
    override_manifest = build_manifest("Dave", "T", "png", override)
    assert manifest_hash(base_manifest) != manifest_hash(override_manifest)
    assert override_manifest["extra_field"] == "value42"


def test_invalid_manifest_override_json_raises():
    with pytest.raises(ValueError):
        build_manifest("Eve", "T", "png", "{not valid json")


def test_invalid_media_format_raises():
    with pytest.raises(ValueError):
        build_manifest("Eve", "T", "gif")


def test_empty_author_raises():
    with pytest.raises(ValueError):
        build_manifest("", "T", "png")


def test_non_string_author_raises():
    with pytest.raises(ValueError):
        build_manifest(123, "T", "png")


def test_missing_manifest_in_media_reports_error_not_crash():
    verifier = PSN_Manifest_HMAC_Check()
    valid, details, error = verifier.run(_media("png", "x"))
    assert valid is False
    assert details == ""
    assert "no embedded manifest" in error


def test_malformed_manifest_payload_reports_error():
    verifier = PSN_Manifest_HMAC_Check()
    media = _media("png", "x", {"psn_manifest": "!!!not-base64!!!"})
    valid, details, error = verifier.run(media)
    assert valid is False
    assert details == ""
    assert error != ""


def test_extract_manifest_missing_key_raises():
    payload = {"manifest": {}, "signature": "sig"}  # missing 'hash'
    encoded = base64.b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    media = _media("png", "x", {"psn_manifest": encoded})
    with pytest.raises(ValueError):
        extract_manifest(media)


def test_sign_manifest_requires_bytes_key():
    with pytest.raises(ValueError):
        sign_manifest({"a": 1}, key="not-bytes")


def test_manifest_hash_is_deterministic_and_order_independent():
    m1 = {"b": 2, "a": 1}
    m2 = {"a": 1, "b": 2}
    assert manifest_hash(m1) == manifest_hash(m2)


def test_hmac_uses_public_fixed_key_so_anyone_can_forge():
    """The key is in the source: an outside party can build a matching HMAC."""
    forged_manifest = build_manifest("Mallory", "Evil", "png")
    sig = hmac.new(
        mod._DEFAULT_KEY, mod._canonical_json(forged_manifest).encode(), hashlib.sha256
    ).hexdigest()
    forged = embed_manifest(_media("png", "x"), forged_manifest, sig)
    valid, details, error = PSN_Manifest_HMAC_Check().run(forged)
    assert valid is True  # proves consistency only, not authorship
    assert json.loads(details)["author"] == "Mallory"


def test_c2pa_claims_are_gone():
    m = build_manifest("A", "T", "png")
    assert "c2pa_version" not in m
    assert m["claim_generator"] == "PSN_Manifest_HMAC_Embed"
    for old in ("PSN_C2PA_Signer", "PSN_C2PA_Verifier"):
        assert old not in mod.NODE_CLASS_MAPPINGS
        assert not hasattr(mod, old)
    assert PSN_Manifest_HMAC_Check.RETURN_NAMES == ("hmac_matches", "details", "error")
    assert PSN_Manifest_HMAC_Embed.RETURN_NAMES == ("media_with_manifest", "manifest_hash")
    assert "Not C2PA" in PSN_Manifest_HMAC_Embed.DESCRIPTION
    assert "Not C2PA" in PSN_Manifest_HMAC_Check.DESCRIPTION


def test_node_mappings_are_registered():
    from psn_nodes.gen.n_1_automated_c2pa_provenance_signing import (
        NODE_CLASS_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS,
    )
    assert "PSN_Manifest_HMAC_Embed" in NODE_CLASS_MAPPINGS
    assert "PSN_Manifest_HMAC_Check" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Manifest_HMAC_Embed"] == "Manifest HMAC Embed (not C2PA)"
