# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T002 (REQ-002 / SC-002): build the held-out set v2 from a class plan and per-split templates.

Every case is written from structured ``facts`` (units, effects, content use, ordering, coverage), and its
``prompt`` and ``expect`` are both derived from those facts. ``expect`` follows the SPEC-069 case format and is
scored by the unchanged ``scripts/spec069_scoring.py``. Pair classifications are written here from the exact
footprint rules (dependency, then shared write, then partial coverage, then delete or deploy, else
independent); Gate 0 (T004) checks them against the real analyzer.

    python -m scripts.spec078_build_set           # write the three split files
    python -m scripts.spec078_build_set --check   # exit 1 unless the committed files equal a fresh build

The build checks refuse a set whose splits miss a class, reuse a prompt or a fact pattern, name a path or
branch the prompt does not contain, have a unit without a required effect on a fixture file, use an effect
outside the fixed vocabulary, mention content use without a ``uses`` fact (or the reverse), share an 8-word
normalized window across splits, with the analyze skill or with either SPEC-069 set.
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
from pathlib import Path

from agent_braid.lightning_runner import WINDOW, normalize_words
from scripts.spec069_fixture_workspace import BASE_FILES, BASE_BRANCH, BRANCHES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "specs/078-lightning-heldout-v2/prompts"
SKILL = ROOT / "integrations/agent-braid/skills/agent-braid-analyze/SKILL.md"
V1_SETS = [ROOT / "specs/069-aim-request-authoring/prompts/development.json",
           ROOT / "specs/069-aim-request-authoring/prompts/held-out.json"]
SEED = 78
SPLITS = {"feedback": 24, "validation": 40, "test": 100}
ID_PREFIX = {"feedback": "V2F", "validation": "V2V", "test": "V2T"}
CLASSES = ("disjoint", "shared-write", "read-write", "delete", "chain-read", "chain-plain",
           "mixed-overlap", "git", "partial", "deploy")
EFFECT_KINDS = {"write", "read", "delete", "deploy"}
WRITE_LIKE = {"write", "delete", "deploy"}
EXTERNAL = {"delete", "deploy"}
CONSTRAINTS = {"ordered": "preserve-dependency-order", "conflicting": "serialize-or-isolate",
               "unknown": "serialize-unless-stronger-evidence",
               "independent-candidate": "requires-execution-contract-before-parallelism"}
FILES = sorted(BASE_FILES)
DEPLOYABLE = ["config/production.yaml", "config/staging.yaml"]
SOURCES = [f for f in FILES if f.startswith(("src/", "scripts/", "tests/"))]
KEYS = ("a", "b", "c")


class SetError(ValueError):
    """The set breaks a REQ-002 build rule."""


