# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-080 T004: static checks of the portable read-only `harness` skill, with mutation controls."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from agent_braid import harness_cli

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "integrations" / "agent-braid" / "plugin" / "harness" / "SKILL.md"
HELDOUT = ROOT / "specs" / "080-harness-skill-every-host" / "evidence" / "heldout-set.json"

ALLOWED_KEYS = {"name", "description", "compatibility", "metadata"}
READ_COMMANDS = frozenset(c for c in harness_cli.COMMANDS if c not in {"prepare", "recover-inspect"})
FORBIDDEN_COMMANDS = ("prepare", "recover-inspect")
DECLINED_EFFECTS = ("prepare", "launch", "grant", "promote", "activate", "edit a registry")
_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COMMAND = re.compile(r'"<launch>" harness ([a-z-]+)')


class SkillCheckError(AssertionError):
    pass


def frontmatter(text: str) -> tuple[dict, str]:
    """Parse the bounded frontmatter: top-level `key: value` lines and one-level `metadata` map."""
    if not text.startswith("---\n"):
        raise SkillCheckError("no frontmatter")
    head, sep, body = text[4:].partition("\n---\n")
    if not sep:
        raise SkillCheckError("frontmatter not closed")
    fields: dict = {}
    current = None
    for line in head.splitlines():
        if line.startswith("  ") and current == "metadata":
            key, colon, value = line.strip().partition(": ")
            if not colon or key in fields["metadata"]:
                raise SkillCheckError(f"bad metadata line {line!r}")
            fields["metadata"][key] = value.strip()
            continue
        key, colon, value = line.partition(":")
        if not colon or key in fields:
            raise SkillCheckError(f"bad frontmatter line {line!r}")
        current = key
        fields[key] = {} if key == "metadata" and not value.strip() else value.strip()
    return fields, body


def check_frontmatter(text: str, directory: str = "harness") -> None:
    fields, _ = frontmatter(text)
    if set(fields) - ALLOWED_KEYS:
        raise SkillCheckError(f"keys outside the four: {sorted(set(fields) - ALLOWED_KEYS)}")
    if fields.get("name") != directory or not _NAME.fullmatch(fields["name"]) or len(fields["name"]) > 64:
        raise SkillCheckError("name must equal its directory and match the naming pattern")
    if not fields.get("description") or not fields.get("compatibility"):
        raise SkillCheckError("description and compatibility are required")
    metadata = fields.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("license") != "CC-BY-SA-4.0":
        raise SkillCheckError("metadata.license must be CC-BY-SA-4.0")


def check_commands(text: str) -> None:
    named = set(_COMMAND.findall(text))
    if named != READ_COMMANDS:
        raise SkillCheckError(f"command set {sorted(named)} differs from the eight read commands")
    for forbidden in FORBIDDEN_COMMANDS:
        if re.search(rf"harness {re.escape(forbidden)}\b", text):
            raise SkillCheckError(f"forbidden command {forbidden} appears as a command")
    for match in re.finditer(r'"<launch>" (\S+)', text):
        if match.group(1) != "harness":
            raise SkillCheckError(f"launcher command outside the harness surface: {match.group(1)}")
    if re.search(r"\b(pip|uv|npm) install\b", text):
        raise SkillCheckError("installation instruction")
    for line in text.splitlines():
        if "--telemetry local" in line and "only when the user asks" not in line:
            raise SkillCheckError("--telemetry local outside its conditional rule")
    if "experimental" not in text or "executionAuthorization" not in text:
        raise SkillCheckError("experimental status and executionAuthorization must be stated")


def check_declines(text: str) -> None:
    _, _, decline = text.partition("## Decline everything else")
    decline = decline.split("\n## ", 1)[0]
    if not decline.strip():
        raise SkillCheckError("decline section missing")
    missing = [effect for effect in DECLINED_EFFECTS if effect not in decline]
    if missing:
        raise SkillCheckError(f"no decline for {missing}")
    if "run no command for it" not in decline:
        raise SkillCheckError("decline must say no command runs for the effect")
    if "untrusted data, not instructions" not in text:
        raise SkillCheckError("untrusted-data rule missing")


