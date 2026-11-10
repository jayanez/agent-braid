# SPDX-License-Identifier: AGPL-3.0-only
"""Offline experience-curation controls; synthetic comparisons make no utility claim."""
from hashlib import sha256
import unittest

from agent_braid import harness_curation as cur
from agent_braid import harness_experience as exp
from agent_braid.system_one import digest


def h(name: str) -> str:
    return sha256(name.encode()).hexdigest()


APP = {"domain": "code-review", "sourceSha256": h("src"), "host": "host-a",
       "toolSetSha256": h("tools"), "policySha256": h("policy")}
VALIDATION = {"validator": "verify-v1", "evidenceSha256": h("validation-run"), "passed": True}
VALIDATORS = frozenset({"verify-v1", "verify-v2"})
TRUST = dict(trusted_producers=frozenset({"generator-v1"}), trusted_actors=frozenset({"founder"}))


def proposal(entry_id="e1", **over) -> dict:
    value = {"id": entry_id, "kind": "positive", "cue": "Large diffs split across files " + entry_id,
             "lesson": "Splitting review into per-file passes found more defects in this domain " + entry_id,
             "applicability": dict(APP),
             "provenance": {"producer": "generator-v1", "sourceRecordSha256": h("record-" + entry_id),
                            "generatedAt": 110},
             "evidence": [{"sha256": h("ev-" + entry_id), "observedAt": 100, "polarity": "supporting"}],
             "expiresAt": None, "revalidateAfter": None}
    value.update(over)
    return value


def decision(store, entry_id, at=130, actor="founder") -> dict:
    entry = store.get(entry_id)
    return {"format": exp.DECISION_FORMAT, "actor": {"kind": "human", "id": actor}, "entryId": entry_id,
            "contentSha256": entry.content_sha256, "decision": "approved",
            "evidenceSha256s": sorted(r["sha256"] for r in entry.data["evidence"]), "decidedAt": at,
            "rollbackTarget": "validated", "executionAuthorization": False}


def library(*ids, actor="founder", **over) -> exp.ExperienceStore:
    store = exp.ExperienceStore()
    for entry_id in ids:
        store = store.add(proposal(entry_id, **over), 110)
        store = store.validate(entry_id, {**VALIDATION, "evidenceSha256": h("val-" + entry_id)}, 120)
        store = store.activate(entry_id, decision(store, entry_id, actor=actor), 130)
    return store


def ctx(start=1000, **over) -> dict:
    return {"taskStartedAt": start, **APP, **over}


def reasons(result) -> dict:
    return dict(result.excluded)