# ----------------------------------------------------------------------------
# Per-split templates. No 8-word window may be shared between splits (checked below).
# ----------------------------------------------------------------------------
STYLES = {
    "feedback": {
        "label": ["Task one", "Task two", "Task three"],
        "parallel": "With Agent Braid, find out if the following tasks may run at the same time.",
        "relation": "With Agent Braid, work out how the following tasks relate to each other.",
        "overlap": "Could these tasks overlap? Check with Agent Braid.",
        "write": "{L} edits {p}.",
        "read": "{L} only looks at {p} and leaves it unchanged.",
        "delete": "{L} removes the file {p} from the repository.",
        "deploy": "{L} deploys {p}.",
        "partial": "{L} edits {p} and may change other files as well.",
        "after": "{L} cannot begin until {M} is done.",
        "uses": "{L} edits {p} so that it uses what {M} puts into {q}.",
        "git": "With Agent Braid, find out if the fixture repository may have its branches {names} "
               "developed at the same time. Every branch starts from {base}.",
        "git_after": "Branch {b} cannot begin until branch {a} is done.",
    },
    "validation": {
        "label": ["Change A", "Change B", "Change C"],
        "parallel": "Ask Agent Braid whether the changes listed here can be carried out in parallel.",
        "relation": "Ask Agent Braid to describe the ordering and conflicts among these changes.",
        "overlap": "Ask Agent Braid if the changes below can be worked on side by side.",
        "write": "{L} rewrites part of {p}.",
        "read": "{L} reads {p} for reference without modifying it.",
        "delete": "{L} deletes {p}.",
        "deploy": "{L} ships {p} as a deployment.",
        "partial": "{L} rewrites part of {p}, possibly together with files nobody has named yet.",
        "after": "{L} has to wait for {M} to finish first.",
        "uses": "{L} rewrites part of {p} and relies on the contents {M} writes to {q}.",
        "git": "Ask Agent Braid whether work on the branches {names} can be carried out in parallel. "
               "They were all created from {base}.",
        "git_after": "Work on {b} has to wait for {a} to finish first.",
    },
    "test": {
        "label": ["Job 1", "Job 2", "Job 3"],
        "parallel": "Run an Agent Braid check: can the jobs below happen simultaneously?",
        "relation": "Run an Agent Braid check that explains how the jobs below depend on or clash with one another.",
        "overlap": "Have Agent Braid tell me whether the jobs listed here can overlap in time.",
        "write": "{L} makes an update to {p}.",
        "read": "{L} just inspects {p}; nothing in it gets altered.",
        "delete": "{L} erases {p} entirely.",
        "deploy": "{L} rolls out a deploy of {p}.",
        "partial": "{L} makes an update to {p}, and other unnamed files might get touched too.",
        "after": "{L} must not start before {M} has completed.",
        "uses": "{L} makes an update to {p} which takes in the values {M} adds to {q}.",
        "git": "Run an Agent Braid check: can the repository branches {names} be worked on "
               "simultaneously? All of them branch off {base}.",
        "git_after": "{b} must not start before {a} has completed.",
    },
}
USE_MARKERS = ("uses what", "relies on the contents", "takes in the values")


# ----------------------------------------------------------------------------
# Facts → expectation
# ----------------------------------------------------------------------------
def _ancestors(units: list[dict]) -> dict[str, set[str]]:
    direct = {u["key"]: set(u["after"]) for u in units}
    result = {k: set(v) for k, v in direct.items()}
    changed = True
    while changed:
        changed = False
        for key in result:
            grown = result[key] | {a for item in result[key] for a in result[item]}
            if grown != result[key]:
                result[key], changed = grown, True
    return result


def footprint(unit: dict) -> dict[str, set[str]]:
    """Path -> effect kinds of an aim unit (its own effects plus the reads its content use implies)."""
    out: dict[str, set[str]] = {}
    for effect in unit["effects"]:
        out.setdefault(effect["path"], set()).add(effect["kind"])
    for path in unit["uses"]:
        out.setdefault(path, set()).add("read")
    return out


def git_footprint(branch: str) -> dict[str, set[str]]:
    kind = "delete" if branch == "remove-legacy" else "write"
    return {path: {kind} for path in BRANCHES[branch]}


def classify(left: dict, right: dict, prints: dict, ancestors: dict, partial: set[str]) -> str:
    if left["key"] in ancestors[right["key"]] or right["key"] in ancestors[left["key"]]:
        return "ordered"
    lp, rp = prints[left["key"]], prints[right["key"]]
    if any((lp[p] | rp[p]) & WRITE_LIKE for p in set(lp) & set(rp)):
        return "conflicting"
    if partial & {left["key"], right["key"]}:
        return "unknown"
    if any(kinds & EXTERNAL for kinds in (*lp.values(), *rp.values())):
        return "unknown"
    return "independent-candidate"


