# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T011 controls for the offline, opt-in operational lifecycle.

Synthetic doubles in temporary directories only: no host, model, network or native run.
Nothing here observes human workflow usability; that remains a separate pending observation.
"""
import ast
from hashlib import sha256
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from agent_braid import harness_auto_promotion as ap
from agent_braid import harness_lifecycle as hl
from agent_braid import harness_promotion as pr

from tests.test_harness_auto_promotion import CLEAR, CONTROL, PROPOSER, World
from tests.test_harness_components import _compile, file_row, make_inventory
from tests.test_harness_curation import library
from tests.test_harness_promotion import HUMAN, IDENTITY, SCOPE, decide, h

ROBOT = {"kind": "automatic-policy", "id": "policy-1"}
V1 = _compile(make_inventory([file_row("guidance/main.md", b"v1\n")]))
V2 = _compile(make_inventory([file_row("guidance/main.md", b"v2\n", "override")], version=2,
                             parentSha256=V1.sha256),
              parent_raw=V1.canonical_bytes, expected_parent_sha256=V1.sha256)
V3 = _compile(make_inventory([file_row("guidance/main.md", b"v3\n", "override")], version=3,
                             parentSha256=V2.sha256),
              parent_raw=V2.canonical_bytes, expected_parent_sha256=V2.sha256)
BLOCKED = _compile(make_inventory([file_row("eventnotes/a.md", b"x\n")], componentClass="C6"))


def tree(path: Path) -> dict:
    """Every entry under ``path`` with its bytes (files) or None (directories)."""
    out = {}
    for base, dirs, files in os.walk(path):
        for name in dirs:
            out[os.path.relpath(os.path.join(base, name), path)] = None
        for name in files:
            full = os.path.join(base, name)
            out[os.path.relpath(full, path)] = Path(full).read_bytes()
    return out


class Case(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outer = Path(self._tmp.name)
        self.root = self.outer / "ws"
        self.root.mkdir()
        (self.outer / "sentinel.txt").write_bytes(b"outside\n")

    def tearDown(self):
        # Nothing is ever written outside the caller-supplied root.
        self.assertEqual(sorted(os.listdir(self.outer)), ["sentinel.txt", "ws"])
        self.assertEqual((self.outer / "sentinel.txt").read_bytes(), b"outside\n")
        self._tmp.cleanup()

    def refuses(self, expected, fn, /, *args, **kwargs):
        with self.assertRaises(hl.LifecycleError) as ctx:
            fn(*args, **kwargs)
        self.assertEqual(ctx.exception.reason, expected)

    def install(self, at=1, **over):
        args = {"opt_in": True, "operator": HUMAN, "scope": SCOPE, "host": "claude",
                "identity": IDENTITY, "at": at} | over
        return hl.install(self.root, **args)

    def migrate(self, profile, at, expires_at=1000, operator=HUMAN, expected=None):
        return hl.migrate(self.root, profile.canonical_bytes,
                          expected_sha256=expected or profile.sha256, expires_at=expires_at,
                          operator=operator, at=at)

    @property
    def owned(self) -> Path:
        return self.root / hl.OWNED


class DefaultAndInstallTests(Case):
    def test_default_is_not_installed_and_reading_status_writes_nothing(self):
        status = hl.status(self.root)
        self.assertEqual((status["installed"], status["state"]), (False, "not-installed"))
        self.assertIs(status["executionAuthorization"], False)
        self.assertEqual(status["ordinaryUse"], "unavailable")
        self.assertEqual(os.listdir(self.root), [])
        self.refuses("not-installed", self.migrate, V1, at=2)
        self.refuses("not-installed", hl.uninstall, self.root, operator=HUMAN, at=2)
        self.refuses("activation-requires-adoption", hl.activate, self.root)
        self.assertEqual(os.listdir(self.root), [])

    def test_installation_is_explicitly_opted_in_by_a_human(self):
        for value in (False, None, 1, "yes"):
            self.refuses("opt-in-required", self.install, opt_in=value)
        self.refuses("automatic-promotion-disabled", self.install, operator=ROBOT)
        for bad in (None, {"kind": "human"}, {"kind": "human", "id": "bad id"}, "human"):
            self.refuses("invalid-operator", self.install, operator=bad)
        for bad in (None, {}, IDENTITY | {"extra": "x"}, IDENTITY | {"sourceSha256": "short"}):
            self.refuses("invalid-identity", self.install, identity=bad)
        self.refuses("invalid-scope", self.install, scope="bad scope")
        self.refuses("invalid-time", self.install, at=-1)
        self.assertEqual(os.listdir(self.root), [])

    def test_unsupported_and_unknown_hosts_are_refused_without_writing(self):
        for host in ("codex", "gemini", "", None, "Claude"):
            self.refuses("unsupported-host", self.install, host=host)
        self.assertEqual(os.listdir(self.root), [])

    def test_root_must_be_an_existing_real_directory(self):
        self.refuses("invalid-root", hl.install, self.root / "missing", opt_in=True,
                     operator=HUMAN, scope=SCOPE, host="claude", identity=IDENTITY, at=1)
        link = self.root / "link"
        link.symlink_to(self.outer)
        self.refuses("invalid-root", hl.status, link)
        link.unlink()
        (self.root / "file").write_bytes(b"x")
        self.refuses("invalid-root", hl.status, self.root / "file")
        (self.root / "file").unlink()

    def test_fresh_install_is_private_disabled_and_cannot_be_repeated(self):
        status = self.install()
        self.assertEqual((status["installed"], status["state"]), (True, "installed"))
        self.assertIsNone(status["current"])
        self.assertEqual(status["previous"], [])
        self.assertEqual((status["ordinaryUse"], status["export"]), ("unavailable", "disabled"))
        self.assertEqual(status["activation"], "requires-separate-adr-and-operator-decision")
        self.assertEqual(status["journal"]["last"], "installed")
        self.assertEqual(sorted(os.listdir(self.root)), [hl.OWNED])
        for path in [self.owned, *self.owned.rglob("*")]:
            mode = stat.S_IMODE(path.lstat().st_mode)
            self.assertEqual(mode & 0o077, 0, path)  # private to the owner
        registry = hl.load_registry(self.root)
        self.assertEqual((registry.scope, registry.active, registry.journal), (SCOPE, None, ()))
        self.refuses("already-installed", self.install, at=2)
        self.refuses("activation-requires-adoption", hl.activate, self.root)


class MigrationTests(Case):
    def setUp(self):
        super().setUp()
        self.install()

    def test_fresh_upgrade_and_downgrade_preserve_the_prior_profile_byte_for_byte(self):
        status = self.migrate(V1, at=2)
        self.assertEqual(status["current"]["sha256"], V1.sha256)
        status = self.migrate(V2, at=3)
        self.assertEqual((status["current"]["sha256"], status["previous"]), (V2.sha256, [V1.sha256]))
        self.assertEqual(hl.read_profile(self.root, V1.sha256), V1.canonical_bytes)
        status = hl.rollback(self.root, operator=HUMAN, at=4, reason="owner-downgrade")
        self.assertEqual((status["current"]["sha256"], status["previous"]), (V1.sha256, []))
        self.assertEqual(hl.read_profile(self.root, V1.sha256), V1.canonical_bytes)
        self.refuses("no-prior-profile", hl.rollback, self.root, operator=HUMAN, at=5,
                     reason="again")
        # The withdrawn v2 can be migrated to again only as a new linked step.
        self.assertEqual(self.migrate(V2, at=6)["current"]["sha256"], V2.sha256)
        events = [e["event"] for e in hl.status(self.root)["events"]]
        self.assertEqual(events, ["installed", "migrated", "migrated", "rolled-back", "migrated"])

    def test_migration_must_be_linked_admitted_verified_and_human(self):
        self.refuses("migration-not-linked", self.migrate, V2, at=2)  # no v1 installed
        self.migrate(V1, at=2)
        self.refuses("migration-not-linked", self.migrate, V3, at=3)  # skips v2
        self.refuses("migration-not-linked", self.migrate, V1, at=3)  # not a child
        self.refuses("profile-drift", self.migrate, V2, at=3, expected=h("other"))
        self.refuses("profile-drift", hl.migrate, self.root, V2.canonical_bytes + b" ",
                     expected_sha256=V2.sha256, expires_at=100, operator=HUMAN, at=3)
        self.refuses("automatic-promotion-disabled", self.migrate, V2, at=3, operator=ROBOT)
        self.refuses("invalid-expiry", self.migrate, V2, at=3, expires_at=3)
        self.refuses("invalid-expiry", self.migrate, V2, at=3, expires_at=None)
        self.refuses("time-regression", self.migrate, V2, at=1)
        self.assertEqual(hl.status(self.root)["current"]["sha256"], V1.sha256)

    def test_blocked_profiles_are_never_staged(self):
        self.assertEqual(BLOCKED.data["admission"]["state"], "blocked")
        self.refuses("profile-blocked", self.migrate, BLOCKED, at=2)
        self.assertIsNone(hl.status(self.root)["current"])

    def test_tampered_or_missing_prior_profile_refuses_rollback_and_changes_nothing(self):
        self.migrate(V1, at=2)
        self.migrate(V2, at=3)
        blob = self.owned / "profiles" / f"{V1.sha256}.json"
        blob.write_bytes(V1.canonical_bytes.replace(b"v1", b"vX"))
        before = tree(self.root)
        self.refuses("prior-profile-unavailable", hl.rollback, self.root, operator=HUMAN, at=4,
                     reason="downgrade")
        self.assertEqual(tree(self.root), before)
        blob.unlink()
        self.refuses("prior-profile-unavailable", hl.rollback, self.root, operator=HUMAN, at=4,
                     reason="downgrade")
        self.assertEqual(hl.status(self.root)["current"]["sha256"], V2.sha256)

    def test_expiry_is_reported_and_gates_operation_without_deleting_anything(self):
        self.migrate(V1, at=2, expires_at=50)
        self.migrate(V2, at=3, expires_at=10)
        self.assertFalse(hl.status(self.root, now=9)["current"]["expired"])
        status = hl.status(self.root, now=10)
        self.assertTrue(status["current"]["expired"])
        self.assertEqual(status["state"], "expired")
        self.assertTrue((self.owned / "profiles" / f"{V2.sha256}.json").exists())
        # Rollback restores the prior profile with its own expiry.
        status = hl.rollback(self.root, operator=HUMAN, at=11, reason="expired")
        self.assertEqual((status["current"]["sha256"], status["current"]["expiresAt"]),
                         (V1.sha256, 50))


class InterruptionAndFormatTests(Case):
    def test_interrupted_migration_keeps_the_prior_profile_and_recover_cleans_debris(self):
        self.install()
        self.migrate(V1, at=2)
        before = hl.status(self.root)
        calls = []

        def crash_on_state(src, dst):  # the blob is written; the state write crashes
            calls.append(dst)
            if Path(dst).name == "state.json":
                raise OSError("crash")
            os.replace(src, dst)

        with mock.patch.object(hl, "_replace", side_effect=crash_on_state):
            self.refuses("write-failed", self.migrate, V2, at=3)
        self.assertEqual([Path(c).name for c in calls], [f"{V2.sha256}.json", "state.json"])
        self.assertEqual(hl.status(self.root)["debris"], [f"profiles/{V2.sha256}.json"])
        after = hl.status(self.root)
        self.assertEqual(after["current"], before["current"])
        self.assertEqual(after["journal"], before["journal"])
        # A crash can also leave temporary files and an unreferenced profile blob behind.
        (self.owned / ".state.json.tmp-0123456789abcdef").write_bytes(b"partial")
        (self.owned / "profiles" / f"{V2.sha256}.json").write_bytes(V2.canonical_bytes)
        self.assertEqual(sorted(hl.status(self.root)["debris"]),
                         [".state.json.tmp-0123456789abcdef", f"profiles/{V2.sha256}.json"])
        receipt = hl.recover(self.root)
        self.assertEqual(sorted(receipt["removed"]),
                         [f"{hl.OWNED}/.state.json.tmp-0123456789abcdef",
                          f"{hl.OWNED}/profiles/{V2.sha256}.json"])
        self.assertEqual(hl.status(self.root)["debris"], [])
        self.assertEqual(self.migrate(V2, at=3)["current"]["sha256"], V2.sha256)

    def test_interrupted_install_leaves_nothing_installed_and_is_recoverable(self):
        with mock.patch.object(hl, "_rename", side_effect=OSError("crash")):
            self.refuses("write-failed", self.install)
        self.assertFalse(self.owned.exists())
        status = hl.status(self.root)
        self.assertEqual(status["state"], "not-installed")
        # The failed install cleaned its staging directory; a hard crash would not.
        (self.root / f"{hl.STAGING_PREFIX}0123456789abcdef").mkdir(mode=0o700)
        self.assertEqual(hl.residue(self.root), [f"{hl.STAGING_PREFIX}0123456789abcdef"])
        hl.recover(self.root)
        self.assertEqual(hl.residue(self.root), [])
        self.assertTrue(self.install()["installed"])

    def test_interrupted_uninstall_is_already_uninstalled_and_resumable(self):
        self.install()
        self.migrate(V1, at=2)
        with mock.patch.object(hl, "_unlink", side_effect=OSError("crash")):
            self.refuses("cleanup-incomplete", hl.uninstall, self.root, operator=HUMAN, at=3)
        self.assertEqual(hl.status(self.root)["state"], "not-installed")
        residue = hl.residue(self.root)
        self.assertEqual(len(residue), 1)
        self.assertTrue(residue[0].startswith(hl.REMOVING_PREFIX))
        receipt = hl.recover(self.root)
        self.assertIn(residue[0], receipt["removed"])
        self.assertEqual(hl.residue(self.root), [])
        self.assertEqual(os.listdir(self.root), [])

    def test_future_old_or_noncanonical_state_formats_refuse_and_are_not_rewritten(self):
        self.install()
        state = self.owned / "state.json"
        original = state.read_bytes()
        for bad, reason in ((original.replace(hl.FORMAT.encode(), b"braid-harness-lifecycle/v0.2"),
                             "unsupported-version"),
                            (original.replace(hl.FORMAT.encode(), b"braid-harness-lifecycle/v0.0"),
                             "unsupported-version"),
                            (original + b"\n", "non-canonical"),
                            (b"{", "invalid-state"),
                            (original.replace(b'"executionAuthorization":false',
                                              b'"executionAuthorization":true'), "invalid-state"),
                            (original.replace(b'"previous":[]', b'"previous":[{"expiresAt":9,'
                                              b'"migratedAt":1,"sha256":"' + b"a" * 64
                                              + b'","version":1}]'), "invalid-state")):
            state.write_bytes(bad)
            self.refuses(reason, hl.status, self.root)
            self.refuses(reason, self.migrate, V1, at=2)
            self.refuses(reason, hl.uninstall, self.root, operator=HUMAN, at=2)
            self.assertEqual(state.read_bytes(), bad)
        state.write_bytes(original)
        self.assertTrue(hl.status(self.root)["installed"])
        # A forged prior-profile stack that does not descend from version 1 is refused.
        self.migrate(V1, at=2)
        self.migrate(V2, at=3)
        good = state.read_bytes()
        self.assertEqual(good.count(b'"version":1}'), 1)
        state.write_bytes(good.replace(b'"version":1}', b'"version":2}'))
        self.refuses("invalid-state", hl.status, self.root)
        state.write_bytes(good)

    def test_foreign_or_linked_content_blocks_uninstall_and_recover(self):
        self.install()
        before = tree(self.root)
        (self.owned / "notes.txt").write_bytes(b"user data")
        self.assertEqual(hl.status(self.root)["foreign"], ["notes.txt"])
        self.refuses("foreign-content", hl.uninstall, self.root, operator=HUMAN, at=2)
        self.refuses("foreign-content", hl.recover, self.root)
        (self.owned / "notes.txt").unlink()
        self.assertEqual(tree(self.root), before)
        (self.owned / "private" / ("a" * 64)).symlink_to(self.outer / "sentinel.txt")
        self.refuses("foreign-content", hl.uninstall, self.root, operator=HUMAN, at=2)
        (self.owned / "private" / ("a" * 64)).unlink()


class DriftTests(Case):
    def setUp(self):
        super().setUp()
        self.install()
        self.migrate(V1, at=2)

    def test_host_model_and_tool_drift_require_human_requalification(self):
        self.assertEqual(hl.check_drift(self.root, IDENTITY, at=3), [])
        for key, reason in (("host", "stale-host"), ("model", "stale-model"),
                            ("toolSetSha256", "stale-tool"), ("sourceSha256", "stale-source"),
                            ("policySha256", "stale-policy")):
            drifted = IDENTITY | {key: h("drift") if key.endswith("Sha256") else "drifted"}
            self.assertEqual(hl.check_drift(self.root, drifted, at=3), [reason])
        status = hl.status(self.root)
        self.assertEqual(status["state"], "requalification-required")
        self.assertEqual(status["requalification"],
                         ["stale-host", "stale-model", "stale-policy", "stale-source", "stale-tool"])
        self.refuses("requalification-required", self.migrate, V2, at=4)
        self.refuses("invalid-identity", hl.check_drift, self.root, {"host": "x"}, at=4)
        new = IDENTITY | {"model": "model-b:2"}
        self.refuses("automatic-promotion-disabled", hl.requalify, self.root, new, operator=ROBOT,
                     evidence=h("requalification"), at=4)
        self.refuses("invalid-evidence", hl.requalify, self.root, new, operator=HUMAN,
                     evidence="short", at=4)
        status = hl.requalify(self.root, new, operator=HUMAN, evidence=h("requalification"), at=4)
        self.assertEqual((status["state"], status["requalification"]), ("installed", []))
        self.assertEqual(status["identity"], new)
        self.assertEqual(hl.check_drift(self.root, new, at=5), [])
        self.assertEqual(hl.check_drift(self.root, IDENTITY, at=5), ["stale-model"])
        self.refuses("requalification-required", self.migrate, V2, at=6)
        # Requalifying the installation does not requalify a promotion decision: the registry
        # still refuses to serve a profile decided under the old identity.
        registry = pr.ProfileRegistry.empty(SCOPE).begin(decide(at=5), current=IDENTITY, at=6)
        hl.save_registry(self.root, registry.commit(current=IDENTITY, at=6), at=6)
        hl.requalify(self.root, new, operator=HUMAN, evidence=h("requalification-2"), at=7)
        self.assertEqual(hl.load_registry(self.root).resolve(new, cohort="synthetic").reason,
                         "stale-model")

    def test_drift_check_is_idempotent_and_records_a_journal_entry_only_on_change(self):
        drifted = IDENTITY | {"model": "model-b:2"}
        hl.check_drift(self.root, drifted, at=3)
        length = hl.status(self.root)["journal"]["entries"]
        hl.check_drift(self.root, drifted, at=4)
        self.assertEqual(hl.status(self.root)["journal"]["entries"], length)


class CanaryIncidentRevocationTests(Case):
    @classmethod
    def setUpClass(cls):
        cls.world = World(evidence=[h("lesson-1")])

    def setUp(self):
        super().setUp()
        self.install(at=1)
        self.migrate(V1, at=2)

    def inputs(self, **over):
        w = self.world
        return {"registration": w.registration, "evaluation": w.report, "base_files": w.base,
                "candidate_files": w.candidate, "proposer": PROPOSER, "acceptance": w.accept(),
                "identity": IDENTITY, "evaluated_at": 10} | CLEAR | over

    def shadow(self, pol=None):
        return ap.PolicyRun(pol or ap.build_policy(CONTROL)).enable(HUMAN, at=11)

    def test_canary_uses_the_persisted_registry_and_never_activates(self):
        run = hl.begin_canary(self.root, self.shadow(), self.world.record, at=12, **self.inputs())
        self.assertEqual((run.state, run.canary), ("canary", "running"))
        for _ in range(3):
            step = hl.observe_canary(self.root, run, "ok", current=IDENTITY, at=13)
            run = step.run
        self.assertEqual(run.canary, "complete")
        self.refuses("activation-requires-adoption", hl.activate, self.root)
        self.assertIsNone(hl.load_registry(self.root).active)
        events = [e["event"] for e in hl.status(self.root)["events"]]
        self.assertEqual(events[-4:], ["canary-begun"] + ["canary-observed"] * 3)
        with self.assertRaises(ap.AutoPromotionError):
            run.activate()

    def test_production_policy_abstains_and_the_refusal_is_not_hidden(self):
        prod = ap.build_policy(CONTROL | {"tolerablePendingEndpoints": []})
        with self.assertRaises(ap.AutoPromotionError) as ctx:
            hl.begin_canary(self.root, self.shadow(prod), self.world.record, at=12,
                            **self.inputs())
        self.assertEqual(ctx.exception.reason, "pending-endpoints")

    def test_canary_is_gated_by_lifecycle_health(self):
        self.refuses("invalid-input", hl.begin_canary, self.root, self.shadow(), self.world.record,
                     at=12, registry=pr.ProfileRegistry.empty(SCOPE), **self.inputs())
        self.refuses("identity-drift", hl.begin_canary, self.root, self.shadow(),
                     self.world.record, at=12, **self.inputs(identity=IDENTITY | {"model": "m:2"}))
        self.refuses("profile-expired", hl.begin_canary, self.root, self.shadow(),
                     self.world.record, at=1000, **self.inputs())
        hl.check_drift(self.root, IDENTITY | {"host": "host-b:2"}, at=12)
        self.refuses("requalification-required", hl.begin_canary, self.root, self.shadow(),
                     self.world.record, at=12, **self.inputs())

    def test_canary_drift_stop_rolls_back_the_registry_and_requires_requalification(self):
        first = decide(at=5)
        second = decide(at=6, rollback=first.to_dict()["profileSha256"])
        registry = (pr.ProfileRegistry.empty(SCOPE).begin(first, current=IDENTITY, at=20)
                    .commit(current=IDENTITY, at=20).begin(second, current=IDENTITY, at=20)
                    .commit(current=IDENTITY, at=20))
        hl.save_registry(self.root, registry, at=20)
        run = hl.begin_canary(self.root, self.shadow(), self.world.record, at=21,
                              **self.inputs(evaluated_at=10))
        step = hl.observe_canary(self.root, run, "ok", current=IDENTITY | {"model": "m:2"}, at=22)
        self.assertEqual((step.run.state, step.run.journal[-1]["reason"]), ("stopped", "drift-stop"))
        self.assertEqual(hl.load_registry(self.root).active, first.sha256)  # prior preserved
        status = hl.status(self.root)
        self.assertEqual(status["requalification"], ["stale-model"])
        self.assertEqual(status["events"][-1]["event"], "canary-stopped")

    def test_incident_stop_halts_rolls_back_and_needs_a_human_to_clear(self):
        first = decide(at=5)
        second = decide(at=6, rollback=first.to_dict()["profileSha256"])
        registry = (pr.ProfileRegistry.empty(SCOPE).begin(first, current=IDENTITY, at=20)
                    .commit(current=IDENTITY, at=20).begin(second, current=IDENTITY, at=20)
                    .commit(current=IDENTITY, at=20))
        hl.save_registry(self.root, registry, at=20)
        stop = hl.incident_stop(self.root, at=30)
        self.assertIsNone(stop.registryFailure)
        self.assertEqual(hl.load_registry(self.root).active, first.sha256)
        status = hl.status(self.root)
        self.assertEqual((status["state"], status["halted"]), ("halted", "incident-stop"))
        self.refuses("incident-stop", self.migrate, V2, at=31)
        self.refuses("incident-stop", hl.begin_canary, self.root, self.shadow(), self.world.record,
                     at=31, **self.inputs())
        # A second stop still halts; with nothing active the registry failure is visible.
        hl.incident_stop(self.root, at=31)
        again = hl.incident_stop(self.root, at=32)
        self.assertEqual(again.registryFailure, "no-active-profile")
        self.refuses("automatic-promotion-disabled", hl.clear_incident, self.root, operator=ROBOT,
                     evidence=h("postmortem"), at=33)
        status = hl.clear_incident(self.root, operator=HUMAN, evidence=h("postmortem"), at=33)
        self.assertIsNone(status["halted"])
        self.refuses("not-halted", hl.clear_incident, self.root, operator=HUMAN,
                     evidence=h("postmortem"), at=34)

    def test_incident_stop_with_a_canary_stops_the_run(self):
        run = hl.begin_canary(self.root, self.shadow(), self.world.record, at=12, **self.inputs())
        stop = hl.incident_stop(self.root, at=13, run=run)
        self.assertEqual((stop.run.state, stop.run.journal[-1]["reason"]),
                         ("stopped", "incident-stop"))
        self.assertEqual(stop.registryFailure, "no-active-profile")
        self.assertEqual(hl.status(self.root)["halted"], "incident-stop")

    def test_revocation_propagates_to_registry_and_curation_without_rewriting_history(self):
        first = decide(at=5, evidence=[h("lesson-1")])
        hl.save_registry(self.root, pr.ProfileRegistry.empty(SCOPE).begin(
            first, current=IDENTITY, at=20).commit(current=IDENTITY, at=20), at=20)
        store = library("e1")
        registry, curated = hl.revoke(self.root, h("lesson-1"), at=200, reason="lesson-revoked",
                                      store=store)
        self.assertIsNone(registry.active)
        self.assertIn(h("lesson-1"), hl.load_registry(self.root).revoked)
        self.assertEqual(curated.revoked, ())  # e1 does not cite lesson-1
        _, curated = hl.revoke(self.root, h("ev-e1"), at=201, reason="lesson-revoked", store=store)
        self.assertEqual(curated.revoked, ("e1",))
        self.assertEqual(store.get("e1").state, "active")  # the caller's value is untouched
        self.refuses("already-revoked", hl.revoke, self.root, h("lesson-1"), at=202,
                     reason="again")
        self.assertEqual(hl.load_registry(self.root).decisions[first.sha256], first.data)

    def test_registry_updates_must_extend_the_stored_journal_and_scope(self):
        registry = pr.ProfileRegistry.empty(SCOPE).begin(decide(at=5), current=IDENTITY, at=20)
        hl.save_registry(self.root, registry, at=20)
        before = tree(self.root)
        self.refuses("concurrent-update", hl.save_registry, self.root,
                     pr.ProfileRegistry.empty(SCOPE), at=21)
        self.refuses("scope-mismatch", hl.save_registry, self.root,
                     pr.ProfileRegistry.empty("task-002"), at=21)
        self.refuses("invalid-registry", hl.save_registry, self.root, "registry", at=21)
        self.assertEqual(tree(self.root), before)
        self.assertTrue(hl.status(self.root)["registryConsistent"])

    def test_a_crash_between_state_and_registry_writes_keeps_the_halt_and_is_repairable(self):
        first = decide(at=5)
        hl.save_registry(self.root, pr.ProfileRegistry.empty(SCOPE).begin(
            first, current=IDENTITY, at=20).commit(current=IDENTITY, at=20), at=20)
        with mock.patch.object(hl, "save_registry_file",
                               side_effect=pr.PromotionError("registry-unavailable")):
            stop = hl.incident_stop(self.root, at=30)
        self.assertEqual(stop.registryFailure, "registry-unavailable")
        status = hl.status(self.root)
        self.assertEqual((status["halted"], status["registryConsistent"]),
                         ("incident-stop", False))
        self.assertEqual(hl.load_registry(self.root).active, first.sha256)  # not yet rolled back
        self.refuses("registry-inconsistent", hl.revoke, self.root, h("x"), at=31, reason="r")
        stop = hl.incident_stop(self.root, at=31)  # repeating the stop completes it
        self.assertIsNone(stop.registryFailure)
        self.assertIsNone(hl.load_registry(self.root).active)
        self.assertTrue(hl.status(self.root)["registryConsistent"])

    def test_observing_on_a_halted_or_drifted_installation_stops_the_run(self):
        run = hl.begin_canary(self.root, self.shadow(), self.world.record, at=12, **self.inputs())
        hl.incident_stop(self.root, at=13)
        step = hl.observe_canary(self.root, run, "ok", current=IDENTITY, at=14)
        self.assertEqual((step.run.state, step.run.journal[-1]["reason"]),
                         ("stopped", "incident-stop"))
        hl.clear_incident(self.root, operator=HUMAN, evidence=h("pm"), at=15)
        run = hl.begin_canary(self.root, self.shadow(), self.world.record, at=16, **self.inputs())
        hl.check_drift(self.root, IDENTITY | {"host": "host-b:2"}, at=17)
        step = hl.observe_canary(self.root, run, "ok", current=IDENTITY, at=18)
        self.assertEqual(step.run.journal[-1]["reason"], "drift-stop")

    def test_other_refusals_leave_everything_unchanged(self):
        before = tree(self.root)
        self.refuses("invalid-reason", hl.revoke, self.root, h("x"), at=20, reason="bad reason")
        self.refuses("invalid-time", hl.begin_canary, self.root, self.shadow(), self.world.record,
                     at=None, **self.inputs())
        self.refuses("invalid-time", hl.check_drift, self.root, IDENTITY, at=None)
        self.assertEqual(tree(self.root), before)

    def test_stops_still_halt_when_the_journal_is_full(self):
        evidence = h("requalification")
        with self.assertRaises(hl.LifecycleError) as ctx:
            for at in range(3, 400):
                hl.requalify(self.root, IDENTITY, operator=HUMAN, evidence=evidence, at=at)
        self.assertEqual(ctx.exception.reason, "journal-full")
        reserved = hl.MAX_JOURNAL - hl.STOP_RESERVE
        self.assertEqual(hl.status(self.root)["journal"]["entries"], reserved)
        hl.incident_stop(self.root, at=399)
        self.assertEqual(hl.status(self.root)["events"][reserved]["event"], "incident-stop")
        for at in range(400, 400 + hl.STOP_RESERVE + 2):
            hl.incident_stop(self.root, at=at)
        status = hl.status(self.root)
        self.assertEqual((status["halted"], status["journal"]["entries"]),
                         ("incident-stop", hl.MAX_JOURNAL))


class RetentionAndUninstallTests(Case):
    def setUp(self):
        super().setUp()
        self.install()

    def test_private_records_need_an_explicit_retention_tick_and_are_never_auto_deleted(self):
        a = hl.retain(self.root, b"trace one", kind="trace", retain_until=10, at=2)
        b = hl.retain(self.root, b"lesson two", kind="lesson", retain_until=100, at=2)
        self.assertEqual(a, sha256(b"trace one").hexdigest())
        for kwargs, reason in (({"retain_until": None}, "invalid-retention"),
                               ({"retain_until": 2}, "invalid-retention"),
                               ({"kind": "secret"}, "invalid-kind")):
            self.refuses(reason, hl.retain, self.root, b"x", **({"kind": "trace", "retain_until": 9,
                                                                 "at": 2} | kwargs))
        self.refuses("duplicate-record", hl.retain, self.root, b"trace one", kind="trace",
                     retain_until=10, at=2)
        self.refuses("record-too-large", hl.retain, self.root, b"x" * (hl.MAX_PRIVATE_BYTES + 1),
                     kind="trace", retain_until=10, at=2)
        hl.status(self.root, now=10_000)  # reading past the retention tick deletes nothing
        self.assertTrue((self.owned / "private" / a).exists())
        self.refuses("automatic-promotion-disabled", hl.purge, self.root, now=50, operator=ROBOT,
                     at=50)
        receipt = hl.purge(self.root, now=50, operator=HUMAN, at=50)
        self.assertEqual(receipt["purged"], [a])
        self.assertFalse((self.owned / "private" / a).exists())
        self.assertTrue((self.owned / "private" / b).exists())
        status = hl.status(self.root)
        self.assertEqual([r["sha256"] for r in status["private"]], [b])
        self.assertEqual(status["events"][-1], {"seq": status["events"][-1]["seq"],
                                                "event": "purged", "at": 50, "actor": HUMAN["id"],
                                                "subject": None, "detail": [a]})
        self.assertEqual(hl.purge(self.root, now=50, operator=HUMAN, at=51)["purged"], [])

    def test_symlinked_blob_directories_are_refused_before_any_write_or_delete(self):
        digest = hl.retain(self.root, b"trace", kind="trace", retain_until=10, at=2)
        outside = self.outer / "elsewhere"
        for name in ("private", "profiles"):
            moved = self.root / f"moved-{name}"
            (self.owned / name).rename(moved)
            outside.mkdir()
            (self.owned / name).symlink_to(outside)
            self.refuses("foreign-content", self.migrate, V1, at=3)
            self.refuses("foreign-content", hl.retain, self.root, b"x", kind="trace",
                         retain_until=10, at=3)
            self.refuses("foreign-content", hl.purge, self.root, now=20, operator=HUMAN, at=20)
            self.refuses("foreign-content", hl.uninstall, self.root, operator=HUMAN, at=20)
            self.refuses("foreign-content", hl.recover, self.root)
            self.assertEqual(os.listdir(outside), [])
            (self.owned / name).unlink()
            outside.rmdir()
            moved.rename(self.owned / name)
        self.assertTrue((self.owned / "private" / digest).exists())

    def test_interrupted_purge_is_completed_by_recover(self):
        digest = hl.retain(self.root, b"trace", kind="trace", retain_until=10, at=2)
        with mock.patch.object(hl, "_unlink", side_effect=OSError("crash")):
            receipt = hl.purge(self.root, now=20, operator=HUMAN, at=20)
        self.assertEqual((receipt["purged"], receipt["failures"]), ([digest], [digest]))
        self.assertEqual(hl.status(self.root)["debris"], [f"private/{digest}"])
        hl.recover(self.root)
        self.assertFalse((self.owned / "private" / digest).exists())
        self.refuses("invalid-time", hl.purge, self.root, now=30, operator=HUMAN, at=21)

    def test_uninstall_removes_every_owned_file_and_returns_a_receipt(self):
        hl.retain(self.root, b"trace", kind="trace", retain_until=10, at=2)
        self.migrate(V1, at=3)
        self.migrate(V2, at=4)
        hl.save_registry(self.root, pr.ProfileRegistry.empty(SCOPE).begin(
            decide(at=5), current=IDENTITY, at=20), at=20)
        owned = sorted(p.relative_to(self.owned).as_posix() for p in self.owned.rglob("*")
                       if p.is_file())
        self.refuses("automatic-promotion-disabled", hl.uninstall, self.root, operator=ROBOT,
                     at=21)
        receipt = hl.uninstall(self.root, operator=HUMAN, at=21)
        self.assertIs(receipt["executionAuthorization"], False)
        self.assertEqual(sorted(r["path"] for r in receipt["removed"]), owned)
        self.assertEqual(receipt["operator"], HUMAN["id"])
        self.assertEqual(os.listdir(self.root), [])
        self.assertEqual(hl.residue(self.root), [])
        self.assertEqual(hl.status(self.root)["state"], "not-installed")
        # Reinstalling starts fresh: nothing of the previous installation survives.
        self.assertIsNone(self.install(at=30)["current"])

    def test_unrelated_files_beside_the_installation_are_never_touched(self):
        (self.root / "project.md").write_bytes(b"mine")
        (self.root / ".braid-harness-lifecycle-notes").write_bytes(b"also mine")
        hl.uninstall(self.root, operator=HUMAN, at=2)
        hl.recover(self.root)
        self.assertEqual(sorted(os.listdir(self.root)), [".braid-harness-lifecycle-notes",
                                                         "project.md"])


class StaticTests(unittest.TestCase):
    def test_module_has_no_network_process_clock_or_host_access(self):
        source = Path(hl.__file__).read_text()
        tree_ = ast.parse(source)
        imported = {a.name.split(".")[0] for n in ast.walk(tree_) if isinstance(n, ast.Import)
                    for a in n.names}
        imported |= {n.module.split(".")[0] for n in ast.walk(tree_)
                     if isinstance(n, ast.ImportFrom) and n.level == 0}
        self.assertFalse(imported & {"subprocess", "socket", "urllib", "http", "time",
                                     "datetime", "random", "shutil"})
        self.assertIs(pr.AUTOMATIC_PROMOTION, False)


if __name__ == "__main__":
    unittest.main()
