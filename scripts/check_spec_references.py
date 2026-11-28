# SPDX-License-Identifier: AGPL-3.0-only
"""Mechanical cross-reference check of feature specifications.

Answers, without a model, the questions a reviewer otherwise answers by reading every file: does each cited
REQ, SC, OD or task ID exist, does each requirement have a scenario and a task, do the tasks form a cycle, and
does each planned test file belong to the task named as its owner. It reads ``assurance.json`` (REQ and SC),
``tasks.md`` (tasks; ``Task ID T0nn is retired`` declares an unused ID) and ``spec.md`` (owner decisions, written
``**OD-n``); it does not judge meaning. A citation written as
``SPEC-NNN <id>`` is resolved in that feature's folder.

    python -m scripts.check_spec_references specs/090-example [specs/091-example ...]

Exit status 1 when any error is found. Warnings do not fail the check.

Interim tool. Reference integrity of a specification set is the remit of SpecTorque, the external checker this
repository already uses (docs/development/SPEC_KIT.md). Retire this script, its tests and its section in
SPEC_KIT.md when a SpecTorque release reports the same errors for this repository's ID conventions; until then
it is run by hand and is not wired into CI or the validation profiles.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ID = r"(?:REQ-\d{3,}|SC-\d{3,}|OD-[A-Z]?\d*[A-Z]?|T\d{3})"
TOKEN = re.compile(rf"\b{ID}\b")
SEPARATOR = r"(?:\s*(?:,|/|\.\.|to|and|or|–|-)\s*)"
FOREIGN = re.compile(rf"SPEC-(\d{{3}})\b(?:\]\([^)]*\))?[\s(]*((?:{ID}{SEPARATOR}?)+)")
RANGE = re.compile(r"\b(REQ|SC|OD)-(\d+)\s*(?:\.\.|to|–)\s*(?:REQ|SC|OD)-(\d+)\b")
TASK_LINE = re.compile(r"^- \[[ x]\] (T\d{3})(?: \(([^)]*)\))?: (.*)$")
OD_DEFINITION = re.compile(r"\*\*(OD-[A-Z]?\d*[A-Z]?)\b")
DEPENDENCIES = re.compile(r"Dependencies:(.*?)(?=\b(?:Verification|Files|Tests|Obtained):|$)")
RETIRED = re.compile(r"\bTask ID (T\d{3}) is retired\b")
PLAN_ROW = re.compile(r"^\|\s*REQ-\d+\s*\|\s*(SC-\d+)\s*\|\s*`([^`]+)`\s*\|.*\|\s*(.*?)\s*\|\s*$")


class Feature:
    def __init__(self, folder: Path):
        self.folder = folder
        self.number = folder.name[:3]
        self.texts = {p.name: p.read_text(encoding='utf-8') for p in sorted(folder.rglob('*.md'))}
        self.requirements: dict[str, list[str]] = {}
        record = folder / 'assurance.json'
        if record.exists():
            for item in json.loads(record.read_text(encoding='utf-8')).get('requirements', []):
                self.requirements[item['id']] = [s['id'] for s in item.get('scenarios', [])]
        self.scenarios = {s for ids in self.requirements.values() for s in ids}
        self.tasks: dict[str, tuple[str, str]] = {}
        for line in self.texts.get('tasks.md', '').splitlines():
            match = TASK_LINE.match(line)
            if match:
                self.tasks[match[1]] = (match[2] or '', match[3])
        self.retired = set(RETIRED.findall(self.texts.get('tasks.md', '')))
        self.decisions = set(OD_DEFINITION.findall(self.texts.get('spec.md', '')))
        self.defined = set(self.requirements) | self.scenarios | set(self.tasks) | self.decisions | self.retired


def _strip_foreign(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Remove ``SPEC-NNN <ids>`` citations from ``text``; return the rest and the (spec, id) pairs removed."""
    foreign = [(m[1], token) for m in FOREIGN.finditer(text) for token in TOKEN.findall(m[2])]
    return FOREIGN.sub(lambda m: ' ' * len(m[0]), text), foreign


def _expand_ranges(text: str) -> list[str]:
    return [f'{m[1]}-{n:0{len(m[2])}d}' for m in RANGE.finditer(text) for n in range(int(m[2]), int(m[3]) + 1)]


