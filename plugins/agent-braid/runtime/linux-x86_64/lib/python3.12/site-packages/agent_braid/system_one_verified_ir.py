# SPDX-License-Identifier: AGPL-3.0-only
"""Pure finite LF patch semantics and exact EN/ES grammar for verified plans.

This is an extraction of T024's literal domain, not a general language parser.
Invalid input and trusted checkpoint failures raise sanitized ValueError codes;
only completed finite runs return answered/semantic-defer records. T05 owns the
external refused envelope. Every source-validation hunk (including validation
nested in interpret/render) charges checkpoint('verification', 1). Callers own
that shared context: no function starts clocks or resets outer counters.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from hashlib import sha1
import json
import re
from typing import Any

from .system_one import InvalidDecision, canonical, freeze, parse_json, thaw

Checkpoint = Callable[[str, int], None]
_PROGRAM_KEYS = {'files', 'goal', 'ops', 'plans'}
_HUNK_KEYS = {'begin', 'end', 'old', 'new', 'atStart', 'atEnd', 'patchLines'}
_TOKENS = {
    'symbolic': ('FILE ', 'GOAL ', 'OP ', 'CHANGE ', 'HUNK ', 'PLAN '),
    'en': ('Initial file: ', 'Required final blob: ', 'Operation and dependencies: ',
           'Operation file preimage and postimage: ', 'Operation hunk read and write: ',
           'Offered plan: '),
    'es': ('Archivo inicial: ', 'Blob final requerido: ', 'Operación y dependencias: ',
           'Archivo de operación antes y después: ', 'Lectura y escritura del hunk de operación: ',
           'Plan ofrecido: '),
}


def _require(condition: bool, reason: str = 'invalid-ir') -> None:
    if not condition:
        raise ValueError(reason)


def _json_copy(value: Any, reason: str) -> dict:
    """Admit bounded JSON-compatible records, including frozen mappings/tuples."""
    try:
        _require(isinstance(value, Mapping), reason)
        parse_json(canonical(value))
        stack = [value]
        while stack:
            item = stack.pop()
            if isinstance(item, Mapping):
                _require(all(type(key) is str for key in item), reason)
                stack.extend(item.values())
            elif isinstance(item, (list, tuple)):
                stack.extend(item)
        # JSON validation above must not sort the explicit offered-plan order.
        return thaw(value)
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise ValueError(reason) from None


def _keys(value: Any, keys: set[str]) -> None:
    _require(type(value) is dict and set(value) == keys)


def _blob(lines: list[str] | None) -> str:
    if lines is None:
        return '0' * 40
    data = ''.join(lines).encode('utf-8')
    return sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def _text(lines: Any, *, initial: bool = True) -> None:
    _require(type(lines) is list and 1 <= len(lines) <= (64 if initial else 128))
    _require(all(type(line) is str and line.endswith('\n') and line.count('\n') == 1
                 and '\r' not in line and '\0' not in line and bool(line.strip())
                 for line in lines))
    _require(len(''.join(lines).encode('utf-8')) <= (4096 if initial else 8192))


def _matches(lines: list[str], block: list[str]) -> list[int]:
    return [index for index in range(len(lines) - len(block) + 1)
            if lines[index:index + len(block)] == block]


def _has_trailing_context(hunk: dict) -> bool:
    # Actual diff prefixes matter even when adjacent text happens to be equal.
    return hunk['patchLines'][-1].startswith(' ')


def _apply(files: dict, changes: list, checkpoint: Checkpoint) -> tuple[dict | None, list, str | None]:
    """Stage all files; failure returns no committed state, with attempted trace."""
    staged = {path: None if lines is None else list(lines) for path, lines in files.items()}
    trace = []
    for change in changes:
        checkpoint('verification', 0)
        path = change['path']
        current = staged[path]
        if current is None:
            if change['hunks'][0]['old'] is not None:
                return None, trace, 'missing-context'
            checkpoint('verification', 1)
            current = list(change['hunks'][0]['new'])
            trace.append({'path': path, 'hunk': 0, 'position': 0})
        else:
            for index, hunk in enumerate(change['hunks']):
                checkpoint('verification', 1)
                if hunk['old'] is None:
                    return None, trace, 'file-already-exists'
                matches = [position for position in _matches(current, hunk['old'])
                           if (not hunk['atStart'] or position == 0)
                           and (not hunk['atEnd'] or _has_trailing_context(hunk)
                                or position + len(hunk['old']) == len(current))]
                _require(len(matches) <= 1, 'ambiguous-anchor')
                if not matches:
                    return None, trace, 'missing-context'
                position = matches[0]
                current = current[:position] + hunk['new'] + current[position + len(hunk['old']):]
                _text(current, initial=False)
                trace.append({'path': path, 'hunk': index, 'position': position})
        _text(current, initial=False)
        staged[path] = current
    return staged, trace, None


def _validate(program: dict, checkpoint: Checkpoint) -> None:
    _keys(program, _PROGRAM_KEYS)
    _require(all(type(program[key]) is dict for key in program))
    files, goal, ops, plans = (program[key] for key in ('files', 'goal', 'ops', 'plans'))
    _require(1 <= len(files) <= 8 and set(goal) == set(files))
    for path, lines in files.items():
        checkpoint('verification', 0)
        _require(re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.txt', path) is not None)
        if lines is not None:
            _text(lines)
        _require(type(goal[path]) is str and re.fullmatch(r'[0-9a-f]{40}', goal[path]) is not None)
    _require(2 <= len(ops) <= 4 and set(ops) == set('abcd'[:len(ops)]))
    changed = set()
    for name, op in ops.items():
        checkpoint('verification', 0)
        _keys(op, {'dependencies', 'changes'})
        dependencies, changes = op['dependencies'], op['changes']
        _require(type(dependencies) is list and all(type(item) is str and item in ops and item != name
                                                   for item in dependencies))
        _require(len(set(dependencies)) == len(dependencies))
        _require(type(changes) is list and 1 <= len(changes) <= 2)
        paths = []
        for change in changes:
            checkpoint('verification', 0)
            _keys(change, {'path', 'old', 'new', 'hunks'})
            path = change['path']
            _require(type(path) is str and path in files and path not in paths)
            paths.append(path)
            changed.add(path)
            _require(change['old'] == _blob(files[path]))
            _require(type(change['new']) is str and re.fullmatch(r'[0-9a-f]{40}', change['new']) is not None
                     and change['new'] != change['old'])
            hunks = change['hunks']
            _require(type(hunks) is list and 1 <= len(hunks) <= 2)
            cursor, reconstructed, base = 0, [], files[path]
            for hunk in hunks:
                checkpoint('verification', 0)
                _keys(hunk, _HUNK_KEYS)
                patch = hunk['patchLines']
                _require(type(patch) is list and 1 <= len(patch) <= 128)
                _require(all(type(line) is str and len(line) > 1 and line[0] in ' +-'
                             for line in patch))
                _require([line[1:] for line in patch if line[0] in ' -'] ==
                         ([] if hunk['old'] is None else hunk['old']))
                _require([line[1:] for line in patch if line[0] in ' +'] == hunk['new'])
                _require(any(line[0] in '+-' for line in patch))
                _require(type(hunk['begin']) is int and type(hunk['end']) is int)
                _require(type(hunk['atStart']) is bool and type(hunk['atEnd']) is bool)
                _text(hunk['new'])
                if base is None:
                    _require(len(hunks) == 1 and hunk['old'] is None
                             and hunk['begin'] == hunk['end'] == 0
                             and hunk['atStart'] is True and hunk['atEnd'] is True)
                    reconstructed = list(hunk['new'])
                    continue
                _text(hunk['old'])
                _require(cursor <= hunk['begin'] < hunk['end'] <= len(base))
                _require(hunk['atStart'] == (hunk['begin'] == 0)
                         and hunk['atEnd'] == (hunk['end'] == len(base)))
                _require(base[hunk['begin']:hunk['end']] == hunk['old']
                         and _matches(base, hunk['old']) == [hunk['begin']], 'ambiguous-anchor')
                reconstructed += base[cursor:hunk['begin']] + hunk['new']
                cursor = hunk['end']
            if base is not None:
                reconstructed += base[cursor:]
            _text(reconstructed)
            _require(_blob(reconstructed) == change['new'])
        _require(paths == sorted(paths))
        staged, _, failure = _apply(files, changes, checkpoint)
        _require(failure is None and staged is not None)
        _require(all(_blob(staged[change['path']]) == change['new'] for change in changes))
    _require(changed == set(files))
    remaining, done = set(ops), set()
    while remaining:
        checkpoint('verification', 0)
        ready = {name for name in remaining if set(ops[name]['dependencies']) <= done}
        _require(bool(ready))
        remaining -= ready
        done |= ready
    _require(len(plans) == 4 and sum(sequence is None for sequence in plans.values()) == 1)
    for key, sequence in plans.items():
        checkpoint('verification', 0)
        _require(re.fullmatch(r'[a-z][a-z0-9]*', key) is not None and len(key.encode('utf-8')) <= 64)
        _require(sequence is None or type(sequence) is list and len(sequence) <= 6
                 and all(type(name) is str and name in ops for name in sequence))


def validate_program(program: Mapping[str, object], *, checkpoint: Checkpoint) -> Mapping[str, object]:
    """Validate/copy the retained IR; source simulation consumes shared hunk work."""
    checkpoint('verification', 0)
    value = _json_copy(program, 'invalid-ir')
    _validate(value, checkpoint)
    checkpoint('verification', 0)
    return freeze(value)


def _literal(value: Any) -> str:
    return json.dumps(thaw(value), ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def _render(program: dict, language: str, representation: str, checkpoint: Checkpoint) -> dict:
    _require(language in ('en', 'es') and representation in ('symbolic', 'controlled'), 'text-mismatch')
    tokens = _TOKENS['symbolic' if representation == 'symbolic' else language]
    lines = [f'T024 {representation} {language}.']

    def add(kind: int, value: Any) -> None:
        checkpoint('interpretation', 0)
        lines.append(tokens[kind] + _literal(value) + '.')

    for path in sorted(program['files']):
        add(0, [path, program['files'][path]])
    for path in sorted(program['goal']):
        add(1, [path, program['goal'][path]])
    for name in sorted(program['ops']):
        op = program['ops'][name]
        add(2, [name, op['dependencies']])
        for change in op['changes']:
            add(3, [name, change['path'], change['old'], change['new']])
            for hunk in change['hunks']:
                add(4, [name, change['path']] + [hunk[key] for key in
                    ('begin', 'end', 'old', 'new', 'atStart', 'atEnd', 'patchLines')])
    for key, sequence in program['plans'].items():
        add(5, [key, sequence])
    text = '\n'.join(lines) + '\n'
    _require(len(lines) <= 96 and len(text.encode('utf-8')) <= 65536, 'text-mismatch')
    return {'format': 't024-text-v1', 'language': language, 'representation': representation,
            'text': text, 'executionAuthorization': False}


def render(program: Mapping[str, object], language: str, representation: str, *,
           checkpoint: Checkpoint) -> Mapping[str, object]:
    """Render the exact grammar; nested source validation charges verification."""
    checkpoint('interpretation', 0)
    value = _json_copy(program, 'invalid-ir')
    _validate(value, checkpoint)
    result = _render(value, language, representation, checkpoint)
    checkpoint('interpretation', 0)
    return freeze(result)


def interpret(payload: Mapping[str, object], *, checkpoint: Checkpoint) -> Mapping[str, object]:
    """Extract only the complete canonical grammar; never infer unknown facts."""
    checkpoint('interpretation', 0)
    value = _json_copy(payload, 'text-mismatch')
    _require(set(value) == {'format', 'language', 'representation', 'text', 'executionAuthorization'},
             'text-mismatch')
    _require(value['format'] == 't024-text-v1' and value['executionAuthorization'] is False,
             'text-mismatch')
    language, representation, text = value['language'], value['representation'], value['text']
    _require(language in ('en', 'es') and representation in ('symbolic', 'controlled'), 'text-mismatch')
    _require(type(text) is str and len(text.encode('utf-8')) <= 65536 and text.endswith('\n'), 'text-mismatch')
    lines = text[:-1].split('\n')
    _require(2 <= len(lines) <= 96 and lines[0] == f'T024 {representation} {language}.', 'text-mismatch')
    tokens = _TOKENS['symbolic' if representation == 'symbolic' else language]
    program = {'files': {}, 'goal': {}, 'ops': {}, 'plans': {}}
    changes = {}
    for line in lines[1:]:
        checkpoint('interpretation', 0)
        matches = [index for index, token in enumerate(tokens)
                   if line.startswith(token) and line.endswith('.')]
        _require(len(matches) == 1, 'text-mismatch')
        kind = matches[0]
        try:
            record = parse_json(('{"record":' + line[len(tokens[kind]):-1] + '}').encode('utf-8'))['record']
        except (InvalidDecision, UnicodeError):
            raise ValueError('text-mismatch') from None
        _require(type(record) is list and len(record) == (2, 2, 2, 4, 9, 2)[kind], 'text-mismatch')
        _require(type(record[0]) is str, 'text-mismatch')
        if kind in (0, 1, 5):
            target = program[('files', 'goal', '', '', '', 'plans')[kind]]
            _require(record[0] not in target, 'text-mismatch')
            target[record[0]] = record[1]
        elif kind == 2:
            _require(record[0] not in program['ops'], 'text-mismatch')
            program['ops'][record[0]] = {'dependencies': record[1], 'changes': []}
        elif kind == 3:
            _require(record[0] in program['ops'] and type(record[1]) is str, 'text-mismatch')
            key = (record[0], record[1])
            _require(key not in changes, 'text-mismatch')
            change = {'path': record[1], 'old': record[2], 'new': record[3], 'hunks': []}
            changes[key] = change
            program['ops'][record[0]]['changes'].append(change)
        else:
            _require(type(record[1]) is str and (record[0], record[1]) in changes, 'text-mismatch')
            changes[(record[0], record[1])]['hunks'].append(dict(zip(
                ('begin', 'end', 'old', 'new', 'atStart', 'atEnd', 'patchLines'), record[2:])))
    _validate(program, checkpoint)
    _require(_render(program, language, representation, checkpoint)['text'] == text, 'text-mismatch')
    checkpoint('interpretation', 0)
    return freeze(program)


def _run(program: dict, sequence: list, checkpoint: Checkpoint) -> dict:
    files, completed, trace, failure = program['files'], [], [], None
    for index, name in enumerate(sequence):
        checkpoint('verification', 0)
        operation = program['ops'][name]
        if name in completed or not set(operation['dependencies']) <= set(completed):
            failure = {'step': index, 'reason': 'operation-precondition'}
            break
        staged, fragments, reason = _apply(files, operation['changes'], checkpoint)
        blobs = {path: _blob(lines) for path, lines in (staged if staged is not None else files).items()}
        trace.append({'operation': name, 'committed': reason is None, 'fragments': fragments,
                      'blobsAfter': blobs})
        if reason is not None:
            failure = {'step': index, 'reason': reason}
            break
        files = staged
        completed.append(name)
    complete = failure is None and set(completed) == set(program['ops']) and len(completed) == len(program['ops'])
    goal = all(_blob(files[path]) == blob for path, blob in program['goal'].items())
    if failure is None and not (complete and goal):
        failure = {'step': len(sequence), 'reason': 'final-goal'}
    return {'valid': complete and goal, 'complete': complete, 'goalAchieved': goal,
            'cost': len(sequence), 'failure': failure, 'trace': trace,
            'finalBlobs': {path: _blob(lines) for path, lines in files.items()},
            'executionAuthorization': False}


def verify_program(program: Mapping[str, object], option_order: tuple[str, ...], *,
                   max_hunks: int, checkpoint: Checkpoint) -> Mapping[str, object]:
    """Check all offered plans; raise on unknown/invalid/exhausted work.

    This local cap tightens the caller's shared cap and includes source validation.
    It does not reset the caller's accumulated work across prior/repeated calls.
    """
    checkpoint('verification', 0)
    _require(type(max_hunks) is int and 0 <= max_hunks <= 128, 'invalid-budget')
    value = _json_copy(program, 'invalid-ir')
    used = 0

    def checked(stage: str, units: int) -> None:
        nonlocal used
        _require(used + units <= max_hunks, 'work-budget-exceeded')
        checkpoint(stage, units)
        used += units

    _validate(value, checked)
    _require(type(option_order) is tuple and len(option_order) == 4
             and all(type(key) is str for key in option_order)
             and len(set(option_order)) == 4 and set(option_order) == set(value['plans']))
    runs = {}
    for key in option_order:
        checked('verification', 0)
        if value['plans'][key] is not None:
            runs[key] = _run(value, value['plans'][key], checked)
    successes = {key: result['cost'] for key, result in runs.items() if result['valid']}
    minimum = min(successes.values()) if successes else None
    eligible = sorted(key for key, cost in successes.items() if cost == minimum)
    status = 'answered' if eligible else 'semantic-defer'
    if not eligible:
        eligible = [key for key in option_order if value['plans'][key] is None]
    checked('verification', 0)
    return freeze({'status': status, 'eligible': eligible, 'choice': eligible[0],
                   'plans': runs, 'executionAuthorization': False})
