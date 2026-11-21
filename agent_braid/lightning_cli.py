# SPDX-License-Identifier: AGPL-3.0-only
"""Experimental `agent-braid lightning` commands (SPEC-070 REQ-005 to REQ-008, SPEC-071 REQ-010).

`init`, `validate`, `status` and `purge` configure and inspect. `export` (SPEC-075) writes a local dataset from
consented, redacted runs; it refuses with `export-disabled` unless the profile has `export.enabled` true, prints only
counts, hashes and fixed codes (never record content, ids beyond the manifest's, or the output path) and never
writes outside the output directory. `run` delegates to `lightning_runner` (SPEC-071):
`--dry-run` launches nothing, `--fake-hosts` runs the pipeline against fake hosts, and a host run needs the
`plugin setup --lightning lab` consent and the host subscription route. The MCP server never starts a run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import lightning_adapter as adapter
from . import lightning_config as config
from . import lightning_store as store
from . import plugin_registry as registry

# Wizard questions: (section, key, prompt, parser). Defaults come from the contract.
QUESTIONS = (
    ('target', 'path', 'Guidance file to optimize (repository-relative)', str),
    ('rollout', 'hosts', 'Hosts for rollouts (comma-separated: claude-code, opencode)', lambda text: _hosts(text)),
    ('algorithm', 'name', 'Algorithm (gepa, apo, baseline)', str),
    ('rollout', 'repetitions', 'Repetitions per prompt (1-5)', int),
    ('budget', 'maxRollouts', 'Maximum rollouts (1-2000)', int),
    ('traces', 'contentConsent', 'Trace content consent (none, redacted)', str),
    ('traces', 'sources', 'Trace content sources (comma-separated: rollout, host-transcript, loom, system-one)',
     lambda text: _sources(text)),
    ('export', 'enabled', 'Prepare dataset export later (yes/no)',
     lambda text: {'yes': True, 'y': True, 'no': False, 'n': False}[text.strip().lower()]),
)
FLAG_FIELDS = {
    'target_path': ('target', 'path'), 'hosts': ('rollout', 'hosts'), 'algorithm': ('algorithm', 'name'),
    'repetitions': ('rollout', 'repetitions'), 'max_rollouts': ('budget', 'maxRollouts'),
    'max_optimizer_calls': ('budget', 'maxOptimizerCalls'), 'optimizer_host': ('optimizer', 'host'),
    'trace_content': ('traces', 'contentConsent'), 'trace_sources': ('traces', 'sources'),
    'retention_days': ('traces', 'retentionDays'),
    'parallel': ('rollout', 'parallel'), 'beam_width': ('algorithm', 'beamWidth'),
    'branch_factor': ('algorithm', 'branchFactor'), 'rounds': ('algorithm', 'rounds'),
    'minibatch': ('algorithm', 'minibatch'), 'export': ('export', 'enabled'),
}


def _sources(text: str) -> list[str]:
    return [item.strip() for item in text.split(',') if item.strip()]


def _hosts(text: str) -> list[str]:
    return [part.strip() for part in text.split(',') if part.strip()]


def add_parser(subparsers):
    parser = subparsers.add_parser('lightning', help='experimental Braid Lightning optimization laboratory (configure only)')
    commands = parser.add_subparsers(dest='lightning_command', required=True)
    for name in ('init', 'validate', 'status', 'purge', 'sweep', 'run', 'report'):
        command = commands.add_parser(name)
        command.add_argument('--home', type=Path, help='explicit private Agent Braid state root')
    init = commands.choices['init']
    init.add_argument('--non-interactive', action='store_true', help='take answers from flags and defaults only')
    init.add_argument('--target-path')
    init.add_argument('--hosts', type=_hosts)
    init.add_argument('--algorithm', choices=('gepa', 'apo', 'baseline'))
    init.add_argument('--repetitions', type=int)
    init.add_argument('--max-rollouts', type=int)
    init.add_argument('--max-optimizer-calls', type=int)
    init.add_argument('--optimizer-host', choices=config.HOSTS)
    init.add_argument('--trace-content', '--trace-consent', dest='trace_content', choices=('none', 'redacted'),
                      help='content consent (SPEC-074); redacted records the apply date and preview digest')
    init.add_argument('--trace-sources', type=_sources,
                      help='content sources (comma-separated: rollout, host-transcript, loom, system-one)')
    init.add_argument('--retention-days', type=int)
    init.add_argument('--parallel', type=int)
    init.add_argument('--beam-width', type=int, help='apo: candidates kept per round')
    init.add_argument('--branch-factor', type=int, help='apo: children per parent per round')
    init.add_argument('--rounds', type=int, help='apo/gepa: search rounds')
    init.add_argument('--minibatch', type=int, help='apo/gepa: development prompts per minibatch evaluation')
    export = init.add_mutually_exclusive_group()
    export.add_argument('--export', dest='export', action='store_const', const=True, default=None)
    export.add_argument('--no-export', dest='export', action='store_const', const=False)
    init.add_argument('--apply', action='store_true')
    init.add_argument('--preview-digest')
    commands.choices['status'].add_argument('--run-id', help='report one run: attempts, stop and resume command')
    commands.choices['report'].add_argument('--run-id', required=True)
    runner = commands.choices['run']
    mode = runner.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', help='print the planned rollouts; launch nothing')
    mode.add_argument('--fake-hosts', action='store_true', help='run the full pipeline against fake hosts (pipeline-only)')
    mode.add_argument('--resume', metavar='RUN_ID', help='continue a stopped run explicitly (never automatic)')
    runner.add_argument('--prompt-set', choices=('development', 'held-out', 'v2-feedback', 'v2-validation', 'v2-test', 'v3-test'),
                        default='development')
    runner.add_argument('--plugin-dir', type=Path, help='a prebuilt plugins/agent-braid directory; skips the build')
    runner.add_argument('--seed-run', metavar='RUN_ID',
                        help='apo/gepa: a finished development baseline run whose results score the seed')
    runner.add_argument('--rng-seed', type=int, default=0, help='gepa: parent and minibatch sampling seed')
    runner.add_argument('--source', choices=('final', 'baseline'), default='final',
                        help='apo/gepa: plugin arm the seed skill and candidate plugin come from '
                             '(final = A0; baseline = T010 guidance, exploratory E1/E2)')
    runner.add_argument('--model', help='pin the Claude Code model of rollouts and optimizer calls '
                                         '(apo/gepa default: claude-sonnet-5-5, the SPEC-071 T012 model)')
    # export parses its own tokens (export_parser): argparse would echo a bad value before export-disabled is known
    exporter = commands.add_parser('export', add_help=False, prefix_chars='\0',
                                   help='write a local dataset from consented, redacted runs (off by default)')
    exporter.add_argument('export_argv', nargs=argparse.REMAINDER)
    purge = commands.choices['purge']
    target = purge.add_mutually_exclusive_group(required=True)
    target.add_argument('--run-id')
    target.add_argument('--all', action='store_true', help='every run (SPEC-074: content, salts and indexes)')
    target.add_argument('--expired', action='store_true', help='same as lightning sweep')
    purge.add_argument('--apply', action='store_true', help='delete; requires the preview digest')
    purge.add_argument('--preview-digest')


def _answers(args) -> dict:
    answers = {}
    for attribute, (section, key) in FLAG_FIELDS.items():
        value = getattr(args, attribute, None)
        if value is not None:
            answers.setdefault(section, {})[key] = value
    return answers


def _ask(answers: dict, *, ask, say) -> dict:
    """Ask each question not already answered by a flag; an empty reply keeps the default."""
    base = config.defaults()
    for section, key, prompt, convert in QUESTIONS:
        if key in answers.get(section, {}):
            continue
        default = base[section][key]
        shown = ', '.join(default) if isinstance(default, list) else ('yes' if default is True else 'no' if default is False else default)
        while True:
            reply = ask(f'{prompt} [{shown}]: ').strip()
            if not reply:
                break
            try:
                value = convert(reply)
                config.build({section: {key: value}})
            except (ValueError, KeyError, config.ConfigError) as exc:
                say(f'  {exc if isinstance(exc, config.ConfigError) else "Unrecognized answer"}; try again')
                continue
            answers.setdefault(section, {})[key] = value
            break
    return answers


def _flags(answers: dict) -> list[str]:
    """Flags that reproduce an interactive answer set, so the preview can be applied non-interactively."""
    flags = ['--non-interactive']
    for attribute, (section, key) in FLAG_FIELDS.items():
        if key in answers.get(section, {}):
            value = answers[section][key]
            name = '--' + attribute.replace('_', '-')
            if attribute == 'export':
                flags.append('--export' if value else '--no-export')
            else:
                flags += [name, ','.join(value) if isinstance(value, list) else str(value)]
    return flags


EXPORT_HELP = """Write a local dataset from consented, redacted Braid Lightning runs (SPEC-075).

