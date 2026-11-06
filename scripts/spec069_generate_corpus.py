# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T004: deterministic generator of the analyze-work request corpus.

Writes ``tests/fixtures/analysis-requests/{aim,git}.json``. Each case records its
request, the schema and service verdicts it is *expected* to produce (derived from
how the case was constructed, never from running the validators), the JSON
Pointer of the failing location, the layer and, where the two layers differ on
purpose, the documented difference.

    python -m scripts.spec069_generate_corpus            # write
    python -m scripts.spec069_generate_corpus --check    # fail when committed files differ
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from scripts import spec069_divergence_inventory as inv

ROOT = inv.ROOT
OUTPUT = ROOT / "tests/fixtures/analysis-requests"
AIM_SCHEMA = json.loads(inv.AIM_SCHEMA.read_text())
GIT_SCHEMA = json.loads(inv.GIT_SCHEMA.read_text())

# Limits declared in the contract: characters on which Python and ECMAScript
# disagree, and a Python-jsonschema quirk. Cases keep them visible but tagged.
ES_DIFFERS = ("U+001C", "U+001D", "U+001E", "U+001F", "U+0085", "U+FEFF")


AIM_NONBLANK = ("/instanceId", "/attemptId", "/definition/id", "/effects/coverage/domain", "/effects/coverage/method")
GIT_NONBLANK = ("/repository", "/baseRevision", "/operations/0/instanceId", "/operations/0/attemptId",
                "/operations/0/source/revision")
GIT_RESOLVED = ("/repository", "/baseRevision", "/operations/0/source/revision")


def expectation(kind: str, ptr: str, keyword: str, label: str) -> tuple[str, str, dict]:
    """Expected (schema, service, extra) of a mutation, from the contract's field rules."""
    schema, service, extra = "refuses", "refuses", {}
    es_char = next((tag for tag in ES_DIFFERS if tag in label), None)
    if label.startswith("blank string"):
        nonblank = (ptr in AIM_NONBLANK or ptr.endswith("/resource")) if kind == "aim" else ptr in GIT_NONBLANK
        if ptr.endswith("/dependencies/0"):
            schema, service, extra = "accepts", "refuses", {"difference": "RC-batch"}
        elif not nonblank:
            schema, service = "accepts", "accepts"  # blank is a valid value for this field
        elif es_char == "U+FEFF":
            # not blank for Python strip(); blank for ECMAScript \s
            schema, service = "accepts", "accepts"
            if kind == "git" and ptr in GIT_RESOLVED:
                service, extra = "refuses", {"difference": "RC-git-resolution"}
        if es_char and nonblank:
            extra["limit"] = "blank-whitespace-differs-in-ecmascript"
    elif "trailing newline" in label:
        schema, service = "accepts", "refuses"
        extra["limit"] = "python-jsonschema-dollar-accepts-trailing-newline"
    elif "float 1.0" in label:
        schema, service = "accepts", "refuses" if ptr.startswith("/readVersions/") else "accepts"
        if ptr.startswith("/readVersions/"):
            extra["limit"] = "json-1.0-is-integer-for-schema-float-for-runtime"
    elif keyword == "uniqueItems" and ptr.endswith("/uncertainPaths"):
        schema, service, extra = "refuses", "accepts", {"difference": "RC-git-unique"}
    if kind == "aim" and ptr.startswith("/evidence/0") and schema == "refuses":
        service, extra = "accepts", {"difference": "RC-evidence"}
    return schema, service, extra


def case(cases, kind, form, label, request, schema, service, pointer, layer, **extra):
    entry = {
        "id": f"{kind}-{len(cases) + 1:04d}",
        "form": form,
        "label": label,
        "layer": layer,
        "pointer": pointer,
        "expect": {"schema": schema, "service": service},
        "request": request,
    }
    entry.update({k: v for k, v in extra.items() if v})
    cases.append(entry)


