# SPDX-License-Identifier: AGPL-3.0-only
"""Opt-in diagnostic accounting, without runtime authority or utility claims.

Monotonic float clock readings are converted to integer nanoseconds; this does
not improve the underlying clock's resolution. Child CPU is process-global
completed-child usage, never a sum of inclusive per-budget observations.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
import math
import sys
import threading
import time

from agent_braid.utility_budget_observer import observe_git_budgets

PHASES = ("input", "replay", "preparation", "grant", "execution",
          "independent_verification", "report_serialization", "cleanup")


class AccountingError(ValueError):
    """Required wall accounting is invalid."""


def completed_children_cpu():
    """Only completed child processes observed by process-global getrusage."""
    import resource
    value = resource.getrusage(resource.RUSAGE_CHILDREN)
    return value.ru_utime, value.ru_stime


def process_lifetime_rss():
    import resource
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


class UtilityAccounting:
    """One coordinator treatment with disjoint phases and explicit residual."""

    def __init__(self, *, monotonic=time.monotonic, parent_cpu=time.process_time,
                 child_cpu=completed_children_cpu, lifetime_rss=process_lifetime_rss,
                 child_attribution_valid=False, max_budgets=64):
        if not isinstance(max_budgets, int) or isinstance(max_budgets, bool) or max_budgets < 1:
            raise ValueError("max_budgets must be a positive integer")
        self.monotonic = monotonic
        self.parent_cpu = parent_cpu
        self.child_cpu = child_cpu
        self.lifetime_rss = lifetime_rss
        self.child_attribution_valid = child_attribution_valid
        self.max_budgets = max_budgets
        self._start = None
        self._last_wall = None
        self._active = None
        self._phases = []
        self._workers = []
        self._budgets = {}
        self._budget_valid = True
        self._registry_depth = 0
        self._registry_ever_active = False
        self._errors = []
        self._lock = threading.Lock()
        self._record = None
        self._end_sample = None
        self._sealed = False

    def _wall(self):
        try:
            value = self.monotonic()
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError("nonfinite or negative")
            value = round(value * 1_000_000_000)
        except Exception as exc:
            raise AccountingError("invalid monotonic wall clock") from exc
        if self._last_wall is not None and value < self._last_wall:
            raise AccountingError("reversed monotonic wall clock")
        self._last_wall = value
        return value

    def _optional(self, function, name):
        try:
            value = function()
            values = value if isinstance(value, tuple) else (value,)
            if any(isinstance(item, bool) or not math.isfinite(item) or item < 0 for item in values):
                self._errors.append(f"invalid {name} counter")
                return None, "invalid nonfinite or negative counter"
            return value, None
        except Exception as exc:
            return None, f"unavailable: {type(exc).__name__}"

    def _sample(self):
        wall = self._wall()
        parent, parent_reason = self._optional(self.parent_cpu, "parent CPU")
        if self.child_attribution_valid:
            child, child_reason = self._optional(self.child_cpu, "completed-child CPU")
            if child is not None and (not isinstance(child, tuple) or len(child) != 2):
                child, child_reason = None, "invalid completed-child counter shape"
                self._errors.append(child_reason)
        else:
            child, child_reason = None, "process-global completed-child attribution not asserted"
        return {"wallNs": wall, "parent": parent, "parentReason": parent_reason,
                "child": child, "childReason": child_reason}

    def _delta(self, start, end):
        result = {"startWallNs": start["wallNs"], "endWallNs": end["wallNs"],
                  "wallNs": end["wallNs"] - start["wallNs"], "counterReasons": {}}
        for name, index in (("parentCpuSeconds", None),
                            ("completedChildUserCpuSeconds", 0),
                            ("completedChildSystemCpuSeconds", 1)):
            field = "parent" if index is None else "child"
            reason = start[field + "Reason"] or end[field + "Reason"]
            value = None
            if reason is None:
                left = start[field] if index is None else start[field][index]
                right = end[field] if index is None else end[field][index]
                value = right - left
                if not math.isfinite(value) or value < 0:
                    value, reason = None, "invalid reversed or nonfinite counter delta"
                    self._errors.append(f"invalid {name} delta")
            result[name] = value
            if reason is not None:
                result["counterReasons"][name] = reason
        return result

    def start(self):
        if self._start is not None:
            raise AccountingError("treatment already started")
        self._start = self._sample()
        return self

    @contextmanager
    def phase(self, name):
        if self._start is None or self._record is not None:
            raise AccountingError("phase requires an open treatment")
        if name not in PHASES:
            raise AccountingError("unknown required phase")
        if self._active is not None:
            raise AccountingError("overlapping coordinator phases")
        if any(item["name"] == name for item in self._phases):
            raise AccountingError("duplicate coordinator phase")
        start = self._sample()
        budget_start = self._budget_snapshot()
        self._active = name
        outcome = "success"
        try:
            yield
        except BaseException:
            outcome = "failure"
            raise
        finally:
            self._active = None
            budget_end = self._budget_snapshot()
            end = self._sample()
            phase = {"name": name, "outcome": outcome, **self._delta(start, end)}
            budget_reason = budget_start[2] or budget_end[2]
            values = None if budget_reason else (
                budget_end[0] - budget_start[0], budget_end[1] - budget_start[1])
            if values is not None and any(value < 0 for value in values):
                budget_reason = "invalid reversed budget counter delta"
                self._budget_valid = False
                self._errors.append(budget_reason)
            for key, index in (("gitCommands", 0), ("acceptedBudgetOutputBytes", 1)):
                phase[key] = None if budget_reason else values[index]
                if budget_reason:
                    phase["counterReasons"][key] = budget_reason
            phase["sampledScratchPeakBytes"] = None
            phase["observedCapturedOutputBytes"] = None
            phase["counterReasons"]["observedCapturedOutputBytes"] = (
                "runner does not expose rejected or discarded output bytes; total bytes read unavailable")
            phase["counterReasons"]["sampledScratchPeakBytes"] = (
                "budget scratch is a cumulative sampled high-water; no isolated phase allocation")
            self._phases.append(phase)

    def _register_budget(self, budget):
        try:
            with self._lock:
                if self._record is not None:
                    self._budget_valid = False
                    self._errors.append("budget registered after operational finish")
                elif id(budget) not in self._budgets:
                    if len(self._budgets) >= self.max_budgets:
                        self._budget_valid = False
                        self._errors.append("budget registry capacity exceeded")
                    else:
                        with budget.lock:
                            baseline = (budget.commands, budget.output_bytes)
                        self._budgets[id(budget)] = (budget, baseline)
        except Exception as exc:
            self._budget_valid = False
            self._errors.append(f"budget observer unavailable: {type(exc).__name__}")

    @contextmanager
    def activate_git_budget_registry(self):
        if self._start is None or self._record is not None:
            raise AccountingError("budget registry requires an open treatment")
        self._registry_depth += 1
        self._registry_ever_active = True
        try:
            with observe_git_budgets(self._register_budget):
                yield
        finally:
            self._registry_depth -= 1

    def _budget_snapshot(self, *, require_active=True):
        """Unique budget charges since registration, never nested CPU sums."""
        if not self._registry_ever_active or (require_active and not self._registry_depth):
            return None, None, "no budget observer active"
        if not self._budget_valid:
            return None, None, "incomplete or invalid budget observations"
        commands = captured = 0
        try:
            with self._lock:
                for budget, baseline in self._budgets.values():
                    with budget.lock:
                        count = budget.commands - baseline[0]
                        size = budget.output_bytes - baseline[1]
                    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0
                           for v in (count, size)):
                        raise ValueError("invalid budget counters")
                    commands += count
                    captured += size
        except Exception as exc:
            self._budget_valid = False
            self._errors.append(f"budget observation invalid: {type(exc).__name__}")
            return None, None, "incomplete or invalid budget observations"
        return commands, captured, None

    def record_worker_interval(self, start, end):
        if self._record is not None:
            raise AccountingError("worker interval after finish")
        if any(isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in (start, end)) or end < start:
            raise AccountingError("invalid worker interval")
        with self._lock:
            self._workers.append((round(start * 1e9), round(end * 1e9)))

    def _worker_summary(self, outer):
        if not self._workers:
            return {"unionWallNs": None, "peakOccupancy": None,
                    "reason": "no worker interval observations"}
        points = []
        for start, end in self._workers:
            if start < outer["startWallNs"] or end > outer["endWallNs"]:
                raise AccountingError("worker interval outside operational outer interval")
            if end > start:
                points.extend(((start, 1), (end, -1)))
        occupancy = peak = union = 0
        previous = None
        for tick, delta in sorted(points):
            if previous is not None and occupancy:
                union += tick - previous
            occupancy += delta
            peak = max(peak, occupancy)
            previous = tick
        return {"unionWallNs": union, "peakOccupancy": peak, "reason": None}

    def finish(self, *, outcome="success"):
        if self._start is None or self._record is not None or self._active is not None:
            raise AccountingError("finish requires open treatment without active phase")
        if outcome not in ("success", "failure"):
            raise AccountingError("unknown treatment outcome")
        if outcome == "failure":
            self._errors.append("treatment failed; no complete diagnostic treatment")
        end = self._sample()  # Closing tick precedes all sealing/encoding.
        self._end_sample = end
        outer = self._delta(self._start, end)
        residual = outer["wallNs"] - sum(item["wallNs"] for item in self._phases)
        if residual < 0:
            raise AccountingError("phase wall totals exceed outer wall interval")
        missing = [name for name in PHASES if name not in {p["name"] for p in self._phases}]
        if missing:
            self._errors.append("missing required wall phases: " + ", ".join(missing))
        if any(p["outcome"] == "failure" for p in self._phases):
            self._errors.append("one or more required phases failed")
        commands, captured, budget_reason = self._budget_snapshot(require_active=False)
        scratch_reason = (
            "frozen budget does not expose whether sampled scratch high-water was observed; allocation unavailable")
        if not self._budget_valid:
            budget_reason = "incomplete or invalid budget observations"
        if budget_reason:
            scratch_reason = budget_reason
        rss, rss_reason = self._optional(self.lifetime_rss, "process lifetime RSS")
        worker = self._worker_summary(outer)
        self._record = {"outcome": outcome, "complete": not self._errors,
                        "errors": list(self._errors), "outer": outer,
                        "phases": copy.deepcopy(self._phases), "residualWallNs": residual,
                        "gitBudgetCount": len(self._budgets),
                        "gitCommands": commands if self._budget_valid else None,
                        "acceptedBudgetOutputBytes": captured if self._budget_valid else None,
                        "observedCapturedOutputBytes": None,
                        "sampledScratchPeakBytes": None,
                        "processLifetimeRssBytes": rss,
                        "optionalReasons": {"sampledScratchPeakBytes": scratch_reason,
                                            "gitCommands": budget_reason,
                                            "acceptedBudgetOutputBytes": budget_reason,
                                            "observedCapturedOutputBytes": (
                                                "runner does not expose rejected or discarded output bytes; total bytes read unavailable"),
                                            "processLifetimeRssBytes": rss_reason},
                        "workerIntervals": worker,
                        "scopes": {"parentCpu": "process including threads",
                                   "childCpu": "process-global completed children; not per-worker",
                                   "scratch": "unavailable; frozen budgets expose no reliable sample-presence counter",
                                   "rss": "process lifetime high-water, not treatment delta",
                                   "bytes": (
                                       "accepted budget-counted Git output; discarded overflow chunks excluded; total bytes read unavailable"),
                                   "commands": "Git command budget charges, including refused launches",
                                   "workerOverlap": "observed wall intervals, not CPU parallelism",
                                   "observer": "sealing and output excluded from operational outer"}}
        self._budgets.clear()
        return self.snapshot()

    def snapshot(self):
        if self._record is None:
            raise AccountingError("operational treatment not finished")
        return copy.deepcopy(self._record)

    def preview(self):
        """Unsealed phase observations; no future closing timestamp is invented."""
        if self._start is None or self._record is not None:
            raise AccountingError("preview requires an open treatment")
        return {"sealed": False, "startWallNs": self._start["wallNs"],
                "phases": copy.deepcopy(self._phases), "activePhase": self._active,
                "errors": list(self._errors)}

    def seal(self, encoder):
        """Time all work since closing, including finish aggregation and copying.

        The callback cannot encode its own future ending timestamp. Its separately
        returned observer record and subsequent aggregate writing have a later,
        explicitly separate output boundary.
        """
        if self._sealed:
            raise AccountingError("observer already sealed")
        record = self.snapshot()
        self._sealed = True
        start = self._end_sample
        errors_before = len(self._errors)
        try:
            value = encoder(record)
        finally:
            end = self._sample()
            self.observer = self._delta(start, end)
            self.observer["scope"] = "observer sealing/output outside operational outer"
            self.observer["complete"] = len(self._errors) == errors_before
            self.observer["errors"] = self._errors[errors_before:]
        return value, copy.deepcopy(self.observer)
