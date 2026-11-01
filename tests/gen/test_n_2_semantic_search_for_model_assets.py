"""Tests for PSN Semantic Search for Model Assets (pure-logic core)."""

import json

import pytest

from psn_nodes.gen.n_2_semantic_search_for_model_assets import (
    PSN_Keyword_Index_Builder,
    PSN_Keyword_Search_Query,
    _psn_build_index,
    _psn_bow_vector,
    _psn_search,
    _psn_validate_folder_path,
    _psn_validate_index_name,
    SUPPORTED_KINDS,
)


def _make_assets():
    return [
        {"name": "red_car.png", "path": "/assets/red_car.png", "kind": "image", "text": "red car"},
        {"name": "blue_sky.png", "path": "/assets/blue_sky.png", "kind": "image", "text": "blue sky"},
        {"name": "model_doc.pdf", "path": "/docs/model_doc.pdf", "kind": "pdf", "text": "model documentation"},
    ]


def test_index_builder_creates_index_with_stats():
    node = PSN_Keyword_Index_Builder()
    assets_json = json.dumps(_make_assets())
    index, stats = node.run(
        folder_path="/assets",
        index_name="test_index",
        assets_json=assets_json,
    )
    assert isinstance(index, dict)
    assert index["index_name"] == "test_index"
    assert index["item_count"] == 3
    assert len(index["items"]) == 3
    stats_obj = json.loads(stats)
    assert stats_obj["item_count"] == 3
    assert stats_obj["index_name"] == "test_index"


def test_index_builder_rejects_bad_kind():
    bad_assets = [{"name": "x", "path": "/x", "kind": "video", "text": ""}]
    with pytest.raises(ValueError, match="kind"):
        _psn_build_index("/assets", "idx", bad_assets)


def test_index_builder_rejects_duplicate_paths():
    dup_assets = [
        {"name": "a", "path": "/a.png", "kind": "image", "text": ""},
        {"name": "b", "path": "/a.png", "kind": "image", "text": ""},
    ]
    with pytest.raises(ValueError, match="duplicate"):
        _psn_build_index("/assets", "idx", dup_assets)


def test_index_builder_rejects_empty_index_name():
    with pytest.raises(ValueError, match="index_name"):
        _psn_validate_index_name("   ")


def test_index_builder_rejects_path_separator_in_name():
    with pytest.raises(ValueError, match="path separators"):
        _psn_validate_index_name("foo/bar")


def test_search_returns_correct_top_result():
    assets = _make_assets()
    index = _psn_build_index("/assets", "idx", assets)
    node = PSN_Keyword_Search_Query()
    result, _ = node.run(
        query_text="red car",
        keyword_index=index,
        top_k=3,
        min_score=-1.0,
    )
    assert result["result_count"] == 3
    top = result["results"][0]
    assert top["path"] == "/assets/red_car.png"
    assert top["name"] == "red_car.png"


def test_search_respects_min_score_threshold():
    assets = _make_assets()
    index = _psn_build_index("/assets", "idx", assets)
    node = PSN_Keyword_Search_Query()
    # Very high threshold should filter out most results.
    result, _ = node.run(
        query_text="red car",
        keyword_index=index,
        top_k=3,
        min_score=0.99,
    )
    # With deterministic pseudo-embeddings, scores are unlikely to be >= 0.99
    # for unrelated items; the matching item may or may not pass.
    # We just verify the result is a valid structure and count <= 3.
    assert result["result_count"] <= 3
    for r in result["results"]:
        assert r["score"] >= 0.99


def test_search_respects_top_k():
    assets = _make_assets()
    index = _psn_build_index("/assets", "idx", assets)
    node = PSN_Keyword_Search_Query()
    result, _ = node.run(
        query_text="anything",
        keyword_index=index,
        top_k=1,
        min_score=-1.0,
    )
    assert result["result_count"] == 1
    assert len(result["results"]) == 1


def test_search_rejects_invalid_top_k():
    assets = _make_assets()
    index = _psn_build_index("/assets", "idx", assets)
    node = PSN_Keyword_Search_Query()
    with pytest.raises(ValueError, match="top_k"):
        node.run(query_text="q", keyword_index=index, top_k=0, min_score=0.0)


