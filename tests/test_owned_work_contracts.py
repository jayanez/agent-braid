# SPDX-License-Identifier: AGPL-3.0-only
"""Pure synthetic state-machine controls, not observed development episodes."""
import ast
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from agent_braid.owned_work_authority import OwnedWorkError, canonical_bytes, digest
from agent_braid.owned_work_contracts import (
    AttemptRegistration, DiagnosticAttestation, FrozenRegistration, OracleAttestation,
    ValidatedState, event_schema, parse_event, span_union_ns, validate_append,
)
from tests.test_owned_work_authority import D, NOW, authority_fixture


def seal(event):
    event["recordDigest"] = digest({k: v for k, v in event.items() if k != "recordDigest"})
    return canonical_bytes(event)


def fixtures():
    _, authority, registry = authority_fixture()
    pins = dict(sourceRevision="1"*40, sourceState="clean", dirtyDiffDigest=None,
                configDigest=D("3"), policyDigest=D("4"), toolchainDigest=D("5"), modelDigest=None)
    cap = dict(name="native-stdio-containment", status="not-probed", availableAtNs=None,
               evidenceDigest=None, reason="not-probed")
    attempt = AttemptRegistration("1"*32, "2"*32, "3"*32, "evaluation", "4"*32,
                                  canonical_bytes(pins), canonical_bytes({"capabilities": [cap]}))
    oracle = OracleAttestation(attempt.attempt_id, D("6"), attempt.clock_domain_id,
                               110, 150, 160, 170, 0)
    registration = FrozenRegistration(D("a"), D("b"), canonical_bytes({
        "featureAllowlistDigest": D("e"), "oracleContractDigest": D("f"), "splitProtocolDigest": D("1")}),
        D("7"), D("8"), D("9"), (attempt,), (oracle,), method_digests=frozenset({D("0")}))
    event = dict(schema="agent-braid-owned-work-evaluation/v1", kind="origin",
                 sourceKind="owned-deterministic-development", sequence=0, attemptId=attempt.attempt_id,
                 taskId=attempt.task_id, familyId=attempt.family_id, authorityDigest=digest(json.loads(authority)),
                 **pins, recordedAtUTC=NOW, previousRecordDigest=None, supersedesRecordDigest=None,
                 executionAuthorization=False, trainingAdmission=False, collector047Projection="none")
    event["payload"] = dict(clockDomainId=attempt.clock_domain_id, originNs=100, cutoffNs=100,
        lotDigest=D("7"), populationDigest=D("8"), partitionDigest=D("9"), familyPartition="evaluation",
        features=[dict(name="operation_count", unit="count", value=2, missingReason=None, scope="attempt",
                       eventNs=90, availableAtNs=95)], capabilities=[cap], condition="unknown",
        recommendation="not-produced", recommendationArtifactDigest=None, chosenAction="not-yet-chosen",
        forecast=dict(status="produced", target="validation_wall_ns", horizonNs=100, point=50,
                      lower=30, upper=70, unit="ns", methodDigest=D("0"), missingReason=None))
    seal(event)
    return authority, registry, registration, event


