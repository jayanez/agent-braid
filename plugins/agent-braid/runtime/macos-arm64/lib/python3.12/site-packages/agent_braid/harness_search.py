# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Agent Braid modifications Copyright 2026 Juan Antonio Yáñez García.
# Adapted the sequential-depth and parallel-width stage structure from
# harness2/core/recursion.py (run_sequential, run_parallel), the candidate pool that
# includes the unchanged base from harness2/core/selection.py, and the rollout/session
# ledger identity from harness2/core/ledger.py (Ledger.assert_identity: counts must
# match the reservation and no label repeats) at
# 1cfe254e8d25b15f37048c3730134686abe60335. Changes: injected proposer/prober callbacks
# instead of model sessions and thread pools (width is simulated serially), a frozen
# hash-bound plan, reservations computed before any stage, separate proposal and
# transport retry counters, an identity-bound cache of scored outcomes, a lineage DAG,
# cancellation, equal-budget baselines (including the one-round refinement it imports
# unchanged) and marginal-quality reporting, with no reflection or adoption step.
"""Bounded sequential-depth and parallel-width refinement with equal-budget comparison.

SPEC-050/T007, component class C9, under the frozen capability profile contract
(specs/050-braid-harness-adaptation/contracts/interface.md). Pure and offline. The
module dispatches nothing: a trusted caller supplies a proposer (untrusted text in)
and a prober (an independent verifier's score out). It reuses ``harness_refinement``
for policy binding, proposal validation, composition, outcome normalization and
selection, and adds the search shape around them.

Ceilings: the contract admits depth 1 and width 1 at v0.1. Plans above that ceiling
(up to the local offline limits ``MAX_DEPTH``/``MAX_WIDTH``) exist only so equal-budget
evidence can be produced; they are recorded ``aboveContractCeiling`` with
``amendmentRequired`` and admission stays ``blocked``. Width is simulated serially; a
plan that asks for native concurrency refuses, because native concurrency needs its
own qualified effect profile. Nothing here starts a process, opens a connection or
spends model quota, and every result and comparison record carries ``executionAuthorization`` false.

Comparison results are synthetic unless a trusted caller feeds real, separately
authorized probe outcomes; they never support a utility claim by themselves.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from types import MappingProxyType
from typing import Any
import re

from .harness_manifest import HarnessManifest
from .harness_refinement import (
    SCOPES, ProbeRequest, SelectionPolicy, _candidate_hash,
    _compose, _copy, _decide, _outcome, _validate_proposal, parse_policy, run_round)
from .system_one import InvalidDecision, canonical, digest, freeze, parse_json, thaw

PLAN_FORMAT = "braid-harness-search-plan/v0.1"
RESULT_FORMAT = "braid-harness-search-result/v0.1"
COMPARISON_FORMAT = "braid-harness-search-comparison/v0.1"
UPSTREAM_REVISION = "1cfe254e8d25b15f37048c3730134686abe60335"
CONTRACT_DEPTH = 1                # contract section 6 ceilings at v0.1
CONTRACT_WIDTH = 1
MAX_DEPTH = 4                     # local offline limits for equal-budget evidence only
MAX_WIDTH = 4
MAX_RETRIES = 2
MAX_PLAN_BYTES = 4096
MAX_BUDGET = MAX_DEPTH            # non-base probes per comparison arm
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_PLAN_KEYS = {"format", "planId", "proberId", "policySha256", "depth", "width", "compose",
              "stopOnPlateau", "proposalRetries", "transportRetries", "concurrency"}
ADMISSION = {"state": "blocked", "blocker": "no-containment-qualification"}
_PROVENANCE = {
    "upstreamRevision": UPSTREAM_REVISION,
    "adapted": [
        "core/recursion.py: run_sequential/run_parallel round structure",
        "core/selection.py: candidate pool that includes the unchanged base",
        "core/ledger.py: reservation and ledger identity (no repeated label)",
    ],
    "changes": "injected callbacks; serial simulation of width; frozen hash-bound plan; "
               "reservation before any stage; separate retry counters; identity-bound "
               "cache; lineage DAG; cancellation; no reflection",
}


class SearchError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-request"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-request") -> None:
    if not condition:
        raise SearchError(reason)


def _int(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


# --- plan and reservation ----------------------------------------------------------------


@dataclass(frozen=True)
class SearchPlan:
    """Frozen search shape; construction is not verification (see ``parse_plan``)."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    @property
    def depth(self) -> int:
        return self.data["depth"]

    @property
    def width(self) -> int:
        return self.data["width"]

    @property
    def compose(self) -> bool:
        return self.data["compose"]

    @property
    def stop_on_plateau(self) -> bool:
        return self.data["stopOnPlateau"]

    @property
    def proposal_retries(self) -> int:
        return self.data["proposalRetries"]

    @property
    def transport_retries(self) -> int:
        return self.data["transportRetries"]

    @property
    def prober_id(self) -> str:
        return self.data["proberId"]

    @property
    def reservation(self) -> dict:
        slots = self.depth * self.width
        composes = self.depth if self.compose and self.width >= 2 else 0
        retries = self.transport_retries
        return {
            "rounds": self.depth, "slotsPerRound": self.width,
            "proposalAttempts": slots * (1 + self.proposal_retries + retries),
            "probeAttempts": (slots + composes) * (1 + retries),
            "baseProbeAttempts": 1 + retries,
        }


