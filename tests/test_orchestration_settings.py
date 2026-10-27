# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-057 T022: the orchestration settings schema and the scope resolver."""

from __future__ import annotations

import ast
import itertools
import json
import os
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from agent_braid import ownership
from tests.test_orchestration_bounds import FORBIDDEN_IMPORTS
from tests.test_ownership_receipt import git

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "specs/057-claude-orchestration-advisory/contracts/orchestration-settings.schema.json").read_text("utf-8")
)
INPUT = Draft202012Validator(SCHEMA)
RESOLVED = Draft202012Validator({"$schema": SCHEMA["$schema"], "$defs": SCHEMA["$defs"], "$ref": "#/$defs/resolvedSettings"})
DIGEST = "a" * 64
VERSION = ownership.SETTINGS_VERSION
SCOPES = ownership.ORCHESTRATION_SCOPES
GUARDS = ownership.GUARD_MODES
EFFECTIVE = {
    "effectiveNotificationMode": "pull",
    "effectiveDelivery": "mailbox",
    "whisperStatus": "companion-SPEC-058-not-enabled-here",
    "enforcement": "none-in-SPEC-057",
    "settingsSource": "operator-owned-location",
}


def doc(scope: str, **settings) -> dict:
    return {"schemaVersion": VERSION, scope: settings}


def resolve(**scopes) -> dict:
    result = ownership.resolve_settings({s: doc(s, **v) for s, v in scopes.items()})
    assert not list(RESOLVED.iter_errors(result)), list(RESOLVED.iter_errors(result))
    return result


class SchemaAgreementTests(unittest.TestCase):
    def test_module_and_schema_agree_on_enums_and_patterns(self):
        scope = SCHEMA["$defs"]["scopeSettings"]["properties"]
        self.assertEqual(tuple(scope["notificationMode"]["enum"]), ownership.NOTIFICATION_MODES)
        self.assertEqual(tuple(scope["notificationStrategy"]["enum"]), ownership.NOTIFICATION_STRATEGIES)
        self.assertEqual(tuple(scope["guardMode"]["enum"]), ownership.GUARD_MODES)
        self.assertEqual(SCHEMA["properties"]["schemaVersion"]["const"], ownership.SETTINGS_VERSION)
        value = SCHEMA["$defs"]["extensionValue"]["oneOf"]
        self.assertEqual(value[3]["pattern"], ownership.REPOSITORY_TEXT_PATTERN)
        self.assertEqual(value[4]["items"]["pattern"], ownership.REPOSITORY_TEXT_PATTERN)

    def test_validator_and_schema_agree_on_a_matrix_of_documents(self):
        cases = [
            {"schemaVersion": VERSION},
            {"schemaVersion": "other"},
            {"user": {}},
            {"schemaVersion": VERSION, "user": {"guardMode": "block"}},
            {"schemaVersion": VERSION, "user": {"guardMode": "strict"}},
            {"schemaVersion": VERSION, "team": {}},
            {"schemaVersion": VERSION, "user": {"colour": "red"}},
            {"schemaVersion": VERSION, "user": {"notificationMode": "push"}},
            {"schemaVersion": VERSION, "user": {"notificationMode": "push", "notificationStrategy": "doorbell"}},
            {"schemaVersion": VERSION, "user": {"notificationMode": "push", "notificationStrategy": "mailbox-whisper"}},
            {"schemaVersion": VERSION, "user": {"notificationMode": "pull", "notificationStrategy": "megaphone"}},
            {"schemaVersion": VERSION, "user": {"notificationStrategy": "doorbell"}},
            {"schemaVersion": VERSION, "user": {"notificationStrategy": "mailbox-whisper"}},
            {"schemaVersion": VERSION, "user": {"notificationMode": "pull"}},
            {"schemaVersion": VERSION, "user": {"notificationMode": "queue"}},
            {"schemaVersion": VERSION, "extensions": {"SPEC-059": {"extensionVersion": "v0.1", "settings": {"a": 1}}}},
            {"schemaVersion": VERSION, "extensions": {"spec-059": {"extensionVersion": "v0.1", "settings": {}}}},
            {"schemaVersion": VERSION, "extensions": {"SPEC-059": {"extensionVersion": "v0.1", "settings": {"a": {}}}}},
            {"schemaVersion": VERSION, "extensions": {"SPEC-059": {"extensionVersion": "v0.1", "settings": {"a": "‮"}}}},
            {"schemaVersion": VERSION, "extensions": {"SPEC-059": {"extensionVersion": "v0.1", "settings": {"a": "x\n"}}}},
            {"schemaVersion": VERSION, "extensions": {"SPEC-059": {"extensionVersion": "v0.1", "settings": {"a": ["x"] * 17}}}},
            {"schemaVersion": VERSION, "extensions": {"SPEC-059": {"extensionVersion": "v0.1"}}},
            {"schemaVersion": VERSION, "extensions": {"SPEC-059": {"extensionVersion": "v0.1", "settings": {}, "x": 1}}},
            {"schemaVersion": VERSION, "repository": {"extensions": {"SPEC-059": {"extensionVersion": "v0", "settings": {"k": None}}}}},
        ]
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(not list(INPUT.iter_errors(case)), not ownership.validate_settings(case))