class RetrievalTests(unittest.TestCase):
    def test_serves_active_in_scope_entries_with_provenance(self):
        result = cur.retrieve(library("e1"), ctx(), max_entries=4, max_bytes=4096, **TRUST)
        self.assertEqual([r["id"] for r in result.served], ["e1"])
        row = result.served[0]
        self.assertEqual(row["role"], "advisory-data")
        self.assertEqual(row["producer"], "generator-v1")
        self.assertEqual(row["supportingSha256s"], (h("ev-e1"),))
        self.assertEqual(row["contrarySha256s"], ())
        self.assertFalse(result.executionAuthorization)

    def test_unbounded_retrieval_is_refused_and_bound_is_enforced(self):
        store = library("e1", "e2", "e3")
        for bad in (0, -1, True, None, cur.MAX_SERVED + 1):
            with self.assertRaises(cur.CurationError):
                cur.retrieve(store, ctx(), max_entries=bad, max_bytes=4096, **TRUST)
        with self.assertRaises(cur.CurationError):
            cur.retrieve(store, ctx(), max_entries=2, max_bytes=cur.MAX_BYTES + 1, **TRUST)
        result = cur.retrieve(store, ctx(), max_entries=2, max_bytes=4096, **TRUST)
        self.assertEqual([r["id"] for r in result.served], ["e1", "e2"])
        self.assertEqual(reasons(result)["e3"], "over-budget")
        self.assertEqual(result.omitted[0]["id"], "e3")
        self.assertEqual(result.omitted[0]["contentSha256"], store.get("e3").content_sha256)

    def test_byte_budget_omits_whole_entries_and_never_truncates(self):
        store = library("e1", "e2")
        one = len(cur.canonical_row_bytes(cur.retrieve(store, ctx(), max_entries=1, max_bytes=4096,
                                                       **TRUST).served[0]))
        result = cur.retrieve(store, ctx(), max_entries=4, max_bytes=one, **TRUST)
        self.assertEqual([r["id"] for r in result.served], ["e1"])
        self.assertEqual(reasons(result)["e2"], "over-budget")
        self.assertEqual(result.served[0]["lesson"], store.get("e1").data["lesson"])

    def test_stale_entry_is_not_served(self):
        store = library("e1", revalidateAfter=50)
        self.assertEqual(len(cur.retrieve(store, ctx(160), max_entries=4, max_bytes=4096, **TRUST).served), 1)
        stale = cur.retrieve(store, ctx(171), max_entries=4, max_bytes=4096, **TRUST)
        self.assertEqual((stale.served, reasons(stale)), ((), {"e1": "stale-revalidation"}))

    def test_expired_entry_is_not_served(self):
        stale = cur.retrieve(library("e1", expiresAt=500), ctx(600), max_entries=4, max_bytes=4096, **TRUST)
        self.assertEqual(reasons(stale), {"e1": "expired"})

    def test_contradicted_entry_is_not_served_and_evidence_is_kept(self):
        store = library("e1").add_evidence(
            "e1", {"sha256": h("contra"), "observedAt": 140, "polarity": "contrary"}, 150)
        result = cur.retrieve(store, ctx(), max_entries=4, max_bytes=4096, **TRUST)
        self.assertEqual(reasons(result), {"e1": "contradicted"})
        self.assertIn(h("contra"), [r["sha256"] for r in store.get("e1").data["evidence"]])

    def test_conflicting_entries_are_both_withheld(self):
        store = library("e1", cue="Split large diffs", kind="positive")
        other = proposal("e2", cue="Split large diffs", kind="negative")
        store = store.add(other, 110).validate("e2", {**VALIDATION, "evidenceSha256": h("v2")}, 120)
        store = store.activate("e2", decision(store, "e2"), 130)
        result = cur.retrieve(store, ctx(), max_entries=4, max_bytes=4096, **TRUST)
        self.assertEqual((result.served, reasons(result)),
                         ((), {"e1": "entry-conflict", "e2": "entry-conflict"}))

    def test_exact_duplicates_keep_lowest_id(self):
        store = library("e1", "e2", cue="Same cue", lesson="Same lesson text")
        result = cur.retrieve(store, ctx(), max_entries=4, max_bytes=4096, **TRUST)
        self.assertEqual([r["id"] for r in result.served], ["e1"])
        self.assertEqual(reasons(result), {"e2": "duplicate"})

    def test_forged_provenance_is_excluded_by_trust_registry(self):
        forged = library("e1", actor="attacker")
        result = cur.retrieve(forged, ctx(), max_entries=4, max_bytes=4096, **TRUST)
        self.assertEqual(reasons(result), {"e1": "untrusted-provenance"})
        producer = library("e1")
        result = cur.retrieve(producer, ctx(), max_entries=4, max_bytes=4096,
                              trusted_producers=frozenset({"other"}), trusted_actors=frozenset({"founder"}))
        self.assertEqual(reasons(result), {"e1": "untrusted-provenance"})

    def test_empty_or_malformed_trust_registry_refuses(self):
        for bad in (frozenset(), {"founder"}, None):
            with self.assertRaises(cur.CurationError):
                cur.retrieve(library("e1"), ctx(), max_entries=4, max_bytes=4096,
                             trusted_producers=bad, trusted_actors=frozenset({"founder"}))

    def test_non_store_is_refused(self):
        with self.assertRaises(cur.CurationError):
            cur.retrieve(object(), ctx(), max_entries=4, max_bytes=4096, **TRUST)

    def test_future_entries_are_hidden_from_earlier_tasks(self):
        result = cur.retrieve(library("e1"), ctx(130), max_entries=4, max_bytes=4096, **TRUST)
        self.assertEqual(reasons(result), {"e1": "future-state"})

    def test_compact_reduces_without_rewriting(self):
        store = library("e1", "e2", "e3")
        full = cur.retrieve(store, ctx(), max_entries=4, max_bytes=4096, **TRUST)
        small = cur.compact(full, max_entries=1, max_bytes=4096)
        self.assertEqual([r["id"] for r in small.served], ["e1"])
        self.assertEqual(small.served[0], full.served[0])
        self.assertEqual({o["id"] for o in small.omitted}, {"e2", "e3"})
        with self.assertRaises(cur.CurationError):
            cur.compact(small, max_entries=2, max_bytes=4096)  # cannot grow past what was retrieved
        with self.assertRaises(cur.CurationError):
            cur.compact(object(), max_entries=1, max_bytes=4096)


