# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit bounded local-file simulation and read-only replay verification."""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat

from .evidence import explore, verify
from .model import InvalidWorkload, canonical, loads

REQUEST_BYTES = 8 * 1024 * 1024
REPORT_BYTES = 512 * 1024 * 1024


class Rejected(InvalidWorkload):
    """A CLI refusal carrying a stable machine-readable reason."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _open(name, flags, parent, mode=0o777):
    """Open one path component relative to ``parent``, naming why it failed."""
    try:
        return os.open(name, flags, mode, dir_fd=parent)
    except OSError as exc:
        try:
            link = stat.S_ISLNK(os.stat(name, dir_fd=parent, follow_symlinks=False).st_mode)
        except OSError:
            link = False
        reason = ("symlink-path" if link else "output-exists" if isinstance(exc, FileExistsError)
                  else "unavailable-path")
        raise Rejected(reason) from exc


@contextmanager
def _parent(path):
    path = Path(path).absolute()
    if ".." in path.parts or not path.name or not hasattr(os, "O_NOFOLLOW"):
        raise Rejected("unsupported-path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:-1]:
            child = _open(part, flags, descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor, path.name
    finally:
        os.close(descriptor)


def load_file(path, limit=REQUEST_BYTES):
    """Read a bounded regular file without following any symlink component."""
    with _parent(path) as (parent, name):
        descriptor = _open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, parent)
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise Rejected("not-regular-file")
            if metadata.st_size > limit:
                raise Rejected("too-large")
            raw = stream.read(limit + 1)
            if len(raw) > limit:
                raise Rejected("too-large")
    try:
        return loads(raw, limit=limit)
    except InvalidWorkload as exc:
        raise Rejected("invalid-json") from exc


def write_exclusive(path, data, input_path):
    """Create one explicit output; never replace input, existing files or links."""
    if Path(path).absolute() == Path(input_path).absolute():
        raise Rejected("output-is-input")
    if len(data) > REPORT_BYTES:
        raise Rejected("report-too-large")
    with _parent(path) as (parent, name):
        descriptor = _open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                           parent, 0o600)
        created = os.fstat(descriptor)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
        except BaseException:
            try:
                current = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino):
                    os.unlink(name, dir_fd=parent)
            except FileNotFoundError:
                pass
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("explore", "verify"))
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "explore":
            if args.output is None:
                raise Rejected("output-required")
            report = explore(load_file(args.input))
            write_exclusive(args.output, canonical(report), args.input)
            result = {"status": "written", "verdict": report["comparison"]["verdict"],
                      "requestHash": report["requestHash"], "executionAuthorization": False}
        else:
            if args.output is not None:
                raise Rejected("verify-is-read-only")
            result = verify(load_file(args.input, REPORT_BYTES))
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] in ("written", "verified") else 1
    except Rejected as exc:
        reason = exc.reason
    except InvalidWorkload:
        reason = "invalid-request"
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
        reason = "invalid-bounded-local-artifact"
    print(json.dumps({"status": "rejected", "reason": reason,
                      "executionAuthorization": False}, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
