# Braid Harness capability profile contract — frozen design v0.1

Status: **frozen design contract, offline and design-only**, dated 2026-11-08 by
founder decision ([record](../owner-decisions-20261108.md)). It is not an
implemented or adopted API, extends no existing public schema (`agent-braid-plugin/v0.1`,
AIM, runtime grants, the fixed-patch operation language, the offline
[manifest contract](../../048-harness-variant-laboratory/contracts/offline-foundations.md)),
and grants no permission. Every record below carries `executionAuthorization=false`.
Extend the HAR.1/HAR.2 records rather than redefine their authority semantics.

## 1. Freeze scope and open dependency

- **Dependency SPEC-048/T001** is satisfied for the bounded offline profile only
  ([ADR 0027](../../../docs/adr/0027-braid-harness-offline-foundations.md)).
- **Dependency SPEC-049/T005 stays OPEN.** No cohort result exists (the deterministic
  cohort was recorded infeasible; native yield is unknown). Nothing in this contract
  is derived from, or claims, a T005 outcome.
- Freezing is therefore a **design freeze**. Any T005 result (or a missing result
  that changes an assumption here) reopens this contract by a **versioned
  amendment** (`v0.2`; the founder decides whether a T005 outcome changes an
  assumption, and this section is the only amendment trigger; same file, change log in section 11). Silent edits of a
  frozen value are refused; a stale reader treats a newer minor as unsupported.
- The feature-local [ADR proposal](../../048-harness-variant-laboratory/adr-proposal.md)
  **stays a proposal** and is not edited. The staged admission decisions live only
  in section 8 of this file. No ADR number is reserved here.

## 2. Admission vocabulary

Each state is recorded per *(component class, host, profile version)*, never per
spec or per milestone. A state does not imply the next one.

| State | Meaning | Evidence needed to claim it |
|---|---|---|
| implemented | Code exists on `develop`, with positive and negative tests, for a stated offline scope. | Merged module and test run; says nothing about any host. |
| qualified | An actual native host profile ran the component class under enforced containment and the controls passed. | Native unit records within the section 6 limits plus an obtained qualification decision (SPEC-048/T008 for HAR.1; component-specific for HAR.3). Doubles and simulated containment never qualify. |
| enabled | An exact adopted policy and fresh operator authority allow use of one qualified profile in one scope. | Separate adoption record. Nothing is enabled by this contract. |
| blocked | The class could become admissible, but a named prerequisite is missing. Stays visible; an infeasible profile stays blocked. | Blocker and unblock condition recorded in section 8. |
| excluded | Deliberately outside the contract. Reopens only by versioned amendment. | Reason recorded in section 9. |

A milestone or task cannot close by relabeling blocked implementation work as an
assessment. A no-go finding leaves the implementation task open.

## 3. Component class inventory

Classes follow the eight-component upstream taxonomy plus the HAR.3 control
layers. "Current implementation" is what exists on `develop` at `76d5a8a6`.
Upstream paths are in `google-research/harness2` at
`1cfe254e8d25b15f37048c3730134686abe60335`; SHA-256 values are from
[source-identity.json](../../048-harness-variant-laboratory/research-evidence/source-identity.json).

| Class | Owning task | Current implementation | Exact source reuse (file, SHA-256 prefix) |
|---|---|---|---|
| C1 task-local guidance/prompt | 048 (done), 050/T002 | Offline: `harness_manifest`, `harness_surface`, `harness_context`, `harness_observation`, `harness_refinement` | `core/tree.py` c2a15690, `core/context.py` 63dd482e, `core/spec.py` f245ec9e, `core/runmark.py` 99a7c3f0 (048/T002 to T006) |
| C2 memory / reusable experience | 049/T006 (done), 050/T008 | Offline: `harness_experience` (quarantine states) | `core/library.py` 00219fda |
| C3 skills, frontmatter, lazy workflows | 050/T003 | None | `core/tree.py` (skill/script reference checks); `core/prompts.py` has **no pinned hash**: record file, revision and hash in T003 before any adaptation |
| C4 tool guidance | 050/T004 | None | None pinned; original text only |
| C5 deterministic helpers / tools | 050/T004 | None | None pinned; new code needs its own provenance record |
| C6 hooks / events | 050/T005 | None | None reusable; `substrate/codex.py` 281a0727 hook-trust/bypass argv is excluded (section 9) |
| C7 plugins / tool-loop changes | 050/T005 | None | None reusable; `substrate/opencode.py` dabc7995 not adopted |
| C8 delegated roles, handoffs | 050/T006 | None (existing analysis/planning semantics are reused, not changed) | `core/proposer.py` 475ef49d is pinned but its fit for role scaffolds is unreviewed; T006 decides |
| C9 search depth / width | 050/T007 | One round only (`harness_refinement`) | `core/recursion.py` b299813b, `core/selection.py` 2cb3353b, `core/ledger.py` 7059de5d, `core/schedule.py` 6e46c5ab |
| C10 automatic-promotion policy | 050/T009 | None; human promotion exists (`harness_promotion`, 049) | None pinned |
| C11 product CLI / advisory contract | 050/T010 | Laboratory CLI only (`harness_cli`, 048/T015); no product contract | `cli/run_sweep.py` 83998848 |
| C12 lifecycle (install, migrate, drift, rollback, uninstall) | 050/T011 | None | None pinned |