def outcome(origin, *, sequence=1, previous=None):
    event = {k: v for k, v in origin.items() if k != "payload"}
    event.update(kind="outcome", sequence=sequence,
                 previousRecordDigest=origin["recordDigest"] if previous is None else previous,
                 supersedesRecordDigest=None)
    event["payload"] = dict(originRecordDigest=origin["recordDigest"], clockDomainId="4"*32,
        chosenAction="serial-development", workflowTerminal="completed", productDisposition="answered",
        verificationDisposition="verified", terminalNs=150, availableAtNs=160, maturityNs=170,
        labelState="mature", metrics=[dict(name="validation_wall_ns", unit="ns", value=40,
                                         missingReason=None, scope="validation-process")],
        oracle=dict(status="verified", contractDigest=D("f"), artifactDigest=D("6"),
                    check="validation-command-terminal-and-bound-log", semanticCorrectness="unknown",
                    humanLabel="unknown"),
        censoring=dict(state="not-censored", reason=None, observedUntilNs=170),
        diagnosis=dict(claimLevel="unknown", layer="unknown", causeCode="unassigned",
                       evidenceDigest=None, boundedDiagnosticAnnexDigest=None), spans=[], amendmentReason="initial")
    seal(event)
    return event


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.authority, self.registry, self.registration, self.origin = fixtures()

    def append(self, event, state=ValidatedState(), **changes):
        args = dict(authority=self.authority, registry=self.registry,
                    registration=self.registration, now_utc=NOW, state=state)
        args.update(changes)
        return validate_append(seal(event), **args)

    def origin_state(self):
        return self.append(self.origin).state

    def reject(self, event, code=None, **changes):
        with self.assertRaisesRegex(OwnedWorkError, code or ".+"):
            self.append(event, **changes)

    def test_origin_outcome_full_chain_and_eligible_target(self):
        first = self.append(self.origin)
        self.assertEqual(first.population_status, (("1"*32, "outcome-missing"),))
        result = self.append(outcome(self.origin), state=first.state)
        self.assertEqual(result.eligible_outcome_digests, (result.state.head_digest,))
        self.assertEqual(result.population_status, (("1"*32, "mature"),))
        self.assertFalse(result.execution_authorization)
        self.assertFalse(result.training_admission)
        self.assertEqual(len(first.state.records), 1)
        self.assertEqual(len(result.state.records), 2)
        with self.assertRaises(FrozenInstanceError): result.state.records = ()

    def test_duplicate_is_idempotent_but_conflicting_origin_refuses(self):
        state = self.origin_state()
        same = self.append(self.origin, state)
        self.assertTrue(same.duplicate); self.assertEqual(same.state, state)
        self.origin["sequence"] = 1; self.origin["previousRecordDigest"] = state.head_digest
        self.reject(self.origin, "conflicting-origin", state=state)

    def test_valid_correction_appends_without_overwriting(self):
        state = self.origin_state(); event = outcome(self.origin)
        prior = self.append(event, state).state
        event["sequence"] = 2
        event["previousRecordDigest"] = prior.head_digest
        event["supersedesRecordDigest"] = prior.head_digest
        event["payload"]["amendmentReason"] = "correction"
        result = self.append(event, prior)
        self.assertEqual(result.state.records[:2], prior.records)
        self.assertEqual(len(result.state.records), 3)
        self.assertEqual(result.eligible_outcome_digests, (result.state.head_digest,))

    def test_broken_chain_and_wrong_origin_or_supersession(self):
        state = self.origin_state()
        for field, value, code in [("sequence", 2, "record-chain"),
                                   ("previousRecordDigest", D("0"), "record-chain"),
                                   ("supersedesRecordDigest", D("0"), "outcome-supersession")]:
            event = outcome(self.origin); event[field] = value
            self.reject(event, code, state=state)
        event = outcome(self.origin); event["payload"]["originRecordDigest"] = D("0")
        self.reject(event, "origin-reference", state=state)

    def test_raw_event_schema_and_digest_are_required(self):
        raw = seal(self.origin)
        self.assertEqual(parse_event(raw), self.origin)
        with self.assertRaisesRegex(OwnedWorkError, "duplicate-key"):
            parse_event(raw.replace(b'"kind":"origin"', b'"kind":"origin","kind":"origin"'))
        self.origin["sequence"] = True
        self.reject(self.origin, "schema-type")
        self.origin["sequence"] = 0
        raw = seal(self.origin).replace(b'"originNs":100', b'"originNs":101')
        with self.assertRaisesRegex(OwnedWorkError, "record-digest"): parse_event(raw)

    def test_untrusted_history_is_revalidated(self):
        event = dict(self.origin); event["recordDigest"] = D("0")
        state = ValidatedState((canonical_bytes(event),))
        with self.assertRaises(OwnedWorkError): self.append(outcome(self.origin), state)
        for raw in (b'{}', b'not-json'):
            with self.subTest(raw=raw), self.assertRaises(OwnedWorkError):
                self.append(outcome(self.origin), ValidatedState((raw,)))

    def test_registered_source_and_population_not_just_regex(self):
        for key in ("sourceRevision", "configDigest", "policyDigest", "toolchainDigest", "authorityDigest"):
            event = json.loads(seal(self.origin)); event[key] = "f"*len(event[key])
            self.reject(event, "authority-binding" if key == "authorityDigest" else "source-pins")
        for key in ("lotDigest", "populationDigest", "partitionDigest", "familyPartition", "clockDomainId"):
            event = json.loads(seal(self.origin))
            event["payload"][key] = "development" if key == "familyPartition" else "f"*len(event["payload"][key])
            self.reject(event)
        self.origin["attemptId"] = "9"*32
        self.reject(self.origin, "unregistered-attempt")

    def test_family_and_task_partition_overlap_refuses_registration(self):
        a = self.registration.attempts[0]
        b = replace(a, attempt_id="9"*32, family_partition="development")
        with self.assertRaisesRegex(OwnedWorkError, "registration-partition"):
            replace(self.registration, attempts=(a, b))
        with self.assertRaisesRegex(OwnedWorkError, "registration-duplicate"):
            replace(self.registration, attempts=(a, a))

    def test_late_features_and_cutoff_cannot_be_backfilled(self):
        for key, value in [("eventNs", 96), ("availableAtNs", 101), ("scope", "validation-process")]:
            event = json.loads(seal(self.origin)); event["payload"]["features"][0][key] = value
            self.reject(event)
        self.origin["payload"]["cutoffNs"] = 101
        self.reject(self.origin, "origin-cutoff")

    def test_missing_features_remain_null_not_zero_or_available(self):
        feature = self.origin["payload"]["features"][0]
        feature.update(value=None, eventNs=None, availableAtNs=None, missingReason="not-measured")
        result = self.append(self.origin)
        self.assertIs(json.loads(result.state.records[0])["payload"]["features"][0]["value"], None)
        feature["availableAtNs"] = 95
        self.reject(self.origin)

    def test_duplicate_feature_capability_and_metric_names(self):
        for key in ("features", "capabilities"):
            event = json.loads(seal(self.origin)); event["payload"][key] *= 2
            self.reject(event, "duplicate-"+key.rstrip("s") if key == "features" else "duplicate-capability")
        state = self.origin_state(); event = outcome(self.origin); event["payload"]["metrics"] *= 2
        self.reject(event, "duplicate-metric", state=state)

    def test_capability_not_probed_is_not_available_by_declaration(self):
        self.origin["payload"]["capabilities"][0].update(status="available", reason="observed-pass",
                                                             availableAtNs=95, evidenceDigest=D("0"))
        self.reject(self.origin, "unobserved-capability")

    def test_registered_capability_requires_pre_t0_evidence(self):
        cap = self.origin["payload"]["capabilities"][0]
        cap.update(status="available", reason="observed-pass", availableAtNs=95, evidenceDigest=D("0"))
        a = replace(self.registration.attempts[0], capabilities=canonical_bytes({"capabilities": [cap]}))
        reg = replace(self.registration, attempts=(a,))
        self.append(self.origin, registration=reg)
        cap["availableAtNs"] = 101
        a = replace(a, capabilities=canonical_bytes({"capabilities": [cap]}))
        self.reject(self.origin, "future-capability", registration=replace(reg, attempts=(a,)))

    def test_intervals_methods_and_no_forecast_missingness(self):
        for changes in ({"lower": 51}, {"upper": 49}, {"lower": None}, {"methodDigest": D("a")}):
            event = json.loads(seal(self.origin)); event["payload"]["forecast"].update(changes)
            self.reject(event)
        self.origin["payload"]["forecast"].update(status="not-produced", horizonNs=None,
            point=None, lower=None, upper=None, methodDigest=None, missingReason="not-admitted")
        state = self.origin_state()
        result = self.append(outcome(self.origin), state)
        self.assertEqual(result.eligible_outcome_digests, ())
        self.origin["payload"]["forecast"]["point"] = 0
        self.reject(self.origin)

    def test_mature_requires_bound_oracle_same_clock_and_actual_target(self):
        state = self.origin_state()
        for changes in ({"clockDomainId": "f"*32}, {"terminalNs": 151}, {"maturityNs": 159}):
            event = outcome(self.origin); event["payload"].update(changes)
            self.reject(event, state=state)
        for key, value in [("status", "pending"), ("artifactDigest", D("a")),
                           ("semanticCorrectness", "correct"), ("humanLabel", "approved")]:
            event = outcome(self.origin); event["payload"]["oracle"][key] = value
            self.reject(event, state=state)
        event = outcome(self.origin); event["payload"]["metrics"][0]["value"] = 0
        self.reject(event, "mature-target", state=state)
        event = outcome(self.origin); event["payload"]["verificationDisposition"] = "unavailable"
        self.reject(event, "maturity-evidence", state=state)

    def test_censored_late_completion_remains_ineligible_after_amendment(self):
        state = self.origin_state()
        late_oracle = replace(self.registration.oracle_attestations[0], terminal_ns=250,
                              available_at_ns=260, maturity_ns=270)
        reg = replace(self.registration, oracle_attestations=(late_oracle,))
        event = outcome(self.origin)
        event["payload"].update(terminalNs=250, availableAtNs=260, maturityNs=270)
        event["payload"]["metrics"][0]["value"] = 140
        self.reject(event, "original-horizon-censored", state=state, registration=reg)
        event["payload"].update(labelState="censored",
            censoring=dict(state="right-censored", reason="censored", observedUntilNs=270))
        first = self.append(event, state, registration=reg)
        self.assertEqual(first.eligible_outcome_digests, ())
        event.update(sequence=2, previousRecordDigest=first.state.head_digest,
                     supersedesRecordDigest=first.state.head_digest)
        event["payload"]["amendmentReason"] = "late-maturity"
        second = self.append(event, first.state, registration=reg)
        self.assertEqual(second.eligible_outcome_digests, ())
        event["payload"].update(labelState="mature",
             censoring=dict(state="not-censored", reason=None, observedUntilNs=270))
        self.reject(event, "original-horizon-censored", state=first.state, registration=reg)

    def test_missing_refused_and_cancelled_are_retained_not_error_labels(self):
        state = self.origin_state()
        for terminal in ("missing", "refused", "cancelled", "abandoned", "not-selected", "error"):
            event = outcome(self.origin)
            event["payload"].update(workflowTerminal=terminal, productDisposition="unknown",
                verificationDisposition="unavailable", terminalNs=None, availableAtNs=None,
                maturityNs=None, labelState="censored",
                censoring=dict(state="missing-outcome", reason="unknown", observedUntilNs=190),
                oracle=dict(status="not-obtained", contractDigest=D("f"), artifactDigest=None,
                            check="validation-command-terminal-and-bound-log", semanticCorrectness="unknown",
                            humanLabel="unknown"))
            event["payload"]["metrics"][0].update(value=None, missingReason="censored")
            result = self.append(event, state)
            self.assertEqual(result.eligible_outcome_digests, ())
            self.assertEqual(json.loads(result.state.records[-1])["payload"]["workflowTerminal"], terminal)

    def test_supplied_population_preserves_missing_members_and_retries(self):
        a = self.registration.attempts[0]; b = replace(a, attempt_id="9"*32)
        reg = replace(self.registration, attempts=(a, b))
        result = self.append(self.origin, registration=reg)
        self.assertEqual(result.population_status, ((a.attempt_id,"outcome-missing"), (b.attempt_id,"origin-missing")))

    def test_diagnostic_symptom_cannot_be_promoted_to_observed_mechanism(self):
        state = self.origin_state(); event = outcome(self.origin)
        diagnosis = event["payload"]["diagnosis"]
        diagnosis.update(claimLevel="observed-mechanism", layer="infrastructure",
                         causeCode="os-exec-permission-denied", evidenceDigest=D("a"))
        self.reject(event, "unbound-diagnosis", state=state)
        evidence = DiagnosticAttestation("1"*32, D("a"), "infrastructure", "os-exec-permission-denied")
        self.append(event, state, registration=replace(self.registration, diagnostic_attestations=(evidence,)))
        diagnosis["boundedDiagnosticAnnexDigest"] = D("b")
        self.reject(event, "annex-not-admitted", state=state,
                    registration=replace(self.registration, diagnostic_attestations=(evidence,)))

    def test_raw_content_and_047_identity_projection_refuse(self):
        for key in ("stderr", "stdout", "PATH", "path", "secret", "prompt", "repository"):
            event = json.loads(seal(self.origin)); event[key] = "private body"
            self.reject(event, "schema-extra")
        for key,value in [("collector047Projection", "identity"), ("executionAuthorization",True),
                          ("trainingAdmission",True), ("schema","agent-braid-owned-work-evaluation/v2")]:
            event = json.loads(seal(self.origin)); event[key] = value
            self.reject(event)

    def test_expiry_revocation_and_caps_are_rechecked_even_for_duplicate(self):
        state = self.origin_state()
        self.reject(self.origin, "authority-revoked", state=state,
                    registry=replace(self.registry, revoked_ids=frozenset({"a"*32})))
        self.reject(self.origin, "authority-expired", state=state, now_utc="2030-01-02T00:00:00Z")
        body = json.loads(self.authority); body["caps"]["maxRecords"] = 1
        authority = canonical_bytes(body)
        registry = replace(self.registry, descriptors=(authority,))
        event = json.loads(seal(self.origin)); event["authorityDigest"] = digest(body)
        first = self.append(event, authority=authority, registry=registry)
        second = outcome(event)
        self.reject(second, "authority-cap", state=first.state, authority=authority, registry=registry)
        # An exact duplicate consumes neither a record nor an attempt.
        self.assertTrue(self.append(event, first.state, authority=authority, registry=registry).duplicate)

    def test_span_union_is_not_nested_sum_and_cycles_or_crossclock_refuse(self):
        def span(id, left, right, parent=None):
            return dict(spanId=id*32, parentSpanId=parent*32 if parent else None, clockDomainId="4"*32,
                        stage="validation", startedNs=left, finishedNs=right, status="complete", accounting="inclusive")
        rows = [span("1",100,150), span("2",110,140,"1"), span("3",145,160)]
        self.assertEqual(span_union_ns(tuple(rows),stage="validation",clock_domain_id="4"*32),60)
        rows[1]["parentSpanId"] = "2"*32
        with self.assertRaisesRegex(OwnedWorkError,"span-parent"):
            span_union_ns(tuple(rows),stage="validation",clock_domain_id="4"*32)
        rows[1]["parentSpanId"] = "1"*32; rows[1]["clockDomainId"] = "9"*32
        with self.assertRaisesRegex(OwnedWorkError,"span-clock"):
            span_union_ns(tuple(rows),stage="validation",clock_domain_id="4"*32)

    def test_schemas_are_identical_to_adopted_and_dev_validator_agrees(self):
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root/'specs/051-owned-work-evaluation/contracts/owned-work-evaluation.schema.json').read_text())
        self.assertEqual(event_schema(),schema)
        from jsonschema import Draft202012Validator, FormatChecker
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for event in (self.origin, outcome(self.origin)):
            validator.validate(event); parse_event(seal(event))
        for key,value in [("sequence",True),("executionAuthorization",0),("extra","body")]:
            event = json.loads(seal(self.origin)); event[key] = value
            self.assertTrue(list(validator.iter_errors(event)))
            self.reject(event)

    def test_modules_have_no_io_model_or_collector_imports_and_no_side_effects(self):
        root = Path(__file__).resolve().parents[1]
        allowed = {"__future__","dataclasses","datetime","hashlib","json","math","re","typing",
                   "agent_braid.owned_work_authority"}
        for name in ("owned_work_authority", "owned_work_contracts"):
            tree = ast.parse((root/f'agent_braid/{name}.py').read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    self.assertTrue(all(n.name in allowed for n in node.names))
                if isinstance(node,ast.ImportFrom): self.assertIn(node.module,allowed)
        with patch('builtins.open',side_effect=AssertionError("unexpected I/O")), \
             patch('subprocess.Popen',side_effect=AssertionError("unexpected child")):
            state = self.origin_state()
            self.append(outcome(self.origin),state)

    def test_bool_zero_wrong_units_and_partial_metrics_are_not_coerced(self):
        for change in ({"value":True}, {"unit":"ns"}, {"missingReason":"unknown"}):
            event = json.loads(seal(self.origin)); event["payload"]["features"][0].update(change)
            self.reject(event)
        event = outcome(self.origin); event["payload"]["metrics"][0]["unit"] = "ms"
        self.reject(event, state=self.origin_state())

    def test_verified_disposition_without_operational_oracle_refuses(self):
        event = outcome(self.origin)
        event["payload"].update(labelState="pending", terminalNs=None, availableAtNs=None, maturityNs=None)
        event["payload"]["oracle"].update(status="pending", artifactDigest=None)
        event["payload"]["metrics"][0].update(value=None, missingReason="not-measured")
        self.reject(event, "verification-evidence", state=self.origin_state())

    def test_horizon_overflow_and_premature_right_censor_refuse(self):
        event = json.loads(seal(self.origin)); event["payload"].update(originNs=2**63-1, cutoffNs=2**63-1)
        self.reject(event, "horizon-overflow")
        event = outcome(self.origin)
        event["payload"].update(labelState="censored", terminalNs=None, availableAtNs=None,
                               maturityNs=None, verificationDisposition="unavailable")
        event["payload"]["oracle"].update(status="not-obtained", artifactDigest=None)
        event["payload"]["metrics"][0].update(value=None, missingReason="censored")
        event["payload"]["censoring"].update(state="right-censored", reason="censored", observedUntilNs=199)
        self.reject(event,"censor-horizon",state=self.origin_state())

    def test_span_future_missing_parent_duplicate_and_partial_accounting(self):
        s=dict(spanId="7"*32,parentSpanId=None,clockDomainId="4"*32,stage="validation",
               startedNs=110,finishedNs=171,status="complete",accounting="inclusive")
        state=self.origin_state(); event=outcome(self.origin); event["payload"]["spans"]=[s]
        self.reject(event,"future-span",state=state)
        s["finishedNs"]=150; s["parentSpanId"]="8"*32
        self.reject(event,"span-parent",state=state)
        s["parentSpanId"]=None; event["payload"]["spans"]=[s,s]
        self.reject(event,"duplicate-span",state=state)
        s.update(status="interrupted",finishedNs=None)
        self.assertIsNone(span_union_ns((s,),stage="validation",clock_domain_id="4"*32))

    def test_correction_cannot_target_another_attempt(self):
        a=self.registration.attempts[0]; b=replace(a,attempt_id="9"*32)
        reg=replace(self.registration,attempts=(a,b))
        first=self.append(self.origin,registration=reg).state
        other=json.loads(seal(self.origin)); other.update(sequence=1,attemptId=b.attempt_id,
                                                         previousRecordDigest=first.head_digest)
        second=self.append(other,first,registration=reg).state
        event=outcome(self.origin,sequence=2,previous=second.head_digest)
        third=self.append(event,second,registration=reg).state
        other_outcome=outcome(other,sequence=3,previous=third.head_digest)
        other_outcome["supersedesRecordDigest"]=third.head_digest
        other_outcome["payload"]["amendmentReason"]="correction"
        self.reject(other_outcome,"outcome-supersession",state=third,registration=reg)

    def test_date_retention_and_future_dates_are_not_monotonic_times(self):
        self.origin["recordedAtUTC"]="2030-01-01T00:00:02Z"
        self.reject(self.origin,"record-date")
        self.origin["recordedAtUTC"]=NOW
        body=json.loads(self.authority)
        body.update(validUntilUTC="2030-01-10T00:00:00Z")
        body["caps"]["retentionUTCDates"]=1
        authority=canonical_bytes(body); self.origin["authorityDigest"]=digest(body)
        registry=replace(self.registry,descriptors=(authority,))
        self.reject(self.origin,"retention-expired",authority=authority,registry=registry,
                    now_utc="2030-01-02T00:00:00Z")

    def test_fixed_schema_interpreter_only_uses_supported_keywords(self):
        # Guard the interpreter boundary if future schemas evolve.
        allowed={"type","additionalProperties","required","properties","const","enum",
                 "pattern","format","anyOf","oneOf","allOf","if","then","else",
                 "minimum","maximum","maxItems","uniqueItems","items","$schema","$id",
                 "title","$defs","$ref"}
        def inspect(schema):
            self.assertTrue(set(schema)<=allowed,set(schema)-allowed)
            for key in ("properties","$defs"):
                for child in schema.get(key,{}).values(): inspect(child)
            for key in ("items","if","then","else"):
                if key in schema: inspect(schema[key])
            for key in ("anyOf","oneOf","allOf"):
                for child in schema.get(key,[]): inspect(child)
        from agent_braid.owned_work_authority import authority_schema
        inspect(event_schema()); inspect(authority_schema())