def parse_plan(raw: bytes, *, manifest: HarnessManifest, policy: SelectionPolicy) -> SearchPlan:
    """Strictly parse a plan and bind it to the manifest and its verified policy."""
    _require(isinstance(manifest, HarnessManifest) and isinstance(policy, SelectionPolicy))
    policy = parse_policy(policy.canonical_bytes, manifest=manifest)  # re-verify, never trust
    _require(type(raw) is bytes and len(raw) <= MAX_PLAN_BYTES, "invalid-plan")
    try:
        value = parse_json(raw)
    except InvalidDecision:
        raise SearchError("invalid-plan") from None
    _require(type(value) is dict and set(value) == _PLAN_KEYS and value["format"] == PLAN_FORMAT,
             "invalid-plan")
    # A plan that requests native concurrency is refused: it needs its own effect profile.
    _require(value["concurrency"] != "native", "native-concurrency-gated")
    ok = (value["concurrency"] == "serial"
          and all(type(value[k]) is str and _ID.fullmatch(value[k]) for k in ("planId", "proberId"))
          and type(value["policySha256"]) is str and _HASH.fullmatch(value["policySha256"])
          and _int(value["depth"], 1, MAX_DEPTH) and _int(value["width"], 1, MAX_WIDTH)
          and type(value["compose"]) is bool and type(value["stopOnPlateau"]) is bool
          and _int(value["proposalRetries"], 0, MAX_RETRIES)
          and _int(value["transportRetries"], 0, MAX_RETRIES))
    _require(bool(ok), "invalid-plan")
    _require(value["policySha256"] == policy.sha256, "policy-drift")
    return SearchPlan(freeze(value), canonical(value))


# --- cache and shared base ------------------------------------------------------------------


def _cache_key(manifest: HarnessManifest, policy_sha256: str, prober_id: str, scope: str,
               candidate_sha256: str) -> str:
    return digest({"manifestSha256": manifest.sha256, "policySha256": policy_sha256,
                   "proberId": prober_id, "scope": scope, "candidateSha256": candidate_sha256})


class SearchCache:
    """Scored outcomes keyed by manifest, policy, prober, scope and candidate identity.

    Only completed, scored outcomes are stored; failed, interrupted, refused and
    unscored results are never reused, so a transport hiccup cannot be pinned.
    """

    def __init__(self) -> None:
        self._rows: dict[str, dict] = {}

    def get(self, key: str) -> dict | None:
        row = self._rows.get(key)
        return None if row is None else dict(row)

    def put(self, key: str, outcome: Mapping[str, Any]) -> bool:
        if outcome.get("status") != "scored":
            return False
        self._rows[key] = {"status": "scored", "reason": None, "score": outcome["score"],
                           "observationSha256": outcome["observationSha256"]}
        return True

    def __len__(self) -> int:
        return len(self._rows)


@dataclass(frozen=True)
class SharedBase:
    """One base probe reused by every arm; bound to the manifest and prober identity."""

    manifest_sha256: str
    prober_id: str
    raw: Any                      # plain-dict snapshot of the prober's base output
    attempts: int


