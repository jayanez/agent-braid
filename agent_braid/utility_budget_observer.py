# SPDX-License-Identifier: AGPL-3.0-only
"""Opt-in coordinator budget observations, outside frozen process-runner bytes.

Only explicitly registered coordinator budgets are observed. Worker threads share
those same budgets; this context never installs global patches or execution hooks.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, TypeVar

_Budget = TypeVar('_Budget')
_observer: ContextVar[Callable[[object], None] | None] = ContextVar(
    'utility_git_budget_observer', default=None)


@contextmanager
def observe_git_budgets(callback):
    """Restore the previous observer even after a failed treatment."""
    token = _observer.set(callback)
    try:
        yield
    finally:
        _observer.reset(token)


def observe_git_budget(budget: _Budget) -> _Budget:
    """Observe and return the exact same budget without authorizing execution."""
    callback = _observer.get()
    if callback is not None:
        try:
            callback(budget)
        except BaseException:
            # An instrumentation callback cannot interrupt or alter execution.
            pass
    return budget
