# SPDX-License-Identifier: AGPL-3.0-only
"""Offline cost reconciliation controls; no host, model, paid route or economic acceptance."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
import unittest

from agent_braid import harness_costs as costs
from agent_braid.harness_admission import Reservation
from agent_braid.system_one import canonical


def h(name: str) -> str:
    return sha256(name.encode()).hexdigest()


def reservation(name: str, journal: int = 4096) -> Reservation:
    return Reservation(canonical({
        "format": "braid-harness-reservation/v0.1", "id": name, "admissionSha256": h("adm-" + name),
        "manifestSha256": h("manifest"), "envelopeSha256": h("envelope"), "reservedAt": 10,
        "expiresAt": 20, "reservedJournalBytes": journal, "executionAuthorization": False}))


def obs(value: int, unit: str, evidence: str = "ev") -> dict:
    return {"status": "observed", "value": value, "unit": unit, "evidenceSha256": h(evidence)}


def unknown(reason: str = "not-exported") -> dict:
    return {"status": "unknown", "reason": reason}


ZERO = {"cash": obs(0, "eur-cent", "invoice"), "quota": obs(0, "token"), "wall": obs(0, "ms"),
        "cpu": obs(0, "ms"), "rss": obs(0, "byte"), "disk": obs(0, "byte"),
        "journal": obs(0, "byte"), "processes": obs(0, "count"), "human": obs(0, "s")}


def measures(**over) -> dict:
    value = deepcopy(ZERO)
    value.update(over)
    return value


def entry(entry_id, phase, *, attempt=None, shared=None, rule="equal", **over) -> dict:
    value = {"id": entry_id, "phase": phase, "measures": measures(**over)}
    if shared is None:
        value["attempt"] = attempt
    else:
        value.update(shared=list(shared), rule=rule)
    return value


RA, RB = reservation("ra"), reservation("rb")


def attempt(attempt_id, unit, arm, *, res=None, terminal="completed", outcome="correct") -> dict:
    return {"id": attempt_id, "unitId": unit, "arm": arm,
            "reservationSha256": res.sha256 if res is not None else None,
            "observationSha256": h("obs-" + attempt_id), "terminal": terminal, "outcome": outcome}


def ledger() -> dict:
    """Two arms on the same three registered units; each started attempt is reserved."""
    return {
        "registered_units": ["u1", "u2", "u3"], "arms": ["base", "refined"],
        "attempts": [attempt("a1", "u1", "base", res=RA),
                     attempt("b1", "u1", "refined", res=RB, terminal="failed", outcome="incorrect")],
        "entries": [entry("setup-1", "setup", shared=["a1", "b1"], wall=obs(2, "s")),
                    entry("prop-a1", "proposal", attempt="a1", wall=obs(1500, "ms"),
                          quota=obs(3, "ktoken"), human=obs(2, "min")),
                    entry("prop-b1", "proposal", attempt="b1", wall=obs(700, "ms")),
                    entry("clean-a1", "cleanup", attempt="a1", journal=obs(1, "kib")),
                    entry("clean-b1", "cleanup", attempt="b1", journal=obs(2048, "byte"))],
        "reservations": [RA, RB]}


def run(value=None) -> dict:
    return costs.reconcile(**(value or ledger())).to_dict()


class Conversion(unittest.TestCase):
    def test_units_convert_exactly_to_canonical_integer_units(self):
        report = run()
        self.assertEqual(report["units"]["wall"], "ms")
        self.assertEqual(report["totals"]["wall"]["point"], 2000 + 1500 + 700)
        self.assertEqual(report["totals"]["quota"]["point"], 3000)
        self.assertEqual(report["totals"]["human"]["point"], 120)
        self.assertEqual(report["totals"]["journal"]["point"], 1024 + 2048)

    def test_eur_converts_to_cents(self):
        value = ledger()
        value["entries"][1]["measures"]["cash"] = obs(1, "eur", "invoice")
        self.assertEqual(run(value)["totals"]["cash"]["point"], 100)

    def test_unit_of_another_dimension_is_refused_so_quota_never_becomes_cash(self):
        for dim, unit in (("cash", "token"), ("quota", "eur-cent"), ("wall", "byte"),
                          ("human", "ms"), ("cash", "EUR"), ("cash", ["eur"])):
            value = ledger()
            value["entries"][1]["measures"][dim] = obs(1, unit)
            with self.subTest(dim=dim, unit=unit), self.assertRaises(costs.CostError) as caught:
                run(value)
            self.assertEqual(caught.exception.reason, "invalid-unit")

    def test_values_must_be_bounded_nonnegative_integers_with_evidence(self):
        for bad in (-1, 1.5, True, "1", None, costs.MAX_VALUE + 1):
            value = ledger()
            value["entries"][1]["measures"]["wall"] = obs(0, "ms") | {"value": bad}
            with self.subTest(value=bad), self.assertRaises(costs.CostError) as caught:
                run(value)
            self.assertEqual(caught.exception.reason, "invalid-value")
        value = ledger()
        value["entries"][1]["measures"]["wall"] = obs(costs.MAX_VALUE // 1000 + 1, "s")
        with self.assertRaises(costs.CostError):
            run(value)
        for broken in ({"status": "observed", "value": 1, "unit": "ms"},
                       obs(1, "ms") | {"evidenceSha256": "x"}, obs(1, "ms") | {"extra": 1},
                       {"status": "unknown"}, {"status": "unknown", "reason": "bad reason"},
                       {"status": "guessed", "value": 1}, [1]):
            value = ledger()
            value["entries"][1]["measures"]["wall"] = broken
            with self.assertRaises(costs.CostError):
                run(value)

    def test_unknown_dimension_is_refused(self):
        value = ledger()
        value["entries"][1]["measures"]["gpu"] = obs(1, "ms")
        with self.assertRaises(costs.CostError):
            run(value)


class Unknowns(unittest.TestCase):
    def test_missing_cash_is_unknown_never_zero_and_blocks_economic_claim(self):
        value = ledger()
        del value["entries"][1]["measures"]["cash"]
        report = run(value)
        cash = report["totals"]["cash"]
        self.assertIsNone(cash["point"])
        self.assertIsNone(cash["upper"])
        self.assertEqual(cash["lower"], 0)
        self.assertEqual(cash["unknownEntries"], ["prop-a1"])
        self.assertIn("unknown-cash", report["economic"]["blockers"])
        self.assertTrue(report["economic"]["claimBlocked"])
        self.assertIsNone(report["arms"]["base"]["costs"]["cash"]["point"])
        self.assertEqual(report["arms"]["refined"]["costs"]["cash"]["point"], 0)

    def test_explicit_unknown_keeps_known_lower_bound(self):
        value = ledger()
        value["entries"][2]["measures"]["wall"] = unknown("host-lost")
        wall = run(value)["totals"]["wall"]
        self.assertEqual((wall["lower"], wall["point"], wall["upper"]), (3500, None, None))
        self.assertEqual(wall["unknownEntries"], ["prop-b1"])

    def test_unknown_quota_does_not_block_cash_claim_but_stays_unknown(self):
        value = ledger()
        value["entries"][1]["measures"]["quota"] = unknown()
        report = run(value)
        self.assertIsNone(report["totals"]["quota"]["point"])
        self.assertEqual(report["economic"]["blockers"], [])

    def test_empty_ledger_has_no_known_cash(self):
        value = ledger()
        value.update(attempts=[], entries=[], reservations=[])
        report = run(value)
        self.assertIsNone(report["totals"]["cash"]["point"])
        self.assertIn("unknown-cash", report["economic"]["blockers"])
        self.assertEqual(report["phasesWithoutEntries"], list(costs.PHASES))


class Cash(unittest.TestCase):
    def test_complete_zero_cash_ledger_is_not_blocked(self):
        report = run()
        economic = report["economic"]
        self.assertEqual(economic["additionalCashEurCents"]["point"], 0)
        self.assertEqual(economic["cashCapEurCents"], 0)
        self.assertEqual(economic["numericCaps"], "deferred-D2")
        self.assertEqual(economic["blockers"], [])
        self.assertFalse(economic["claimBlocked"])
        self.assertIs(report["executionAuthorization"], False)

    def test_any_observed_additional_cash_breaches_eur_zero_cap(self):
        value = ledger()
        value["entries"][2]["measures"]["cash"] = obs(1, "eur-cent", "invoice-2")
        value["entries"][1]["measures"]["cash"] = unknown()
        blockers = run(value)["economic"]["blockers"]
        self.assertIn("additional-cash-observed", blockers)
        self.assertIn("unknown-cash", blockers)


class SharedCosts(unittest.TestCase):
    def test_equal_rule_allocates_exact_shares_and_bounds_by_full_shared_cost(self):
        value = ledger()
        value["entries"][0]["measures"]["wall"] = obs(7, "ms")
        report = run(value)
        base = report["arms"]["base"]["costs"]["wall"]
        self.assertEqual(base["lower"], 1500)
        self.assertEqual(base["point"], "3007/2")
        self.assertEqual(base["upper"], 1507)
        self.assertEqual(report["totals"]["wall"]["point"], 7 + 1500 + 700)

    def test_unallocated_rule_is_excluded_from_point_but_kept_in_upper(self):
        value = ledger()
        value["entries"][0]["rule"] = "unallocated"
        base = run(value)["arms"]["base"]["costs"]["wall"]
        self.assertEqual((base["lower"], base["point"], base["upper"]), (1500, 1500, 3500))
        self.assertEqual(base["unallocatedEntries"], ["setup-1"])

    def test_shared_within_one_arm_is_fully_attributed(self):
        value = ledger()
        value["registered_units"].append("u4")
        value["attempts"].append(attempt("a2", "u2", "base", terminal="refused", outcome="ungraded"))
        value["entries"].append(entry("rev", "review", shared=["a1", "a2"], rule="unallocated",
                                      human=obs(1, "min")))
        human = run(value)["arms"]["base"]["costs"]["human"]
        self.assertEqual((human["lower"], human["point"], human["upper"]), (180, 180, 180))

    def test_peak_dimension_takes_maximum_not_sum(self):
        value = ledger()
        value["entries"][0]["measures"]["rss"] = obs(4, "mib")
        value["entries"][1]["measures"]["rss"] = obs(1, "mib")
        report = run(value)
        self.assertEqual(report["totals"]["rss"]["point"], 4 << 20)
        base = report["arms"]["base"]["costs"]["rss"]
        self.assertEqual((base["lower"], base["point"], base["upper"]), (1 << 20, 4 << 20, 4 << 20))
        self.assertNotIn("rss", report["arms"]["base"]["costPerCorrect"])

    def test_shared_scope_is_strict(self):
        for shared, rule, reason in (
                (["a1"], "equal", "invalid-entry"), (["a1", "a1"], "equal", "invalid-entry"),
                (["a1", "zz"], "equal", "unknown-attempt"), (["a1", "b1"], "weighted", "invalid-entry"),
                ("a1b1", "equal", "invalid-entry"), ([["a1"], "b1"], "equal", "invalid-entry")):
            value = ledger()
            value["entries"][0].update(shared=shared, rule=rule)
            with self.subTest(shared=shared, rule=rule), \
                    self.assertRaises(costs.CostError) as caught:
                run(value)
            self.assertEqual(caught.exception.reason, reason)
        value = ledger()
        value["entries"][1]["attempt"] = "zz"
        with self.assertRaises(costs.CostError) as caught:
            run(value)
        self.assertEqual(caught.exception.reason, "unknown-attempt")


class Reservations(unittest.TestCase):
    def test_open_reservation_blocks_claim(self):
        value = ledger()
        rc = reservation("rc")
        value["reservations"].append(rc)
        report = run(value)
        self.assertEqual(report["reconciliation"]["openReservations"], [rc.sha256])
        self.assertIn("open-reservation", report["economic"]["blockers"])

    def test_started_attempt_without_reservation_is_reported(self):
        value = ledger()
        value["attempts"][0]["reservationSha256"] = None
        value["reservations"] = [RB]
        report = run(value)
        self.assertEqual(report["reconciliation"]["unreservedAttempts"], ["a1"])
        self.assertIn("unreserved-attempt", report["economic"]["blockers"])

    def test_refused_attempt_needs_no_reservation(self):
        value = ledger()
        value["attempts"].append(attempt("a2", "u2", "base", terminal="refused", outcome="ungraded"))
        report = run(value)
        self.assertEqual(report["reconciliation"]["unreservedAttempts"], [])
        self.assertEqual(report["economic"]["blockers"], [])

    def test_reservation_reuse_unknown_hash_and_foreign_types_are_refused(self):
        value = ledger()
        value["attempts"][1]["reservationSha256"] = RA.sha256
        with self.assertRaises(costs.CostError) as caught:
            run(value)
        self.assertEqual(caught.exception.reason, "reservation-reused")
        value = ledger()
        value["attempts"][1]["reservationSha256"] = h("other")
        with self.assertRaises(costs.CostError) as caught:
            run(value)
        self.assertEqual(caught.exception.reason, "unknown-reservation")
        for bad in ([RA.to_dict(), RB], [RA, RA], [Reservation(b"{}"), RB],
                    [Reservation(canonical(RA.to_dict() | {"executionAuthorization": True}))]):
            value = ledger()
            value["reservations"] = bad
            with self.assertRaises(costs.CostError) as caught:
                run(value)
            self.assertEqual(caught.exception.reason, "invalid-reservation")

    def test_journal_overrun_and_unknown_journal_are_reported(self):
        value = ledger()
        value["entries"][3]["measures"]["journal"] = obs(4097, "byte")
        value["entries"][4]["measures"]["journal"] = unknown()
        report = run(value)["reconciliation"]
        self.assertEqual(report["journalExceeded"], ["a1"])
        self.assertEqual(report["journalUnreconciled"], ["b1"])

    def test_reserved_attempt_without_cleanup_is_unaccounted(self):
        value = ledger()
        value["entries"] = [e for e in value["entries"] if e["id"] != "clean-b1"]
        report = run(value)
        self.assertEqual(report["reconciliation"]["cleanupUnaccounted"], ["b1"])
        self.assertIn("cleanup-unaccounted", report["economic"]["blockers"])
        self.assertIn("cleanup", report["phases"])

    def test_shared_cleanup_accounts_for_each_target(self):
        value = ledger()
        value["entries"][3:] = [entry("clean", "cleanup", shared=["a1", "b1"])]
        self.assertEqual(run(value)["reconciliation"]["cleanupUnaccounted"], [])


    def test_journal_exactly_at_reservation_is_not_exceeded(self):
        value = ledger()
        value["entries"][3]["measures"]["journal"] = obs(4096, "byte")
        report = run(value)
        self.assertEqual(report["reconciliation"]["journalExceeded"], [])
        self.assertEqual(report["economic"]["blockers"], [])

    def test_shared_journal_follows_declared_allocation(self):
        for size, rule, exceeded, unreconciled in ((6000, "equal", [], []),
                                                   (9000, "equal", ["a1", "b1"], []),
                                                   (6000, "unallocated", [], ["a1", "b1"]),
                                                   (4096, "unallocated", [], [])):
            value = ledger()
            value["entries"][3:] = [entry("clean", "cleanup", shared=["a1", "b1"], rule=rule,
                                          journal=obs(size, "byte"))]
            with self.subTest(size=size, rule=rule):
                report = run(value)["reconciliation"]
                self.assertEqual(report["journalExceeded"], exceeded)
                self.assertEqual(report["journalUnreconciled"], unreconciled)

    def test_negative_reserved_journal_is_refused(self):
        value = ledger()
        value["reservations"] = [reservation("ra", -5), RB]
        value["attempts"][0]["reservationSha256"] = value["reservations"][0].sha256
        with self.assertRaises(costs.CostError) as caught:
            run(value)
        self.assertEqual(caught.exception.reason, "invalid-reservation")

    def test_reserved_refused_attempt_still_needs_cleanup(self):
        value = ledger()
        value["attempts"][1].update(terminal="refused", outcome="ungraded")
        value["entries"] = [e for e in value["entries"] if e["id"] != "clean-b1"]
        self.assertEqual(run(value)["reconciliation"]["cleanupUnaccounted"], ["b1"])

    def test_started_attempt_without_cost_entries_blocks_claim(self):
        value = ledger()
        value["registered_units"].append("u4")
        value["attempts"] += [attempt("a2", "u2", "base"),
                              attempt("a3", "u3", "base", terminal="refused", outcome="ungraded")]
        value["entries"].append(entry("clean-a2", "cleanup", attempt="a2"))
        report = run(value)
        self.assertEqual(report["reconciliation"]["attemptsWithoutCost"], ["a2"])
        self.assertIn("incomplete-attempt-costs", report["economic"]["blockers"])


class Denominators(unittest.TestCase):
    def test_all_registered_units_and_terminals_stay_in_denominators(self):
        report = run()
        base, refined = report["arms"]["base"], report["arms"]["refined"]
        self.assertEqual(base["denominators"], {
            "registered": 3, "attempted": 1, "started": 1, "notAttempted": 2,
            "terminals": {"completed": 1, "failed": 0, "interrupted": 0, "refused": 0,
                          "unobserved": 0},
            "outcomes": {"correct": 1, "incorrect": 0, "ungraded": 0}})
        self.assertEqual(base["correctPerRegistered"], "1/3")
        self.assertEqual(base["correctPerStarted"], 1)
        self.assertEqual(base["costPerCorrect"]["wall"]["point"], 2500)
        self.assertEqual(refined["denominators"]["terminals"]["failed"], 1)
        self.assertEqual(refined["correctPerRegistered"], 0)
        self.assertEqual(refined["costPerCorrect"], "undefined")

    def test_zero_started_rate_is_undefined(self):
        value = ledger()
        value["attempts"][1].update(terminal="refused", outcome="ungraded", reservationSha256=None)
        value["reservations"] = [RA]
        self.assertEqual(run(value)["arms"]["refined"]["correctPerStarted"], "undefined")

    def test_cost_per_correct_preserves_unknown(self):
        value = ledger()
        value["entries"][1]["measures"]["wall"] = unknown()
        per = run(value)["arms"]["base"]["costPerCorrect"]["wall"]
        self.assertEqual((per["lower"], per["point"], per["upper"]), (0, None, None))

    def test_population_cannot_expand_or_duplicate(self):
        cases = [("unitId", "u9", "unregistered-unit"), ("arm", "other", "unknown-arm"),
                 ("terminal", "done", "invalid-attempt"), ("outcome", "pass", "invalid-attempt"),
                 ("observationSha256", "x", "invalid-attempt"), ("unitId", ["u1"], "invalid-attempt"),
                 ("arm", {"base": 1}, "invalid-attempt")]
        for key, bad, reason in cases:
            value = ledger()
            value["attempts"][0][key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(costs.CostError) as caught:
                run(value)
            self.assertEqual(caught.exception.reason, reason)
        value = ledger()
        value["attempts"][1].update(arm="base", id="a2")
        with self.assertRaises(costs.CostError) as caught:
            run(value)
        self.assertEqual(caught.exception.reason, "duplicate-attempt")
        value = ledger()
        value["attempts"][1]["id"] = "a1"
        with self.assertRaises(costs.CostError):
            run(value)

    def test_outcomes_need_a_bound_observation_unless_unobserved(self):
        for over in ({"observationSha256": None},
                     {"terminal": "unobserved", "outcome": "ungraded"}):
            value = ledger()
            value["attempts"][0].update(over)
            with self.subTest(over=over), self.assertRaises(costs.CostError) as caught:
                run(value)
            self.assertEqual(caught.exception.reason, "inconsistent-outcome")
        value = ledger()
        value["attempts"][0].update(terminal="unobserved", outcome="ungraded",
                                    observationSha256=None)
        base = run(value)["arms"]["base"]
        self.assertEqual(base["denominators"]["terminals"]["unobserved"], 1)
        self.assertEqual(base["denominators"]["started"], 1)
        self.assertEqual(base["costPerCorrect"], "undefined")

    def test_correct_requires_completed_terminal(self):
        value = ledger()
        value["attempts"][0]["terminal"] = "interrupted"
        with self.assertRaises(costs.CostError) as caught:
            run(value)
        self.assertEqual(caught.exception.reason, "inconsistent-outcome")

    def test_registration_is_strict(self):
        for key, bad in (("registered_units", ["u1", "u1"]), ("arms", []), ("arms", ["a", "a"]),
                         ("registered_units", "u1"), ("arms", ["bad arm"])):
            value = ledger()
            value[key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(costs.CostError) as caught:
                run(value)
            self.assertEqual(caught.exception.reason, "invalid-registration")


class Phases(unittest.TestCase):
    def test_every_registered_phase_is_reported_and_unknown_phase_refused(self):
        self.assertEqual(costs.PHASES, ("setup", "context", "proposal", "probe", "retry",
                                        "selection", "reflection", "verification", "recovery",
                                        "review", "cleanup"))
        value = ledger()
        value["entries"] += [entry(p + "-x", p, attempt="a1") for p in costs.PHASES]
        report = run(value)
        self.assertEqual(sorted(report["phases"]), sorted(costs.PHASES))
        self.assertEqual(report["phasesWithoutEntries"], [])
        self.assertEqual(report["phases"]["proposal"]["wall"]["point"], 2200)
        value = ledger()
        value["entries"][1]["phase"] = "billing"
        with self.assertRaises(costs.CostError):
            run(value)

    def test_entry_shape_is_strict(self):
        for mutate in (lambda e: e.update(extra=1), lambda e: e.pop("measures"),
                       lambda e: e.update(shared=["a1", "b1"]), lambda e: e.update(id="bad id"),
                       lambda e: e.update(measures=[1])):
            value = ledger()
            mutate(value["entries"][1])
            with self.assertRaises(costs.CostError) as caught:
                run(value)
            self.assertEqual(caught.exception.reason, "invalid-entry")
        value = ledger()
        value["entries"].append(deepcopy(value["entries"][1]))
        with self.assertRaises(costs.CostError) as caught:
            run(value)
        self.assertEqual(caught.exception.reason, "duplicate-entry")


class Record(unittest.TestCase):
    def test_report_is_deterministic_under_input_order_and_bound_to_ledger(self):
        first = costs.reconcile(**ledger())
        value = ledger()
        for key in ("attempts", "entries", "reservations", "registered_units", "arms"):
            value[key] = list(reversed(value[key]))
        second = costs.reconcile(**value)
        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual(first.data["ledgerSha256"], second.data["ledgerSha256"])
        changed = ledger()
        changed["entries"][1]["measures"]["wall"] = obs(1500, "ms", "other-evidence")
        self.assertNotEqual(costs.reconcile(**changed).data["ledgerSha256"],
                            first.data["ledgerSha256"])
        swapped = ledger()
        swapped["entries"][0]["shared"].reverse()
        self.assertEqual(costs.reconcile(**swapped).sha256, first.sha256)
        extra = ledger()
        extra["reservations"].append(reservation("rc"))
        self.assertNotEqual(costs.reconcile(**extra).data["ledgerSha256"],
                            first.data["ledgerSha256"])
        self.assertEqual(first.data["format"], costs.FORMAT)

    def test_report_is_immutable_and_detached_from_inputs(self):
        value = ledger()
        report = costs.reconcile(**value)
        before = report.sha256
        value["entries"][1]["measures"]["wall"]["value"] = 9
        self.assertEqual(report.sha256, before)
        with self.assertRaises(FrozenInstanceError):
            report.data = {}
        with self.assertRaises(TypeError):
            report.data["format"] = "x"
        out = report.to_dict()
        out["format"] = "x"
        self.assertEqual(report.data["format"], costs.FORMAT)

    def test_input_counts_are_bounded(self):
        value = ledger()
        value["entries"] = [entry(f"e{i}", "probe", attempt="a1")
                            for i in range(costs.MAX_ENTRIES + 1)]
        with self.assertRaises(costs.CostError) as caught:
            run(value)
        self.assertEqual(caught.exception.reason, "invalid-entry")
        ids = [f"x{i}" for i in range(costs.MAX_ATTEMPTS)]
        value = ledger()
        value["registered_units"] = ids
        value["attempts"] = [attempt(i, i, "base", terminal="refused", outcome="ungraded")
                             for i in ids]
        value["reservations"] = []
        value["entries"] = [entry(f"e{i}", "probe", shared=ids)
                            for i in range(costs.MAX_TARGET_REFS // costs.MAX_ATTEMPTS + 1)]
        with self.assertRaises(costs.CostError) as caught:
            run(value)
        self.assertEqual(caught.exception.reason, "invalid-entry")


if __name__ == "__main__":
    unittest.main()