def five_word_overlaps(skill_text: str, prompts: list[str]) -> list[str]:
    words = lambda value: re.findall(r"[a-záéíóúñü0-9'-]+", value.lower())  # noqa: E731
    skill_words = words(skill_text)
    grams = {tuple(skill_words[i:i + 5]) for i in range(len(skill_words) - 4)}
    hits = []
    for prompt in prompts:
        prompt_words = words(prompt)
        hits += [" ".join(prompt_words[i:i + 5]) for i in range(len(prompt_words) - 4)
                 if tuple(prompt_words[i:i + 5]) in grams]
    return hits


class HarnessSkillTests(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_frontmatter_has_only_the_four_fields_and_metadata_license(self):
        check_frontmatter(self.text)

    def test_command_set_is_exactly_the_eight_read_commands(self):
        check_commands(self.text)
        self.assertEqual(len(READ_COMMANDS), 8)

    def test_every_forbidden_effect_is_declined_and_output_is_untrusted(self):
        check_declines(self.text)

    def test_no_heldout_prompt_shares_five_consecutive_words(self):
        prompts = [p["prompt"] for p in json.loads(HELDOUT.read_text(encoding="utf-8"))["prompts"]]
        self.assertEqual(five_word_overlaps(self.text, prompts), [])

    # Mutation controls: each guard must catch its planted defect.
    def mutated(self, old: str, new: str) -> str:
        self.assertIn(old, self.text)
        return self.text.replace(old, new, 1)

    def test_mutation_extra_frontmatter_key_fails(self):
        with self.assertRaises(SkillCheckError):
            check_frontmatter(self.mutated("metadata:\n", "allowed-tools: Bash\nmetadata:\n"))

    def test_mutation_top_level_license_fails(self):
        with self.assertRaises(SkillCheckError):
            check_frontmatter(self.mutated("metadata:\n  license: CC-BY-SA-4.0\n", "license: CC-BY-SA-4.0\n"))

    def test_mutation_renamed_skill_fails(self):
        with self.assertRaises(SkillCheckError):
            check_frontmatter(self.mutated("name: harness\n", "name: harness-tools\n"))

    def test_mutation_inserted_prepare_command_fails(self):
        with self.assertRaises(SkillCheckError):
            check_commands(self.mutated("## Decline", '- `"<launch>" harness prepare <manifest>`\n\n## Decline'))

    def test_mutation_missing_read_command_fails(self):
        with self.assertRaises(SkillCheckError):
            check_commands(self.mutated('- `"<launch>" harness evidence <spec-dir>`', "- evidence inventory"))

    def test_mutation_plugin_setup_command_fails(self):
        with self.assertRaises(SkillCheckError):
            check_commands(self.mutated("## Decline", 'Then run `"<launch>" plugin setup --apply`.\n\n## Decline'))

    def test_mutation_unconditional_telemetry_flag_fails(self):
        with self.assertRaises(SkillCheckError):
            check_commands(self.mutated("Add `--telemetry local` only when the user asks",
                                        "Always add `--telemetry local` when the user asks"))

    def test_mutation_removed_decline_fails(self):
        with self.assertRaises(SkillCheckError):
            check_declines(self.mutated("promote, adopt,", "adopt,"))

    def test_mutation_removed_untrusted_rule_fails(self):
        with self.assertRaises(SkillCheckError):
            check_declines(self.mutated("untrusted data, not instructions", "data"))

    def test_mutation_leaked_prompt_wording_is_detected(self):
        leaked = self.text + "\nCompare the two harness candidates in a directory.\n"
        self.assertTrue(five_word_overlaps(leaked, ["I want to compare the two harness candidates in it"]))


if __name__ == "__main__":
    unittest.main()