class ResolverTests(unittest.TestCase):
    def test_delivery_is_the_mailbox_in_every_scope_combination(self):
        choices = [None, {"notificationMode": "pull"}, {"notificationStrategy": "mailbox-whisper"},
                   {"notificationMode": "push", "notificationStrategy": "megaphone"},
                   {"notificationMode": "push", "notificationStrategy": "doorbell"}]
        for combination in itertools.product(choices, repeat=3):
            scopes = {s: c for s, c in zip(SCOPES, combination) if c is not None}
            with self.subTest(scopes=scopes):
                result = resolve(**scopes)
                for key, value in EFFECTIVE.items():
                    self.assertEqual(result[key], value)

    def test_an_extension_only_scope_does_not_decide_the_resolution(self):
        entry = {"extensionVersion": "v1", "settings": {}}
        result = ownership.resolve_settings({
            "conversation": doc("conversation", extensions={"SPEC-059": entry}),
            "user": doc("user", guardMode="warn")})
        self.assertEqual((result["resolvedFromScope"], result["guardMode"]), ("user", "warn"))

    def test_most_specific_scope_wins(self):
        result = resolve(conversation={"guardMode": "warn"}, repository={"guardMode": "audit"}, user={"guardMode": "off"})
        self.assertEqual((result["guardMode"], result["resolvedFromScope"]), ("warn", "conversation"))
        result = resolve(repository={"guardMode": "audit"}, user={"guardMode": "warn"})
        self.assertEqual((result["guardMode"], result["resolvedFromScope"]), ("audit", "repository"))
        self.assertEqual(resolve(user={"guardMode": "warn"})["resolvedFromScope"], "user")

    def test_defaults_when_nothing_is_set(self):
        result = ownership.resolve_settings({})
        self.assertEqual((result["guardMode"], result["resolvedFromScope"], result["scopeSources"]), ("off", "default", []))
        self.assertEqual(result["requestedNotificationStrategy"], "mailbox-whisper")
        self.assertEqual(result["pushStatus"], "not-requested")
        self.assertFalse(list(RESOLVED.iter_errors(result)))

    def test_conversation_may_raise_or_leave_the_mode(self):
        self.assertEqual(resolve(conversation={"guardMode": "block"}, user={"guardMode": "audit"})["guardMode"], "block")
        self.assertEqual(resolve(conversation={"notificationMode": "pull"}, user={"guardMode": "warn"})["guardMode"], "warn")

    def test_push_requests_are_recorded_and_never_effective(self):
        for strategy in ("megaphone", "doorbell"):
            result = resolve(user={"notificationMode": "push", "notificationStrategy": strategy})
            self.assertEqual((result["requestedNotificationMode"], result["requestedNotificationStrategy"]),
                             ("push", strategy))
            self.assertEqual(result["pushStatus"], "reserved-for-SPEC-059")
            self.assertEqual((result["effectiveNotificationMode"], result["effectiveDelivery"]), ("pull", "mailbox"))
        self.assertEqual(resolve(user={"notificationStrategy": "mailbox-whisper"})["pushStatus"], "not-requested")

    def test_a_more_specific_pull_replaces_a_less_specific_push_request(self):
        result = resolve(conversation={"notificationMode": "pull"},
                         user={"notificationMode": "push", "notificationStrategy": "doorbell"})
        self.assertEqual((result["requestedNotificationMode"], result["pushStatus"]), ("pull", "not-requested"))

    def test_contradictory_pairs_are_rejected(self):
        for settings in ({"notificationMode": "push", "notificationStrategy": "mailbox-whisper"},
                         {"notificationMode": "pull", "notificationStrategy": "megaphone"},
                         {"notificationMode": "pull", "notificationStrategy": "doorbell"},
                         {"notificationMode": "push"}, {"notificationStrategy": "doorbell"}):
            with self.subTest(settings=settings), self.assertRaises(ownership.SettingsRefused) as caught:
                ownership.resolve_settings({"user": doc("user", **settings)})
            self.assertEqual(caught.exception.code, "ERR-MALFORMED-INPUT")
            self.assertIn("contradictory-notification", [d.code for d in caught.exception.diagnostics])

    def test_unknown_values_scopes_and_members_are_rejected(self):
        bad = ({"schemaVersion": VERSION, "user": {"guardMode": "strict"}},
               {"schemaVersion": VERSION, "user": {"notificationMode": "queue"}},
               {"schemaVersion": VERSION, "user": {"notificationStrategy": "pager"}},
               {"schemaVersion": VERSION, "team": {}},
               {"schemaVersion": VERSION, "user": {"colour": "red"}},
               {"schemaVersion": VERSION, "colour": "red"},
               {"schemaVersion": "v9", "user": {}}, {"user": {}}, [], "text")
        for document in bad:
            with self.subTest(document=document), self.assertRaises(ownership.SettingsRefused) as caught:
                ownership.resolve_settings({"user": document})
            self.assertEqual(caught.exception.code, "ERR-MALFORMED-INPUT")
        with self.assertRaises(ownership.SettingsRefused):
            ownership.resolve_settings({"team": doc("user")})

    def test_a_document_may_carry_only_the_scope_of_its_location(self):
        both = {"schemaVersion": VERSION, "user": {}, "repository": {"guardMode": "block"}}
        with self.assertRaises(ownership.SettingsRefused):
            ownership.resolve_settings({"user": both})
        with self.assertRaises(ownership.SettingsRefused):
            ownership.parse_settings(json.dumps(both), "user")

    def test_resolution_reports_where_each_scope_came_from(self):
        result = resolve(conversation={}, repository={}, user={})
        self.assertEqual({s["scope"]: s["location"] for s in result["scopeSources"]}, ownership.SCOPE_LOCATIONS)
        self.assertEqual([s["scope"] for s in resolve(user={})["scopeSources"]], ["user"])