Reuse rules: every adapted portion carries file and revision, file-level terms,
retained notices and a modification notice under
[THIRD_PARTY.md](../../../docs/development/THIRD_PARTY.md) and `LICENSES/`. Source
reuse never imports upstream runtime permissions. Upstream benchmark stacks,
cloud bridges, runner patches, logos and prose are not dependencies.

## 4. Actual host support

Observed 2026-11-06 to 2026-11-08 ([founder decisions](../../048-harness-variant-laboratory/evidence/founder-decisions-20261106.json),
[T008 evidence](../../048-harness-variant-laboratory/evidence/t008.json)); no other
support is assumed from vendor documentation.

| Host | Observation | Qualification |
|---|---|---|
| Claude Code | `claude` 2.1.292, pinned at `/usr/local/libexec/braid/claude-2.1.292`. Adapter and native wiring tested with doubles only. | Qualification **authorized**, not decided. Window 2026-11-09T20:30Z to 2026-11-30, at most 4 serial units. No native unit has run, so no class is qualified. |
| Codex CLI | Not installed (`command -v codex` finds nothing). | `not-qualified: not installed`; refused. Review again before HAR.1 closes. |

Per-class cell for both hosts at this freeze:

| Class | Claude | Codex |
|---|---|---|
| C1, C2 | implemented offline only; not qualified | refused |
| C3 to C12 | no observed support inventory; not qualified | refused |

Event, hook and plugin schemas per host are **not yet inventoried**; T005 must
record the observed host build and its schema before any claim. A host that
supports a feature does not make the other host support it. Partial qualification
never implies both-host acceptance.

## 5. Records and versioning

Wire identity: `braid-harness-profile/v0.1`. Validation rules are the offline
manifest rules: exact key sets, unknown or future fields and versions refuse,
`executionAuthorization` is boolean false, raw JSON is bounded UTF-8 (depth 16,
finite numbers, signed 64-bit integers), duplicate keys and invalid Unicode refuse,
identities are full SHA-256 over canonical JSON (`system_one.canonical`), paths are
normalized relative NFC strings with no traversal or case-fold collision. Consumers
reparse raw bytes and verify a trusted full hash; a producer hash alone proves
neither authenticity nor rights.

Version policy: a patch version changes no field. A minor version only adds
optional fields that old readers may ignore **only if** declared in a
`compatible` list; otherwise old readers refuse. A major version or any
tightening or loosening of a section 6 limit needs a versioned amendment. The
previous usable profile is retained by every migration, and downgrade must
produce the prior profile byte-for-byte or refuse.

Record mapping: C1 to C8 use ComponentProfile (C8 also OrchestrationProfile); C9
SearchPlan; C10 AutomaticPolicy; C11 is an advisory view over ComponentProfile and
LifecycleEvent with no record of its own (T010 defines the codec); C12
LifecycleEvent. A component-specific qualification (section 2) is a separate
founder-signed decision record per class and host, like SPEC-048 founder decisions.

- **ComponentProfile**: version, `componentClass` (C1 to C8 above), component
  inventory (positive list; path, SHA-256, size), parent/derived source with file
  and revision, host support matrix (per host: observed build, qualification
  record hash or explicit `unqualified`), immutable path/content/effect policies,
  declared effect class (section 7), lazy context limits, tool/event/role schemas,
  license provenance (file, terms, notices, modification notice), admission state
  per section 2. No field holds authority.
- **SearchPlan**: source, base and profile identity; sequential depth and parallel
  width (section 6 ceilings); full trial DAG and lineage; equal-budget comparator;
  reservation and stop rules. Proposal, transport and selection retries are
  separate counted attempts; keep-base and inconclusive are valid outcomes.