def probe_base(manifest: HarnessManifest, *, prober_id: str, probe: Callable[[ProbeRequest], Any],
               retries: int = 0) -> SharedBase:
    """Probe the unchanged base once (with transport retries) for reuse across arms."""
    _require(isinstance(manifest, HarnessManifest) and callable(probe)
             and type(prober_id) is str and _ID.fullmatch(prober_id) is not None
             and _int(retries, 0, MAX_RETRIES))
    request = ProbeRequest("base", manifest.data["base"]["sha256"], MappingProxyType({}))
    raw: Any = None
    for attempts in range(1, retries + 2):
        try:
            raw = probe(request)
        except Exception:  # untrusted prober
            raw = None
        if raw is not None:
            break
    if raw is not None:  # snapshot once so a stateful result cannot change between arms
        raw = _copy(raw) or {}
    return SharedBase(manifest.sha256, prober_id, raw, attempts)


# --- context handed to the proposer ---------------------------------------------------------


@dataclass(frozen=True)
class SearchContext:
    """What a proposer may see: position and incumbent, never policy, plan or scores of others."""

    scope: str
    round: int
    slot: int
    attempt: int
    incumbent_sha256: str
    incumbent_score: int
    incumbent_changes: Mapping[str, bytes]


# --- stage ledger ---------------------------------------------------------------------------


def reconcile_stages(stages: Sequence[Mapping[str, Any]], reservation: Mapping[str, int]) -> dict:
    """Adapted ledger identity: unique ids, and charged attempts within the reservation."""
    ids = [s["id"] for s in stages]
    _require(len(set(ids)) == len(ids), "ledger-identity")
    proposals = sum(1 for s in stages if s["kind"] == "propose")
    probes = sum(1 for s in stages if s["kind"] == "probe" and s["charged"])
    base = sum(1 for s in stages if s["kind"] == "probe" and s["scope"] == "base" and s["charged"])
    spent = probes - base
    _require(proposals <= reservation["proposalAttempts"]
             and spent <= reservation["probeAttempts"]
             and base <= reservation["baseProbeAttempts"], "ledger-identity")
    return {"proposalAttempts": proposals, "probeAttempts": spent, "baseProbeAttempts": base,
            "cachedProbes": sum(1 for s in stages if s["kind"] == "probe" and s["cached"]),
            "unusedProposalAttempts": reservation["proposalAttempts"] - proposals,
            "unusedProbeAttempts": reservation["probeAttempts"] - spent}


class _Search:
    """Mutable bookkeeping for one search; never exposed to callbacks."""

    def __init__(self, manifest: HarnessManifest, policy: SelectionPolicy, plan: SearchPlan,
                 cache: SearchCache | None, cancelled: Callable[[], bool] | None):
        self.manifest, self.policy, self.plan = manifest, policy, plan
        self.cache, self.cancel_check = cache, cancelled
        self.stages: list[dict] = []
        self.nodes: list[dict] = []
        self.seen: set[str] = {manifest.data["base"]["sha256"]}
        self.changes: dict[str, dict] = {}        # node id -> accumulated changes
        self.losses: set[str] = set()
        self.stopped: str | None = None

    def cancelled(self) -> bool:
        if self.cancel_check is None:
            return False
        try:
            return bool(self.cancel_check())
        except Exception:  # fail closed: an unreadable cancel signal stops the search
            self.stopped = "cancel-check-failed"
            return True

    def stage(self, kind: str, **fields: Any) -> dict:
        row = {"id": f"s{len(self.stages) + 1}", "kind": kind, "round": None, "slot": None,
               "scope": None, "attempt": 1, "nodeId": None, "status": None, "reason": None,
               "cached": False, "charged": True, **fields}
        self.stages.append(row)
        return row

    def node(self, **fields: Any) -> dict:
        row = {"id": f"n{len(self.nodes) + 1}", "scope": None, "round": None, "slot": None,
               "candidateSha256": None, "parent": "base", "parents": [], "lineage": ["base"],
               "status": None, "reason": None, "score": None, "deltaMicros": None,
               "regressed": None, "observationSha256": None, "floorScore": None,
               "eligible": None, **fields}
        self.nodes.append(row)
        return row


def _scope_for(slot: int) -> str:
    return SCOPES[(slot - 1) % len(SCOPES)]


