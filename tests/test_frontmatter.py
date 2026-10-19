"""SKILL.md frontmatter checks, following the Agent Skills spec (https://agentskills.io/specification)."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"


def frontmatter(text: str) -> dict[str, str]:
    """Parse the flat `key: value` frontmatter SKILL.md uses (no nesting, one line per key)."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError("SKILL.md must start with a --- frontmatter line")
    end = lines.index("---", 1)
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if not sep or not re.fullmatch(r"[a-z][a-z0-9_-]*", key):
            raise AssertionError(f"not a flat key: value line: {line!r}")
        fields[key] = value.strip()
    return fields


class FrontmatterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields = frontmatter(SKILL.read_text(encoding="utf-8"))

    def test_name(self):
        name = self.fields.get("name", "")
        self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)
        self.assertEqual(name, "ornament")

    def test_description(self):
        desc = self.fields.get("description", "")
        self.assertTrue(desc, "description is required")
        self.assertLessEqual(len(desc), 1024)
        self.assertNotRegex(desc, r"[<>]", "no angle brackets in the description")
        # An unquoted YAML value must not contain ": " or " #".
        if desc[0] not in "'\"":
            self.assertNotIn(": ", desc)
            self.assertNotIn(" #", desc)

    def test_triggers_in_english_and_russian(self):
        desc = self.fields["description"]
        for trigger in ("Ornament Health", "biomarkers", "show my labs", "анализы", "биомаркеры"):
            self.assertIn(trigger, desc)

    def test_license_and_metadata(self):
        self.assertEqual(self.fields.get("license"), "MIT")
        metadata = json.loads(self.fields["metadata"])
        self.assertEqual(metadata["openclaw"]["primaryEnv"], "ORNAMENT_API_KEY")

    def test_only_known_keys(self):
        allowed = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
        self.assertLessEqual(set(self.fields), allowed)


if __name__ == "__main__":
    unittest.main()