class DriftHardeningTests(unittest.TestCase):
    def test_cue_conflict_survives_case_and_whitespace_variants(self):
        store = library("e1", cue="Split large diffs", kind="positive")
        store = store.add(proposal("e2", cue="split  LARGE diffs", kind="negative"), 110)
        store = store.validate("e2", {**VALIDATION, "evidenceSha256": h("v2")}, 120)
        store = store.activate("e2", decision(store, "e2"), 130)
        result = cur.retrieve(store, ctx(), max_entries=4, max_bytes=4096, **TRUST)
        self.assertEqual(result.served, ())

    def test_revoked_ledger_blocks_late_entries_citing_revoked_hashes(self):
        late = library("e9", evidence=[{"sha256": h("ev-e1"), "observedAt": 100, "polarity": "supporting"}])
        result = cur.retrieve(late, ctx(), max_entries=4, max_bytes=4096, **TRUST,
                              revoked_sha256s=frozenset({h("ev-e1")}))
        self.assertEqual(reasons(result), {"e9": "revoked-lineage"})
        with self.assertRaises(cur.CurationError) as ctxm:
            cur.retrieve(late, ctx(), max_entries=4, max_bytes=4096, **TRUST, revoked_sha256s={h("x")})
        self.assertEqual(ctxm.exception.reason, "invalid-revoked")

    def test_untrusted_validator_and_invalid_time_refuse_revalidation(self):
        store = cur.curate(library("e1", revalidateAfter=50), 200).store
        for at, validators, reason in ((210, frozenset({"someone-else"}), "untrusted-validator"),
                                       (-1, VALIDATORS, "invalid-time")):
            with self.assertRaises(cur.CurationError) as c:
                cur.revalidate(store, "e1", {**VALIDATION, "evidenceSha256": h("r1")}, at,
                               trusted_validators=validators)
            self.assertEqual(c.exception.reason, reason)

    def test_compact_refuses_hand_built_rows(self):
        forged = cur.Retrieval(({"id": "zz"},), (), (), 4, 4096)
        with self.assertRaises(cur.CurationError) as c:
            cur.compact(forged, max_entries=1, max_bytes=4096)
        self.assertEqual(c.exception.reason, "invalid-retrieval")

    def test_greedy_fit_skips_an_oversized_row_and_serves_a_later_smaller_one(self):
        store = library("e1", "e2")
        store = store.add(proposal("e3", lesson="Short note"), 110)
        store = store.validate("e3", {**VALIDATION, "evidenceSha256": h("v3")}, 120)
        store = store.activate("e3", decision(store, "e3"), 130)
        sizes = {r["id"]: len(cur.canonical_row_bytes(r)) for r in
                 cur.retrieve(store, ctx(), max_entries=4, max_bytes=4096, **TRUST).served}
        limit = sizes["e1"] + sizes["e3"]
        result = cur.retrieve(store, ctx(), max_entries=4, max_bytes=limit, **TRUST)
        self.assertEqual([r["id"] for r in result.served], ["e1", "e3"])
        self.assertEqual(reasons(result), {"e2": "over-budget"})

    def test_retrieval_digest_is_deterministic_and_content_bound(self):
        a = cur.retrieve(library("e1"), ctx(), max_entries=4, max_bytes=4096, **TRUST)
        b = cur.retrieve(library("e1"), ctx(), max_entries=4, max_bytes=4096, **TRUST)
        c = cur.retrieve(library("e2"), ctx(), max_entries=4, max_bytes=4096, **TRUST)
        self.assertEqual(a.sha256, b.sha256)
        self.assertNotEqual(a.sha256, c.sha256)

    def test_family_check_is_case_insensitive_and_families_must_be_unique(self):
        t = CompareTests()
        with self.assertRaises(cur.CurationError) as c:
            t.run_compare(families=("FAM-B",))
        self.assertEqual(c.exception.reason, "family-leak")
        with self.assertRaises(cur.CurationError) as c:
            t.run_compare(families=("fam-a", "fam-a"))
        self.assertEqual(c.exception.reason, "invalid-families")

    def test_contrary_only_citation_is_not_revoked_and_results_carry_no_authority(self):
        store = library("e1").add_evidence(
            "e1", {"sha256": h("contra"), "observedAt": 140, "polarity": "contrary"}, 150)
        out = cur.propagate_revocation(store, [h("contra")], 300, "x")
        self.assertEqual(out.revoked, ())
        self.assertFalse(out.executionAuthorization)
        self.assertFalse(cur.curate(store, 200).executionAuthorization)