def check(folders: list[Path]) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    features = {f.number: f for f in map(Feature, folders)}
    root = folders[0].parent
    edges: dict[str, set[str]] = {}

    def lookup(number: str) -> Feature | None:
        if number not in features:
            found = sorted(root.glob(f'{number}-*'))
            if found:
                features[number] = Feature(found[0])
        return features.get(number)

    for feature in [features[f.name[:3]] for f in folders]:
        where = feature.folder.name
        cited: set[str] = set()
        for name, text in feature.texts.items():
            for number_, line in enumerate(text.splitlines(), 1):
                local, foreign = _strip_foreign(line)
                for token in TOKEN.findall(local) + _expand_ranges(local):
                    cited.add(token)
                    if token not in feature.defined and token != 'OD-':
                        errors.append(f'{where}/{name}:{number_}: {token} is cited but not defined')
                for number, token in foreign:
                    target = lookup(number)
                    if target is None:
                        errors.append(f'{where}/{name}:{number_}: SPEC-{number} does not exist')
                    elif token not in target.defined and target.defined:
                        errors.append(f'{where}/{name}:{number_}: SPEC-{number} {token} is cited but not defined')
        for requirement, scenarios in feature.requirements.items():
            if not scenarios:
                errors.append(f'{where}: {requirement} has no acceptance scenario')
        task_text = ' '.join(f'{trace} {body}' for trace, body in feature.tasks.values())
        traced = set(TOKEN.findall(task_text)) | set(_expand_ranges(task_text))
        for item in sorted(set(feature.requirements) | feature.scenarios):
            if feature.tasks and item not in traced:
                errors.append(f'{where}: {item} is not traced by any task')
        for task, (trace, body) in feature.tasks.items():
            if 'REQ-' not in trace and task != 'T001':
                warnings.append(f'{where}/tasks.md: {task} names no requirement')
            depends = ' '.join(DEPENDENCIES.findall(body))
            local, foreign = _strip_foreign(depends)
            edges[f'{feature.number}:{task}'] = (
                {f'{feature.number}:{t}' for t in re.findall(r'\bT\d{3}\b', local) if t != task}
                | {f'{n}:{t}' for n, t in foreign if t.startswith('T')})
        numbered = [int(d[3:]) for d in feature.decisions if d[3:].isdigit()]
        review = ' '.join(feature.tasks.get('T001', ('', '')))
        for match in RANGE.finditer(review):
            if match[1] == 'OD' and numbered and int(match[3]) != max(numbered):
                errors.append(f'{where}/tasks.md: T001 covers OD-{match[2]}..OD-{match[3]} '
                              f'but the highest decision is OD-{max(numbered)}')
        outside = '\n'.join(OD_DEFINITION.sub('', line) for text in feature.texts.values()
                            for line in text.splitlines() if not line.startswith('- [') or ' T001' not in line[:12])
        for decision in sorted(feature.decisions - {'OD-'}):
            if not re.search(rf'\b{re.escape(decision)}\b', outside):
                warnings.append(f'{where}: {decision} is defined and never cited')
        for number_, line in enumerate(feature.texts.get('validation-plan.md', '').splitlines(), 1):
            row = PLAN_ROW.match(line)
            owners = re.findall(r'\bT\d{3}\b', row[3]) if row else []
            if row and owners and all(row[2] not in feature.tasks.get(t, ('', ''))[1] for t in owners):
                errors.append(f'{where}/validation-plan.md:{number_}: {row[2]} ({row[1]}) is not in the '
                              f'files of {", ".join(owners)}')

    state: dict[str, int] = {}

    def visit(node: str, path: list[str]) -> None:
        state[node] = 1
        for nxt in sorted(edges.get(node, ())):
            if state.get(nxt) == 1:
                cycle = path[path.index(nxt):] if nxt in path else [nxt]
                errors.append('dependency cycle: ' + ' -> '.join([*cycle, nxt]))
            elif nxt not in state:
                visit(nxt, [*path, nxt])
        state[node] = 2

    for node in sorted(edges):
        if node not in state:
            visit(node, [node])
    return sorted(set(errors)), sorted(set(warnings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('features', nargs='+', type=Path, help='feature folders, e.g. specs/090-example')
    args = parser.parse_args(argv)
    missing = [str(f) for f in args.features if not (f / 'spec.md').exists()]
    if missing:
        print('not a feature folder: ' + ', '.join(missing), file=sys.stderr)
        return 2
    errors, warnings = check([f.resolve() for f in args.features])
    for line in warnings:
        print('warning: ' + line)
    for line in errors:
        print('error: ' + line)
    print(f'{len(errors)} error(s), {len(warnings)} warning(s) in {len(args.features)} feature(s)')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
