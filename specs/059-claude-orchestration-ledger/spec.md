# SPEC-059: Coordination ledger and opt-in push notifications across Claude Code sessions (sketch)

**Milestone:** M4.6 — Claude Code dynamic workflows

**Status:** sketch. This is a short specification that records an objective, limits and the decisions already taken; it is **specified now and implemented later or never**. Implementation is blocked by gate GN of the G1 protocol (SPEC-057 owns G1), then by gate G2 (the "Coordination across tools" contract of `specs/039-ai-tooling-program`, drafted in `contracts/coordination-contract.md` for founder review) and by a dedicated ADR. A GN fail means SPEC-059 is not adopted and G2 is not opened. Nothing is implemented, frozen, signed, run or approved; `obtained_evidence` is empty and human review is pending. An earlier draft of this specification (17 requirements, 42 tasks, nine contract files) was reduced to this sketch by a founder decision of 2026-10-24 after the five-axis review of its pull request found it disproportionate to a feature that may never be built; it is recoverable from Git history if G2 opens.

## Objective

SPEC-057 gives an orchestrator advisory evidence about parallel Claude Code units and delivers notices as **data that the orchestrator pulls**. SPEC-059 records what would be added only if the evidence shows that is not enough: durable state that survives a session, a crash or a restart and is visible across **separate** sessions (an append-only, content-free, advisory ledger) and timely delivery to sessions that are not looking (opt-in push). It exists to put the question, its gates and its drafted contract in front of the founder, not to build either.

Article 12 applies in both directions. A delivered notice is never described as concurrency control, and the ledger never claims that a session read or acted on anything.

## Limits

- Advisory only. A claim is a declaration with a history: it never blocks a write, is never reclaimed automatically and is not a lock or lease. Blocking belongs to SPEC-058's opt-in guard.
- Agent Braid never launches, messages as, resumes, stops or authorizes a session, agent, team or batch (AGENTS.md; ADR 0021; Article 20), and never writes to another session's socket or calls a session-messaging tool. Every push transport is receiver-side: a component that runs in or for the receiving session.
- No hook, monitor, channel, mod or MCP tool in the main plugin (ADR 0024). Any delivery component is an opt-in companion, separate from the SPEC-058 guard companion, with its own ADR and package inventory.
- Content-free and local: identifiers, repository-relative paths, digests, counts and closed vocabularies; one user account, one macOS or Linux machine, a local POSIX filesystem. The hash chain is tamper-evident, not authentication. Cloud and Remote Control sessions, other machines, Codex, the VS Code extension, Windows, network filesystems and non-Git workspaces are not covered.
- Telemetry is deferred; nothing is collected.
- Unverified host behavior: every transport is unverified and none is selected; agent teams, channels and monitors are experimental or research previews; host facts are the documentation as read on 2026-10-24 (changelog to 2.1.310) and need probe receipts (HV-L1 to HV-L8) before any is relied on.
- No speed claim, no claim that notifications prevent conflicts or that a notice was read, no novelty claim: the research radar records mcp_agent_mail, Gas Town and Beads as ahead on shared claims and liveness, so interoperation is preferred and the ledger is a thin local record. The dogfood datum (one stale-read event) is an anecdote.

## Decisions taken (founder, 2026-10-24)