- **OrchestrationProfile**: ownership, declared dependencies and effects,
  role-specific bounded context, handoff/output contracts and a serial-reference
  verifier. Unknown interactions cannot be asserted independent by model text; role
  text never grants concurrency or permissions.
- **AutomaticPolicy**: exact adopted eligibility and version, independent
  evidence, regression and cost gates, state `disabled|shadow|canary|active|stopped`
  (initial and default `disabled`), operator authority and rollback target.
  Generated policy text is never its own adoption record.
- **LifecycleEvent**: source, profile and host identity; actual transition, actor
  and evidence; migration and rollback links; private retention and export
  disposition; incident or drift reason.

## 6. Numeric limits

**Native quota and time (reused unchanged from SPEC-049 D2** — see
[protocol](../../049-harness-evaluation-learning/evaluation-protocol.md) and the
[2026-10-31 founder decision](../../049-harness-evaluation-learning/evidence/registration/d2-caps-founder-decision-20261031.json)):

| Limit | Value |
|---|---|
| Wall time per unit | at most 30 minutes; a unit that reaches it is recorded `interrupted` and stays in the denominator |
| Session quota | at most 10 % of the 5-hour window per native session |
| Cohort quota | at most 15 % of the weekly all-models window |
| Cohort size | at most 16 native units in total; any cohort needs its own admission. The SPEC-048/T008 cohort of at most 4 serial units is a tighter, separate authorization and binds first for that task |
| Stop rule | no next unit if weekly use exceeds 80 %, extra usage is enabled, or the quota reading is unavailable or stale |
| Additional cash | EUR 0; no paid fallback route |

These caps bound quota only. They admit no cohort, and each profile inherits them
without loosening. A tighter cap in a later admission wins.

**Offline structural ceilings (reused from ADR 0027 and the implemented modules):**
manifest 1 MiB and JSON depth 16; candidate files 32, per file 32 KiB, total
256 KiB, relative depth 4; context inventory 16 entries and 128 KiB; stage output
64 KiB; journal/export allowance 8 MiB; admission 300 seconds with one reservation
and no renewal by recovery; context feedback at most 64 records of 16 KiB;
experience store at most 128 entries, 16 evidence rows, cue 160 and lesson 512
characters; context budget at most 64 entries and 256 KiB (a packaging ceiling
above the 16-entry/128 KiB laboratory inventory, which binds first); observation at
most 256 events, 32 artifacts of 256 KiB, 64 secrets and 16 transport errors;
refinement policy 4096 bytes, rationale 2048 bytes and at most 4 probes. Native, model, child, network, retry and cash counts stay **zero** until
a separate adoption.

**Search ceilings at v0.1:** sequential depth 1 round, parallel width 1 (serial),
matching the implemented one-round default (one base probe, two scoped proposals,
one composed probe). Raising either needs T007 equal-budget evidence, a versioned
amendment and, for native concurrency, its own qualified effect profile.

**Not set by this freeze (see open questions):** retention duration, per-class
CPU/RSS/disk caps, and any hook/event rate caps. Missing required enforcement
refuses the profile; it is not replaced by a default.

## 7. Threat and effect boundaries

Threat model: the owner controls the trusted host and OS; compromised operators or
kernels are out of scope. Hostile same-UID interference needs explicit handling in a
qualification or is excluded from it. A worktree is a Git separation, not a
sandbox. Candidate text, skills, lessons, hooks and plugin descriptions are
untrusted data; instruction-like content cannot alter policy.

| Effect class | Description | Admission |
|---|---|---|
| E0 | Inert text or ordering inside the owned laboratory | Offline, ADR 0027 |
| E1 | Bounded reads from positive inventories | Offline, ADR 0027 |
| E2 | Writes to a new private owned laboratory destination | Offline, ADR 0027 |
| E3 | Child process or deterministic helper execution | Blocked: needs adopted effect contract plus qualified containment |
| E4 | Network or provider/model session | Blocked: needs admission, zero-spend route, quota gate (section 6) |
| E5 | Host or global configuration, authorities, permission issuers, acceptance verifiers, unrelated workspaces | Excluded for every profile |

Protected layers no profile may modify: Constitution and canonical authorities,
AGENTS and host global instructions, Spec Kit scaffolding, acceptance verifiers
and oracles, permission issuers and grants, provider and model settings, source
baselines and output destinations. Task-local components install only inside a
reviewed qualified effect contract. Syntax acceptance and simulated containment
are not execution qualification. Plugin and tool-loop components have distinct
provider support; hooks must deny recursive privilege expansion, bound ordering and
cancellation, and clean up on failure. An explicit native refusal is required when
containment, authentication route, zero-spend conditions, outcome checks or
observation support are unavailable. Advice returns `executionAuthorization=false`;
future execution interfaces need separate contract adoption.

