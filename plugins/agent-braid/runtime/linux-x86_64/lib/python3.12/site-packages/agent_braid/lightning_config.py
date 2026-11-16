# SPDX-License-Identifier: AGPL-3.0-only
# Configuration surface adapted from microsoft/agent-lightning agentlightning/verl/config.yaml at commit
# bc3a9e80417d731744040df5d37117f9cc48005f (v1.0.3) and the v0.x Trainer keyword arguments at commit
# 6db3c73dc0af2e50fe80e56873a57c1703f1b2a7, Copyright (c) Microsoft Corporation, MIT License
# (LICENSES/Agent-Lightning-MIT.txt). Changes: Hydra/OmegaConf YAML replaced by one JSON document with exact
# keys and closed enumerations; Kubernetes, gateway and GPU trainer keys removed; spend, route, promotion
# and execution authority are fixed constants. See docs/development/THIRD_PARTY.md.
"""Braid Lightning configuration profile and its wizard (SPEC-070 REQ-004, REQ-005; SPEC-074 REQ-001)."""
from __future__ import annotations

import copy
from datetime import date
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile

from . import plugin_registry as registry

SCHEMA = 'braid-lightning-config/v0.1'
PREVIEW_SCHEMA = 'braid-lightning-init-preview/v0.1'
MAX_BYTES = 64 * 1024
HOSTS = ('claude-code', 'opencode')

# (kind, argument, default). Kinds: const, enum, int, bool, path, sha|null, subset (unique, non-empty unless noted).
FIELDS = {
    'target': {
        'kind': ('enum', ('skill',), 'skill'),
        'path': ('path', None, 'integrations/agent-braid/skills/agent-braid-analyze/SKILL.md'),
        'lab': ('enum', ('spec069',), 'spec069'),
    },
    'data': {
        'train': ('path', None, 'specs/069-aim-request-authoring/prompts/development.json'),
        'holdout': ('path', None, 'specs/069-aim-request-authoring/prompts/held-out.json'),
        'freezeSha256': ('sha-or-null', None, None),
    },
    'rollout': {
        'hosts': ('subset', HOSTS, list(HOSTS)),
        'repetitions': ('int', (1, 5), 3),
        'maxTurns': ('int', (1, 50), 12),
        'timeoutSeconds': ('int', (30, 3600), 300),
        'parallel': ('int', (1, 4), 1),
    },
    'algorithm': {
        'name': ('enum', ('gepa', 'apo', 'baseline'), 'gepa'),
        'beamWidth': ('int', (1, 8), 4),
        'branchFactor': ('int', (1, 8), 4),
        'rounds': ('int', (1, 10), 3),
        'minibatch': ('int', (1, 32), 5),
    },
    'optimizer': {
        'host': ('enum', HOSTS, 'claude-code'),
        'route': ('const', 'subscription', 'subscription'),
    },
    'reward': {
        'components': ('subset', ('schema', 'd4', 'canary'), ['schema', 'd4', 'canary']),
        'gate': ('enum', ('d4-holdout',), 'd4-holdout'),
    },
    'budget': {
        'maxRollouts': ('int', (1, 2000), 120),
        'maxOptimizerCalls': ('int', (0, 500), 40),
        'eurCap': ('const', 0, 0),
    },
    'traces': {
        'sources': ('subset', ('rollout', 'host-transcript', 'loom', 'system-one'), ['rollout']),
        'contentConsent': ('enum', ('none', 'redacted'), 'none'),
        'retentionDays': ('int', (1, 90), 30),
        # SPEC-074 consent record: set only by `lightning init --apply`, never by an answer. Optional in a stored
        # profile (BL.0 profiles lack them) and canonicalized to null; the consent never expires (OD-3).
        'consentedAt': ('date-or-null', None, None),
        'consentPreviewDigest': ('sha-or-null', None, None),
    },
    'export': {
        'enabled': ('bool', None, False),
        'level': ('enum', ('transition', 'trajectory'), 'trajectory'),
    },
    'promotion': {
        'mode': ('const', 'human', 'human'),
        'executionAuthorization': ('const', False, False),
    },
}
OPTIONAL = {('traces', 'consentedAt'), ('traces', 'consentPreviewDigest')}
CONSENT_RECORD = ('consentedAt', 'consentPreviewDigest')
REDACTION_CLASSES = ('secret', 'token', 'bearer', 'private-key', 'email (per-run salted hash)', 'home path')
_SHA = re.compile(r'[0-9a-f]{64}')
_DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
_PATH_PART = re.compile(r'[A-Za-z0-9._-]+')


