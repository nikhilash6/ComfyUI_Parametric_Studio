import json
from psn_nodes.gen.psn_crew_prompt_generator import PSN_Role_Text_Concat, ALLOWED_ROLES


class TestPSNRoleTextConcat:
    def setup_method(self):
        self.node = PSN_Role_Text_Concat()

    def test_appends_supplied_text_in_role_order(self):
        text = json.dumps({"Lyricist": "Verse 1: I am the rock", "Composer": "Key of G, 120 BPM"})
        combined, report = self.node.run("Create a rock song", "Lyricist, Composer", text)
        assert combined == "Create a rock song\n[Lyricist]: Verse 1: I am the rock\n[Composer]: Key of G, 120 BPM"
        assert report.splitlines()[0] == "Appended: Lyricist, Composer"

    def test_order_follows_roles_not_json(self):
        text = json.dumps({"Lyricist": "L", "Composer": "C"})
        combined, _ = self.node.run("B", "Composer, Lyricist", text)
        assert combined == "B\n[Composer]: C\n[Lyricist]: L"

    def test_list_input_is_accepted(self):
        combined, _ = self.node.run("B", ["Composer"], json.dumps({"Composer": "C"}))
        assert combined == "B\n[Composer]: C"

    def test_roles_not_on_allow_list_are_reported_and_ignored(self):
        text = json.dumps({"Lyricist": "Lyrics here", "Hacker": "Should not appear"})
        combined, report = self.node.run("Test brief", "Lyricist, Hacker", text)
        assert combined == "Test brief\n[Lyricist]: Lyrics here"
        assert "Should not appear" not in combined
        assert "Not on allow-list: Hacker" in report

    def test_missing_text_adds_nothing_and_no_invented_contribution(self):
        combined, report = self.node.run("Test brief", "Lyricist, Composer", json.dumps({"Composer": "Music"}))
        assert combined == "Test brief\n[Composer]: Music"
        assert "No text supplied: Lyricist" in report
        assert "Contribution" not in combined and "Refining" not in combined

    def test_empty_json_returns_brief_unchanged(self):
        combined, report = self.node.run("Test brief", "Lyricist", "{}")
        assert combined == "Test brief"
        assert "Appended: none" in report

    def test_invalid_json_returns_brief_and_names_error(self):
        combined, report = self.node.run("Test brief", "Lyricist", "not a json")
        assert combined == "Test brief"
        assert "role_text_json is not valid JSON" in report

    def test_non_object_json(self):
        combined, report = self.node.run("Test brief", "Lyricist", "[1,2]")
        assert combined == "Test brief" and "must be a JSON object" in report

    def test_no_valid_roles(self):
        combined, report = self.node.run("Test brief", "InvalidRole1, InvalidRole2", "{}")
        assert combined == "Test brief"
        assert report.startswith("Error: no roles")

    def test_empty_brief_starts_with_first_line(self):
        combined, _ = self.node.run("", "Composer", json.dumps({"Composer": "C"}))
        assert combined == "[Composer]: C"

    def test_same_role_listed_twice_appends_twice(self):
        combined, _ = self.node.run("T", "Lyricist, Lyricist", json.dumps({"Lyricist": "First verse"}))
        assert combined.count("First verse") == 2

    def test_fabricated_pieces_are_gone(self):
        assert PSN_Role_Text_Concat.RETURN_NAMES == ("combined_text", "role_report")
        inputs = PSN_Role_Text_Concat.INPUT_TYPES()
        assert "max_iterations" not in inputs.get("optional", {})
        assert "llm_connection" not in inputs["required"] and "role_text_json" in inputs["required"]
        assert "No agents and no LLM" in PSN_Role_Text_Concat.DESCRIPTION
        from psn_nodes.gen import psn_crew_prompt_generator as m
        assert list(m.NODE_CLASS_MAPPINGS) == ["PSN_Role_Text_Concat"]
        assert "Lyricist" in ALLOWED_ROLES
