# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T006 bounded delegated roles and interaction-aware orchestration policy.

Offline policy layer for component class C8 under the frozen capability profile
contract (specs/050-braid-harness-adaptation/contracts/interface.md). It binds, per
role, bounded context (a subset of a trusted C8 ``ComponentProfile`` inventory), an
exclusive write ownership set, declared dependencies, an effect ceiling (E0 to E2),
an allowlisted tool scope (T004) and an output schema that defines the handoff.

Delegation is **blocked from the start** (no containment qualification): every plan
keeps admission ``blocked`` with ``no-containment-qualification``, ``delegation`` is
``none``, nothing is enabled and ``executionAuthorization`` stays false. ``run_plan``
only drives caller-supplied deterministic in-process doubles, serially, so a result
is labelled ``simulated``; it starts no process, opens no network connection, reads no
file and spawns no agent. Provider-native delegation needs its own qualified profile.

Interaction awareness reuses ``analysis.analyze`` (exact-resource footprints) instead
of a second analyzer: roles are expressed as declared-only AIM records. Any pair that
the analyzer cannot show ``ordered`` or ``independent-candidate`` refuses. An
independent candidate is advice only: width stays 1 (contract section 6), the
execution order is the serial reference order, and role text never grants
concurrency or permissions. Handlers are trusted test doubles; they are not
sandboxed, and enforced containment is the SPEC-048/T008 qualification.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
import re
from typing import Any, NoReturn

from .analysis import InvalidAnalysis, analyze
from .harness_components import (
    EFFECTS, ComponentProfile, ProfileError, _hash, _keys, _parse, _require)
from .harness_tools import (
    MAX_READS, MAX_TOOLS, MAX_WRITE_FILE, MAX_WRITES, WRITE_ROOT,
    WRITE_SUFFIXES, ToolAllowlist, ToolResult, _schema, _size, _sorted_unique, _tool_path, _typed,
    run_tool)
from .system_one import canonical, digest, freeze, thaw

_MINT = object()

SPEC_FORMAT = "braid-harness-orchestration-spec/v0.1"
FORMAT = "braid-harness-orchestration/v0.1"
HANDOFF_FORMAT = "braid-harness-handoff/v0.1"
ADMISSION = {"state": "blocked", "blocker": "no-containment-qualification"}
RANK = {"E0": 0, "E1": 1, "E2": 2}
MAX_ROLES = 8
MAX_CONTEXT_ENTRIES = 16          # contract section 6 laboratory inventory
MAX_CONTEXT_BYTES = 128 * 1024
MAX_HANDOFF_BYTES = 64 * 1024     # contract section 6 stage output
MAX_ARTIFACT_BYTES = 256 * 1024
_SPEC_KEYS = {"format", "planId", "profileSha256", "roles", "executionAuthorization"}
_ROLE_KEYS = {"roleId", "context", "ownership", "reads", "dependencies", "effectClass",
              "tools", "output"}
_PLAN_KEYS = {"format", "spec", "inputSha256", "allowlistSha256", "order", "analysis",
              "parallelism", "admission", "delegation", "executionAuthorization"}
_HANDOFF_KEYS = {"format", "planSha256", "roleId", "dependencies", "outputs",
                 "outputSha256", "artifacts", "executionAuthorization"}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")


def _id(value: Any) -> str:
    _require(type(value) is str and _ID.fullmatch(value) is not None, "invalid-role-id")
    return value


def _ids(value: Any, ceiling: int, reason: str = "invalid-role") -> list[str]:
    _require(type(value) is list and len(value) <= ceiling, reason)
    for item in value:
        _id(item)
    _sorted_unique(value, reason)
    return value


def _paths(value: Any, ceiling: int) -> list[str]:
    _require(type(value) is list and len(value) <= ceiling, "inventory-budget-exceeded")
    for item in value:
        _tool_path(item)
    _sorted_unique(value)
    return value


def _owned(paths: Any) -> list[str]:
    paths = _paths(paths, MAX_WRITES)
    for path in paths:
        parts = path.split("/")
        _require(len(parts) >= 2 and parts[0] == WRITE_ROOT and path.endswith(WRITE_SUFFIXES),
                 "path-outside-surface")
    return paths


