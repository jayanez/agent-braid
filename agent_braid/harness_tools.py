# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T004 allowlisted deterministic helper and tool contracts (offline, unqualified).

Immutable, allowlisted tool contracts (``braid-harness-tool/v0.1``) and a
task-local runner for deterministic helpers, under the frozen capability profile
contract (specs/050-braid-harness-adaptation/contracts/interface.md, class C4/C5).
The module starts no process, opens no network connection, reads no file and
issues no grant. Every record keeps ``executionAuthorization`` false.

A contract states typed input/output schemas, a positive read inventory (path,
SHA-256, size), a positive list of new private ``out/`` write destinations, the
declared effect class and a bounded execution contract. The effect class decides
admission here: E0 to E2 are ``implemented`` (offline, doubles only; nothing is
qualified or enabled); E3 (child process) and E4 (network) parse but stay
``blocked`` and ``run_tool`` refuses them; E5 is refused outright. No native
effect exists in this module: it waits for the SPEC-048/T008 verdict and an
adopted E3 effect contract.

Helpers are caller-supplied callables passed per run, never registered globally:
a helper whose tool is not in the verified allowlist is refused, so a new
executable cannot enter by being present. A helper only reaches resources through
a ``ToolContext`` that enforces the declared inventories, effect class, operation
count and deadline, and that is closed at teardown. The context cannot stop a
helper from using Python facilities directly: in-process helpers are trusted test
doubles, and enforced containment is the T008 qualification, not this module.
Wall time is measured on an injected clock and checked at every context call and
at return; an in-process helper cannot be preempted.

Every run needs a checker that is a distinct callable object (identity only, not
proof of independence) and returns exactly ``True`` for the validated input, output
and artifacts. Refusals raised by the context are latched: a helper that swallows one
still fails the run. E2 writes are held in memory and discarded at teardown; no
on-disk destination exists yet. This module decides C5 tool admission itself because
``harness_components.derive_admission`` still lists C5 as owner-task-unimplemented;
the PR records the divergence for the orchestrator to reconcile.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from time import monotonic_ns
from typing import Any
import unicodedata

from .harness_components import (
    EFFECTS, HOST_SUPPORT, PROTECTED_COMPONENTS, ProfileError, _ID, _hash, _keys, _parse,
    _path, _provenance, _require)
from .system_one import canonical, digest, freeze, thaw

FORMAT = "braid-harness-tool/v0.1"
SPEC_FORMAT = "braid-harness-tool-spec/v0.1"
ALLOWLIST_FORMAT = "braid-harness-toolset/v0.1"
POLICIES = {"path": "positive-inventory-v1", "effect": "declared-effect-v1",
            "result": "independent-check-v1"}
TYPES = ("string", "integer", "boolean")
WRITE_ROOT = "out"
WRITE_SUFFIXES = (".md", ".txt", ".json")
# Ceilings reuse the contract section 6 offline values (stage output, context inventory,
# candidate files); maxOps and timeoutMs are T004 choices, recorded in the PR.
CEILINGS = {"maxInputBytes": 16 * 1024, "maxOutputBytes": 64 * 1024, "maxOps": 64,
            "maxWriteBytes": 256 * 1024, "timeoutMs": 10_000}
MAX_FIELDS = 16
MAX_READS = 16
MAX_READ_FILE = 32 * 1024
MAX_READ_TOTAL = 128 * 1024
MAX_WRITES = 32
MAX_WRITE_FILE = 32 * 1024
MAX_STRING = 4096
MAX_INT = 2 ** 31
MAX_GUIDANCE = 1024
MAX_TOOLS = 16
_SPEC_KEYS = {"format", "toolId", "version", "effectClass", "guidance", "input", "output",
              "reads", "writes", "limits", "provenance", "executionAuthorization"}
_CONTRACT_KEYS = _SPEC_KEYS | {"componentClass", "host", "hostSupport", "inputSha256",
                                "policies", "admission"}
_FIELD_KEYS = {"name", "type", "max"}


def _admission(effect_class: str) -> dict:
    """Return the only admission this module can produce."""
    _require(effect_class in EFFECTS, "invalid-effect")
    _require(effect_class != "E5", "excluded-effect")
    if effect_class in ("E3", "E4"):
        return {"state": "blocked", "blocker": "effects-not-adopted"}
    return {"state": "implemented", "blocker": None}


