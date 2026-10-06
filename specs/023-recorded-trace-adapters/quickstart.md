# Acceptance contracts and implementation quickstart

This is a planning artifact. The importer, proposed `analyze-trace` command,
provider spikes and feature test suite below do not exist yet. Each SC section
is the acceptance contract referenced by draft assurance; it is not passing
test evidence.

## Planning checks available now

```sh
SPECIFY_FEATURE_DIRECTORY="$PWD/specs/023-recorded-trace-adapters" python3 .specify/scripts/python/check_prerequisites.py --json --require-spec --require-tasks --include-tasks
python3 scripts/validate_spec_kit.py
```

Expected: feature artifacts exist and the repository's structural checker passes
once the complete planning candidate is assembled. This does not certify mapping
correctness, scientific validity or human review.

## SC-001 — Versioned metadata mapping

Create valid synthetic identity/dependency/version/effect records and malformed,
missing, duplicate, cyclic and stale-version counterparts. Expected: a bijective
source-to-AIM identity table for admitted records; all required-field failures
reject before a report. Save source, projection and provenance hashes and raw
exit/diagnostic results.

## SC-002 — Unknown and attempts

Omit optional coverage/version semantics, introduce unsupported lifecycle data,
and supply two attempts for one instance. Expected: explicit unknown/loss for
optional semantics, no false independence from missing footprints, and rejection
of the generic multi-attempt case. Save supported/unsupported field tables and
classification comparisons with fixed direct-AIM controls.

## SC-003 — Zero dispatch

Inject execution/grant/plugin/network/model fields and observe the process/network
interfaces with spies. Expected: forbidden fields rejected and zero process,
network or model calls across positive and negative cases. No imported status
or annotation grants execution. Save spy counts and diagnostics.

## SC-004 — Privacy and parser rejection

Use synthetic prompt/credential/person-content sentinels, non-admitted real
source labels, duplicate JSON members, bound breaches, symlink destinations and
output collisions. Expected: rejection without sentinel leakage or persisted
partial outputs. Save redacted diagnostics, rejection reasons and filesystem
before/after assertions; do not persist real sensitive samples.

## SC-005 — Baseline parity and determinism

Run direct AIM and generic importer paths on the same mapped fixture twice.
Expected: identical classifications/constraints and deterministic report and
provenance bytes, existing schemas still validate, source and output hashes
match, and reports remain non-authorizing. Save each artifact and comparison.

## SC-006 — Lifecycle spike packet

First pin primary source versions. Run the predeclared OpenAI approval/reject/
pause/resume and MCP deferred/status/state fixtures without SDK/provider calls.
Expected: field retention/loss, attempt ownership, unknown and false-safe counts
with denominators, unsupported shapes, and positive/negative/inconclusive outcome
for each spike. Negative results may complete this contract; they cannot promote
provider adoption. Save source pins, fixed cases, outputs and limits.

## SC-007 — Ecosystem screening

Create one screening record each for A2A, NeMo Agent Toolkit and OpenTelemetry.
Expected: version/source, conformance availability, license/dependency/privacy
assessment, AIM losses and explicit next disposition. A missing version or
source is pending/inconclusive, never compatible by default. Save records without
installing dependencies or sending traces.

## SC-008 — Readiness decision

Assemble the mapping evidence and provider/screening outcomes; link the relevant
SPEC-011 track IDs and preserve their frozen record bytes. Expected: distinct
outcomes for generic software, provider adoption, real-source admission and
publication, with reviewer/founder status explicit. Save a current decision
packet; no automatic adoption or historical status rewrite.

## Checks after implementation

The implementation tasks will add `tests/test_trace_adapter.py`; run the
following only after that file and its fixtures exist:

```sh
python3 -m unittest discover -s tests -p 'test_trace_adapter.py'
python3 scripts/validate_change.py --base develop --profile quick
python3 scripts/validate_change.py --base develop --profile pr
```

Evidence must include candidate commit, Python/environment, actual commands,
results, exclusions and limits. Run `pr` once on the stable candidate. Internal
clean-room and independent reproduction remain separate, explicit checks.
