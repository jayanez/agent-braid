# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T004 (REQ-003, REQ-004, REQ-005 / SC-003 to SC-005): Gate 0, the evaluation of the evaluation.

No rollouts. Every check sends requests through the real ``analyze-work`` service over the SPEC-069 fixture
workspace and scores the result with the unchanged ``scripts/spec069_scoring.py``:

* **references** (REQ-003): a request built from each case's facts, with partial coverage where the facts
  say so, must be accepted and valid; the complete-coverage variant of every partial case must be invalid.
* **literal follower** (REQ-004): the request the analyze skill prescribes when followed literally. It copies
  the skill's own documented example of the kind and changes only what the case's facts define, applying the
  rules in ``RULES``; each rule is pinned to its sentence in the skill (``pin_problems``).
* **null baselines** (REQ-005): deterministic wrong answers, each scored once on the cases it applies to
  (``NULLS``); each must fail the cases ``NULLS`` names, and none may meet the OD-1 threshold, taken over the
  cases it was scored on, in any split. A host that follows the old HELD-04 read rule and is otherwise
  perfect (``oldReadRuleStrategy``) must not meet OD-1 either, which the per-class clause guarantees.

    python -m scripts.spec078_gate0 [--json <report path>]   # exit 0 only if every check passes
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import tempfile
import threading
from pathlib import Path

from agent_braid import lightning_heldout_v2
from agent_braid.tooling_mcp import ToolingConfig, ToolingService
from scripts import spec069_fixture_workspace, spec069_scoring
from scripts.spec078_build_set import OUT, SKILL, SPLITS

EXAMPLE = re.compile(r"```json kind=(\w+) result=\S+ constraints=\S+\n(.*?)```", re.S)
REPOSITORY_PLACEHOLDER = "<workspace root directory>"

# The skill sentences each follower rule relies on. A guidance edit that drops one fails the pin check, so
# the follower cannot silently drift from the guidance it stands for.
RULES = {
    "kind-aim": "whether work on named files can run in parallel, overlap or must be ordered | `aim`",
    "kind-git": "branches or worktrees of a Git repository | `git`",
    "copy-example": "Copy the matching example and change only what the\nuser's work defines.",
    "distinct-ids": "Give every unit a distinct `instanceId`, `attemptId`, `definition.digest` and\n  `inputDigest`",
    "declare-effects": "list every resource it touches under `effects.declared`",
    "resource-form": "the resource `repo://workspace/<path>`",
    "dependency": "A unit that must wait for another lists that unit's `instanceId` under\n  `dependencies`",
    "read-only-for-content": "Declare a `read`\n  of a file the other unit writes only when the user says this unit uses that\n  file's content",
    "coverage-complete": "`coverage.status` is `complete` when the user named the exact files each unit\n  touches",
    "coverage-partial": "Use `partial` or `unknown` only when the user says\n  other files may be touched",
    "git-repository": "`repository` is the registered workspace's root directory.",
    "git-attempts": "each `attemptId` must differ from the others",
}


def meets_od1(passes: list[tuple[str, bool]]) -> tuple[bool, float]:
    """OD-1 items 1-2 (share and per-class clause); the runner's analysis owns the definition."""
    return lightning_heldout_v2.meets_share_and_classes(passes)


class Gate0Error(ValueError):
    """The skill no longer documents what the follower needs."""


def pin_problems(skill_text: str) -> list[str]:
    return [f"rule {name!r}: sentence not found in the skill" for name, sentence in RULES.items()
            if sentence not in skill_text]


def examples(skill_text: str) -> dict[str, dict]:
    found = {kind: json.loads(body) for kind, body in EXAMPLE.findall(skill_text)}
    if not {"aim", "git"} <= set(found):
        raise Gate0Error("the skill must document one aim and one git example")
    return found


# ----------------------------------------------------------------------------
# Requests
# ----------------------------------------------------------------------------
def _digest(char: str) -> str:
    return "sha256:" + char * 64


GIT_WORDS = re.compile(r"\b(branch|branches|worktree|worktrees)\b", re.I)
UNITS_WORDS = re.compile(r"\bquick\b.*\bby path\b|\bwithout digests\b", re.I | re.S)


def kind_from_prompt(text: str) -> str:
    """The kind table read literally: branches or worktrees mean `git`, a quick check by path means `units`,
    work on named files means `aim`."""
    if GIT_WORDS.search(text):
        return "git"
    if UNITS_WORDS.search(text):
        return "units"
    return "aim"