def _sorted_unique(items: list, reason: str = "duplicate-or-unordered-inventory") -> None:
    _require(items == sorted(items) and len(set(items)) == len(items), reason)


def _guidance(value: Any) -> None:
    _require(type(value) is str and len(value.encode("utf-8", "surrogatepass")) <= MAX_GUIDANCE
             and not any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} and c != "\n"
                         for c in value), "invalid-guidance")


def _schema(value: Any) -> None:
    _require(type(value) is list and len(value) <= MAX_FIELDS, "invalid-schema")
    for field in value:
        _keys(field, _FIELD_KEYS, "invalid-schema")
        _require(type(field["name"]) is str and _ID.fullmatch(field["name"]) is not None
                 and field["type"] in TYPES, "invalid-schema")
        bound = field["max"]
        if field["type"] == "boolean":
            _require(bound is None, "invalid-schema")
        else:
            limit = MAX_STRING if field["type"] == "string" else MAX_INT
            _require(type(bound) is int and 0 <= bound <= limit and
                     (field["type"] == "integer" or bound >= 1), "invalid-schema")
    _sorted_unique([f["name"] for f in value], "invalid-schema")


def _tool_path(value: Any) -> str:
    path = _path(value, depth=4)
    parts = path.split("/")
    _require(not any(p.startswith(".") or p.split(".", 1)[0].rstrip(" .").casefold()
                     in PROTECTED_COMPONENTS for p in parts), "protected-component")
    return path


def _reads(value: Any) -> list[str]:
    _require(type(value) is list and len(value) <= MAX_READS, "inventory-budget-exceeded")
    for row in value:
        _keys(row, {"path", "sha256", "sizeBytes"})
        _hash(row["sha256"])
        _require(type(row["sizeBytes"]) is int and 0 <= row["sizeBytes"] <= MAX_READ_FILE,
                 "inventory-budget-exceeded")
        _require(_tool_path(row["path"]).split("/")[0].casefold() != WRITE_ROOT,
                 "path-outside-surface")
    _require(sum(r["sizeBytes"] for r in value) <= MAX_READ_TOTAL, "inventory-budget-exceeded")
    paths = [r["path"] for r in value]
    _sorted_unique(paths)
    return paths


def _writes(value: Any) -> list[str]:
    _require(type(value) is list and len(value) <= MAX_WRITES, "inventory-budget-exceeded")
    for path in value:
        parts = _tool_path(path).split("/")
        _require(len(parts) >= 2 and parts[0] == WRITE_ROOT and path.endswith(WRITE_SUFFIXES),
                 "path-outside-surface")
    _sorted_unique(value)
    return value


def _limits(value: Any) -> None:
    _keys(value, set(CEILINGS), "invalid-limits")
    for name, ceiling in CEILINGS.items():
        low = 0 if name == "maxWriteBytes" else 1
        _require(type(value[name]) is int and low <= value[name] <= ceiling,
                 "limits-exceed-ceiling")


def _body(value: dict) -> None:
    """Validate the fields shared by a spec and a compiled contract."""
    _require(value["executionAuthorization"] is False, "unsupported-profile")
    _require(type(value["toolId"]) is str and _ID.fullmatch(value["toolId"]) is not None,
             "invalid-tool-id")
    # No parent chain exists yet; migration (T011) must define it before version > 1.
    _require(type(value["version"]) is int and value["version"] == 1, "invalid-version")
    effect = value["effectClass"]
    _admission(effect)
    _guidance(value["guidance"])
    _schema(value["input"])
    _schema(value["output"])
    reads, writes = _reads(value["reads"]), _writes(value["writes"])
    _require(len({p.casefold() for p in reads + writes}) == len(reads) + len(writes),
             "path-alias")
    _limits(value["limits"])
    # A declaration may not exceed its effect class (E1 reads, E2 and above also write).
    _require(effect != "E0" or not (reads or writes), "undeclared-effect")
    _require(effect != "E1" or (reads and not writes), "undeclared-effect")
    _require(effect != "E2" or writes, "undeclared-effect")
    _require(not writes or value["limits"]["maxWriteBytes"] > 0, "invalid-limits")
    _provenance(value["provenance"])


