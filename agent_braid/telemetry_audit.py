# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only, bounded audit of the host MCP logs of this plugin against the local telemetry store.

Only files named ``<cache root>/<any project>/mcp-logs-plugin-agent-braid-agent-braid/*.jsonl`` are read, and from
each line only the event kind, the day, a salted hash of the session and a closed-vocabulary class are kept. Paths,
working directories, project directory names, arguments, results and free text never enter the output. Nothing is
written, uploaded or repaired, and the result is advice about observation gaps, not a cause or an approval.
"""
from __future__ import annotations

import datetime
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import stat

from .tooling_telemetry import OPERATIONS, REFUSAL_REASONS

SCHEMA = 'agent-braid-telemetry-log-audit/v1'
LOG_DIR_NAME = 'mcp-logs-plugin-agent-braid-agent-braid'
DEFAULT_WINDOW_DAYS = 7
RETENTION_DAYS = 30
MAX_FILES = 4096
MAX_ENTRIES = 8192
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_LINE_CHARS = 256 * 1024
MAX_SESSION_HASHES = 50

# Log classes of a failed tool call, matched on fixed phrases of the plugin's own envelope summaries.
CALL_CLASSES = ('router-refused', 'reconnect-required', 'worktree-allowlist', 'request-shape', 'arguments-invalid',
                'operation-refused', 'other')
STARTUP_CLASSES = REFUSAL_REASONS

CANNOT_SEE = (
    'Startup failures before the registry passed validation or without consent local: serve-start leaves no trace.',
    'Calls from sessions whose workspace has telemetry off, or made before consent was enabled.',
    'The precise reason of most router-level refusals: the host log shows one generic summary (only reconnect-required is spelled out), so only the store has the bucket.',
    'Calls the host never forwarded (permission prompts, tool lists, a server that never connected).',
    'Other hosts (for example Codex), logs the host already rotated away, and any process death before the store write.',
    'Durations, user intent, cause, approval and whether a refusal was the correct outcome.',
)
LIMITS = (
    'Advisory only: log text is classified with fixed phrases and may mis-bucket; a gap is a signal to inspect, not a cause.',
    'The store report includes imported batches; log sessions are counted once per day and reason while serve-start counts events; a call crossing UTC midnight shows as open on one day.',
    'Counts cover Claude CLI host logs of this plugin on this machine and the local store in this OS account only.',
    'plugin-status and workspaces are counted by the store only from builds with SPEC-047/T011, so older gaps for them are expected.',
)

_CALL = re.compile(r"^Calling MCP tool: ([A-Za-z0-9_-]{1,64})$")
_OK = re.compile(r"^Tool '([A-Za-z0-9_-]{1,64})' completed successfully in ")
_FAIL = re.compile(r"^Tool '([A-Za-z0-9_-]{1,64})' failed after [0-9.]+m?s: (.*)$", re.S)
_STATUS = re.compile(r'"status":"([a-z-]{1,20})"')
_SUMMARY = re.compile(r'"summary":"((?:[^"\\]|\\.){0,400})"')
_STARTUP = re.compile(r"^(?:stderr of the stdio server before restarting it|Server stderr): plugin refused: (.*)$", re.S)
_CONNECTED = re.compile(r"^Successfully connected \(transport: stdio\)")
_CONNECTION_FAILED = re.compile(r"^Connection failed after .*\(CONNECTION_CLOSED\)")
_DAY = re.compile(r'^(\d{4}-\d{2}-\d{2})T')
_GENERIC_ROUTER = 'Plugin request refused: check workspace, arguments, registry and reconnect state'


def classify_call_failure(summary: str) -> str:
    lowered = summary.lower()
    if summary == _GENERIC_ROUTER:
        return 'router-refused'
    for needle, label in (('reconnect', 'reconnect-required'), ('allowlist', 'worktree-allowlist'),
                          ('shape is invalid', 'request-shape'), ('do not match the declared input schema', 'arguments-invalid'),
                          ('bounded operation was refused', 'operation-refused')):
        if needle in lowered:
            return label
    return 'other'


def classify_startup(message: str) -> str:
    """Approximate the telemetry bucket from fixed phrases; the real bucket is only in the store."""
    lowered = message.lower()
    for needles, label in ((('unsafe', 'symbolic', 'private to its user', 'canonical path', 'overlap', 'traversal'), 'registry-unsafe-path'),
                           (('migrat',), 'migration-required'), (('reconnect',), 'reconnect-required'),
                           (('grant',), 'grant-missing'), (('registry', 'workspace', 'malformed', 'unknown'), 'registry-shape')):
        if any(needle in lowered for needle in needles):
            return label
    return 'other'


def default_cache_root() -> Path | None:
    home = Path.home()
    for candidate in (home / 'Library/Caches/claude-cli-nodejs', home / '.cache/claude-cli-nodejs'):
        if candidate.is_dir():
            return candidate
    return None


def _log_files(cache_root: Path):
    """Yield (regular, non-symlink) plugin log files; names of project directories are never reported."""
    if cache_root.is_symlink() or not cache_root.is_dir():
        return
    for project in itertools.islice(cache_root.iterdir(), MAX_ENTRIES):
        logs = project / LOG_DIR_NAME
        if project.is_symlink() or logs.is_symlink() or not logs.is_dir():
            continue
        for path in itertools.islice(logs.glob('*.jsonl'), MAX_ENTRIES):
            if not path.is_symlink() and stat.S_ISREG(path.lstat().st_mode):
                yield path


def _empty_day():
    return {'connections': 0, 'connectionFailures': 0, 'startupRefusals': {}, 'startupRefusalSessions': set(),
            'calls': {}, 'callFailureClasses': {}}


def _tool(name: str) -> str:
    return name if name in OPERATIONS['mcp'] else 'other'


def _bump(mapping: dict, key: str, amount: int = 1):
    mapping[key] = mapping.get(key, 0) + amount


def read_logs(cache_root: Path, since: str, salt: bytes) -> dict:
    """Aggregate plugin host logs from ``since`` (UTC date, inclusive) into closed-vocabulary daily counts."""
    days: dict[str, dict] = {}
    startup_seen: set[tuple] = set()
    stats = {'filesRead': 0, 'filesSkipped': 0, 'linesRead': 0, 'linesSkipped': 0, 'truncated': False}
    total = 0
    for path in _log_files(cache_root):
        if stats['filesRead'] + stats['filesSkipped'] >= MAX_FILES or total >= MAX_TOTAL_BYTES:
            stats['truncated'] = True
            break
        try:
            descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        except OSError:
            stats['filesSkipped'] += 1
            continue
        with os.fdopen(descriptor, 'rb') as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode):
                stats['filesSkipped'] += 1
                continue
            if info.st_size > MAX_FILE_BYTES or total + info.st_size > MAX_TOTAL_BYTES:
                stats['filesSkipped'] += 1
                stats['truncated'] = True
                continue
            data = handle.read(MAX_FILE_BYTES + 1)
        total += len(data)
        stats['filesRead'] += 1
        for raw in data.splitlines():
            stats['linesRead'] += 1
            event = _parse_line(raw)
            if event is None:
                stats['linesSkipped'] += 1
                continue
            kind, text, day, session = event
            if day < since:
                continue
            _apply(days, startup_seen, kind, text, day, session, salt)
    for day in days.values():
        for tool in day['calls'].values():
            tool['unfinished'] = max(0, tool['calls'] - tool['ok'] - tool['refused'] - tool['error'])
        day['startupRefusalSessionCount'] = len(day['startupRefusalSessions'])
        day['startupRefusalSessions'] = sorted(day['startupRefusalSessions'])[:MAX_SESSION_HASHES]
    return {**stats, 'days': dict(sorted(days.items()))}


def _parse_line(raw: bytes):
    if len(raw) > MAX_LINE_CHARS:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(value, dict):
        return None
    timestamp, session = value.get('timestamp'), value.get('sessionId')
    match = _DAY.match(timestamp) if isinstance(timestamp, str) else None
    if not match or not isinstance(session, str):
        return None
    if isinstance(value.get('debug'), str):
        return 'debug', value['debug'], match.group(1), session
    if isinstance(value.get('error'), str):
        return 'error', value['error'], match.group(1), session
    return None


def _apply(days, startup_seen, kind, text, day_key, session, salt):
    day = days.setdefault(day_key, _empty_day())
    if kind == 'debug':
        if _CONNECTED.match(text):
            day['connections'] += 1
        elif _CONNECTION_FAILED.match(text):
            day['connectionFailures'] += 1
        elif match := _CALL.match(text):
            _tool_counts(day, match.group(1))['calls'] += 1
        elif match := _OK.match(text):
            _tool_counts(day, match.group(1))['ok'] += 1
        elif match := _FAIL.match(text):
            body = match.group(2)
            status = _STATUS.search(body)
            summary = _SUMMARY.search(body)
            _tool_counts(day, match.group(1))['error' if status and status.group(1) == 'error' else 'refused'] += 1
            _bump(day['callFailureClasses'], classify_call_failure(summary.group(1) if summary else ''))
    match = _STARTUP.match(text)
    if match:
        reason = classify_startup(match.group(1))
        digest = hashlib.sha256(salt + session.encode()).hexdigest()[:8]
        # The same refusal is logged twice (debug and error); count it once per session, day and reason.
        if (day_key, digest, reason) not in startup_seen:
            startup_seen.add((day_key, digest, reason))
            _bump(day['startupRefusals'], reason)
            day['startupRefusalSessions'].add(digest)


def _tool_counts(day, name):
    return day['calls'].setdefault(_tool(name), {'calls': 0, 'ok': 0, 'refused': 0, 'error': 0, 'unfinished': 0})


def reconcile(days: dict, report: dict | None, today: datetime.date, since: str = '') -> dict:
    """Compare log call counts with the store's ``calls`` per UTC day and operation."""
    if report is None:
        return {'status': 'unavailable', 'rows': [], 'flagged': 0}
    first_retained = (today - datetime.timedelta(days=RETENTION_DAYS - 1)).isoformat()
    store: dict[tuple, dict] = {}
    serve_start_refused: dict[str, int] = {}
    for row in report.get('rows', []):
        if row['metric'] != 'calls':
            continue
        if row['surface'] == 'mcp':
            _bump(store.setdefault((row['day'], row['operation']), {}), row['outcome'], row['count'])
        elif row['surface'] == 'lifecycle' and row['outcome'] == 'refused':
            _bump(serve_start_refused, row['day'], row['count'])
    keys = {(d, op) for d, v in days.items() for op, c in v['calls'].items() if c['calls']}
    keys |= {key for key in store if key[0] in days or key[0] >= since}  # store-only days are gaps too
    rows = []
    for day, operation in sorted(keys):
        log = days.get(day, {}).get('calls', {}).get(operation, {'calls': 0, 'ok': 0, 'refused': 0, 'error': 0})
        outcomes = store.get((day, operation), {})
        store_calls = sum(outcomes.values())
        store_failed = outcomes.get('refused', 0) + outcomes.get('error', 0)
        log_failed = log['refused'] + log['error']
        retained = day >= first_retained
        rows.append({'day': day, 'operation': operation, 'logCalls': log['calls'], 'storeCalls': store_calls,
                     'callGap': log['calls'] - store_calls, 'logFailed': log_failed, 'storeFailed': store_failed,
                     'failedGap': log_failed - store_failed, 'inStoreRetention': retained,
                     'flagged': retained and (log['calls'] != store_calls or log_failed != store_failed)})
    startup = [{'day': day, 'logStartupRefusalSessions': days.get(day, {}).get('startupRefusalSessionCount', 0),
                'storeServeStartRefused': serve_start_refused.get(day, 0)}
               for day in sorted(set(days) | set(serve_start_refused)) if day >= since
               and (days.get(day, {}).get('startupRefusalSessionCount') or serve_start_refused.get(day))]
    return {'status': 'compared' if report.get('rows') else 'store-empty', 'rows': rows, 'startup': startup,
            'flagged': sum(1 for row in rows if row['flagged']), 'storeRetentionStart': first_retained}


def audit(cache_root: Path | None, report: dict | None, today: datetime.date | None = None,
          since: str | None = None, salt: bytes | None = None) -> dict:
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    since = since or (today - datetime.timedelta(days=DEFAULT_WINDOW_DAYS - 1)).isoformat()
    logs = read_logs(cache_root, since, salt or os.urandom(8)) if cache_root else None
    days = logs['days'] if logs else {}
    reconciliation = reconcile(days, report, today, since)
    startup_total = sum(sum(day['startupRefusals'].values()) for day in days.values())
    alerts = []
    if startup_total:
        alerts.append('startup-refusals')
    if reconciliation['flagged']:
        alerts.append('reconciliation-gap')
    if reconciliation['status'] == 'store-empty':
        alerts.append('store-empty')
    summary = {'startupRefusals': startup_total, 'connectionFailures': sum(d['connectionFailures'] for d in days.values()),
               'callFailureClasses': {}}
    for day in days.values():
        for label, count in day['callFailureClasses'].items():
            _bump(summary['callFailureClasses'], label, count)
    return {'schema': SCHEMA, 'since': since, 'today': today.isoformat(), 'logsAvailable': logs is not None,
            'logs': {k: v for k, v in (logs or {}).items() if k != 'days'}, 'days': days, 'summary': summary,
            'reconciliation': reconciliation, 'alerts': alerts, 'cannotSee': list(CANNOT_SEE), 'limits': list(LIMITS)}


def render_text(result: dict) -> str:
    lines = [f"Telemetry log audit since {result['since']} (UTC), advisory only"]
    if not result['logsAvailable']:
        lines.append('No Claude CLI cache found: host logs unavailable')
    summary = result['summary']
    lines.append(f"Startup refusals: {summary['startupRefusals']}; connection failures: {summary['connectionFailures']}")
    for day, value in result['days'].items():
        calls = ', '.join(f"{op} {c['calls']}={c['ok']}ok/{c['refused']}ref/{c['error']}err/{c['unfinished']}open"
                          for op, c in sorted(value['calls'].items()))
        reasons = ', '.join(f'{k} {v}' for k, v in sorted(value['startupRefusals'].items()))
        lines.append(f"{day}: connections {value['connections']}, startup refusals [{reasons or 'none'}]; calls: {calls or 'none'}")
    reconciliation = result['reconciliation']
    lines.append(f"Reconciliation: {reconciliation['status']}, flagged rows {reconciliation['flagged']}")
    for row in reconciliation['rows']:
        if row['flagged']:
            lines.append(f"  GAP {row['day']} {row['operation']}: log {row['logCalls']} vs store {row['storeCalls']}"
                         f" (failed {row['logFailed']} vs {row['storeFailed']})")
    lines.append('Alerts: ' + (', '.join(result['alerts']) or 'none'))
    lines.append('Telemetry cannot see:')
    lines.extend('  - ' + item for item in result['cannotSee'])
    lines.extend(result['limits'])
    return '\n'.join(lines)
