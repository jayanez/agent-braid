# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T103: loader, validator, digest, sample selector and noise estimator.

Pure and offline. The only file read is the frozen rubric under the spec contracts
directory. It reads no corpus, no episode and no registry, and it returns no
input beyond the opaque join keys it was handed. Nothing here is a scientific
result: the rubric fixes how labels are named, scored, counted and sampled before
any fit, and the noise estimate is a rate with an interval, not a quality claim.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import stat

SCHEMA_VERSION = "agent-braid-s1-label-rubric/v0.1"
MAX_BYTES = 65536
RUBRIC_PATH = (Path(__file__).resolve().parents[1] / "specs" / "066-system-one-shadow"
               / "contracts" / "label-rubric-v0.1.json")
WILSON_Z = 1.959963984540054
_DIGEST = re.compile(r"[0-9a-f]{64}")

LABELS = ("conflict", "integration-failure", "no-conflict-observed", "textually-clean")
SOURCES = ("git-history-replay", "real-run")
DP1_ANSWERS = ("likely-conflicting", "likely-independent", "undetermined")
OUTCOME_KINDS = frozenset({"runtime-conflict", "merge-conflict", "merge-clean",
                           "verify-pass", "verify-fail"})
_TOP = {"adjudication", "dp1", "executionAuthorization", "labels", "missingLabelPolicy",
        "oracles", "outcomeToLabel", "schemaVersion", "sources"}
_MISSING_POLICY = {"countBy": ["class", "reason", "source"], "dropSilently": False,
                   "excludeFromFitAndEvaluation": True, "impute": False,
                   "reportUnlabelledShare": True,
                   "worstCaseBound": "all-unlabelled-as-each-label"}
_DP1_TRUTH = {"likely-conflicting": ["conflict"],
              "likely-independent": ["no-conflict-observed", "textually-clean"]}
_SAMPLE = {"fractionPercent": 20, "perSourceCap": 40, "strata": ["source", "label"]}
_ADJUDICATION = {"estimand": "owner-vs-observed-disagreement-rate", "interval": "wilson-95",
                 "packetFields": ["joinKey", "label", "outcomeKind", "source", "structuralPair"]}
_SAMPLE_TEXT = {"drawKey": "sha256 of manifest digest, source, label and joinKey, lowest ranks first",
                "manifestDigestSource": "T104 sealed corpus manifest"}
_MAPPING = {"runtime-conflict": "conflict", "merge-conflict": "conflict",
            "merge-clean": "textually-clean", "verify-pass": "no-conflict-observed",
            "verify-fail": "integration-failure"}
_ORACLES = {"git-history-replay": "git-merge-tree", "real-run": "observed-run-result"}
LIMITATION = ("One-person owned population; owner adjudication replaces two blind reviewers "
              "and the interval is wide when the sample is small.")


class RubricError(ValueError):
    """Closed failure: the rubric or an input is malformed; nothing is guessed."""


def _require(ok, reason="invalid-rubric"):
    if not ok:
        raise RubricError(reason)