def expectation(facts: dict) -> dict:
    units = facts["units"]
    ancestors = _ancestors(units)
    if facts["kind"] == "git":
        prints = {u["key"]: git_footprint(u["branch"]) for u in units}
        partial: set[str] = set()
        expect = {"kind": "git", "baseRevision": facts["base"],
                  "units": [{"key": u["key"], "revision": u["branch"], "dependsOn": list(u["after"])}
                            for u in units]}
    else:
        prints = {u["key"]: footprint(u) for u in units}
        partial = {u["key"] for u in units if u["partial"]}
        expect = {"kind": "aim", "units": [
            {"key": u["key"],
             "effects": [{"kind": e["kind"], "resource": e["path"]} for e in u["effects"]]
                        + [{"kind": "read", "resource": p} for p in u["uses"]],
             "dependsOn": list(u["after"])} for u in units]}
    pairs = []
    for left, right in itertools.combinations(units, 2):
        label = classify(left, right, prints, ancestors, partial)
        pairs.append({"left": left["key"], "right": right["key"], "classification": label,
                      "constraints": [CONSTRAINTS[label]]})
    expect["pairs"] = pairs
    return expect


# ----------------------------------------------------------------------------
# Facts → prompt
# ----------------------------------------------------------------------------
def _unit(key: str, effects: list[tuple[str, str]], *, uses: tuple = (), after: tuple = (),
          partial: bool = False) -> dict:
    return {"key": key, "effects": [{"kind": k, "path": p} for k, p in effects], "uses": list(uses),
            "after": list(after), "partial": partial}


def prompt(facts: dict, style: dict) -> str:
    label = dict(zip(KEYS, style["label"]))
    if facts["kind"] == "git":
        names = [u["branch"] for u in facts["units"]]
        listed = ", ".join(names[:-1]) + " and " + names[-1]
        parts = [style["git"].format(names=listed, base=facts["base"])]
        by_key = {u["key"]: u["branch"] for u in facts["units"]}
        parts += [style["git_after"].format(a=by_key[a], b=u["branch"]) for u in facts["units"] for a in u["after"]]
        return " ".join(parts)
    parts = [style[facts["question"]]]
    by_writer = {e["path"]: u["key"] for u in facts["units"] for e in u["effects"]}
    for unit in facts["units"]:
        name = label[unit["key"]]
        effects = unit["effects"]
        first = effects[0]
        if unit["uses"]:
            source = unit["uses"][0]
            parts.append(style["uses"].format(L=name, p=first["path"], M=label[by_writer[source]], q=source))
        elif unit["partial"]:
            parts.append(style["partial"].format(L=name, p=first["path"]))
        else:
            parts.append(style[first["kind"]].format(L=name, p=first["path"]))
        for after in unit["after"]:
            parts.append(style["after"].format(L=name, M=label[after]))
    return " ".join(parts)


# ----------------------------------------------------------------------------
# Class plan
# ----------------------------------------------------------------------------
def _pick(rng: random.Random, pool: list[str], n: int, avoid: set[str] = frozenset()) -> list[str]:
    return rng.sample([p for p in pool if p not in avoid], n)


