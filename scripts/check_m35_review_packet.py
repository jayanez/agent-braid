# SPDX-License-Identifier: AGPL-3.0-only
"""Check a prospective M3.5 source review packet without opening source data.

The checker reads only six fixed repository-relative metadata/document files.
It validates packet shape and commitments; it cannot verify permissions, admit
data, or authorize capture, training, execution, or human review.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
from pathlib import Path
import re
import stat
from typing import Any

FORMAT = "m35-source-candidates-v1"
MAX_FILE_BYTES = 1024 * 1024
MAX_DEPTH = 32
HASH = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
REPOSITORIES = frozenset({"jayanez/agent-braid", "jayanez/kinetiq-core", "jayanez/smart-notes"})
FILES = (
    "specs/019-native-predictor/source-candidates.json",
    "specs/019-native-predictor/workload-protocol.md",
    "specs/019-native-predictor/annotation-rubric.md",
    "specs/019-native-predictor/model-interface-plan.md",
    "specs/019-native-predictor/adr-extension-proposal.md",
    "specs/019-native-predictor/source-review-packet.md",
)
AUXILIARY_FILES = frozenset({
    "scripts/check_m35_review_packet.py",
    "tests/test_m35_review_packet.py",
    "specs/019-native-predictor/completion-plan.md",
    "specs/019-native-predictor/candidate-review-decisions.template.md",
    "docs/experiments/evidence/m35-review-preparation-2026-10-08/capture_binding.py",
    "docs/experiments/evidence/m35-review-preparation-2026-10-08/adversarial-regression-review.md",
})
FAMILY_KEYS = {
    "familyId", "repository", "workflow", "decisionContext", "naturalTrigger",
    "distinctnessReview", "permissionReview", "eligibilityReview",
}


class PacketError(ValueError):
    """A safe-to-report packet validation error with a stable reason code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _parse_json(raw: bytes) -> Any:
    def members(pairs: list[tuple[str, Any]]) -> dict:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise PacketError("duplicate-json-member")
            result[key] = value
        return result

    def reject_constant(_value: str) -> None:
        raise PacketError("nonfinite-json-value")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=members,
                           parse_constant=reject_constant)
    except PacketError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise PacketError("invalid-json") from None
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise PacketError("json-depth-limit")
        if type(item) is dict:
            stack.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            stack.extend((child, depth + 1) for child in item)
    return value


def _read_fixed_file(root: Path, relative: str) -> bytes:
    """Read a bounded regular file after checking every path component."""
    import os

    descriptors: list[int] = []
    try:
        required_flags = ("O_NOFOLLOW", "O_DIRECTORY")
        if (any(not hasattr(os, name) for name in required_flags)
                or os.open not in os.supports_dir_fd):
            raise PacketError("symlink-safe-open-unavailable")
        root_info = root.lstat()
        if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
            raise PacketError("repository-root-not-directory")
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory_fd = os.open(root, directory_flags)
        descriptors.append(directory_fd)
        components = Path(relative).parts
        for index, component in enumerate(components):
            is_file = index == len(components) - 1
            flags = os.O_RDONLY | os.O_NOFOLLOW
            if not is_file:
                flags |= os.O_DIRECTORY
            elif hasattr(os, "O_NONBLOCK"):
                # A FIFO can block before fstat identifies it as non-regular.
                flags |= os.O_NONBLOCK
            try:
                next_fd = os.open(component, flags, dir_fd=descriptors[-1])
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    try:
                        link_info = os.stat(component, dir_fd=descriptors[-1], follow_symlinks=False)
                    except OSError:
                        link_info = None
                    if link_info is not None and stat.S_ISLNK(link_info.st_mode):
                        raise PacketError("input-symlink-rejected") from None
                raise
            descriptors.append(next_fd)
        descriptor = descriptors[-1]
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise PacketError("input-not-regular-file")
        if info.st_nlink != 1:
            raise PacketError("input-hardlink-rejected")
        if info.st_size > MAX_FILE_BYTES:
            raise PacketError("input-size-limit")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
    except PacketError:
        raise
    except FileNotFoundError:
        raise PacketError("required-input-missing") from None
    except OSError:
        raise PacketError("input-unreadable-or-unsafe") from None
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass
    if len(raw) > MAX_FILE_BYTES:
        raise PacketError("input-size-limit")
    return raw