def test_search_rejects_invalid_min_score():
    assets = _make_assets()
    index = _psn_build_index("/assets", "idx", assets)
    node = PSN_Keyword_Search_Query()
    with pytest.raises(ValueError, match="min_score"):
        node.run(query_text="q", keyword_index=index, top_k=1, min_score=2.0)


def test_search_rejects_non_dict_index():
    node = PSN_Keyword_Search_Query()
    with pytest.raises(ValueError, match="keyword_index"):
        node.run(query_text="q", keyword_index="not a dict", top_k=1, min_score=0.0)


def test_embed_is_deterministic():
    v1 = _psn_bow_vector("hello world")
    v2 = _psn_bow_vector("hello world")
    assert v1 == v2
    v3 = _psn_bow_vector("different text")
    assert v1 != v3


def test_embed_dimension():
    v = _psn_bow_vector("test")
    assert len(v) == 64


def test_embed_similarity_for_shared_tokens():
    # Texts sharing tokens should have higher cosine similarity than disjoint texts.
    v_shared = _psn_bow_vector("red car")
    v_same = _psn_bow_vector("red car")
    v_diff = _psn_bow_vector("blue sky")
    sim_same = sum(a * b for a, b in zip(v_shared, v_same))
    sim_diff = sum(a * b for a, b in zip(v_shared, v_diff))
    assert sim_same > sim_diff


def test_folder_path_validation():
    assert _psn_validate_folder_path("/valid/path") == "/valid/path"
    with pytest.raises(ValueError, match="folder_path"):
        _psn_validate_folder_path("")
    with pytest.raises(ValueError, match="folder_path"):
        _psn_validate_folder_path(123)


def test_builder_rejects_invalid_json():
    node = PSN_Keyword_Index_Builder()
    with pytest.raises(ValueError, match="JSON"):
        node.run(
            folder_path="/assets",
                index_name="idx",
            assets_json="not valid json",
        )


def test_builder_rejects_non_list_json():
    node = PSN_Keyword_Index_Builder()
    with pytest.raises(ValueError, match="JSON list"):
        node.run(
            folder_path="/assets",
                index_name="idx",
            assets_json='{"not": "a list"}',
        )


def test_builder_has_no_embedding_model_input_or_field():
    assert "embedding_model" not in PSN_Keyword_Index_Builder.INPUT_TYPES()["required"]
    node = PSN_Keyword_Index_Builder()
    index, stats = node.run("/assets", "idx", json.dumps(_make_assets()))
    assert "embedding_model" not in index and "embedding_model" not in json.loads(stats)
    assert "embedding" not in index["items"][0]
    assert len(index["items"][0]["vector"]) == 64
    assert "no embedding model" in PSN_Keyword_Index_Builder.DESCRIPTION


def test_registry_renamed():
    from psn_nodes.gen import n_2_semantic_search_for_model_assets as m
    assert "PSN_Semantic_Index_Builder" not in m.NODE_CLASS_MAPPINGS
    assert "PSN_Semantic_Search_Query" not in m.NODE_CLASS_MAPPINGS
    assert m.NODE_CLASS_MAPPINGS["PSN_Keyword_Index_Builder"] is PSN_Keyword_Index_Builder
    assert m.NODE_CLASS_MAPPINGS["PSN_Keyword_Search_Query"] is PSN_Keyword_Search_Query
    assert PSN_Keyword_Search_Query.RETURN_TYPES[0] == "SEARCH_RESULTS"
    assert "not meaning" in PSN_Keyword_Search_Query.DESCRIPTION


def test_search_is_word_overlap_not_meaning():
    # synonyms do not match; shared words do. exact cosine for a one-token overlap.
    index = _psn_build_index("/assets", "idx", [
        {"name": "a", "path": "/x", "kind": "image", "text": "automobile"},
        {"name": "a", "path": "/y", "kind": "image", "text": "car"},
    ])
    result, _ = PSN_Keyword_Search_Query().run("car", index, 2, -1.0)
    by_path = {r["path"]: r["score"] for r in result["results"]}
    assert result["results"][0]["path"] == "/y"
    assert abs(by_path["/y"] - 1.0) < 1e-5   # identical single token -> identical vector
    assert by_path["/x"] < 0.5               # 'automobile' is not treated as 'car'