class ConfigError(ValueError):
    """A Braid Lightning configuration is refused; `code` is from the contract's closed vocabulary."""

    def __init__(self, message: str, code: str = 'config-shape'):
        super().__init__(message)
        self.code = code


def defaults() -> dict:
    value = {'schema': SCHEMA}
    for section, keys in FIELDS.items():
        value[section] = {key: copy.deepcopy(spec[2]) for key, spec in keys.items()}
    return value


def _check(where: str, kind: str, argument, item):
    if kind == 'const':
        if type(item) is not type(argument) or item != argument:
            raise ConfigError(f'{where} is fixed to {json.dumps(argument)}', 'config-constant')
    elif kind == 'enum':
        if not isinstance(item, str):
            raise ConfigError(f'{where} must be a string', 'config-type')
        if item not in argument:
            raise ConfigError(f'{where} must be one of {", ".join(argument)}', 'config-enum')
    elif kind == 'int':
        if type(item) is not int:
            raise ConfigError(f'{where} must be an integer', 'config-type')
        low, high = argument
        if not low <= item <= high:
            raise ConfigError(f'{where} must be in [{low}, {high}]', 'config-range')
    elif kind == 'bool':
        if type(item) is not bool:
            raise ConfigError(f'{where} must be a boolean', 'config-type')
    elif kind == 'path':
        if not isinstance(item, str):
            raise ConfigError(f'{where} must be a string', 'config-type')
        parts = PurePosixPath(item).parts
        if (not 1 <= len(item) <= 256 or item.startswith('/') or '\\' in item or not parts
                or any(part in ('.', '..') or not _PATH_PART.fullmatch(part) for part in parts)
                or PurePosixPath(*parts).as_posix() != item):
            raise ConfigError(f'{where} must be a normalized repository-relative path', 'config-path')
    elif kind == 'sha-or-null':
        if item is not None and (not isinstance(item, str) or not _SHA.fullmatch(item)):
            raise ConfigError(f'{where} must be a lowercase SHA-256 digest or null', 'config-type')
    elif kind == 'date-or-null':
        if item is not None:
            if not isinstance(item, str) or not _DATE.fullmatch(item):
                raise ConfigError(f'{where} must be a YYYY-MM-DD date or null', 'config-type')
            try:
                date.fromisoformat(item)
            except ValueError as exc:
                raise ConfigError(f'{where} must be a YYYY-MM-DD date or null', 'config-type') from exc
    elif kind == 'subset':
        if not isinstance(item, list) or not all(isinstance(x, str) for x in item):
            raise ConfigError(f'{where} must be a list of strings', 'config-type')
        if not item:
            raise ConfigError(f'{where} must not be empty', 'config-range')
        if len(set(item)) != len(item):
            raise ConfigError(f'{where} has duplicate entries', 'config-duplicate')
        if set(item) - set(argument):
            raise ConfigError(f'{where} entries must be among {", ".join(argument)}', 'config-enum')


def _exact(value, keys, where: str) -> None:
    if not isinstance(value, dict):
        raise ConfigError(f'{where} must be an object', 'config-type')
    unknown, missing = set(value) - set(keys), set(keys) - set(value)
    if unknown:
        raise ConfigError(f'{where} has unknown key(s): {", ".join(sorted(unknown))}', 'config-unknown-key')
    if missing:
        raise ConfigError(f'{where} lacks key(s): {", ".join(sorted(missing))}', 'config-missing-key')


def _consent(traces: dict, pending: bool) -> None:
    """`none` carries no consent record; `redacted` carries the apply date and the applied preview digest."""
    if traces['contentConsent'] == 'none':
        if any(traces[key] is not None for key in CONSENT_RECORD):
            raise ConfigError('traces.consentedAt and consentPreviewDigest must be null without consent', 'config-consent')
    elif traces['consentedAt'] is None or (traces['consentPreviewDigest'] is None and not pending):
        raise ConfigError('traces.contentConsent redacted needs the record written by lightning init --apply',
                          'config-consent')


