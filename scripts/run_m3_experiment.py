#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Print reproducible finite M3 corpus observations; never authorize execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys
from time import perf_counter
import tracemalloc

from agent_braid.structured_exchange import exhaustive_corpus


def main() -> int:
    paths = [Path("agent_braid/structured_exchange.py"),
             Path("docs/theory/STRUCTURED_EXCHANGE.md"),
             Path("specs/018-structured-exchange/fixtures/same-anchor.json")]
    inputs = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    tracemalloc.start()
    started = perf_counter()
    report = exhaustive_corpus()
    elapsed = perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result = {"format": "m3-finite-corpus-v1", "inputs": inputs,
              "python": sys.version.split()[0], "platform": platform.platform(),
              "elapsedSeconds": round(elapsed, 6), "peakTrackedBytes": peak,
              "result": report, "limits": [
                  "Fixed IDs and payloads; anchor topology exhaustive only.",
                  "Producer and verifier use the same replay implementation.",
                  "Elapsed time and tracked memory are one local observation, not production claims.",
              ]}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if report["falseCertificates"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
