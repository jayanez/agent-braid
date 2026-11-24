# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-079 T004/T005 (REQ-006, REQ-007 / SC-009, SC-010): build, check and Gate 0 the fresh held-out v4 split.

v4 measures the tool-level kind-choice fix. Facts and expectations reuse the SPEC-078 fact generator and
footprint rule (``spec078_build_set``); the class plan, seed and prompt templates are new. The templates were
written from the class plan without opening any v2-test or v3-test prompt text; the checks below are the
guard. A build refuses a case whose prompt or expectation does not follow from its facts, a fact pattern
(ignoring the question label) already used by a SPEC-078 split, and any 8-word normalized window shared with a
SPEC-069 prompt, a SPEC-078 split, the analyze skill or the SPEC-079 tool descriptions and redirect message.

    python -m scripts.spec079_build_v4           # write specs/079-kind-choice-tool-fix/prompts/v4-test.json
    python -m scripts.spec079_build_v4 --check   # exit 1 unless the committed file equals a fresh build
    python -m scripts.spec079_build_v4 --gate0 specs/079-kind-choice-tool-fix/evidence/gate0-v4-report.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from agent_braid import tooling_mcp
from scripts import spec078_build_set as v2set
from scripts.spec069_fixture_workspace import BASE_FILES

ROOT = v2set.ROOT
OUT = ROOT / "specs/079-kind-choice-tool-fix/prompts/v4-test.json"
V3 = v2set.OUT / "v3-test.json"
SEED = 4079
SET_ID = "spec079-held-out-v4-test"
GENERATOR = "scripts/spec079_build_v4.py"
# REQ-006 class plan (plan.md design 5): class -> (prompts, SPEC-078 fact class or the v4-only `read-shared`).
PLAN = {
    "disjoint-parallel": (20, "disjoint"),
    "overlap-write": (15, "shared-write"),
    "dependency-order": (15, "chain"),
    "read-only-shared": (10, "read-shared"),
    "kind-choice-probe": (20, "disjoint"),
    "analyze-tempting": (10, "disjoint"),
    "git-branch": (10, "git"),
}
SIZE = sum(n for n, _ in PLAN.values())
FILES = sorted(BASE_FILES)
LABEL = {"a": "A", "b": "B", "c": "C"}

# ----------------------------------------------------------------------------
# Templates (v4 only). Each class has several phrasings; ``style`` picks one and is stored in the case.
# ----------------------------------------------------------------------------
INTRO = {
    "disjoint-parallel": ["I have {n} pieces of work queued for this repository.",
                          "Our sprint board lists {n} small jobs in this project.",
                          "Before I hand these {n} jobs to separate agents, here is what each one does."],
    "overlap-write": ["Three teammates each picked up a ticket in this codebase today.",
                      "Here are three edits I am about to start in this project.",
                      "My plan for this afternoon has three separate jobs."],
    "dependency-order": ["We are preparing three related changes in this project.",
                         "Three jobs are planned for this repo and one of them has to wait.",
                         "I am lining up three edits; please read the ordering note carefully."],
    "read-only-shared": ["A few jobs here consult the same reference file but edit different targets.",
                         "I want to farm out {n} jobs that all look at one shared file.",
                         "These {n} jobs each open a common file for reference only."],
    "kind-choice-probe": ["Quick sanity question about {n} jobs I am planning.",
                          "Just checking something before I start {n} jobs.",
                          "Short one: I have {n} jobs lined up."],
    "analyze-tempting": ["Analyze this plan for me.", "Please analyze the following work plan.",
                         "Can you run an analysis on this plan?"],
}
ASK = {
    "disjoint-parallel": ["Can all of them run in parallel?", "Is it safe to run these concurrently?",
                          "Would running them side by side cause any interference?"],
    "overlap-write": ["Which of these could collide if we start them together?",
                      "Do any of them overlap, and which ones are fine to run together?",
                      "Tell me which pairs are safe to work on simultaneously."],
    "dependency-order": ["What can start together and what must wait?",
                         "Which pairs can proceed side by side, and which need an order?",
                         "Please tell me how these relate to each other."],
    "read-only-shared": ["Can they all proceed at once?", "Is there any reason not to run them concurrently?",
                         "Would they get in each other's way if started together?"],
    "kind-choice-probe": ["Can these happen at the same time?", "Are these fine to do simultaneously?",
                          "Is there any problem doing them all at once?"],
    "analyze-tempting": ["I mainly want to know whether these can be done in parallel.",
                         "The question is whether any of them clash or can all go at once.",
                         "Specifically: can the work be split across parallel workers?"],
}
COMPLETE = ["Those are the only files involved.", "Nothing else gets touched.",
            "No other files are affected by any job."]
WRITE = ["Job {k} edits `{p}`.", "Job {k} touches only `{p}`.", "Job {k} only changes `{p}`."]
READ = [" It looks at `{p}` for reference but does not change it.", " It also opens `{p}` read-only.",
        " It consults `{p}` without modifying it."]
