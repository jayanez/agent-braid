# SPDX-License-Identifier: AGPL-3.0-only
"""Apply hard process limits before replacing this launcher with Git."""

from __future__ import annotations

import os
import resource
import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        return 125
    address_space = int(args[0])
    command = args[1:]
    try:
        resource.setrlimit(resource.RLIMIT_AS, (address_space, address_space))
        os.execvpe(command[0], command, os.environ.copy())
    except (OSError, ValueError, resource.error) as exc:
        os.write(2, f"agent-braid-git-limit-setup-failed:{type(exc).__name__}\n".encode())
        return 125
    return 125


if __name__ == "__main__":
    raise SystemExit(main())
