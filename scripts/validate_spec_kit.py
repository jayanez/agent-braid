#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Dependency-free structural gates, not a constitutional semantic proof."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from constitution_replica import sync

COMMANDS = {"analyze", "checklist", "clarify", "constitution", "converge",
            "implement", "plan", "specify", "tasks", "taskstoissues"}
AUTHORITIES = ("CONSTITUTION.md", "GOVERNANCE.md", "ARCHITECTURE.md",
               "MATHEMATICAL_FOUNDATIONS.md", "RESEARCH.md", "TERMINOLOGY.md",
               "LICENSE", "TRADEMARKS.md")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local(root, name):
    path = (root / name).resolve()
    if path == root.resolve() or not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Missing or unsafe repository reference: {name}")
    return path


def safe_name(root, name):
    if not isinstance(name, str) or not name:
        raise ValueError(f"Missing or unsafe repository reference: {name}")
    path = (root / name).resolve()
    if path == root.resolve() or not path.is_relative_to(root.resolve()):
        raise ValueError(f"Missing or unsafe repository reference: {name}")
    return Path(name).as_posix()


def authorities(root):
    paths = set(AUTHORITIES)
    for folder in ("docs/adr", "docs/theory", "docs/architecture", "schemas"):
        paths.update(p.relative_to(root).as_posix() for p in (root / folder).rglob("*")
                     if p.is_file())
    return {name: digest(local(root, name)) for name in sorted(paths)}


def git(root, *args):
    process = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    if process.returncode:
        message = process.stderr.decode("utf-8", "replace").strip()
        raise ValueError(f"Git history required for authority validation: {message or args[0]}")
    return process.stdout


def authorities_at_commit(root, commit):
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Historical authority snapshot requires a full commit hash")
    git(root, "cat-file", "-e", f"{commit}^{{commit}}")
    paths = set(AUTHORITIES)
    paths.update(git(
        root, "ls-tree", "-r", "--name-only", commit, "--",
        "docs/adr", "docs/theory", "docs/architecture", "schemas",
    ).decode("utf-8").splitlines())
    return {
        name: hashlib.sha256(git(root, "show", f"{commit}:{name}")).hexdigest()
        for name in sorted(paths)
    }


def snapshot(root, feature):
    path = local(root, f"{feature}/assurance.json")
    if not path.is_relative_to((root / "specs").resolve()):
        raise ValueError("Assurance records must be under specs/")
    record = json.loads(path.read_text())
    record.pop("authority_hashes", None)
    record["authority_snapshot"] = {
        "mode": "current", "commit": None, "hashes": authorities(root)
    }
    record["evidence_snapshot"] = {"mode": "current", "commit": None}
    record["human_review"] = "pending"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


def freeze(root, feature):
    path = local(root, f"{feature}/assurance.json")
    if not path.is_relative_to((root / "specs").resolve()):
        raise ValueError("Assurance records must be under specs/")
    if git(root, "status", "--porcelain"):
        raise ValueError("Authority freeze requires a clean candidate commit")
    commit = git(root, "rev-parse", "HEAD").decode("ascii").strip()
    current = authorities(root)
    if current != authorities_at_commit(root, commit):
        raise ValueError("Candidate commit does not contain the current authority inventory")
    record = json.loads(path.read_text())
    record.pop("authority_hashes", None)
    record["authority_snapshot"] = {
        "mode": "historical", "commit": commit, "hashes": current
    }
    record["evidence_snapshot"] = {"mode": "historical", "commit": commit}
    record["human_review"] = "pending"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing {label}")