def validate(value, *, pending_consent: bool = False) -> dict:
    """Return a canonical copy of a complete configuration or raise ConfigError.

    `pending_consent` admits a `redacted` profile whose preview digest is not yet known (an init preview).
    """
    _exact(value, {'schema', *FIELDS}, 'configuration')
    if value['schema'] != SCHEMA:
        raise ConfigError('Unknown configuration schema', 'config-constant')
    value = copy.deepcopy(value)
    for section, keys in FIELDS.items():
        if isinstance(value[section], dict):
            for optional_section, key in OPTIONAL:
                if optional_section == section:
                    value[section].setdefault(key, None)
        _exact(value[section], keys, section)
        for key, (kind, argument, _default) in keys.items():
            _check(f'{section}.{key}', kind, argument, value[section][key])
    if value['data']['train'] == value['data']['holdout']:
        raise ConfigError('data.train and data.holdout must differ', 'config-duplicate')
    _consent(value['traces'], pending_consent)
    canonical = value
    for section, keys in FIELDS.items():
        for key, (kind, argument, _default) in keys.items():
            if kind == 'subset':  # order carries no meaning; keep the declared order
                canonical[section][key] = [x for x in argument if x in value[section][key]]
    return canonical


def to_bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode()


def digest(value, *, pending_consent: bool = False) -> str:
    return hashlib.sha256(to_bytes(validate(value, pending_consent=pending_consent))).hexdigest()


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ConfigError(f'Duplicate key {key}', 'config-duplicate')
        value[key] = item
    return value


def parse(raw: bytes) -> dict:
    if len(raw) > MAX_BYTES:
        raise ConfigError('Configuration is too large', 'config-shape')
    try:
        value = json.loads(raw, object_pairs_hook=_pairs,
                           parse_constant=lambda name: (_ for _ in ()).throw(ConfigError(f'Non-finite {name}', 'config-type')))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError('Configuration is not valid JSON', 'config-shape') from exc
    return validate(value)


def directory(home: Path | None = None) -> Path:
    return registry.home_path(home) / 'lightning'


def config_path(home: Path | None = None) -> Path:
    return directory(home) / 'lightning.json'


def _read(path: Path) -> bytes | None:
    registry._safe(path.parent.parent, directory=True)
    registry._safe(path.parent, directory=True)
    registry._safe(path, directory=False)
    if not path.exists():
        return None
    registry._private(path, directory=False)
    return path.read_bytes()


def load(home: Path | None = None) -> dict | None:
    raw = _read(config_path(home))
    return None if raw is None else parse(raw)


def build(answers: dict | None = None, *, previous: dict | None = None, today: date | None = None) -> dict:
    """Overlay `{section: {key: value}}` answers on the defaults and validate.

    The consent record is derived, never answered: `redacted` keeps the previous record when the previous
    profile already consented to the same sources, otherwise it is dated `today` and awaits its digest.
    """
    value = defaults()
    for section, keys in (answers or {}).items():
        if section not in FIELDS or not isinstance(keys, dict):
            raise ConfigError(f'Unknown section {section}', 'config-unknown-key')
        for key, item in keys.items():
            if key not in FIELDS[section]:
                raise ConfigError(f'Unknown key {section}.{key}', 'config-unknown-key')
            if section == 'traces' and key in CONSENT_RECORD:
                raise ConfigError(f'{section}.{key} is written only by lightning init --apply', 'config-consent')
            value[section][key] = item
    traces = value['traces']
    if traces['contentConsent'] == 'redacted' and isinstance(traces['contentConsent'], str):
        before = (previous or {}).get('traces', {})
        same = (before.get('contentConsent') == 'redacted'
                and isinstance(traces['sources'], list) and set(before.get('sources', ())) == set(traces['sources']))
        if same:
            traces.update({key: before[key] for key in CONSENT_RECORD})
        else:
            traces['consentedAt'] = (today or date.today()).isoformat()
    return validate(value, pending_consent=True)


