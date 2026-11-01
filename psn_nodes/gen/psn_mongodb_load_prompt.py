"""PSN_Prompt_Document_Lookup (pure logic).

Looks up a prompt document by id in a JSON mapping that you paste in. No
database is used: there is no pymongo, network, file or OS access.

Inputs:
    documents_json (STRING): JSON text mapping doc_id -> {"prompt": str, "params": dict}
    doc_id     (STRING): the id of the document to fetch

Outputs:
    prompt (STRING): the stored prompt text ("" if missing)
    params (STRING): the stored params serialized as JSON ("" if missing)
    found  (BOOLEAN): whether the document was found
    reason (STRING): human-readable status / error message
"""

import json

CAT = "ParametricStudio/Database"


def _parse_documents_json(documents_json):
    """Parse the documents_json JSON text into a dict.

    Returns (data, error).  On success error is None and data is a dict.
    On failure data is None and error is a descriptive string.
    """
    if not isinstance(documents_json, str):
        return None, "documents_json must be a JSON string"
    text = documents_json.strip()
    if not text:
        return None, "documents_json is empty"
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as exc:
        return None, "documents_json is not valid JSON: %s" % exc
    if not isinstance(data, dict):
        return None, "documents_json must be a JSON object mapping id -> document"
    return data, None


def _fetch_document(data, doc_id):
    """Fetch a document by id from the parsed mapping.

    Returns (doc, error).  doc is the stored document (a dict) or None.
    """
    if not isinstance(doc_id, str):
        return None, "doc_id must be a string"
    if doc_id not in data:
        return None, "document not found: %s" % doc_id
    doc = data[doc_id]
    if not isinstance(doc, dict):
        return None, "document for %s is not an object" % doc_id
    return doc, None


def _extract_prompt(doc):
    prompt = doc.get("prompt", "")
    if not isinstance(prompt, str):
        prompt = str(prompt)
    return prompt


def _extract_params(doc):
    params = doc.get("params", {})
    if not isinstance(params, (dict, list)):
        params = {"value": params}
    try:
        return json.dumps(params, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return json.dumps({"value": str(params)}, sort_keys=True)


class PSN_Prompt_Document_Lookup:
    """Fetch a prompt document by id from pasted JSON text."""

    DESCRIPTION = (
        "Looks up an id in a JSON mapping of id to {prompt, params} that you paste in. "
        "Uses no database and reads no file."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "documents_json": ("STRING", {"default": "{}", "multiline": True}),
                "doc_id": ("STRING", {"default": ""}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("prompt", "params", "found", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, documents_json, doc_id):
        data, err = _parse_documents_json(documents_json)
        if err is not None:
            return ("", "", False, err)

        doc, err = _fetch_document(data, doc_id)
        if err is not None:
            return ("", "", False, err)

        prompt = _extract_prompt(doc)
        params = _extract_params(doc)
        return (prompt, params, True, "ok")


NODE_CLASS_MAPPINGS = {"PSN_Prompt_Document_Lookup": PSN_Prompt_Document_Lookup}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Prompt_Document_Lookup": "PSN Prompt Document Lookup (pasted JSON, no database)"}