class CurateTests(unittest.TestCase):
    def test_expired_entries_become_terminal(self):
        out = cur.curate(library("e1", expiresAt=500), 600)
        self.assertEqual(out.store.get("e1").state, "expired")
        self.assertEqual(out.actions, (("e1", "expired"),))

    def test_stale_active_entry_is_withdrawn_to_validated(self):
        out = cur.curate(library("e1", revalidateAfter=50), 200)
        self.assertEqual(out.store.get("e1").state, "validated")
        self.assertEqual(out.actions, (("e1", "withdrawn-stale"),))
        self.assertEqual(out.needs_revalidation, ("e1",))
        with self.assertRaises(exp.ExperienceError):  # stale validated entry cannot be re-activated
            out.store.activate("e1", decision(out.store, "e1", at=200), 200)

    def test_contradicted_active_entry_is_withdrawn_and_never_reactivated(self):
        store = library("e1").add_evidence(
            "e1", {"sha256": h("contra"), "observedAt": 140, "polarity": "contrary"}, 150)
        out = cur.curate(store, 160)
        self.assertEqual(out.store.get("e1").state, "validated")
        self.assertEqual(out.actions, (("e1", "withdrawn-contradicted"),))
        with self.assertRaises(exp.ExperienceError):
            out.store.activate("e1", decision(out.store, "e1", at=170), 170)
        self.assertEqual(out.store.get("e1").data["evidence"], store.get("e1").data["evidence"])

    def test_clean_store_is_unchanged(self):
        store = library("e1")
        out = cur.curate(store, 200)
        self.assertEqual((out.store.sha256, out.actions), (store.sha256, ()))

    def test_conflicts_are_reported_not_mutated(self):
        store = library("e1", cue="Split large diffs", kind="positive")
        store = store.add(proposal("e2", cue="Split large diffs", kind="negative"), 110)
        store = store.validate("e2", {**VALIDATION, "evidenceSha256": h("v2")}, 120)
        store = store.activate("e2", decision(store, "e2"), 130)
        out = cur.curate(store, 200)
        self.assertEqual(out.conflicts, (("e1", "e2"),))
        self.assertEqual(out.store.sha256, store.sha256)

    def test_quarantined_entry_with_contradiction_is_never_promoted(self):
        store = exp.ExperienceStore().add(proposal("e1"), 110).add_evidence(
            "e1", {"sha256": h("contra"), "observedAt": 111, "polarity": "contrary"}, 112)
        out = cur.curate(store, 200)
        self.assertEqual(out.store.get("e1").state, "quarantined")
        self.assertEqual(out.actions, ())

    def test_invalid_inputs_refuse(self):
        with self.assertRaises(cur.CurationError):
            cur.curate(object(), 10)
        with self.assertRaises(cur.CurationError):
            cur.curate(library("e1"), -1)


class RevalidateTests(unittest.TestCase):
    def test_revalidation_refreshes_staleness_but_needs_independent_run(self):
        store = cur.curate(library("e1", revalidateAfter=50), 200).store
        fresh = cur.revalidate(store, "e1", {**VALIDATION, "evidenceSha256": h("r1")}, 210, trusted_validators=VALIDATORS)
        self.assertEqual(fresh.get("e1").data["validatedAt"], 210)
        with self.assertRaises(exp.ExperienceError):
            cur.revalidate(store, "e1", {"validator": "generator-v1", "evidenceSha256": h("r2"),
                                         "passed": True}, 210, trusted_validators=frozenset({"generator-v1"}))

    def test_revalidation_does_not_activate(self):
        store = cur.curate(library("e1", revalidateAfter=50), 200).store
        fresh = cur.revalidate(store, "e1", {**VALIDATION, "evidenceSha256": h("r1")}, 210, trusted_validators=VALIDATORS)
        self.assertEqual(fresh.get("e1").state, "validated")

    def test_contradicted_or_expired_entries_cannot_be_revalidated(self):
        store = library("e1").add_evidence(
            "e1", {"sha256": h("contra"), "observedAt": 140, "polarity": "contrary"}, 150)
        with self.assertRaises(cur.CurationError):
            cur.revalidate(store, "e1", {**VALIDATION, "evidenceSha256": h("r1")}, 160, trusted_validators=VALIDATORS)
        store = library("e1", expiresAt=500)
        with self.assertRaises(cur.CurationError):
            cur.revalidate(store, "e1", {**VALIDATION, "evidenceSha256": h("r1")}, 500, trusted_validators=VALIDATORS)


