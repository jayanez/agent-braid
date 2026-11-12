# SPDX-License-Identifier: AGPL-3.0-only
"""Write the SPEC-072 held-out fingerprints (REQ-006).

The optimizer path never loads held-out prompts: it scans every optimizer input against these hashes instead. The
file holds sha256 digests of the held-out case ids and of every normalized word window of the held-out prompts, bound
to the held-out file hash recorded in the SPEC-069 FREEZE. Windows that also occur in a development prompt
are left out: development text is optimizer-visible by design. Run once from the repository root after a freeze:

    python -m scripts.spec072_holdout_fingerprints
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent_braid import lightning_runner as runner  # noqa: E402
from agent_braid.lightning_reward import frozen_hashes  # noqa: E402


def build(root: Path = ROOT) -> dict:
    relative = runner.PROMPT_FILES['held-out']
    raw = (root / relative).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if frozen_hashes(root).get(relative) != actual:
        raise SystemExit('held-out.json differs from FREEZE.json; refusing to fingerprint it')
    cases = json.loads(raw)['cases']
    development = json.loads((root / runner.PROMPT_FILES['development']).read_text())['cases']

    def windows_of(prompts) -> set[str]:
        found = set()
        for prompt in prompts:
            words = runner.normalize_words(prompt)
            found |= {runner.window_sha256(words[i:i + runner.WINDOW]) for i in range(len(words) - runner.WINDOW + 1)}
        return found

    # Phrasing the development prompts share is optimizer-visible by design and is not held-out material.
    windows = windows_of(c['prompt'] for c in cases) - windows_of(c['prompt'] for c in development)
    return {'schema': runner.FINGERPRINT_SCHEMA, 'heldOutPath': relative, 'heldOutSha256': actual,
            'window': runner.WINDOW, 'idSha256': sorted(hashlib.sha256(c['id'].encode()).hexdigest() for c in cases),
            'windowSha256': sorted(windows)}


def main() -> int:
    path = ROOT / runner.FINGERPRINTS
    path.write_text(json.dumps(build(), indent=1, sort_keys=True) + '\n')
    print(f'wrote {runner.FINGERPRINTS}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