def _same(left, right):
    """Equality that does not let 0 pass for False or 20.0 for 20."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_same(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _no_duplicates(pairs):
    keys = [key for key, _ in pairs]
    _require(len(keys) == len(set(keys)), "duplicate-member")
    return dict(pairs)


def _no_constant(_name):
    raise RubricError("non-finite-number")


def load_rubric(path=None):
    """Read the bounded regular file, parse strictly and validate. Symlinks are refused."""
    target = Path(path) if path is not None else RUBRIC_PATH
    try:
        info = target.lstat()
        _require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_BYTES, "unreadable-rubric")
        raw = target.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise RubricError("unreadable-rubric") from error
    _require(len(raw) <= MAX_BYTES, "unreadable-rubric")
    try:
        value = json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
    except (json.JSONDecodeError, RecursionError) as error:
        raise RubricError("invalid-json") from error
    return validate_rubric(value)


def validate_rubric(value):
    """Return `value` when it is exactly the frozen v0.1 structure, else raise."""
    _require(type(value) is dict and set(value) == _TOP)
    _require(value["schemaVersion"] == SCHEMA_VERSION)
    _require(value["executionAuthorization"] is False)
    _require(value["labels"] == list(LABELS) and value["sources"] == list(SOURCES))
    mapping = value["outcomeToLabel"]
    _require(type(mapping) is dict and set(mapping) == OUTCOME_KINDS)
    _require(_same(mapping, _MAPPING) and _same(value["oracles"], _ORACLES))
    _require(_same(value["missingLabelPolicy"], _MISSING_POLICY))
    dp1 = value["dp1"]
    _require(type(dp1) is dict and set(dp1) == {"answers", "poolLabelsByDefault", "truth",
                                                "undetermined", "unscoredLabels"})
    _require(_same(dp1["answers"], list(DP1_ANSWERS)) and _same(dp1["truth"], _DP1_TRUTH))
    _require(dp1["poolLabelsByDefault"] is False and dp1["undetermined"] == "counted-never-scored")
    # dp1_truth scores one label at a time; callers report right/wrong per label.
    scored = {label for labels in _DP1_TRUTH.values() for label in labels}
    _require(_same(dp1["unscoredLabels"], sorted(set(LABELS) - scored)))
    adjudication = value["adjudication"]
    _require(type(adjudication) is dict and set(adjudication) == set(_ADJUDICATION) | {
        "packetLimitation", "populationLimitation", "sample"})
    _require(all(_same(adjudication[key], expected) for key, expected in _ADJUDICATION.items()))
    _require(all(type(adjudication[key]) is str and adjudication[key]
                 for key in ("packetLimitation", "populationLimitation")))
    sample = adjudication["sample"]
    _require(type(sample) is dict and set(sample) == set(_SAMPLE) | set(_SAMPLE_TEXT))
    _require(all(_same(sample[key], expected) for key, expected in {**_SAMPLE, **_SAMPLE_TEXT}.items()))
    return value


def rubric_digest(value=None):
    """SHA-256 of the canonical JSON; the `oracleContractDigest` input of a later descriptor."""
    body = load_rubric() if value is None else value
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                           allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def label_for(outcome_kind):
    _require(outcome_kind in OUTCOME_KINDS, "unknown-outcome-kind")
    return load_rubric()["outcomeToLabel"][outcome_kind]


def dp1_truth(answer, label):
    """Score a DP-1 answer: right, wrong, unscored (label outside truth) or counted."""
    _require(answer in DP1_ANSWERS and label in LABELS, "unknown-vocabulary")
    if answer == "undetermined":
        return "counted"
    if label in load_rubric()["dp1"]["unscoredLabels"]:
        return "unscored"
    return "right" if label in _DP1_TRUTH[answer] else "wrong"


def sample_size(labelled):
    """`min(40, ceil(20 percent of labelled))` for one source."""
    _require(type(labelled) is int and labelled >= 0, "invalid-count")
    return min(_SAMPLE["perSourceCap"], -(-labelled * _SAMPLE["fractionPercent"] // 100))


def _quotas(counts, size):
    """Proportional allocation, largest remainder first, ties by label order."""
    total = sum(counts.values())
    quotas = {label: size * count // total for label, count in counts.items()}
    spare = size - sum(quotas.values())
    order = sorted(counts, key=lambda label: (-(size * counts[label] % total), LABELS.index(label)))
    for label in order[:spare]:
        quotas[label] += 1
    return quotas


def select_adjudication_sample(entries, manifest_digest):
    """Sorted join keys of a stratified draw keyed by the sealed manifest digest.

    Entries are `{joinKey, source, label}` only. Within each (source, label) stratum
    the lowest SHA-256 ranks of manifest, source, label and join key are taken, so
    the draw is fixed once the manifest is sealed and needs no PRNG state.
    """
    _require(type(manifest_digest) is str and _DIGEST.fullmatch(manifest_digest),
             "invalid-manifest-digest")
    _require(type(entries) is list)
    seen, strata = set(), {}
    for entry in entries:
        _require(type(entry) is dict and set(entry) == {"joinKey", "source", "label"})
        key = entry["joinKey"]
        _require(type(key) is str and 0 < len(key) <= 128 and key.isascii() and key not in seen,
                 "invalid-join-key")
        _require(entry["source"] in SOURCES and entry["label"] in LABELS, "unknown-vocabulary")
        seen.add(key)
        strata.setdefault(entry["source"], {}).setdefault(entry["label"], []).append(key)
    chosen = []
    for source, labels in strata.items():
        counts = {label: len(keys) for label, keys in labels.items()}
        quotas = _quotas(counts, sample_size(sum(counts.values())))
        for label, keys in labels.items():
            ranked = sorted(keys, key=lambda key: hashlib.sha256(
                f"{manifest_digest}\n{source}\n{label}\n{key}".encode("utf-8")).hexdigest())
            chosen.extend(ranked[:quotas[label]])
    return sorted(chosen)


def estimate_noise(disagreements, adjudicated):
    """Owner-vs-observed disagreement rate with a Wilson 95 percent interval."""
    for number in (disagreements, adjudicated):
        _require(type(number) is int and number >= 0, "invalid-count")
    _require(disagreements <= adjudicated, "invalid-count")
    result = {"n": adjudicated, "k": disagreements, "rate": None, "lower": None, "upper": None,
              "interval": "wilson-95", "limitation": LIMITATION}
    if adjudicated:
        rate = disagreements / adjudicated
        z2 = WILSON_Z ** 2
        center = (rate + z2 / (2 * adjudicated)) / (1 + z2 / adjudicated)
        margin = (WILSON_Z * math.sqrt(rate * (1 - rate) / adjudicated + z2 / (4 * adjudicated ** 2))
                  / (1 + z2 / adjudicated))
        result.update(rate=rate, lower=max(0.0, center - margin), upper=min(1.0, center + margin))
    return result