def _context(rows: Any, profile: ComponentProfile) -> list[str]:
    _require(type(rows) is list and len(rows) <= MAX_CONTEXT_ENTRIES, "inventory-budget-exceeded")
    inventory = {r["path"]: r for r in profile.data["inventory"]}
    for row in rows:
        _keys(row, {"path", "sha256", "sizeBytes"})
        _hash(row["sha256"])
        _require(type(row["path"]) is str and row["path"] in inventory and dict(inventory[row["path"]]) == row,
                 "context-outside-profile")
    paths = [r["path"] for r in rows]
    _sorted_unique(paths)
    _require(sum(r["sizeBytes"] for r in rows) <= MAX_CONTEXT_BYTES, "inventory-budget-exceeded")
    return paths


def _role(role: Any, profile: ComponentProfile) -> None:
    _keys(role, _ROLE_KEYS)
    _id(role["roleId"])
    context = _context(role["context"], profile)
    owned, reads = _owned(role["ownership"]), _paths(role["reads"], MAX_READS)
    _require(not (set(owned) | set(context)) & set(reads) and not set(owned) & set(context),
             "path-alias")
    _ids(role["dependencies"], MAX_ROLES - 1, "invalid-dependencies")
    effect = role["effectClass"]
    _require(effect in EFFECTS, "invalid-effect")
    _require(effect != "E5", "excluded-effect")
    _require(effect in RANK, "effect-blocked")
    tools = _ids(role["tools"], MAX_TOOLS)
    fits = {"E0": not (context or owned or reads or tools), "E1": bool(context or reads) and not owned,
            "E2": bool(owned)}
    _require(fits[effect], "undeclared-effect")
    _schema(role["output"])
    _require(role["output"], "invalid-schema")


def _tool_scope(role: dict, allowlist: ToolAllowlist | None) -> None:
    readable = {r["path"] for r in role["context"]} | set(role["reads"])
    for tool_id in role["tools"]:
        _require(allowlist is not None and tool_id in allowlist.contracts, "tool-not-allowlisted")
        data = allowlist.contracts[tool_id].data
        _require(data["admission"]["state"] == "implemented", "effect-blocked")
        _require(set(data["writes"]) <= set(role["ownership"]) and
                 {r["path"] for r in data["reads"]} <= readable, "tool-scope-escalation")


def _aim(role: dict) -> dict:
    effects = ([{"kind": "read", "resource": r["path"]} for r in role["context"]] +
               [{"kind": "read", "resource": p} for p in role["reads"]] +
               [{"kind": "write", "resource": p} for p in role["ownership"]])
    return {
        "aimVersion": "0.2.0-draft", "instanceId": role["roleId"],
        "attemptId": role["roleId"] + "#1",
        "definition": {"id": role["roleId"], "digest": "sha256:" + digest(role)},
        "inputDigest": "sha256:" + digest(role["context"]),
        "dependencies": list(role["dependencies"]), "readVersions": {},
        "effects": {"declared": effects, "inferred": [], "observed": [],
                    "coverage": {"status": "complete", "domain": "role-scope",
                                 "method": "declared"}},
        "evidence": [{"method": "declared"}]}


def _interactions(roles: list[dict]) -> tuple[dict, list[str]]:
    try:
        report = analyze([_aim(r) for r in roles])
    except InvalidAnalysis as exc:
        raise ProfileError({"cyclic-dependencies": "dependency-cycle",
                            "unknown-dependency": "unknown-dependency",
                            "self-dependency": "dependency-cycle"}.get(
                                exc.code, "invalid-dependencies")) from None
    rows = [{"left": i["left"], "right": i["right"], "classification": i["classification"]}
            for i in report["interactions"]]
    _require(all(r["classification"] in ("ordered", "independent-candidate") for r in rows),
             "unordered-conflict")
    done, order = set(), []
    deps = {r["roleId"]: set(r["dependencies"]) for r in roles}
    while len(order) < len(roles):
        step = next(rid for rid in sorted(deps) if rid not in done and deps[rid] <= done)
        order.append(step)
        done.add(step)
    return {"analysisId": report["analysisId"], "interactions": rows}, order