def make_facts(cls: str, rng: random.Random) -> dict:
    """One fact pattern of class ``cls``. Every class except ``partial`` and ``git`` keeps at least one
    independent pair, so the partial-coverage null baseline fails it (REQ-005)."""
    if cls == "git":
        names = sorted(BRANCHES)
        n = rng.choice((2, 3))
        branches = rng.sample(names, n)
        units = [{"key": KEYS[i], "branch": b, "after": []} for i, b in enumerate(branches)]
        if n == 3 and rng.random() < 0.5:
            units[1]["after"] = ["a"]
        return {"kind": "git", "base": BASE_BRANCH, "units": units}
    if cls == "disjoint":
        n = rng.choice((2, 3))
        paths = _pick(rng, FILES, n)
        units = [_unit(KEYS[i], [("write", p)]) for i, p in enumerate(paths)]
        return {"kind": "aim", "question": "parallel", "units": units}
    if cls == "shared-write":
        shared, other = _pick(rng, FILES, 2)
        units = [_unit("a", [("write", shared)]), _unit("b", [("write", shared)]), _unit("c", [("write", other)])]
        return {"kind": "aim", "question": "parallel", "units": units}
    if cls == "read-write":
        shared, other = _pick(rng, FILES, 2)
        units = [_unit("a", [("write", shared)]), _unit("b", [("read", shared)]), _unit("c", [("write", other)])]
        return {"kind": "aim", "question": "parallel", "units": units}
    if cls == "delete":
        gone, x, y = _pick(rng, FILES, 3)
        units = [_unit("a", [("delete", gone)]), _unit("b", [("write", x)]), _unit("c", [("write", y)])]
        return {"kind": "aim", "question": "parallel", "units": units}
    if cls == "mixed-overlap":
        gone, other = _pick(rng, FILES, 2)
        units = [_unit("a", [("delete", gone)]), _unit("b", [("write", other)]), _unit("c", [("write", gone)])]
        return {"kind": "aim", "question": "overlap", "units": units}
    if cls in ("chain-read", "chain-plain"):
        first = rng.choice(DEPLOYABLE + ["src/utils.py", "docs/api.md"])
        second, other = _pick(rng, SOURCES, 2, {first})
        uses = (first,) if cls == "chain-read" else ()
        units = [_unit("a", [("write", first)]), _unit("b", [("write", second)], uses=uses, after=("a",)),
                 _unit("c", [("write", other)])]
        return {"kind": "aim", "question": "relation", "units": units}
    if cls == "partial":
        x, y = _pick(rng, FILES, 2)
        units = [_unit("a", [("write", x)], partial=True), _unit("b", [("write", y)])]
        return {"kind": "aim", "question": "parallel", "units": units}
    if cls == "deploy":
        target = rng.choice(DEPLOYABLE)
        x, y = _pick(rng, FILES, 2, set(DEPLOYABLE))
        units = [_unit("a", [("deploy", target)]), _unit("b", [("write", x)]), _unit("c", [("write", y)])]
        return {"kind": "aim", "question": "parallel", "units": units}
    raise SetError(f"unknown class {cls!r}")


def _plan(size: int) -> list[str]:
    base, extra = divmod(size, len(CLASSES))
    return [c for i, c in enumerate(CLASSES) for _ in range(base + (1 if i < extra else 0))]


def _signature(facts: dict) -> str:
    return json.dumps(facts, sort_keys=True)


def build() -> dict[str, dict]:
    rng = random.Random(SEED)
    seen: set[str] = set()
    out = {}
    for split, size in SPLITS.items():
        cases = []
        for index, cls in enumerate(_plan(size), 1):
            for _ in range(200):
                facts = make_facts(cls, rng)
                if _signature(facts) not in seen:
                    break
            else:
                raise SetError(f"no fresh fact pattern for class {cls!r}")
            seen.add(_signature(facts))
            cases.append({"id": f"{ID_PREFIX[split]}-{index:03d}", "class": cls, "facts": facts,
                          "prompt": prompt(facts, STYLES[split]), "expect": expectation(facts)})
        out[split] = {"setId": f"spec078-held-out-v2-{split}", "split": split, "cases": cases}
    check(out)
    return out


# ----------------------------------------------------------------------------
# Build checks (REQ-002)
# ----------------------------------------------------------------------------
def windows(text: str) -> set[str]:
    words = normalize_words(text)
    return {" ".join(words[i:i + WINDOW]) for i in range(len(words) - WINDOW + 1)}


def _v1_prompts() -> list[str]:
    return [c["prompt"] for path in V1_SETS for c in json.loads(path.read_text("utf-8"))["cases"]]


