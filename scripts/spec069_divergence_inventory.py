# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T002: inventory of differences between published request schemas and
the runtime validators of ``analyze-work``.

The script (1) enumerates every keyword of the AIM record schema and the git
request schema, (2) enumerates the checks the runtime performs (hand-curated
list, each anchored to a source line that the script verifies still exists),
(3) probes each schema keyword with generated mutations and each runtime check
with a dedicated input, comparing the schema verdict with the verdict of the
complete ``analyze-work`` service path (adapter bounds plus validator), and
(4) writes ``evidence/divergence-inventory.json``.

Nothing is executed outside a temporary directory; inputs never leave the
process. The output is deterministic apart from the ``environment`` block.

    python -m scripts.spec069_divergence_inventory            # write
    python -m scripts.spec069_divergence_inventory --check    # compare, exit 1 on drift
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import jsonschema
from importlib import metadata

from agent_braid import analysis
from agent_braid.tooling_mcp import ToolingConfig, ToolingService

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs/069-aim-request-authoring/evidence"
# The T002 baseline pins the schemas of develop at the start of SPEC-069 P1 (PR #1138's base);
# the "after decisions" inventory reads the working tree and shows what the D8 decisions left.
BASELINE_REV = "14187e05668e03ee452a91f5209fd5ae883a04e4"
OUTPUT = EVIDENCE / "divergence-inventory.json"
OUTPUT_AFTER = EVIDENCE / "divergence-inventory-after-decisions.json"
AIM_SCHEMA = ROOT / "schemas/0.2.0-draft/agent-interaction-metadata.schema.json"
INPUT_SCHEMA = ROOT / "schemas/0.1.0-alpha/analysis-input.schema.json"
GIT_SCHEMA = ROOT / "schemas/0.1.0-alpha/git-analysis-request.schema.json"
REPO_PLACEHOLDER = "<repo>"
THRESHOLD = 15  # counterfactual C1: more root causes reopen D1 for the owner

