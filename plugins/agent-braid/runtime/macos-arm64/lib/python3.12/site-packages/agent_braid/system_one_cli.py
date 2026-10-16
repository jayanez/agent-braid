# SPDX-License-Identifier: AGPL-3.0-only
"""Opt-in offline decision command; file acquisition precedes core ingress."""
from __future__ import annotations

import os
from pathlib import Path
import stat


def read_input(path: Path) -> bytes:
    """Read at most 1 MiB from one regular local file, refusing symlink/FIFO."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 1_048_576:
            raise ValueError("invalid local input")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(1_048_577)
        if len(raw) > 1_048_576:
            raise ValueError("invalid local input")
        return raw
    finally:
        os.close(descriptor)


def run(args) -> int:
    # Imports remain lazy: legacy commands do not instantiate a decision runtime.
    from .system_one import canonical, thaw
    from .system_one_backends import DecisionRuntime, capabilities

    if args.decision_command == "capabilities":
        print(canonical(thaw(capabilities())).decode("utf-8"))
        return 0
    try:
        raw = read_input(args.input)
    except (OSError, ValueError):
        print('{"error":"system-one requires a bounded regular local input file"}')
        return 2
    with DecisionRuntime() as runtime:
        response = runtime.evaluate(raw)
    print(canonical(response).decode("utf-8"))
    return {"answered": 0, "abstain": 1, "defer": 1, "refused": 2}[response["status"]]