def check(sets: dict[str, dict], *, skill_text: str | None = None, v1: list[str] | None = None) -> None:
    skill_text = SKILL.read_text("utf-8") if skill_text is None else skill_text
    v1 = _v1_prompts() if v1 is None else v1
    if set(sets) != set(SPLITS):
        raise SetError("the set must have exactly the splits " + ", ".join(SPLITS))
    ids, prompts, signatures = set(), set(), set()
    split_windows = {}
    for split, data in sets.items():
        cases = data["cases"]
        if len(cases) != SPLITS[split]:
            raise SetError(f"{split} has {len(cases)} cases instead of {SPLITS[split]}")
        missing = set(CLASSES) - {c["class"] for c in cases}
        if missing:
            raise SetError(f"{split} misses classes {sorted(missing)}")
        split_windows[split] = set()
        for case in cases:
            _check_case(case)
            for value, pool, what in ((case["id"], ids, "id"), (case["prompt"], prompts, "prompt"),
                                      (_signature(case["facts"]), signatures, "fact pattern")):
                if value in pool:
                    raise SetError(f"{case['id']}: duplicate {what}")
                pool.add(value)
            split_windows[split] |= windows(case["prompt"])
    for a, b in itertools.combinations(SPLITS, 2):
        if split_windows[a] & split_windows[b]:
            raise SetError(f"{a} and {b} share an 8-word window: {sorted(split_windows[a] & split_windows[b])[0]!r}")
    protected = split_windows["validation"] | split_windows["test"]
    if protected & windows(skill_text):
        raise SetError("a validation or test prompt shares an 8-word window with the analyze skill")
    old = set().union(*(windows(p) for p in v1))
    normalized_old = {" ".join(normalize_words(p)) for p in v1}
    for split, found in split_windows.items():
        if found & old:
            raise SetError(f"{split} shares an 8-word window with a SPEC-069 prompt")
    for data in sets.values():
        for case in data["cases"]:
            if " ".join(normalize_words(case["prompt"])) in normalized_old:
                raise SetError(f"{case['id']}: copies a SPEC-069 prompt")


def _check_case(case: dict) -> None:
    facts, text = case["facts"], case["prompt"]
    if case["class"] not in CLASSES:
        raise SetError(f"{case['id']}: unknown class")
    if case["expect"] != expectation(facts):
        raise SetError(f"{case['id']}: expectation does not follow from the facts")
    if facts["kind"] == "git":
        for unit in facts["units"]:
            if unit["branch"] not in BRANCHES or unit["branch"] not in text:
                raise SetError(f"{case['id']}: branch {unit['branch']!r} is unknown or not in the prompt")
        if facts["base"] not in text:
            raise SetError(f"{case['id']}: base revision not in the prompt")
        return
    uses_any = any(u["uses"] for u in facts["units"])
    if uses_any != any(m in text for m in USE_MARKERS):
        raise SetError(f"{case['id']}: content-use wording does not match the facts")
    for unit in facts["units"]:
        kinds = {e["kind"] for e in unit["effects"]}
        if kinds - EFFECT_KINDS:
            raise SetError(f"{case['id']}: effect outside the vocabulary")
        if not any(e["path"] in BASE_FILES for e in unit["effects"]):
            raise SetError(f"{case['id']}: unit {unit['key']} has no effect on a fixture file")
        for path in [e["path"] for e in unit["effects"]] + unit["uses"]:
            if path not in BASE_FILES or path not in text:
                raise SetError(f"{case['id']}: path {path!r} is not a fixture file named in the prompt")


# ----------------------------------------------------------------------------
def render(data: dict) -> str:
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare the committed files with a fresh build")
    args = parser.parse_args(argv)
    sets = build()
    if args.check:
        stale = [s for s, d in sets.items() if not (OUT / f"{s}.json").is_file()
                 or (OUT / f"{s}.json").read_text("utf-8") != render(d)]
        if stale:
            print("stale or missing split files: " + ", ".join(stale), file=sys.stderr)
            return 1
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for split, data in sets.items():
        (OUT / f"{split}.json").write_text(render(data), encoding="utf-8")
    counts = {s: {c: sum(x["class"] == c for x in d["cases"]) for c in CLASSES} for s, d in sets.items()}
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
