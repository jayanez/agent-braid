# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T013 (REQ-014 / SC-014): build and check the fresh v3 test split of Amendment 1.

The v3 split measures the fixed analyze skill (A0'). It reuses the v2 class plan, fact generator and expectation
rule (``spec078_build_set``) with its own seed and its own templates, new wording not derived from v2 prompts or
rollout traces (the author had read three v2-test prompts in the Gate 1 review; the checks below are the guard). The checks refuse a case whose prompt or expectation does not follow from its facts, a fact pattern
already used by a v2 split, and any 8-word window shared with a v2 split, a SPEC-069 prompt or the analyze skill.

    python -m scripts.spec078_build_v3           # write specs/078-lightning-heldout-v2/prompts/v3-test.json
    python -m scripts.spec078_build_v3 --check   # exit 1 unless the committed file equals a fresh build
    python -m scripts.spec078_build_v3 --gate0 specs/078-lightning-heldout-v2/evidence/gate0-v3-report.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from scripts import spec078_build_set as v2set

ROOT = v2set.ROOT
OUT = v2set.OUT / "v3-test.json"
SEED = 3078
SIZE = 100
SET_ID = "spec078-held-out-v3-test"
GENERATOR = "scripts/spec078_build_v3.py"

STYLE = {
    "label": ["Edit X", "Edit Y", "Edit Z"],
    "parallel": "Use Agent Braid to tell me whether these changes are safe to make in parallel.",
    "relation": "Use Agent Braid to explain what ordering holds between these changes.",
    "overlap": "Use Agent Braid to tell me whether any of these changes collide.",
    "write": "{L} reworks a section of {p}.",
    "read": "{L} consults {p} but never modifies it.",
    "delete": "{L} deletes {p} outright.",
    "deploy": "{L} ships {p} to the live environment.",
    "partial": "{L} reworks a section of {p} and may also touch files nobody has listed yet.",
    "after": "{L} has to wait until {M} is finished.",
    "uses": "{L} reworks a section of {p} using the values that {M} puts into {q}.",
    "git": "Using Agent Braid, I want to know if merging {names} at once is safe; each is a branch cut from {base}.",
    "git_after": "Branch {b} must land after branch {a}.",
}


def _v2_sets() -> dict[str, list[dict]]:
    return {split: json.loads((v2set.OUT / f"{split}.json").read_text("utf-8"))["cases"] for split in v2set.SPLITS}


def build() -> dict:
    rng = random.Random(SEED)
    seen = {v2set._signature(c["facts"]) for cases in _v2_sets().values() for c in cases}
    cases = []
    for index, cls in enumerate(v2set._plan(SIZE), 1):
        for _ in range(500):
            facts = v2set.make_facts(cls, rng)
            if v2set._signature(facts) not in seen:
                break
        else:
            raise v2set.SetError(f"no fact pattern of class {cls!r} outside v2")
        seen.add(v2set._signature(facts))
        cases.append({"id": f"V3T-{index:03d}", "class": cls, "facts": facts, "prompt": v2set.prompt(facts, STYLE),
                      "expect": v2set.expectation(facts)})
    data = {"setId": SET_ID, "split": "test", "generator": {"script": GENERATOR, "seed": SEED,
                                                              "classPlan": "spec078_build_set._plan, ten classes"},
            "cases": cases}
    check(data)
    return data


def check(data: dict, *, v2: dict[str, list[dict]] | None = None, v1: list[str] | None = None,
          skill_text: str | None = None) -> None:
    v2 = _v2_sets() if v2 is None else v2
    v1 = v2set._v1_prompts() if v1 is None else v1
    skill_text = v2set.SKILL.read_text("utf-8") if skill_text is None else skill_text
    cases = data["cases"]
    if len(cases) != SIZE:
        raise v2set.SetError(f"v3-test has {len(cases)} cases instead of {SIZE}")
    missing = set(v2set.CLASSES) - {c["class"] for c in cases}
    if missing:
        raise v2set.SetError(f"v3-test misses classes {sorted(missing)}")
    old_signatures = {v2set._signature(c["facts"]) for split in v2.values() for c in split}
    ids, signatures, found = set(), set(), set()
    for case in cases:
        facts = case["facts"]
        if case["class"] not in v2set.CLASSES:
            raise v2set.SetError(f"{case['id']}: unknown class")
        if case["prompt"] != v2set.prompt(facts, STYLE):
            raise v2set.SetError(f"{case['id']}: prompt does not follow from the facts")
        if case["expect"] != v2set.expectation(facts):
            raise v2set.SetError(f"{case['id']}: expectation does not follow from the facts")
        signature = v2set._signature(facts)
        if case["id"] in ids or signature in signatures:
            raise v2set.SetError(f"{case['id']}: duplicate id or fact pattern")
        if signature in old_signatures:
            raise v2set.SetError(f"{case['id']}: fact pattern already used by a v2 split")
        ids.add(case["id"])
        signatures.add(signature)
        found |= v2set.windows(case["prompt"])
    for name, texts in (("a v2 split", [c["prompt"] for split in v2.values() for c in split]),
                        ("a SPEC-069 prompt", v1), ("the analyze skill", [skill_text])):
        shared = found & set().union(*(v2set.windows(t) for t in texts))
        if shared:
            raise v2set.SetError(f"v3-test shares an 8-word window with {name}: {sorted(shared)[0]!r}")


def render(data: dict) -> str:
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare the committed file with a fresh build")
    parser.add_argument("--gate0", type=Path, help="run Gate 0 on the committed v3 split and write its report here")
    args = parser.parse_args(argv)
    if args.gate0:
        from scripts import spec078_gate0
        report = spec078_gate0.run({"test": json.loads(OUT.read_text("utf-8"))["cases"]})
        args.gate0.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return 0 if report["passed"] else 1
    data = build()
    if args.check:
        if not OUT.is_file() or OUT.read_text("utf-8") != render(data):
            print("stale or missing v3-test.json", file=sys.stderr)
            return 1
        return 0
    OUT.write_text(render(data), encoding="utf-8")
    print(json.dumps({c: sum(x["class"] == c for x in data["cases"]) for c in v2set.CLASSES}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