# Whitespace semantics: characters on which Python ``str.strip`` and the
# ECMAScript ``\s`` / ``trim`` disagree (the validators use ``strip``).
PYTHON_ONLY_BLANK = ["\x1c", "\x1d", "\x1e", "\x1f", "\x85"]
ECMASCRIPT_ONLY_BLANK = ["﻿"]


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# Runtime check catalogue. ``anchor`` is a source fragment that must still be
# present in ``file``; the script fails if code moved without this list.
# --------------------------------------------------------------------------
RUNTIME_CHECKS = [
    # id, layer, file, anchor, description
    ("RC-ENV-1", "analysis.py", "agent_braid/analysis.py", 'set(value) == {"analysisInputVersion", "source", "operations"}', "envelope has exactly analysisInputVersion, source, operations"),
    ("RC-ENV-2", "analysis.py", "agent_braid/analysis.py", 'set(source) == {"kind", "description"}', "source is an object with exactly kind and description"),
    ("RC-ENV-3", "analysis.py", "agent_braid/analysis.py", '_nonempty(source.get("kind"), "source kind")', "source.kind is a non-blank string"),
    ("RC-ENV-4", "analysis.py", "agent_braid/analysis.py", '_nonempty(source.get("description"), "source description")', "source.description is a non-blank string"),
    ("RC-ENV-5", "analysis.py", "agent_braid/analysis.py", 'isinstance(value, list) and value, "expected AIM record or nonempty AIM array"', "operations (or a bare array) is a nonempty list"),
    ("RC-ENV-6", "analysis.py", "agent_braid/analysis.py", '"AIM records must be objects"', "every operation is an object"),
    ("RC-REC-1", "analysis.py", "agent_braid/analysis.py", 'set(record) == required', "record has exactly the nine AIM fields"),
    ("RC-REC-2", "analysis.py", "agent_braid/analysis.py", 'record["aimVersion"] == "0.2.0-draft"', "aimVersion is 0.2.0-draft"),
    ("RC-REC-3", "analysis.py", "agent_braid/analysis.py", '_nonempty(record["instanceId"], "instanceId")', "instanceId is a non-blank string"),
    ("RC-REC-4", "analysis.py", "agent_braid/analysis.py", '_nonempty(record["attemptId"], "attemptId")', "attemptId is a non-blank string"),
    ("RC-REC-5", "analysis.py", "agent_braid/analysis.py", 'set(definition) == {"id", "digest"}', "definition has exactly id and digest"),
    ("RC-REC-6", "analysis.py", "agent_braid/analysis.py", '_nonempty(definition["id"], "definition id")', "definition.id is a non-blank string"),
    ("RC-REC-7", "analysis.py", "agent_braid/analysis.py", 'DIGEST.fullmatch(definition["digest"])', "definition.digest matches sha256:<64 lowercase hex>"),
    ("RC-REC-8", "analysis.py", "agent_braid/analysis.py", 'DIGEST.fullmatch(record["inputDigest"])', "inputDigest matches sha256:<64 lowercase hex>"),
    ("RC-REC-9", "analysis.py", "agent_braid/analysis.py", 'isinstance(item, str) and item for item in dependencies', "dependencies items are nonempty strings"),
    ("RC-REC-10", "analysis.py", "agent_braid/analysis.py", 'len(dependencies) == len(set(dependencies))', "dependencies are unique"),
    ("RC-REC-11", "analysis.py", "agent_braid/analysis.py", '_nonempty(resource, "version resource")', "readVersions keys are non-blank strings"),
    ("RC-REC-12", "analysis.py", "agent_braid/analysis.py", 'type(version) is int and version >= 0', "readVersions values are Python ints >= 0 (JSON 1.0 is a float)"),
    ("RC-REC-13", "analysis.py", "agent_braid/analysis.py", '{"declared", "inferred", "observed", "coverage"}', "effects has exactly four members"),
    ("RC-REC-14", "analysis.py", "agent_braid/analysis.py", 'set(effect) == {"kind", "resource"}', "each effect has exactly kind and resource"),
    ("RC-REC-15", "analysis.py", "agent_braid/analysis.py", 'effect["kind"] in EFFECT_KINDS', "effect kind is one of eight kinds"),
    ("RC-REC-16", "analysis.py", "agent_braid/analysis.py", '_nonempty(effect["resource"], "effect resource")', "effect resource is a non-blank string"),
    ("RC-REC-17", "analysis.py", "agent_braid/analysis.py", 'set(coverage) == {"status", "domain", "method"}', "coverage has exactly status, domain, method"),
    ("RC-REC-18", "analysis.py", "agent_braid/analysis.py", 'coverage["status"] in {"complete", "partial", "unknown"}', "coverage status is complete, partial or unknown"),
    ("RC-REC-19", "analysis.py", "agent_braid/analysis.py", '_nonempty(coverage["domain"], "coverage domain")', "coverage domain is non-blank"),
    ("RC-REC-20", "analysis.py", "agent_braid/analysis.py", '_nonempty(coverage["method"], "coverage method")', "coverage method is non-blank"),
    ("RC-REC-21", "analysis.py", "agent_braid/analysis.py", 'evidence must be a nonempty array', "evidence is a nonempty list (items are not inspected)"),
    ("RC-BAT-1", "analysis.py", "agent_braid/analysis.py", '"duplicate instance ID"', "instanceId values are unique in a batch"),
    ("RC-BAT-2", "analysis.py", "agent_braid/analysis.py", '"duplicate attempt ID"', "attemptId values are unique in a batch"),
    ("RC-BAT-3", "analysis.py", "agent_braid/analysis.py", '"unknown dependency"', "dependencies name instances of the batch"),
    ("RC-BAT-4", "analysis.py", "agent_braid/analysis.py", '"self dependency"', "no instance depends on itself"),
    ("RC-BAT-5", "analysis.py", "agent_braid/analysis.py", '"cyclic dependencies"', "dependencies are acyclic"),
    ("RC-ADP-1", "tooling_mcp.py adapter", "agent_braid/tooling_mcp.py", "count > MAX_OPERATIONS", "at most 32 operations (array, or 'operations'/'tasks' list of an object)"),
    ("RC-ADP-2", "tooling_mcp.py adapter", "agent_braid/tooling_mcp.py", "> MAX_IDENTIFIER_BYTES", "instanceId and attemptId at most 256 UTF-8 bytes (array items and 'operations' items only)"),
    ("RC-ADP-3", "tooling_mcp.py adapter", "agent_braid/tooling_mcp.py", "depth > MAX_INPUT_DEPTH", "nesting depth at most 32"),
    ("RC-ADP-4", "tooling_mcp.py adapter", "agent_braid/tooling_mcp.py", "len(raw) > MAX_FRAME_BYTES", "request at most 1 MiB"),
    ("RC-GIT-1", "tooling_mcp.py adapter", "agent_braid/tooling_mcp.py", '"gitAnalysisRequestVersion", "repository", "baseRevision", "operations"}', "git request has exactly the four fields"),
    ("RC-GIT-2", "git_adapter.py", "agent_braid/git_adapter.py", 'unsupported Git analysis request version', "git request version is 0.1.0-alpha"),
    ("RC-GIT-3", "git_adapter.py", "agent_braid/git_adapter.py", 'isinstance(value["repository"], str) and value["repository"].strip()', "repository is a non-blank string"),
    ("RC-GIT-4", "tooling_mcp.py adapter", "agent_braid/tooling_mcp.py", "Git repository is outside the configured source root", "repository equals the configured source root"),
    ("RC-GIT-5", "git_adapter.py", "agent_braid/git_adapter.py", "at least two Git operations are required", "operations is a list with at least two items"),
    ("RC-GIT-6", "git_adapter.py", "agent_braid/git_adapter.py", 'set(operation) == required', "operation has exactly the five fields"),
    ("RC-GIT-7", "git_adapter.py", "agent_braid/git_adapter.py", 'operation[name].strip(), f"invalid {name}"', "instanceId and attemptId are non-blank strings"),
    ("RC-GIT-8", "git_adapter.py", "agent_braid/git_adapter.py", 'all(isinstance(x, str) and x for x in dependencies)', "dependencies items are nonempty strings (uniqueness is not checked)"),
    ("RC-GIT-9", "git_adapter.py", "agent_braid/git_adapter.py", 'all(isinstance(x, str) and x for x in uncertain)', "uncertainPaths items are nonempty strings (uniqueness is not checked)"),
    ("RC-GIT-10", "git_adapter.py", "agent_braid/git_adapter.py", '{"kind", "revision"} if kind == "commit"', "source has exactly kind+revision (commit) or kind+path (worktree)"),
    ("RC-GIT-11", "git_adapter.py", "agent_braid/git_adapter.py", '"unsupported Git source kind"', "source kind is commit or worktree"),
    ("RC-GIT-12", "git_adapter.py", "agent_braid/git_adapter.py", 'revision.strip(), "invalid Git revision"', "baseRevision and source revisions are non-blank and resolve to a commit"),
]