def _ancestors(roles: list[dict]) -> dict[str, set[str]]:
    direct = {r["roleId"]: set(r["dependencies"]) for r in roles}
    result = {rid: set(deps) for rid, deps in direct.items()}
    for _ in roles:
        for deps in result.values():
            deps.update(a for d in list(deps) for a in result[d])
    return result


def _build(spec: dict, input_sha: str, profile: ComponentProfile,
           allowlist: ToolAllowlist | None) -> dict:
    _keys(spec, _SPEC_KEYS)
    _require(spec["format"] == SPEC_FORMAT, "unsupported-version")
    _require(spec["executionAuthorization"] is False, "unsupported-profile")
    _id(spec["planId"])
    _require(profile.data["componentClass"] == "C8" and
             profile.data["admission"]["state"] == "blocked", "profile-mismatch")
    _hash(spec["profileSha256"])
    _require(spec["profileSha256"] == profile.sha256, "profile-drift")
    roles = spec["roles"]
    _require(type(roles) is list and 1 <= len(roles) <= MAX_ROLES, "invalid-role")
    for role in roles:
        _role(role, profile)
    ids = [r["roleId"] for r in roles]
    _sorted_unique(ids, "duplicate-or-unordered-inventory")
    owners: dict[str, str] = {}
    for role in roles:
        for path in role["ownership"]:
            _require(path.casefold() not in owners, "ownership-overlap")
            owners[path.casefold()] = role["roleId"]
    spellings: dict[str, set[str]] = {}
    for role in roles:
        for path in [r["path"] for r in role["context"]] + role["reads"] + role["ownership"]:
            spellings.setdefault(path.casefold(), set()).add(path)
    _require(all(len(v) == 1 for v in spellings.values()), "path-alias")
    owner_of = {p: r["roleId"] for r in roles for p in r["ownership"]}
    for role in roles:
        own_context = {r["path"] for r in role["context"]}
        _require(all(p in owner_of or p in own_context for p in role["reads"]),
                 "read-outside-scope")
        _tool_scope(role, allowlist)
    uses_tools = any(r["tools"] for r in roles)
    analysis, order = _interactions(roles)
    ancestors = _ancestors(roles)
    _require(all(owner_of[p] in ancestors[r["roleId"]] for r in roles for p in r["reads"]
                 if p in owner_of), "read-before-write")
    candidates = [[r["left"], r["right"]] for r in analysis["interactions"]
                  if r["classification"] == "independent-candidate"]
    return {
        "format": FORMAT, "spec": spec, "inputSha256": input_sha,
        "allowlistSha256": allowlist.sha256 if uses_tools else None,
        "order": order, "analysis": analysis,
        "parallelism": {"width": 1, "allowed": False, "advisoryCandidates": candidates},
        "admission": dict(ADMISSION), "delegation": "none", "executionAuthorization": False}


@dataclass(frozen=True)
class OrchestrationPlan:
    """Immutable plan; construction is not independent verification or authority."""

    data: Mapping[str, Any]
    canonical_bytes: bytes
    _mint: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        # Only compile_plan/verify_plan can mint a plan; a hand-built one never runs.
        _require(self._mint is _MINT, "plan-not-compiled")

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    @property
    def order(self) -> tuple[str, ...]:
        return tuple(self.data["order"])

    def role(self, role_id: str) -> Mapping[str, Any]:
        found = next((r for r in self.data["spec"]["roles"] if r["roleId"] == role_id), None)
        _require(found is not None, "unknown-role")
        return found

    def to_dict(self) -> dict:
        return thaw(self.data)


def compile_plan(raw: bytes, *, expected_input_sha256: str, profile: ComponentProfile,
                 allowlist: ToolAllowlist | None = None) -> OrchestrationPlan:
    """Compile one trusted role spec into an immutable, blocked, non-authorizing plan."""
    _hash(expected_input_sha256, "invalid-expected-hash")
    _require(isinstance(profile, ComponentProfile), "profile-mismatch")
    _require(allowlist is None or (isinstance(allowlist, ToolAllowlist) and
                                   canonical(allowlist.data) == allowlist.canonical_bytes),
             "invalid-allowlist")
    spec = _parse(raw)
    _require(digest(spec) == expected_input_sha256, "input-drift")
    plan = _build(spec, expected_input_sha256, profile, allowlist)
    return OrchestrationPlan(freeze(plan), canonical(plan), _MINT)


