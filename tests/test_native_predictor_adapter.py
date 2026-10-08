import copy
import hashlib
import json
import unittest

from agent_braid.m35_source_window import EVENT_FORMAT
from agent_braid.native_predictor_adapter import ReviewedLocalGate, adapt as _adapt
from agent_braid.native_predictor_training import FEATURE_VERSION
from agent_braid.structured_exchange import ROOT


def adapt(events, **kwargs):
    """Supply only hand-authored synthetic window and census metadata."""
    source_kind = kwargs["source_kind"]
    if "window_metadata" not in kwargs:
        kwargs["window_metadata"] = {
            "format": "m35-source-window-v1", "sourceKind": source_kind,
            "windowId": "window-a", "familyId": kwargs["family_id"],
            "startUtc": "2026-10-01T00:00:00Z", "endUtc": "2026-10-15T00:00:00Z",
            "registrationRunId": 17 if source_kind == "prospective" else None,
            "protocolCommit": "a" * 40}
    if "admissions" not in kwargs:
        kwargs["admissions"] = [
            {"sessionId": event["sessionId"], "eventId": event["eventId"],
             "timestampUtc": event["timestampUtc"]}
            for event in events if event["kind"] == "session-open"]
    return _adapt(events, **kwargs)


def _hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def records(*, missing_receipt=False, dependent=False, unsupported=False,
            session_id="session-a", start_sequence=0, previous_hash=None, prefix=""):
    open_id = prefix + "open-id"
    specs = [("session-open", {"participants": ["actor-a", "actor-b", "actor-c"],
                               "base": [{"id": "b1", "value": "base"}], "sourceRef": "private/path",
                               "contextSha": "a" * 40}),
             ("base-seen", {"actorId": "actor-a", "baseEventId": open_id}),
             ("base-seen", {"actorId": "actor-b", "baseEventId": open_id}),
             ("base-seen", {"actorId": "actor-c", "baseEventId": open_id})]
    if dependent:
        specs.append(("external-observation", {"actorId": "actor-b"}))
    for n, actor in enumerate(("actor-a", "actor-b", "actor-c")):
        op = {"id": f"{prefix}op-{n}", "kind": "insert", "anchorId": ROOT if n == 0 else "b1",
              "newId": f"{prefix}new-{n}", "value": f"synthetic value {n}"}
        if unsupported and n == 2:
            op["kind"] = "delete"
        specs.append(("proposal", {"actorId": actor, "baseEventId": open_id, "operation": op,
                                    "sourceRef": "private/path"}))
    specs.append(("session-close", {"outcome": "accepted"}))
    if missing_receipt:
        specs = [s for s in specs if not (s[0] == "base-seen" and s[1]["actorId"] == "actor-c")]
    result, previous = [], previous_hash
    for local_seq, (kind, data) in enumerate(specs):
        seq = start_sequence + local_seq
        event_id = open_id if kind == "session-open" else f"{prefix}event-{seq}"
        body = {"format": EVENT_FORMAT, "sequence": seq, "eventId": event_id,
                "timestampUtc": f"2026-10-01T00:00:{seq:02d}Z", "kind": kind,
                "sessionId": session_id, "data": data, "previousHash": previous}
        event = {**body, "eventHash": _hash(body)}
        result.append(event)
        previous = event["eventHash"]
    return result