def read_auxiliary_file(root: str | Path, relative: str) -> bytes:
    """Read a bounded, single-link auxiliary input from the fixed allowlist."""
    if type(relative) is not str or relative not in AUXILIARY_FILES:
        raise PacketError("auxiliary-input-not-allowlisted")
    return _read_fixed_file(Path(root), relative)


def _validate_candidates(value: Any) -> list[dict[str, str]]:
    if type(value) is not dict or set(value) != {"format", "sourceKind", "basedOnCommit", "families"}:
        raise PacketError("candidate-manifest-shape-invalid")
    if value["format"] != FORMAT or value["sourceKind"] != "metadata-only":
        raise PacketError("candidate-manifest-format-invalid")
    if type(value["basedOnCommit"]) is not str or COMMIT.fullmatch(value["basedOnCommit"]) is None:
        raise PacketError("candidate-base-commit-invalid")
    families = value["families"]
    if type(families) is not list or len(families) > 100:
        raise PacketError("candidate-family-roster-invalid")
    seen: set[str] = set()
    public: list[dict[str, str]] = []
    for family in families:
        if type(family) is not dict or set(family) != FAMILY_KEYS:
            raise PacketError("candidate-family-shape-invalid")
        family_id = family["familyId"]
        if type(family_id) is not str or ID.fullmatch(family_id) is None or family_id in seen:
            raise PacketError("candidate-family-id-invalid-or-duplicate")
        seen.add(family_id)
        repository = family["repository"]
        if type(repository) is not str or repository not in REPOSITORIES:
            raise PacketError("candidate-repository-not-allowlisted")
        for field, maximum in (("workflow", 512), ("decisionContext", 1024), ("naturalTrigger", 1024)):
            text = family[field]
            if type(text) is not str or not text.strip() or len(text) > maximum:
                raise PacketError("candidate-description-invalid")
        for field in ("distinctnessReview", "permissionReview", "eligibilityReview"):
            if family[field] != "pending":
                raise PacketError("candidate-review-status-must-remain-pending")
        # Strings describing workflows/context remain bound by the manifest hash,
        # but are omitted from the report to keep it metadata-only and compact.
        public.append({"familyId": family_id, "repository": repository})
    return public


def check_packet(root: str | Path, expected_hash: str | None = None) -> dict:
    """Return a deterministic preparatory report for the fixed packet files.

    A successful report means only that the metadata packet is structurally
    complete and pinned. All scientific, source and authorization gates remain
    explicitly pending.
    """
    if expected_hash is not None and (type(expected_hash) is not str or HASH.fullmatch(expected_hash) is None):
        raise PacketError("expected-packet-hash-invalid")
    repo_root = Path(root)
    file_hashes: dict[str, str] = {}
    payloads: dict[str, bytes] = {}
    for relative in FILES:
        payload = _read_fixed_file(repo_root, relative)
        payloads[relative] = payload
        file_hashes[relative] = hashlib.sha256(payload).hexdigest()
    packet_material = {"format": "m35-review-packet-commit-v1", "fileSha256": file_hashes}
    packet_hash = hashlib.sha256(_canonical(packet_material)).hexdigest()
    if expected_hash is not None and packet_hash != expected_hash:
        raise PacketError("packet-commitment-drift")
    candidate_path = FILES[0]
    candidate_value = _parse_json(payloads[candidate_path])
    candidates = _validate_candidates(candidate_value)
    reasons = [
        "owner-permission-review-pending",
        "participant-and-data-rights-review-pending",
        "privacy-review-pending",
        "eligible-yield-unobserved",
        "family-distinctness-review-pending",
        "eligibility-review-pending",
        "source-roster-not-approved",
        "registration-not-approved",
        "protocol-and-rubric-human-review-pending",
    ]
    return {
        "format": "m35-review-packet-report-v1",
        "packetStructurallyComplete": True,
        "packetSha256": packet_hash,
        "basedOnCommit": candidate_value["basedOnCommit"],
        "inputSha256": file_hashes,
        "families": candidates,
        "reasons": reasons,
        "realPairsAdmitted": 0,
        "sourceCaptureAuthorization": False,
        "trainingAuthorization": False,
        "executionAuthorization": False,
        "humanApprovalVerified": False,
        "limitations": "Preparatory metadata commitment only; rights, roster, protocol approval, yield, and human decisions remain unverified and pending.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="repository root; inputs are fixed relative paths")
    parser.add_argument("--expected-packet-sha256")
    args = parser.parse_args(argv)
    try:
        report = check_packet(args.root, args.expected_packet_sha256)
    except PacketError as exc:
        parser.error(f"review packet invalid ({exc.code})")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