class FloorTests(unittest.TestCase):
    def test_block_at_repository_or_user_is_a_floor(self):
        for scope in ("repository", "user"):
            result = resolve(**{scope: {"guardMode": "block"}})
            self.assertEqual(result["guardModeFloor"], {"mode": "block", "scope": scope})
            self.assertEqual((result["guardMode"], result["guardModeLoweringRefused"]), ("block", False))

    def test_the_floor_cannot_be_lowered_by_any_combination(self):
        for floor_scopes in (("repository",), ("user",), ("repository", "user")):
            others = [s for s in SCOPES if s not in floor_scopes]
            for values in itertools.product((None, *GUARDS), repeat=len(others)):
                scopes = {s: {"guardMode": "block"} for s in floor_scopes}
                scopes.update({s: {"guardMode": v} for s, v in zip(others, values) if v is not None})
                with self.subTest(scopes=scopes):
                    result = resolve(**scopes)
                    self.assertEqual(result["guardMode"], "block")
                    self.assertEqual(result["guardModeFloor"]["scope"], "repository" if scopes.get("repository", {}).get("guardMode") == "block" else "user")

    def test_a_refused_lowering_is_recorded(self):
        result = resolve(conversation={"guardMode": "off"}, user={"guardMode": "block"})
        self.assertEqual((result["guardMode"], result["guardModeLoweringRefused"]), ("block", True))
        result = resolve(repository={"guardMode": "warn"}, user={"guardMode": "block"})
        self.assertEqual((result["guardModeFloor"], result["guardModeLoweringRefused"]),
                         ({"mode": "block", "scope": "user"}, True))

    def test_a_floor_offered_at_conversation_scope_is_not_a_floor(self):
        result = resolve(conversation={"guardMode": "block"})
        self.assertEqual((result["guardMode"], result["guardModeFloor"]), ("block", None))
        self.assertEqual(resolve(conversation={"guardMode": "block"}, user={"guardMode": "audit"})["guardModeFloor"], None)
        # The conversation sits above a lower mode; only repository and user can hold a floor.
        self.assertEqual(resolve(conversation={"guardMode": "block"}, repository={"guardMode": "warn"})["guardMode"], "block")

    def test_a_block_that_a_more_specific_scope_lowered_before_is_no_floor_when_absent(self):
        result = resolve(repository={"guardMode": "warn"})
        self.assertEqual((result["guardMode"], result["guardModeFloor"], result["guardModeLoweringRefused"]),
                         ("warn", None, False))