## 8. Staged admission decisions (2026-11-08)

Decisions recorded in this file only. "Blocked" lists the prerequisite; none is
waived by this freeze.

| Class | Offline implementation | Native qualification | Enabled | Decision and unblock condition |
|---|---|---|---|---|
| C1 guidance/context | implemented (HAR.1) | blocked until SPEC-048/T008 verdict (Claude units from 2026-11-09T20:30Z; Codex refused) | no | Offline use admitted under ADR 0027. Native effects blocked until the T008 verdict. |
| C2 experience | implemented (quarantine) | blocked, as C1 | no | Curation (050/T008) after T003; no unreviewed semantic rewrite becomes active. |
| C3 skills, lazy loading | planned (T003) | blocked | no | Inert-text offline loading admissible once T003 passes; executable references stay blocked. |
| C4 tool guidance | planned (T004) | blocked | no | Text only until C5 is admitted. |
| C5 helpers/tools | planned (T004) | blocked | no | **Blocked**: native effects need SPEC-048/T008 verdict plus an adopted E3 effect contract. |
| C6 hooks | planned (T005) | **blocked from the start** | no | No containment qualification; Codex not installed. Unsupported events stay unavailable. |
| C7 plugins / tool loops | planned (T005) | **blocked from the start** | no | Same blocker as C6; syntax acceptance is not qualification. |
| C8 delegated roles, provider-native delegation | planned (T006) | **blocked from the start** | no | Same blocker; provider-native delegation needs its own qualified profile. |
| C9 depth/width search | planned (T007) | blocked | no | Offline serial refinement only; native concurrency gated by its exact effect profile. |
| C10 automatic policy | planned (T009), `disabled` | blocked | no | Native activation needs a separately adopted exact policy; offline synthetic transitions supply no adoption. |
| C11 product CLI/advisory | planned (T010) | not applicable (advice only) | no | Existing plugin/MCP analysis-only contracts do not change; any execution surface needs separate adoption. |
| C12 lifecycle | planned (T011) | blocked | no | Depends on T005, T008 to T010; previous usable profile always preserved. |

Reopening: a blocked class changes state only through its named prerequisite
(qualification record, adopted effect contract or adopted policy) recorded as its
own artifact, never through this table alone.

## 9. Deliberate exclusions

Reopen only by versioned amendment after source, rights and cost review:
benchmark downloads, cloud and provider bridges, bundled third-party runner
patches; the upstream Codex sandbox/approval/hook-trust bypass launcher argv;
global or host configuration writes; modification of authorities, permission
issuers or acceptance verifiers (E5); automatic global registration of new
executables; model training and hosted memory services; paid or extra-usage fallback;
importing forecasting or System 1 acceptance; unrestricted self-modification.

## 10. Privacy, retention and export

All profile, lesson, trace and trial data is private by default and stays in the
owned laboratory destination. Export requires an explicit per-export disposition
in the LifecycleEvent, bounded size (section 6 allowance), a secret inventory and
no personal or credential material; hashes bind bytes, not reviewer identity or
permission. Lessons and traces keep supporting and contrary provenance; expiry or
revocation propagates without rewriting historical evidence. Uninstall removes
only owned staging inventory and keeps failure and cleanup receipts. Purge
semantics and retention duration are an open question below; until set, nothing is
auto-deleted and nothing is auto-exported.

## 11. Verification and change log

Verification of this freeze is structural: the section 6 and 7 values trace to the
cited records, section 8 contains one row per class, and no field here grants
authority. It is not scientific, native or product acceptance. Implementation tasks
T002 to T011 add positive and negative tests against these records; planned
evidence remains `evidence/t001.json` with obtained evidence stated there.

| Version | Date | Change |
|---|---|---|
| v0.1 | 2026-11-08 | First frozen design replacing the 13-line draft; SPEC-049/T005 open. |

## 12. Open questions (non-blocking)

1. Retention duration and purge schedule for lessons, traces and trial data.
2. Per-class CPU, RSS and disk caps for E3 helpers (needs a qualified containment).
3. Observed hook/event schemas per host build (needs T005 inventory).
4. Pinned hash for `core/prompts.py` (absent from source-identity.json) before C3 reuse, and a fit review of `core/proposer.py` before C8 reuse.
5. ADR numbering at adoption: `docs/adr/` already holds a Braid Lightning ADR
   numbered 0039, and the proposal's "next available" note is out of date.
