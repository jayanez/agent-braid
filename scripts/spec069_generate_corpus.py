# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T004 / T006: deterministic generator of the analyze-work request corpus.

Writes ``tests/fixtures/analysis-requests/{aim,git}.json`` and, for the ``units``
kind, one file per case under ``units/valid/`` and ``units/invalid/`` (by the
expected service verdict). Each case records its request, the schema and service
verdicts it is *expected* to produce (derived from how the case was constructed,
never from running the validators), the JSON Pointer of the failing location, the
layer and, where the two layers differ on purpose, the documented difference.

``units/golden/`` holds byte goldens of the AIM request that ``agent_braid.units``
constructs for a few named requests at a fixed workspace scope. They are snapshots
of the construction, reviewed as diffs; the tests recompute their digests from the
contract's construction table independently.

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
UNITS_SCHEMA_PATH = ROOT / "schemas/0.1.0-alpha/units-request.schema.json"
UNITS_SCHEMA = json.loads(UNITS_SCHEMA_PATH.read_text())
UNITS_OUTPUT = OUTPUT / "units"
# Fixed workspace scope of the goldens: the scope of a source root at /workspace.
GOLDEN_SCOPE = "c52ddf65534b7b46035084358ab7902b"

# Limits declared in the contract: characters on which Python and ECMAScript
# disagree, and a Python-jsonschema quirk. Cases keep them visible but tagged.
ES_DIFFERS = ("U+001C", "U+001D", "U+001E", "U+001F", "U+0085", "U+FEFF")


AIM_NONBLANK = ("/instanceId", "/attemptId", "/definition/id", "/effects/coverage/domain", "/effects/coverage/method")
GIT_NONBLANK = ("/repository", "/baseRevision", "/operations/0/instanceId", "/operations/0/attemptId",
                "/operations/0/source/revision")
GIT_RESOLVED = ("/repository", "/baseRevision", "/operations/0/source/revision")


LAYER_OF = {"RC-batch": "batch", "RC-git-resolution": "semantic"}


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
        layer = LAYER_OF.get(extra.get("difference"), "structural")
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
    def env(label, mutate, pointer):
        e = copy.deepcopy(envelope); mutate(e)
        case(cases, "aim", "envelope", label, e, "refuses", "refuses", pointer, "structural")
    env("envelope with an extra field", lambda e: e.__setitem__("extra", 1), "")
    env("envelope without source", lambda e: e.pop("source"), "")
    env("envelope without operations", lambda e: e.pop("operations"), "")
    env("envelope without version", lambda e: e.pop("analysisInputVersion"), "")
    env("envelope source with an extra field", lambda e: e["source"].__setitem__("x", 1), "/source")
    env("envelope source kind blank", lambda e: e["source"].__setitem__("kind", "  "), "/source/kind")
    env("envelope source description empty", lambda e: e["source"].__setitem__("description", ""), "/source/description")
    env("envelope with empty operations", lambda e: e.__setitem__("operations", []), "/operations")
    env("envelope with a non-object operation", lambda e: e.__setitem__("operations", ["x"]), "/operations/0")
    env("envelope with another analysisInputVersion", lambda e: e.__setitem__("analysisInputVersion", "9.9.9"), "")
    env("envelope operations is an object", lambda e: e.__setitem__("operations", {}), "/operations")
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
        layer = LAYER_OF.get(extra.get("difference"), "structural")
        case(cases, "git", "request", f"{label} at {ptr or '/'}", mutant, schema, service, ptr, layer, keyword=keyword, **extra)
    single = copy.deepcopy(base); single["operations"] = single["operations"][:1]; single["operations"][0]["dependencies"] = []
    case(cases, "git", "request", "a single operation (at least two are required)", single, "refuses", "refuses", "/operations", "structural", keyword="minItems")
    outside = copy.deepcopy(base); outside["repository"] = "<outside-root>"
    case(cases, "git", "request", "repository outside the configured source root", outside, "accepts", "refuses", "/repository", "semantic", difference="RC-git-semantic")
    unresolved = copy.deepcopy(base); unresolved["baseRevision"] = "no-such-revision"
    case(cases, "git", "request", "baseRevision that does not resolve", unresolved, "accepts", "refuses", "/baseRevision", "semantic", difference="RC-git-semantic")
    return cases


# --- units (SPEC-069 T006 / REQ-006) ---------------------------------------------------------
def units_base() -> dict:
    """Two valid units; unit 0 carries every optional property so each one is mutated."""
    return {
        "unitsRequestVersion": "0.1.0-alpha",
        "units": [
            {"id": "edit-readme", "dependencies": ["write-guide"],
             "effects": [{"kind": "write", "resource": "README.md"}], "coverage": "partial"},
            {"id": "write-guide", "effects": [{"kind": "write", "resource": "docs/guide.md"}]},
        ],
    }


def units_request(*units: dict) -> dict:
    return {"unitsRequestVersion": "0.1.0-alpha", "units": list(units)}


