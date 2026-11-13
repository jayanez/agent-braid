# SPDX-License-Identifier: AGPL-3.0-only
"""Experimental `agent-braid lightning` commands (SPEC-070 REQ-005 to REQ-008, SPEC-071 REQ-010).

`init`, `validate`, `status` and `purge` configure and inspect. `run` delegates to `lightning_runner` (SPEC-071):
`--dry-run` launches nothing, `--fake-hosts` runs the pipeline against fake hosts, and a host run needs the
`plugin setup --lightning lab` consent and the host subscription route. The MCP server never starts a run.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

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
    for name in ('init', 'validate', 'status', 'purge', 'run', 'report'):
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
    runner.add_argument('--prompt-set', choices=('development', 'held-out'), default='development')
    runner.add_argument('--plugin-dir', type=Path, help='a prebuilt plugins/agent-braid directory; skips the build')
    runner.add_argument('--seed-run', metavar='RUN_ID',
                        help='apo/gepa: a finished development baseline run whose results score the seed')
    runner.add_argument('--rng-seed', type=int, default=0, help='gepa: parent and minibatch sampling seed')
    runner.add_argument('--source', choices=('final', 'baseline'), default='final',
                        help='apo/gepa: plugin arm the seed skill and candidate plugin come from '
                             '(final = A0; baseline = T010 guidance, exploratory E1/E2)')
    runner.add_argument('--model', help='pin the Claude Code model of rollouts and optimizer calls '
                                         '(apo/gepa default: claude-sonnet-5-5, the SPEC-071 T012 model)')
    purge = commands.choices['purge']
    target = purge.add_mutually_exclusive_group(required=True)
    target.add_argument('--run-id')
    target.add_argument('--expired', action='store_true', help='remove runs older than the profile retention')


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


def run(args, *, ask=None) -> int:
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
                      'setupConsent': consent, 'runs': len(store.list_runs(home)),
                      'path': str(config.config_path(home)), 'executionAuthorization': False}
        else:
            if args.expired:
                value = config.load(home)
                if value is None:
                    raise config.ConfigError('No Braid Lightning profile; retention is unknown', 'config-missing-key')
                output = store.sweep(home, value['traces']['retentionDays'])
            else:
                output = store.purge(home, args.run_id)
            output['executionAuthorization'] = False
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        code = getattr(exc, 'code', 'other')
        print(f'lightning refused ({code}): {exc}', file=sys.stderr)
        return 2