def validate_record(root, path):
    record = json.loads(path.read_text())
    if "authority_hashes" in record:
        raise ValueError("Legacy authority_hashes must be migrated to authority_snapshot")
    authority_snapshot = record.get("authority_snapshot")
    if not isinstance(authority_snapshot, dict) or set(authority_snapshot) != {
            "mode", "commit", "hashes"}:
        raise ValueError("Complete authority_snapshot required")
    mode = authority_snapshot["mode"]
    if mode == "current":
        if authority_snapshot["commit"] is not None or \
                authority_snapshot["hashes"] != authorities(root):
            raise ValueError("Stale or incomplete current authority snapshot")
        if record.get("human_review") == "approved":
            raise ValueError("Approval requires a frozen historical authority snapshot")
    elif mode == "historical":
        expected = authorities_at_commit(root, authority_snapshot["commit"])
        if authority_snapshot["hashes"] != expected:
            raise ValueError("Historical authority snapshot does not match its commit")
    else:
        raise ValueError("authority_snapshot mode must be current or historical")
    evidence_snapshot = record.get("evidence_snapshot")
    if not isinstance(evidence_snapshot, dict) or set(evidence_snapshot) != {"mode", "commit"}:
        raise ValueError("Complete evidence_snapshot required")
    evidence_mode = evidence_snapshot["mode"]
    if evidence_mode == "current":
        if evidence_snapshot["commit"] is not None:
            raise ValueError("Current evidence snapshot cannot name a commit")
        if record.get("human_review") == "approved":
            raise ValueError("Approval requires a frozen historical evidence snapshot")
    elif evidence_mode == "historical":
        evidence_commit = evidence_snapshot["commit"]
        if not isinstance(evidence_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", evidence_commit):
            raise ValueError("Historical evidence snapshot requires a full commit hash")
        git(root, "cat-file", "-e", f"{evidence_commit}^{{commit}}")
    else:
        raise ValueError("evidence_snapshot mode must be current or historical")
    if record.get("stage") not in ("draft", "validated"):
        raise ValueError("stage must be draft or validated")
    if record.get("human_review") not in ("pending", "approved", "changes-requested"):
        raise ValueError("Explicit human_review required")
    if record["human_review"] == "approved":
        review = json.loads(local(root, record.get("review_record", "")).read_text())
        if review.get("reviewedCommit") != authority_snapshot["commit"]:
            raise ValueError("Approved review does not match the historical authority commit")
    for field in ("scope", "assumptions", "domain", "observation_contract",
                  "execution_contract", "scientific_limits", "compatibility", "hypotheses"):
        nonempty(record.get(field), field)
    articles = record.get("articles")
    if not isinstance(articles, list) or not articles or any(
            type(a) is not int or a not in range(0, 26) for a in articles):
        raise ValueError("Article references must use 0 (clause zero) through 25")
    if not record.get("references"):
        raise ValueError("Document references required")
    for name in record["references"]:
        if evidence_mode == "historical":
            name = safe_name(root, name)
            git(root, "cat-file", "-e", f"{evidence_snapshot['commit']}:{name}")
        else:
            local(root, name)
    requirements = record.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("Identifiable requirements required")
    ids, scenario_ids = set(), set()
    for req in requirements:
        identifier = req.get("id", "")
        if not re.fullmatch(r"REQ-\d{3,}", identifier) or identifier in ids:
            raise ValueError("Invalid or duplicate requirement ID")
        ids.add(identifier)
        nonempty(req.get("text"), "requirement text")
        if not req.get("scenarios"):
            raise ValueError("Acceptance scenarios required")
        for scenario in req["scenarios"]:
            identifier = scenario.get("id", "")
            if not re.fullmatch(r"SC-\d{3,}", identifier) or identifier in scenario_ids:
                raise ValueError("Invalid or duplicate scenario ID")
            scenario_ids.add(identifier)
            for field in ("given", "when", "then", "planned_evidence"):
                nonempty(scenario.get(field), field)
            test_file = local(root, scenario.get("test_file", ""))
            nonempty(scenario.get("test_name"), "test name")
            if test_file.suffix == ".py":
                tree = ast.parse(test_file.read_text())
                names = {f"{node.name}.{method.name}" for node in tree.body
                         if isinstance(node, ast.ClassDef) for method in node.body
                         if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))}
                names.update(node.name for node in tree.body if isinstance(node, ast.FunctionDef))
                if scenario["test_name"] not in names:
                    raise ValueError("Test reference does not identify a Python test definition")
            evidence = scenario.get("obtained_evidence")
            if not isinstance(evidence, list) or (record["stage"] == "validated" and not evidence):
                raise ValueError("Required obtained evidence absent")
            for item in evidence:
                if evidence_mode == "historical":
                    artifact_name = safe_name(root, item.get("path", ""))
                    artifact_bytes = git(
                        root, "show", f"{evidence_snapshot['commit']}:{artifact_name}"
                    )
                    artifact_digest = hashlib.sha256(artifact_bytes).hexdigest()
                    data = json.loads(artifact_bytes) if Path(artifact_name).suffix == ".json" else None
                else:
                    artifact = local(root, item.get("path", ""))
                    artifact_digest = digest(artifact)
                    data = json.loads(artifact.read_text()) if artifact.suffix == ".json" else None
                if item.get("sha256") != artifact_digest:
                    raise ValueError("Evidence artifact missing or changed")
                if isinstance(data, dict) and "inputs" in data:
                    for name, checksum in data["inputs"].items():
                        if evidence_mode == "historical":
                            observed = hashlib.sha256(git(
                                root, "show", f"{evidence_snapshot['commit']}:{name}"
                            )).hexdigest()
                        else:
                            observed = digest(local(root, name))
                        if observed != checksum:
                            raise ValueError(f"Stale evidence input: {name}")
                for field in ("command", "outcome", "limits"):
                    nonempty(item.get(field), field)