def unit(identifier: str, *effects: tuple[str, str], dependencies=None, coverage=None) -> dict:
    value = {"id": identifier, "effects": [{"kind": kind, "resource": resource} for kind, resource in effects]}
    if dependencies is not None:
        value["dependencies"] = dependencies
    if coverage is not None:
        value["coverage"] = coverage
    return value


def units_expectation(ptr: str, label: str) -> tuple[str, str, dict]:
    """Expected (schema, service, extra) of a mutation of the units base request."""
    es_char = next((tag for tag in ES_DIFFERS if tag in label), None)
    if not label.startswith("blank string") or es_char is None:
        return "refuses", "refuses", {}
    if ptr.endswith("/resource") and es_char in ("U+001C", "U+001D", "U+001E", "U+001F"):
        return "refuses", "refuses", {}  # control characters: refused by every validator
    extra = {"limit": "blank-whitespace-differs-in-ecmascript"}
    if es_char != "U+FEFF":
        return "refuses", "refuses", extra
    if ptr.endswith("/dependencies/0"):
        return "accepts", "refuses", dict(extra, difference="RC-batch")  # a valid string naming no unit
    return "accepts", "accepts", extra


def units_cases() -> list[dict]:
    cases: list[dict] = []
    base = units_base()

    def add(label, request, schema, service, pointer, layer, **extra):
        case(cases, "units", "request", label, request, schema, service, pointer, layer, **extra)

    # valid cases
    add("two units, one depends on the other", base, "accepts", "accepts", "", "valid")
    add("single unit", units_request(unit("only", ("write", "README.md"))), "accepts", "accepts", "", "valid")
    add("two units write README.md (T010 F1 shape)",
        units_request(unit("edit-readme", ("write", "README.md")), unit("edit-readme-intro", ("write", "README.md"))),
        "accepts", "accepts", "", "valid")
    for kind in ("read", "write", "call", "transform", "emit", "delete", "deploy"):
        add(f"effect kind {kind}", units_request(unit("u", (kind, "repo-file.txt"))), "accepts", "accepts", "", "valid")
    for claim in ("complete", "partial", "unknown"):
        add(f"coverage claim {claim} (recorded as partial)",
            units_request(unit("u", ("write", "README.md"), coverage=claim)), "accepts", "accepts", "", "valid")
    for label, resource in (("dot-slash prefix", "./README.md"), ("trailing slash", "docs/"),
                            ("empty segment", "docs//guide.md"), ("dot segment", "docs/./guide.md"),
                            ("three dots is a name", "..."), ("hidden file", ".github/CODEOWNERS"),
                            ("colon after the first segment", "docs/a:b.md"), ("dots inside a name", "a..b/c..d"),
                            ("non-ASCII composed", "docs/caf\u00e9.md"), ("non-ASCII decomposed", "docs/cafe\u0301.md")):
        add(f"resource {label}", units_request(unit("u", ("write", resource))), "accepts", "accepts", "", "valid")
    add("unit without dependencies or coverage", units_request(unit("u", ("read", "a"), ("write", "b"))),
        "accepts", "accepts", "", "valid")
    add("same resource read and written in one unit", units_request(unit("u", ("read", "a"), ("write", "./a"))),
        "accepts", "accepts", "", "valid")
    add("unit id of exactly 256 bytes", units_request(unit("i" * 256, ("write", "a"))), "accepts", "accepts", "", "valid")
    add("exactly 32 units", units_request(*[unit(f"u{i}", ("write", f"f{i}")) for i in range(32)]),
        "accepts", "accepts", "", "valid")

    # structural mutations of the base request (schema keywords walked by the inventory)
    for path, keyword, label, fn in inv.mutations(UNITS_SCHEMA, base):
        mutant = inv.roundtrip(fn(copy.deepcopy(base)))
        ptr = inv.pointer(path)
        schema, service, extra = units_expectation(ptr, label)
        layer = LAYER_OF.get(extra.get("difference"), "structural")
        case(cases, "units", "request", f"{label} at {ptr or '/'}", mutant, schema, service, ptr, layer,
             keyword=keyword, **extra)

    # lexical refusals stated by the resource pattern (schema and runtime agree)
    where = "/units/0/effects/0/resource"
    for label, resource in (("a .. segment", "../README.md"), ("an inner .. segment", "docs/../README.md"),
                            ("a trailing .. segment", "docs/.."), ("an absolute path", "/etc/hosts"),
                            ("a scheme", "repo://w/README.md"), ("a URL", "https://example.org/x"),
                            ("a drive letter", "C:/Users/x"), ("a backslash", "docs\\guide.md"),
                            ("a Windows path", "C:\\Users\\x"), ("a tab", "docs/a\tb"),
                            ("a newline", "README.md\n"), ("DEL", "a\u007fb"), ("a lone dot", "."),
                            ("a dot slash", "./"), ("only slashes and dots", ".//./"),
                            ("a scheme-like first segment", "notes:2026.md")):
        add(f"resource with {label}", units_request(unit("u", ("write", resource))), "refuses", "refuses",
            where, "structural", keyword="pattern")
    add("effect kind unknown (not an Article 5 family)", units_request(unit("u", ("unknown", "a"))),
        "refuses", "refuses", "/units/0/effects/0/kind", "structural", keyword="enum")
    add("effect kind outside the vocabulary", units_request(unit("u", ("modify", "a"))),
        "refuses", "refuses", "/units/0/effects/0/kind", "structural", keyword="enum")
    add("request is an array", [unit("u", ("write", "a"))], "refuses", "refuses", "", "structural", keyword="type")

    # bounds: maxItems and maxLength in the schema, the adapter bounds at runtime (A7)
    add("33 units", units_request(*[unit(f"u{i}", ("write", f"f{i}")) for i in range(33)]),
        "refuses", "refuses", "/units", "structural", keyword="maxItems")
    add("unit id of 257 bytes", units_request(unit("i" * 257, ("write", "a"))), "refuses", "refuses",
        "/units/0/id", "structural", keyword="maxLength")
    add("unit id of 129 two-byte characters (258 bytes)", units_request(unit("\u00e9" * 129, ("write", "a"))),
        "accepts", "refuses", "/units/0/id", "adapter", difference="RC-adapter")

    # batch-level refusals: valid units, invalid declaration; the schema cannot express them
    def batch(label, request, pointer):
        add(label, request, "accepts", "refuses", pointer, "batch", difference="RC-batch")
    batch("duplicate unit id", units_request(unit("u", ("write", "a")), unit("u", ("write", "b"))), "/units/1/id")
    batch("unknown dependency", units_request(unit("u", ("write", "a"), dependencies=["ghost"])), "/units/0/dependencies/0")
    batch("self dependency", units_request(unit("u", ("write", "a"), dependencies=["u"])), "/units/0/dependencies/0")
    batch("cyclic dependencies", units_request(unit("x", ("write", "a"), dependencies=["y"]),
                                               unit("y", ("write", "b"), dependencies=["x"])), "/units")
    batch("resources differ only by letter case", units_request(unit("u", ("write", "README.md")),
                                                                unit("v", ("write", "readme.md"))),
          "/units/1/effects/0/resource")
    batch("case-only difference inside one unit", units_request(unit("u", ("read", "Docs/a"), ("write", "docs/a"))),
          "/units/0/effects/1/resource")
    return cases