def follower_request(case: dict, shown: dict, repository: str) -> tuple[str, dict]:
    """The request the skill prescribes when followed literally; ``shown`` is ``examples(skill_text)``."""
    facts = case["facts"]
    kind = kind_from_prompt(case["prompt"])  # rules kind-aim, kind-git
    if kind != facts["kind"]:
        raise Gate0Error(f"{case['id']}: the prompt reads as kind {kind!r}, the facts say {facts['kind']!r}")
    if kind == "git":
        request = copy.deepcopy(shown["git"])  # rule copy-example
        template = request["operations"][0]
        request["repository"] = repository  # rule git-repository
        request["baseRevision"] = facts["base"]
        request["operations"] = []
        for unit in facts["units"]:
            op = copy.deepcopy(template)
            op.update(instanceId=unit["branch"], attemptId=unit["branch"] + "-1",  # rule git-attempts
                      dependencies=[_branch(facts, a) for a in unit["after"]], uncertainPaths=[])
            op["source"] = {"kind": "commit", "revision": unit["branch"]}
            request["operations"].append(op)
        return "git", request
    request = copy.deepcopy(shown["aim"])  # rules kind-aim, copy-example
    template = request["operations"][0]
    request["source"]["description"] = "Synthetic placeholder digests; " + case["id"]
    request["operations"] = []
    for index, unit in enumerate(facts["units"], 1):
        op = copy.deepcopy(template)
        op.update(instanceId=unit["key"], attemptId=unit["key"] + "-1",  # rule distinct-ids
                  dependencies=list(unit["after"]))  # rule dependency
        op["definition"]["digest"] = _digest("0123456789"[index % 10])
        op["inputDigest"] = _digest("abcdef"[index % 6])
        declared = [{"kind": e["kind"], "resource": "repo://workspace/" + e["path"]}  # declare-effects, resource-form
                    for e in unit["effects"]]
        declared += [{"kind": "read", "resource": "repo://workspace/" + p} for p in unit["uses"]]  # read-only-for-content
        op["effects"]["declared"] = declared
        op["effects"]["coverage"]["status"] = "partial" if unit["partial"] else "complete"  # coverage rules
        request["operations"].append(op)
    return "aim", request


def _branch(facts: dict, key: str) -> str:
    return next(u["branch"] for u in facts["units"] if u["key"] == key)


def reference_request(case: dict, repository: str, *, honour_partial: bool = True) -> tuple[str, dict]:
    """The SPEC-069 reference request for the expectation, with the coverage the facts give."""
    return case["expect"]["kind"], lightning_heldout_v2.reference_request(
        case, spec069_scoring, repository, honour_partial=honour_partial)


# ----------------------------------------------------------------------------
# Null baselines (REQ-005): name -> (applies to kind, builder, classes it must fail)
# ----------------------------------------------------------------------------
def _null_empty(case, repository):
    kind, request = reference_request(case, repository)
    for op in request["operations"]:
        op["effects"]["declared"] = []
    return kind, request


def _null_partial(case, repository):
    kind, request = reference_request(case, repository)
    for op in request["operations"]:
        op["effects"]["coverage"]["status"] = "partial"
    return kind, request


def _null_overdeclare(case, repository):
    kind, request = reference_request(case, repository)
    writes = {u["key"]: [e["resource"] for e in u["effects"] if e["kind"] in spec069_scoring.WRITE_LIKE]
              for u in case["expect"]["units"]}
    for op, unit in zip(request["operations"], case["expect"]["units"]):
        have = {e["resource"] for e in op["effects"]["declared"]}
        for dep in unit["dependsOn"]:
            for path in writes[dep]:
                if "repo://workspace/" + path not in have:
                    op["effects"]["declared"].append({"kind": "read", "resource": "repo://workspace/" + path})
    return kind, request


def _null_wrong_base(case, repository):
    kind, request = reference_request(case, repository)
    request["baseRevision"] = "docs-guide"
    return kind, request


def _null_units(case, repository):
    """The `units` kind with the expected effects: the scorer accepts it for an `aim` case, and the analyzer
    always records partial coverage for it, so it must agree with `partial-coverage`."""
    units = [{"id": u["key"], "dependencies": list(u["dependsOn"]),
              "effects": [{"kind": e["kind"], "resource": e["resource"]} for e in u["effects"] if not e.get("optional")]}
             for u in case["expect"]["units"]]
    return "units", {"unitsRequestVersion": "0.1.0-alpha", "units": units}


def _has_independent_pair(case: dict) -> bool:
    return any(p["classification"] == "independent-candidate" for p in case["expect"]["pairs"])


def _any(case: dict) -> bool:
    return True


# name -> (classes it is scored on, builder, which scored cases it must fail). A null is scored only where it
# means something, and its OD-1 share is taken over those cases.
NULLS = {
    "no-call": (None, None, _any),  # every case; scored without a request
    "empty-declaration": ({"aim"}, _null_empty, _any),
    "partial-coverage": ({"aim"}, _null_partial, _has_independent_pair),
    "units-kind": ({"aim"}, _null_units, _has_independent_pair),
    "over-declaration": ({"chain-read", "chain-plain"}, _null_overdeclare, lambda c: c["class"] == "chain-plain"),
    "wrong-base": ({"git"}, _null_wrong_base, _any),
}


def _scored_on(case: dict, scope: set[str] | None) -> bool:
    return scope is None or case["expect"]["kind"] in scope or case["class"] in scope


