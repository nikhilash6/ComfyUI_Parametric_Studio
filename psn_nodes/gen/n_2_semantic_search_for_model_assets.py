"""PSN Keyword Search for Model Assets (pure-logic core).

This module builds and searches a keyword index over an explicit list of asset
descriptors.  It uses no embedding model, no reranker and no FAISS, and it does
not scan the filesystem; callers supply the descriptors.

  * PSN_Keyword_Index_Builder  -- validates the index configuration and
    builds an in-memory index from a list of asset descriptors
    (name, path, kind, text).  Each item's name and text are turned into a
    64-bucket hashed bag-of-words vector (SHA-256 of each token picks a bucket
    and a sign).
  * PSN_Keyword_Search_Query   -- builds the same kind of vector for the
    query, scores it against the index by cosine similarity, applies a
    minimum-score threshold, and returns the top-k matches.  A score reflects
    shared words (and some hash-bucket collisions), not meaning: "car" does
    not match "automobile".

All functions and node wrappers take plain values (strings, numbers, lists,
JSON text).  No sockets, no file/OS access, no network, no torch, no ComfyUI
imports, no eval/exec.  The "keyword_index" and "search_results" outputs are
plain Python dicts (JSON-serialisable) so they can be passed between nodes.
"""

import hashlib
import json
import math
import re

CAT = "ParametricStudio/SemanticSearch"

# Supported asset kinds (images and PDFs per the spec).
SUPPORTED_KINDS = ("image", "pdf")

# Number of hash buckets in the bag-of-words vector.
_EMB_DIM = 64

# Simple stop words to ignore when building the bag-of-words vector.
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "shall", "it", "its", "this",
    "that", "these", "those", "i", "you", "he", "she", "we", "they", "me",
    "him", "her", "us", "them", "my", "your", "his", "our", "their",
})


def _psn_tokenize(text):
    """Lowercase and split text into alphanumeric tokens, dropping stop words."""
    if text is None:
        return []
    text = str(text).lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    return [t for t in tokens if t not in _STOP_WORDS]


def _psn_bow_vector(text):
    """Hashed bag-of-words unit vector for a string.

    A fixed-length unit vector built by hashing each token (stop words
    dropped) into one of _EMB_DIM buckets with a +1/-1 sign.  It captures which
    words appear, not what they mean.  Identical text -> identical vector;
    texts sharing tokens score higher than texts with none.
    """
    if text is None:
        text = ""
    text = str(text)
    tokens = _psn_tokenize(text)
    vec = [0.0] * _EMB_DIM
    for token in tokens:
        token_bytes = token.encode("utf-8")
        # Use a stable hash to pick a bucket and a sign.
        h = hashlib.sha256(token_bytes).digest()
        bucket = int.from_bytes(h[:4], "big") % _EMB_DIM
        sign_byte = h[4]
        sign = 1.0 if (sign_byte & 1) == 0 else -1.0
        vec[bucket] += sign
    # Normalise to unit length.
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _psn_cosine(a, b):
    """Cosine similarity between two equal-length vectors."""
    if len(a) != len(b):
        raise ValueError("vector dimension mismatch")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _psn_validate_index_name(index_name):
    """Validate an index name: non-empty, no path separators, length cap."""
    if not isinstance(index_name, str):
        raise ValueError("index_name must be a string")
    name = index_name.strip()
    if not name:
        raise ValueError("index_name must not be empty")
    if len(name) > 128:
        raise ValueError("index_name too long (max 128 chars)")
    if "/" in name or "\\" in name:
        raise ValueError("index_name must not contain path separators")
    return name


def _psn_validate_folder_path(folder_path):
    """Validate a folder path string (no actual filesystem access)."""
    if not isinstance(folder_path, str):
        raise ValueError("folder_path must be a string")
    path = folder_path.strip()
    if not path:
        raise ValueError("folder_path must not be empty")
    if len(path) > 1024:
        raise ValueError("folder_path too long (max 1024 chars)")
    return path


def _psn_build_index(folder_path, index_name, assets):
    """Build an in-memory keyword index from asset descriptors.

    Args:
        folder_path: validated folder path string (recorded only).
        index_name: validated index name.
        assets: list of dicts, each with keys:
            "name" (str), "path" (str), "kind" (str in SUPPORTED_KINDS),
            "text" (str, optional, default "").

    Returns:
        dict with keys: index_name, folder_path,
        item_count, items (list of {name, path, kind, text, vector}).
    """
    if not isinstance(assets, list):
        raise ValueError("assets must be a list")
    items = []
    seen_paths = set()
    for i, asset in enumerate(assets):
        if not isinstance(asset, dict):
            raise ValueError("asset %d must be a dict" % i)
        name = asset.get("name", "")
        path = asset.get("path", "")
        kind = asset.get("kind", "")
        text = asset.get("text", "")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("asset %d: name must be a non-empty string" % i)
        if not isinstance(path, str) or not path.strip():
            raise ValueError("asset %d: path must be a non-empty string" % i)
        if kind not in SUPPORTED_KINDS:
            raise ValueError(
                "asset %d: kind '%s' not supported (use %s)"
                % (i, kind, ", ".join(SUPPORTED_KINDS))
            )
        if not isinstance(text, str):
            raise ValueError("asset %d: text must be a string" % i)
        if path in seen_paths:
            raise ValueError("asset %d: duplicate path '%s'" % (i, path))
        seen_paths.add(path)
        # Combine name and text so both contribute.
        emb = _psn_bow_vector(name + " " + text)
        items.append({
            "name": name,
            "path": path,
            "kind": kind,
            "text": text,
            "vector": emb,
        })
    return {
        "index_name": index_name,
        "folder_path": folder_path,
        "item_count": len(items),
        "items": items,
    }


