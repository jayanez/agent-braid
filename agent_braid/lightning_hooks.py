# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from microsoft/agent-lightning agentlightning/hooks.py at commit
# bc3a9e80417d731744040df5d37117f9cc48005f (v1.0.3), Copyright (c) Microsoft Corporation, MIT License
# (LICENSES/Agent-Lightning-MIT.txt). Changes: upstream server-side lifecycle hooks (on_enqueue, on_succeeded,
# on_failed) become rollout-level hooks with the v0.x names; hooks are synchronous, receive read-only copies,
# and a hook failure fails only the rollout. See docs/development/THIRD_PARTY.md.
"""Rollout hooks for the Braid Lightning runner (SPEC-071 REQ-007).

Order per rollout: ``on_rollout_start`` → ``on_trace_end`` → ``on_rollout_end``.
"""
from __future__ import annotations

import copy
from types import MappingProxyType

HOOK_ORDER = ('on_rollout_start', 'on_trace_end', 'on_rollout_end')


class HookFailed(RuntimeError):
    code = 'hook-failed'


class RolloutHooks:
    """Override any method. Arguments are read-only views; return values are ignored."""

    def on_rollout_start(self, rollout):
        pass

    def on_trace_end(self, rollout, result):
        pass

    def on_rollout_end(self, rollout, result, reward):
        pass


def _frozen(value):
    if isinstance(value, dict):
        return MappingProxyType({k: _frozen(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_frozen(v) for v in value)
    return value


def call(hooks: RolloutHooks | None, name: str, *records) -> None:
    """Run one hook on deep read-only copies; any exception becomes ``HookFailed``."""
    if hooks is None:
        return
    if name not in HOOK_ORDER:
        raise ValueError(f'Unknown hook {name}')
    try:
        getattr(hooks, name)(*(_frozen(copy.deepcopy(r)) for r in records))
    except Exception as exc:  # noqa: BLE001 - any hook error fails the rollout only
        raise HookFailed(f'{name} raised {type(exc).__name__}') from exc