class ExtensionTests(unittest.TestCase):
    ENTRY = {"extensionVersion": "agent-braid-push-settings/v0.1", "settings": {"killSwitch": True, "targets": ["a"]}}

    def test_an_extension_is_stored_reported_and_never_effective(self):
        plain = resolve(user={"guardMode": "warn"})
        document = {"schemaVersion": VERSION, "user": {"guardMode": "warn", "extensions": {"SPEC-059": self.ENTRY}},
                    "extensions": {"SPEC-059": self.ENTRY}}
        with_extension = ownership.resolve_settings({"user": document})
        self.assertFalse(list(RESOLVED.iter_errors(with_extension)))
        self.assertEqual(with_extension["extensions"], [{"owner": "SPEC-059", "extensionVersion": self.ENTRY["extensionVersion"],
                                                         "status": "not-interpreted-by-SPEC-057"}])
        self.assertEqual({k: v for k, v in with_extension.items() if k != "extensions"},
                         {k: v for k, v in plain.items() if k != "extensions"})

    def test_an_extension_asking_for_push_or_block_changes_nothing(self):
        entry = {"extensionVersion": "v9", "settings": {"notificationMode": "push", "guardMode": "block"}}
        result = ownership.resolve_settings({"user": {"schemaVersion": VERSION, "user": {"extensions": {"SPEC-059": entry}}}})
        self.assertEqual((result["guardMode"], result["guardModeFloor"], result["pushStatus"]), ("off", None, "not-requested"))

    def test_extension_bounds(self):
        entries = {f"SPEC-{n:03d}": {"extensionVersion": "v1", "settings": {}} for n in range(9)}
        with self.assertRaises(ownership.SettingsRefused):
            ownership.resolve_settings({"user": {"schemaVersion": VERSION, "extensions": entries}})
        for count, refused in ((8, False), (9, True)):
            document = {"schemaVersion": VERSION, "extensions": dict(list(entries.items())[:count])}
            self.assertEqual(bool(ownership.validate_settings(document)), refused)
        many_distinct = {s: {"schemaVersion": VERSION, "extensions": {f"SPEC-{n:03d}": {"extensionVersion": s, "settings": {}}
                                                                    for n in range(5)}} for s in ("user", "repository")}
        with self.assertRaises(ownership.SettingsRefused) as caught:
            ownership.resolve_settings(many_distinct)
        self.assertEqual(caught.exception.code, "ERR-OVER-BOUND")


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="settings-")).resolve()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.base, ignore_errors=True))
        self.config = self.base / "config"
        self.config.mkdir()
        self.repo = self.base / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")

    def put(self, scope, settings=None, *, mode=0o600):
        path = ownership.operator_location(scope, self.config, DIGEST)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc(scope, **(settings or {"guardMode": "audit"}))), encoding="utf-8")
        path.chmod(mode)
        return path

    def load(self, **extra):
        return ownership.load_settings(config_dir=self.config, repository_digest=DIGEST, working_trees=[self.repo], **extra)

    def refused(self, code="ERR-UNOBSERVABLE-SOURCE", **extra):
        with self.assertRaises(ownership.SettingsRefused) as caught:
            self.load(**extra)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_operator_locations_are_fixed(self):
        self.assertEqual(ownership.operator_location("user", self.config), self.config / "orchestration-settings.json")
        self.assertEqual(ownership.operator_location("repository", self.config, DIGEST),
                         self.config / "repositories" / DIGEST / "orchestration-settings.json")
        for call in (("conversation",), ("repository",), ("repository", self.config, "../x"), ("team",)):
            with self.assertRaises(ValueError):
                ownership.operator_location(call[0], *(call[1:] or (self.config,)))

    def test_three_scopes_resolve_from_their_sources(self):
        self.put("user", {"guardMode": "block"})
        self.put("repository", {"guardMode": "warn"})
        result = self.load(conversation=json.dumps(doc("conversation", guardMode="off")))
        self.assertEqual(result["guardMode"], "block")
        self.assertEqual(result["guardModeFloor"], {"mode": "block", "scope": "user"})
        self.assertTrue(result["guardModeLoweringRefused"])
        self.assertEqual([s["scope"] for s in result["scopeSources"]], ["conversation", "repository", "user"])
        self.assertFalse(list(RESOLVED.iter_errors(result)))

    def test_absent_sources_resolve_to_the_defaults(self):
        self.assertEqual(self.load()["resolvedFromScope"], "default")
        self.assertEqual(ownership.load_settings(config_dir=self.config, repository_digest=None, working_trees=[]
                                                 )["scopeSources"], [])

    def test_a_tracked_file_inside_a_working_tree_is_refused(self):
        inside = self.repo / "cfg"
        path = ownership.operator_location("user", inside)
        path.parent.mkdir()
        path.write_text(json.dumps(doc("user", guardMode="off")))
        path.chmod(0o600)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "tracked settings")
        self.assertIn(path.name, git(self.repo, "ls-files").split("/")[-1])
        with self.assertRaises(ownership.SettingsRefused) as caught:
            ownership.read_operator_file("user", inside, None, [self.repo])
        self.assertEqual(caught.exception.code, "ERR-UNOBSERVABLE-SOURCE")

    def test_a_symlink_into_a_tracked_file_is_refused(self):
        tracked = self.repo / "orchestration-settings.json"
        tracked.write_text(json.dumps(doc("repository", guardMode="off")))
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "settings")
        # Even placed at the operator location by a link into the tree, the tracked file is not read.
        location = ownership.operator_location("repository", self.config, DIGEST)
        location.parent.mkdir(parents=True)
        location.symlink_to(tracked)
        self.refused()

    def test_a_config_directory_inside_a_working_tree_is_refused(self):
        inside = self.repo / "cfg"
        inside.mkdir()
        for scope in ("user", "repository"):
            path = ownership.operator_location(scope, inside, DIGEST)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(doc(scope, guardMode="off")))
            path.chmod(0o600)
            with self.assertRaises(ownership.SettingsRefused) as caught:
                ownership.read_operator_file(scope, inside, DIGEST, [self.repo])
            self.assertEqual(caught.exception.code, "ERR-UNOBSERVABLE-SOURCE")
            self.assertIn("inside-working-tree", [d.code for d in caught.exception.diagnostics])

    def test_a_linked_worktree_counts_as_a_working_tree(self):
        (self.repo / "f").write_text("x")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        linked = self.base / "linked"
        git(self.repo, "worktree", "add", "-q", str(linked), "-b", "side")
        path = ownership.operator_location("user", linked / "cfg")
        path.parent.mkdir()
        path.write_text(json.dumps(doc("user", guardMode="off")))
        path.chmod(0o600)
        with self.assertRaises(ownership.SettingsRefused):
            ownership.read_operator_file("user", linked / "cfg", None, [self.repo, linked])

    def test_a_symlink_is_refused(self):
        target = self.base / "elsewhere.json"
        target.write_text(json.dumps(doc("user", guardMode="off")))
        target.chmod(0o600)
        (self.config / "orchestration-settings.json").symlink_to(target)
        self.assertIn("symlink", [d.code for d in self.refused().diagnostics])

    def test_a_group_or_world_writable_file_is_refused(self):
        for mode in (0o620, 0o602, 0o666, 0o660):
            with self.subTest(mode=oct(mode)):
                self.put("user", mode=mode)
                self.assertIn("writable-by-group-or-others", [d.code for d in self.refused().diagnostics])
        self.put("user", mode=0o644)
        self.assertEqual(self.load()["guardMode"], "audit")

    def test_a_directory_or_special_file_is_refused(self):
        path = ownership.operator_location("user", self.config)
        path.mkdir()
        self.refused()
        path.rmdir()
        os.mkfifo(path, 0o600)
        self.refused()

    def test_a_repository_directory_that_escapes_the_config_directory_is_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.config / "repositories").mkdir()
        (self.config / "repositories" / DIGEST).symlink_to(outside)
        (outside / "orchestration-settings.json").write_text(json.dumps(doc("repository", guardMode="off")))
        (outside / "orchestration-settings.json").chmod(0o600)
        self.assertIn("outside-config-directory", [d.code for d in self.refused().diagnostics])

    def test_a_repository_file_cannot_come_from_any_other_digest_or_path(self):
        self.put("repository", {"guardMode": "block"})
        other = ownership.load_settings(config_dir=self.config, repository_digest="b" * 64, working_trees=[self.repo])
        self.assertEqual(other["guardModeFloor"], None)

    def test_malformed_and_over_bound_sources_are_refused_with_their_codes(self):
        path = ownership.operator_location("user", self.config)
        for raw, code in ((b"{", "ERR-MALFORMED-INPUT"), (b'{"schemaVersion": 1, "schemaVersion": 1}', "ERR-MALFORMED-INPUT"),
                          (b"\xff", "ERR-MALFORMED-INPUT"), (b"NaN", "ERR-MALFORMED-INPUT"),
                          (b" " * (ownership.MAX_SETTINGS_BYTES + 1), "ERR-OVER-BOUND")):
            with self.subTest(code=code, size=len(raw)):
                path.write_bytes(raw)
                path.chmod(0o600)
                self.refused(code)
        ownership.parse_settings(b'{"schemaVersion": "%s"}' % VERSION.encode() + b" " * (ownership.MAX_SETTINGS_BYTES - 60), "user")

    def test_the_conversation_document_is_the_only_one_that_is_not_a_file(self):
        result = self.load(conversation=json.dumps(doc("conversation", guardMode="block")))
        self.assertEqual((result["guardMode"], result["guardModeFloor"]), ("block", None))
        self.refused("ERR-MALFORMED-INPUT", conversation=json.dumps({"schemaVersion": VERSION, "user": {"guardMode": "block"}}))

    def test_a_refusal_never_echoes_file_content(self):
        secret = "SEEDED-" + "x" * 8
        path = ownership.operator_location("user", self.config)
        path.write_text(json.dumps({"schemaVersion": VERSION, "user": {secret: 1}}))
        path.chmod(0o600)
        error = self.refused("ERR-MALFORMED-INPUT")
        self.assertNotIn(secret, repr([tuple(d) for d in error.diagnostics]))


class PurityTests(unittest.TestCase):
    def test_the_resolver_imports_no_socket_network_or_process_helper(self):
        tree = ast.parse((ROOT / "agent_braid/ownership.py").read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level:
                names.add((node.module or "").split(".")[0])
        self.assertEqual(names & FORBIDDEN_IMPORTS, set())
        self.assertIn("stat", names)

    def test_resolution_opens_no_socket_and_starts_no_process(self):
        import socket
        import subprocess
        from unittest import mock

        with mock.patch.object(socket, "socket", side_effect=AssertionError), \
                mock.patch.object(subprocess, "Popen", side_effect=AssertionError):
            resolve(user={"notificationMode": "push", "notificationStrategy": "doorbell"})


if __name__ == "__main__":
    unittest.main()