def _obtain(state: _Search, propose: Callable[[SearchContext], Any], rnd: int, slot: int,
            incumbent: dict) -> tuple[str, dict | None, str | None]:
    """Ask for one proposal with separate invalid/transport retries.

    Returns (outcome, merged_changes, candidate): outcome is ``ok``, ``abstained``,
    ``rejected``, ``failed`` or ``cancelled``.
    """
    plan, scope = state.plan, _scope_for(slot)
    invalid = transport = 0
    last = "rejected"
    while invalid <= plan.proposal_retries and transport <= plan.transport_retries:
        if state.cancelled():
            return "cancelled", None, None
        attempt = invalid + transport + 1
        ctx = SearchContext(scope, rnd, slot, attempt, incumbent["candidateSha256"],
                            incumbent["score"], MappingProxyType(dict(incumbent["changes"])))
        try:
            proposed = propose(ctx)
        except Exception:  # untrusted proposer: surface a fixed reason only
            state.stage("propose", round=rnd, slot=slot, scope=scope, attempt=attempt,
                        status="failed", reason="proposer-failed")
            transport += 1
            last = "failed"
            continue
        if proposed is None:
            state.stage("propose", round=rnd, slot=slot, scope=scope, attempt=attempt,
                        status="abstained")
            return "abstained", None, None
        changes, reason = _validate_proposal(proposed, scope, state.manifest)
        merged, candidate = None, None
        if changes is not None:
            merged = {**incumbent["changes"], **changes}  # the proposal refines the incumbent
            candidate, reason = _candidate_hash(state.manifest, merged)
            if candidate is None:
                merged = None
            elif candidate in state.seen:
                merged, candidate, reason = None, None, "duplicate-candidate"
        if merged is None:
            state.stage("propose", round=rnd, slot=slot, scope=scope, attempt=attempt,
                        status="rejected", reason=reason)
            invalid += 1
            last = "rejected"
            continue
        state.seen.add(candidate)
        state.stage("propose", round=rnd, slot=slot, scope=scope, attempt=attempt, status="valid")
        return "ok", merged, candidate
    return last, None, None


def _probe_node(state: _Search, probe: Callable[[ProbeRequest], Any], node: dict,
                changes: Mapping[str, bytes]) -> None:
    """Probe one node with transport retries; the cache is consulted first."""
    plan, scope = state.plan, node["scope"]
    key = _cache_key(state.manifest, state.policy.sha256, plan.prober_id, scope,
                     node["candidateSha256"])
    hit = state.cache.get(key) if state.cache is not None else None
    if hit is not None:
        state.stage("probe", round=node["round"], slot=node["slot"], scope=scope,
                    nodeId=node["id"], status="scored", cached=True, charged=False)
        _settle(node, hit)
        return
    request = ProbeRequest(scope, node["candidateSha256"], MappingProxyType(dict(changes)))
    for attempt in range(1, plan.transport_retries + 2):
        try:
            raw = probe(request)
        except Exception:  # untrusted prober: surface a fixed reason only
            raw = None
        failed = raw is None
        outcome = {"status": "missing", "reason": "probe-failed"} if failed else _outcome(raw)
        state.stage("probe", round=node["round"], slot=node["slot"], scope=scope, attempt=attempt,
                    nodeId=node["id"], status="failed" if failed else outcome["status"],
                    reason=outcome["reason"])
        if not failed:
            break
    if state.cache is not None:
        state.cache.put(key, outcome)
    _settle(node, outcome)


def _settle(node: dict, outcome: Mapping[str, Any]) -> None:
    node["status"], node["reason"] = outcome["status"], outcome["reason"]
    node["score"] = outcome.get("score")
    node["observationSha256"] = outcome.get("observationSha256")


def _new_node(state: _Search, scope: str, rnd: int, slot: int, candidate: str, parents: list[dict],
              changes: dict, floor: int) -> dict:
    node = state.node(scope=scope, round=rnd, slot=slot, candidateSha256=candidate, floorScore=floor,
                      parent=parents[0]["id"] if parents else "base",
                      parents=[p["id"] for p in parents],
                      lineage=["base"] + sorted(
                          {i for p in parents for i in p["lineage"][1:]} | {p["id"] for p in parents},
                          key=lambda i: int(i[1:])))
    state.changes[node["id"]] = changes
    return node


def _beats(node: dict | None, floor: int, margin: int) -> bool:
    return node is not None and node["status"] == "scored" and node["score"] - floor >= margin


def _round_winner(nodes: list[dict], floor: int, margin: int) -> dict | None:
    scored = [n for n in nodes if _beats(n, floor, margin)]
    if not scored:
        return None
    best = max(n["score"] for n in scored)
    top = [n for n in scored if n["score"] == best]
    return top[0] if len(top) == 1 else None      # a tied top never silently advances


