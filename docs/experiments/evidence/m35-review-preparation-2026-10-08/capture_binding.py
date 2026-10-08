# SPDX-License-Identifier: AGPL-3.0-only
"""Print preparation input commitments only; no source admission or fitting."""
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.check_m35_review_packet import check_packet, read_auxiliary_file  # noqa: E402


def main() -> None:
    packet = check_packet(ROOT)
    inputs = dict(packet["inputSha256"])
    for name in (
        "scripts/check_m35_review_packet.py",
        "tests/test_m35_review_packet.py",
        "specs/019-native-predictor/completion-plan.md",
        "specs/019-native-predictor/candidate-review-decisions.template.md",
        "docs/experiments/evidence/m35-review-preparation-2026-10-08/capture_binding.py",
        "docs/experiments/evidence/m35-review-preparation-2026-10-08/adversarial-regression-review.md",
    ):
        inputs[name] = sha256(read_auxiliary_file(ROOT, name)).hexdigest()
    result = {
        "format": "m35-review-preparation-evidence-v1",
        "inputs": inputs,
        "packetSha256": packet["packetSha256"],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "outcome": "Preparatory packet structurally complete; zero real admitted pairs; no capture, fit, calibration, held-out evaluation or human approval. Focused test results are recorded separately.",
        "limits": "Input hashes bind supplied bytes, not authenticity, workflow independence, consent, human decisions or scientific evidence. Prospective windows, labels, experiment and M3.5 closure remain pending.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