def _psn_search(index, query_text, top_k, min_score):
    """Search a keyword index with a query.

    Args:
        index: dict produced by _psn_build_index.
        query_text: natural-language query string.
        top_k: number of results to return (int >= 1).
        min_score: minimum cosine similarity threshold (float in [-1, 1]).

    Returns:
        dict with keys: query, top_k, min_score, result_count,
        results (list of {name, path, kind, score}).
    """
    if not isinstance(index, dict):
        raise ValueError("keyword_index must be a dict")
    if "items" not in index:
        raise ValueError("keyword_index missing 'items'")
    if not isinstance(query_text, str):
        raise ValueError("query_text must be a string")
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise ValueError("top_k must be an integer")
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    if not isinstance(min_score, (int, float)) or isinstance(min_score, bool):
        raise ValueError("min_score must be a number")
    if min_score < -1.0 or min_score > 1.0:
        raise ValueError("min_score must be in [-1, 1]")

    q_emb = _psn_bow_vector(query_text)
    scored = []
    for item in index["items"]:
        score = _psn_cosine(q_emb, item["vector"])
        if score >= min_score:
            scored.append({
                "name": item["name"],
                "path": item["path"],
                "kind": item["kind"],
                "score": round(score, 6),
            })
    # Sort by score descending, then by name for stability.
    scored.sort(key=lambda r: (-r["score"], r["name"]))
    results = scored[:top_k]
    return {
        "query": query_text,
        "top_k": top_k,
        "min_score": min_score,
        "result_count": len(results),
        "results": results,
    }


class PSN_Keyword_Index_Builder:
    """Build an in-memory hashed bag-of-words keyword index from asset descriptors.

    Pure-logic core: validates configuration and builds the index.  No
    embedding model, no filesystem scanning, no torch, no FAISS.
    """

    DESCRIPTION = ("Builds a hashed bag-of-words keyword index from the asset descriptors you "
                   "supply. It uses no embedding model and does not scan any folder.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "", "multiline": False}),
                "index_name": ("STRING", {"default": "my_index", "multiline": False}),
                "assets_json": ("STRING", {
                    "default": "[]",
                    "multiline": True,
                    "tooltip": "JSON list of asset descriptors: "
                               '[{"name":"a.png","path":"/a.png","kind":"image","text":"red car"}]',
                }),
            },
        }

    RETURN_TYPES = ("KEYWORD_INDEX", "STRING")
    RETURN_NAMES = ("keyword_index", "index_stats")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, folder_path, index_name, assets_json):
        path = _psn_validate_folder_path(folder_path)
        name = _psn_validate_index_name(index_name)
        try:
            assets = json.loads(assets_json)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError("assets_json is not valid JSON: %s" % e)
        if not isinstance(assets, list):
            raise ValueError("assets_json must decode to a JSON list")
        index = _psn_build_index(path, name, assets)
        stats = json.dumps({
            "index_name": name,
            "folder_path": path,
            "item_count": index["item_count"],
        }, indent=2)
        return (index, stats)


class PSN_Keyword_Search_Query:
    """Rank indexed assets by hashed bag-of-words cosine overlap with a query.

    Pure-logic core: cosine search with threshold and top-k.  It matches shared
    words, not meaning.  No embedding model, no torch, no FAISS, no reranker.
    """

    DESCRIPTION = ("Ranks indexed assets by hashed bag-of-words cosine overlap with the query "
                   "text, with a minimum score and top-k. It matches shared words, not meaning.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "query_text": ("STRING", {"default": "", "multiline": False}),
                "keyword_index": ("KEYWORD_INDEX",),
                "top_k": ("INT", {"default": 5, "min": 1, "max": 100, "step": 1}),
                "min_score": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.001}),
            },
        }

    RETURN_TYPES = ("SEARCH_RESULTS", "STRING")
    RETURN_NAMES = ("search_results", "results_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, query_text, keyword_index, top_k, min_score):
        result = _psn_search(keyword_index, query_text, top_k, min_score)
        results_json = json.dumps(result, indent=2)
        return (result, results_json)


NODE_CLASS_MAPPINGS = {
    "PSN_Keyword_Index_Builder": PSN_Keyword_Index_Builder,
    "PSN_Keyword_Search_Query": PSN_Keyword_Search_Query,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Keyword_Index_Builder": "Keyword Index Builder (no embedding model)",
    "PSN_Keyword_Search_Query": "Keyword Search Query (word overlap, not semantic)",
}