USES = [" It relies on the new content Job {a} writes into `{p}`.", " It copies text from `{p}` once Job {a} is done.",
        " It needs to read the updated `{p}`."]
AFTER = [" It must not start until Job {a} has finished.", " It has to wait for Job {a}.",
         " Job {a} must be completed first."]
GIT = {
    "intro": ["Several feature lines were cut from `{base}` in this repository: {names}.",
              "We have work in progress on {names}, all started from `{base}`.",
              "Look at {names}; each one was created from `{base}`."],
    "after": [" `{b}` is meant to land after `{a}`.", " `{b}` should only merge once `{a}` is in."],
    "ask": ["Can these branches be merged in parallel, or do some conflict?",
            "Do any of these branches touch the same files?",
            "Which of these branches can land independently?"],
}


def _choice(options: list[str], style: int, salt: int) -> str:
    return options[(style + salt) % len(options)]


def prompt(cls: str, facts: dict, style: int) -> str:
    """The v4 prompt for ``facts``: every path, wait and content use in it comes from the facts."""
    if facts["kind"] == "git":
        names = ", ".join(f"`{u['branch']}`" for u in facts["units"])
        text = _choice(GIT["intro"], style, 0).format(base=facts["base"], names=names)
        branch = {u["key"]: u["branch"] for u in facts["units"]}
        for unit in facts["units"]:
            for after in unit["after"]:
                text += _choice(GIT["after"], style, 1).format(a=branch[after], b=unit["branch"])
        return text + " " + _choice(GIT["ask"], style, 2)
    n = len(facts["units"])
    parts = [_choice(INTRO[cls], style, 0).format(n=n)]
    for unit in facts["units"]:
        writes = [e["path"] for e in unit["effects"] if e["kind"] == "write"]
        reads = [e["path"] for e in unit["effects"] if e["kind"] == "read"]
        sentence = _choice(WRITE, style, 1).format(k=LABEL[unit["key"]], p=writes[0])
        for path in reads:
            sentence += _choice(READ, style, 2).format(p=path)
        for after in unit["after"]:
            sentence += _choice(AFTER, style, 3).format(a=LABEL[after])
        for path in unit["uses"]:
            writer = next(u["key"] for u in facts["units"] if any(e["path"] == path for e in u["effects"]))
            sentence += _choice(USES, style, 4).format(a=LABEL[writer], p=path)
        parts.append(sentence)
    parts.append(_choice(COMPLETE, style, 5))
    parts.append(_choice(ASK[cls], style, 6))
    return " ".join(parts)


# ----------------------------------------------------------------------------
# Facts
# ----------------------------------------------------------------------------
def make_facts(cls: str, rng: random.Random) -> dict:
    source = PLAN[cls][1]
    if source == "read-shared":
        n = rng.choice((2, 3))
        shared, *targets = v2set._pick(rng, FILES, n + 1)
        units = [v2set._unit(v2set.KEYS[i], [("read", shared), ("write", p)]) for i, p in enumerate(targets)]
        return {"kind": "aim", "question": "parallel", "units": units}
    if source == "chain":
        return v2set.make_facts(rng.choice(("chain-read", "chain-plain")), rng)
    return v2set.make_facts(source, rng)


def _pattern(facts: dict) -> str:
    """The fact pattern up to unit keys, order and question label."""
    return v2set._signature({**facts, "question": "-"} if facts["kind"] == "aim" else facts)


def _plan() -> list[str]:
    return [cls for cls, (n, _) in PLAN.items() for _ in range(n)]


def _earlier_sets() -> list[dict]:
    paths = [v2set.OUT / f"{split}.json" for split in v2set.SPLITS] + [V3]
    return [case for path in paths for case in json.loads(path.read_text("utf-8"))["cases"]]


def protected_texts() -> dict[str, list[str]]:
    """Every text a v4 prompt may not share an 8-word window with."""
    return {"a SPEC-069 prompt": v2set._v1_prompts(),
            "a SPEC-078 split": [c["prompt"] for c in _earlier_sets()],
            "the analyze skill": [v2set.SKILL.read_text("utf-8")],
            "a SPEC-079 tool text": [tooling_mcp._ANALYZE_WORK_SCHEMA_HELP, tooling_mcp._ANALYZE_WORK_REQUEST_HELP,
                                     tooling_mcp._ANALYZE_HELP, tooling_mcp._UNITS_REDIRECT]}