def verify_plan(raw: bytes, *, expected_sha256: str, profile: ComponentProfile,
                allowlist: ToolAllowlist | None = None) -> OrchestrationPlan:
    """Reparse a plan and recompile its embedded spec; equality is not authority."""
    _hash(expected_sha256, "invalid-expected-hash")
    value = _parse(raw)
    _keys(value, _PLAN_KEYS)
    _require(digest(value) == expected_sha256, "plan-drift")
    spec = value["spec"]
    _require(isinstance(spec, dict), "invalid-profile")
    plan = compile_plan(canonical(spec), expected_input_sha256=digest(spec),
                        profile=profile, allowlist=allowlist)
    _require(plan.canonical_bytes == canonical(value), "plan-drift")
    return plan


def _handoff_body(plan: OrchestrationPlan, role_id: str, value: Any) -> Mapping[str, Any]:
    _keys(value, _HANDOFF_KEYS, "invalid-handoff")
    _require(value["format"] == HANDOFF_FORMAT and value["executionAuthorization"] is False,
             "invalid-handoff")
    _hash(value["planSha256"], "invalid-handoff")
    _require(value["planSha256"] == plan.sha256, "handoff-plan-mismatch")
    _require(value["roleId"] == role_id, "handoff-role-mismatch")
    role = plan.role(role_id)
    _require(type(value["dependencies"]) is dict and
             sorted(value["dependencies"]) == list(role["dependencies"]), "handoff-dependencies")
    for item in value["dependencies"].values():
        _hash(item, "invalid-handoff")
    _typed(role["output"], value["outputs"], "invalid-output", "output-budget-exceeded")
    _hash(value["outputSha256"], "invalid-handoff")
    _require(value["outputSha256"] == digest(value["outputs"]), "handoff-output-mismatch")
    arts = value["artifacts"]
    _require(type(arts) is dict and set(arts) == set(role["ownership"]), "handoff-artifacts")
    for item in arts.values():
        _hash(item, "invalid-handoff")
    _size(value, MAX_HANDOFF_BYTES, "invalid-handoff", "output-budget-exceeded")
    return freeze(value)


def verify_handoff(plan: OrchestrationPlan, role_id: str, raw: bytes, *,
                   expected_sha256: str) -> Mapping[str, Any]:
    """Reparse one handoff against the plan's schema and a trusted full hash."""
    _hash(expected_sha256, "invalid-expected-hash")
    _require(isinstance(plan, OrchestrationPlan) and role_id in plan.order, "unknown-role")
    value = _parse(raw)
    _require(digest(value) == expected_sha256, "handoff-drift")
    return _handoff_body(plan, role_id, value)