def aim_cases() -> list[dict]:
    cases: list[dict] = []
    a, b = inv.aim_pair()
    solo = copy.deepcopy(b)

    # valid cases
    case(cases, "aim", "array", "two records, one depends on the other", [a, b], "accepts", "accepts", "", "valid")
    case(cases, "aim", "record", "single record", solo, "accepts", "accepts", "", "valid")
    envelope = {"analysisInputVersion": "0.1.0-alpha", "source": {"kind": "probe", "description": "probe"}, "operations": [a, b]}
    case(cases, "aim", "envelope", "envelope with two records", envelope, "accepts", "accepts", "", "valid")
    for kind in ("read", "write", "call", "transform", "emit", "delete", "deploy", "unknown"):
        record = copy.deepcopy(solo)
        record["effects"]["declared"] = [{"kind": kind, "resource": "repo://w/x"}]
        case(cases, "aim", "record", f"effect kind {kind}", record, "accepts", "accepts", "", "valid")
    for status in ("complete", "partial", "unknown"):
        record = copy.deepcopy(solo)
        record["effects"]["coverage"]["status"] = status
        case(cases, "aim", "record", f"coverage status {status}", record, "accepts", "accepts", "", "valid")
    for klass in (0, 5):
        record = copy.deepcopy(solo)
        record["evidence"][0]["assuranceClass"] = klass
        case(cases, "aim", "record", f"assurance class boundary {klass}", record, "accepts", "accepts", "", "valid")
    record = copy.deepcopy(solo); record["readVersions"] = {}
    case(cases, "aim", "record", "empty readVersions", record, "accepts", "accepts", "", "valid")
    record = copy.deepcopy(solo); record["effects"]["declared"] = []
    case(cases, "aim", "record", "no declared effects", record, "accepts", "accepts", "", "valid")
    record = copy.deepcopy(solo); record["effects"]["declared"][0]["resource"] = "repo://w/dir/ünï.txt"
    case(cases, "aim", "record", "non-ASCII resource", record, "accepts", "accepts", "", "valid")
    record = copy.deepcopy(solo); record["evidence"] = [record["evidence"][0], copy.deepcopy(record["evidence"][0])]
    case(cases, "aim", "record", "two evidence items", record, "accepts", "accepts", "", "valid")

    # structural mutations of record 0, sent in array form with a valid partner
    for path, keyword, label, fn in inv.mutations(AIM_SCHEMA, a):
        mutant = inv.roundtrip(fn(copy.deepcopy(a)))
        ptr = inv.pointer(path)
        schema, service, extra = expectation("aim", ptr, keyword, label)
        request = [mutant, copy.deepcopy(b)]
        layer = "structural" if (schema == "refuses" or service == "refuses" and "difference" not in extra) else "structural"
        case(cases, "aim", "array", f"{label} at {ptr or '/'}", request, schema, service, "/0" + ptr, layer, keyword=keyword, **extra)

    # batch-level cases (valid records, invalid batch): the schema cannot express them
    def batch(label, request):
        case(cases, "aim", "array", label, request, "accepts", "refuses", "", "batch", difference="RC-batch")
    dup = copy.deepcopy(b); dup["attemptId"] = "other-1"
    batch("duplicate instanceId", [b, dup])
    dup = copy.deepcopy(b); dup["instanceId"] = "probe-c"
    batch("duplicate attemptId", [b, dup])
    ghost = copy.deepcopy(b); ghost["dependencies"] = ["ghost"]
    batch("unknown dependency", [ghost, copy.deepcopy(a)])
    selfdep = copy.deepcopy(b); selfdep["dependencies"] = ["probe-b"]
    batch("self dependency", [selfdep])
    x = inv.base_record("cx", "cx-1", ["cy"], "repo://w/x"); y = inv.base_record("cy", "cy-1", ["cx"], "repo://w/y")
    batch("cyclic dependencies", [x, y])

    # envelope structure (schema and service agree)
    def env(label, mutate):
        e = copy.deepcopy(envelope); mutate(e)
        case(cases, "aim", "envelope", label, e, "refuses", "refuses", "", "structural")
    env("envelope with an extra field", lambda e: e.__setitem__("extra", 1))
    env("envelope without source", lambda e: e.pop("source"))
    env("envelope without operations", lambda e: e.pop("operations"))
    env("envelope without version", lambda e: e.pop("analysisInputVersion"))
    env("envelope source with an extra field", lambda e: e["source"].__setitem__("x", 1))
    env("envelope source kind blank", lambda e: e["source"].__setitem__("kind", "  "))
    env("envelope source description empty", lambda e: e["source"].__setitem__("description", ""))
    env("envelope with empty operations", lambda e: e.__setitem__("operations", []))
    env("envelope with a non-object operation", lambda e: e.__setitem__("operations", ["x"]))
    env("envelope with another analysisInputVersion", lambda e: e.__setitem__("analysisInputVersion", "9.9.9"))
    env("envelope operations is an object", lambda e: e.__setitem__("operations", {}))
    case(cases, "aim", "array", "empty array", [], "refuses", "refuses", "", "structural")
    case(cases, "aim", "record", "empty object", {}, "refuses", "refuses", "", "structural")
    case(cases, "aim", "record", "string instead of a request", "x", "refuses", "refuses", "", "structural")

    # adapter bounds: not expressible in the schema
    many = [inv.base_record(f"m{i}", f"m{i}-1", [], f"repo://w/{i}") for i in range(33)]
    case(cases, "aim", "array", "33 operations in an array", many, "accepts", "refuses", "", "adapter", difference="RC-adapter")
    case(cases, "aim", "envelope", "33 operations in an envelope", dict(envelope, operations=many), "accepts", "refuses", "", "adapter", difference="RC-adapter")
    long_id = copy.deepcopy(b); long_id["instanceId"] = "i" * 257
    partner = copy.deepcopy(a); partner["dependencies"] = []
    case(cases, "aim", "array", "instanceId of 257 bytes in an array", [long_id, partner], "accepts", "refuses", "", "adapter", difference="RC-adapter")
    case(cases, "aim", "envelope", "instanceId of 257 bytes in an envelope", dict(envelope, operations=[long_id, partner]), "accepts", "refuses", "", "adapter", difference="RC-adapter")
    case(cases, "aim", "record", "instanceId of 257 bytes in a single record", long_id, "accepts", "accepts", "", "adapter", difference="RC-adapter-bypass")
    two = copy.deepcopy(b); two["instanceId"] = "é" * 129
    case(cases, "aim", "array", "instanceId of 129 two-byte characters in an array", [two, partner], "accepts", "refuses", "", "adapter", difference="RC-adapter")
    boundary = copy.deepcopy(b); boundary["instanceId"] = "i" * 256
    case(cases, "aim", "array", "instanceId of exactly 256 bytes", [boundary, partner], "accepts", "accepts", "", "valid")
    case(cases, "aim", "array", "exactly 32 operations", many[:32], "accepts", "accepts", "", "valid")
    return cases


