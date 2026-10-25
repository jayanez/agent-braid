# SPDX-License-Identifier: AGPL-3.0-only
"""Experimental laboratory CLI controls: inspection is effect-free, refusals are stable."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import harness_cli as cli
from agent_braid import harness_journal as journal
from agent_braid import harness_records as records
from agent_braid.cli import main
from agent_braid.system_one import canonical
from tests.test_harness_journal import NOW, reservation_for
from tests.test_harness_lab import manifest_for
from tests.test_harness_manifest import make_manifest
from tests.test_harness_records import decision_wire
from tests import test_harness_surface

REFUSAL_KEYS = {"status", "reason", "executionAuthorization"}


def run(*argv):
    """Run the real entry point; return (exit code, parsed stdout JSON or raw text)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = main(["harness", *map(str, argv)])
        except SystemExit as exc:
            code = exc.code
    text = out.getvalue()
    return code, (json.loads(text) if text.startswith("{") else text)


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def put(self, name, data) -> Path:
        path = self.root / name
        path.write_bytes(data if isinstance(data, bytes) else canonical(data))
        return path

    def tree(self, root=None):
        root = root or self.root
        return sorted((p.relative_to(root).as_posix(), p.stat().st_mtime_ns,
                       p.read_bytes() if p.is_file() else None) for p in root.rglob("*"))

    def refused(self, *argv, reason=None):
        code, out = run(*argv)
        self.assertEqual(code, 2, out)
        self.assertEqual(out["status"], "refused")
        self.assertIs(out["executionAuthorization"], False)
        self.assertTrue(REFUSAL_KEYS <= set(out))
        self.assertRegex(out["reason"], r"^[a-z][a-z-]+\Z")
        if reason:
            self.assertEqual(out["reason"], reason)
        return out


class InspectValidateTests(Workspace):
    def test_manifest_inspection_shows_diff_limits_and_no_authority(self):
        path = self.put("manifest.json", make_manifest())
        before = self.tree()
        code, out = run("inspect", path)
        self.assertEqual((code, out["status"], out["kind"]), (0, "ok", "manifest"))
        self.assertIs(out["executionAuthorization"], False)
        self.assertEqual(out["candidateVsBase"]["modified"], ["guidance/main.md"])
        self.assertEqual(out["candidateVsBase"]["added"] + out["candidateVsBase"]["removed"], [])
        self.assertIn("offline-foundations", " ".join(out["profileLimits"]))
        self.assertEqual(out["sha256"], records.decode(path.read_bytes()).sha256)
        self.assertEqual(self.tree(), before)

    def test_decision_inspection_surfaces_evidence_losses(self):
        wire = decision_wire()
        wire["losses"] = ["budget-exhausted"]
        path = self.put("decision.json", records.encode("decision", wire).canonical_bytes)
        code, out = run("inspect", path)
        self.assertEqual((code, out["kind"]), (0, "decision"))
        self.assertEqual(out["evidenceLosses"], ["budget-exhausted"])
        self.assertEqual(out["decision"], "candidate")
        self.assertIn("advisory", " ".join(out["profileLimits"]))

    def test_validate_distinguishes_shape_from_trusted_identity(self):
        path = self.put("manifest.json", make_manifest())
        trusted = records.decode(path.read_bytes()).sha256
        code, out = run("validate", path)
        self.assertEqual((code, out["authenticity"]), (0, "unverified"))
        code, out = run("validate", path, "--sha256", trusted)
        self.assertEqual((code, out["authenticity"]), (0, "hash-matched"))
        self.refused("validate", path, "--sha256", "f" * 64, reason="manifest-drift")
        bindings = records.decode(path.read_bytes()).data
        self.refused("validate", path, "--sha256", trusted, "--binding", "task=" + "0" * 64,
                     reason="binding-drift")
        self.refused("validate", path, "--sha256", trusted, "--binding", "bogus=" + "0" * 64,
                     reason="invalid-binding")
        self.refused("validate", path, "--sha256", "nothex", reason="invalid-hash")
        self.assertTrue(bindings)

    def test_other_kinds_compare_the_record_hash(self):
        record = records.encode("decision", decision_wire())
        path = self.put("decision.json", record.canonical_bytes)
        code, out = run("validate", path, "--sha256", record.sha256)
        self.assertEqual((code, out["authenticity"]), (0, "hash-matched"))
        self.refused("validate", path, "--sha256", "e" * 64, reason="record-drift")
        self.refused("validate", path, "--sha256", record.sha256, "--binding", "task=" + "0" * 64,
                     reason="binding-not-applicable")

    def test_malformed_future_and_non_canonical_records_refuse_with_stable_reasons(self):
        wire = make_manifest()
        cases = {
            "unsupported-version": canonical(dict(wire, format=wire["format"].replace("v0.1", "v9.0"))),
            "unknown-format": canonical(dict(wire, format="something-else")),
            "non-canonical": json.dumps(wire, indent=2).encode(),
            "invalid-json": b"{not json",
            "unsupported-profile": canonical(dict(wire, profile="native")),
        }
        for reason, data in cases.items():
            path = self.put("bad.json", data)
            for command in ("inspect", "validate"):
                with self.subTest(reason=reason, command=command):
                    self.refused(command, path, reason=reason)

    def test_hostile_inputs_never_escape_as_exceptions(self):
        (self.root / "dir").mkdir()
        self.put("target", b"{}")
        os.symlink(self.root / "target", self.root / "link")
        os.mkfifo(self.root / "fifo")
        self.put("huge", b" " * (records.MAX_RECORD_BYTES + 1))
        for name, reason in (("missing", "input-unreadable"), ("dir", "input-unreadable"),
                             ("link", "input-unreadable"), ("fifo", "input-unreadable"),
                             ("huge", "input-too-large")):
            with self.subTest(name=name):
                self.refused("inspect", self.root / name, reason=reason)

    def test_internal_bugs_are_not_hidden_as_refusals(self):
        path = self.put("manifest.json", make_manifest())
        with patch.object(cli, "decode", side_effect=RuntimeError("bug")):
            with self.assertRaises(RuntimeError):
                run("inspect", path)