class NativePredictorAdapterTests(unittest.TestCase):
    def test_pairs_are_exhaustive_deterministic_and_oriented_by_event_order(self):
        source = records()
        first = adapt(source, source_kind="synthetic", family_id="family-a", partition="train")
        second = adapt(copy.deepcopy(source), source_kind="synthetic", family_id="family-a", partition="train")
        self.assertEqual(first, second)
        self.assertEqual(len(first["pairs"]), 3)
        self.assertTrue(all("excludedReason" not in pair for pair in first["pairs"]))
        self.assertEqual(first["pairs"][0]["request"]["operations"][0]["id"], "op-0")
        self.assertEqual(first["pairs"][0]["request"]["operations"][1]["id"], "op-1")
        self.assertTrue(all(pair["featureVector"]["version"] == FEATURE_VERSION
                            for pair in first["pairs"]))

    def test_global_sequence_accepts_multiple_sessions_and_enumerates_all_pairs_once(self):
        first = records()
        second = records(session_id="session-b", start_sequence=len(first),
                         previous_hash=first[-1]["eventHash"], prefix="second-")
        result = adapt(first + second, source_kind="synthetic", family_id="family-a", partition="train")
        self.assertEqual(len(result["pairs"]), 6)
        self.assertEqual(len({pair["pairId"] for pair in result["pairs"]}), 6)
        self.assertEqual(len(result["sessionCommitments"]), 2)

    def test_hash_tamper_is_rejected_without_echoing_identifiers(self):
        source = records()
        source[2]["data"]["actorId"] = "sensitive-identifier"
        with self.assertRaises(ValueError) as error:
            adapt(source, source_kind="synthetic", family_id="family-a", partition="train")
        self.assertNotIn("sensitive-identifier", str(error.exception))

    def test_outputs_are_label_free_and_hide_actor_context_and_source_refs(self):
        result = adapt(records(), source_kind="synthetic", family_id="family-a", partition="train")
        serialized = str(result)
        for forbidden in ("actor-a", "actor-b", "sourceRef", "private/path", "outcome"):
            self.assertNotIn(forbidden, serialized)
        self.assertTrue(all(pair["label"] is None for pair in result["pairs"]))

    def test_every_pair_has_explicit_exclusion_when_receipt_missing_or_observation_seen(self):
        no_receipt = adapt(records(missing_receipt=True), source_kind="synthetic",
                           family_id="family-a", partition="train")
        observed = adapt(records(dependent=True), source_kind="synthetic",
                         family_id="family-a", partition="train")
        self.assertEqual(len(no_receipt["pairs"]), 3)
        self.assertEqual(sum("excludedReason" in p for p in no_receipt["pairs"]), 2)
        self.assertEqual(sum(p.get("excludedReason") == "dependent-observation"
                             for p in observed["pairs"]), 2)
        self.assertEqual(sum("request" in p for p in observed["pairs"]), 1)

    def test_partial_session_is_refused_and_unsupported_pair_is_excluded(self):
        with self.assertRaises(ValueError):
            adapt(records()[:-1], source_kind="synthetic", family_id="family-a", partition="train")
        result = adapt(records(unsupported=True), source_kind="synthetic",
                       family_id="family-a", partition="train")
        self.assertEqual(len(result["pairs"]), 3)
        self.assertTrue(any(p.get("excludedReason") == "unsupported-operation"
                            for p in result["pairs"]))

    def test_prospective_fails_closed_even_with_fabricated_registration_and_gate(self):
        error = "prospective adaptation unavailable: no independently verified registration"
        with self.assertRaisesRegex(ValueError, error):
            adapt(records(), source_kind="prospective", family_id="family-a", partition="train")
        event_records = records()
        metadata = {"format": "m35-source-window-v1", "sourceKind": "prospective",
                    "windowId": "window-a", "familyId": "family-a",
                    "startUtc": "2026-10-01T00:00:00Z", "endUtc": "2026-10-15T00:00:00Z",
                    "registrationRunId": 17, "protocolCommit": "a" * 40}
        admissions = [{"sessionId": "session-a", "eventId": event_records[0]["eventId"],
                       "timestampUtc": event_records[0]["timestampUtc"]}]
        gate = ReviewedLocalGate(reviewed=True, completeness_declared=True,
                                 protocol_review_declared=True)
        # Even internally consistent caller-supplied values (including an
        # apparently valid run ID and registration timing) are not receipts.
        metadata["registrationRunId"] = 999999
        with self.assertRaisesRegex(ValueError, error):
            adapt(event_records, source_kind="prospective", family_id="family-a", partition="train",
                  gate=gate, window_metadata=metadata, admissions=admissions)

    def test_prospective_gate_without_window_or_admission_census_fails_closed(self):
        gate = ReviewedLocalGate(reviewed=True, completeness_declared=True,
                                 protocol_review_declared=True)
        with self.assertRaisesRegex(ValueError, "prospective adaptation unavailable"):
            _adapt(records(), source_kind="prospective", family_id="family-a", partition="train",
                   gate=gate)

    def test_missing_or_mismatched_manifest_is_rejected_even_for_synthetic_label(self):
        events = records()
        admissions = [{"sessionId": events[0]["sessionId"], "eventId": events[0]["eventId"],
                       "timestampUtc": events[0]["timestampUtc"]}]
        with self.assertRaises(ValueError):
            _adapt(events, source_kind="synthetic", family_id="family-a", partition="train",
                   admissions=admissions)
        wrong_source = {"format": "m35-source-window-v1", "sourceKind": "prospective",
                        "windowId": "window-a", "familyId": "family-a",
                        "startUtc": "2026-10-01T00:00:00Z", "endUtc": "2026-10-15T00:00:00Z",
                        "registrationRunId": 17, "protocolCommit": "a" * 40}
        with self.assertRaises(ValueError):
            _adapt(events, source_kind="synthetic", family_id="family-a", partition="train",
                   window_metadata=wrong_source, admissions=admissions)

    def test_close_outcome_does_not_change_pair_model_inputs(self):
        accepted = records()
        rejected = copy.deepcopy(accepted)
        rejected[-1]["data"]["outcome"] = "rejected"
        previous = None
        for event in rejected:
            event["previousHash"] = previous
            body = {key: value for key, value in event.items() if key != "eventHash"}
            event["eventHash"] = _hash(body)
            previous = event["eventHash"]
        left = adapt(accepted, source_kind="synthetic", family_id="family-a", partition="train")
        right = adapt(rejected, source_kind="synthetic", family_id="family-a", partition="train")
        for first, second in zip(left["pairs"], right["pairs"]):
            self.assertEqual((first["request"], first["requestHash"], first["featureVector"]),
                             (second["request"], second["requestHash"], second["featureVector"]))

    def test_malformed_participants_and_window_metadata_fail_closed(self):
        malformed = records()
        malformed[0]["data"]["participants"] = [["unhashable"]]
        previous = None
        for event in malformed:
            event["previousHash"] = previous
            body = {key: value for key, value in event.items() if key != "eventHash"}
            event["eventHash"] = _hash(body)
            previous = event["eventHash"]
        with self.assertRaises(ValueError):
            adapt(malformed, source_kind="synthetic", family_id="family-a", partition="train")
        metadata = {"format": "m35-source-window-v1", "sourceKind": "synthetic",
                    "windowId": "window-a", "familyId": "family-a",
                    "startUtc": "2026-10-01T00:00:00Z", "endUtc": "2026-10-15T00:00:00Z",
                    "registrationRunId": None, "protocolCommit": "a" * 40}
        result = adapt(records(), source_kind="synthetic", family_id="family-a", partition="train",
                       window_metadata=metadata)
        self.assertEqual(len(result["pairs"]), 3)
        with self.assertRaises(ValueError):
            adapt(records(), source_kind="synthetic", family_id="family-b", partition="train",
                  window_metadata=metadata)

    def test_feature_vector_is_accepted_by_trainer_feature_interface(self):
        from agent_braid.native_predictor_training import feature_vector
        result = adapt(records(), source_kind="synthetic", family_id="family-a", partition="train")
        for pair in result["pairs"]:
            self.assertEqual(pair["featureVector"],
                             feature_vector(pair["featureVector"]["features"]))

    def test_extreme_feature_content_stays_outside_contract_without_verifier_boundary(self):
        source = records()
        for event in source:
            if event["kind"] == "proposal":
                event["data"]["operation"]["value"] = "x" * 10000
        previous = None
        for event in source:
            event["previousHash"] = previous
            body = {key: value for key, value in event.items() if key != "eventHash"}
            event["eventHash"] = _hash(body)
            previous = event["eventHash"]
        result = adapt(source, source_kind="synthetic", family_id="family-a", partition="train")
        self.assertTrue(all(p.get("excludedReason") == "outside-model-contract"
                            for p in result["pairs"]))
        self.assertNotIn("executionAuthorization", result)
        self.assertNotIn("certificate", result)

    def test_duplicate_event_ids_and_invalid_timestamps_fail_closed(self):
        duplicate = records()
        duplicate[1]["eventId"] = duplicate[0]["eventId"]
        previous = None
        for event in duplicate:
            event["previousHash"] = previous
            body = {key: value for key, value in event.items() if key != "eventHash"}
            event["eventHash"] = _hash(body)
            previous = event["eventHash"]
        with self.assertRaises(ValueError):
            adapt(duplicate, source_kind="synthetic", family_id="family-a", partition="train")
        invalid_time = records()
        invalid_time[1]["timestampUtc"] = "yesterday"
        previous = None
        for event in invalid_time:
            event["previousHash"] = previous
            body = {key: value for key, value in event.items() if key != "eventHash"}
            event["eventHash"] = _hash(body)
            previous = event["eventHash"]
        with self.assertRaises(ValueError):
            adapt(invalid_time, source_kind="synthetic", family_id="family-a", partition="train")


if __name__ == "__main__":
    unittest.main()
