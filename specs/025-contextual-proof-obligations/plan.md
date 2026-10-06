# SPEC-025 implementation plan

## Technical context and scope

Build a stdlib `research/contextual_lab/` checker over existing `research.lab.model`
configurations; preserve `integer-batch-v1`. Add candidate statement/premise and
source-binding documents under `research/proofs/`. Existing M3 paths supply scoped
cross-check inputs only. Planning delivery contains no functional implementation.

## Constitution check before research

Articles 2/4/6 demand admissibility and continuation preservation. Articles 8/10/11
require declared crossing conventions/coherence. Articles 13/14/17 distinguish
finite checking, proof and approval; Article 22 permits math tools only when useful.
Articles 23–25 permit a restricted proof packet with executable falsification.
Clause zero forbids an assumed YB theorem. ADR 0017's bounded insert approval does
not approve a proof or extension. No contradiction or SHOULD deviation identified.

## Research, assumptions and alternatives

See [research.md](research.md). Use explicit suffixes, not an undocumented universal
search. Keep existing bounds and <=6 total original operations; prefixes/suffixes
reuse instance IDs and no retry/new generation. At most 720 suffix schedules,
20,000 config/suffix comparisons and 120,000 steps; exhausted exploration is
inconclusive. No new solver/proof assistant is required.

## Design and compatibility

T001 writes typed candidate statements and a premise/source mapping. For T1,
separate equality of state/versions/results from chronology of identified events.
A candidate event-multiset quotient is considered only with an explicit proof
that all admitted modeled continuations cannot inspect event order. T2 records
termination, reachable-context independence, swap admissibility and suffix
congruence. A finite observation is not a proof of these universal premises.

T002 defines an experimental contextual request/report and read-only checker.
Inputs bind one complete fixture, two prefix schedules, explicit suffix set,
observation and caps. Replay prefixes rather than trusting arbitrary supplied
configurations. Confirm equal consumed/pending ID sets; evaluate enabledness of
remaining candidates and replay every specified admissible suffix from both
configurations. Suffix dependencies, guards and version checks use the original
integer semantics. Include empty suffix and preserve complete traces. Return
`divergent` with witness, `equivalent-for-listed-continuations` for a complete
matching finite domain, or `inconclusive`. Bind source/request/trace hashes;
reject producer verdicts unsupported by recomputation.

T003 adds negative/positive controls and finite corpus reports. T004 builds the
anchored proof packet: exact carrier, deterministic flattening, set-union argument,
exchange/residual mapping, closure, pair and far/adjacent coherence, involutivity
and observation quotient. Distinguish proof of an abstract class from finite
cross-check of executable bytes. T005 assesses review/tool options. T006 prepares
CoAgent artifact/semantic readiness, without executing third-party code. T007
packages independent reproduction and specific proof review. Tool/comparator
adoption after readiness needs a distinct ADR/founder decision and authorization.

## Validation strategy

The assurance/quickstart map every requirement to named future tests or review
protocols. Tamper fixture/suffix/model/step hashes; test cap exhaustion and
unsupported extensions. Capture raw finite results and source-bound candidate
statements separately. Quick/PR profiles validate repository consistency; fresh
reproduction and reviewer proof assessment remain separate gates. If no proof is
accepted, publish only a candidate with gaps and finite scoped findings.

## Constitution check after design

Continuation outputs explicitly name the examined suffix set. Trace differences
remain visible. Bound exhaustion and model mismatch abstain. Preserved notation
and excluded delete/nested/nondeterministic models protect historical M3 scope.
No core dependency, universal theorem or runtime permission follows.

## Human review and unresolved decisions

Candidate statements and proposed research contracts require review before
integration. Source-bound proof review remains pending; an accepted proof can be
handwritten/unmechanized with disclosed trusted assumptions. CoAgent feasibility
and tool value are open research questions addressed by tasks, not prerequisites
for bounded checker implementation. Expansion/adoption decisions remain separate.