# Schema-walk probes that exercise a runtime check, by JSON Pointer prefix.
CHECK_POINTERS = {
    "RC-REC-1": ("aim", [""]), "RC-REC-2": ("aim", ["/aimVersion"]),
    "RC-REC-3": ("aim", ["/instanceId"]), "RC-REC-4": ("aim", ["/attemptId"]),
    "RC-REC-5": ("aim", ["/definition"]), "RC-REC-6": ("aim", ["/definition/id"]),
    "RC-REC-7": ("aim", ["/definition/digest"]), "RC-REC-8": ("aim", ["/inputDigest"]),
    "RC-REC-9": ("aim", ["/dependencies"]), "RC-REC-10": ("aim", ["/dependencies"]),
    "RC-REC-11": ("aim", ["/readVersions"]), "RC-REC-12": ("aim", ["/readVersions"]),
    "RC-REC-13": ("aim", ["/effects"]), "RC-REC-14": ("aim", ["/effects/declared"]),
    "RC-REC-15": ("aim", ["/effects/declared/0/kind"]), "RC-REC-16": ("aim", ["/effects/declared/0/resource"]),
    "RC-REC-17": ("aim", ["/effects/coverage"]), "RC-REC-18": ("aim", ["/effects/coverage/status"]),
    "RC-REC-19": ("aim", ["/effects/coverage/domain"]), "RC-REC-20": ("aim", ["/effects/coverage/method"]),
    "RC-REC-21": ("aim", ["/evidence"]),
    "RC-GIT-1": ("git", [""]), "RC-GIT-2": ("git", ["/gitAnalysisRequestVersion"]),
    "RC-GIT-3": ("git", ["/repository"]), "RC-GIT-5": ("git", ["/operations"]),
    "RC-GIT-6": ("git", ["/operations/0"]), "RC-GIT-7": ("git", ["/operations/0/instanceId", "/operations/0/attemptId"]),
    "RC-GIT-8": ("git", ["/operations/0/dependencies"]), "RC-GIT-9": ("git", ["/operations/0/uncertainPaths"]),
    "RC-GIT-10": ("git", ["/operations/0/source"]), "RC-GIT-11": ("git", ["/operations/0/source/kind"]),
}


# --------------------------------------------------------------------------
# Instances
# --------------------------------------------------------------------------
def base_record(instance: str, attempt: str, dependencies: list[str], resource: str) -> dict:
    return {
        "aimVersion": "0.2.0-draft",
        "instanceId": instance,
        "attemptId": attempt,
        "definition": {"id": "inventory.probe-v1", "digest": "sha256:" + "1" * 64},
        "inputDigest": "sha256:" + "a" * 64,
        "dependencies": dependencies,
        "readVersions": {"repo://w/read.txt": 3},
        "effects": {
            "declared": [{"kind": "write", "resource": resource}],
            "inferred": [{"kind": "read", "resource": resource}],
            "observed": [{"kind": "read", "resource": resource}],
            "coverage": {"status": "complete", "domain": "probe", "method": "probe"},
        },
        "evidence": [{
            "property": "independence", "method": "declared", "domain": "probe",
            "assumptions": ["probe"], "observationContract": "probe",
            "executionContract": "probe", "assuranceClass": 1,
        }],
    }


def aim_pair() -> tuple[dict, dict]:
    # record 0 depends on the partner so that the dependencies array is nonempty
    return (base_record("probe-a", "probe-a-1", ["probe-b"], "repo://w/a.txt"),
            base_record("probe-b", "probe-b-1", [], "repo://w/b.txt"))


def git_base() -> dict:
    return {
        "gitAnalysisRequestVersion": "0.1.0-alpha",
        "repository": REPO_PLACEHOLDER,
        "baseRevision": "HEAD",
        "operations": [
            {"instanceId": "g-a", "attemptId": "g-a-1", "dependencies": ["g-b"],
             "uncertainPaths": ["docs/x.md"], "source": {"kind": "commit", "revision": "HEAD"}},
            {"instanceId": "g-b", "attemptId": "g-b-1", "dependencies": [],
             "uncertainPaths": [], "source": {"kind": "commit", "revision": "HEAD"}},
        ],
    }


# --------------------------------------------------------------------------
# Schema walk -> mutations
# --------------------------------------------------------------------------
def get_at(instance, path):
    for step in path:
        instance = instance[step]
    return instance


def set_at(instance, path, value):
    if not path:
        return value
    parent = get_at(instance, path[:-1])
    parent[path[-1]] = value
    return instance


def del_at(instance, path):
    del get_at(instance, path[:-1])[path[-1]]
    return instance


def pointer(path) -> str:
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in path)