GOLDEN_REQUESTS = {
    "t010-readme-conflict": units_request(unit("edit-readme", ("write", "README.md")),
                                          unit("edit-readme-intro", ("write", "README.md"))),
    "dot-slash-alias": units_request(unit("edit-readme", ("write", "README.md")),
                                     unit("edit-readme-intro", ("write", "./README.md"))),
    "disjoint-claimed-complete": units_request(unit("edit-readme", ("write", "README.md"), coverage="complete"),
                                               unit("edit-guide", ("write", "docs/guide.md"), coverage="complete")),
    "ordered": units_request(unit("write-guide", ("write", "docs/guide.md")),
                             unit("link-guide", ("read", "docs/guide.md"), ("write", "README.md"),
                                  dependencies=["write-guide"])),
}


def golden_bytes(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def units_files() -> dict[str, str]:
    """Relative path under ``units/`` -> exact file text."""
    from agent_braid import units as construction
    files = {}
    for entry in units_cases():
        folder = "valid" if entry["expect"]["service"] == "accepts" else "invalid"
        files[f"{folder}/{entry['id']}.json"] = json.dumps(entry, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
    for name, request in GOLDEN_REQUESTS.items():
        files[f"golden/{name}.request.json"] = golden_bytes(request)
        constructed = construction.construct(request, GOLDEN_SCOPE)["constructedRequest"]
        files[f"golden/{name}.constructed.json"] = golden_bytes(constructed)
    return files


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
    files = units_files()
    present = {p.relative_to(UNITS_OUTPUT).as_posix() for p in UNITS_OUTPUT.rglob("*") if p.is_file()} \
        if UNITS_OUTPUT.exists() else set()
    if args.check:
        stale = sorted(name for name, text in files.items()
                       if not (UNITS_OUTPUT / name).exists() or (UNITS_OUTPUT / name).read_text() != text)
        stale += sorted(present - set(files))
        if stale:
            print(f"units/ is stale ({len(stale)} files); rerun without --check", file=sys.stderr)
            status = 1
        else:
            print(f"units/ is current ({len(files)} files)")
        return status
    for name in present - set(files):
        (UNITS_OUTPUT / name).unlink()
    for name, text in files.items():
        (UNITS_OUTPUT / name).parent.mkdir(parents=True, exist_ok=True)
        (UNITS_OUTPUT / name).write_text(text)
    print(f"units/: {len(files)} files")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
