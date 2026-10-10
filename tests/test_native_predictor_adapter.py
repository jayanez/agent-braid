import copy
import hashlib
import json
import unittest

from agent_braid.m35_source_window import EVENT_FORMAT
from agent_braid.native_predictor_adapter import (
    ReviewedLocalGate, adapt as _adapt, derive_duplicate_group_ids, project_trainer_rows,
)
from agent_braid.native_predictor_training import FEATURE_VERSION, fit
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
            session_id="session-a", start_sequence=0, previous_hash=None, prefix="",
            same_timestamp=False, value_prefix="synthetic value"):
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
              "newId": f"{prefix}new-{n}", "value": f"{value_prefix} {n}"}
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
        timestamp = "2026-10-01T00:00:00Z" if same_timestamp else f"2026-10-01T00:00:{seq:02d}Z"
        body = {"format": EVENT_FORMAT, "sequence": seq, "eventId": event_id,
                "timestampUtc": timestamp, "kind": kind,
                "sessionId": session_id, "data": data, "previousHash": previous}
        event = {**body, "eventHash": _hash(body)}
        result.append(event)
        previous = event["eventHash"]
    return result


class NativePredictorAdapterTests(unittest.TestCase):
    @staticmethod
    def _inventory(pair_id, session_id, partition, *, base_id, values, op_ids,
                   anchors, operations_order=None):
        operations = [
            {"id": op_id, "kind": "insert", "anchorId": anchor,
             "newId": f"new-{op_id}", "value": value}
            for op_id, anchor, value in zip(op_ids, anchors, values)
        ]
        if operations_order is not None:
            operations = [operations[index] for index in operations_order]
        request = {"model": "anchored-sequence-v1",
                   "base": [{"id": base_id, "value": "Base\t NODE"}],
                   "operations": operations}
        pair = {"pairId": pair_id, "sessionId": session_id,
                "partition": partition, "request": request}
        return {"format": "m35-native-inventory-v1", "sourceKind": "synthetic",
                "pairs": [pair]}

    def test_duplicate_groups_normalize_text_ignore_ephemeral_ids_and_unorder_operations(self):
        first = self._inventory(
            "pair-a", "session-a", "train", base_id="base-id-a",
            values=["CAFÉ\t  x", "de\u0301cision"], op_ids=["op-a", "op-b"],
            anchors=["$root", "base-id-a"])
        second = self._inventory(
            "pair-b", "session-b", "train", base_id="different-base-id",
            values=["DÉCISION", "cafe\u0301 x"], op_ids=["ephemeral-1", "ephemeral-2"],
            anchors=["different-base-id", "$root"], operations_order=[1, 0])
        groups = derive_duplicate_group_ids([first, second])
        self.assertEqual(groups["pair-a"], groups["pair-b"])

    def test_distinct_semantics_in_distinct_sessions_get_distinct_groups(self):
        first = self._inventory("pair-a", "session-a", "train", base_id="base-a",
                                values=["hello", "world"], op_ids=["a", "b"],
                                anchors=["$root", "base-a"])
        second = self._inventory("pair-b", "session-b", "train", base_id="base-b",
                                 values=["hello", "unrelated"], op_ids=["c", "d"],
                                 anchors=["$root", "base-b"])
        groups = derive_duplicate_group_ids([first, second])
        self.assertNotEqual(groups["pair-a"], groups["pair-b"])

    def test_identical_duplicate_component_crossing_partitions_fails_closed(self):
        train = self._inventory("pair-a", "session-a", "train", base_id="base-a",
                                values=["hello", "world"], op_ids=["a", "b"],
                                anchors=["$root", "base-a"])
        holdout = self._inventory("pair-b", "session-b", "holdout", base_id="base-b",
                                  values=["HELLO", "world"], op_ids=["c", "d"],
                                  anchors=["$root", "base-b"])
        with self.assertRaisesRegex(ValueError, "duplicate group crosses partitions"):
            derive_duplicate_group_ids([train, holdout])

    def test_duplicate_fingerprint_and_projection_reject_non_spec_model_and_non_pair_counts(self):
        valid = adapt(records(), source_kind="synthetic", family_id="family-a", partition="train")
        pair_ids = [pair["pairId"] for pair in valid["pairs"]]
        invalid_cases = []
        wrong_model = copy.deepcopy(valid)
        wrong_model["pairs"][0]["request"]["model"] = "arbitrary-model"
        invalid_cases.append(wrong_model)
        for count in (3, 4):
            wrong_count = copy.deepcopy(valid)
            operations = wrong_count["pairs"][0]["request"]["operations"]
            wrong_count["pairs"][0]["request"]["operations"] = [
                *operations, *copy.deepcopy(operations[:count - 2])]
            invalid_cases.append(wrong_count)

        for inventory in invalid_cases:
            with self.subTest(model=inventory["pairs"][0]["request"]["model"],
                              operation_count=len(inventory["pairs"][0]["request"]["operations"])):
                with self.assertRaises(ValueError):
                    derive_duplicate_group_ids([inventory])
                with self.assertRaises(ValueError):
                    project_trainer_rows(
                        [inventory], training_labels={pair_id: 0 for pair_id in pair_ids},
                        calibration_labels={}, duplicate_group_ids={})

    def test_pairs_are_exhaustive_deterministic_and_oriented_by_event_order(self):
        source = records()
        first = adapt(source, source_kind="synthetic", family_id="family-a", partition="train")
        second = adapt(copy.deepcopy(source), source_kind="synthetic", family_id="family-a", partition="train")
        self.assertEqual(first, second)
        self.assertEqual(len(first["pairs"]), 3)
        self.assertTrue(all("excludedReason" not in pair for pair in first["pairs"]))
        self.assertEqual(first["pairs"][0]["request"]["operations"][0]["id"], "op-0")
        self.assertEqual(first["pairs"][0]["request"]["operations"][1]["id"], "op-1")
        orientation = first["pairs"][0]["orientation"]
        self.assertEqual(orientation["method"], "source-event-sequence-provisional-v1")
        self.assertLess(orientation["firstSequence"], orientation["secondSequence"])
        self.assertFalse(orientation["sameEventTie"])
        self.assertFalse(orientation["sameTimestamp"])
        self.assertFalse(orientation["annotatorVisible"])

    def test_each_pair_freezes_its_own_second_proposal_cutoff_and_complete_prefix(self):
        first_session = records(session_id="prior-session")
        second_session = records(session_id="session-a", start_sequence=len(first_session),
                                 previous_hash=first_session[-1]["eventHash"], prefix="next-")
        source = first_session + second_session
        inventory = adapt(source, source_kind="synthetic", family_id="family-a",
                          partition="train")
        proposals = [event for event in second_session if event["kind"] == "proposal"]
        pairs = inventory["pairs"][3:]
        expected = [(proposals[1]["sequence"], 14),
                    (proposals[2]["sequence"], 15),
                    (proposals[2]["sequence"], 15)]
        self.assertEqual([pair["cutoff"]["sequence"] for pair in pairs],
                         [cutoff for cutoff, _ in expected])
        for pair, (cutoff_sequence, prefix_count) in zip(pairs, expected):
            prefix = [event for event in source if event["sequence"] <= cutoff_sequence]
            self.assertEqual(pair["cutoff"]["sourcePrefixEventCount"], prefix_count)
            self.assertEqual(
                pair["cutoff"]["sourcePrefixCommitment"],
                _hash([event["eventHash"] for event in prefix]),
            )
            self.assertFalse(pair["cutoff"]["annotatorVisible"])
            self.assertNotIn("sessionCommitments", pair["cutoff"])
            self.assertNotIn("auditOnlySessionCommitments", pair["cutoff"])
            self.assertGreater(second_session[-1]["sequence"], cutoff_sequence)

    def test_pair_identity_is_scoped_to_window_and_family(self):
        source = records()
        family_a = adapt(source, source_kind="synthetic", family_id="family-a", partition="train")
        family_b = adapt(source, source_kind="synthetic", family_id="family-b", partition="holdout")
        window_b = adapt(source, source_kind="synthetic", family_id="family-a", partition="train",
                         window_metadata={"format": "m35-source-window-v1", "sourceKind": "synthetic",
                                          "windowId": "window-b", "familyId": "family-a",
                                          "startUtc": "2026-10-01T00:00:00Z",
                                          "endUtc": "2026-10-15T00:00:00Z",
                                          "registrationRunId": None, "protocolCommit": "a" * 40})
        ids_a = {item["pairId"] for item in family_a["pairs"]}
        ids_b = {item["pairId"] for item in family_b["pairs"]}
        ids_window_b = {item["pairId"] for item in window_b["pairs"]}
        self.assertTrue(ids_a.isdisjoint(ids_b))
        self.assertTrue(ids_a.isdisjoint(ids_window_b))

    def test_session_groups_are_stable_across_windows_without_exposing_session_id(self):
        window_a = adapt(records(session_id="shared-session", value_prefix="window a"),
                         source_kind="synthetic", family_id="family-a", partition="train")
        window_b = adapt(
            records(session_id="shared-session", value_prefix="window b"),
            source_kind="synthetic", family_id="family-a", partition="train",
            window_metadata={"format": "m35-source-window-v1", "sourceKind": "synthetic",
                             "windowId": "window-b", "familyId": "family-a",
                             "startUtc": "2026-10-01T00:00:00Z",
                             "endUtc": "2026-10-15T00:00:00Z",
                             "registrationRunId": None, "protocolCommit": "a" * 40})
        all_pairs = window_a["pairs"] + window_b["pairs"]
        self.assertTrue({pair["pairId"] for pair in window_a["pairs"]}.isdisjoint(
            pair["pairId"] for pair in window_b["pairs"]))
        self.assertEqual({pair["sessionId"] for pair in all_pairs},
                         {window_a["pairs"][0]["sessionId"]})
        groups = derive_duplicate_group_ids([window_a, window_b])
        self.assertEqual(len(set(groups.values())), 1)
        self.assertNotIn("shared-session", str(all_pairs))

    def test_equal_timestamps_keep_sequence_orientation_without_claiming_event_tie(self):
        inventory = adapt(records(same_timestamp=True), source_kind="synthetic",
                          family_id="family-a", partition="train")
        orientation = inventory["pairs"][0]["orientation"]
        self.assertTrue(orientation["sameTimestamp"])
        self.assertFalse(orientation["sameEventTie"])
        self.assertLess(orientation["firstSequence"], orientation["secondSequence"])

    def test_projection_connects_adapted_inventories_to_synthetic_trainer_without_holdout_labels(self):
        inventories = [
            adapt(records(session_id="train-session", value_prefix="train example"), source_kind="synthetic",
                  family_id="train-family", partition="train"),
            adapt(records(session_id="cal-session", value_prefix="cal example"), source_kind="synthetic",
                  family_id="cal-family", partition="calibration"),
            adapt(records(session_id="holdout-session", value_prefix="holdout example"), source_kind="synthetic",
                  family_id="holdout-family", partition="holdout"),
        ]
        train_ids = [item["pairId"] for item in inventories[0]["pairs"]]
        calibration_ids = [item["pairId"] for item in inventories[1]["pairs"]]
        duplicate_groups = derive_duplicate_group_ids(inventories)
        rows = project_trainer_rows(
            inventories,
            training_labels={train_ids[0]: 0, train_ids[1]: 1, train_ids[2]: None},
            calibration_labels={calibration_ids[0]: 1, calibration_ids[1]: 0,
                                calibration_ids[2]: None},
            duplicate_group_ids=duplicate_groups,
        )
        self.assertEqual(len(rows), 9)
        self.assertTrue(all(row["label"] is None for row in rows if row["partition"] == "holdout"))
        artifact = fit(rows, model_id="adapted-synthetic", dataset_kind="synthetic")
        self.assertFalse(artifact["coverageReceipt"]["satisfiesRealReadiness"])

        leaked_groups = dict(duplicate_groups)
        leaked_groups[next(item["pairId"] for item in inventories[2]["pairs"])] = \
            leaked_groups[train_ids[0]]
        with self.assertRaisesRegex(ValueError, "invalid event records or adapter input"):
            project_trainer_rows(
                inventories,
                training_labels={train_ids[0]: 0, train_ids[1]: 1, train_ids[2]: None},
                calibration_labels={calibration_ids[0]: 1, calibration_ids[1]: 0,
                                    calibration_ids[2]: None},
                duplicate_group_ids=leaked_groups,
            )
        self.assertTrue(all(pair["featureVector"]["version"] == FEATURE_VERSION
                            for inventory in inventories for pair in inventory["pairs"]
                            if "featureVector" in pair))

    def test_projection_rejects_pair_family_forgery_before_it_can_mask_partition_leakage(self):
        inventories = [
            adapt(records(session_id="train-session", value_prefix="train example"), source_kind="synthetic",
                  family_id="shared-family", partition="train"),
            adapt(records(session_id="cal-session", value_prefix="cal example"), source_kind="synthetic",
                  family_id="calibration-family", partition="calibration"),
            adapt(records(session_id="holdout-session", value_prefix="holdout example"), source_kind="synthetic",
                  family_id="shared-family", partition="holdout"),
        ]
        train_ids = [item["pairId"] for item in inventories[0]["pairs"]]
        calibration_ids = [item["pairId"] for item in inventories[1]["pairs"]]
        duplicate_groups = derive_duplicate_group_ids(inventories)
        labels = {
            "training_labels": {train_ids[0]: 0, train_ids[1]: 1, train_ids[2]: None},
            "calibration_labels": {calibration_ids[0]: 1, calibration_ids[1]: 0,
                                   calibration_ids[2]: None},
            "duplicate_group_ids": duplicate_groups,
        }

        rows = project_trainer_rows(inventories, **labels)
        with self.assertRaisesRegex(ValueError, "family crosses partitions"):
            fit(rows, model_id="adapted-synthetic", dataset_kind="synthetic")

        forged = copy.deepcopy(inventories)
        forged[2]["pairs"][0]["familyId"] = "forged-holdout-family"
        forged[2]["pairs"][1]["familyId"] = "forged-holdout-family"
        forged[2]["pairs"][2]["familyId"] = "forged-holdout-family"
        with self.assertRaisesRegex(ValueError, "invalid event records or adapter input"):
            project_trainer_rows(forged, **labels)

    def test_global_sequence_accepts_multiple_sessions_and_enumerates_all_pairs_once(self):
        first = records()
        second = records(session_id="session-b", start_sequence=len(first),
                         previous_hash=first[-1]["eventHash"], prefix="second-")
        result = adapt(first + second, source_kind="synthetic", family_id="family-a", partition="train")
        self.assertEqual(len(result["pairs"]), 6)
        self.assertEqual(len({pair["pairId"] for pair in result["pairs"]}), 6)
        self.assertEqual(len(result["auditOnlySessionCommitments"]), 2)

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

    def test_missing_source_provenance_is_excluded_like_canonical_window_audit(self):
        cases = []
        missing_open_source = records()
        del missing_open_source[0]["data"]["sourceRef"]
        cases.append((missing_open_source, 3))
        missing_context_hash = records()
        del missing_context_hash[0]["data"]["contextSha"]
        cases.append((missing_context_hash, 3))
        missing_proposal_source = records()
        del missing_proposal_source[4]["data"]["sourceRef"]
        cases.append((missing_proposal_source, 2))

        for source, expected_exclusions in cases:
            previous = None
            for event in source:
                event["previousHash"] = previous
                body = {key: value for key, value in event.items() if key != "eventHash"}
                event["eventHash"] = _hash(body)
                previous = event["eventHash"]
            result = adapt(source, source_kind="synthetic", family_id="family-a",
                           partition="train")
            self.assertEqual(len(result["pairs"]), 3)
            excluded = [pair for pair in result["pairs"]
                        if pair.get("excludedReason") == "missing-provenance"]
            self.assertEqual(len(excluded), expected_exclusions)
            self.assertTrue(all("request" not in pair for pair in excluded))

    def test_primary_exclusion_reason_matches_canonical_order(self):
        source = records(missing_receipt=True, dependent=True)
        previous = None
        for event in source:
            event["previousHash"] = previous
            body = {key: value for key, value in event.items() if key != "eventHash"}
            event["eventHash"] = _hash(body)
            previous = event["eventHash"]
        result = adapt(source, source_kind="synthetic", family_id="family-a",
                       partition="train")
        counts = {reason: sum(pair.get("excludedReason") == reason for pair in result["pairs"])
                  for reason in ("dependent-observation", "missing-receipt")}
        self.assertEqual(counts, {"dependent-observation": 2, "missing-receipt": 1})

    def test_base_over_canonical_size_limit_is_excluded(self):
        source = records()
        source[0]["data"]["base"].extend(
            {"id": f"extra-{index}", "value": f"extra value {index}"}
            for index in range(3))
        previous = None
        for event in source:
            event["previousHash"] = previous
            body = {key: value for key, value in event.items() if key != "eventHash"}
            event["eventHash"] = _hash(body)
            previous = event["eventHash"]
        result = adapt(source, source_kind="synthetic", family_id="family-a",
                       partition="train")
        self.assertEqual(len(result["pairs"]), 3)
        self.assertTrue(all(pair.get("excludedReason") == "invalid-base"
                            for pair in result["pairs"]))

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

    def test_unreviewed_resolution_before_second_proposal_fails_closed(self):
        events = records()
        second_proposal_index = next(
            index for index, event in enumerate(events)
            if event["kind"] == "proposal" and event["data"]["actorId"] == "actor-b"
        )
        resolution = {
            "format": EVENT_FORMAT,
            "sequence": second_proposal_index,
            "eventId": "resolution-before-second-proposal",
            "timestampUtc": "2026-10-01T00:00:04Z",
            "kind": "proposal-resolved",
            "sessionId": "session-a",
            "data": {"proposalEventId": events[second_proposal_index - 1]["eventId"],
                     "outcome": "accepted"},
            "previousHash": None,
            "eventHash": None,
        }
        events.insert(second_proposal_index, resolution)
        previous = None
        for sequence, event in enumerate(events):
            event["sequence"] = sequence
            event["timestampUtc"] = f"2026-10-01T00:00:{sequence:02d}Z"
            event["previousHash"] = previous
            body = {key: value for key, value in event.items() if key != "eventHash"}
            event["eventHash"] = _hash(body)
            previous = event["eventHash"]

        # Resolution events have no reviewed taxonomy or cutoff semantics yet.
        # Reject the whole feed; do not emit a pair as eligible.
        with self.assertRaisesRegex(ValueError, "invalid event records"):
            adapt(events, source_kind="synthetic", family_id="family-a", partition="train")

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
        from agent_braid.native_predictor_training import prepare_request
        result = adapt(records(), source_kind="synthetic", family_id="family-a", partition="train")
        for pair in result["pairs"]:
            self.assertEqual(pair["featureVector"],
                             prepare_request(pair["request"], source_kind="synthetic"))

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