def wrong_types(value):
    candidates = {"string": "text", "integer": 7, "array": [], "object": {}, "null": None, "boolean": True}
    current = ("boolean" if isinstance(value, bool) else "integer" if isinstance(value, int)
               else "string" if isinstance(value, str) else "array" if isinstance(value, list)
               else "object" if isinstance(value, dict) else "null")
    return [(name, candidates[name]) for name in ("string", "integer", "array", "object", "null")
            if name != current][:3]


def mutations(schema: dict, instance, path=(), keyword_log=None, root_instance=None):
    """Yield (path, keyword, label, mutate) tuples for every keyword of ``schema``.

    ``mutate`` takes a deep copy of the root instance and returns the mutant.
    """
    out = []
    root_instance = instance if root_instance is None else root_instance
    node = get_at(instance, path) if path else instance
    log = (lambda kw: keyword_log.append((pointer(path), kw))) if keyword_log is not None else (lambda kw: None)

    def add(keyword, label, fn):
        out.append((path, keyword, label, fn))

    if "oneOf" in schema:
        log("oneOf")
        for branch in schema["oneOf"]:
            if jsonschema.Draft202012Validator(branch).is_valid(node):
                out.extend(mutations(branch, instance, path, keyword_log, root_instance))
                break
        return out
    if "const" in schema:
        log("const")
        add("const", "wrong constant", lambda r, p=path: set_at(r, p, "not-the-constant"))
    if "enum" in schema:
        log("enum")
        add("enum", "value outside enum", lambda r, p=path: set_at(r, p, "not-in-enum"))
    if "type" in schema:
        log("type")
        for name, replacement in wrong_types(node):
            add("type", f"{name} instead of {schema['type']}", lambda r, p=path, v=replacement: set_at(r, p, copy.deepcopy(v)))
        if schema["type"] == "integer":
            add("type", "float 1.0 for an integer", lambda r, p=path: set_at(r, p, 1.0))
            add("type", "boolean for an integer", lambda r, p=path: set_at(r, p, True))
    if schema.get("type") == "string":
        if "minLength" in schema:
            log("minLength")
            add("minLength", "empty string", lambda r, p=path: set_at(r, p, ""))
            add("minLength", "blank string (spaces)", lambda r, p=path: set_at(r, p, "   "))
            for ch in PYTHON_ONLY_BLANK + ECMASCRIPT_ONLY_BLANK:
                add("minLength", f"blank string (U+{ord(ch):04X} only)", lambda r, p=path, c=ch: set_at(r, p, c))
        if "pattern" in schema:
            log("pattern")
        if "pattern" in schema and schema["pattern"] != "\\S":  # \S nodes are covered by the blank mutations
            add("pattern", "string not matching the pattern", lambda r, p=path: set_at(r, p, "sha256:ZZ"))
            add("pattern", "uppercase hex digest", lambda r, p=path: set_at(r, p, "sha256:" + "A" * 64))
            add("pattern", "trailing newline after a valid digest", lambda r, p=path: set_at(r, p, "sha256:" + "a" * 64 + "\n"))
    if "minimum" in schema:
        log("minimum")
        add("minimum", "below minimum", lambda r, p=path, m=schema["minimum"]: set_at(r, p, m - 1))
    if "maximum" in schema:
        log("maximum")
        add("maximum", "above maximum", lambda r, p=path, m=schema["maximum"]: set_at(r, p, m + 1))
    if schema.get("type") == "array":
        if "minItems" in schema:
            log("minItems")
            add("minItems", "empty array", lambda r, p=path: set_at(r, p, []))
        if schema.get("uniqueItems"):
            log("uniqueItems")
            add("uniqueItems", "duplicate item", lambda r, p=path: set_at(r, p, [copy.deepcopy(get_at(r, p)[0])] * 2))
        if "items" in schema and isinstance(node, list) and node:
            log("items")
            out.extend(mutations(schema["items"], instance, path + (0,), keyword_log, root_instance))
    if schema.get("type") == "object":
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            log("additionalProperties")
            add("additionalProperties", "unknown extra property", lambda r, p=path: get_at(r, p).__setitem__("unexpectedField", "x") or r)
        elif isinstance(schema.get("additionalProperties"), dict):
            log("additionalProperties")
            sub = schema["additionalProperties"]
            key = next(iter(node), None) if isinstance(node, dict) else None
            if key is not None:
                out.extend(mutations(sub, instance, path + (key,), keyword_log, root_instance))
            add("additionalProperties", "empty property name", lambda r, p=path: get_at(r, p).__setitem__("", 1) or r)
            add("additionalProperties", "blank property name", lambda r, p=path: get_at(r, p).__setitem__("  ", 1) or r)
        for name in schema.get("required", []):
            log("required")
            add("required", f"missing required property {name}", lambda r, p=path + (name,): del_at(r, p))
        if props:
            log("properties")
        for name, sub in props.items():
            if isinstance(node, dict) and name in node:
                out.extend(mutations(sub, instance, path + (name,), keyword_log, root_instance))
    return out