class RoleContext:
    """Role-scoped capability handle; closed at teardown, latches scope violations.

    Handlers are trusted doubles: the handle cannot stop a handler from using Python
    facilities directly, and enforced containment is the T008 qualification.
    """

    def __init__(self, role: Mapping[str, Any], files: Mapping[str, bytes],
                 store: Mapping[str, bytes], inputs: Mapping[str, Any], tools: tuple) -> None:
        self._role, self._files, self._store, self._tools = role, files, store, tools
        self._readable = {r["path"]: r for r in role["context"]} | {p: None for p in role["reads"]}
        self._owned = frozenset(role["ownership"])
        self.inputs = inputs
        self._writes: dict[str, bytes] = {}
        self._tool_hashes: dict[str, str] = {}
        self._violation: str | None = None
        self._open = True

    @property
    def writes(self) -> Mapping[str, bytes]:
        return freeze(self._writes)

    @property
    def violation(self) -> str | None:
        return self._violation

    def _refuse(self, reason: str) -> NoReturn:
        self._violation = self._violation or reason
        raise ProfileError(reason)

    def _bytes(self, path: str) -> bytes:
        """Bytes of a readable path: a dependency artifact, else hash-checked context."""
        if path in self._store:
            return self._store[path]
        row, data = self._readable[path], self._files.get(path)
        if type(data) is not bytes or row is None or len(data) != row["sizeBytes"] \
                or sha256(data).hexdigest() != row["sha256"]:
            self._refuse("context-drift")
        return data

    def read(self, path: str) -> bytes:
        if not self._open:
            self._refuse("context-closed")
        if path not in self._readable:
            self._refuse("read-outside-scope")
        return self._bytes(path)

    def write(self, path: str, data: bytes) -> None:
        if not self._open:
            self._refuse("context-closed")
        if path not in self._owned:
            self._refuse("write-outside-ownership")
        if type(data) is not bytes or len(data) > MAX_WRITE_FILE:
            self._refuse("write-budget-exceeded")
        others = sum(len(v) for p, v in self._writes.items() if p != path)
        if others + len(data) > MAX_ARTIFACT_BYTES:
            self._refuse("write-budget-exceeded")
        if path in self._tool_hashes and sha256(data).hexdigest() != self._tool_hashes[path]:
            self._refuse("tool-artifact-mismatch")
        self._writes[path] = data

    def tool(self, tool_id: str, input_value: Mapping[str, Any]) -> ToolResult:
        """Run one in-scope allowlisted helper; its verified artifacts bind later writes."""
        if not self._open:
            self._refuse("context-closed")
        if tool_id not in self._role["tools"]:
            self._refuse("tool-outside-role-scope")
        allowlist, helpers, checkers = self._tools
        paths = [r["path"] for r in allowlist.contracts[tool_id].data["reads"]]
        files = {p: self._bytes(p) for p in paths}
        try:
            result = run_tool(allowlist, tool_id, input_value, helpers=helpers,
                              checkers=checkers, files=files)
        except ProfileError as exc:
            self._refuse(exc.reason)
        self._tool_hashes.update(result.artifacts)
        return result

    def close(self) -> None:
        self._open = False


@dataclass(frozen=True)
class OrchestrationResult:
    """Outcome of a simulated serial run; ``completed`` alone says nothing about authority."""

    plan_sha256: str
    status: str                       # completed | failed | cancelled
    reason: str | None
    failed_role: str | None
    completed: tuple[str, ...]
    skipped: tuple[str, ...]
    handoffs: Mapping[str, bytes]     # roleId -> canonical handoff bytes
    handoff_sha256: Mapping[str, str]
    artifacts: Mapping[str, bytes]
    simulated: bool = True
    delegation: str = "none"
    execution_authorization: bool = False


def _require_fresh(record: Mapping, hashes: Mapping[str, str], store: Mapping[str, bytes]) -> None:
    _require(all(hashes.get(d) == h for d, h in record["dependencies"].items()),
             "stale-handoff")
    for path, item in record["artifacts"].items():
        data = store.get(path)
        _require(data is not None and sha256(data).hexdigest() == item, "stale-handoff")


def _output_failure(role: Mapping, out: Any) -> str | None:
    try:
        _typed(role["output"], out, "invalid-output", "output-budget-exceeded")
        _size(out, MAX_HANDOFF_BYTES, "invalid-output", "output-budget-exceeded")
    except ProfileError as exc:
        return exc.reason
    return None


def _resume_inputs(plan: OrchestrationPlan, handoffs: Any, artifacts: Any) -> tuple[dict, dict]:
    _require(isinstance(handoffs, Mapping) and isinstance(artifacts, Mapping), "invalid-input")
    resume = dict(handoffs)
    _require(set(resume) <= set(plan.order), "unknown-role")
    for item in resume.values():
        _require(type(item) is tuple and len(item) == 2 and type(item[0]) is bytes
                 and type(item[1]) is str, "invalid-input")
    store = dict(artifacts)
    _require(all(type(k) is str and type(v) is bytes for k, v in store.items()),
             "invalid-input")
    _require(set(store) <= {p for r in resume for p in plan.role(r)["ownership"]},
             "stale-handoff")
    _require(all(len(v) <= MAX_WRITE_FILE for v in store.values()) and
             sum(map(len, store.values())) <= MAX_ARTIFACT_BYTES, "write-budget-exceeded")
    return resume, store