def git_cases() -> list[dict]:
    cases: list[dict] = []
    base = inv.git_base()
    case(cases, "git", "request", "two commit operations", base, "accepts", "accepts", "", "valid")
    worktree = copy.deepcopy(base)
    worktree["operations"][1]["source"] = {"kind": "worktree", "path": inv.REPO_PLACEHOLDER}
    case(cases, "git", "request", "worktree source at the repository root", worktree, "accepts", "accepts", "", "valid", note="worktree allowlist is a configuration check; the test harness allows the source root")
    for path, keyword, label, fn in inv.mutations(GIT_SCHEMA, base):
        mutant = inv.roundtrip(fn(copy.deepcopy(base)))
        ptr = inv.pointer(path)
        schema, service, extra = expectation("git", ptr, keyword, label)
        case(cases, "git", "request", f"{label} at {ptr or '/'}", mutant, schema, service, ptr, "structural", keyword=keyword, **extra)
    single = copy.deepcopy(base); single["operations"] = single["operations"][:1]; single["operations"][0]["dependencies"] = []
    case(cases, "git", "request", "a single operation (at least two are required)", single, "refuses", "refuses", "/operations", "structural", keyword="minItems")
    outside = copy.deepcopy(base); outside["repository"] = "<outside-root>"
    case(cases, "git", "request", "repository outside the configured source root", outside, "accepts", "refuses", "/repository", "semantic", difference="RC-git-semantic")
    unresolved = copy.deepcopy(base); unresolved["baseRevision"] = "no-such-revision"
    case(cases, "git", "request", "baseRevision that does not resolve", unresolved, "accepts", "refuses", "/baseRevision", "semantic", difference="RC-git-semantic")
    return cases


def render(cases: list[dict], kind: str) -> str:
    """One case per line, keys sorted: compact and reviewable as a diff."""
    head = {"corpusVersion": "1", "specification": "SPEC-069 T004 / REQ-004", "kind": kind,
            "note": "Generated by scripts/spec069_generate_corpus.py; expected verdicts come from construction, not from running the validators."}
    lines = [json.dumps(case, sort_keys=True, ensure_ascii=True, separators=(",", ":")) for case in cases]
    return json.dumps(head, sort_keys=True, ensure_ascii=True)[:-1] + ',\n"cases":[\n' + ",\n".join(lines) + "\n]}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    status = 0
    for kind, cases in (("aim", aim_cases()), ("git", git_cases())):
        path = OUTPUT / f"{kind}.json"
        text = render(cases, kind)
        if args.check:
            if not path.exists() or path.read_text() != text:
                print(f"{path.name} is stale; rerun without --check", file=sys.stderr)
                status = 1
            else:
                print(f"{path.name} is current ({len(cases)} cases)")
            continue
        OUTPUT.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"{path.name}: {len(cases)} cases")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
