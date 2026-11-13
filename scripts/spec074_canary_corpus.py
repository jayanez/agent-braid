# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 REQ-004 (T005): generate the committed secret-canary corpus.

Every canary is synthetic (no real credential) and appears in five forms: plain, JSON-escaped,
URL-encoded, split across two JSON fields, and base64. The output is deterministic, so the test
regenerates it and compares bytes with the committed file.

    python -m scripts.spec074_canary_corpus [--check]
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'tests/fixtures/spec074-canaries/corpus.json'
HOME = '/Users/canary-owner'
LITERAL = 'canary-literal-0f1e2d3c4b5a'
SCHEMA = 'braid-spec074-canary-corpus/v0.1'

# (class, sensitive value). The value is what must never reach an output.
CANARIES = [
    ('secret', LITERAL),
    ('token', 'sk-ant-api03-CANARY' + 'a1B2c3D4e5F6g7H8'),
    ('token', 'sk-proj-CANARY' + 'q9W8e7R6t5Y4u3I2'),
    ('token', 'ghp_CANARY' + 'Zx9Yw8Vu7Ts6Rq5Po4Nm'),
    ('token', 'github_pat_CANARY' + '11AbCdEfGhIjKlMnOpQr'),
    ('token', 'AIzaCANARY' + 'SyA1b2C3d4E5f6G7h8I9j0'),
    ('token', 'xoxb-CANARY' + '-1234567890-abcdef'),
    ('token', 'AKIACANARY' + 'ABCDEF1234'),
    ('token', 'ya29.CANARY' + 'a0AfH6SMBxyz0123456789'),
    ('bearer', 'Bearer CANARY' + 'eyJhbGciOiJIUzI1NiJ9xyz'),
    ('private-key', '-----BEGIN OPENSSH PRIVATE KEY-----\nCANARYb3BlbnNzaC1rZXktdjEAAAAA\n-----END OPENSSH PRIVATE KEY-----'),
    ('email', 'canary.owner@example.org'),
    ('home', HOME + '/projects/secret-plan'),
]
FORMS = ('plain', 'json-escaped', 'url-encoded', 'split', 'base64')


def _json_escaped(value: str) -> str:
    return ''.join(f'\\u{ord(ch):04x}' if ch in '@-_.' or not ch.isalnum() else ch for ch in value)


def record(value: str, form: str) -> dict:
    if form == 'plain':
        return {'text': f'context before {value} context after'}
    if form == 'json-escaped':
        return {'text': 'escaped payload: ' + _json_escaped(value)}
    if form == 'url-encoded':
        return {'text': 'url https://example.invalid/cb?state=' + quote(value, safe='')}
    if form == 'split':
        middle = len(value) // 2
        return {'first': value[:middle], 'second': value[middle:]}
    return {'text': 'blob ' + base64.b64encode(value.encode()).decode()}


def corpus() -> dict:
    items = [{'id': f'{cls}-{n:02d}-{form}', 'class': cls, 'form': form, 'value': value,
              'record': record(value, form)}
             for n, (cls, value) in enumerate(CANARIES) for form in FORMS]
    return {'schema': SCHEMA, 'home': HOME, 'literalSecrets': [LITERAL], 'forms': list(FORMS), 'canaries': items}


def render() -> bytes:
    return (json.dumps(corpus(), indent=1, sort_keys=True, ensure_ascii=True) + '\n').encode()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ['--check']:
        same = CORPUS.exists() and CORPUS.read_bytes() == render()
        print('corpus up to date' if same else 'corpus differs from the generator', file=sys.stderr)
        return 0 if same else 1
    CORPUS.write_bytes(render())
    print(f'wrote {CORPUS.relative_to(ROOT)} ({len(CANARIES) * len(FORMS)} canaries)', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
