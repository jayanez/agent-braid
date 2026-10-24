# SPDX-License-Identifier: AGPL-3.0-only
"""Offline observation controls; no host, native or utility acceptance."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
import unittest

from agent_braid import harness_observation as obs
from agent_braid.system_one import canonical, thaw

SECRET = "sk-test-SECRET-0123456789"
NOW = 1_800_000_000
MANIFEST = "a" * 64


def inventory_wire(**over) -> dict:
    wire = {"format": obs.INVENTORY_FORMAT, "allowedEventFields": ["text", "tool", "state", "effect", "path"],
            "secrets": [SECRET], "maxRetentionSeconds": 3600}
    wire.update(over)
    return wire


def make_inventory(**over) -> obs.ExportInventory:
    wire = inventory_wire(**over)
    return obs.verify_inventory(canonical(wire), expected_sha256=sha256(canonical(wire)).hexdigest())


def events(*extra, terminal="completed") -> list:
    out = [{"seq": 0, "kind": "start"}, *extra]
    if terminal:
        out.append({"seq": len(out), "kind": "terminal", "state": terminal})
    return out


def observe(evts=None, **over):
    args = dict(manifest_sha256=MANIFEST, attempt_id="attempt-1", source="fixture",
                inventory=make_inventory(), now=NOW, retention_seconds=60)
    args.update(over)
    return obs.observe(events() if evts is None else evts, **args)


class InventoryTests(unittest.TestCase):
    def test_hash_drift_refused(self):
        raw = canonical(inventory_wire())
        with self.assertRaises(obs.ObservationError) as ctx:
            obs.verify_inventory(raw, expected_sha256="0" * 64)
        self.assertEqual(ctx.exception.reason, "inventory-drift")

    def test_strict_shape(self):
        for wire in (inventory_wire(extra=1), inventory_wire(secrets=["short"]),
                     inventory_wire(maxRetentionSeconds=True), inventory_wire(format="future/v9"),
                     inventory_wire(allowedEventFields=["seq"]), inventory_wire(secrets=[SECRET, SECRET])):
            raw = canonical(wire)
            with self.assertRaises(obs.ObservationError, msg=wire):
                obs.verify_inventory(raw, expected_sha256=sha256(raw).hexdigest())


class NormalizationTests(unittest.TestCase):
    def test_complete_trajectory_is_completed_without_authority(self):
        o = observe(events({"seq": 1, "kind": "message", "text": "hello"}))
        d = o.to_dict()
        self.assertEqual(d["terminal"], "completed")
        self.assertFalse(d["executionAuthorization"])
        self.assertEqual(d["loss"]["missingSeq"], [])
        self.assertEqual(d["retainUntil"], NOW + 60)
        self.assertEqual(d["manifestSha256"], MANIFEST)
        self.assertEqual(len(d["rawEventsSha256"]), 64)
        self.assertEqual(d["normalizedEventsSha256"], sha256(canonical(d["events"])).hexdigest())

    def test_missing_events_cannot_complete(self):
        evts = [{"seq": 0, "kind": "start"}, {"seq": 2, "kind": "terminal", "state": "completed"}]
        d = observe(evts).to_dict()
        self.assertEqual(d["loss"]["missingSeq"], [1])
        self.assertEqual(d["terminal"], "unobserved")

    def test_declared_count_exposes_lost_tail(self):
        d = observe(events(terminal=None), expected_events=5).to_dict()
        self.assertEqual(d["loss"]["missingSeq"], [1, 2, 3, 4])
        self.assertEqual(d["terminal"], "unobserved")

    def test_no_terminal_event_is_unobserved(self):
        self.assertEqual(observe(events(terminal=None)).to_dict()["terminal"], "unobserved")

    def test_transport_error_blocks_completion_and_is_recorded(self):
        d = observe(transport_errors=("stream-reset",)).to_dict()
        self.assertEqual(d["terminal"], "unobserved")
        self.assertEqual(d["loss"]["transportErrors"], ["stream-reset"])

    def test_duplicate_and_malformed_events_counted(self):
        evts = events({"seq": 1, "kind": "message", "text": "a"})
        evts.insert(2, {"seq": 1, "kind": "message", "text": "conflict"})
        evts.append({"seq": "x", "kind": "message"})
        evts.append({"seq": 9, "kind": "mystery"})
        evts.append({"seq": True, "kind": "message"})
        d = observe(evts).to_dict()
        self.assertEqual(d["loss"]["duplicateSeq"], [1])
        self.assertEqual(d["loss"]["malformedEvents"], 3)
        self.assertEqual(d["terminal"], "unobserved")

    def test_failed_attempts_are_retained_with_state(self):
        for state in ("failed", "interrupted", "refused"):
            d = observe(events(terminal=state)).to_dict()
            self.assertEqual(d["terminal"], state)
            self.assertEqual(d["state"], "retained")

    def test_bad_inputs_refused(self):
        for over in ({"manifest_sha256": "short"}, {"attempt_id": "bad id!"}, {"source": "cloud"},
                     {"now": True}, {"retention_seconds": 0}, {"retention_seconds": 3601}):
            with self.assertRaises(obs.ObservationError, msg=over):
                observe(**over)
        with self.assertRaises(obs.ObservationError):
            observe([{"seq": i, "kind": "message"} for i in range(obs.MAX_EVENTS + 1)])


class PrivacyTests(unittest.TestCase):
    def test_raw_transcript_not_exported_and_secret_redacted(self):
        evts = events({"seq": 1, "kind": "message", "text": f"token {SECRET} ok",
                       "reasoning": "private chain", "provider_raw": {"x": 1}})
        o = observe(evts)
        text = o.canonical_bytes.decode()
        self.assertNotIn(SECRET, text)
        self.assertNotIn("private chain", text)
        d = o.to_dict()
        self.assertEqual(d["events"][1]["text"], "token [REDACTED] ok")
        self.assertEqual(d["redaction"]["replacements"], 1)
        self.assertEqual(d["redaction"]["droppedFields"], 2)
        self.assertEqual(d["redaction"]["inventorySha256"], make_inventory().sha256)
        # raw identity still binds the unredacted stream
        self.assertEqual(d["rawEventsSha256"], sha256(canonical(evts)).hexdigest())

    def test_secret_in_identity_fields_refused(self):
        with self.assertRaises(obs.ObservationError) as ctx:
            observe(after={f"dir/{SECRET}.txt": b"x"}, before={})
        self.assertEqual(ctx.exception.reason, "secret-in-identity")
        with self.assertRaises(obs.ObservationError):
            observe(attempt_id=SECRET)

    def test_secret_in_artifact_content_is_never_exported(self):
        d = observe(before={}, after={"out.txt": SECRET.encode()}).to_dict()
        self.assertNotIn(SECRET, json.dumps(d))
        self.assertEqual(d["artifacts"][0]["sizeBytes"], len(SECRET))


class ArtifactAndEffectTests(unittest.TestCase):
    def test_diff_and_observed_effects(self):
        before = {"keep.txt": b"1", "edit.txt": b"old", "gone.txt": b"x"}
        after = {"keep.txt": b"1", "edit.txt": b"new", "new.txt": b"n"}
        d = observe(before=before, after=after).to_dict()
        changes = {a["path"]: a for a in d["artifacts"]}
        self.assertEqual(set(changes), {"edit.txt", "gone.txt", "new.txt"})
        self.assertEqual(changes["edit.txt"]["change"], "modified")
        self.assertEqual(changes["edit.txt"]["beforeSha256"], sha256(b"old").hexdigest())
        self.assertEqual(changes["edit.txt"]["afterSha256"], sha256(b"new").hexdigest())
        self.assertIsNone(changes["new.txt"]["beforeSha256"])
        self.assertIsNone(changes["gone.txt"]["afterSha256"])
        self.assertEqual({(e["kind"], e["path"], e["evidence"]) for e in d["effects"]},
                         {("write", "edit.txt", "observed"), ("delete", "gone.txt", "observed"),
                          ("create", "new.txt", "observed")})

    def test_uncorroborated_declared_effect_is_inferred(self):
        evts = events({"seq": 1, "kind": "effect", "effect": "write", "path": "claimed.txt"},
                      {"seq": 2, "kind": "effect", "effect": "create", "path": "real.txt"},
                      {"seq": 3, "kind": "effect", "effect": "network"})
        d = observe(evts, before={}, after={"real.txt": b"r"}).to_dict()
        got = {(e["kind"], e.get("path"), e["evidence"]) for e in d["effects"]}
        self.assertEqual(got, {("write", "claimed.txt", "inferred"), ("create", "real.txt", "observed"),
                               ("network", None, "inferred")})

    def test_unobserved_artifacts_when_not_supplied(self):
        d = observe().to_dict()
        self.assertEqual(d["artifacts"], [])
        self.assertFalse(d["artifactsObserved"])
        self.assertTrue(observe(before={}, after={}).to_dict()["artifactsObserved"])

    def test_artifact_path_and_limits(self):
        for bad in ("../x", "/abs", "a\\b", "a//b", "", "a/./b"):
            with self.assertRaises(obs.ObservationError, msg=bad):
                observe(before={}, after={bad: b"x"})
        with self.assertRaises(obs.ObservationError):
            observe(before={}, after={f"f{i}": b"x" for i in range(obs.MAX_ARTIFACTS + 1)})
        with self.assertRaises(obs.ObservationError):
            observe(before={}, after={"big": b"x" * (obs.MAX_ARTIFACT_BYTES + 1)})
        with self.assertRaises(obs.ObservationError):
            observe(before={}, after={"s": "text"})
        with self.assertRaises(obs.ObservationError):  # one side only is not a diff
            observe(before={})


class RetentionAndReuseTests(unittest.TestCase):
    def test_verify_roundtrip_and_expiry(self):
        o = observe()
        again = obs.verify_observation(o.canonical_bytes, expected_sha256=o.sha256, now=NOW + 59)
        self.assertEqual(again.sha256, o.sha256)
        with self.assertRaises(obs.ObservationError) as ctx:
            obs.verify_observation(o.canonical_bytes, expected_sha256=o.sha256, now=NOW + 60)
        self.assertEqual(ctx.exception.reason, "observation-expired")

    def test_drift_future_format_and_tamper_refused(self):
        o = observe()
        with self.assertRaises(obs.ObservationError) as ctx:
            obs.verify_observation(o.canonical_bytes, expected_sha256="0" * 64, now=NOW)
        self.assertEqual(ctx.exception.reason, "observation-drift")
        for mutate in (lambda d: d.update(format="braid-harness-observation/v9"),
                       lambda d: d.update(extra=1),
                       lambda d: d.update(executionAuthorization=True),
                       lambda d: d.update(terminal="success"),
                       lambda d: d.update(retainUntil=True)):
            d = o.to_dict()
            mutate(d)
            raw = canonical(d)
            with self.assertRaises(obs.ObservationError, msg=d):
                obs.verify_observation(raw, expected_sha256=sha256(raw).hexdigest(), now=NOW)

    def test_verify_with_inventory_rejects_leaked_secret(self):
        d = observe().to_dict()
        d["events"][0]["text"] = SECRET
        d["normalizedEventsSha256"] = sha256(canonical(d["events"])).hexdigest()
        raw = canonical(d)
        with self.assertRaises(obs.ObservationError) as ctx:
            obs.verify_observation(raw, expected_sha256=sha256(raw).hexdigest(), now=NOW,
                                   inventory=make_inventory())
        self.assertEqual(ctx.exception.reason, "secret-in-export")

    def test_purged_record_is_not_reusable(self):
        purged = obs.purge_expired([observe()], now=NOW + 60)[0][0]
        with self.assertRaises(obs.ObservationError):
            obs.verify_observation(purged.canonical_bytes, expected_sha256=purged.sha256, now=NOW)


class PurgeTests(unittest.TestCase):
    def test_purge_drops_payload_but_retains_failures(self):
        ok = observe(events({"seq": 1, "kind": "message", "text": "x"}), attempt_id="ok")
        bad = observe(events({"seq": 1, "kind": "message", "text": "x"}, terminal="failed"),
                      attempt_id="bad", before={}, after={"o": b"1"})
        live = observe(attempt_id="live", retention_seconds=3600)
        kept, receipt = obs.purge_expired([ok, bad, live], now=NOW + 600)
        by_id = {o.to_dict()["attemptId"]: o.to_dict() for o in kept}
        self.assertEqual(len(kept), 3)  # nothing silently disappears
        self.assertEqual(by_id["live"]["state"], "retained")
        self.assertEqual(by_id["ok"]["state"], "purged")
        self.assertEqual(by_id["ok"]["events"], [])
        self.assertEqual(by_id["bad"]["state"], "purged")
        self.assertEqual(by_id["bad"]["terminal"], "failed")
        self.assertEqual(by_id["bad"]["artifacts"], [])
        self.assertEqual(by_id["bad"]["rawEventsSha256"], bad.to_dict()["rawEventsSha256"])
        self.assertEqual(by_id["bad"]["purgedPayloadSha256"], bad.sha256)
        self.assertEqual({r["attemptId"] for r in receipt["purged"]}, {"ok", "bad"})
        self.assertNotIn("events", json.dumps(receipt))

    def test_purge_is_idempotent(self):
        kept, _ = obs.purge_expired([observe()], now=NOW + 60)
        again, receipt = obs.purge_expired(kept, now=NOW + 120)
        self.assertEqual(again[0].sha256, kept[0].sha256)
        self.assertEqual(receipt["purged"], [])


class ImmutabilityTests(unittest.TestCase):
    def test_frozen(self):
        o = observe()
        with self.assertRaises(FrozenInstanceError):
            o.sha256_override = 1  # type: ignore[attr-defined]
        with self.assertRaises(TypeError):
            o.data["terminal"] = "completed"
        d = o.to_dict()
        d["terminal"] = "tampered"
        self.assertEqual(o.to_dict()["terminal"], "completed")
        self.assertEqual(thaw(o.data), o.to_dict())


if __name__ == "__main__":
    unittest.main()