def effects(value: dict) -> list[str]:
    rollout, budget = value['rollout'], value['budget']
    return [
        'Write only the private Braid Lightning profile; no run starts and no host or model is contacted',
        f"Target {value['target']['path']} ({value['target']['lab']} laboratory); algorithm {value['algorithm']['name']}",
        f"Rollouts on {', '.join(rollout['hosts'])}, {rollout['repetitions']} repetition(s), parallel {rollout['parallel']}; "
        f"budget at most {budget['maxRollouts']} rollouts and {budget['maxOptimizerCalls']} optimizer calls",
        'Model route: host subscription only; any *_API_KEY is refused; extra cash spend EUR 0',
        *consent_effects(value),
        'Promotion is human only; executionAuthorization stays false',
    ]


def consent_summary(value: dict) -> dict:
    """The consent facts `status` and the init preview show (SPEC-074 OD-3: consent has no expiry)."""
    traces = value['traces']
    return {'contentConsent': traces['contentConsent'], 'consentedAt': traces['consentedAt'],
            'sources': traces['sources'], 'retentionDays': traces['retentionDays'], 'expires': None}


def consent_effects(value: dict) -> list[str]:
    traces = value['traces']
    retention = f"retention {traces['retentionDays']} day(s), then the sweep deletes content records"
    if traces['contentConsent'] == 'none':
        return [f"Trace content consent none: every record stays content-free; {retention}",
                'Lowering consent stores no new content; agent-braid lightning purge removes stored runs']
    since = ('kept from the previous consent' if traces['consentPreviewDigest']
             else 'recorded when this preview is applied')
    return [
        f"Trace content consent redacted since {traces['consentedAt']} ({since}); it does not expire and "
        'stays until lightning init lowers it to none',
        f"Content sources: {', '.join(traces['sources'])}; other sources stay content-free; host transcripts, "
        'Loom and System One files are read in place and never modified',
        f"Redaction before storage: {', '.join(REDACTION_CLASSES)}; a record whose post-redaction scan is "
        'not clean is refused',
        f"Content is stored only in the private plugin home lightning/ directory (owner-only), never uploaded; {retention}",
        'Residual risk: pattern redaction cannot catch every secret shape or personal detail (for example '
        'names in free text)',
        'Until the SPEC-074 store gate lands, the store still refuses every content field',
    ]


def plan_init(home: Path | None, answers: dict | None = None, *, today: date | None = None) -> dict:
    path = config_path(home)
    before = _read(path)
    try:
        previous = None if before is None else parse(before)
    except ConfigError:
        previous = None  # an unreadable profile carries no consent (fail closed)
    value = build(answers, previous=previous, today=today)
    preview = {'schema': PREVIEW_SCHEMA, 'path': str(path),
               'beforeSha256': None if before is None else hashlib.sha256(before).hexdigest(),
               'config': value, 'configDigest': digest(value, pending_consent=True),
               'consent': consent_summary(value), 'effects': effects(value),
               'executionAuthorization': False}
    preview['previewDigest'] = hashlib.sha256(to_bytes(preview)).hexdigest()
    return preview


def apply_init(home: Path | None, preview: dict, preview_digest: str | None) -> dict:
    path = config_path(home)
    body = {key: item for key, item in preview.items() if key != 'previewDigest'}
    if (not preview_digest or preview.get('previewDigest') != preview_digest
            or hashlib.sha256(to_bytes(body)).hexdigest() != preview_digest or preview.get('path') != str(path)):
        raise ConfigError('Preview digest does not match; preview again', 'config-digest')
    value = validate(preview['config'], pending_consent=True)
    if value['traces']['contentConsent'] == 'redacted' and value['traces']['consentPreviewDigest'] is None:
        value['traces']['consentPreviewDigest'] = preview_digest
    value = validate(value)
    home_dir = path.parent.parent
    registry._safe(home_dir, directory=True)
    home_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    registry._private(home_dir, directory=True)
    registry._safe(path.parent, directory=True)
    path.parent.mkdir(mode=0o700, exist_ok=True)
    registry._private(path.parent, directory=True)
    before = _read(path)
    if (None if before is None else hashlib.sha256(before).hexdigest()) != preview['beforeSha256']:
        raise ConfigError('Profile changed after preview; preview again', 'config-changed')
    fd, name = tempfile.mkstemp(prefix='.lightning-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(to_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise
    return {'status': 'configured', 'path': str(path), 'configDigest': digest(value),
            'consent': consent_summary(value), 'executionAuthorization': False}