# --------------------------------------------------------------------------
# Probing
# --------------------------------------------------------------------------
def init_repo(base: Path) -> tuple[Path, Path]:
    """Create a one-commit Git repository and an empty results directory under ``base``."""
    repo, results = base / "repo", base / "results"
    repo.mkdir()
    results.mkdir()
    env = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
           "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
    for args in (["init", "-q"], ["config", "user.email", "p@example.test"], ["config", "user.name", "p"]):
        subprocess.run(["git", *args], cwd=repo, check=True, env=env)
    (repo / "a.txt").write_text("a\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True, env=env)
    return repo, results


class Prober:
    def __init__(self, repo: Path, results: Path) -> None:
        self.repo = repo
        self.service = ToolingService(ToolingConfig(repo, results))

    def service_verdict(self, kind: str, request) -> tuple[bool, str]:
        if kind == "git":
            request = json.loads(json.dumps(request).replace(REPO_PLACEHOLDER, str(self.repo)))
        result = self.service.invoke("analyze-work", {"kind": kind, "request": request}, threading.Event())
        text = str(result.get("summary", ""))
        text = text.replace(str(self.repo), "<repo>")
        return result.get("status") == "ok", text

    @staticmethod
    def analysis_verdict(request) -> bool:
        try:
            analysis.analyze(request)
            return True
        except analysis.InvalidAnalysis:
            return False
        except Exception:
            return False


def schema_text(path: Path, rev: str | None) -> str:
    if rev is None:
        return path.read_text()
    return subprocess.run(["git", "show", f"{rev}:{path.relative_to(ROOT)}"], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout


def text_sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def roundtrip(value):
    """Serialise and parse so numbers behave as they do on the wire (1.0 is a float)."""
    return json.loads(json.dumps(value))


# Root-cause attribution -------------------------------------------------
def root_cause(row: dict) -> str:
    rel, kw, ptr, label = row["relation"], row["keyword"], row["pointer"], row["label"]
    if rel == "equal":
        return "none"
    if rel in {"runtime-only-batch"}:
        return "RC-batch: batch-level checks (duplicates, unknown or self dependency, cycles) that JSON Schema cannot express"
    if rel == "adapter-only":
        if "single record" in label:
            return "RC-adapter-bypass: the 256-byte identifier bound is not applied to a single AIM record request"
        return "RC-adapter: adapter bounds (32 operations, 256-byte identifiers) are not in any schema"
    if rel == "schema-absent":
        return "RC-envelope: no published schema for the analysis-input envelope"
    if ptr.startswith("/evidence/0"):
        return "RC-evidence: runtime checks only that evidence is a nonempty array; the schema validates each item"
    if ptr.endswith("/dependencies/0") and ("blank" in label or "U+" in label):
        return "RC-batch: batch-level checks (duplicates, unknown or self dependency, cycles) that JSON Schema cannot express"
    if row["kind"] == "git" and "U+FEFF" in label:
        return "RC-git-resolution: a value that is not blank for Python strip() but does not resolve to a repository or revision"
    if "blank" in label or "U+" in label:
        return "RC-blank: the runtime refuses blank strings; the schema states minLength only"
    if kw == "pattern" and "newline" in label:
        return "RC-pattern-newline: the Python jsonschema `$` accepts a trailing newline (ECMAScript does not); the runtime fullmatch refuses it"
    if ptr.startswith("/readVersions"):
        return "RC-readversions: readVersions key and number semantics differ"
    if kw == "uniqueItems":
        return "RC-git-unique: the git adapter does not enforce uniqueItems on dependencies and uncertainPaths"
    return f"RC-other: {kw} at {ptr}"


def relation(schema_ok: bool, service_ok: bool) -> str:
    if schema_ok == service_ok:
        return "equal"
    return "runtime-stricter" if schema_ok else "schema-stricter"


def decision_for(rel: str, cause: str) -> dict:
    if rel == "equal":
        return {"policy": "none", "status": "no-divergence"}
    if rel == "runtime-stricter":
        if cause.startswith(("RC-blank", "RC-readversions", "RC-evidence")):
            return {"policy": "D8", "proposal": "tighten the published schema where JSON Schema can express the runtime check (no runtime change, no new AIM version, schema note); otherwise document as a runtime-only check", "status": "proposed", "ownerDecisionRequired": True}
        return {"policy": "D8", "proposal": "document as an intentional non-structural or runtime-only check", "status": "proposed", "ownerDecisionRequired": False}
    if rel == "schema-stricter":
        return {"policy": "D8", "proposal": "keep runtime behaviour as a documented runtime-only difference; fold the tightening into the next AIM version", "status": "proposed", "ownerDecisionRequired": True}
    if rel == "runtime-only-batch":
        return {"policy": "D8", "proposal": "document as an intentional non-structural check; the corpus records the expected runtime refusal", "status": "proposed", "ownerDecisionRequired": False}
    if rel == "adapter-only":
        return {"policy": "D8", "proposal": "document as an adapter bound; publish the bound in the contract, not in the AIM schema", "status": "proposed", "ownerDecisionRequired": False}
    return {"policy": "D8", "proposal": "publish an envelope schema (T003)", "status": "proposed", "ownerDecisionRequired": False}


def build(schemas_at: str | None = None) -> dict:
    """Probe the schemas of revision ``schemas_at`` (None: the working tree) against the current runtime."""
    aim_text, git_text = schema_text(AIM_SCHEMA, schemas_at), schema_text(GIT_SCHEMA, schemas_at)
    aim_schema, git_schema = json.loads(aim_text), json.loads(git_text)
    aim_validator = jsonschema.Draft202012Validator(aim_schema)
    git_validator = jsonschema.Draft202012Validator(git_schema)
    try:
        input_schema = json.loads(schema_text(INPUT_SCHEMA, schemas_at))
    except (subprocess.CalledProcessError, FileNotFoundError):
        input_schema = None  # the envelope schema does not exist at this revision
    input_validator = None
    if input_schema is not None:
        from referencing import Registry, Resource
        registry = Registry().with_resources([(aim_schema["$id"], Resource.from_contents(aim_schema))])
        input_validator = jsonschema.Draft202012Validator(input_schema, registry=registry)
    rows: list[dict] = []
    keyword_log: dict[str, list] = {"aim": [], "git": []}

    with tempfile.TemporaryDirectory() as tmp:
        repo, results = init_repo(Path(tmp))
        prober = Prober(repo.resolve(), results)

        def record(kind, label, keyword, ptr, request, schema_ok, service_ok, analysis_ok, summary, rel=None):
            rel = rel or relation(schema_ok, service_ok)
            if len(json.dumps(request)) > 20000:
                request = {"omitted": f"input of {len(json.dumps(request))} bytes; regenerate with the script"}
            row = {
                "id": f"{kind}-{len(rows) + 1:04d}", "kind": kind, "pointer": ptr, "keyword": keyword,
                "label": label, "input": request,
                "verdicts": {"schema": "accepts" if schema_ok else "refuses",
                             "service": "accepts" if service_ok else "refuses",
                             "analysisModule": None if analysis_ok is None else ("accepts" if analysis_ok else "refuses")},
                "relation": rel,
            }
            row["rootCause"] = root_cause(row)
            row["decision"] = decision_for(rel, row["rootCause"])
            rows.append(row)

        # 1. AIM: schema-driven mutations of record 0 inside a two-record array
        a, b = aim_pair()
        assert aim_validator.is_valid(a) and aim_validator.is_valid(b)
        assert prober.service_verdict("aim", [a, b])[0], "base AIM pair must be accepted"
        keyword_log_aim: list = []
        for path, keyword, label, fn in mutations(aim_schema, a, keyword_log=keyword_log_aim):
            mutant = roundtrip(fn(copy.deepcopy(a)))
            request = [mutant, copy.deepcopy(b)]
            ok_service, summary = prober.service_verdict("aim", roundtrip(request))
            record("aim", label, keyword, pointer(path), mutant, aim_validator.is_valid(mutant),
                   ok_service, Prober.analysis_verdict(roundtrip(request)), summary)
        keyword_log["aim"] = sorted(set(keyword_log_aim))

        # 2. AIM: runtime-check driven probes (batch, envelope, adapter, depth)
        def runtime_probe(label, request, rc, kind="aim", rel=None, ptr="", schema_ok=True):
            ok_service, summary = prober.service_verdict(kind, roundtrip(request))
            if rel == "schema-absent" and input_validator is not None:
                schema_ok, rel = input_validator.is_valid(roundtrip(request)), None
                if schema_ok != ok_service:
                    rel = "runtime-stricter" if schema_ok else "schema-stricter"
            record(kind, label, rc, ptr, request, schema_ok, ok_service,
                   Prober.analysis_verdict(roundtrip(request)) if kind == "aim" else None, summary,
                   rel or ("runtime-only-batch" if (schema_ok and not ok_service) else relation(schema_ok, ok_service)))

        dup = copy.deepcopy(b); dup["attemptId"] = "other-1"
        runtime_probe("duplicate instanceId in a batch", [b, dup], "RC-BAT-1")
        dup = copy.deepcopy(b); dup["instanceId"] = "probe-c"
        runtime_probe("duplicate attemptId in a batch", [b, dup], "RC-BAT-2")
        solo = copy.deepcopy(b); solo["dependencies"] = ["ghost"]
        runtime_probe("unknown dependency", [solo, copy.deepcopy(a)], "RC-BAT-3")
        selfdep = copy.deepcopy(b); selfdep["dependencies"] = ["probe-b"]
        runtime_probe("self dependency", [selfdep], "RC-BAT-4")
        x = base_record("cx", "cx-1", ["cy"], "repo://w/x"); y = base_record("cy", "cy-1", ["cx"], "repo://w/y")
        runtime_probe("cyclic dependencies", [x, y], "RC-BAT-5")

        envelope = {"analysisInputVersion": "0.1.0-alpha", "source": {"kind": "probe", "description": "probe"}, "operations": [a, b]}
        runtime_probe("valid envelope", envelope, "RC-ENV-1", rel="schema-absent")
        for label, mutate, rc in [
            ("envelope with an extra field", lambda e: e.__setitem__("extra", 1), "RC-ENV-1"),
            ("envelope without source", lambda e: e.pop("source"), "RC-ENV-1"),
            ("envelope source with an extra field", lambda e: e["source"].__setitem__("x", 1), "RC-ENV-2"),
            ("envelope source kind blank", lambda e: e["source"].__setitem__("kind", "  "), "RC-ENV-3"),
            ("envelope source description blank", lambda e: e["source"].__setitem__("description", " "), "RC-ENV-4"),
            ("envelope with empty operations", lambda e: e.__setitem__("operations", []), "RC-ENV-5"),
            ("envelope with a non-object operation", lambda e: e.__setitem__("operations", ["x"]), "RC-ENV-6"),
            ("envelope with another analysisInputVersion", lambda e: e.__setitem__("analysisInputVersion", "9.9.9"), "RC-ENV-1"),
        ]:
            e = copy.deepcopy(envelope); mutate(e)
            runtime_probe(label, e, rc, rel="schema-absent")
        runtime_probe("bare nonempty AIM array", [a, b], "RC-ENV-5", rel="schema-absent")
        runtime_probe("empty array", [], "RC-ENV-5", rel="schema-absent")
        runtime_probe("single AIM record", dict(b, dependencies=[]), "RC-ENV-5", rel="schema-absent")

        # adapter bounds
        many = [base_record(f"m{i}", f"m{i}-1", [], f"repo://w/{i}") for i in range(33)]
        runtime_probe("33 operations in an array", many, "RC-ADP-1", rel="adapter-only")
        runtime_probe("33 operations in an envelope", dict(envelope, operations=many), "RC-ADP-1", rel="adapter-only")
        long_id = copy.deepcopy(b); long_id["instanceId"] = "i" * 257
        runtime_probe("instanceId of 257 bytes in an array", [long_id, copy.deepcopy(a) | {"dependencies": []}], "RC-ADP-2", rel="adapter-only")
        runtime_probe("instanceId of 257 bytes in an envelope", dict(envelope, operations=[long_id, copy.deepcopy(a) | {"dependencies": []}]), "RC-ADP-2", rel="adapter-only")
        runtime_probe("instanceId of 257 bytes in a single record request", long_id, "RC-ADP-2", rel="adapter-only")
        multi = copy.deepcopy(b); multi["instanceId"] = "é" * 129
        runtime_probe("instanceId of 129 two-byte characters (258 bytes) in an array", [multi, copy.deepcopy(a) | {"dependencies": []}], "RC-ADP-2", rel="adapter-only")
        nest = {}
        cursor = nest
        for _ in range(34):
            cursor["x"] = {}
            cursor = cursor["x"]
        runtime_probe("nesting depth 34", nest, "RC-ADP-3", rel="adapter-only")

        huge = copy.deepcopy(b); huge["effects"]["declared"][0]["resource"] = "r" * (1024 * 1024)
        runtime_probe("request larger than 1 MiB", [huge, copy.deepcopy(a) | {"dependencies": []}], "RC-ADP-4", rel="adapter-only")

        # analysis semantics observed in review A2 (not structural; out of scope)
        alias_a = base_record("al-a", "al-a-1", [], "repo://w/README.md")
        alias_b = base_record("al-b", "al-b-1", [], "repo://w/./README.md")
        for rec in (alias_a, alias_b):
            rec["effects"]["declared"] = [{"kind": "write", "resource": rec["effects"]["declared"][0]["resource"]}]
            rec["effects"]["inferred"] = []; rec["effects"]["observed"] = []
        report = analysis.analyze([alias_a, alias_b])
        semantic = {"id": "aim-semantic-alias", "kind": "aim", "input": [alias_a, alias_b],
                    "classification": report["interactions"][0]["classification"],
                    "observation": "repo://w/README.md and repo://w/./README.md, both written with complete coverage, are classified as above (exact-string resource identity; out of scope for SPEC-069, addressed by the declared-not-observed label T015 and by units normalization if P3 runs)"}

        # 3. Git: schema-driven mutations of the request
        gb = git_base()
        assert git_validator.is_valid(gb)
        assert prober.service_verdict("git", roundtrip(gb))[0], "base git request must be accepted"
        keyword_log_git: list = []
        for path, keyword, label, fn in mutations(git_schema, gb, keyword_log=keyword_log_git):
            mutant = roundtrip(fn(copy.deepcopy(gb)))
            ok_service, summary = prober.service_verdict("git", mutant)
            record("git", label, keyword, pointer(path), mutant, git_validator.is_valid(mutant), ok_service, None, summary)
        keyword_log["git"] = sorted(set(keyword_log_git))
        # extra git probes for checks the schema cannot state
        other_repo = copy.deepcopy(gb); other_repo["repository"] = str(Path(tmp).resolve())
        ok_service, summary = prober.service_verdict("git", other_repo)
        record("git", "repository outside the configured source root", "RC-GIT-4", "/repository",
               dict(other_repo, repository="<outside-root>"), True, ok_service, None, summary,
               rel="runtime-only-batch" if not ok_service else "equal")
        unresolved = copy.deepcopy(gb); unresolved["baseRevision"] = "no-such-revision"
        ok_service, summary = prober.service_verdict("git", unresolved)
        record("git", "baseRevision that does not resolve", "RC-GIT-12", "/baseRevision", unresolved,
               True, ok_service, None, summary, rel="runtime-only-batch" if not ok_service else "equal")

    # 4. Runtime check catalogue. Anchors are verified against the alpha.7 sources (BASELINE_REV):
    # the catalogue describes the checks that existed when the inventory began, whatever
    # later refactors do to the code.
    checks = []
    for rc_id, layer, file, anchor, description in RUNTIME_CHECKS:
        text = subprocess.run(["git", "show", f"{BASELINE_REV}:{file}"], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout
        line = next((i for i, l in enumerate(text.splitlines(), 1) if anchor in l), 0)
        if line == 0 and anchor not in text:
            raise SystemExit(f"catalogue anchor for {rc_id} not found in {file}@{BASELINE_REV[:8]}: {anchor!r}; update RUNTIME_CHECKS")
        checks.append({"id": rc_id, "layer": layer, "file": file, "sourceRevision": BASELINE_REV,
                       "line": line or None, "description": description})
    for check in checks:
        kind, ptrs = CHECK_POINTERS.get(check["id"], (None, None))
        check["probedBy"] = sorted(
            r["id"] for r in rows
            if r["keyword"] == check["id"] or (kind == r["kind"] and ptrs and any(
                r["pointer"] == q or r["pointer"].startswith(q + "/") for q in ptrs))
        )

    divergent = [r for r in rows if r["relation"] != "equal"]
    causes: dict[str, list[str]] = {}
    for r in divergent:
        causes.setdefault(r["rootCause"], []).append(r["id"])
    schema_ok_runtime_ref = [r for r in rows if r["relation"] == "runtime-stricter"]
    summary = {
        "probes": len(rows),
        "equalVerdicts": len(rows) - len(divergent),
        "divergentProbes": len(divergent),
        "byRelation": {rel: sum(1 for r in rows if r["relation"] == rel)
                       for rel in sorted({r["relation"] for r in rows})},
        "rootCauses": [{"rootCause": cause, "probeCount": len(ids), "probes": ids} for cause, ids in sorted(causes.items())],
        "rootCauseCount": len(causes),
        "threshold": THRESHOLD,
        "thresholdExceeded": len(causes) > THRESHOLD,
        "thresholdNote": "Counted per root cause, not per probe: one cause (for example the runtime ignoring evidence items) yields many probes. Per-probe and per-keyword counts are in the rows.",
        "observedOn2026-11-05": {
            "evidence [{}] accepted by runtime, refused by schema": any(r["kind"] == "aim" and r["pointer"].startswith("/evidence/0") and r["relation"] == "schema-stricter" for r in rows),
            "blank instanceId accepted by schema, refused by runtime": any(r["kind"] == "aim" and r["pointer"] == "/instanceId" and "blank string (spaces)" in r["label"] and r["relation"] == "runtime-stricter" for r in rows),
            "readVersions 1.0 accepted by schema, refused by runtime": any(r["pointer"].startswith("/readVersions") and "float 1.0" in r["label"] and r["relation"] == "runtime-stricter" for r in rows),
        },
    }
    return {
        "inventoryVersion": "1",
        "schemasAt": schemas_at or "working-tree",
        "specification": "SPEC-069 T002 / REQ-002",
        "schemas": [
            {"path": str(AIM_SCHEMA.relative_to(ROOT)), "sha256": text_sha256(aim_text), "keywordsProbed": [{"pointer": p, "keyword": k} for p, k in keyword_log["aim"]]},
            {"path": str(GIT_SCHEMA.relative_to(ROOT)), "sha256": text_sha256(git_text), "keywordsProbed": [{"pointer": p, "keyword": k} for p, k in keyword_log["git"]]},
            {"path": None, "note": "analysis-input envelope: no published schema (REQ-003 / T003)"},
        ],
        "runtimeChecks": checks,
        "whitespaceSemantics": {
            "runtimeBlank": "Python str.strip() is empty (the validators)",
            "pythonOnlyBlank": [f"U+{ord(c):04X}" for c in PYTHON_ONLY_BLANK],
            "ecmascriptOnlyBlank": [f"U+{ord(c):04X}" for c in ECMASCRIPT_ONLY_BLANK],
            "note": "A schema pattern for 'not blank' would use ECMAScript \\s, which differs from Python on these characters; corpus strings avoid them (REQ-004).",
        },
        "semanticObservations": [semantic],
        "summary": summary,
        "rows": rows,
        "environment": {"python": sys.version.split()[0], "jsonschema": metadata.version("jsonschema")},
    }


def render(doc: dict) -> str:
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail when a committed inventory differs")
    args = parser.parse_args()
    status = 0
    for output, rev in ((OUTPUT, BASELINE_REV), (OUTPUT_AFTER, None)):
        if args.check and not output.exists():
            print(f"{output.name} is missing", file=sys.stderr)
            status = 1
            continue
        doc = build(rev)
        if args.check:
            committed = json.loads(output.read_text())
            committed.pop("environment", None)
            fresh = copy.deepcopy(doc)
            fresh.pop("environment", None)
            if committed != fresh:
                print(f"{output.name} is stale; rerun without --check", file=sys.stderr)
                status = 1
            else:
                print(f"{output.name} is current")
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render(doc))
        s = doc["summary"]
        print(f"{output.name}: probes={s['probes']} divergent={s['divergentProbes']} rootCauses={s['rootCauseCount']} thresholdExceeded={s['thresholdExceeded']}")
        for item in s["rootCauses"]:
            print(f"  {item['probeCount']:3d}  {item['rootCause']}")
        print("  observed 2026-11-05:", s["observedOn2026-11-05"])
    return status


if __name__ == "__main__":
    raise SystemExit(main())
