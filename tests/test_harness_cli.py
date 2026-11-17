# SPDX-License-Identifier: AGPL-3.0-only
"""Experimental laboratory CLI controls: inspection is effect-free, refusals are stable."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from hashlib import sha256
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
from agent_braid import harness_promotion as promotion
from agent_braid import harness_records as records
from agent_braid.cli import main
from agent_braid.system_one import canonical
from tests.test_harness_journal import NOW, reservation_for
from tests.test_harness_lab import manifest_for
from tests.test_harness_manifest import make_manifest
from tests.test_harness_promotion import IDENTITY, SCOPE, decide, evaluated
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

    def test_non_string_formats_refuse_with_json_and_no_traceback(self):
        for declared in ([1], {}, 7, None):
            path = self.put("format.json", {"format": declared})
            for command in ("inspect", "validate"):
                with self.subTest(declared=declared, command=command):
                    self.refused(command, path, reason="unknown-format")
            self.refused("compare", path, path, reason="unknown-format")

    def test_reads_survive_short_reads(self):
        path = self.put("manifest.json", make_manifest())
        real, calls = os.read, []

        def small(fd, count):
            calls.append(count)
            return real(fd, min(count, 100))
        with patch.object(os, "read", small):
            code, out = run("inspect", path)
        self.assertEqual((code, out["kind"]), (0, "manifest"))
        self.assertGreater(len(calls), 2)  # more than one chunk was needed
        self.assertGreater(path.stat().st_size, 100)

    def test_a_file_just_over_the_limit_is_too_large_even_when_read_in_chunks(self):
        path = self.put("huge.json", b" " * (records.MAX_RECORD_BYTES + 1))
        real = os.read
        with patch.object(os, "read", lambda fd, count: real(fd, min(count, 4096))):
            self.refused("inspect", path, reason="input-too-large")

    def test_usage_errors_and_refusals_share_exit_code_two_but_differ_in_stream(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            with self.assertRaises(SystemExit) as caught:
                main(["harness", "inspect"])
        self.assertEqual((caught.exception.code, out.getvalue()), (2, ""))
        self.assertIn("usage:", err.getvalue())
        code, refusal = run("inspect", self.root / "missing")
        self.assertEqual((code, refusal["status"]), (2, "refused"))  # JSON on stdout, nothing on stderr

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


class CapabilitiesTests(Workspace):
    def test_capabilities_are_experimental_effect_free_and_await_t007(self):
        before = self.tree()
        code, out = run("capabilities")
        self.assertEqual((code, out["status"]), (0, "ok"))
        self.assertIs(out["executionAuthorization"], False)
        self.assertIs(out["experimental"], True)
        self.assertIs(out["automaticPromotion"], False)
        self.assertIn("SPEC-049 T007", out["ordinaryUseActivation"])
        self.assertEqual(sorted(out["commands"]), sorted(cli.COMMANDS))
        effects = {name: c["effect"] for name, c in out["commands"].items()}
        self.assertEqual({n for n, e in effects.items() if e != "none"}, {"prepare"})
        self.assertEqual(out["pluginOrMcpSurface"], "none")
        self.assertEqual(out["globalHostInstructions"], "untouched")
        self.assertEqual(self.tree(), before)


def active_registry() -> promotion.ProfileRegistry:
    approved = decide()
    return (promotion.ProfileRegistry.empty(SCOPE).record(decide(decision="rejected", at=5), 5)
            .begin(approved, current=IDENTITY, at=20).commit(current=IDENTITY, at=21))


class RegistryStatusTests(Workspace):
    def test_status_reports_active_profile_and_audit_without_effects(self):
        registry = active_registry()
        path = self.put("registry.json", registry.to_bytes())
        before = self.tree()
        code, out = run("registry-status", path)
        self.assertEqual((code, out["status"]), (0, "ok"), out)
        self.assertIs(out["executionAuthorization"], False)
        self.assertIs(out["automaticPromotion"], False)
        self.assertEqual(out["sha256"], registry.sha256)
        self.assertEqual(out["scope"], SCOPE)
        self.assertEqual(out["active"]["decisionSha256"], decide().sha256)
        self.assertEqual(out["active"]["profile"]["cohort"], "synthetic")
        self.assertIsNone(out["pending"])
        self.assertEqual(out["journal"], {"entries": 3, "lastEvent": "committed", "lastAt": 21})
        self.assertEqual(sorted(d["decision"] for d in out["decisions"]), ["approved", "rejected"])
        self.assertEqual(out["revokedEvidence"], [])
        self.assertEqual(self.tree(), before)

    def test_decision_rows_report_the_decided_cohort(self):
        rejected = decide(cohort="native", profile_cohort="synthetic", decision="rejected")
        registry = promotion.ProfileRegistry.empty(SCOPE).record(rejected, 5)
        code, out = run("registry-status", self.put("registry.json", registry.to_bytes()))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["decisions"][0]["cohort"], "native")

    def test_empty_registry_has_no_active_profile(self):
        path = self.put("registry.json", promotion.ProfileRegistry.empty(SCOPE).to_bytes())
        code, out = run("registry-status", path)
        self.assertEqual(code, 0, out)
        self.assertIsNone(out["active"])
        self.assertEqual(out["journal"], {"entries": 0, "lastEvent": None, "lastAt": None})

    def test_revoked_evidence_withdraws_the_active_profile(self):
        evidence = sha256(b"review").hexdigest()
        approved = decide(evidence=[evidence])
        registry = (promotion.ProfileRegistry.empty(SCOPE).begin(approved, current=IDENTITY, at=20)
                    .commit(current=IDENTITY, at=21)
                    .revoke_evidence(evidence, at=22, reason="review-withdrawn"))
        code, out = run("registry-status", self.put("registry.json", registry.to_bytes()))
        self.assertEqual(code, 0, out)
        self.assertIsNone(out["active"])
        self.assertEqual(out["revokedEvidence"], [evidence])
        self.assertEqual(out["journal"]["lastEvent"], "evidence-revoked")

    def test_invalid_registries_refuse(self):
        raw = active_registry().to_bytes()
        self.refused("registry-status", self.put("a.json", raw + b" "), reason="non-canonical")
        self.refused("registry-status", self.put("b.json", b"{"), reason="invalid-json")
        self.refused("registry-status", self.put("c.json", raw.replace(b'"rejected"', b'"pending"')),
                     reason="decision-hash-mismatch")
        self.refused("registry-status", self.put("d.json", b" " * (records.MAX_RECORD_BYTES + 1)),
                     reason="input-too-large")
        link = self.root / "link.json"
        link.symlink_to(self.put("e.json", raw))
        self.refused("registry-status", link, reason="input-unreadable")
        self.refused("registry-status", self.root, reason="input-unreadable")


class EvaluationSummaryTests(Workspace):
    def test_summary_reports_strata_and_bindings_without_effects(self):
        _, report = evaluated()
        path = self.put("report.json", report.canonical_bytes)
        before = self.tree()
        code, out = run("evaluation-summary", path)
        self.assertEqual((code, out["status"]), (0, "ok"), out)
        self.assertIs(out["executionAuthorization"], False)
        data = report.to_dict()
        self.assertEqual(out["sha256"], report.sha256)
        self.assertEqual(out["authenticity"], "unverified")
        self.assertEqual(out["registrationSha256"], data["registrationSha256"])
        self.assertEqual(out["costReportSha256"], data["costReportSha256"])
        self.assertEqual(out["pendingEndpoints"], data["pendingEndpoints"])
        self.assertEqual(out["rows"], len(data["rows"]))
        stratum = next(iter(data["strata"]))
        summary = out["strata"][stratum]
        self.assertEqual(summary["arms"]["A"]["outcomes"], data["strata"][stratum]["arms"]["A"]["outcomes"])
        self.assertEqual(summary["comparisons"]["C-vs-A"]["noninferiority"],
                         data["strata"][stratum]["comparisons"]["C-vs-A"]["noninferiority"])
        self.assertNotIn("interval", summary["arms"]["A"])
        self.assertTrue(any("not re-derived" in limit for limit in out["limits"]))
        self.assertEqual(self.tree(), before)

    def test_trusted_hash_is_compared(self):
        _, report = evaluated()
        path = self.put("report.json", report.canonical_bytes)
        code, out = run("evaluation-summary", path, "--sha256", report.sha256)
        self.assertEqual((code, out["authenticity"]), (0, "hash-matched"))
        self.refused("evaluation-summary", path, "--sha256", "0" * 64, reason="record-drift")
        self.refused("evaluation-summary", path, "--sha256", "abc", reason="invalid-hash")
        self.refused("evaluation-summary", self.root / "absent", "--sha256", "abc",
                     reason="invalid-hash")
        self.refused("evaluation-summary", self.put("bad.json", b"{"), "--sha256", report.sha256,
                     reason="record-drift")

    def test_malformed_reports_refuse(self):
        data = evaluated()[1].to_dict()
        self.refused("evaluation-summary", self.put("a.json", canonical(data) + b"\n"),
                     reason="non-canonical")
        self.refused("evaluation-summary", self.put("b.json", b"[1,"), reason="invalid-json")
        for name, change in (("format", {"format": "other/v0"}),
                             ("authority", {"executionAuthorization": True}),
                             ("strata", {"strata": []}),
                             ("stratum", {"strata": {"s": {"units": 1}}}),
                             ("rows", {"rows": {}}),
                             ("cohort", {"cohort": "other"}),
                             ("hash", {"registrationSha256": "x"}),
                             ("count", {"strata": {"s": {**next(iter(data["strata"].values())),
                                                         "units": "many"}}})):
            self.refused("evaluation-summary", self.put(f"{name}.json", canonical({**data, **change})),
                         reason="invalid-evaluation")
        missing = {k: v for k, v in data.items() if k != "costReportSha256"}
        self.refused("evaluation-summary", self.put("missing.json", canonical(missing)),
                     reason="invalid-evaluation")


class EvidenceInventoryTests(Workspace):
    def spec(self, files=None, tasks="- [x] T001 (REQ-001): Done.\n- [ ] T002 (REQ-002): Open.\n"):
        spec = self.root / "specs" / "099-demo"
        (spec / "evidence" / "registration").mkdir(parents=True)
        (spec / "tasks.md").write_text(tasks)
        for name, data in (files or {"t001.json": {"task": "T001", "executionAuthorization": False},
                                     "registration/freeze.json": {"x": 1}}).items():
            (spec / "evidence" / name).write_bytes(data if isinstance(data, bytes) else canonical(data))
        return spec

    def test_inventory_lists_files_and_task_evidence_without_effects(self):
        spec = self.spec()
        before = self.tree()
        code, out = run("evidence", spec)
        self.assertEqual((code, out["status"]), (0, "ok"), out)
        self.assertIs(out["executionAuthorization"], False)
        paths = [f["path"] for f in out["files"]]
        self.assertEqual(paths, ["registration/freeze.json", "t001.json"])
        t001 = out["files"][1]
        self.assertEqual(t001["sha256"], sha256((spec / "evidence/t001.json").read_bytes()).hexdigest())
        self.assertEqual((t001["task"], t001["executionAuthorization"]), ("T001", False))
        self.assertEqual(out["tasks"], [{"id": "T001", "checked": True, "evidence": True},
                                        {"id": "T002", "checked": False, "evidence": False}])
        self.assertEqual(out["anomalies"], [])
        self.assertEqual(self.tree(), before)

    def test_anomalies_flag_claimed_authority_and_unevidenced_checked_tasks(self):
        spec = self.spec({"t002.json": {"executionAuthorization": True}, "notes.json": b"not json"},
                         tasks="- [x] T001 (R): a, unlike - [x] T009 mid-line\n- [ ] T002 (R): b\n")
        code, out = run("evidence", spec)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["anomalies"], [{"kind": "checked-without-evidence", "subject": "T001"},
                                            {"kind": "claims-execution-authorization",
                                             "subject": "t002.json"}])
        notes = next(f for f in out["files"] if f["path"] == "notes.json")
        self.assertIs(notes["jsonObject"], False)

    def test_real_spec_directory_inventory(self):
        spec = Path(__file__).resolve().parents[1] / "specs" / "049-harness-evaluation-learning"
        code, out = run("evidence", spec)
        self.assertEqual(code, 0, out)
        self.assertIn("t013.json", [f["path"] for f in out["files"]])
        self.assertIn({"id": "T013", "checked": True, "evidence": True}, out["tasks"])

    def test_unsafe_or_oversized_inputs_refuse(self):
        self.refused("evidence", self.root / "absent", reason="input-unreadable")
        spec = self.spec()
        self.refused("evidence", spec / "tasks.md", reason="input-unreadable")
        link = self.root / "link-spec"
        link.symlink_to(spec)
        self.refused("evidence", link, reason="input-unreadable")
        (spec / "evidence" / "escape.json").symlink_to(spec / "tasks.md")
        self.refused("evidence", spec, reason="input-unreadable")
        (spec / "evidence" / "escape.json").unlink()
        (spec / "evidence" / "big.json").write_bytes(b" " * (records.MAX_RECORD_BYTES + 1))
        self.refused("evidence", spec, reason="input-too-large")
        (spec / "evidence" / "big.json").unlink()
        for index in range(cli.MAX_EVIDENCE_FILES):
            (spec / "evidence" / f"f{index}.json").write_bytes(b"{}")
        self.refused("evidence", spec, reason="too-many-entries")

    def test_depth_and_directory_entry_bounds(self):
        spec = self.spec()
        (spec / "evidence" / "a" / "b" / "c").mkdir(parents=True)
        (spec / "evidence" / "a" / "b" / "c" / "x.json").write_bytes(b"{}")
        code, out = run("evidence", spec)
        self.assertEqual(code, 0, out)
        self.assertIn("a/b/c/x.json", [f["path"] for f in out["files"]])
        (spec / "evidence" / "a" / "b" / "c" / "d").mkdir()
        self.refused("evidence", spec, reason="too-deep")
        (spec / "evidence" / "a" / "b" / "c" / "d").rmdir()
        for index in range(cli.MAX_EVIDENCE_ENTRIES):
            (spec / "evidence" / "a" / f"empty{index}").mkdir()
        self.refused("evidence", spec, reason="too-many-entries")

    def test_special_files_and_non_object_json(self):
        spec = self.spec({"list.json": b"[1]"})
        code, out = run("evidence", spec)
        self.assertEqual((code, out["files"][0]["jsonObject"]), (0, False))
        os.mkfifo(spec / "evidence" / "pipe.json")
        self.refused("evidence", spec, reason="input-unreadable")

    def test_spec_directory_name_is_resolved(self):
        spec = self.spec()
        old = os.getcwd()
        os.chdir(spec)
        self.addCleanup(os.chdir, old)
        code, out = run("evidence", ".")
        self.assertEqual((code, out["specDirectory"]), (0, "099-demo"))

    def test_missing_evidence_directory_or_tasks_refuses(self):
        spec = self.spec()
        (spec / "tasks.md").write_bytes(b"\xff")
        self.refused("evidence", spec, reason="invalid-tasks")
        (spec / "tasks.md").unlink()
        self.refused("evidence", spec, reason="input-unreadable")
        (spec / "evidence" / "registration" / "freeze.json").unlink()
        (spec / "evidence" / "registration").rmdir()
        (spec / "evidence" / "t001.json").unlink()
        (spec / "evidence").rmdir()
        (spec / "tasks.md").write_text("- [ ] T001 (R): a\n")
        self.refused("evidence", spec, reason="input-unreadable")


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

    def test_harness_help_lists_exactly_the_ten_entry_points(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            main(["harness", "--help"])
        commands = re.search(r"\{([a-z,-]+)\}", out.getvalue()).group(1).split(",")
        self.assertEqual(commands, ["inspect", "validate", "prepare", "status", "recover-inspect",
                                    "compare", "capabilities", "registry-status",
                                    "evaluation-summary", "evidence"])

    def test_a_pre_existing_command_still_dispatches(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["system-one", "capabilities"])
        self.assertEqual(code, 0)
        self.assertTrue(out.getvalue().startswith("{"))


if __name__ == "__main__":
    unittest.main()