Export is OFF by default: it refuses with export-disabled unless the profile has export.enabled true, which only
`agent-braid lightning init --export` (previewed and applied) sets. No provider's terms have been reviewed (OD-1 is
deferred), so host-model output exports only with an owner terms decision record you write yourself; without one,
only fixture runs export. A record covers one host and the exact model ids it lists (its provider field is
informational only); a run of another host or model stays refused. --out must be a canonical path without symbolic links (on macOS /tmp and /var are
symbolic links: use /private/tmp or a directory under your home) inside an existing directory, and must not exist
or be empty. Records whose source run is past its retention (traces.retentionDays) are excluded and
counted as retention-expired. Exported files are outside lightning purge: purge lists the datasets that cite a
purged run, and you delete them yourself; a small private index (output path, digest, runs) under the
plugin home records each export until you delete the dataset and purge again. Before anything is written, the bytes are scanned for known secret shapes (tokens, bearer headers,
private keys, e-mail addresses, your home path) and for any /Users/<name> or /home/<name> path in any case and
anywhere, such as /home/runner/ or /srv/home/x or a URL path /api/users/42; a hit refuses the export with
canary-detected. The scan catches known shapes only: pattern-based redaction cannot catch every secret shape or
every piece of personal data (for example names in free text). Not caught: a literal secret not given when the
trace was stored, a raw attempt id typed inside content, encodings nested twice or more, and Windows (C:\\Users\\x)
or doubly escaped (\\/Users\\/x) paths. Errors print one line with a fixed code and
no value."""
EXPORT_FLAGS = ('--home', '--run', '--all', '--kind', '--level', '--out', '--seed', '--balance', '--outcome-field',
                '--terms-decision', '--dry-run', '--help')


class _ExportParser(argparse.ArgumentParser):
    def error(self, message):  # argparse would print the offending value
        from . import lightning_export as export
        raise export.ExportError('Invalid export arguments: see lightning export --help', 'invalid-argument')


def export_parser() -> argparse.ArgumentParser:
    parser = _ExportParser(prog='agent-braid lightning export', description=EXPORT_HELP, add_help=False,
                           allow_abbrev=False, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--home', type=Path, help='explicit private Agent Braid state root')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--run', dest='runs', action='append', metavar='RUN_ID', help='a run to export (repeatable)')
    source.add_argument('--all', dest='all_runs', action='store_true', help='every run in the store')
    parser.add_argument('--kind', choices=('supervised', 'rollout'), required=True)
    parser.add_argument('--level', choices=('transition', 'trajectory'), required=True)
    parser.add_argument('--out', type=Path, required=True, help='a new or empty output directory')
    parser.add_argument('--seed', type=int, default=0, help='balance draw seed (default 0)')
    parser.add_argument('--balance', choices=('equal', 'none'), help='rollout: default equal; supervised: always none')
    parser.add_argument('--outcome-field', action='store_true', help='supervised: keep every outcome, labelled')
    parser.add_argument('--terms-decision', metavar='terms/NAME.json',
                        help='your owner terms decision record, relative to the plugin home lightning directory; '
                             'needed to export host-model output; none ships with Agent Braid')
    parser.add_argument('--dry-run', action='store_true', help='check and build everything, write nothing')
    parser.add_argument('--help', '-h', action='store_true', help='show this help')
    return parser


def _export_home(argv: list[str]) -> Path:
    """The --home value, read before the full parse so export-disabled is decided first."""
    for index, token in enumerate(argv):
        if token == '--home' and index + 1 < len(argv):
            return registry.home_path(Path(argv[index + 1]))
        if token.startswith('--home='):
            return registry.home_path(Path(token.split('=', 1)[1]))
    return registry.home_path(None)


def _export(argv: list[str]) -> dict | None:
    from . import lightning_export as export
    if '--help' in argv or '-h' in argv:  # help shows even while export is disabled
        print(export_parser().format_help())
        return None
    home = _export_home(argv)
    try:
        value = config.load(home)
    except (ValueError, OSError):
        value = None  # an unreadable or invalid profile never enables export
    if value is None or value['export']['enabled'] is not True:
        raise export.ExportError('Dataset export is disabled: lightning init --export', 'export-disabled')
    args = export_parser().parse_args(argv)
    try:
        runs = sorted(run['runId'] for run in store.list_runs(home)) if args.all_runs else args.runs
    except (ValueError, OSError):
        raise export.ExportError('Run store refused', 'store-shape') from None
    manifest = export.export_dataset(home, runs, kind=args.kind, level=args.level, out=args.out, seed=args.seed,
                                     balance=args.balance, outcome_field=args.outcome_field,
                                     terms_decision=args.terms_decision, dry_run=args.dry_run)
    return {'status': 'planned' if args.dry_run else 'exported', 'kind': manifest['kind'], 'level': manifest['level'],
            'balance': manifest['balance'], 'seed': manifest['seed'], 'records': len(manifest['records']),
            'exclusions': manifest['exclusions'], 'balanceReport': manifest['balanceReport'],
            'termsDecision': manifest['termsDecision'], 'redactionVersion': manifest['redactionVersion'],
            'recordsSha256': manifest['recordsSha256'], 'digest': manifest['digest'],
            'files': [] if args.dry_run else ['manifest.json', 'records.jsonl'], 'executionAuthorization': False}


def run(args, *, ask=None) -> int:
    if args.lightning_command == 'export':
        return _run_export(args.export_argv)
    try:
        home = registry.home_path(args.home)
        if args.lightning_command == 'init':
            answers = _answers(args)
            if args.apply:
                if not args.non_interactive:
                    raise config.ConfigError('--apply takes its answers from flags; add --non-interactive', 'config-shape')
                output = config.apply_init(home, config.plan_init(home, answers), args.preview_digest)
            else:
                if args.preview_digest:
                    raise config.ConfigError('--preview-digest is only used with --apply', 'config-shape')
                if not args.non_interactive:
                    answers = _ask(answers, ask=ask or input, say=lambda text: print(text, file=sys.stderr))
                output = config.plan_init(home, answers)
                output['applyWith'] = _flags(answers) + ['--apply', '--preview-digest', output['previewDigest']]
        elif args.lightning_command == 'validate':
            value = config.load(home)
            if value is None:
                raise config.ConfigError('No Braid Lightning profile; run lightning init first', 'config-missing-key')
            output = {'status': 'valid', 'path': str(config.config_path(home)), 'configDigest': config.digest(value),
                      'executionAuthorization': False}
        elif args.lightning_command == 'run':
            from . import lightning_runner as runner
            value = config.load(home)
            if value is None:
                raise config.ConfigError('No Braid Lightning profile; run lightning init first', 'config-missing-key')
            root = runner.checkout_root()
            arm = value['algorithm']['name'] in ('apo', 'gepa')
            if arm and args.prompt_set != 'development':
                raise config.ConfigError('Optimization arms run on the development set only', 'holdout-contamination')
            if args.dry_run:
                if arm:
                    from . import lightning_arm
                    output = lightning_arm.estimate(value, root)
                else:
                    output = runner.plan(value, args.prompt_set, root)
                    output.pop('order')
            else:
                if not args.fake_hosts and registry.inspect_registry(home)['value'].get('lightning') != 'lab':
                    raise config.ConfigError('Host runs need setup consent: plugin setup --lightning lab', 'consent-required')
            if arm and not args.dry_run:
                from . import lightning_arm
                if not args.seed_run:
                    raise config.ConfigError('apo and gepa need --seed-run <baseline development run id>', 'config-shape')
                output = lightning_arm.run_arm(home, value, seed_run=args.seed_run, run_id=args.resume,
                                               resume=bool(args.resume), fake_hosts=args.fake_hosts,
                                               plugin_dir=args.plugin_dir, rng_seed=args.rng_seed,
                                               models={'claude-code': args.model} if args.model else None,
                                               source=args.source)
            elif not args.dry_run:
                output = runner.run(home, value, run_id=args.resume, resume=bool(args.resume), prompt_set=args.prompt_set,
                                    fake_hosts=args.fake_hosts, plugin_dir=args.plugin_dir,
                                    models={'claude-code': args.model} if args.model else None)
        elif args.lightning_command == 'report':
            from . import lightning_runner as runner
            output = runner.report(home, args.run_id)
        elif args.lightning_command == 'status' and args.run_id:
            from . import lightning_runner as runner
            output = runner.run_status(home, args.run_id)
        elif args.lightning_command == 'status':
            value = config.load(home)
            consent = registry.inspect_registry(home)['value'].get('lightning', 'off')
            output = {'configured': value is not None, 'configDigest': config.digest(value) if value else None,
                      'traceConsent': config.consent_summary(value if value else config.defaults()),
                      'traceContent': adapter.gate(home),
                      'setupConsent': consent, 'runs': len(store.list_runs(home)),
                      'path': str(config.config_path(home)), 'executionAuthorization': False}
        elif args.lightning_command == 'sweep' or args.expired:
            value = config.load(home)
            if value is None:
                raise config.ConfigError('No Braid Lightning profile; retention is unknown', 'config-missing-key')
            output = store.sweep(home, value['traces']['retentionDays'])
            output['executionAuthorization'] = False
        else:
            run_id = None if args.all else args.run_id
            if args.apply:
                output = store.apply_purge(home, run_id, args.preview_digest)
                purged = output['removed']
            else:
                if args.preview_digest:
                    raise store.StoreError('--preview-digest is only used with --apply', 'store-shape')
                output = store.plan_purge(home, run_id)
                output['applyWith'] = (['--all'] if args.all else ['--run-id', run_id]) + [
                    '--apply', '--preview-digest', output['previewDigest']]
                purged = [run['runId'] for run in output['runs']]
            # SPEC-075 REQ-013: exported datasets are outside purge; list the ones that cite these runs (outside the
            # preview digest, so an export between preview and apply does not stale the preview)
            from . import lightning_export as export
            output['citingDatasets'] = export.citing_manifests(home, purged, prune=bool(args.apply))
            output['datasetsNote'] = ('Exported datasets are not deleted by purge; delete the listed directories '
                                      'yourself')
            output['executionAuthorization'] = False
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        code = getattr(exc, 'code', 'other')
        print(f'lightning refused ({code}): {exc}', file=sys.stderr)
        return 2


def _run_export(argv: list[str]) -> int:
    """Run `lightning export`; every refusal is one stderr line with a fixed code and text (no value, no trace)."""
    from . import lightning_export as export
    try:
        output = _export(list(argv))
    except KeyboardInterrupt:
        print('lightning refused (interrupted): Export interrupted; nothing was written', file=sys.stderr)
        return 130
    except (ValueError, OSError) as exc:
        code = getattr(exc, 'code', None)
        fixed = isinstance(exc, export.ExportError) and isinstance(code, str) and export._CODE.fullmatch(code)
        text = str(exc) if fixed else 'Export refused'
        print(f"lightning refused ({code if fixed else 'other'}): {text}", file=sys.stderr)
        return 2
    if output is not None:
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
    return 0
