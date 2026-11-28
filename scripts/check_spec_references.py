# SPDX-License-Identifier: AGPL-3.0-only
"""Mechanical cross-reference check of feature specifications.

Answers, without a model, questions a reviewer otherwise answers by reading every file: does each cited REQ,
SC, OD or task ID exist, does each requirement have a scenario and a task, do the task dependencies form a
cycle, and does each planned test file appear in the files of the task that produces it. It does not judge
meaning: it shows that a cited ID exists, not that it is the right one.

Conventions it reads (docs/development/SPEC_KIT.md, "Reference check and review sequence"):

- ``assurance.json`` defines REQ and SC IDs; ``tasks.md`` defines tasks (``- [ ] T001 (trace): text``, with
  indented continuation lines); ``Task ID T0nn is retired`` in ``tasks.md`` declares an unused task ID.
- ``spec.md`` defines owner decisions as list items that start with ``**OD-<id>``.
- A task states its dependencies in a ``Dependencies:`` clause and its files in a ``Files:`` clause.
- A ``validation-plan.md`` row whose last column reads ``Output of T0nn`` names the task whose files hold the test.
- ``SPEC-NNN <id>`` cites an ID of another feature; the ID is resolved in that feature's folder.

    python3 -m scripts.check_spec_references specs/090-example [specs/091-example ...]

Exit status 0 when no error is found, 1 on errors, 2 when an argument is not a feature folder. Warnings do not
fail the check.

Host-specific by design: the checks depend on this repository's conventions, so SpecTorque, the external
checker this repository uses, does not take them over. Run by hand; not wired into CI or the validation
profiles. Specs written before these conventions are not expected to pass.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ID = r"(?:REQ-\d{3,}|SC-\d{3,}|OD-[A-Za-z0-9]+|T\d{3})"
TOKEN = re.compile(rf"(?<![\w-]){ID}(?![\w])")
JOIN = r"(?:\s*(?:,|/|\.\.|–|-)\s*|\s+(?:to|through|and|or)\s+)"
FOREIGN = re.compile(rf"\bSPEC-(\d{{3}})\b(?:\]\([^)]*\))?(\s*\(\s*|\s+)({ID}(?:{JOIN}{ID})*)")
RANGE = re.compile(r"(?<![\w-])(REQ-|SC-|OD-|T)([A-Z]|\d+)\s*(?:\.\.|–|-|to|through)\s*\1([A-Z]|\d+)(?!\w)")
URL = re.compile(r"https?://\S+")
TASK_LINE = re.compile(r"^- \[[ x]\] (T\d{3})(?: \(([^)]*)\))?: (.*)$")
RETIRED = re.compile(r"\bTask ID (T\d{3}) is retired\b")
OD_DEFINITION = re.compile(r"^\s*[-*]\s+\*\*(OD-[A-Za-z0-9]+)", re.M)
FIELD = r"(?=\b(?:Dependencies|Verification|Files|Tests|Obtained):|$)"
DEPENDENCIES = re.compile(r"Dependencies:(.*?)" + FIELD, re.S)
FILES = re.compile(r"Files:(.*?)" + FIELD, re.S)
PLAN_ROW = re.compile(r"^\|\s*REQ-\d+\s*\|\s*(SC-\d+)\s*\|\s*`([^`]+)`\s*\|.*\|\s*Output of (T\d{3})\.?\s*\|\s*$")
PLACEHOLDERS = {'OD-n', 'OD-x'}


def _expand(text: str) -> list[str]:
    """The IDs strictly inside each range of ``text`` (the endpoints are ordinary tokens)."""
    found = []
    for prefix, low, high in RANGE.findall(text):
        if low.isdigit() and high.isdigit():
            found += [f'{prefix}{n:0{len(low)}d}' for n in range(int(low) + 1, int(high))]
        elif low.isalpha() and high.isalpha():
            found += [prefix + chr(n) for n in range(ord(low) + 1, ord(high))]
    return found


def _ids(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text) + _expand(text) if t not in PLACEHOLDERS]


def _split_foreign(text: str) -> tuple[str, list[tuple[int, str, str, bool]]]:
    """Blank ``SPEC-NNN <ids>`` citations in ``text``; return it and (offset, spec, id, strict) per cited ID.

    ``strict`` holds for the ID written directly after ``SPEC-NNN``; an ID after a bracket or a conjunction may
    belong to either feature.
    """
    found = []

    def blank(match: re.Match) -> str:
        found.extend((match.start(), match[1], token, i == 0 and '(' not in match[2])
                     for i, token in enumerate(_ids(match[3])))
        return re.sub(r'[^\n]', ' ', match[0])

    return FOREIGN.sub(blank, text), found


def _rank(value: str) -> int:
    return int(value) if value.isdigit() else ord(value)


class Feature:
    def __init__(self, folder: Path):
        self.folder, self.name = folder, folder.name
        self.notes: list[str] = []
        self.texts = {p.relative_to(folder).as_posix(): URL.sub('', p.read_text(encoding='utf-8'))
                      for p in sorted(folder.rglob('*.md'))}
        self.requirements: dict[str, list[str]] = {}
        self.has_record = (folder / 'assurance.json').exists()
        if self.has_record:
            try:
                for item in json.loads((folder / 'assurance.json').read_text(encoding='utf-8'))['requirements']:
                    self.requirements[item['id']] = [s['id'] for s in item.get('scenarios', [])]
            except (ValueError, KeyError, TypeError):
                self.has_record, self.requirements = False, {}
                self.notes.append('assurance.json is not readable; REQ and SC citations are not checked')
        else:
            self.notes.append('no assurance.json; REQ and SC citations are not checked')
        self.scenarios = {s for ids in self.requirements.values() for s in ids}
        self.tasks: dict[str, tuple[str, str]] = {}
        self.has_tasks = 'tasks.md' in self.texts
        current = None
        for line in self.texts.get('tasks.md', '').splitlines():
            match = TASK_LINE.match(line)
            if match:
                current = match[1]
                self.tasks[current] = (match[2] or '', match[3])
            elif current and line[:1] in ' \t' and line.strip():
                self.tasks[current] = (self.tasks[current][0], self.tasks[current][1] + ' ' + line.strip())
            else:
                current = None
        if not self.has_tasks:
            self.notes.append('no tasks.md; task citations are not checked')
        self.retired = set(RETIRED.findall(self.texts.get('tasks.md', '')))
        self.decisions = set(OD_DEFINITION.findall(self.texts.get('spec.md', ''))) - PLACEHOLDERS
        self.defined = set(self.requirements) | self.scenarios | set(self.tasks) | self.decisions | self.retired

    def checks(self, token: str) -> bool:
        """Whether this feature can say if ``token`` is defined."""
        if token.startswith(('REQ-', 'SC-')):
            return self.has_record
        return self.has_tasks if token.startswith('T') else True


def check(folders: list[Path]) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    checked = [Feature(folder) for folder in folders]
    known = {feature.folder: feature for feature in checked}
    edges: dict[str, set[str]] = {}

    def lookup(number: str, near: Path, where: str) -> Feature | None:
        found = [p for p in sorted(near.glob(f'{number}-*')) if (p / 'spec.md').exists()]
        if not found:
            errors.append(f'{where}: SPEC-{number} does not exist')
        elif len(found) > 1:
            errors.append(f'{where}: SPEC-{number} is ambiguous: ' + ', '.join(p.name for p in found))
        if len(found) != 1:
            return None
        return known.setdefault(found[0], Feature(found[0]))

    for feature in checked:
        where = feature.name
        warnings += [f'{where}: {note}' for note in feature.notes]
        prose = {}
        for name, text in feature.texts.items():
            local, foreign = _split_foreign(text)
            prose[name] = local
            for number_, line in enumerate(local.splitlines(), 1):
                for token in _ids(line):
                    if feature.checks(token) and token not in feature.defined:
                        errors.append(f'{where}/{name}:{number_}: {token} is cited but not defined')
            for offset, number, token, strict in foreign:
                at = f'{where}/{name}:{text.count(chr(10), 0, offset) + 1}'
                target = lookup(number, feature.folder.parent, at)
                if target is not None and target.checks(token) and token not in target.defined \
                        and (strict or not feature.checks(token) or token not in feature.defined):
                    errors.append(f'{at}: SPEC-{number} {token} is cited but not defined')
        for requirement, scenarios in feature.requirements.items():
            if not scenarios:
                errors.append(f'{where}: {requirement} has no acceptance scenario')
        traced = set(_ids(_split_foreign(' '.join(f'{t} {b}' for t, b in feature.tasks.values()))[0]))
        for item in sorted(set(feature.requirements) | feature.scenarios):
            if feature.tasks and item not in traced:
                errors.append(f'{where}: {item} is not traced by any task')
        for task, (trace, body) in feature.tasks.items():
            if 'REQ-' not in trace and task != 'T001':
                warnings.append(f'{where}/tasks.md: {task} names no requirement')
            clause = ' '.join(DEPENDENCIES.findall(body)).strip()
            clause = '' if clause.lower().startswith('none') else re.sub(r'\([^)]*\)', ' ', clause)
            local, foreign = _split_foreign(clause)
            mine = set(re.findall(r'\bT\d{3}\b', local))
            if task in mine:
                errors.append(f'{where}/tasks.md: {task} depends on itself')
            edges[f'{where}:{task}'] = {f'{where}:{t}' for t in mine - {task}}
            for _, number, token, _ in foreign:
                target = lookup(number, feature.folder.parent, f'{where}/tasks.md') if token[0] == 'T' else None
                if target is not None:
                    edges[f'{where}:{task}'].add(f'{target.name}:{token}')
        review = ' '.join(feature.tasks.get('T001', ('', '')))
        for prefix, low, high in RANGE.findall(review):
            same = [d[3:] for d in feature.decisions if d[3:].isdigit() == high.isdigit()
                    and (d[3:].isdigit() or (len(d) == 4 and d[3:].isupper()))]
            if prefix == 'OD-' and low.isdigit() == high.isdigit() and same \
                    and _rank(max(same, key=_rank)) > _rank(high):
                errors.append(f'{where}/tasks.md: T001 covers decisions up to OD-{high} '
                              f'but the highest decision is OD-{max(same, key=_rank)}')
        outside = '\n'.join(OD_DEFINITION.sub('', line) for text in prose.values()
                            for line in text.splitlines() if not line.startswith('- [') or ' T001' not in line[:12])
        for decision in sorted(feature.decisions - set(_ids(outside))):
            warnings.append(f'{where}: {decision} is defined and never cited')
        for number_, line in enumerate(feature.texts.get('validation-plan.md', '').splitlines(), 1):
            row = PLAN_ROW.match(line)
            if row and feature.has_tasks:
                files = re.findall(r'`([^`]+)`', ' '.join(FILES.findall(feature.tasks.get(row[3], ('', ''))[1])))
                if row[2] not in files:
                    errors.append(f'{where}/validation-plan.md:{number_}: {row[2]} ({row[1]}) is not in the '
                                  f'files of {row[3]}')

    state: dict[str, int] = {}

    def visit(node: str, path: list[str]) -> None:
        state[node] = 1
        for nxt in sorted(edges.get(node, ())):
            if state.get(nxt) == 1:
                errors.append('dependency cycle: ' + ' -> '.join([*path[path.index(nxt):], nxt]))
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
    folders = list(dict.fromkeys(f.resolve() for f in args.features))
    errors, warnings = check(folders)
    for line in warnings:
        print('warning: ' + line)
    for line in errors:
        print('error: ' + line)
    print(f'{len(errors)} error(s), {len(warnings)} warning(s) in {len(folders)} feature(s)')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
