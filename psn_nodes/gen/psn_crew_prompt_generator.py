"""
PSN_Role_Text_Concat: appends user-supplied text for each listed role to a brief, in role order.

No agents and no LLM are involved. The user supplies a JSON object that maps role names to
the text each role should contribute. The node checks each role against an allow-list and
appends "[Role]: text" lines to the brief in the order the roles are listed. A role with no
supplied text, or one that is not on the allow-list, adds nothing and is named in the report.

No network, no torch, no file access.
"""

import json

CAT = "ParametricStudio/Crew"

# Allowed roles for validation (allow-list check)
ALLOWED_ROLES = [
    "Lyricist",
    "Composer",
    "Producer",
    "Vocalist",
    "SoundEngineer",
    "Director",
    "Editor",
    "MixingEngineer",
    "MasteringEngineer",
    "CreativeDirector"
]


def _split_roles(roles):
    """Roles arrive as a comma-separated string (or a list); return a clean list of names."""
    if isinstance(roles, str):
        roles = roles.split(",")
    return [str(r).strip() for r in (roles or []) if str(r).strip()]


class PSN_Role_Text_Concat:
    """Appends user-supplied per-role text (JSON) to a brief, in role order. No agents, no LLM."""

    DESCRIPTION = ("Appends the text you supply for each listed role (from a JSON object) to the brief, in role order. "
                   "No agents and no LLM: it writes nothing itself, and a role with no supplied text adds nothing.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "brief": ("STRING", {"default": "", "multiline": True}),
                "roles": ("STRING", {"default": "Lyricist, Composer, Producer", "tooltip": "Comma-separated role names, appended in this order. Allowed: " + ", ".join(ALLOWED_ROLES)}),
                "role_text_json": ("STRING", {"default": "{}", "multiline": True, "tooltip": "JSON object mapping role name to the text to append. Example: {\"Lyricist\": \"Verse 1...\", \"Composer\": \"Key of C...\"}"})
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("combined_text", "role_report")
    FUNCTION = "run"
    CATEGORY = CAT

    @staticmethod
    def _parse_role_text(role_text_json):
        """Parse the JSON object of role -> text. Returns (dict of str->str, error or None)."""
        if not role_text_json or not role_text_json.strip():
            return {}, None
        try:
            data = json.loads(role_text_json)
        except json.JSONDecodeError:
            return {}, "role_text_json is not valid JSON"
        if not isinstance(data, dict):
            return {}, "role_text_json must be a JSON object"
        return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}, None

    def run(self, brief, roles, role_text_json):
        role_list = _split_roles(roles)
        valid_roles = [r for r in role_list if r in ALLOWED_ROLES]
        rejected = [r for r in role_list if r not in ALLOWED_ROLES]
        if not valid_roles:
            return (brief, "Error: no roles from the allow-list were given; brief returned unchanged.")

        texts, err = self._parse_role_text(role_text_json)

        combined = brief
        appended, skipped = [], []
        for role in valid_roles:
            text = texts.get(role)
            if not text:
                skipped.append(role)
                continue
            line = f"[{role}]: {text}"
            combined = f"{combined}\n{line}" if combined else line
            appended.append(role)

        report = [f"Appended: {', '.join(appended) or 'none'}",
                  f"No text supplied: {', '.join(skipped) or 'none'}",
                  f"Not on allow-list: {', '.join(rejected) or 'none'}"]
        if err:
            report.append(f"Error: {err}")
        return (combined, "\n".join(report))


NODE_CLASS_MAPPINGS = {
    "PSN_Role_Text_Concat": PSN_Role_Text_Concat
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Role_Text_Concat": "Role Text Concatenator (no agents, no LLM)"
}
