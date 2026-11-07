# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T030 (SC-006, procedure_006): redacted receipt of the owner's System One shadow week.

Reads the real-use sources of `docs/development/REAL_USE_EVIDENCE.md` that can hold
SPEC-066 observations and writes
`specs/066-system-one-shadow/evidence/real-use-shadow-<date>.json` with derived,
closed-vocabulary counts only: no identifiers, paths, resource names or content.

Every source is read without changing it: the shadow store through
`system_one_shadow.report()` (which creates and deletes nothing), the plugin registry
through `plugin_registry.inspect_registry()` (the `systemOne` consent that
`plugin-status` reports as `configuredMode`), the telemetry database through a
read-only SQLite connection (so the store's retention-on-access never runs), and the
host plugin caches by directory name. No setting, consent or store is changed.

    python -m scripts.spec066_t030_receipt --dry-run   # print the receipt; write nothing
    python -m scripts.spec066_t030_receipt             # on or after 2026-11-09 (UTC): write it

The receipt is observational real use of one owner. It informs the T032 review and
grants nothing.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # `python scripts/spec066_t030_receipt.py` as well as `-m`
    sys.path.insert(0, str(ROOT))

from agent_braid import __version__  # noqa: E402
from agent_braid import plugin_registry, system_one_shadow as shadow, tooling_telemetry as telemetry  # noqa: E402

EVIDENCE = ROOT / 'specs/066-system-one-shadow/evidence'
SCHEMA = 'agent-braid-spec066-real-use-shadow-receipt/v0.1'
DAY_ONE = date(2026, 11, 2)  # tasks.md T030: first plugin-status with systemOne.activeMode=shadow
DUE = date(2026, 11, 9)      # day 1 plus seven days
NO_OBSERVATIONS = 'no observations'
VERSION = re.compile(r'^\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?$')  # plugin builds
PACKAGE_VERSION = re.compile(r'^\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?(?:\.dev\d+)?$')  # PEP 440 package line
PLUGIN_KEY = 'agent-braid@agent-braid'
TELEMETRY_SELECTION = (('mcp', 'analyze-work'), ('mcp', 'analyze'), ('cli', 'analyze'), ('cli', 'system-one'))
LIMITS = [
    'Observational real use of one owner: not preregistered, not randomized, not bound to a frozen candidate.',
    'Counts only. No accuracy, utility or calibration of System One is measured; the reference backend abstains.',
    'Episodes and telemetry cover UTC dates in the window and only what each store retained (30 dates).',
    'activeMode is a property of the running MCP connection and is not readable offline; configuredMode is.',
    'Plugin versions are the agent-braid versions present in each host plugin cache, not proof of the running build.',
    'Episodes skipped before storage (busy or refused store) are counted only in the observing process.',
    'The window is fixed to the shadow week; when the receipt is made on its last date, that date may be partial.',
    'Counts come from this repository\'s readers (readerPackageVersion), not from the installed plugin runtime.',
]


def today() -> date:
    return datetime.now(timezone.utc).date()


def _closed(counts, allowed) -> dict:
    """A count map whose keys come from a closed vocabulary; anything else stops the receipt."""
    unknown = set(counts) - set(allowed)
    if unknown:
        raise ValueError('value outside the closed vocabulary')
    return {key: counts[key] for key in sorted(counts) if counts[key]}


def _days(first: date, last: date) -> set[str]:
    return {(first + timedelta(days=offset)).isoformat() for offset in range((last - first).days + 1)}


def shadow_counts(window: set[str]) -> dict:
    """SC-006 counts from `system-one report`, restricted to the window dates."""
    try:
        present = shadow.store_present()
        value = shadow.report()
    except (OSError, ValueError):
        return {'status': 'unavailable'}
    totals = {name: Counter() for name in ('operations', 'system2', 'systemOne', 'allPairs', 'schemas')}
    episodes = days = 0
    for bucket in value['days']:
        if bucket['day'] not in window:
            continue
        days += 1
        episodes += bucket['episodes']
        for name, counter in totals.items():
            counter.update(bucket[name])
    analysed = sum(totals['allPairs'].values())
    unknown = totals['allPairs']['unknown']
    return {'status': 'observed' if episodes else NO_OBSERVATIONS,
            'reportSchema': value['schema'],
            'storePresent': present,
            'datesWithEpisodes': days,
            'episodes': episodes,
            'operations': _closed(totals['operations'], shadow.OPERATIONS),
            'episodeSchemas': _closed(totals['schemas'], shadow.SCHEMAS),
            'systemOneStatus': _closed(totals['systemOne'], shadow.STATUSES),
            'pairsAnalysedByClass': _closed(totals['allPairs'], shadow.CLASSIFICATIONS),
            'pairsRecordedByClass': _closed(totals['system2'], shadow.CLASSIFICATIONS),
            'pairsAnalysed': analysed,
            'pairsRecorded': sum(totals['system2'].values()),
            'unknownPairs': unknown,
            'dp1OpportunityShare': round(unknown / analysed, 6) if analysed else None,
            'invalidLinesInRetainedStore': value['invalidLines']}


def consent() -> dict:
    """The registry consent that plugin-status reports as `systemOne.configuredMode`."""
    try:
        home = plugin_registry.home_path()
        if not (home / 'registry.json').exists():
            return {'status': NO_OBSERVATIONS}
        value = plugin_registry.inspect_registry()['value']
    except plugin_registry.RegistryError as exc:
        return {'status': 'unavailable', 'code': exc.code}
    except (OSError, ValueError):
        return {'status': 'unavailable', 'code': 'other'}
    mode = value.get('systemOne', 'off')
    if mode not in plugin_registry.SYSTEM_ONE_MODES or value['telemetry'] not in plugin_registry.TELEMETRY_MODES:
        raise ValueError('value outside the closed vocabulary')
    return {'status': 'observed', 'systemOneConfiguredMode': mode,
            'telemetryConfiguredMode': value['telemetry'], 'systemOneActiveMode': 'not-readable-offline'}


def _telemetry_rows() -> list[tuple] | None:
    """Aggregate rows as `telemetry report` returns them, through a read-only connection."""
    path = telemetry.default_directory() / 'metrics.sqlite3'
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_size > telemetry.MAX_DATABASE_BYTES:
        raise ValueError('unsafe telemetry database')
    db = sqlite3.connect(f'file:{quote(str(path))}?mode=ro', uri=True,
                         timeout=telemetry.SQLITE_TIMEOUT_SECONDS, isolation_level=None)
    try:
        identity = (db.execute('PRAGMA application_id').fetchone()[0], db.execute('PRAGMA user_version').fetchone()[0])
        if identity != (telemetry.APPLICATION_ID, 1):
            raise ValueError('unsupported telemetry database format')
        return db.execute("SELECT day,surface,operation,outcome,metric,bucket,sum(count) FROM cells "
                          "WHERE kind IN ('total','imported') GROUP BY day,surface,operation,outcome,metric,bucket "
                          "ORDER BY day,surface,operation,outcome,metric,bucket").fetchall()
    finally:
        db.close()


def telemetry_counts(window: set[str]) -> dict:
    """Calls by outcome for the shadow-relevant operations, window dates only."""
    try:
        rows = _telemetry_rows()
    except (OSError, ValueError, sqlite3.Error):
        return {'status': 'unavailable'}
    if rows is None:
        return {'status': NO_OBSERVATIONS, 'storePresent': False}
    selected = {key: {'calls': Counter(), 'refusalReasons': Counter(), 'pairClassifications': Counter(), 'dates': set()}
                for key in TELEMETRY_SELECTION}
    for day, surface, operation, outcome, metric, bucket, count in rows:
        entry = selected.get((surface, operation))
        if day not in window or entry is None:
            continue
        if outcome not in telemetry.OUTCOMES:
            raise ValueError('value outside the closed vocabulary')
        if metric == 'calls':
            entry['calls'][outcome] += count
            entry['dates'].add(day)
        elif metric == 'refusal-reason':
            entry['refusalReasons'][bucket] += count
        elif metric == 'classification':
            entry['pairClassifications'][bucket] += count
    operations = {}
    for (surface, operation), entry in selected.items():
        operations[f'{surface}:{operation}'] = {
            'calls': _closed(entry['calls'], telemetry.OUTCOMES),
            'datesWithCalls': len(entry['dates']),
            'refusalReasons': _closed(entry['refusalReasons'], telemetry.REFUSAL_REASONS),
            'pairClassifications': _closed(entry['pairClassifications'], telemetry.CATEGORIES)}
    observed = any(value['calls'] for value in operations.values())
    return {'status': 'observed' if observed else NO_OBSERVATIONS, 'storePresent': True,
            'reportSchema': 'agent-braid-local-telemetry-report/v1', 'operations': operations}


def _cached_versions(cache: Path) -> list[str]:
    try:
        names = [entry.name for entry in cache.iterdir() if entry.is_dir() and not entry.is_symlink()]
    except OSError:
        return []
    return sorted(name for name in names if VERSION.fullmatch(name))


def plugin_versions() -> dict:
    """agent-braid versions in each host's plugin cache, plus Claude Code's installed record."""
    home = Path.home()
    claude = home / '.claude/plugins'
    installed = []
    try:
        record = json.loads((claude / 'installed_plugins.json').read_bytes())
        entries = record.get('plugins', {}).get(PLUGIN_KEY, [])
        installed = sorted({item['version'] for item in entries
                            if isinstance(item, dict) and isinstance(item.get('version'), str)
                            and VERSION.fullmatch(item['version'])})
    except (OSError, ValueError, AttributeError):
        pass
    return {'readerPackageVersion': __version__ if PACKAGE_VERSION.fullmatch(__version__) else None,
            'claudeCode': {'installed': installed,
                           'cached': _cached_versions(claude / 'cache/agent-braid/agent-braid')},
            'codex': {'cached': _cached_versions(home / '.codex/plugins/cache/agent-braid/agent-braid')},
            'opencode': 'not located'}


def _present(*paths: Path) -> bool:
    """Presence only: nothing below the path is listed or read."""
    return any(os.path.lexists(path) for path in paths)


def _other_sources():
    """The remaining REAL_USE_EVIDENCE.md sources; none of them records SPEC-066 episodes or consent."""
    home, data = Path.home(), Path.home() / '.local/share/agent-braid'
    no_shadow = 'it holds no SPEC-066 shadow episodes or consent'
    from_telemetry = 'analyze-work call counts come from telemetry'
    return (('Local evidence, coordination and identity stores',
             (data / 'evidence', data / 'coordination', data / 'identity'), no_shadow),
            ('Runtime state', (home / '.local/state/agent-braid',), no_shadow),
            ('Plugin results', (plugin_registry.home_path() / 'results',), no_shadow),
            ('Claude Code host transcripts', (home / '.claude/projects',),
             from_telemetry + '; the SPEC-053 transcript adapter was not run'),
            ('Codex host sessions', (home / '.codex/sessions',), from_telemetry))


def build(current: date) -> dict:
    last = min(current, DUE)
    window = _days(DAY_ONE, last)
    episodes = shadow_counts(window)
    registry = consent()
    usage = telemetry_counts(window)
    versions = plugin_versions()
    found = lambda value: 'observations' if value['status'] == 'observed' else value['status']
    sources = [
        {'source': 'System One shadow store (system-one report)', 'result': found(episodes)},
        {'source': 'Plugin workspace registry (systemOne consent)', 'result': found(registry)},
        {'source': 'Local technical telemetry (SPEC-047)', 'result': found(usage)},
        {'source': 'Host plugin caches (plugin versions)',
         'result': 'observations' if any(versions['claudeCode'].values()) or versions['codex']['cached']
         else NO_OBSERVATIONS},
        *({'source': name, 'result': (('present; not queried: ' + reason) if _present(*paths) else 'absent')}
          for name, paths, reason in _other_sources()),
    ]
    return {'schema': SCHEMA,
            'specification': 'SPEC-066', 'task': 'T030', 'scenario': 'SC-006', 'procedure': 'procedure_006',
            'receiptDate': current.isoformat(),
            'window': {'firstDate': DAY_ONE.isoformat(), 'lastDate': last.isoformat(), 'clock': 'UTC dates',
                       'basis': 'day 1 is the first plugin-status with systemOne.activeMode=shadow (tasks.md T030)'},
            'outcome': 'observations' if episodes['status'] == 'observed' else NO_OBSERVATIONS,
            'systemOneShadow': episodes,
            'consent': registry,
            'telemetry': usage,
            'versions': versions,
            'sourcesChecked': sources,
            'evidenceClass': 'observational real use (docs/development/REAL_USE_EVIDENCE.md)',
            'limits': list(LIMITS),
            'executionAuthorization': False}


def render(value: dict) -> str:
    text = json.dumps(value, sort_keys=True, indent=1, ensure_ascii=True) + '\n'
    home = str(Path.home())
    if len(home) > 1 and home in text:  # defence in depth: no field may carry a local path
        raise ValueError('receipt would expose a local path')
    return text


def main(argv=None, *, output_dir: Path = EVIDENCE) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run', action='store_true', help='print the receipt to stdout and write nothing')
    args = parser.parse_args(argv)
    current = today()
    try:
        text = render(build(current))
    except ValueError as exc:
        print(f'spec066-t030: refused: {exc}', file=sys.stderr)
        return 2
    if args.dry_run:
        sys.stdout.write(text)
        return 0
    if current < DUE:
        print(f'spec066-t030: refused: the receipt is due on or after {DUE.isoformat()} (UTC); '
              'use --dry-run to preview', file=sys.stderr)
        return 2
    target = output_dir / f'real-use-shadow-{current.isoformat()}.json'
    if target.exists():
        if target.read_text(encoding='utf-8') == text:
            print(f'spec066-t030: unchanged {target.name}')
            return 0
        print(f'spec066-t030: refused: {target.name} exists with different content', file=sys.stderr)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(target, 'x', encoding='utf-8') as stream:
        stream.write(text)
    print(f'spec066-t030: wrote {target.name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
