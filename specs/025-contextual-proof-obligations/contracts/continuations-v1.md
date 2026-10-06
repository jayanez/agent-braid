# Bounded continuation interface v1

Status: proposed technical interface; revised after technical review blockers.
Independent technical re-review pending; no implementation acceptance.
Version: `contextual-continuations-v1`. No accepted proof or human scientific
approval follows. This is an additive feature-local research interface, outside
AIM certificates, runtime grants and canonical schemas.

## Source and architecture mapping

The sole transition interpreter remains `research.lab.model.run`. Its fixture
validation and observation functions remain unchanged. This layer validates an
explicit finite continuation request, maps dependency-closed fragments to the
existing complete-schedule interpreter, retains original configuration dimensions,
and checks precisely the named observation/enablement product below.

The source-bound [premise inventory](../premise-inventory.json) remains a candidate
statement inventory. T1 concerns full effect/control-read completeness and
preserved enabledness; T2 quantifies over every reachable swap context and suffix.
This finite interface checks neither universal quantifier. It introduces no event
quotient, result-reading primitive, runtime admission or real-operation execution.
Constitution Articles 2–4/6/8–14/17–18/20/22–25 and ADRs 0005/0017 remain binding.

## Request

Exact fields:

- `requestVersion`: `contextual-continuations-v1`.
- `fixture`: an unchanged valid `integer-batch-v1` fixture, including the existing
  `exact` or `projection` observation contract.
- `leftPrefix`, `rightPrefix`: lists of original operation-instance IDs, each
  unique, with the same consumed set. Each prefix is dependency-admissible and
  must replay successfully; blocked/error prefixes are rejected as inputs rather
  than treated as reachable successfully consumed configurations.
- `suffixes`: explicit unique ordered lists of original remaining IDs, including
  the empty list. At most 720. No retries or newly generated operations. Partial
  suffixes are legal if every dependency is already consumed or earlier in that
  suffix. Missing prerequisites or invalid order reject before exploration.
- `caps`: exact integer fields `checks` in 0..20,000 and `steps` in 0..120,000.
  Boolean values reject. Zero budgets are admitted and yield honest exhaustion.
- `sourceBindings`: exact required path-to-SHA-256 map returned by
  `source_bindings()`, matched against the current checked source files.

Original model bounds remain: 1–6 total fixture operations, 1–64 resources,
identifiers at most 256 characters, signed integer limit 2^63-1, expression depth
12, JSON nesting depth 64, input at most 8,000,000 bytes. Floats, duplicate JSON
members, unknown object fields, duplicate IDs and unsupported operation/observation
extensions reject. No arbitrary supplied configuration is trusted.

The exact provided suffix set and caps are bound into the request hash. Evaluation
uses deterministic `(length, lexical ID tuple)` ordering. Order normalization does
not invent omitted suffixes or equate differently bound request bytes.

## Faithful fragment mapping

For every replay, form a restricted fixture containing exactly the scheduled
original definitions, with unchanged original initial state, versions and chosen
observation. Dependency closure is checked first. Run the complete scheduled
fragment with the existing `model.run`. This does not start from an injected
configuration or reset counters after a prefix: each prefix-plus-suffix is
replayed from the original initial fixture, preserving all prefix results/events.
An empty fragment uses the canonical initial state/versions, empty results/events
and no executed steps; it does not call the interpreter with an invalid empty
operation batch.

A fragment result retains canonical state, versions, per-instance results, raw
chronological events, status and reason. Restore the full original pending
inventory: interpreter-retained unexecuted scheduled tail first, followed by
original unscheduled IDs in lexical order. A `complete` status means the selected
fragment completed, not that all original operations completed. The pending
inventory remains visible even after a complete partial fragment.

Verify that successful prefix result keys equal precisely the consumed IDs.
Both prefixes have the same remaining original instance set. Prefix guard,
version, missing-resource, arithmetic and dependency behavior is preserved by
replay; no second transition interpreter is introduced.

## Enabledness probes

For every remaining candidate at each successfully replayed configuration,
check whether all its dependencies are already consumed. If not, retain a known
`blocked/unmet dependency` enabledness result without executing the candidate.
Otherwise replay the original fragment followed by that candidate using the
same restricted-fixture mapping. Retain the full probe configuration and digest.

A complete probe means `enabled`. A blocked guard/version probe means known
`blocked`, with canonical reason. An interpreter error means `error/unknown` and
prevents a positive equivalence verdict. A known disabled probe on both sides is
not itself incomplete coverage. Probe results never authorize execution.

Retain enabledness of all remaining operations at the starting prefix pair and
after each successfully completed listed suffix. For blocked/error listed suffixes,
future enabledness is explicitly unavailable; it is not fabricated from a
configuration that failed to execute the selected fragment.

## Comparison and outcome

The comparison is the declared product of:

1. `model.observe(fragmentOutcome, fixture.observation)`;
2. remaining-operation enabledness classifications and reasons.

Exact mode includes full configurations and chronological event order. Projection
retains precisely the existing selected state/outcome observation; it deliberately
excludes result values, versions and events. Those omitted dimensions are retained
and reported as raw differences, never silently asserted equal. No event sorting,
permutation quotient or expanded result-reading observation is introduced.

For complete coverage with successful listed paths and no error probes:

- Any product mismatch yields `divergent`.
- Matching products for every named suffix yields only
  `equivalent-for-listed-continuations`.

Any listed path blocked/error, unavailable check or cap exhaustion yields
`inconclusive`, even if some diagnostic mismatches were retained. Invalid input
rejects. Disabled-but-known probes do not alone make the result inconclusive.
A differing starting enabledness map is a diagnostic empty-suffix witness; the
empty suffix is required and explicitly included in comparison coverage.

