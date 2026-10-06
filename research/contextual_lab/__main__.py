# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit local-file research check/verification; no external execution."""
import argparse
import json
import os
from pathlib import Path
import sys

from research.lab.model import Invalid, canonical, require
from .checker import REPORT_BYTES, REQUEST_BYTES, check, load, verify


def write_exclusive(path, data, input_path):
    require(path.resolve() != input_path.resolve(), "output collides with input")
    require(not any(p.is_symlink() for p in (path, *path.parents)), "symlink destination")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "verify"])
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            require(args.output is not None, "explicit output required")
            result = check(load(args.input, REQUEST_BYTES))
            write_exclusive(args.output, canonical(result), args.input)
            print(json.dumps({"status": "written", "verdict": result["verdict"],
                              "executionAuthorization": False}))
            return 0
        require(args.output is None, "verify is read-only")
        result = verify(load(args.input, REPORT_BYTES))
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "verified" else 1
    except (Invalid, OSError, UnicodeError, ValueError, TypeError, RecursionError):
        print(json.dumps({"status": "rejected", "reason": "invalid bounded local artifact"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