def validate_portable_record(root, path, bind_manifest=True):
    """Validate exported record structure without pretending private Git is present."""
    try:
        from scripts.publication import load_manifest, manifest_entry, root_manifest_payload
    except ModuleNotFoundError:
        from publication import load_manifest, manifest_entry, root_manifest_payload

    root = root.resolve()
    relative_record = path.resolve().relative_to(root).as_posix()
    manifest = load_manifest(root)
    protected = set(manifest["protectedPaths"])
    if bind_manifest and relative_record in protected:
        manifest_entry(root, relative_record)
    record = json.loads(path.read_text())
    authority_candidate = record.get("authority_snapshot", {})
    evidence_candidate = record.get("evidence_snapshot", {})
    if authority_candidate.get("mode") == "historical" \
            and evidence_candidate.get("mode") == "historical" \
            and all(isinstance(item.get("commit"), str)
                    and re.fullmatch(r"[0-9a-f]{40}", item["commit"])
                    for item in (authority_candidate, evidence_candidate)):
        commits_available = all(subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{item['commit']}^{{commit}}"],
            capture_output=True, check=False,
        ).returncode == 0 for item in (authority_candidate, evidence_candidate))
        if commits_available:
            validate_record(root, path)
            return
    if "authority_hashes" in record:
        raise ValueError("Legacy authority_hashes must be migrated to authority_snapshot")
    authority = record.get("authority_snapshot")
    if not isinstance(authority, dict) or set(authority) != {"mode", "commit", "hashes"} \
            or authority.get("mode") not in {"current", "historical"} \
            or not isinstance(authority.get("hashes"), dict) or not authority["hashes"]:
        raise ValueError("Complete portable authority_snapshot required")
    if authority["mode"] == "historical" \
            and (not isinstance(authority.get("commit"), str)
                 or not re.fullmatch(r"[0-9a-f]{40}", authority["commit"])):
        raise ValueError("Portable historical authority requires its private commit identity")
    if authority["mode"] == "current":
        if authority.get("commit") is not None \
                or authority.get("hashes") != authorities(root):
            raise ValueError("Stale or incomplete current authority snapshot")
    if any(not isinstance(name, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
           for name, value in authority["hashes"].items()):
        raise ValueError("Portable authority snapshot contains invalid hashes")
    evidence_snapshot = record.get("evidence_snapshot")
    if not isinstance(evidence_snapshot, dict) or set(evidence_snapshot) != {"mode", "commit"} \
            or evidence_snapshot.get("mode") not in {"current", "historical"}:
        raise ValueError("Complete portable evidence_snapshot required")
    if evidence_snapshot["mode"] == "historical" \
            and (not isinstance(evidence_snapshot.get("commit"), str)
                 or not re.fullmatch(r"[0-9a-f]{40}", evidence_snapshot["commit"])):
        raise ValueError("Portable historical evidence requires its private commit identity")
    if evidence_snapshot["mode"] == "current" \
            and evidence_snapshot.get("commit") is not None:
        raise ValueError("Current evidence snapshot cannot name a commit")
    if record.get("stage") not in ("draft", "validated") \
            or record.get("human_review") not in ("pending", "approved", "changes-requested"):
        raise ValueError("Portable assurance stage or human review is invalid")
    if record["human_review"] == "approved":
        review_name = safe_name(root, record.get("review_record", ""))
        if authority["mode"] != "historical" or evidence_snapshot["mode"] != "historical":
            raise ValueError("Approval requires frozen historical snapshot identities")
        if bind_manifest and review_name in protected:
            review_bytes = root_manifest_payload(root, review_name)
        else:
            review_bytes = local(root, review_name).read_bytes()
        review = json.loads(review_bytes)
        if review.get("reviewedCommit") != authority["commit"]:
            raise ValueError("Approved review does not match the historical authority commit")
    for field in ("scope", "assumptions", "domain", "observation_contract",
                  "execution_contract", "scientific_limits", "compatibility", "hypotheses"):
        nonempty(record.get(field), field)
    articles = record.get("articles")
    if not isinstance(articles, list) or not articles or any(
            type(value) is not int or value not in range(0, 26) for value in articles):
        raise ValueError("Portable article references are invalid")
    if not isinstance(record.get("references"), list) or not record["references"]:
        raise ValueError("Portable document references are required")
    for name in record["references"]:
        relative = safe_name(root, name)
        if evidence_snapshot["mode"] == "historical":
            root_manifest_payload(root, relative)
        else:
            local(root, relative)
    requirements = record.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("Portable identifiable requirements are required")
    requirement_ids, scenario_ids = set(), set()
    for requirement in requirements:
        identifier = requirement.get("id", "")
        if not re.fullmatch(r"REQ-\d{3,}", identifier) or identifier in requirement_ids:
            raise ValueError("Invalid or duplicate portable requirement ID")
        requirement_ids.add(identifier)
        nonempty(requirement.get("text"), "requirement text")
        scenarios = requirement.get("scenarios")
        if not isinstance(scenarios, list) or not scenarios:
            raise ValueError("Portable acceptance scenarios are required")
        for scenario in scenarios:
            scenario_id = scenario.get("id", "")
            if not re.fullmatch(r"SC-\d{3,}", scenario_id) or scenario_id in scenario_ids:
                raise ValueError("Invalid or duplicate portable scenario ID")
            scenario_ids.add(scenario_id)
            for field in ("given", "when", "then", "planned_evidence", "test_name"):
                nonempty(scenario.get(field), field)
            test_path = local(root, safe_name(root, scenario.get("test_file", "")))
            if test_path.suffix == ".py":
                tree = ast.parse(test_path.read_text())
                names = {f"{node.name}.{method.name}" for node in tree.body
                         if isinstance(node, ast.ClassDef) for method in node.body
                         if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))}
                names.update(node.name for node in tree.body if isinstance(node, ast.FunctionDef))
                if scenario["test_name"] not in names:
                    raise ValueError("Test reference does not identify a Python test definition")
            obtained = scenario.get("obtained_evidence")
            if not isinstance(obtained, list) or (record["stage"] == "validated" and not obtained):
                raise ValueError("Required obtained evidence absent")
            for item in obtained:
                relative = safe_name(root, item.get("path", ""))
                if evidence_snapshot["mode"] == "historical":
                    artifact_bytes = root_manifest_payload(root, relative)
                    artifact_digest = hashlib.sha256(artifact_bytes).hexdigest()
                    data = json.loads(artifact_bytes) if Path(relative).suffix == ".json" else None
                else:
                    artifact = local(root, relative)
                    artifact_digest = digest(artifact)
                    data = json.loads(artifact.read_text()) if artifact.suffix == ".json" else None
                if item.get("sha256") != artifact_digest:
                    raise ValueError("Evidence artifact missing or changed")
                if isinstance(data, dict) and "inputs" in data:
                    for name, checksum in data["inputs"].items():
                        if evidence_snapshot["mode"] == "historical":
                            # The clean root contains the selected current tree,
                            # not every historical version named by inherited
                            # evidence. Keep the path present and the recorded
                            # checksum well formed without pretending the private
                            # input bytes can be reconstructed.
                            root_manifest_payload(root, safe_name(root, name))
                            if not re.fullmatch(r"[0-9a-f]{64}", str(checksum)):
                                raise ValueError(f"Historical evidence input hash is invalid: {name}")
                            continue
                        else:
                            observed = digest(local(root, name))
                        if observed != checksum:
                            raise ValueError(f"Stale evidence input: {name}")
                for field in ("command", "outcome", "limits"):
                    nonempty(item.get(field), field)


