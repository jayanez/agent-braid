# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only CLI; output goes to stdout, never to external tools."""

import argparse
import json
from pathlib import Path

from .certificates import produce, verify
from .model import Invalid, loads, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["explore", "verify"])
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        require(args.input.stat().st_size <= 8_000_000, "input exceeds 8 MB")
        data = loads(args.input.read_text(encoding="utf-8"))
        result = produce(data) if args.command == "explore" else verify(data)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if args.command == "explore" or result["status"] == "verified" else 1
    except (Invalid, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