def build() -> dict:
    rng = random.Random(SEED)
    seen = {_pattern(c["facts"]) for c in _earlier_sets()}
    cases = []
    for index, cls in enumerate(_plan(), 1):
        for _ in range(500):
            facts = make_facts(cls, rng)
            if _pattern(facts) not in seen:
                break
        else:
            raise v2set.SetError(f"feasibility failure: no fresh fact pattern for class {cls!r}")
        seen.add(_pattern(facts))
        style = rng.randrange(6)
        cases.append({"id": f"V4T-{index:03d}", "class": cls, "style": style, "facts": facts,
                      "prompt": prompt(cls, facts, style), "expect": v2set.expectation(facts)})
    data = {"setId": SET_ID, "split": "test",
            "generator": {"script": GENERATOR, "seed": SEED, "classPlan": {c: n for c, (n, _) in PLAN.items()}},
            "cases": cases}
    check(data)
    return data


def _check_facts(case: dict) -> None:
    facts = case["facts"]
    if facts["kind"] != ("git" if PLAN[case["class"]][1] == "git" else "aim"):
        raise v2set.SetError(f"{case['id']}: kind does not match the class")
    if facts["kind"] == "git":
        return
    for unit in facts["units"]:
        kinds = [e["kind"] for e in unit["effects"]]
        if kinds.count("write") != 1 or set(kinds) - {"write", "read"} or unit["partial"]:
            raise v2set.SetError(f"{case['id']}: unit {unit['key']} needs one write, optional reads, complete coverage")
        if any(e["path"] not in BASE_FILES for e in unit["effects"]) or any(p not in BASE_FILES for p in unit["uses"]):
            raise v2set.SetError(f"{case['id']}: unit {unit['key']} names a file outside the fixture")


def check(data: dict, *, earlier: list[dict] | None = None, protected: dict[str, list[str]] | None = None) -> None:
    earlier = _earlier_sets() if earlier is None else earlier
    protected = protected_texts() if protected is None else protected
    cases = data["cases"]
    if len(cases) != SIZE:
        raise v2set.SetError(f"v4-test has {len(cases)} cases instead of {SIZE}")
    counts = {cls: sum(c["class"] == cls for c in cases) for cls in PLAN}
    if counts != {cls: n for cls, (n, _) in PLAN.items()}:
        raise v2set.SetError(f"v4-test class counts {counts} differ from the class plan")
    old = {_pattern(c["facts"]) for c in earlier}
    ids, patterns, normalized, found = set(), set(), set(), set()
    for case in cases:
        if case["class"] not in PLAN:
            raise v2set.SetError(f"{case['id']}: unknown class")
        _check_facts(case)
        if case["prompt"] != prompt(case["class"], case["facts"], case["style"]):
            raise v2set.SetError(f"{case['id']}: prompt does not follow from the facts")
        if case["expect"] != v2set.expectation(case["facts"]):
            raise v2set.SetError(f"{case['id']}: expectation does not follow from the facts")
        pattern, text = _pattern(case["facts"]), " ".join(v2set.normalize_words(case["prompt"]))
        for value, pool, what in ((case["id"], ids, "id"), (pattern, patterns, "fact pattern"),
                                  (text, normalized, "normalized prompt")):
            if value in pool:
                raise v2set.SetError(f"{case['id']}: duplicate {what}")
            pool.add(value)
        if pattern in old:
            raise v2set.SetError(f"{case['id']}: fact pattern already used by a SPEC-078 split")
        found |= v2set.windows(case["prompt"])
    for name, texts in protected.items():
        shared = found & set().union(*(v2set.windows(t) for t in texts))
        if shared:
            raise v2set.SetError(f"v4-test shares an 8-word window with {name}: {sorted(shared)[0]!r}")


def _plain_chain(case: dict) -> bool:
    return case["facts"]["kind"] == "aim" and not any(u["uses"] for u in case["facts"]["units"])


def gate0(cases: list[dict]) -> dict:
    """SPEC-078 Gate 0 on v4. Its over-declaration null is scoped by the SPEC-078 class names, so on v4 it is
    scored on `dependency-order` and must fail the chains without a content use (the SPEC-078 `chain-plain`)."""
    from unittest import mock
    from scripts import spec078_gate0
    nulls = dict(spec078_gate0.NULLS)
    nulls["over-declaration"] = ({"dependency-order"}, spec078_gate0._null_overdeclare, _plain_chain)
    with mock.patch.object(spec078_gate0, "NULLS", nulls):
        return spec078_gate0.run({"test": cases})


def render(data: dict) -> str:
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare the committed file with a fresh build")
    parser.add_argument("--gate0", type=Path, help="run Gate 0 on the committed v4 split and write its report here")
    args = parser.parse_args(argv)
    if args.gate0:
        report = gate0(json.loads(OUT.read_text("utf-8"))["cases"])
        args.gate0.parent.mkdir(parents=True, exist_ok=True)
        args.gate0.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return 0 if report["passed"] else 1
    data = build()
    if args.check:
        if not OUT.is_file() or OUT.read_text("utf-8") != render(data):
            print("stale or missing v4-test.json", file=sys.stderr)
            return 1
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(data), encoding="utf-8")
    print(json.dumps(data["generator"]["classPlan"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