def _best_per_scope(nodes: list[dict], floor: int, margin: int) -> dict[str, dict]:
    """Highest-scoring improving node per scope; the lowest slot wins a tie."""
    best: dict[str, dict] = {}
    for node in nodes:
        if _beats(node, floor, margin) and (
                node["scope"] not in best or node["score"] > best[node["scope"]]["score"]):
            best[node["scope"]] = node
    return best


def _expand_round(state: _Search, propose: Callable, probe: Callable, rnd: int,
                  incumbent: dict, counters: dict) -> tuple[list[dict], bool]:
    plan, margin = state.plan, state.policy.margin_micros
    nodes: list[dict] = []
    for slot in range(1, plan.width + 1):
        outcome, merged, candidate = _obtain(state, propose, rnd, slot, incumbent)
        if outcome == "cancelled":
            return nodes, True
        if outcome == "abstained":
            counters["abstained"] += 1
            continue
        if merged is None:
            counters["unfilled"] += 1
            continue
        if state.cancelled():
            return nodes, True
        parents = [] if incumbent["id"] == "base" else [incumbent["node"]]
        node = _new_node(state, _scope_for(slot), rnd, slot, candidate, parents, merged,
                         incumbent["score"])
        _probe_node(state, probe, node, merged)
        nodes.append(node)
    scored = _best_per_scope(nodes, incumbent["score"], margin)
    if plan.compose and plan.width >= 2 and len(scored) == len(SCOPES):
        merged, reason = _compose(state.manifest, state.changes[scored["general"]["id"]],
                                  state.changes[scored["task"]["id"]])
        candidate = None
        if merged is not None:
            candidate, reason = _candidate_hash(state.manifest, merged)
        if candidate is None:
            state.losses.add(reason)
        elif candidate in state.seen:
            state.losses.add("composition-duplicate")
        elif state.cancelled():
            return nodes, True
        else:
            state.seen.add(candidate)
            node = _new_node(state, "composed", rnd, plan.width + 1, candidate,
                             [scored["general"], scored["task"]], merged, incumbent["score"])
            _probe_node(state, probe, node, merged)
            nodes.append(node)
    return nodes, False


def _shared_outcome(shared: SharedBase | None, manifest: HarnessManifest, prober_id: str,
                    probe: Callable, retries: int) -> tuple[Any, int, bool]:
    if shared is None:
        own = probe_base(manifest, prober_id=prober_id, probe=probe, retries=retries)
        return own.raw, own.attempts, False
    _require(isinstance(shared, SharedBase) and shared.manifest_sha256 == manifest.sha256
             and shared.prober_id == prober_id, "base-identity-mismatch")
    _require(_int(shared.attempts, 1, 1 + MAX_RETRIES), "invalid-shared-base")
    return shared.raw, shared.attempts, True


