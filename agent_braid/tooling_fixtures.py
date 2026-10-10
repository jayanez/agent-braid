# SPDX-License-Identifier: AGPL-3.0-only
"""Pinned, owned synthetic inputs for prospective M4.5 evaluation preparation.

Loading and materializing these fixtures does not execute Agent Braid work,
create grants, contact a provider, or authorize capture.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.resources
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

from .git_process import GitCommandBudget, run_git

FIXTURE_INVENTORY_SHA256 = "db76e4ec30c0b09200d6cbdb7a6f863c577a4ac41d7dccbbbd7819f22c93446d"
PROMPTS_SHA256 = "1b5d94eece15b01e0409579adeb18d5da6564b1d5f01487b461197cbe198d3c2"
JOURNEY_CLASSES = (
    "analyze-interactions", "prepare-advisory-plan", "refuse-missing-grant",
    "execute-granted-batch-verify", "inspect-recover-interruption", "export-evidence",
)
_RUNTIME_CLASSES = frozenset(JOURNEY_CLASSES[1:5])
_FIXTURE_FILE = "fixture-inventory.json"
_PROMPTS_FILE = "prompts.json"
_MAX_INVENTORY_BYTES = 64 * 1024
_MAX_PROMPTS_BYTES = 8 * 1024
_MAX_DEFINITION_BYTES = 16 * 1024
_MAX_PROMPT_BYTES = 2 * 1024


class FixtureInventoryError(ValueError):
    """Pinned fixture inventory is absent, changed, or malformed."""


@dataclass(frozen=True)
class FixtureDefinition:
    fixture_id: str
    journey_class: str
    definition_sha256: str
    definition: Mapping[str, Any]


@dataclass(frozen=True)
class FixturePrompt:
    prompt_id: str
    journey_class: str
    text: str
    sha256: str


@dataclass(frozen=True)
class FixtureInventory:
    fixtures: tuple[FixtureDefinition, ...]
    prompts: tuple[FixturePrompt, ...]
    inventory_sha256: str
    prompts_sha256: str


@dataclass(frozen=True)
class FixtureInput:
    fixture_id: str
    journey_class: str
    definition_sha256: str
    input_sha256: str
    request: Mapping[str, Any]
    expected_oracle: Mapping[str, Any]
    scenario: Mapping[str, Any]
    repository_root: Path | None = None
    root_manifest: Mapping[str, Any] | None = None
    analysis_request: Mapping[str, Any] | None = None


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise FixtureInventoryError("fixture values must be bounded JSON data") from exc


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_bounded(resource: Any, limit: int, label: str) -> bytes:
    try:
        with resource.open("rb") as stream:
            raw = stream.read(limit + 1)
    except OSError as exc:
        raise FixtureInventoryError(f"{label} is unavailable") from exc
    if len(raw) > limit:
        raise FixtureInventoryError(f"{label} exceeds its {limit}-byte read limit")
    return raw


def load_inventory(
    *,
    source_checkout: bool = False,
    assets_dir: str | os.PathLike[str] | None = None,
) -> FixtureInventory:
    """Load pinned fixtures from installed resources or an explicit source checkout.

    `assets_dir` is an explicit source-path override intended for offline controls.
    """

    if assets_dir is not None and not source_checkout:
        raise FixtureInventoryError("assets_dir requires explicit source_checkout=True")
    if assets_dir is not None:
        root: Any = Path(assets_dir)
    elif source_checkout:
        root = Path(__file__).resolve().parent.parent / "examples" / "tooling"
    else:
        root = importlib.resources.files("agent_braid").joinpath("tooling_assets", "fixtures")
    fixture_raw = _read_bounded(root.joinpath(_FIXTURE_FILE), _MAX_INVENTORY_BYTES, "fixture inventory")
    prompt_raw = _read_bounded(root.joinpath(_PROMPTS_FILE), _MAX_PROMPTS_BYTES, "prompt inventory")
    if _sha256(fixture_raw) != FIXTURE_INVENTORY_SHA256:
        raise FixtureInventoryError("pinned fixture inventory hash mismatch")
    if _sha256(prompt_raw) != PROMPTS_SHA256:
        raise FixtureInventoryError("pinned prompt inventory hash mismatch")
    try:
        fixture_doc = json.loads(fixture_raw)
        prompt_doc = json.loads(prompt_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FixtureInventoryError("fixture inventory is not valid UTF-8 JSON") from exc
    if (not isinstance(fixture_doc, dict)
            or set(fixture_doc) != {"schemaVersion", "fixtureCount", "fixtures"}
            or fixture_doc["schemaVersion"] != "agent-braid-m45-fixtures-v1"
            or fixture_doc["fixtureCount"] != 18
            or not isinstance(fixture_doc["fixtures"], list)
            or len(fixture_doc["fixtures"]) != 18):
        raise FixtureInventoryError("fixture inventory must contain exactly 18 definitions")
    if (not isinstance(prompt_doc, dict)
            or set(prompt_doc) != {"schemaVersion", "promptCount", "prompts"}
            or prompt_doc["schemaVersion"] != "agent-braid-m45-prompts-v1"
            or prompt_doc["promptCount"] != 6
            or not isinstance(prompt_doc["prompts"], list)
            or len(prompt_doc["prompts"]) != 6):
        raise FixtureInventoryError("prompt inventory must contain exactly six prompts")

    fixtures: list[FixtureDefinition] = []
    seen_ids: set[str] = set()
    class_counts = {name: 0 for name in JOURNEY_CLASSES}
    for row in fixture_doc["fixtures"]:
        if (not isinstance(row, dict)
                or set(row) != {"fixtureId", "journeyClass", "definitionSha256", "definition"}):
            raise FixtureInventoryError("fixture entry has an invalid shape")
        fixture_id, journey = row["fixtureId"], row["journeyClass"]
        definition = row["definition"]
        if (not isinstance(fixture_id, str) or not isinstance(journey, str)
                or journey not in class_counts or fixture_id in seen_ids
                or fixture_id != f"m45-{journey}-{class_counts[journey] + 1:02d}"):
            raise FixtureInventoryError("fixture IDs and journey classes must match the fixed roster")
        raw_definition = canonical_json_bytes(definition)
        if len(raw_definition) > _MAX_DEFINITION_BYTES:
            raise FixtureInventoryError("fixture definition exceeds the 16 KiB bound")
        if _sha256(raw_definition) != row["definitionSha256"]:
            raise FixtureInventoryError(f"fixture definition hash mismatch: {fixture_id}")
        _validate_definition(fixture_id, journey, definition)
        seen_ids.add(fixture_id)
        class_counts[journey] += 1
        fixtures.append(FixtureDefinition(fixture_id, journey, row["definitionSha256"], definition))
    if any(count != 3 for count in class_counts.values()):
        raise FixtureInventoryError("each journey class must have exactly three fixtures")

    prompts: list[FixturePrompt] = []
    prompt_classes: set[str] = set()
    for row in prompt_doc["prompts"]:
        if (not isinstance(row, dict)
                or set(row) != {"promptId", "journeyClass", "text", "sha256"}):
            raise FixtureInventoryError("prompt entry has an invalid shape")
        prompt_id, journey, text = row["promptId"], row["journeyClass"], row["text"]
        if (not isinstance(journey, str) or journey not in class_counts
                or not isinstance(prompt_id, str) or prompt_id != f"m45-prompt-{journey}"
                or journey in prompt_classes or not isinstance(text, str) or not text.strip()
                or len(text.encode("utf-8")) > _MAX_PROMPT_BYTES
                or any(ord(c) < 32 and c not in "\n\t" for c in text)):
            raise FixtureInventoryError("prompt IDs, classes, or text are invalid")
        if _sha256(text.encode("utf-8")) != row["sha256"]:
            raise FixtureInventoryError(f"prompt text hash mismatch: {prompt_id}")
        prompt_classes.add(journey)
        prompts.append(FixturePrompt(prompt_id, journey, text, row["sha256"]))
    if prompt_classes != set(JOURNEY_CLASSES):
        raise FixtureInventoryError("exactly one fixed prompt is required for each journey class")
    return FixtureInventory(tuple(fixtures), tuple(prompts), _sha256(fixture_raw), _sha256(prompt_raw))


def _validate_definition(fixture_id: str, journey: str, definition: Any) -> None:
    if not isinstance(definition, dict) or definition.get("journeyClass") != journey:
        raise FixtureInventoryError(f"fixture journey mismatch: {fixture_id}")
    scenario = definition.get("scenario")
    if (not isinstance(scenario, dict)
            or set(scenario) != {"preconditions", "phases", "expectedOutcomes", "contextStatus"}
            or any(not isinstance(scenario[key], list) or not scenario[key]
                   or any(not isinstance(value, str) or not value.strip() or len(value) > 512
                          for value in scenario[key])
                   for key in ("preconditions", "phases", "expectedOutcomes"))
            or not isinstance(scenario["contextStatus"], str)
            or not scenario["contextStatus"].strip()
            or len(scenario["contextStatus"]) > 512):
        raise FixtureInventoryError(f"fixture scenario requirements are invalid: {fixture_id}")
    if definition.get("kind") == "aim":
        if journey not in {JOURNEY_CLASSES[0], JOURNEY_CLASSES[-1]}:
            raise FixtureInventoryError("runtime journey classes require Git runtime fixtures")
        if set(definition) != {"kind", "journeyClass", "seed", "request", "expected", "scenario"}:
            raise FixtureInventoryError(f"AIM fixture fields are invalid: {fixture_id}")
        request = definition["request"]
        if (not isinstance(request, dict)
                or set(request) != {"analysisInputVersion", "source", "operations"}
                or request.get("analysisInputVersion") != "0.1.0-alpha"
                or not isinstance(request.get("operations"), list)
                or len(request["operations"]) != 2):
            raise FixtureInventoryError(f"AIM request shape is invalid: {fixture_id}")
        ids = [record.get("instanceId") for record in request["operations"] if isinstance(record, dict)]
        if len(ids) != 2 or len(set(ids)) != 2 or not all(isinstance(item, str) and item.startswith(fixture_id + "-") for item in ids):
            raise FixtureInventoryError(f"AIM operation identities must be fixture-unique: {fixture_id}")
        interaction = definition["expected"].get("interactionClassification")
        coverage = definition["expected"].get("coverageStatus")
        if (interaction not in {"independent-candidate", "conflicting", "unknown"}
                or coverage not in {"complete", "unknown"}):
            raise FixtureInventoryError(f"AIM fixture must carry a fixed known/unknown rubric oracle: {fixture_id}")
    elif definition.get("kind") == "git-runtime":
        if journey not in _RUNTIME_CLASSES:
            raise FixtureInventoryError("only runtime journey classes may use Git runtime fixtures")
        if set(definition) != {"kind", "journeyClass", "seed", "recipe", "runtimeRequestTemplate", "expected", "scenario"}:
            raise FixtureInventoryError(f"Git runtime fixture fields are invalid: {fixture_id}")
        recipe = definition["recipe"]
        if (not isinstance(recipe, dict) or set(recipe) != {"version", "baseFile", "baseText", "operations"}
                or recipe.get("version") != "synthetic-git-runtime-recipe-v1"
                or not isinstance(recipe["baseFile"], str) or not isinstance(recipe["baseText"], str)
                or not isinstance(recipe["operations"], list) or len(recipe["operations"]) != 2):
            raise FixtureInventoryError(f"synthetic Git runtime recipe is invalid: {fixture_id}")
        _safe_relative_file(recipe["baseFile"], fixture_id)
        operation_ids: list[str] = []
        operation_paths: list[str] = []
        for operation in recipe["operations"]:
            if (not isinstance(operation, dict) or set(operation) != {"instanceId", "attemptId", "path", "text"}
                    or not all(isinstance(operation[key], str) and operation[key] for key in operation)):
                raise FixtureInventoryError(f"synthetic Git operation is invalid: {fixture_id}")
            if not operation["instanceId"].startswith(fixture_id + "-") or not operation["attemptId"].startswith(fixture_id + "-"):
                raise FixtureInventoryError(f"runtime operation identities must be fixture-unique: {fixture_id}")
            _safe_relative_file(operation["path"], fixture_id)
            operation_ids.append(operation["instanceId"])
            operation_paths.append(operation["path"])
        if len(set(operation_ids)) != 2 or len(set(operation_paths)) != 2 or recipe["baseFile"] in operation_paths:
            raise FixtureInventoryError(f"runtime recipe paths and operation IDs must be distinct: {fixture_id}")
        template = definition["runtimeRequestTemplate"]
        if (not isinstance(template, dict) or set(template) != {
                "gitRuntimeRequestVersion", "repository", "baseRevision", "expectedFinalTree", "order", "operations"}
                or template["gitRuntimeRequestVersion"] != "0.1.0-alpha"
                or template["repository"] != "$REPOSITORY"
                or template["baseRevision"] != "$BASE_COMMIT"
                or template["expectedFinalTree"] != "$EXPECTED_FINAL_TREE"
                or template["order"] != operation_ids
                or not isinstance(template["operations"], list) or len(template["operations"]) != 2):
            raise FixtureInventoryError(f"runtime request template is invalid: {fixture_id}")
        for template_op, recipe_op in zip(template["operations"], recipe["operations"]):
            if (not isinstance(template_op, dict) or set(template_op) != {
                    "instanceId", "attemptId", "source", "dependencies", "uncertainPaths", "declaredWrites"}
                    or template_op["instanceId"] != recipe_op["instanceId"]
                    or template_op["attemptId"] != recipe_op["attemptId"]
                    or template_op["source"] != {"kind": "commit", "revision": "$COMMIT:" + recipe_op["instanceId"]}
                    or template_op["dependencies"] != [] or template_op["uncertainPaths"] != []
                    or template_op["declaredWrites"] != [recipe_op["path"]]):
                raise FixtureInventoryError(f"runtime operation template is invalid: {fixture_id}")
        if definition["expected"].get("interactionClassification") != "independent-candidate":
            raise FixtureInventoryError(f"runtime Git oracle must be independent-candidate: {fixture_id}")
        preconditions = " ".join(scenario["preconditions"]).lower()
        context = scenario["contextStatus"].lower()
        if journey == "execute-granted-batch-verify" and not (
                "already supplied" in preconditions and "operator" in preconditions
                and "none embedded" in context):
            raise FixtureInventoryError(f"execute fixture must require a pre-existing operator grant: {fixture_id}")
        if journey == "inspect-recover-interruption" and not (
                "already interrupted" in preconditions and "matching resume grant" in preconditions
                and "not materialized" in context):
            raise FixtureInventoryError(f"recovery fixture must require interrupted-run context and grant: {fixture_id}")
    else:
        raise FixtureInventoryError(f"unsupported fixture kind: {fixture_id}")
    expected = definition.get("expected")
    if not isinstance(expected, dict) or "claimLimit" not in expected:
        raise FixtureInventoryError(f"fixture oracle metadata is invalid: {fixture_id}")


def _safe_relative_file(value: str, fixture_id: str) -> None:
    path = Path(value)
    if (not value or len(value) > 128 or path.is_absolute() or ".." in path.parts
            or "/" in value or "\\" in value or "\0" in value
            or any(part.lower() in {"", ".", "..", ".git"} for part in path.parts)):
        raise FixtureInventoryError(f"synthetic Git path is unsafe: {fixture_id}")


def fixture_input(inventory: FixtureInventory, fixture_id: str) -> FixtureInput:
    """Resolve an immutable AIM fixture request without filesystem effects."""

    definition = _find_fixture(inventory, fixture_id)
    if definition.definition["kind"] != "aim":
        raise FixtureInventoryError("Git runtime fixture needs explicit private-temp materialization")
    request = definition.definition["request"]
    return FixtureInput(
        definition.fixture_id, definition.journey_class, definition.definition_sha256,
        _sha256(canonical_json_bytes(request)), request, definition.definition["expected"],
        definition.definition["scenario"],
    )


def materialize_fixture(
    inventory: FixtureInventory,
    fixture_id: str,
    destination: str | os.PathLike[str],
) -> FixtureInput:
    """Create only a recipe-owned synthetic Git repository in a new private temp dir."""

    definition = _find_fixture(inventory, fixture_id)
    if definition.definition["kind"] != "git-runtime":
        raise FixtureInventoryError("only runtime Git recipes create a temporary repository")
    # The inventory/definition/paths are revalidated above, before destination creation.
    root = _new_temp_destination(destination)
    recipe = definition.definition["recipe"]
    template = definition.definition["runtimeRequestTemplate"]
    repository = root / "repository"
    home = root / "private-home"
    temp = root / "private-tmp"
    repository.mkdir(mode=0o700)
    home.mkdir(mode=0o700)
    temp.mkdir(mode=0o700)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home),
        "TMPDIR": str(temp), "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0", "GIT_ALLOW_PROTOCOL": "file",
        "GIT_PROTOCOL_FROM_USER": "0", "GIT_AUTHOR_NAME": "Agent Braid Synthetic Fixture",
        "GIT_AUTHOR_EMAIL": "synthetic-fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Agent Braid Synthetic Fixture",
        "GIT_COMMITTER_EMAIL": "synthetic-fixture@example.invalid",
        "GIT_AUTHOR_DATE": "2001-01-01T00:00:00+0000",
        "GIT_COMMITTER_DATE": "2001-01-01T00:00:00+0000",
    }
    budget = GitCommandBudget(temp_root=root, wall_seconds=30, max_commands=48,
                              max_output_bytes=1024 * 1024,
                              max_command_output_bytes=256 * 1024,
                              max_scratch_bytes=16 * 1024 * 1024)

    def git(*args: str, input_bytes: bytes | None = None) -> bytes:
        return run_git(repository, ("-c", "core.hooksPath=/dev/null", *args),
                       env=env, budget=budget, input_bytes=input_bytes,
                       command_timeout=10).stdout

    try:
        git("init", "--template=", "--quiet")
        (repository / ".git").chmod(0o700)
        base_blob = git("hash-object", "-w", "--stdin", input_bytes=recipe["baseText"].encode()).decode().strip()
        base_tree = _make_tree(git, [(recipe["baseFile"], base_blob)])
        base_commit = git("commit-tree", base_tree, "-m", f"synthetic base {fixture_id}").decode().strip()
        git("update-ref", "refs/heads/base", base_commit)
        git("symbolic-ref", "HEAD", "refs/heads/base")
        operation_commits: dict[str, str] = {}
        operation_blobs: list[tuple[str, str]] = [(recipe["baseFile"], base_blob)]
        for operation in recipe["operations"]:
            blob = git("hash-object", "-w", "--stdin", input_bytes=operation["text"].encode()).decode().strip()
            operation_blobs.append((operation["path"], blob))
            tree = _make_tree(git, [(recipe["baseFile"], base_blob), (operation["path"], blob)])
            commit = git("commit-tree", tree, "-p", base_commit,
                         "-m", f"synthetic {operation['instanceId']}").decode().strip()
            git("update-ref", f"refs/heads/{operation['instanceId']}", commit)
            operation_commits[operation["instanceId"]] = commit
        final_tree = _make_tree(git, operation_blobs)
        operations = []
        for op in template["operations"]:
            item = dict(op)
            item["source"] = {"kind": "commit", "revision": operation_commits[item["instanceId"]]}
            operations.append(item)
        request = {
            "gitRuntimeRequestVersion": template["gitRuntimeRequestVersion"],
            "repository": str(repository.resolve(strict=True)),
            "baseRevision": base_commit,
            "expectedFinalTree": final_tree,
            "order": list(template["order"]),
            "operations": operations,
        }
        analysis_request = {
            "gitAnalysisRequestVersion": request["gitRuntimeRequestVersion"],
            "repository": request["repository"], "baseRevision": base_commit,
            "operations": [{key: value for key, value in op.items() if key != "declaredWrites"}
                           for op in operations],
        }
        input_sha = _sha256(canonical_json_bytes(request))
        manifest = {
            "fixtureId": fixture_id, "journeyClass": definition.journey_class,
            "definitionSha256": definition.definition_sha256, "inputSha256": input_sha,
            "repositoryRoot": str(repository), "baseCommit": base_commit,
            "expectedFinalTree": final_tree, "operationCommits": operation_commits,
            "createdPaths": ["repository/.git", "private-home", "private-tmp"],
            "effects": "owned synthetic Git objects and refs only; no hooks, remotes, checkout, grant, or product runtime",
        }
        return FixtureInput(
            fixture_id, definition.journey_class, definition.definition_sha256,
            input_sha, request, definition.definition["expected"], definition.definition["scenario"], repository, manifest,
            analysis_request,
        )
    except BaseException:
        shutil.rmtree(root, ignore_errors=True)
        raise


def _make_tree(git, entries: list[tuple[str, str]]) -> str:
    payload = b"".join(
        f"100644 blob {blob}\t{name}\0".encode("utf-8")
        for name, blob in sorted(entries)
    )
    return git("mktree", "-z", input_bytes=payload).decode().strip()


def _find_fixture(inventory: FixtureInventory, fixture_id: str) -> FixtureDefinition:
    _require_inventory(inventory)
    for fixture in inventory.fixtures:
        if fixture.fixture_id == fixture_id:
            # Rehash and validate at each use; frozen dataclasses do not freeze nested maps.
            if _sha256(canonical_json_bytes(fixture.definition)) != fixture.definition_sha256:
                raise FixtureInventoryError(f"fixture definition changed after loading: {fixture_id}")
            _validate_definition(fixture.fixture_id, fixture.journey_class, fixture.definition)
            return fixture
    raise FixtureInventoryError(f"unknown fixture ID: {fixture_id}")


def _require_inventory(inventory: FixtureInventory) -> None:
    if not isinstance(inventory, FixtureInventory):
        raise FixtureInventoryError("a verified fixture inventory is required")
    fixture_doc = {
        "schemaVersion": "agent-braid-m45-fixtures-v1", "fixtureCount": len(inventory.fixtures),
        "fixtures": [{"fixtureId": item.fixture_id, "journeyClass": item.journey_class,
                      "definitionSha256": item.definition_sha256, "definition": item.definition}
                     for item in inventory.fixtures],
    }
    prompt_doc = {
        "schemaVersion": "agent-braid-m45-prompts-v1", "promptCount": len(inventory.prompts),
        "prompts": [{"promptId": item.prompt_id, "journeyClass": item.journey_class,
                     "text": item.text, "sha256": item.sha256} for item in inventory.prompts],
    }
    fixture_raw = canonical_json_bytes(fixture_doc) + b"\n"
    prompt_raw = canonical_json_bytes(prompt_doc) + b"\n"
    if (_sha256(fixture_raw) != FIXTURE_INVENTORY_SHA256
            or _sha256(fixture_raw) != inventory.inventory_sha256):
        raise FixtureInventoryError("loaded fixture inventory was changed after verification")
    if (_sha256(prompt_raw) != PROMPTS_SHA256 or _sha256(prompt_raw) != inventory.prompts_sha256):
        raise FixtureInventoryError("loaded prompt inventory was changed after verification")


def _new_temp_destination(value: str | os.PathLike[str]) -> Path:
    requested = Path(value).expanduser().absolute()
    if requested.exists() or requested.is_symlink():
        raise FixtureInventoryError("fixture destination must be a new path")
    try:
        parent = requested.parent.resolve(strict=True)
        temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
    except OSError as exc:
        raise FixtureInventoryError("fixture destination parent must already exist") from exc
    if not parent.is_relative_to(temp_root):
        raise FixtureInventoryError("fixture destination must be under a path in the system temp directory")
    canonical = parent / requested.name
    if canonical.exists() or canonical.is_symlink():
        raise FixtureInventoryError("fixture destination must be a new path")
    current = parent
    while current != temp_root and current != current.parent:
        if (current / ".git").exists():
            raise FixtureInventoryError("fixture destination cannot be inside a Git repository")
        current = current.parent
    canonical.mkdir(mode=0o700)
    return canonical


__all__ = [
    "FIXTURE_INVENTORY_SHA256", "JOURNEY_CLASSES", "PROMPTS_SHA256",
    "FixtureDefinition", "FixtureInput", "FixtureInventory", "FixtureInventoryError",
    "FixturePrompt", "canonical_json_bytes", "fixture_input", "load_inventory",
    "materialize_fixture",
]