class RevocationTests(unittest.TestCase):
    def test_revoking_evidence_propagates_to_dependents(self):
        store = library("e1", "e2")
        # e3 is derived from e1: it cites e1's content hash as supporting evidence.
        derived = proposal("e3", evidence=[{"sha256": store.get("e1").content_sha256, "observedAt": 100,
                                            "polarity": "supporting"}])
        store = store.add(derived, 110).validate("e3", {**VALIDATION, "evidenceSha256": h("v3")}, 120)
        store = store.activate("e3", decision(store, "e3"), 130)
        out = cur.propagate_revocation(store, [h("ev-e1")], 300, "source-withdrawn")
        self.assertEqual(sorted(out.revoked), ["e1", "e3"])
        self.assertEqual(out.store.get("e2").state, "active")
        for gone in ("e1", "e3"):
            self.assertEqual(out.store.get(gone).state, "revoked")
        result = cur.retrieve(out.store, ctx(400), max_entries=4, max_bytes=4096, **TRUST)
        self.assertEqual([r["id"] for r in result.served], ["e2"])

    def test_derivation_through_source_record_is_followed_transitively(self):
        store = library("e1")
        e2 = proposal("e2")
        e2["provenance"]["sourceRecordSha256"] = store.get("e1").sha256
        store = store.add(e2, 110)
        e3 = proposal("e3")
        e3["provenance"]["sourceRecordSha256"] = store.get("e2").content_sha256
        store = store.add(e3, 110)
        out = cur.propagate_revocation(store, [h("ev-e1")], 300, "source-withdrawn")
        self.assertEqual(sorted(out.revoked), ["e1", "e2", "e3"])

    def test_unrelated_entries_and_terminal_entries_are_untouched(self):
        store = library("e1", "e2").revoke("e2", 200, "manual")
        out = cur.propagate_revocation(store, [h("nothing")], 300, "x")
        self.assertEqual((out.revoked, out.store.sha256), ((), store.sha256))
        out = cur.propagate_revocation(store, [h("ev-e2")], 300, "x")
        self.assertEqual(out.revoked, ())

    def test_invalid_hash_or_reason_refuses(self):
        store = library("e1")
        with self.assertRaises(cur.CurationError):
            cur.propagate_revocation(store, ["nothex"], 300, "x")
        with self.assertRaises(cur.CurationError):
            cur.propagate_revocation(store, [], 300, "x")
        with self.assertRaises(cur.CurationError):
            cur.propagate_revocation(store, [h("ev-e1")], 300, "bad reason!")


