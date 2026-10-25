# SPDX-License-Identifier: AGPL-3.0-only
"""The single prefix-overlap rule shared by the scheduler and ownership analysis."""

from __future__ import annotations


def paths_overlap(left: str, right: str) -> bool:
    """Two repository paths overlap when equal or when one contains the other."""
    return left == right or left.startswith(right + '/') or right.startswith(left + '/')