1. **Default delivery is Mailbox + Whisper.** The Mailbox is the pull notice that the orchestrator reads (the host wakes the orchestrator at the end of each turn of a linked session). The Whisper is `PreToolUse` `additionalContext` to the affected agent in its own session, a SPEC-058 companion output. The SPEC-059 companion ships no hook for it.
2. **Megaphone (monitor or channel) and Doorbell (data posted to the orchestrator's own session socket) are opt-in, in SPEC-059 only,** and enabled only if (a) G1 records late notices with measurable harm under a late-notice-harm measure that the G1 protocol must define before its freeze (gate G1-harm), (b) G2 is adopted, (c) the ADR is adopted and the companion is installed, and, for the Doorbell, (d) a transport receipt pinned after G2 adoption passes and the ADR reframes "never messages as a session" for it. Without all of these the effective mode is `pull` and the reason is named.
3. **A separate notification and ledger companion,** not part of `agent-braid-guard` (working names; same marketplace; publication only with release acceptance).
4. **The attributed-write ledger for shared-tree agent teams is decided after probe HV-L7;** otherwise guidance is documentation plus per-teammate checkpoints. No `PostToolUse` Bash observer is specified. Unattributed writers (orchestrator, human, shared tree) are unknown by default.
5. **Interoperation is documentation only** (`contracts/interop-adapters.md`); import adapters wait for demand or G1 evidence.
6. **G2 is decided after G1** and opens for planning only after GN passes (GA not `fail`).
7. **Settings** are owned by SPEC-057's `orchestration-settings` schema (most specific scope wins; a `block` at repository or user scope is a floor; operator-owned). SPEC-059 only extends them through `extensions.SPEC-059` (`contracts/push-settings.schema.json`) and redefines no scope.
8. **Host probes** are launched by the orchestrating Claude session through workflows or derived sessions after the founder authorizes each individual probe; agents prepare log-only scripts; evidence is pinned with the host version; additional spend is EUR 0.
9. **G1 stays staged** (SPEC-057 owns it), with a native-controls-only comparison added by that track; the guard ADR proposal (SPEC-058) is reviewed now and adopted with the G1 outcome. SPEC-059 consumes only GA and GN.

## Authorities

Constitution clause zero and Articles 1–3, 5–7, 12–15, 19–21, 23 and 25; GOVERNANCE.md; ADR 0021 (no model-callable grants), ADR 0024 (the main plugin has no hooks); `docs/theory/CLAIM_DISCIPLINE.md`; SPEC-057 (declarations, notices, settings, command errors, G1), SPEC-058 (guard, Whisper), SPEC-047 (telemetry vocabulary, deferred).

## Requirements and acceptance scenarios

Every requirement has planned evidence only. Every implementation task is blocked by G2 and none is written in this sketch; tasks are decisions, reviews and gates. A valid disposition of this specification is "specified but never implemented".

### REQ-001 — Keep the drafted G2 contract a draft and implementation blocked until it and an ADR are adopted

**SC-001:**
- Given the specs/039 route names an identity, concurrency, idempotency and recovery contract as the prerequisite of any shared ledger or cross-session delivery,
- when `contracts/coordination-contract.md` and `tasks.md` are reviewed,
- then the contract states rules, failure cases and conformance statements (C1 to C13) for each part, says that it adopts nothing and that G2 is decided after G1 and only after GN passes, and states the retention and deletion rule as a precondition of G2; no task in `tasks.md` creates source, test, script or companion-package files; and no ledger code, hook, monitor, channel or CLI subcommand is implemented before the founder records adoption of a version of the contract and a dedicated ADR is adopted.

Failure: a missing contract part, a task that implements, a statement that the contract works or is adopted, or adoption inferred from a passing structural check.

### REQ-002 — Compose push settings with SPEC-057 and fall back to the Mailbox with a stated reason

**SC-002:**
- Given the SPEC-057 settings schema, which stores `extensions.SPEC-059` without interpreting it,
- when the push-settings schema, its fixtures and the transport matrix are checked offline,
- then a whole settings record validates against the SPEC-057 schema and its extension entry against `push-settings.schema.json`; a resolved delivery reports `active` if and only if the effective mode is `push` with a transport and a receipt (the fixture with `active` and effective mode `pull` is rejected); every unmet enabling condition is named from the closed list and the effective delivery is then the Mailbox; text patterns reject a trailing line feed; no transport is marked selected or host-observed without a receipt; every transport is receiver-side and no sender-side cross-session post exists.

Failure: push reported active while unavailable, a redefined SPEC-057 scope or vocabulary, an assumed-selected transport, or a pattern that accepts control or bidirectional characters.

### REQ-003 — Decide the attributed-write ledger and the push unlock only on recorded observations

**SC-003:**
- Given probes HV-L1 to HV-L8 and the G1 late-notice-harm measure are unobserved,
- when the founder reviews the gates,
- then the Megaphone and the Doorbell remain disabled without a G1 record under the defined measure, a GN pass and G2 adoption; the attributed-write recorder is not built without a recorded post-HV-L7 decision and, if built, its export is partial, class `0-heuristic` and never yields an independent candidate; unattributed writers stay unknown by default and `unattributed` is a reserved unit name.

Failure: an enabled strategy without its record, a recorder built before the decision, a complete-coverage claim, or an orchestrator or human edit attributed to a unit.

### REQ-004 — Keep interoperation documentary and the governance boundary intact

**SC-004:**
- Given mcp_agent_mail, Gas Town and Beads already run shared claims,
- when `contracts/interop-adapters.md` and the specification are reviewed,
- then interoperation is documentation only with every format marked unconfirmed, adapters are deferred, nothing reads or writes another tool's state, and the specification excludes launching, messaging as, resuming, stopping or authorizing sessions, locks and leases as a feature, hooks in the main plugin, transcripts, telemetry and every host or platform other than Claude Code on macOS or Linux.

Failure: an adapter, a lease, a main-plugin hook, a telemetry field or a claim that the ledger replaces another tool.

### REQ-005 — Bound every claim and gate the work on evidence

**SC-005:**
- Given H-LD1 (a ledger with receiver-side digests surfaces a cross-session hazard earlier than the SPEC-057 pull notice) and H-LD2 (a verified transport delivers with acceptable loss and duplication), both untested,
- when the specification, the contract and the tracking drafts are reviewed,
- then hypotheses are separate from requirements; GA not `fail` and GN `pass` are the preconditions to plan G2; no wording claims prevention, speed, novelty, a read notice or host behavior without a receipt; obtained evidence is empty and nothing is frozen or approved; and negative, inconclusive and "never implemented" outcomes are recorded as valid.

Failure: a speed, prevention or novelty claim, an inconclusive gate treated as passed, or any approval inferred.

## Scientific boundaries and compatibility

Hypotheses (not requirements; no observation exists): H-LD1 (part (b) of the register entry H-CW2, tested against the pull digest by G1 gate GN, owned by SPEC-057) and H-LD2 above. The earlier H-LD3 (attributed-write export) is withdrawn with the recorder's detailed requirements and reopens only if the founder decides to build the recorder after HV-L7. Falsification, no transport verified, no collisions in G1, a GN that does not pass and a decision not to implement are valid outcomes.

Compatibility. Additive and gated: no change to `agent_braid/analysis.py`, AIM `0.2.0-draft`, SPEC-023, the SPEC-052 gate, the SPEC-057 schemas, the plugin MCP tools, limits or grants, or the five product skills. Notices are the SPEC-057 hazard notice and refusals the SPEC-057 command-error shape, both by reference and not copied. Surface ids are the closed four-id vocabulary of the family (`workflow-tracks`, `linked-sessions`, `agent-teams`, `batch`).

## Clarifications

Earlier decisions of the family stay: the split into SPEC-057 (advisory core, implemented after #671 and #672), SPEC-058 (opt-in guard, blocked by G1 and an ADR amendment) and SPEC-059 (this sketch); all four surfaces with one vocabulary and three lifecycle points (pre-flight, continuous, recovery; integration stays SPEC-052); a single policy compiler in SPEC-058 with no hooks in the main plugin; compatibility classes (receipt `1-syntactic`; pre-flight, recovery, ledger and exports `0-heuristic`; `notAGuarantee` always true); "unknown as a first-class result" is not claimed as a differentiator by itself; telemetry deferred with a never-collect exclusion; the scope is Claude Code only. Planning interpretations by the drafting track, not founder-approved: the kill switch is a floor like `block`; one ledger per repository keyed by a digest of the canonical Git common directory in a private per-user state directory outside every working tree; probe ids HV-L1 to HV-L8; every number marked proposed in the contract is a planning value to be fixed in the G2 review and before any run. Decisions recorded as "founder opened" in this family are proposed pending a separate founder decision addendum that the integrator owns.

## Evidence and unresolved questions

Obtained evidence: none. Human review pending. The schemas and fixtures were checked with the pinned `jsonschema` package as a planning aid only.

Open for the founder or for observation: whether to open G2 at all, after G1 and only if GN passed; the G1 late-notice-harm measure (it must exist before the G1 freeze, or the push strategies stay disabled forever); the wording of the Doorbell reframing in the ADR; the kill-switch floor, bounds, hook latency threshold, retention amendment and ledger location; whether the recorder ships after HV-L7; whether any import adapter is wanted; and the host behaviors HV-L1 to HV-L8 (hook context reaching the model per surface, own-session socket acceptance, monitor and channel delivery, repetition after compaction or resume, loss and duplication under bursts, identifier survival across restart, lock and fsync behavior).