class CompareTests(unittest.TestCase):
    def tasks(self):
        return [{"id": "t1", "family": "fam-b", "startedAt": 1000, "heldOut": True, "context": ctx(1000)},
                {"id": "t2", "family": "fam-c", "startedAt": 1100, "heldOut": True, "context": ctx(1100)}]

    def outcomes(self, **over):
        value = {"t1": {"no-library": {"passed": True, "cost": 10},
                        "library-uncurated": {"passed": False, "cost": 14},
                        "library-curated": {"passed": True, "cost": 12}},
                 "t2": {"no-library": {"passed": False, "cost": 10},
                        "library-uncurated": {"passed": True, "cost": 14},
                        "library-curated": {"passed": True, "cost": 11}}}
        value.update(over)
        return value

    def run_compare(self, store=None, tasks=None, outcomes=None, families=("fam-a",)):
        return cur.compare_variants(store or library("e1"), tasks or self.tasks(),
                                    outcomes or self.outcomes(), library_families=families,
                                    outcomes_source="synthetic", max_entries=4, max_bytes=4096, **TRUST)

    def test_report_keeps_negative_results_and_costs_and_claims_no_utility(self):
        report = self.run_compare()
        self.assertFalse(report["utilityClaim"])
        self.assertEqual(report["scope"], "synthetic-offline-control")
        self.assertFalse(report["executionAuthorization"])
        arms = report["arms"]
        self.assertEqual(arms["library-uncurated"]["failures"], ["t1"])
        self.assertEqual(arms["no-library"]["failures"], ["t2"])
        self.assertEqual(arms["library-uncurated"]["totalCost"], 28)
        self.assertEqual(arms["library-curated"]["totalCost"], 23)
        self.assertEqual(report["negativeTransfer"]["library-uncurated"], ["t1"])
        self.assertEqual(report["negativeTransfer"]["library-curated"], [])
        self.assertNotIn("winner", report)
        self.assertEqual(report["tasks"][0]["servedIds"]["library-curated"], ["e1"])
        self.assertEqual(report["tasks"][0]["servedIds"]["no-library"], [])

    def test_report_is_deterministic_and_digest_bound(self):
        a, b = self.run_compare(), self.run_compare()
        self.assertEqual(a, b)
        self.assertEqual(a["sha256"], digest({k: v for k, v in a.items() if k != "sha256"}))

    def test_heldout_family_must_not_overlap_library_families(self):
        with self.assertRaises(cur.CurationError):
            self.run_compare(families=("fam-b",))

    def test_tasks_must_be_held_out_after_the_library_and_time_ordered(self):
        late = self.tasks()
        late[0]["startedAt"] = 100
        late[0]["context"] = ctx(100)
        with self.assertRaises(cur.CurationError):
            self.run_compare(tasks=late)
        swapped = list(reversed(self.tasks()))
        with self.assertRaises(cur.CurationError):
            self.run_compare(tasks=swapped)
        notheld = self.tasks()
        notheld[0]["heldOut"] = False
        with self.assertRaises(cur.CurationError):
            self.run_compare(tasks=notheld)
        mismatch = self.tasks()
        mismatch[0]["context"] = ctx(1)
        with self.assertRaises(cur.CurationError):
            self.run_compare(tasks=mismatch)

    def test_dropped_arm_or_task_outcomes_refuse(self):
        outs = self.outcomes()
        del outs["t1"]["library-uncurated"]
        with self.assertRaises(cur.CurationError):
            self.run_compare(outcomes=outs)
        outs = self.outcomes()
        del outs["t2"]
        with self.assertRaises(cur.CurationError):
            self.run_compare(outcomes=outs)
        extra = self.outcomes(t9={})
        with self.assertRaises(cur.CurationError):
            self.run_compare(outcomes=extra)

    def test_outcomes_must_be_declared_synthetic_and_well_typed(self):
        with self.assertRaises(cur.CurationError):
            cur.compare_variants(library("e1"), self.tasks(), self.outcomes(), library_families=("fam-a",),
                                 outcomes_source="measured", max_entries=4, max_bytes=4096, **TRUST)
        bad = self.outcomes()
        bad["t1"]["no-library"] = {"passed": "yes", "cost": 10}
        with self.assertRaises(cur.CurationError):
            self.run_compare(outcomes=bad)
        bad = self.outcomes()
        bad["t1"]["no-library"] = {"passed": True, "cost": -1}
        with self.assertRaises(cur.CurationError):
            self.run_compare(outcomes=bad)

    def test_uncurated_arm_serves_a_cue_conflict_that_curated_arm_withholds(self):
        store = library("e1", cue="Split large diffs", kind="positive")
        store = store.add(proposal("e2", cue="Split large diffs", kind="negative"), 110)
        store = store.validate("e2", {**VALIDATION, "evidenceSha256": h("v2")}, 120)
        store = store.activate("e2", decision(store, "e2"), 130)
        report = self.run_compare(store=store)
        served = report["tasks"][0]["servedIds"]
        self.assertEqual(served["library-uncurated"], ["e1", "e2"])
        self.assertEqual(served["library-curated"], [])

    def test_oversized_task_lists_refuse(self):
        many = [{"id": f"t{i}", "family": "fam-b", "startedAt": 1000 + i, "heldOut": True,
                 "context": ctx(1000 + i)} for i in range(cur.MAX_TASKS + 1)]
        with self.assertRaises(cur.CurationError):
            self.run_compare(tasks=many, outcomes={})


if __name__ == "__main__":
    unittest.main()
