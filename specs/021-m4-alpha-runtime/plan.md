# Implementation plan

## Technical context and scope

Base: develop at cbe1580ca48d036e386531d843664e4795e64918. Python >=3.12;
existing isolated development environment. Keep the analyzer independently useful.
This candidate is a proposal, with no new execution capability implemented.

## Constitution check before research

Articles 2–4: preserve explicit order, equivalence and claim boundaries.
Articles 5–7, 12: inspectable stage separation, complete footprints and concurrency
control; disjoint paths alone never authorize concurrency.
Articles 13–16, 20: one portable model, observed verification and independent
consumer status; producer claims and MCP annotations grant no authority.
Articles 19, 21–25: measure utility and cost with counterexamples, without claiming
formal or empirical research closure. No MUST conflict or SHOULD waiver proposed.

## Research, assumptions and alternatives

See research.md. Serial-only extension was considered: useful as a reference but
insufficient for this proposed scheduling exit. HTTP and arbitrary-agent execution
would expand the trust boundary without a justified alpha use case and are deferred.
The chosen host pair is proposed as Codex primary / Claude Code contrast; reverse
that order if the founder prefers. Both actual clients are mandatory exit evidence.

## Design and compatibility

C1 — Unified policy path: analysis -> verified plan -> separate local operator
grant -> execution -> independent verification. Provisional owned modules:
`agent_braid/runtime_policy.py` and versioned runtime policy/grant contracts.
A grant binds canonical source/destination, input hashes, ordered dependencies,
effects, operation and attempt IDs, limits, execution contract, policy revision,
expiry and one logical run. No model-callable authorization tool. Do not represent
host approval UI as a server-verifiable grant without an actual verification path.
Attempt retries return verified state; they cannot allocate a second logical run.

C2 — Bounded scheduler: `agent_braid/runtime_scheduler.py` and a new reviewed
parallel execution contract. Preparation workers have separate writable stores,
indexes and scratch space; shared base objects are immutable. Verified disjoint
footprints and dependency-ready state govern admission. Coordinator locks, result
CAS and write-ahead transitions remain exclusive. Workers never publish refs.
A prepared parallel manifest is separately authorized; reordering, fallback to a
serial plan or changing budgets requires a new matching grant. Compare all admitted
orders to the serial reference within the small supported domain.

C3 — MCP/hosts: transport adapter in `agent_braid/mcp_runtime.py`, host-neutral
launch recipes and optional dependency metadata. Provisional tools: analyze,
prepare, status, execute, recover and verify. No authorize tool. Execute/recover
look up a pre-existing operator grant; the server enforces policy independently
of tool descriptions. Stdio only. Pin a common supported MCP revision and schema
in G1; implement exactly its lifecycle rather than mixing protocol generations.
MCP request IDs are transport IDs, not durable operation/attempt IDs. Bound message
size and retained diagnostics; redact credentials and host prompts not needed for
replay. Disconnect stops new scheduling and interrupts owned children under the
recovery contract. Resume requires an explicit valid grant, not reconnection alone.

C4 — Exit evidence: reproduction script, deterministic CI transport cases,
versioned consumer-verifiable host records and an immutable closure anchor.
Both real host exercises run on an owned Darwin arm64 fixture. Independently
reproduce core/runtime/protocol on Linux x86_64. This is the minimum matrix;
Linux real-host and Windows compatibility remain unclaimed until observed.
Capture exact candidate, Git/Python/host/protocol versions, platform, source
fingerprints, request/grant/effect hashes, timestamps, limits, observations and
consumer verdicts. Separate transcript normalization from verdict computation.

## Validation strategy

Requirement -> scenario -> prospective procedure -> actual test -> captured record.
See validation-plan.md and closure-matrix.md. Negative controls are mandatory.
Report correctness, refused unsafe cases, actual worker overlap, schedule equivalence,
replayability, useful diagnostics, startup/verification/coordination/CPU/wall/storage
costs and host-call cost. Use a frozen fixture corpus and budgeted repeated serial
and parallel runs; document repetition count and cold/warm policy before measurement.
These are engineering observations, without inference to arbitrary code workloads.

Run quick after each coherent implementation increment and pr once on a stable
candidate. Fresh reproduction, real-host exercises and independent review are
separate commands; a passing profile does not discharge them. Update assurance
with obtained evidence only after execution. Freeze before human review.

## Constitution check after design

The proposed parallel path adds a contract rather than interpreting M2 evidence as
execution authority. Unknown effects fail closed. No source promotion, prediction-
based admission, new algebra or licensing change. Current draft assurance records
must receive visible authority-drift review when canonical ADR 0020/contracts land;
never refresh them silently. Historical approved records retain their old bindings.

## Human review and unresolved decisions

G0: founder adopts the exact scope/exit matrix and ADR proposal before expanded
execution implementation. G1: pin common host/protocol support, budgets and any
optional SDK. G2: per-cut tests and code review. G3: fresh reproducibility and real
host evidence. G4: independent Luna review and separate final founder acceptance.
Proposal acceptance does not mark any implementation or closure row complete.