A minimum witness is the shortest, then lexical, differing **registered** suffix.
No unregistered minimized continuation is synthesized. Raw chronology/result
mismatches under a projection can be reported without changing its declared
observation. No label denotes all admitted continuations, universal contextual
equivalence, global confluence, theorem acceptance or runtime safety.

## Budget accounting

`checks` counts logical work, including cache hits: each prefix configuration
side, each suffix configuration side, each candidate enabledness probe side, and
each listed-suffix paired comparison costs one check. Dependency-disabled probes
and empty fragments cost a check even without an interpreter call. Reserve a
logical check before evaluating or fetching its cached result. Cache hits cannot
bypass the 20,000-check limit. Report `checks`, `actualReplays`, `cacheHits` and
`steps` distinctly; their names do not imply interchangeable units.

Before an uncached interpreter replay, reserve its scheduled length against the
step cap. Charge actual successful events plus one failed attempt for a
blocked/error replay; release unused step reservation after completion. Cached
replays execute zero new modeled steps, but consume their logical check. Replays
never exceed the step cap. There is no wall-clock cutoff or unreported skip.

### Hard report byte ceiling

The canonical serialized report, including its embedded request, all retained
raw outcomes/probes/observations, coverage, source bindings and report hash, is at
most **16,000,000 bytes**. Verification applies the same ceiling before parsing
and throughout recomputation. Input requests remain at most 8,000,000 bytes.
Larger report input rejects; a producer running out of report capacity yields a
bounded `inconclusive` report with unvisited suffixes and no positive verdict.

Before accumulation, reserve exact bytes for the initial request/source/coverage
envelope plus 32,768 bytes for fixed report metadata, reasons, witness references
and final hashes. The coverage inventory includes the entire requested suffix
set, so unvisited bookkeeping is reserved from the start. A witness refers to a
retained check rather than duplicating full configurations. Before retaining a
prefix/probe/check block, reserve a conservative block upper bound derived from:

- complete original state/versions using maximal signed integers/version values;
- all original result IDs with maximal-length bounded integers;
- up to six chronological events, each with all original resources in its reads,
  its original ID/target strings and maximal-length values/version numbers;
- all original pending IDs; 8,192 bytes of bounded reason allowance;
- one such configuration bound for every retained outcome/probe, another for
  every exact observation copy, and 4,096 bytes of block wrapper/hash allowance.

Use canonical ASCII JSON byte sizes of the actual fixture identifiers, not
character counts. No operation definition or arbitrary source text is copied
into an outcome beyond the already bound embedded request. Missing-resource and
arithmetic reasons in the unchanged interpreter fit the bounded allowance.
A projected observation is bounded by its corresponding full configuration.
After block production, check its actual canonical byte size against reservation
before retaining it, then release unused reservation. Unexpected bound violation
fails closed; it cannot append an oversized block or return equivalence. Before
emitting or verifying, check the exact complete report byte size again.

If a conservative reservation cannot fit, stop before retaining/executing that
block, record `report-byte-cap`, and keep the remaining suffixes unvisited. The
ceiling applies even when all raw results are available through a replay cache.
Budget exhaustion at prefix or probe preparation yields explicit unavailable
configuration/enablement entries and an inconclusive result. No cap exhaustion
can be labeled `equivalent-for-listed-continuations` or universal equivalence.

## Report and verification

Exact top-level fields: `reportVersion`, `request`, `requestHash`, `sourceBindings`,
`prefixes`, `initialEnabledness`, `checks`, `coverage`, `costs`, `verdict`, `witness`,
`executionAuthorization`, `proofAccepted`, `limits`, `reportHash`.
`executionAuthorization` and `proofAccepted` are always false.

Every check retains its suffix, both complete raw fragment outcomes when
available, chosen observations, enabledness/probe configurations, comparison
status, unavailable reasons and separately named raw difference dimensions.
Coverage states requested/completed/unvisited suffixes and cap/failure conditions.
Hash every input/observation/outcome; reportHash binds all other report fields.

All report/input digests use the existing canonical model digest convention;
sourceBindings contain lowercase raw SHA-256 hex. Source bindings pin `research/lab/model.py`, operational semantics, Constitution,
ADRs 0005/0017, premise-inventory.json and contextual implementation files. These
are local source bindings, not permissions or signed proof certificates.
`verify(report)` recomputes the entire report from its embedded request against
current matching pinned sources, comparing canonical bytes. Altered fixtures,
suffixes, caps, sources, outcomes, verdicts, traces or hashes reject. Verification
confirms bounded replay consistency only, not scientific or founder acceptance.

Public API: `check(request) -> report`, `verify(report) -> verification`,
`source_bindings() -> mapping`; invalid inputs raise the model's `Invalid` error.
The invalid-input exception applies to `check`; `verify` returns an explicit
rejected status for malformed or oversized artifacts. Package re-exports and CLI
use those exact implementations. A rejected verifier
returns an explicit rejected status, never the producer's success verdict.

CLI: `python3 -m research.contextual_lab check <request> --output <report>` and
`python3 -m research.contextual_lab verify <report>`. Input is local bounded JSON;
output is an explicitly selected local destination created exclusively after full
production, with existing/symlink/colliding destinations refused. Verification is
read-only. No project commands, network calls, providers or external effects occur.

## Versioning and acceptance boundary

No canonical model, API, schema, authority or existing CLI is changed. The research
package is exercised from a source checkout; installation/backend support is not
claimed. A future observation quotient, event/result-reading expression, new model,
retry or external action requires a separate typed contract and applicable
architectural review. This technical interface review is distinct from specific
independent proof review, human scientific acceptance and founder approval.