@dataclass(frozen=True)
class _Record:
    """Immutable advisory record; ``sha256`` binds its canonical bytes."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    @property
    def executionAuthorization(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return thaw(self.data)


class SearchResult(_Record):
    """Immutable advisory search result."""


def run_search(manifest: HarnessManifest, policy: SelectionPolicy, plan: SearchPlan, *,
               propose: Callable[[SearchContext], Any], probe: Callable[[ProbeRequest], Any],
               cache: SearchCache | None = None, shared_base: SharedBase | None = None,
               cancelled: Callable[[], bool] | None = None) -> SearchResult:
    """Run a bounded depth-by-width search and select candidate, keep-base, inconclusive,
    refused or cancelled under the frozen policy. Invalid arguments raise ``SearchError``."""
    _require(isinstance(manifest, HarnessManifest) and isinstance(policy, SelectionPolicy)
             and isinstance(plan, SearchPlan) and callable(propose) and callable(probe)
             and (cache is None or isinstance(cache, SearchCache))
             and (cancelled is None or callable(cancelled)))
    policy = parse_policy(policy.canonical_bytes, manifest=manifest)
    plan = parse_plan(plan.canonical_bytes, manifest=manifest, policy=policy)
    state = _Search(manifest, policy, plan, cache, cancelled)
    margin, reservation = policy.margin_micros, plan.reservation
    base_hash = manifest.data["base"]["sha256"]

    raw, attempts, shared = _shared_outcome(shared_base, manifest, plan.prober_id, probe,
                                            plan.transport_retries)
    base = _outcome(raw)
    for attempt in range(1, attempts + 1):
        last = attempt == attempts
        state.stage("probe", scope="base", attempt=attempt, nodeId="base", charged=not shared,
                    status=base["status"] if last else "failed",
                    reason=base["reason"] if last else "probe-failed")

    rounds: list[dict] = []
    counters = {"abstained": 0, "unfilled": 0}
    if base["status"] == "refused":
        decision, reasons, chosen, stop = "refused", ["base-refused"], None, "base-refused"
    elif base["status"] != "scored":
        decision, reasons, chosen, stop = "inconclusive", ["base-unscored"], None, "base-unscored"
    else:
        incumbent = {"id": "base", "node": None, "candidateSha256": base_hash,
                     "score": base["score"], "changes": {}}
        stop = None
        cancelled_now = False
        for rnd in range(1, plan.depth + 1):
            if stop is not None:
                rounds.append({"round": rnd, "status": "not-run", "reason": stop})
                continue
            if state.cancelled():
                cancelled_now = True
                stop = state.stopped or "cancelled"
                rounds.append({"round": rnd, "status": "not-run", "reason": stop})
                continue
            nodes, cancelled_now = _expand_round(state, propose, probe, rnd, incumbent, counters)
            winner = _round_winner(nodes, incumbent["score"], margin)
            rounds.append({"round": rnd, "status": "cancelled" if cancelled_now else "ran",
                           "reason": None, "nodes": [n["id"] for n in nodes],
                           "advancedTo": winner["id"] if winner and not cancelled_now else None})
            if cancelled_now:
                stop = state.stopped or "cancelled"
            elif winner is not None:
                incumbent = {"id": winner["id"], "node": winner,
                             "candidateSha256": winner["candidateSha256"],
                             "score": winner["score"], "changes": state.changes[winner["id"]]}
            elif plan.stop_on_plateau:
                stop = "plateau"
        every_slot_abstained = not state.nodes and counters["abstained"] > 0 \
            and not counters["unfilled"]
        for node in state.nodes:  # deltas and eligibility for every node, selected or not
            if node["score"] is not None:
                node["deltaMicros"] = node["score"] - base["score"]
                node["regressed"] = node["deltaMicros"] < 0
            # a scored node that did not beat the incumbent it refined by the margin stays
            # on record but cannot be chosen: depth must earn each step
            node["eligible"] = node["status"] != "scored" \
                or node["score"] - node["floorScore"] >= margin
        decision, reasons, chosen = _decide(
            [n for n in state.nodes if n["eligible"]], base, margin,
            len(SCOPES) if every_slot_abstained else 0)
        if reasons == ["no-valid-candidate"] and any(n["status"] == "scored" for n in state.nodes):
            reasons = ["no-candidate-beats-base"]
        if cancelled_now:  # partial work is evidence, never a selection
            decision, reasons, chosen = "cancelled", [stop], None
    if not rounds:  # the base was unusable: every reserved round is accounted as not run
        rounds = [{"round": r, "status": "not-run", "reason": stop}
                  for r in range(1, plan.depth + 1)]

    ledger = reconcile_stages(state.stages, reservation)
    record = {
        "format": RESULT_FORMAT, "manifestSha256": manifest.sha256, "policySha256": policy.sha256,
        "planSha256": plan.sha256, "baseSha256": base_hash, "marginMicros": margin,
        "decision": decision, "reasons": reasons, "chosenCandidateSha256": chosen,
        "stopReason": stop, "rounds": rounds, "nodes": state.nodes, "stages": state.stages,
        "reservation": reservation, "ledger": ledger,
        "counts": {"abstained": counters["abstained"], "unfilled": counters["unfilled"],
                   "sharedBase": shared, "cacheEntries": len(cache) if cache is not None else 0},
        "shape": _shape(plan), "losses": sorted(state.losses), "admission": ADMISSION,
        "concurrency": "serial-simulated", "delegation": "none", "provenance": _PROVENANCE,
        "executionAuthorization": False}
    return SearchResult(freeze(record), canonical(record))


def _shape(plan: SearchPlan) -> dict:
    above = plan.depth > CONTRACT_DEPTH or plan.width > CONTRACT_WIDTH
    return {"depth": plan.depth, "width": plan.width, "compose": plan.compose,
            "contractDepth": CONTRACT_DEPTH, "contractWidth": CONTRACT_WIDTH,
            "aboveContractCeiling": above, "amendmentRequired": above}


# --- equal-budget comparison --------------------------------------------------------------------


def _plan_wire(name: str, policy: SelectionPolicy, prober_id: str, *, depth: int, width: int,
               compose: bool, stop: bool = False, **over: Any) -> bytes:
    wire = {"format": PLAN_FORMAT, "planId": name, "proberId": prober_id,
            "policySha256": policy.sha256, "depth": depth, "width": width, "compose": compose,
            "stopOnPlateau": stop, "proposalRetries": 0, "transportRetries": 0,
            "concurrency": "serial", **over}
    return canonical(wire)


def _arm_shapes(budget: int) -> dict[str, dict]:
    shapes = {"static": {"depth": 1, "width": budget, "compose": False},
              "sequential": {"depth": budget, "width": 1, "compose": False}}
    if budget >= 3:  # composition needs two improving scopes: budget = width + 1 probes
        shapes["parallel"] = {"depth": 1, "width": budget - 1, "compose": True}
    return shapes


def _q(value: Fraction) -> int | str:
    return value.numerator if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _gain(nodes: Sequence[Mapping], chosen: str | None) -> tuple[int, int | None]:
    best = max((n["deltaMicros"] for n in nodes if n["deltaMicros"] is not None), default=None)
    pick = next((n["deltaMicros"] for n in nodes if chosen and n["candidateSha256"] == chosen), 0)
    return pick, best


def _search_arm(name: str, result: SearchResult, budget: int) -> dict:
    wire = result.to_dict()
    gain, best = _gain(wire["nodes"], wire["chosenCandidateSha256"])
    ran = [r for r in wire["rounds"] if r["status"] == "ran"]
    peak = max((sum(1 for n in wire["nodes"] if n["round"] == r["round"] and n["scope"] != "composed")
                for r in ran), default=0)
    sequential = len(ran) + sum(1 for n in wire["nodes"] if n["scope"] == "composed")
    return _arm_row(name, wire["decision"], wire["reasons"], wire["chosenCandidateSha256"], gain,
                    best, wire["ledger"]["probeAttempts"], wire["ledger"]["proposalAttempts"],
                    wire["ledger"]["cachedProbes"], sequential, peak, budget,
                    wire["shape"], result.sha256)


def _arm_row(name: str, decision: str, reasons: list, chosen: str | None, gain: int,
             best: int | None, probes: int, proposals: int, cached: int, depth_cost: int,
             width_cost: int, budget: int, shape: Mapping, result_sha256: str | None) -> dict:
    return {"arm": name, "decision": decision, "reasons": reasons,
            "chosenCandidateSha256": chosen, "gainMicros": gain, "bestObservedGainMicros": best,
            "executedProbes": probes, "proposalAttempts": proposals, "cachedProbes": cached,
            "axes": {"depthCost": depth_cost, "widthCost": width_cost,
                     "stageCount": probes + proposals},
            "probeBudget": budget, "underspent": probes < budget, "overspent": probes > budget,
            "shape": dict(shape), "resultSha256": result_sha256}


def _one_round_arm(manifest: HarnessManifest, policy: SelectionPolicy, shared: SharedBase,
                   propose: Callable, probe: Callable, budget: int) -> dict:
    base_hash = manifest.data["base"]["sha256"]
    base_score = _outcome(shared.raw)["score"]
    spent = {"real": 0, "proposals": 0}

    def propose_scope(scope: str) -> Any:
        spent["proposals"] += 1
        return propose(SearchContext(scope, 1, SCOPES.index(scope) + 1, 1, base_hash, base_score,
                                     MappingProxyType({})))

    def probe_with_shared_base(request: ProbeRequest) -> Any:
        if request.scope == "base":
            return shared.raw
        if spent["real"] >= budget:  # equal budget: the prober is never called past the cap
            raise SearchError("budget-exhausted")  # becomes a missing, probe-failed attempt
        spent["real"] += 1
        return probe(request)

    decision = run_round(manifest, policy, propose=propose_scope, probe=probe_with_shared_base)
    wire = decision.to_dict()
    rows = [a for a in wire["attempts"] if a["scope"] != "base"]
    round_base = next(a["score"] for a in wire["attempts"] if a["scope"] == "base")
    chosen = wire["chosenCandidateSha256"]
    gain = next((a["score"] - round_base for a in rows if chosen and a["candidateSha256"] == chosen), 0)
    scored = [a["deltaMicros"] for a in rows if a["status"] == "scored"]
    probes = spent["real"]  # the shared base is not this arm's spend
    width = min(probes, len(SCOPES))  # probes run in order: general, task, then composed
    composed = probes - width
    return _arm_row("one-round", wire["decision"], wire["reasons"], chosen, gain,
                    max(scored) if scored else None, probes, spent["proposals"], 0, 1 + composed, width,
                    budget, {"depth": 1, "width": len(SCOPES), "compose": True}, decision.sha256)


def _marginal(arms: list[dict]) -> list[dict]:
    ordered = sorted(arms, key=lambda a: (a["executedProbes"], a["arm"]))
    rows = []
    for earlier, later in zip(ordered, ordered[1:]):
        extra_probes = later["executedProbes"] - earlier["executedProbes"]
        extra_gain = later["gainMicros"] - earlier["gainMicros"]
        if extra_probes == 0:
            verdict, rate = "same-cost", None
        else:
            rate = _q(Fraction(extra_gain, extra_probes))
            verdict = "gain" if extra_gain > 0 else "loss" if extra_gain < 0 else "no-marginal-gain"
        rows.append({"from": earlier["arm"], "to": later["arm"], "extraProbes": extra_probes,
                     "extraGainMicros": extra_gain, "gainPerExtraProbeMicros": rate,
                     "verdict": verdict})
    return rows


class ComparisonRecord(_Record):
    """Immutable equal-budget comparison."""


def compare_arms(manifest: HarnessManifest, policy: SelectionPolicy, *, probe_budget: int,
                 prober_id: str, propose: Callable[[SearchContext], Any],
                 probe: Callable[[ProbeRequest], Any]) -> ComparisonRecord:
    """Run keep-base, one-round, static, sequential and parallel arms under one probe budget.

    The base is probed once and shared; each arm has its own empty cache so reuse cannot
    make one arm cheaper. Quality is reported per arm and as marginal gain per extra probe
    on both cost axes; search volume is never scored. Arms that cannot fit the budget are
    listed under ``omitted`` with a reason instead of being silently dropped.
    """
    _require(isinstance(manifest, HarnessManifest) and isinstance(policy, SelectionPolicy)
             and callable(propose) and callable(probe) and _int(probe_budget, 1, MAX_BUDGET))
    policy = parse_policy(policy.canonical_bytes, manifest=manifest)
    shared = probe_base(manifest, prober_id=prober_id, probe=probe)
    base = _outcome(shared.raw)
    arms = [_arm_row("keep-base", "keep-base", ["no-search"], None, 0, None, 0, 0, 0, 0, 0,
                     probe_budget, {"depth": 0, "width": 0, "compose": False}, None)]
    omitted: list[dict] = []
    if base["status"] == "scored":
        arms.append(_one_round_arm(manifest, policy, shared, propose, probe, probe_budget))
        for name, shape in _arm_shapes(probe_budget).items():
            plan = parse_plan(_plan_wire(name, policy, prober_id, **shape), manifest=manifest,
                              policy=policy)
            result = run_search(manifest, policy, plan, propose=propose, probe=probe,
                                cache=SearchCache(), shared_base=shared)
            arms.append(_search_arm(name, result, probe_budget))
        if probe_budget < 3:
            omitted.append({"arm": "parallel", "reason": "budget-too-small-for-composition"})
    else:
        omitted.append({"arm": "all-search-arms", "reason": f"base-{base['status']}"})
    no_gain = sorted(a["arm"] for a in arms
                     if a["executedProbes"] > 0 and a["gainMicros"] <= 0)
    record = {
        "format": COMPARISON_FORMAT, "manifestSha256": manifest.sha256,
        "policySha256": policy.sha256, "proberId": prober_id, "probeBudget": probe_budget,
        "base": {"status": base["status"], "score": base.get("score"),
                 "sharedAttempts": shared.attempts},
        "arms": sorted(arms, key=lambda a: (a["executedProbes"], a["arm"])),
        "omitted": omitted, "marginal": _marginal(arms), "spentWithoutGain": no_gain,
        "volumeScored": False, "evidence": "synthetic-offline-doubles",
        "utilityClaim": False, "concurrency": "serial-simulated", "admission": ADMISSION,
        "provenance": _PROVENANCE, "executionAuthorization": False}
    return ComparisonRecord(freeze(record), canonical(record))