def check(root=ROOT, require_both=True):
    root = root.resolve()
    sync(root)
    portable = (root / "docs/releases/public-export.json").is_file()
    if portable:
        try:
            from scripts.publication import validate_portable_root
        except ModuleNotFoundError:
            from publication import validate_portable_root
        validate_portable_root(root)
    state = json.loads(local(root, ".specify/integration.json").read_text())
    installed = state.get("installed_integrations", [])
    if (state.get("version") != "1.0.7" or not installed or
            set(installed) - {"codex", "claude"} or len(installed) != len(set(installed)) or
            (require_both and set(installed) != {"codex", "claude"}) or
            state.get("default_integration") not in installed or
            state.get("integration") != state.get("default_integration")):
        raise ValueError("Incompatible Spec Kit integration configuration")
    options = json.loads(local(root, ".specify/init-options.json").read_text())
    if options.get("script") != "py" or options.get("speckit_version") != "1.0.7":
        raise ValueError("Incompatible Spec Kit initialization options")
    for agent in installed:
        if state.get("integration_settings", {}).get(agent, {}).get("script") != "py":
            raise ValueError("Integration script configuration must be py")
    # No preset/extension/hook layer has been approved for this integration.
    for name in ("presets", "extensions", "workflows"):
        if any(p.is_file() for p in (root / ".specify" / name).rglob("*")):
            raise ValueError(f"Unapproved {name} configuration (including constitution-sync)")
    for name in ("extensions.yml", "presets.yml", "memory/.constitution-template.json"):
        if (root / ".specify" / name).exists():
            raise ValueError(f"Incompatible configuration: {name}")
    for folder in (".claude/commands", ".codex/prompts"):
        if any((root / folder).glob("speckit*")):
            raise ValueError("Legacy command integration could shadow reviewed skills")
    lock = json.loads(local(root, ".specify/generation.json").read_text())
    if lock.get("version") != "1.0.7" or lock.get("commit") != "fe1d00e3ccaf495880aaf90fb0e17679e82f065b":
        raise ValueError("Unpinned Spec Kit generation")
    sources = {p.relative_to(root).as_posix() for p in
               (root / ".specify/templates/overrides").rglob("*") if p.is_file()}
    if set(lock["sources"]) != sources | {"scripts/spec_kit.py", "requirements-speckit.txt"}:
        raise ValueError("Override source inventory drift")
    for section in ("sources", "outputs"):
        for name, checksum in lock[section].items():
            if digest(local(root, name)) != checksum:
                raise ValueError(f"Generated integration drift ({section}): {name}")
    for folder in (".specify/scripts", ".specify/templates"):
        for path in (root / folder).rglob("*"):
            if path.is_file() and "overrides" not in path.parts and "__pycache__" not in path.parts:
                if path.relative_to(root).as_posix() not in lock["outputs"]:
                    raise ValueError("Unexpected generated scaffold file")
    for agent in installed:
        folder = ".agents" if agent == "codex" else ".claude"
        actual = {p.parent.name.removeprefix("speckit-") for p in
                  (root / folder / "skills").glob("speckit-*/SKILL.md")}
        if actual != COMMANDS:
            raise ValueError(f"Incomplete or unexpected {agent} skills")
        for command in COMMANDS:
            relative = f"{folder}/skills/speckit-{command}/SKILL.md"
            if relative not in lock["outputs"]:
                raise ValueError(f"Untracked generated command: {relative}")
    for spec in (root / "specs").glob("*/spec.md"):
        assurance = local(root, str(spec.parent.relative_to(root) / "assurance.json"))
        if portable:
            validate_portable_record(root, assurance)
        else:
            validate_record(root, assurance)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", choices=("check", "snapshot", "freeze"), default="check")
    parser.add_argument("feature", nargs="?")
    args = parser.parse_args()
    try:
        if args.mode in {"snapshot", "freeze"}:
            if not args.feature:
                parser.error(f"{args.mode} requires specs/<feature>")
            if args.mode == "snapshot":
                snapshot(ROOT, args.feature)
                print("Current authority snapshot updated; human review reset to pending, not approved.")
            else:
                freeze(ROOT, args.feature)
                print("Authority snapshot frozen at HEAD; human review remains pending, not approved.")
        else:
            check()
            print("Spec Kit structural gates passed; semantic/human review remains separate.")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Spec Kit validation failed: {exc}", file=sys.stderr)
        sys.exit(1)