class CompareTests(Workspace):
    def test_compare_emits_a_strict_comparison_record(self):
        left = make_manifest()
        right = deepcopy(left)
        right["task"]["id"] = "C01-002"
        a, b = self.put("a.json", left), self.put("b.json", right)
        code, out = run("compare", a, b)
        self.assertEqual((code, out["status"]), (0, "ok"))
        record = records.decode(canonical(out["record"]))
        self.assertEqual(record.kind, "comparison")
        self.assertIn("task", [row["field"] for row in out["record"]["differences"]])

    def test_compare_refuses_mixed_kinds_and_bad_inputs(self):
        a = self.put("a.json", make_manifest())
        b = self.put("b.json", records.encode("decision", decision_wire()).canonical_bytes)
        self.refused("compare", a, b, reason="kind-mismatch")
        self.refused("compare", a, self.root / "missing", reason="input-unreadable")


class PrepareTests(Workspace):
    def setUp(self):
        super().setUp()
        self.fixture = test_harness_surface.HarnessSurfaceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        parameters = self.fixture.parameters()
        self.manifest = self.put("manifest.json", parameters["raw"])
        self.bindings = self.put("bindings.json", dict(parameters["expected_bindings"]))
        self.sha = parameters["expected_sha256"]
        self.roots = self.fixture.roots
        self.destination = self.fixture.destination

    def args(self, **over):
        values = {"sha256": self.sha, "bindings": self.bindings, "destination": self.destination,
                  **{f"{n}-root": p for n, p in self.roots.items()}}
        values.update({k.replace("_", "-"): v for k, v in over.items()})
        return [self.manifest, *[x for k, v in values.items() for x in (f"--{k}", v)]]

    def test_prepare_publishes_one_private_candidate_and_authorizes_nothing(self):
        code, out = run("prepare", *self.args())
        self.assertEqual(code, 0, out)
        self.assertEqual(out["receipt"]["status"], "completed")
        self.assertIs(out["executionAuthorization"], False)
        self.assertTrue((self.destination / "candidate/guidance/main.md").is_file())
        self.assertEqual(sorted(p.name for p in self.destination.iterdir()), ["candidate"])

    def test_prepare_refusals_are_stable_and_leave_no_container(self):
        self.refused("prepare", *self.args(sha256="f" * 64), reason="manifest-drift")
        self.assertFalse(self.destination.exists())
        wrong = self.put("partial.json", {"task": "0" * 64})
        self.refused("prepare", *self.args(bindings=wrong), reason="incomplete-consumer-bindings")
        self.assertFalse(self.destination.exists())
        self.refused("prepare", *self.args(bindings=self.root / "missing"), reason="input-unreadable")
        self.destination.mkdir()
        out = self.refused("prepare", *self.args(), reason="destination-exists")
        self.assertIs(out["receipt"]["acceptedPublished"], False)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_prepare_requires_every_root_and_the_trusted_hash(self):
        for flag in ("--sha256", "--bindings", "--destination", "--source-root", "--context-root"):
            argv = self.args()
            index = argv.index(flag)
            del argv[index:index + 2]
            with self.subTest(flag=flag), redirect_stderr(io.StringIO()):
                code, _ = run("prepare", *argv)
                self.assertEqual(code, 2)