@dataclass(frozen=True)
class ToolContract:
    """Immutable parsed tool contract; construction is not independent verification."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    @property
    def tool_id(self) -> str:
        return self.data["toolId"]

    def to_dict(self) -> dict:
        return thaw(self.data)


def parse_contract(raw: bytes) -> ToolContract:
    """Parse strict bounded JSON and revalidate every contract invariant."""
    value = _parse(raw)
    _keys(value, _CONTRACT_KEYS)
    _require(value["format"] == FORMAT, "unsupported-version")
    _require(value["componentClass"] == "C5", "unknown-class")
    _require(value["host"] == "claude", "host-refused")
    _require(canonical(value["hostSupport"]) == canonical(HOST_SUPPORT), "host-build-drift")
    _body(value)
    _hash(value["inputSha256"])
    _require(canonical(value["policies"]) == canonical(POLICIES), "unsupported-profile")
    _require(canonical(value["admission"]) == canonical(_admission(value["effectClass"])),
             "admission-mismatch")
    return ToolContract(freeze(value), canonical(value))


def verify_contract(raw: bytes, *, expected_sha256: str) -> ToolContract:
    """Reparse and compare a trusted full identity; equality is not authority."""
    _hash(expected_sha256, "invalid-expected-hash")
    contract = parse_contract(raw)
    _require(contract.sha256 == expected_sha256, "contract-drift")
    return contract


def compile_contract(raw: bytes, *, expected_input_sha256: str) -> ToolContract:
    """Compile one trusted tool spec into an immutable, non-enabled contract."""
    _hash(expected_input_sha256, "invalid-expected-hash")
    value = _parse(raw)
    _require(sha256(canonical(value)).hexdigest() == expected_input_sha256, "input-drift")
    _keys(value, _SPEC_KEYS)
    _require(value["format"] == SPEC_FORMAT, "unsupported-version")
    _body(value)
    contract = {**value, **{
        "format": FORMAT, "componentClass": "C5", "host": "claude",
        "hostSupport": thaw(HOST_SUPPORT), "inputSha256": expected_input_sha256,
        "policies": dict(POLICIES), "admission": _admission(value["effectClass"])}}
    return parse_contract(canonical(contract))


@dataclass(frozen=True)
class ToolAllowlist:
    """Immutable allowlist bound to the exact verified contracts it names."""

    data: Mapping[str, Any]
    canonical_bytes: bytes
    contracts: Mapping[str, ToolContract]

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()


def _build_allowlist(value: dict, contracts: Sequence[ToolContract]) -> ToolAllowlist:
    by_id = {c.tool_id: c for c in contracts}
    _require(len(by_id) == len(contracts), "duplicate-tool")
    tools = value["tools"]
    _require(type(tools) is list and 1 <= len(tools) <= MAX_TOOLS, "invalid-allowlist")
    for row in tools:
        _keys(row, {"toolId", "contractSha256"}, "invalid-allowlist")
        _hash(row["contractSha256"], "invalid-allowlist")
    _require(all(type(r["toolId"]) is str for r in tools), "invalid-allowlist")
    _sorted_unique([r["toolId"] for r in tools], "invalid-allowlist")
    _require(set(by_id) == {r["toolId"] for r in tools} and all(
        by_id[r["toolId"]].sha256 == r["contractSha256"] for r in tools), "contract-set-mismatch")
    return ToolAllowlist(freeze(value), canonical(value), freeze(by_id))


def compile_allowlist(contracts: Sequence[ToolContract]) -> ToolAllowlist:
    """Build the allowlist record naming exactly these verified contracts."""
    value = {"format": ALLOWLIST_FORMAT, "executionAuthorization": False, "tools": sorted(
        ({"toolId": c.tool_id, "contractSha256": c.sha256} for c in contracts),
        key=lambda row: row["toolId"])}
    return _build_allowlist(value, list(contracts))


def verify_allowlist(raw: bytes, *, expected_sha256: str,
                     contract_raws: Sequence[bytes]) -> ToolAllowlist:
    """Reparse the allowlist and every named contract against trusted identities."""
    _hash(expected_sha256, "invalid-expected-hash")
    value = _parse(raw)
    _keys(value, {"format", "tools", "executionAuthorization"}, "invalid-allowlist")
    _require(value["format"] == ALLOWLIST_FORMAT, "unsupported-version")
    _require(value["executionAuthorization"] is False, "unsupported-profile")
    _require(sha256(canonical(value)).hexdigest() == expected_sha256, "allowlist-drift")
    _require(type(contract_raws) in (list, tuple), "invalid-allowlist")
    return _build_allowlist(value, [parse_contract(item) for item in contract_raws])


class ToolContext:
    """Task-local capability handle; closed at teardown, enforces the contract."""

    def __init__(self, contract: ToolContract, files: Mapping[str, bytes],
                 clock: Callable[[], int]):
        data = contract.data
        self._reads = {row["path"]: row for row in data["reads"]}
        self._writes = frozenset(data["writes"])
        self._effect = data["effectClass"]
        self._limits = data["limits"]
        self._files = files
        self._clock = clock
        self._deadline = clock() + data["limits"]["timeoutMs"] * 1_000_000
        self._ops = 0
        self._written = 0
        self._scratch: dict[str, bytes] = {}
        self._closed = False
        self._violation: str | None = None

    @property
    def violation(self) -> str | None:
        return self._violation

    def _refuse(self, reason: str) -> None:
        if self._violation is None:
            self._violation = reason
        raise ProfileError(reason)

    @property
    def ops(self) -> int:
        return self._ops

    @property
    def artifact_count(self) -> int:
        return len(self._scratch)

    def _tick(self) -> None:
        if self._closed:
            raise ProfileError("context-closed")
        if self._clock() > self._deadline:
            self._refuse("timeout")
        self._ops += 1
        if self._ops > self._limits["maxOps"]:
            self._refuse("ops-budget-exceeded")

    def _guard(self, condition: bool, reason: str) -> None:
        if not condition:
            self._refuse(reason)

    def _clean(self, path: str) -> str:
        try:
            return _path(path, depth=4)
        except ProfileError as exc:
            self._refuse(exc.reason)

    def read(self, path: str) -> bytes:
        self._tick()
        self._guard(self._effect in ("E1", "E2"), "undeclared-effect")
        row = self._reads.get(self._clean(path))
        self._guard(row is not None, "path-outside-inventory")
        data = self._files.get(row["path"])
        self._guard(type(data) is bytes, "resource-missing")
        self._guard(len(data) == row["sizeBytes"] and sha256(data).hexdigest() == row["sha256"],
                 "resource-drift")
        return data

    def write(self, path: str, data: bytes) -> None:
        self._tick()
        self._guard(self._effect == "E2", "undeclared-effect")
        path = self._clean(path)
        self._guard(path in self._writes, "path-outside-inventory")
        self._guard(path not in self._scratch, "artifact-exists")
        self._guard(type(data) is bytes, "invalid-artifact")
        self._guard(len(data) <= MAX_WRITE_FILE and
                 self._written + len(data) <= self._limits["maxWriteBytes"],
                 "write-budget-exceeded")
        self._written += len(data)
        self._scratch[path] = data

    def exec(self, *_args: Any, **_kwargs: Any) -> None:
        """Child processes are E3: not adopted, never reachable from this module."""
        self._tick()
        self._refuse("undeclared-effect")

    def fetch(self, *_args: Any, **_kwargs: Any) -> None:
        """Network is E4: not adopted, never reachable from this module."""
        self._tick()
        self._refuse("undeclared-effect")

    def check_deadline(self) -> None:
        if self._clock() > self._deadline:
            self._refuse("timeout")

    def artifacts(self) -> Mapping[str, bytes]:
        return dict(self._scratch)

    def teardown(self) -> int:
        removed = len(self._scratch)
        self._scratch.clear()
        self._closed = True
        return removed


@dataclass(frozen=True)
class ToolResult:
    """Immutable run receipt: contract, allowlist, input, output and artifact hashes."""

    tool_id: str
    contract_sha256: str
    allowlist_sha256: str
    input_sha256: str
    output_sha256: str
    output: Mapping[str, Any]
    artifacts: Mapping[str, str]
    ops: int
    teardown: Mapping[str, Any]
    execution_authorization: bool = False

    def to_dict(self) -> dict:
        return {"toolId": self.tool_id, "contractSha256": self.contract_sha256,
                "allowlistSha256": self.allowlist_sha256, "inputSha256": self.input_sha256,
                "outputSha256": self.output_sha256, "output": thaw(self.output),
                "artifacts": thaw(self.artifacts), "ops": self.ops,
                "teardown": thaw(self.teardown),
                "executionAuthorization": self.execution_authorization}


def _typed(schema: list[dict], value: Any, invalid: str, over: str) -> None:
    _require(type(value) is dict and all(type(k) is str for k in value) and
             set(value) == {f["name"] for f in schema}, invalid)
    for field in schema:
        item, kind, bound = value[field["name"]], field["type"], field["max"]
        if kind == "boolean":
            _require(type(item) is bool, invalid)
        elif kind == "integer":
            _require(type(item) is int, invalid)
            _require(abs(item) <= bound, over)
        else:
            _require(type(item) is str and not any(0xD800 <= ord(c) <= 0xDFFF for c in item),
                     invalid)
            _require(len(item) <= bound, over)


def _size(value: Any, ceiling: int, invalid: str, over: str) -> None:
    try:
        encoded = canonical(value)
    except (TypeError, ValueError, RecursionError):
        raise ProfileError(invalid) from None
    _require(len(encoded) <= ceiling, over)


def run_tool(allowlist: ToolAllowlist, tool_id: str, input_value: Mapping[str, Any], *,
             helpers: Mapping[str, Callable], checkers: Mapping[str, Callable],
             files: Mapping[str, bytes],
             clock: Callable[[], int] = monotonic_ns) -> ToolResult:
    """Run one allowlisted deterministic helper under its contract, offline.

    ``helpers`` and ``checkers`` are per-run, task-local and explicit. Any helper
    outside the allowlist is refused rather than ignored. The helper is called as
    ``helper(context, input)``; the checker as ``checker(input, output, artifacts)``
    and must be a different callable that returns exactly ``True``.
    """
    _require(isinstance(allowlist, ToolAllowlist), "invalid-allowlist")
    _require(canonical(allowlist.data) == allowlist.canonical_bytes, "contract-drift")
    _require(isinstance(helpers, Mapping) and isinstance(checkers, Mapping) and
             isinstance(files, Mapping), "invalid-input")
    _require(all(name in allowlist.contracts for name in helpers) and
             all(name in allowlist.contracts for name in checkers), "helper-not-allowlisted")
    _require(type(tool_id) is str and tool_id in allowlist.contracts, "tool-not-allowlisted")
    entry = next((r for r in allowlist.data["tools"] if r["toolId"] == tool_id), None)
    _require(entry is not None, "contract-drift")
    # Enforce the re-parsed bytes, never a separately supplied data view.
    contract = parse_contract(allowlist.contracts[tool_id].canonical_bytes)
    _require(contract.sha256 == entry["contractSha256"] and
             canonical(allowlist.contracts[tool_id].data) == contract.canonical_bytes,
             "contract-drift")
    _require(contract.data["admission"]["state"] == "implemented", "effect-blocked")
    helper, checker = helpers.get(tool_id), checkers.get(tool_id)
    _require(callable(helper), "helper-missing")
    _require(callable(checker), "checker-missing")
    _require(helper is not checker, "checker-not-independent")
    data = contract.data
    _require(type(input_value) is dict, "invalid-input")
    _size(input_value, data["limits"]["maxInputBytes"], "invalid-input", "input-budget-exceeded")
    _typed(data["input"], input_value, "invalid-input", "input-budget-exceeded")
    frozen_input = freeze(input_value)
    context = ToolContext(contract, files, clock)
    try:
        try:
            output = helper(context, frozen_input)
        except ProfileError as exc:
            # Only refusals the context itself produced pass through.
            raise ProfileError(exc.reason if exc.reason == context.violation
                               else "helper-failed") from None
        except Exception:
            raise ProfileError("helper-failed") from None
        _require(context.violation is None, context.violation or "helper-failed")
        context.check_deadline()
        _typed(data["output"], output, "invalid-output", "output-budget-exceeded")
        _size(output, data["limits"]["maxOutputBytes"], "invalid-output",
              "output-budget-exceeded")
        artifacts = context.artifacts()
        # ToolContext.write already refuses undeclared paths; equality also catches omissions.
        _require(set(artifacts) == set(data["writes"]), "artifact-missing")
        try:
            verdict = checker(frozen_input, freeze(output), freeze(artifacts))
        except Exception:
            raise ProfileError("checker-raised") from None
        _require(verdict is True, "check-failed")
        input_sha, output_sha = digest(input_value), digest(output)
        artifact_hashes = {p: sha256(b).hexdigest() for p, b in artifacts.items()}
    finally:
        removed = context.teardown()
    return ToolResult(
        tool_id=tool_id, contract_sha256=contract.sha256, allowlist_sha256=allowlist.sha256,
        input_sha256=input_sha, output_sha256=output_sha,
        output=freeze(output), artifacts=freeze(artifact_hashes), ops=context.ops,
        teardown=freeze({"closed": True, "artifactsRemoved": removed}))
