# SPDX-License-Identifier: AGPL-3.0-only
"""Offline verifier and adjudication controls; deterministic doubles only, no host or model."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import unittest
from unittest import mock

from agent_braid import harness_verification as ver
from agent_braid.harness_host_codex import OutcomeVerifier, VerifierRequest
from agent_braid.system_one import canonical, freeze

from tests.test_harness_observation import MANIFEST, NOW, events, observe

SOURCE = "5" * 64
RUBRIC = "7" * 64
RATIONALE = "8" * 64
CANDIDATE = "c" * 64
REFERENCE_OBS = "d" * 64
EXPECTED = {"out/result.txt": b"expected answer: forty-two exactly\n"}
SERIAL = {"a.txt": b"serial a contents, version two\n", "b.txt": b"serial b contents\n"}


def completed_observation(after, before=None):
    return observe(before={} if before is None else before, after=after)


def fixture_unit(partition="discovery", human_required=False, **over):
    args = dict(unit_id="unit-1", partition=partition, source_sha256=SOURCE, rubric_sha256=RUBRIC,
                oracles=(ver.FixtureOracle(EXPECTED),), human_required=human_required)
    args.update(over)
    return ver.Unit(**args)


def commit(unit, outputs, *, observation=None, candidate=CANDIDATE):
    if observation is None and outputs is not None:
        observation = completed_observation(outputs)
    return ver.commit(unit, candidate_sha256=candidate, observation=observation,
                      outputs=outputs, now=NOW)


def human(unit, commitment, annotator, verdict, **over):
    args = dict(annotator=annotator, verdict=verdict, blind=True, rubric_sha256=RUBRIC)
    args.update(over)
    return ver.human_label(unit, commitment, **args)


def adjudicate(unit, commitment, labels, adjudicator="adj-1", verdict="fail"):
    return ver.adjudication(unit, commitment, adjudicator=adjudicator, verdict=verdict,
                            rationale_sha256=RATIONALE, labels=labels)


def forged(record, **changes):
    return ver.VerificationRecord(freeze({**record.to_dict(), **changes}))


def reasons(data):
    return [m["reason"] for m in data["missingLabels"]]


class RefusalCase(unittest.TestCase):
    def refused(self, reason, fn, *args, **kwargs):
        with self.assertRaises(ver.VerificationError) as ctx:
            fn(*args, **kwargs)
        self.assertEqual(ctx.exception.reason, reason)


class OracleTests(RefusalCase):
    def request(self, artifacts):
        return VerifierRequest("attempt-1", MANIFEST, "e" * 64, artifacts)

    def test_fixture_oracle_checks_expected_outputs_only(self):
        oracle = ver.FixtureOracle(EXPECTED)
        self.assertIsInstance(oracle, OutcomeVerifier)  # reuses the SPEC-048 handoff type
        self.assertEqual(oracle.verify(self.request({**EXPECTED, "notes.md": b"x"})), "pass")
        self.assertEqual(oracle.verify(self.request({"out/result.txt": b"wrong\n"})), "fail")
        self.assertEqual(oracle.verify(self.request({})), "fail")

    def test_serial_reference_requires_identical_writes(self):
        oracle = ver.SerialReferenceOracle(SERIAL, reference_observation_sha256=REFERENCE_OBS)
        self.assertEqual(oracle.verify(self.request(dict(SERIAL))), "pass")
        self.assertEqual(oracle.verify(self.request({**SERIAL, "extra.txt": b"x"})), "fail")
        self.assertEqual(oracle.verify(self.request({"a.txt": SERIAL["a.txt"]})), "fail")
        self.assertEqual(oracle.verify(self.request({**SERIAL, "b.txt": b"other"})), "fail")

    def test_oracle_identity_binds_material_and_kind(self):
        a, b = ver.FixtureOracle(EXPECTED), ver.FixtureOracle(EXPECTED)
        self.assertEqual(a.sha256, b.sha256)
        self.assertNotEqual(a.sha256, ver.FixtureOracle({"out/result.txt": b"other"}).sha256)
        serial = ver.SerialReferenceOracle(EXPECTED, reference_observation_sha256=REFERENCE_OBS)
        self.assertNotEqual(a.sha256, serial.sha256)
        self.assertNotEqual(serial.sha256, ver.SerialReferenceOracle(
            EXPECTED, reference_observation_sha256="f" * 64).sha256)

    def test_grader_material_is_not_rendered(self):
        oracle = ver.FixtureOracle(EXPECTED)
        for text in (repr(oracle), str(oracle), repr(fixture_unit())):
            self.assertNotIn("forty-two", text)

    def test_material_is_copied_and_malformed_material_refused(self):
        material = dict(EXPECTED)
        oracle = ver.FixtureOracle(material)
        material["out/result.txt"] = b"mutated"
        self.assertEqual(oracle.verify(self.request(dict(EXPECTED))), "pass")
        for bad in ({}, {"/abs": b"x"}, {"../up": b"x"}, {"a": "text"}, [("a", b"x")]):
            self.refused("invalid-grader-material", ver.FixtureOracle, bad)
        self.refused("invalid-grader-material", ver.SerialReferenceOracle, SERIAL,
                     reference_observation_sha256="nothex")

    def test_malformed_requests_are_inconclusive(self):
        oracle = ver.FixtureOracle(EXPECTED)
        self.assertEqual(oracle.verify("not a request"), "inconclusive")
        self.assertEqual(oracle.verify(self.request([("out/result.txt", b"x")])), "inconclusive")


class UnitTests(RefusalCase):
    def test_unit_is_immutable_and_strict(self):
        unit = fixture_unit()
        with self.assertRaises(FrozenInstanceError):
            unit.partition = "holdout"
        bad = [dict(partition="training"), dict(unit_id="../x"), dict(source_sha256="x"),
               dict(rubric_sha256="X" * 64), dict(oracles=[ver.FixtureOracle(EXPECTED)]),
               dict(human_required=1)]
        for over in bad:
            with self.assertRaises(ver.VerificationError, msg=over):
                fixture_unit(**over)
        self.refused("no-label-source", fixture_unit, oracles=(), human_required=False)

    def test_only_deterministic_oracles_are_oracles(self):
        class ModelJudge(OutcomeVerifier):
            sha256 = "9" * 64

            def verify(self, request):
                return "pass"

        class Sub(ver.FixtureOracle):
            pass

        for oracle in (ModelJudge(), Sub(EXPECTED)):
            self.refused("not-deterministic-oracle", fixture_unit, oracles=(oracle,))
        self.refused("duplicate-oracle", fixture_unit,
                     oracles=(ver.FixtureOracle(EXPECTED), ver.FixtureOracle(EXPECTED)))


class CommitTests(RefusalCase):
    def test_commitment_binds_candidate_source_observation_and_output_hashes(self):
        unit = fixture_unit()
        observation = completed_observation(EXPECTED)
        record = commit(unit, EXPECTED, observation=observation)
        data = record.to_dict()
        self.assertEqual(data["format"], ver.COMMITMENT_FORMAT)
        self.assertEqual((data["unitId"], data["unitSha256"], data["sourceSha256"],
                          data["candidateSha256"]), ("unit-1", unit.sha256, SOURCE, CANDIDATE))
        self.assertEqual(data["observationSha256"], observation.sha256)
        self.assertEqual(data["manifestSha256"], MANIFEST)
        self.assertEqual(data["terminal"], "completed")
        self.assertEqual(data["outputs"], {"out/result.txt": sha256(EXPECTED["out/result.txt"]).hexdigest()})
        self.assertFalse(data["executionAuthorization"])
        self.assertEqual(record.sha256, sha256(canonical(data)).hexdigest())
        self.assertNotIn("forty-two", repr(record))

    def test_record_hash_follows_its_data(self):
        record = commit(fixture_unit(), EXPECTED)
        self.assertNotEqual(forged(record, candidateSha256="b" * 64).sha256, record.sha256)
        self.assertEqual(record.canonical_bytes, canonical(record.to_dict()))

    def test_failed_refused_and_unstarted_attempts_commit_no_outputs(self):
        unit = fixture_unit()
        for terminal in ("failed", "refused", "interrupted"):
            record = commit(unit, None, observation=observe(events(terminal=terminal)))
            self.assertEqual(record.to_dict()["terminal"], terminal)
            self.assertIsNone(record.to_dict()["outputs"])
        unstarted = commit(unit, None, observation=None).to_dict()
        self.assertEqual(unstarted["terminal"], "unobserved")
        self.assertIsNone(unstarted["observationSha256"])

    def test_outputs_require_a_completed_observation(self):
        unit = fixture_unit()
        self.refused("outputs-without-completion", commit, unit, EXPECTED,
                     observation=observe(events(terminal="failed")))
        self.refused("completion-without-outputs", commit, unit, None,
                     observation=completed_observation(EXPECTED))
        self.refused("outputs-without-completion", ver.commit, unit, candidate_sha256=CANDIDATE,
                     observation=None, outputs=EXPECTED, now=NOW)

    def test_outputs_must_be_exactly_the_observed_writes(self):
        unit = fixture_unit()
        observations = (
            completed_observation({"out/result.txt": b"what actually happened\n"}),
            completed_observation({}, before={"out/result.txt": b"old"}),  # deleted
            completed_observation({"notes.md": b"x"}),  # expected file never written
            observe(),  # completed, but no artifacts observed
        )
        for observation in observations:
            self.refused("output-observation-mismatch", commit, unit, EXPECTED,
                         observation=observation)
        self.refused("output-observation-mismatch", commit, unit, {**EXPECTED, "notes.md": b"x"},
                     observation=completed_observation(EXPECTED))
        unchanged = completed_observation({**EXPECTED, "keep.txt": b"same"},
                                          before={"keep.txt": b"same"})
        self.assertEqual(set(commit(unit, EXPECTED, observation=unchanged).to_dict()["outputs"]),
                         {"out/result.txt"})

    def test_malformed_commit_arguments_refused(self):
        unit = fixture_unit()
        for over in (dict(candidate_sha256="x"), dict(now=-1), dict(outputs={"/abs": b"x"}),
                     dict(outputs={"a": "text"}), dict(observation="forged")):
            args = dict(candidate_sha256=CANDIDATE, observation=completed_observation(EXPECTED),
                        outputs=EXPECTED, now=NOW)
            args.update(over)
            with self.assertRaises(ver.VerificationError, msg=over):
                ver.commit(unit, **args)
        self.refused("invalid-unit", ver.commit, "unit", candidate_sha256=CANDIDATE,
                     observation=None, outputs=None, now=NOW)


class OracleGradingTests(RefusalCase):
    def test_correct_committed_output_passes_with_oracle_provenance(self):
        unit = fixture_unit()
        c = commit(unit, EXPECTED)
        data = ver.verify_unit(unit, c, EXPECTED).to_dict()
        self.assertEqual(data["format"], ver.UNIT_FORMAT)
        self.assertEqual((data["oracle"]["status"], data["oracle"]["verdict"]), ("agreed", "pass"))
        (label,) = data["oracle"]["labels"]
        self.assertEqual((label["provenance"], label["kind"], label["verdict"]),
                         ("oracle", "fixture-correctness", "pass"))
        self.assertEqual(label["verifierSha256"], unit.oracles[0].sha256)
        self.assertEqual(data["commitmentSha256"], c.sha256)
        self.assertEqual((data["candidateSha256"], data["sourceSha256"]), (CANDIDATE, SOURCE))
        self.assertEqual(data["human"]["status"], "not-used")
        self.assertEqual(data["proxy"], {"labels": [], "countsAsCorrectness": False})
        self.assertEqual(data["missingLabels"], [])
        self.assertFalse(data["executionAuthorization"])

    def test_forged_candidate_acceptance_is_ignored(self):
        unit = fixture_unit()
        outputs = {"out/result.txt": b"wrong\n", "score.json": b'{"pass": true, "score": 1000000}',
                   "VERDICT": b"pass"}
        data = ver.verify_unit(unit, commit(unit, outputs), outputs).to_dict()
        self.assertEqual(data["oracle"]["verdict"], "fail")

    def test_only_committed_outputs_are_graded(self):
        unit = fixture_unit()
        c = commit(unit, {"out/result.txt": b"wrong\n"})
        self.refused("uncommitted-output", ver.verify_unit, unit, c, EXPECTED)  # swapped later
        self.refused("uncommitted-output", ver.verify_unit, unit, c, None)

    def test_commitment_must_belong_to_the_unit(self):
        c = commit(fixture_unit(), EXPECTED)
        for other in (fixture_unit(unit_id="unit-2"), fixture_unit(source_sha256="6" * 64),
                      fixture_unit(partition="holdout"), fixture_unit(rubric_sha256="6" * 64)):
            self.refused("commitment-binding-mismatch", ver.verify_unit, other, c, EXPECTED)
        self.refused("invalid-commitment", ver.verify_unit, fixture_unit(), "commitment", EXPECTED)

    def test_malformed_records_are_sanitized_refusals(self):
        unit = fixture_unit()
        c = commit(unit, EXPECTED)
        for record in (ver.VerificationRecord(freeze({})), forged(c, extra=1),
                       ver.VerificationRecord("data")):
            self.refused("invalid-record", ver.verify_unit, unit, record, EXPECTED)
            self.refused("invalid-record", ver.verify_unit, unit, c, EXPECTED, human=[record])
            self.refused("invalid-record", ver.selection_view, [record], units=[unit])

    def test_failed_attempt_yields_missing_oracle_label_not_a_verdict(self):
        unit = fixture_unit()
        c = commit(unit, None, observation=observe(events(terminal="refused")))
        data = ver.verify_unit(unit, c, None).to_dict()
        self.assertEqual(data["terminal"], "refused")
        self.assertEqual(data["oracle"]["status"], "missing")
        self.assertIsNone(data["oracle"]["verdict"])
        self.assertEqual(data["missingLabels"], [
            {"source": "oracle", "kind": "fixture-correctness", "reason": "no-committed-output"}])

    def test_oracle_disagreement_is_recorded_without_verdict(self):
        both = fixture_unit(oracles=(ver.FixtureOracle(EXPECTED), ver.SerialReferenceOracle(
            SERIAL, reference_observation_sha256=REFERENCE_OBS)))
        data = ver.verify_unit(both, commit(both, EXPECTED), EXPECTED).to_dict()
        self.assertEqual(data["oracle"]["status"], "disagreement")
        self.assertIsNone(data["oracle"]["verdict"])
        self.assertEqual([l["verdict"] for l in data["oracle"]["labels"]], ["pass", "fail"])

    def test_raising_or_unknown_oracle_result_is_a_missing_label(self):
        unit = fixture_unit()
        c = commit(unit, EXPECTED)
        for kwargs in ({"side_effect": RuntimeError("boom")}, {"return_value": "maybe"}):
            with mock.patch.object(ver.FixtureOracle, "verify", **kwargs):
                data = ver.verify_unit(unit, c, EXPECTED).to_dict()
            self.assertEqual(data["oracle"]["status"], "missing")
            self.assertIsNone(data["oracle"]["verdict"])
            self.assertEqual(reasons(data), ["oracle-inconclusive"])

    def test_human_only_unit_reports_oracle_not_used(self):
        unit = fixture_unit(oracles=(), human_required=True)
        c = commit(unit, EXPECTED)
        labels = [human(unit, c, "ann-1", "pass"), human(unit, c, "ann-2", "pass")]
        data = ver.verify_unit(unit, c, EXPECTED, human=labels).to_dict()
        self.assertEqual(data["oracle"], {"status": "not-used", "verdict": None, "labels": []})
        self.assertEqual(data["missingLabels"], [])
        self.assertFalse(data["crossProvenanceDisagreement"])


class HumanAdjudicationTests(RefusalCase):
    def setUp(self):
        self.unit = fixture_unit(partition="holdout", human_required=True)
        self.c = commit(self.unit, EXPECTED)

    def label(self, annotator, verdict, **over):
        return human(self.unit, self.c, annotator, verdict, **over)

    def verify(self, human=(), adjudications=(), proxies=()):
        return ver.verify_unit(self.unit, self.c, EXPECTED, human=human, proxies=proxies,
                               adjudications=adjudications).to_dict()

    def test_two_blind_annotators_agreeing(self):
        data = self.verify([self.label("ann-1", "pass"), self.label("ann-2", "pass")])
        self.assertEqual((data["human"]["status"], data["human"]["verdict"]), ("agreed", "pass"))
        self.assertTrue(all(l["provenance"] == "human" and l["blind"] for l in data["human"]["labels"]))
        self.assertEqual(data["missingLabels"], [])

    def test_fewer_than_two_annotators_is_missing_not_a_verdict(self):
        for labels in ([], [self.label("ann-1", "pass")],
                       [self.label("ann-1", "pass"), self.label("ann-2", "abstain")]):
            data = self.verify(labels)
            self.assertEqual(data["human"]["status"], "insufficient-annotators")
            self.assertIsNone(data["human"]["verdict"])
            self.assertIn("insufficient-annotators", reasons(data))

    def test_abstention_is_recorded_as_missing_label(self):
        data = self.verify([self.label("ann-1", "pass"), self.label("ann-2", "pass"),
                            self.label("ann-3", "abstain")])
        self.assertEqual(data["human"]["status"], "agreed")
        self.assertIn({"source": "human", "annotator": "ann-3", "reason": "abstained"},
                      data["missingLabels"])

    def test_disagreement_without_adjudication_stays_unresolved(self):
        labels = [self.label("ann-1", "pass"), self.label("ann-2", "pass"), self.label("ann-3", "fail")]
        data = self.verify(labels)  # a 2-1 majority is not a consensus
        self.assertEqual(data["human"]["status"], "unresolved-disagreement")
        self.assertIsNone(data["human"]["verdict"])
        self.assertEqual(data["human"]["disagreement"], {"pass": ["ann-1", "ann-2"], "fail": ["ann-3"]})
        self.assertIn("unresolved-disagreement", reasons(data))

    def test_actual_adjudication_resolves_and_keeps_the_disagreement(self):
        labels = [self.label("ann-1", "pass"), self.label("ann-2", "fail")]
        record = adjudicate(self.unit, self.c, labels)
        data = self.verify(labels, [record])
        self.assertEqual((data["human"]["status"], data["human"]["verdict"]), ("adjudicated", "fail"))
        self.assertEqual(data["human"]["adjudicationSha256"], record.sha256)
        self.assertEqual(data["human"]["disagreement"], {"pass": ["ann-1"], "fail": ["ann-2"]})
        self.assertEqual(data["missingLabels"], [])

    def test_adjudication_over_labels_including_an_abstention(self):
        labels = [self.label("ann-1", "pass"), self.label("ann-2", "fail"),
                  self.label("ann-3", "abstain")]
        data = self.verify(labels, [adjudicate(self.unit, self.c, labels, verdict="pass")])
        self.assertEqual((data["human"]["status"], data["human"]["verdict"]), ("adjudicated", "pass"))
        self.assertEqual(reasons(data), ["abstained"])

    def test_adjudication_must_be_independent_complete_and_needed(self):
        labels = [self.label("ann-1", "pass"), self.label("ann-2", "fail")]
        self.refused("adjudicator-not-independent", adjudicate, self.unit, self.c, labels,
                     adjudicator="ann-1")
        self.refused("adjudication-incomplete", self.verify, labels,
                     [adjudicate(self.unit, self.c, labels[:1])])
        agreeing = [labels[0], self.label("ann-3", "pass")]
        self.refused("adjudication-without-disagreement", self.verify, agreeing,
                     [adjudicate(self.unit, self.c, agreeing)])
        full = adjudicate(self.unit, self.c, labels)
        self.refused("multiple-adjudications", self.verify, labels, [full, full])
        self.refused("adjudicator-not-independent", self.verify, labels,
                     [forged(full, adjudicator="ann-2")])
        self.refused("invalid-adjudication", adjudicate, self.unit, self.c, labels, verdict="abstain")
        self.refused("invalid-adjudication", self.verify, labels, [labels[0]])

    def test_adjudication_bound_to_another_commitment_refused(self):
        other = commit(self.unit, EXPECTED, candidate="b" * 64)
        stray = adjudicate(self.unit, other, [human(self.unit, other, "ann-1", "pass"),
                                              human(self.unit, other, "ann-2", "fail")])
        labels = [self.label("ann-1", "pass"), self.label("ann-2", "fail")]
        self.refused("label-binding-mismatch", self.verify, labels, [stray])

    def test_adjudication_on_unit_without_human_labels_refused(self):
        unit = fixture_unit()
        c = commit(unit, EXPECTED)
        record = adjudicate(unit, c, [human(unit, c, "ann-1", "pass"), human(unit, c, "ann-2", "fail")])
        self.refused("adjudication-without-disagreement", ver.verify_unit, unit, c, EXPECTED,
                     adjudications=[record])

    def test_unblinded_duplicate_drifted_or_excess_human_labels_refused(self):
        self.refused("unblinded-annotator", self.label, "ann-1", "pass", blind=False)
        self.refused("rubric-drift", self.label, "ann-1", "pass", rubric_sha256="6" * 64)
        self.refused("invalid-label", self.label, "ann-1", "maybe")
        self.refused("duplicate-annotator", self.verify,
                     [self.label("ann-1", "pass"), self.label("ann-1", "fail")])
        many = [self.label(f"ann-{i}", "pass") for i in range(ver.MAX_LABELS + 1)]
        self.refused("invalid-label", self.verify, many)

    def test_labels_bound_to_another_commitment_or_provenance_refused(self):
        other = commit(self.unit, EXPECTED, candidate="b" * 64)
        stray = human(self.unit, other, "ann-1", "pass")
        self.refused("label-binding-mismatch", self.verify, [stray, self.label("ann-2", "pass")])
        proxy = ver.proxy_label(self.unit, self.c, model="judge-1", score_micros=900_000)
        self.refused("wrong-provenance", self.verify, [proxy])

    def test_human_and_oracle_disagreement_is_cross_provenance_record(self):
        data = self.verify([self.label("ann-1", "fail"), self.label("ann-2", "fail")])
        self.assertEqual((data["oracle"]["verdict"], data["human"]["verdict"]), ("pass", "fail"))
        self.assertTrue(data["crossProvenanceDisagreement"])
        self.assertNotIn("verdict", data)  # no blended consensus field

    def test_failures_are_still_annotated(self):
        failed = commit(self.unit, None, observation=observe(events(terminal="failed")))
        labels = [human(self.unit, failed, "ann-1", "fail"), human(self.unit, failed, "ann-2", "fail")]
        data = ver.verify_unit(self.unit, failed, None, human=labels).to_dict()
        self.assertEqual(data["human"]["verdict"], "fail")
        self.assertEqual(data["oracle"]["status"], "missing")


class ProxyTests(RefusalCase):
    def test_proxy_scores_are_labeled_and_never_correctness(self):
        unit = fixture_unit()
        wrong = {"out/result.txt": b"wrong\n"}
        c = commit(unit, wrong)
        proxy = ver.proxy_label(unit, c, model="judge-1", score_micros=1_000_000)
        data = ver.verify_unit(unit, c, wrong, proxies=[proxy]).to_dict()
        self.assertEqual(data["oracle"]["verdict"], "fail")
        self.assertFalse(data["proxy"]["countsAsCorrectness"])
        (label,) = data["proxy"]["labels"]
        self.assertEqual((label["provenance"], label["model"], label["scoreMicros"]),
                         ("proxy", "judge-1", 1_000_000))
        self.assertIs(label["countsAsCorrectness"], False)
        self.assertNotIn("verdict", label)
        for bad in (-1, 1_000_001, True, 0.5):
            with self.assertRaises(ver.VerificationError, msg=bad):
                ver.proxy_label(unit, c, model="judge-1", score_micros=bad)
        self.refused("wrong-provenance", ver.verify_unit, unit, c, wrong,
                     proxies=[human(unit, c, "ann-1", "pass")])


class HoldoutSealTests(RefusalCase):
    def test_holdout_verdicts_never_reach_selection(self):
        disc, hold = fixture_unit(), fixture_unit(unit_id="unit-2", partition="holdout")
        units = [disc, hold]
        d = ver.verify_unit(disc, commit(disc, EXPECTED), EXPECTED)
        hc = commit(hold, EXPECTED)
        h = ver.verify_unit(hold, hc, EXPECTED)
        self.assertEqual(ver.selection_view([d], units=units), (d,))
        for records in ([d, h], [hc], [human(hold, hc, "ann-1", "pass")],
                        [forged(h, partition="discovery")]):
            self.refused("holdout-sealed", ver.selection_view, records, units=units)
        self.refused("holdout-sealed", ver.selection_view, [d], units=[hold])  # unregistered
        self.refused("invalid-record", ver.selection_view, ["forged"], units=units)
        self.refused("invalid-unit", ver.selection_view, [d], units=["unit-1"])

    def test_holdout_grader_material_refused_in_solver_context(self):
        hold = fixture_unit(partition="holdout")
        material = EXPECTED["out/result.txt"]
        ver.check_context({"task.md": b"visible acceptance: write out/result.txt"}, [hold])
        leaks = ({"ctx": b"hint: " + material + b" ok"},
                 {"ctx": hold.oracles[0].sha256.encode()},
                 {"ctx": hold.oracles[0].sha256.upper().encode()},
                 {"ctx": sha256(material).hexdigest().encode()},
                 {hold.oracles[0].sha256: b""})
        for context in leaks:
            self.refused("grader-material-in-context", ver.check_context, context, [hold])

    def test_serial_reference_identity_is_sealed(self):
        hold = fixture_unit(partition="holdout", oracles=(ver.SerialReferenceOracle(
            SERIAL, reference_observation_sha256=REFERENCE_OBS),))
        self.refused("grader-material-in-context", ver.check_context,
                     {"ctx": REFERENCE_OBS.encode()}, [hold])

    def test_short_material_matches_whole_values_only(self):
        hold = fixture_unit(partition="holdout", oracles=(ver.FixtureOracle({"n": b"42"}),))
        ver.check_context({"ctx": b"the answer is near 420"}, [hold])
        self.refused("grader-material-in-context", ver.check_context, {"ctx": b"42"}, [hold])

    def test_discovery_material_stays_visible_and_bad_context_refused(self):
        ver.check_context({"ctx": EXPECTED["out/result.txt"]}, [fixture_unit()])
        for context in ({"ctx": "text"}, ["bytes"]):
            self.refused("invalid-context", ver.check_context, context, [fixture_unit()])
        self.refused("invalid-unit", ver.check_context, {}, ["unit"])


if __name__ == "__main__":
    unittest.main()