class JournalViewTests(Workspace):
    def setUp(self):
        super().setUp()
        self.fixture = b"print('x')\n"
        self.manifest = manifest_for(self.fixture)
        self.path = self.put("manifest.json", self.manifest.canonical_bytes)
        self.journal = self.root / "journal"
        self.journal.mkdir(mode=0o700)

    def start(self):
        journal.begin_attempt(self.journal, self.manifest, attempt_id="attempt-1",
                              reservation=reservation_for(self.manifest), now=NOW)

    def view(self, command, attempt="attempt-1", **over):
        args = {"sha256": self.manifest.sha256, "attempt-id": attempt, "now": NOW}
        args.update(over)
        return run(command, self.journal, self.path,
                   *[x for k, v in args.items() for x in (f"--{k}", v)])

    def test_status_reports_the_durable_phase_without_touching_the_journal(self):
        self.start()
        before = self.tree()
        code, out = self.view("status")
        self.assertEqual((code, out["status"]), (0, "ok"))
        self.assertEqual((out["record"]["phase"], out["record"]["outcome"]), ("started", "pending"))
        self.assertEqual(records.decode(canonical(out["record"])).kind, "attempt-status")
        self.assertIs(out["executionAuthorization"], False)
        self.assertEqual(self.tree(), before)

    def test_recover_inspect_points_at_reconciliation_but_performs_none(self):
        self.start()
        before = self.tree()
        code, out = self.view("recover-inspect")
        self.assertEqual(code, 0)
        self.assertEqual(out["recovery"]["action"], "reconcile-required")
        self.assertIs(out["recovery"]["redispatchAllowed"], False)
        self.assertIs(out["recovery"]["cliEffect"], False)
        self.assertEqual(self.tree(), before)  # still open: nothing was reconciled
        journal.reconcile_attempt(self.journal, self.manifest, attempt_id="attempt-1", now=NOW)
        code, out = self.view("recover-inspect")
        self.assertEqual(out["recovery"]["action"], "none")
        self.assertEqual((out["record"]["state"], out["record"]["outcome"]), ("interrupted", "unknown"))

    def test_status_refusals(self):
        self.start()
        self.refused_view("status", "unknown-attempt", attempt="attempt-9")
        self.refused_view("status", "manifest-drift", sha256="f" * 64)
        self.refused_view("status", "invalid-attempt", attempt="Bad Id")
        self.refused("status", self.root / "absent", self.path, "--sha256", self.manifest.sha256,
                     "--attempt-id", "attempt-1", "--now", NOW, reason="unsafe-root")

    def refused_view(self, command, reason, **over):
        code, out = self.view(command, **over)
        self.assertEqual((code, out["status"], out["reason"]), (2, "refused", reason), out)


class ExistingCliTests(unittest.TestCase):
    def test_only_the_harness_entry_is_added_to_top_level_help(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            main(["--help"])
        with_harness = " ".join(out.getvalue().split())
        out = io.StringIO()
        with patch.object(cli, "add_parser", lambda subparsers: None), \
                redirect_stdout(out), self.assertRaises(SystemExit):
            main(["--help"])
        without = " ".join(out.getvalue().split())
        self.assertNotEqual(with_harness, without)
        stripped = with_harness.replace(f"harness {cli.HELP}", "")
        stripped = re.sub(r",harness\b|\bharness,", "", stripped)
        self.assertEqual(" ".join(stripped.split()), without)
        self.assertIn("harness", with_harness)

    def test_harness_help_lists_exactly_the_six_entry_points(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            main(["harness", "--help"])
        commands = re.search(r"\{([a-z,-]+)\}", out.getvalue()).group(1).split(",")
        self.assertEqual(commands, ["inspect", "validate", "prepare", "status", "recover-inspect", "compare"])

    def test_a_pre_existing_command_still_dispatches(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["system-one", "capabilities"])
        self.assertEqual(code, 0)
        self.assertTrue(out.getvalue().startswith("{"))


if __name__ == "__main__":
    unittest.main()