def run_plan(plan: OrchestrationPlan, handlers: Mapping[str, Callable],
             checker: Callable, *, files: Mapping[str, bytes],
             allowlist: ToolAllowlist | None = None,
             helpers: Mapping[str, Callable] | None = None,
             checkers: Mapping[str, Callable] | None = None,
             cancel: Callable[[], bool] = lambda: False,
             resume_handoffs: Mapping[str, tuple[bytes, str]] | None = None,
             resume_artifacts: Mapping[str, bytes] | None = None) -> OrchestrationResult:
    """Drive deterministic role doubles serially in the plan's reference order.

    ``handlers[role](context, inputs)`` returns the role's output dict;
    ``checker(outputs_by_role, artifact_sha256_by_path)`` is the serial-reference
    verifier of this run's results (not a second execution) and must be a distinct
    callable returning exactly ``True``. ``cancel`` is polled before each role that
    is not resumed; a cancel after the last role is not observed. A handoff resumed
    from an earlier run is reverified (plan, schema, dependency hashes, artifact
    bytes and budgets) and any stale or forged one refuses; its supplied hash is
    trusted identity, not authenticity. Role failures (including a tool refusal
    surfaced as a handler exception) and a failed reference end the run as
    ``failed``; scope violations raise.
    """
    _require(isinstance(plan, OrchestrationPlan) and
             canonical(plan.data) == plan.canonical_bytes, "plan-drift")
    _require(isinstance(handlers, Mapping) and set(handlers) == set(plan.order) and
             all(callable(h) for h in handlers.values()), "helper-missing")
    _require(callable(checker) and all(checker is not h for h in handlers.values()) and
             callable(cancel), "checker-not-independent")
    _require(isinstance(files, Mapping), "invalid-input")
    _require(plan.data["allowlistSha256"] is None or
             (allowlist is not None and allowlist.sha256 == plan.data["allowlistSha256"]),
             "invalid-allowlist")
    tools = (allowlist, dict(helpers or {}), dict(checkers or {}))
    resume, store = _resume_inputs(plan, resume_handoffs or {}, resume_artifacts or {})
    hashes: dict[str, str] = {}
    raws: dict[str, bytes] = {}
    outputs: dict[str, Any] = {}
    completed: list[str] = []

    def finish(status, reason=None, failed=None):
        skipped = tuple(r for r in plan.order if r not in completed)
        return OrchestrationResult(
            plan.sha256, status, reason, failed, tuple(completed), skipped,
            freeze(raws), freeze(hashes), freeze(store))

    for role_id in plan.order:
        role = plan.role(role_id)
        if role_id in resume:
            raw, expected = resume[role_id]
            record = verify_handoff(plan, role_id, raw, expected_sha256=expected)
            _require_fresh(record, hashes, store)
            hashes[role_id], raws[role_id] = expected, raw
            outputs[role_id] = thaw(record["outputs"])
            completed.append(role_id)
            continue
        try:
            cancelled = bool(cancel())
        except Exception:
            raise ProfileError("cancel-raised") from None
        if cancelled:
            return finish("cancelled", "cancelled")
        inputs = freeze({d: outputs[d] for d in role["dependencies"]})
        context = RoleContext(role, files, store, inputs, tools)
        try:
            out, reason = handlers[role_id](context, inputs), None
        except Exception:
            out, reason = None, "role-failed"
        finally:
            context.close()
        if context.violation is not None:
            raise ProfileError(context.violation)
        reason = reason or _output_failure(role, out)
        if reason is not None:
            return finish("failed", reason, role_id)
        writes = context.writes
        if set(writes) != set(role["ownership"]):
            return finish("failed", "artifact-missing", role_id)
        record = {
            "format": HANDOFF_FORMAT, "planSha256": plan.sha256, "roleId": role_id,
            "dependencies": {d: hashes[d] for d in role["dependencies"]},
            "outputs": out, "outputSha256": digest(out),
            "artifacts": {p: sha256(writes[p]).hexdigest() for p in role["ownership"]},
            "executionAuthorization": False}
        raw = canonical(record)
        _handoff_body(plan, role_id, record)  # self-check, including the record size budget
        raws[role_id], hashes[role_id] = raw, sha256(raw).hexdigest()
        outputs[role_id] = thaw(out)
        store.update(writes)
        completed.append(role_id)
    try:
        verdict = checker(freeze(outputs), freeze({p: sha256(b).hexdigest()
                                                   for p, b in store.items()}))
    except Exception:
        return finish("failed", "checker-raised")
    return finish("completed") if verdict is True else finish("failed", "reference-mismatch")