# ----------------------------------------------------------------------------
class Analyzer:
    """``analyze-work`` over a fresh fixture workspace; a new service per call keeps the evidence inventory small."""

    def __init__(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        base = Path(self._temp.name)
        self.repository = spec069_fixture_workspace.build(base / "source")
        self._base = base

    def close(self) -> None:
        self._temp.cleanup()

    def attempt(self, kind: str, request: dict) -> dict:
        results = Path(tempfile.mkdtemp(dir=self._base))
        service = ToolingService(ToolingConfig(self.repository, results))
        request = json.loads(json.dumps(request).replace(REPOSITORY_PLACEHOLDER, str(self.repository)))
        envelope = service.invoke("analyze-work", {"kind": kind, "request": request}, threading.Event())
        return {"kind": kind, "request": request, "accepted": envelope["status"] == "ok",
                "refusalSummary": envelope.get("summary"), "report": (envelope.get("result") or {}).get("report")}

    def valid(self, case: dict, kind: str, request: dict) -> tuple[bool, list[str]]:
        score = spec069_scoring.score_case(case, [self.attempt(kind, request)])
        return score["validFirstAttempt"], score["reasons"]


def load_sets() -> dict[str, list[dict]]:
    return {split: json.loads((OUT / f"{split}.json").read_text("utf-8"))["cases"] for split in SPLITS}


def run(sets: dict[str, list[dict]] | None = None, skill_text: str | None = None) -> dict:
    sets = load_sets() if sets is None else sets
    skill_text = SKILL.read_text("utf-8") if skill_text is None else skill_text
    report = {"pins": pin_problems(skill_text), "references": [], "partialControls": [], "follower": [],
              "nulls": {}, "oldReadRuleStrategy": {}, "passed": False}
    shown = examples(skill_text) if not report["pins"] else {}
    analyzer = Analyzer()
    repo = str(analyzer.repository)
    try:
        for split, cases in sets.items():
            for case in cases:
                ok, why = analyzer.valid(case, *reference_request(case, repo))
                if not ok:
                    report["references"].append({"id": case["id"], "reasons": why})
                if any(u.get("partial") for u in case["facts"]["units"]):
                    ok, _ = analyzer.valid(case, *reference_request(case, repo, honour_partial=False))
                    if ok:
                        report["partialControls"].append({"id": case["id"], "reasons": ["complete variant valid"]})
                if not report["pins"]:
                    try:
                        ok, why = analyzer.valid(case, *follower_request(case, shown, repo))
                    except Gate0Error as error:
                        ok, why = False, [str(error)]
                    if not ok:
                        report["follower"].append({"id": case["id"], "reasons": why})
        for name, (scope, build, must_fail) in NULLS.items():
            per_split, unexpected = {}, []
            for split, cases in sets.items():
                scored = [c for c in cases if _scored_on(c, scope)]
                passes = []
                for case in scored:
                    ok = False if build is None else analyzer.valid(case, *build(case, repo))[0]
                    passes.append((case["class"], ok))
                    if ok and must_fail(case):
                        unexpected.append(case["id"])
                meets, low = meets_od1(passes)
                per_split[split] = {"passing": sum(ok for _, ok in passes), "of": len(scored),
                                    "wilsonLower": round(low, 4), "meetsThreshold": meets}
            report["nulls"][name] = {"splits": per_split, "unexpectedPasses": unexpected}
        # A host that follows the old HELD-04 read rule and is otherwise perfect must not meet OD-1.
        for split, cases in sets.items():
            passes = [(c["class"], analyzer.valid(c, *(_null_overdeclare(c, repo) if c["expect"]["kind"] == "aim"
                                                        else reference_request(c, repo)))[0]) for c in cases]
            meets, low = meets_od1(passes)
            report["oldReadRuleStrategy"][split] = {"passing": sum(ok for _, ok in passes), "of": len(cases),
                                                    "wilsonLower": round(low, 4), "meetsThreshold": meets}
    finally:
        analyzer.close()
    report["passed"] = (not report["pins"] and not report["references"] and not report["partialControls"]
                        and not report["follower"]
                        and all(not n["unexpectedPasses"] and not any(s["meetsThreshold"] for s in n["splits"].values())
                                for n in report["nulls"].values())
                        and not any(s["meetsThreshold"] for s in report["oldReadRuleStrategy"].values()))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", type=Path, help="also write the report to this path")
    args = parser.parse_args(argv)
    report = run()
    text = json.dumps(report, indent=1, sort_keys=True) + "\n"
    if args.json:
        args.json.write_text(text, encoding="utf-8")
    summary = {"passed": report["passed"], "pinProblems": len(report["pins"]),
               "referenceFailures": len(report["references"]), "partialControlFailures": len(report["partialControls"]),
               "followerFailures": len(report["follower"]),
               "nulls": {k: {s: f"{v['passing']}/{v['of']}" for s, v in n["splits"].items()}
                         | {"unexpectedPasses": len(n["unexpectedPasses"])} for k, n in report["nulls"].items()}}
    print(json.dumps(summary, indent=1))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
