# Coordination contract (draft for founder review): identity, concurrency, idempotency, recovery

Status: **draft for founder review. Not adopted, not frozen, not approved.** This document drafts the contract that the `specs/039-ai-tooling-program` route "Coordination across tools" (shared plans and resource ownership) names as its prerequisite: "Identity, concurrency, idempotency and recovery contract". It is gate G2 for SPEC-059. G2 is decided after G1 (the founder decided so on 2026-10-24) and is opened for planning only after gate GN of the G1 protocol has passed (SPEC-057 owns G1; a GN fail means SPEC-059 is not adopted and G2 is not opened). G2 is satisfied only when the founder adopts a version of this contract in a separate decision record and a dedicated ADR for the notification and ledger companion is adopted. Neither exists. Until then nothing in SPEC-059 may be implemented, and nothing here adds a v1 task, a compatibility claim or execution authority (specs/039 says so of every route).

SPEC-059 is a sketch (a short specification, five requirements, decision and gate tasks only); this contract is the one substantial artifact kept for founder review. The ledger event schema, notice and recovery-view schemas and the attributed-write export schema of the earlier draft were removed: notices and errors are the SPEC-057 hazard notice and command-error shapes, and an event schema is drafted only if G2 opens. Only the push-settings extension schema is kept (`push-settings.schema.json`).

How to read it. Sections 1 to 4 are the four parts of the contract. Section 5 fixes what delivery means, section 6 the privacy and tamper boundary, section 7 compatibility, section 8 the conformance statements that SPEC-059's requirements and procedures test, and section 9 the decisions (recorded on 2026-10-24, and those that only the founder can still take). Numbers marked **proposed** are planning values to be fixed in the review, not measurements. Words in capitals follow RFC 2119 as a drafting convenience; the Constitution, GOVERNANCE.md and the ADRs keep their authority and this draft cannot weaken any MUST in them.

## 0. Scope and non-goals

The contract governs one thing: a durable, local, advisory record of who declared ownership of what, which notices exist about it, and what each receiver-side component observed about delivering them, for several Claude Code sessions, agents or teammates on one machine and one repository.

It is **not**:

- a lock manager or lease service. A claim is a declaration with a history. It never blocks a write, never expires into someone else's hands and is never a headline feature (the research records mcp_agent_mail, Gas Town and Beads as ahead on shared claims and liveness; interoperation is preferred, see `interop-adapters.md`);
- a scheduler, launcher, messenger or recovery executor. Agent Braid never launches, messages as, resumes, stops or authorizes a session, agent, team or batch (AGENTS.md; ADR 0021; Article 20);
- an authority. It holds no grants and no model-callable capability. `executionAuthorization` is the constant `false` in every record (ADR 0021);
- a multi-host or multi-user store. One user account, one machine, one local POSIX filesystem. Cloud sessions, Remote Control, other machines, Codex, the VS Code extension, Windows and network filesystems are **not covered**.

## 1. Identity

### 1.1 Identifier classes

| Class | Examples | Who assigns it | What it means |
|---|---|---|---|
| Run id | `run-01` | the orchestrator, or the CLI on `ledger-open-run` | One coordination run (a workflow run, a batch, a team, a set of linked sessions). Scopes units and notices. |
| Unit id | `track-a`, `teammate-2` | the orchestrator in the SPEC-057 declaration | A stable name for a unit of work. Survives restarts. |
| Host binding | host `session_id`, `agent_id`, `agent_type`, working-directory digest | the host, as observed by a hook input or supplied by the operator | An opaque observation of which host entity currently runs the unit. Never interpreted. |
| Actor | `operator-cli`, `checker`, `companion-hook`, `adapter`, `model-asserted` | the writing component | Who wrote an event, with a trust label. |
| Event id, notice id, idempotency key | hex ids, keys | the ledger or the caller | Section 3. |

### 1.2 Rules

1. **Identity is not authority.** No identifier, binding or actor label grants anything. A unit's right to edit a path is decided by the host's permission system and by the user, never by the ledger.
2. **Late binding.** A unit id is known before its host binding. A `unit-bound` event links the two when a hook input or the operator supplies the host identifiers. Writes observed before binding are recorded as `unattributed`; they are never retro-attributed silently.
3. **Restart, resume, fork.** A restarted or resumed agent may carry a new host identifier. A new `unit-bound` event supersedes the previous binding (`supersedesBindingSeq`); the old binding stays in the history. Whether a host identifier survives resume or restart is unverified and is a probe question (HV-L7), so the ledger never assumes either.
4. **Trust labels.** Every event carries `actor.trust`: `operator` (a person or the operator-invoked CLI), `tool` (a Braid checker or companion hook), `imported` (another tool's state), `model-asserted` (a label supplied by a model through an invoked command). Readers weigh events by trust. A `model-asserted` event is a label, not evidence of ownership or liveness.
5. **Operator-only transitions.** Reassigning a unit's binding to a different host entity (`operator-reassigned`) requires `operator-cli` with trust `operator`. The schema enforces the labels; it cannot authenticate the person (section 6).
6. **Orchestrator, human and shared-tree writers** have no unit. They are `unattributed` writers (SPEC-057) and are **unknown by default**: reported as unknown, never blamed on a unit, never silently excluded; only a path under an explicit declared exemption rule is excluded, and the export names the rule.
7. **No model-callable surface.** The ledger is written through operator-invoked CLI subcommands and companion hook scripts. SPEC-059 adds no MCP tool and no skill script that issues anything. A model that runs a CLI subcommand through Bash writes a `model-asserted` or `tool` event under the same bounds as any other writer; the event stays advisory.

## 2. Concurrency

### 2.1 Model

A single ledger per repository (identified by a digest of the canonical Git common directory, so every worktree of one repository shares it), stored **outside any working tree** in a private directory (mode 0700, files 0600, owned by the user, no symbolic links, canonical existing parent), following `agent_braid/tooling_coordination.py` and `docs/tooling/COORDINATION.md`: one POSIX file lock (`fcntl`), atomic writes, fsync, bounded size, refusal of aliases and permissive modes.

### 2.2 Rules

1. **Writers are serialized by one exclusive lock**, taken non-blocking. A competing writer receives `busy`: no action occurred and nothing was queued. Retrying is the caller's explicit choice; the ledger never retries, queues or blocks. (Same discipline as the plugin MCP admission lock, which is per process and is not a cross-session lease.)
2. **Order is `seq`.** `seq` is assigned while the lock is held and is the only ordering the ledger relies on. Wall-clock time (`recordedAt`) is advisory and used only for expiry hints; clock skew and clock changes cannot reorder events.
3. **Append-only.** An event is one JSON line, appended and fsynced under the lock. Existing lines are never rewritten except by the explicit compaction of section 4.
4. **Readers.** A reader takes a non-blocking shared lock, reads a prefix that ends at a complete line, validates it, and reports `busy` rather than waiting. A reader that finds a torn final line ignores it, reports `tornTailDetected`, and does not repair. A busy, unreadable or over-bound ledger ends the command with a command error (the SPEC-057 `command-error.schema.json` shape, extended by reference with the ledger codes below: a code, a nonzero exit and no result object); a refusal is never a result and is never read as clean, while `unverified` and `unknown` inside a produced result are Article 13 outcomes and are also never clean.
5. **Bounds (proposed).** Event at most 8 KiB; strings and paths at most 256 characters; at most 512 paths per unit and 64 per attributed-write batch; at most 32 units per run and 8 open runs; active log at most 4 MiB and 16384 events; snapshot at most 1 MiB. Beyond a bound the write is **refused** (`ERR-LEDGER-FULL`, `ERR-OVER-BOUND`); nothing is truncated or dropped.
6. **Platform.** macOS and Linux with POSIX locking on a local filesystem. Where `fcntl` is unavailable the ledger refuses to start (`ERR-PLATFORM-NOT-SUPPORTED`); there is no emulation. A network or synchronized-folder filesystem is outside the tested boundary and is **not detected**; the operator is told (HV-L8 records the behavior on the founder's filesystems).
7. **Hook latency.** A hook that reads or writes the ledger must finish within its host timeout and fail soft: a busy, unreadable or full ledger yields no output, never a block, and records a `failed` or `suppressed` delivery state where it can. Latency percentiles are measured and reported; the threshold is to be fixed before any run (proposed p95 not above 200 ms for the read path).
8. **The ledger is not the MCP.** Continuous use goes through the CLI and companion scripts at tool boundaries and quiescent checkpoints, not through the plugin MCP, whose admission lock is global and non-blocking. The ledger never writes the plugin registry.

### 2.3 Claims under concurrency

A claim is recorded with `claim-recorded` (declared paths as a digest and a count, plus the digest of an opaque token returned to the caller). Two units whose declared paths overlap are both recorded; the overlap is reported as a `claim-overlap` hazard in a notice. The ledger never refuses a claim because another exists (advisory), and never grants exclusivity.

## 3. Idempotency

1. **Every write has an idempotency key**, supplied by the caller or derived from (kind, runId, subject, epoch). The key space is per ledger.
2. **Replay.** The same key with the same payload digest returns the original event and appends nothing. The same key with a different payload digest is refused (`ERR-IDEMPOTENCY-CONFLICT`). A missing key on a write that requires one is refused.
3. **Window.** The ledger remembers the most recent 4096 keys (proposed). A replay older than the window cannot be recognized and is appended as a new event; the contract states this and does not claim exactly-once.
4. **Notice ids are deterministic** from (runId, epoch, hazard kinds, units, data digest). The same hazard at the same epoch deduplicates; a changed snapshot produces a new epoch and a new notice that **supersedes** the old one by an explicit link.
5. **Delivery is at-least-once with receiver-side deduplication.** A receiver-side component records `delivery-observed` per (noticeId, transport, receiver session). Before injecting it checks for an earlier `injected` record for the same triple and suppresses duplicates (`suppressed-duplicate`), and suppresses expired (`suppressed-expired`), superseded (`suppressed-superseded`) and over-rate (`suppressed-rate-limit`) notices. After a resume or compaction the same notice may be seen again; the check handles it.
6. **No acknowledgement claim.** `injected` records that the component handed text to the host for its own session. The host does not acknowledge it, a model may ignore it, and the ledger never records a notice as read, heeded or acted on.
7. **Back-pressure (proposed).** At most one injection per receiver per 30 seconds, at most 1500 characters and 5 hazards per injection, newest epoch only, the remainder summarized as a count with a pointer to the pull command. A burst is coalesced, never queued without bound.

## 4. Recovery

Recovery in this contract reconstructs a **view** of the ledger and lists what is orphaned. It performs no repair of the world: no claim is reclaimed, no session is resumed, restarted, messaged or deleted. Integration recovery stays with SPEC-052 and the owned runtime; the SPEC-057 recovery report remains the source for worktree state.

### 4.1 Failure matrix

| Failure | State left behind | Detection | Required behavior |
|---|---|---|---|
| Writer crashes before appending | Nothing | None needed | Retry with the same key is safe |
| Writer crashes during append | A torn final line | Final line fails to parse or lacks a newline | Readers ignore it and report `tornTailDetected`; `ledger-verify` is read-only; an explicit operator command `ledger-quarantine-tail` moves the torn bytes to a side file and appends `recovery-note: torn-tail-quarantined`; never deletes |
| Writer crashes after append, before reporting | Event present, caller unaware | Replay with the same key | Returns the original event |
| Lock holder dies | The OS releases the `fcntl` lock | None needed | No stale-lock repair exists; a lock file left on disk is not a held lock |
| Two writers race | One gets the lock | `busy` | The loser receives `busy`; nothing is queued |
| Hash chain breaks (edit, truncation, restore) | `prevHash` mismatch | `ledger-verify` | Report `hashChain: broken` and the first bad `seq`; mark the ledger `unverified`; consumers fall back to pull and treat claims as `unknown`; no automatic repair |
| Clock jumps | `recordedAt` out of order | Compare with `seq` | Order by `seq`; record `clock-skew-observed`; expiry hints are advisory |
| Agent or session dies mid-run | A claim with no further events | Heartbeat age, operator-supplied `claude agents --json`, quiescent Git state | Append `claim-suspected-stale` with the basis; **do not release**; the recovery view lists it and any overlap with live units; only `operator-reassigned` or `claim-released` by the owner token or the operator changes ownership |
| Usage-limit stop, laptop sleep, host restart | Same as above, possibly all units | Same | Same; a restarted agent binds a new host identity (section 1.2.3) |
| Compaction crashes | A partial snapshot | Snapshot digest does not match the marker | The old log remains authoritative; the marker is appended only after the snapshot is fsynced and verified |
| Ledger deleted or restored from backup | Missing or older state | Absent file or lower `seq` than a receiver last recorded | Report `unknown`; claims are not reconstructed from memory of a model; `restore-from-backup` is recorded by the operator |
| Disk full or over bound | Write refused | Error code | Refuse, never truncate; pull remains available from what exists |
| Hook errors or times out | Nothing injected | Host-defined | Fail soft: no block, no partial output, a `failed` delivery state if recordable |
| Receiver compacts or resumes | Notice context lost | Delivery check on next hook | Re-inject only if still valid and not already `injected` for this receiver and epoch |
| Sender and receiver disagree on state | Different views | Epoch comparison | The newer epoch wins; an older epoch is stale and is suppressed |

### 4.2 Compaction

Compaction is an explicit operator command. It writes a snapshot of the live state (claims, bindings, pending notices, the idempotency window) to a new private file, verifies its digest, then appends a `compaction-marker`. It never discards the information needed to answer "who was bound to this unit and when" for the current run. The retention of closed runs is the operator's choice (section 6).

## 5. Delivery

Decided by the founder on 2026-10-24 (round 2) and recorded here as the frame of the contract; it is not an acceptance of this contract.

1. **Default: Mailbox + Whisper.** The **Mailbox** is the pull notice (data in the ledger or the SPEC-057 hazard notice) that the orchestrator reads with `ledger-inspect` or a notice file; the host already wakes the orchestrator at the end of each turn of a linked session. The **Whisper** is `PreToolUse` `additionalContext` to the affected agent in its own session, a SPEC-058 companion output. Always available, always the fallback. The SPEC-059 notification companion ships no hook for it.
2. **Opt-in strategies, SPEC-059 only.** The **Megaphone** (a companion monitor or channel server) and the **Doorbell** (a script posting data only to the orchestrator's **own** session messaging socket) are opt-in. They are enabled only if G1 shows late notices with measurable harm (a recorded G1 observation under the late-notice-harm measure CN2 of the G1 proposal, which names how an arm with earlier notice differs from the pull arm, the observation unit and a threshold; CN2 has no pass or fail effect, so until a G1 record cites it these strategies stay disabled), G2 is adopted, the ADR is adopted and the companion is installed. The Doorbell additionally needs a transport verified by a receipt pinned after G2 adoption and an ADR that reframes the rule "Agent Braid never messages as a session" for it (data only, to the orchestrator's own socket, as the operator's tooling and not as a session, labelled as data).
3. **Receiver-side only.** Every push transport is a component that runs in or for the receiving session and hands a bounded digest to that same session: a companion monitor, a companion channel server, or a script posting to the orchestrator's own session socket. Agent Braid never writes to any other session's socket and never calls a session-messaging tool. A notice authored by the checker therefore reaches another session only because that session's own component chose to read and inject it.
4. **Settings.** `notificationMode`, `notificationStrategy` and `guardMode` are owned by SPEC-057's `orchestration-settings` schema (most specific scope wins; a `block` at repository or user scope is a floor; operator-owned). SPEC-059 adds `pushTransports` and `killSwitch` under `extensions.SPEC-059` (`push-settings.schema.json`) and resolves them; it redefines no scope. The resolved delivery is coherent by construction: `pushStatus` `active` holds if and only if the effective mode is `push`, with a transport and a receipt (an `active` state with effective mode `pull` is rejected; see `push-resolution-active-while-pull.invalid.json`).
5. **Push is effective only when all hold:** this contract and the ADR are adopted (G2); the strategy is `megaphone` or `doorbell`; a G1 late-notice-harm record exists; for the Doorbell the ADR reframing is adopted and a receipt pinned after G2 adoption passes; the companion component is installed (installing it is the opt-in); at least one transport of the requested strategy has a passing probe receipt on the running host version; the ledger verifies; the platform is supported; the kill switch is off. Otherwise the effective mode is `pull`, the effective delivery is the Mailbox and every unmet condition is named from the closed list. A requested push that cannot be honored is never reported as active.
6. **Transport status.** The documentation-level candidates, their strategy, owner, gates and evidence status are in `transport-matrix.json`. All are unverified; none is selected; two (monitor, channel) are experimental or research previews.
7. **Strings are data.** Every repository-derived string in a notice is escaped, bounded and placed only in a labelled data field; instruction fields come from a closed list. Delivered text begins with the data label. The SPEC-057 escaping and bounding rules are reused unchanged: one named character set (Unicode categories Cc and Cf, C1 controls, U+2028 and U+2029, tag characters, and the bidirectional set of the G1 protocol) is rejected or escaped, and a final line feed is rejected by an anchor that does not treat it as an end (a plain `$` does under Python). Any pattern in a SPEC-059 schema uses that anchor; the receipt path of `push-settings.schema.json` is restricted to a conservative ASCII set.

## 6. Security, privacy and retention

1. **Content-free.** The ledger stores identifiers, repository-relative paths, digests, counts and closed vocabularies. It never stores file content, command text, prompts, transcripts, tool output or secrets. The attributed-write recorder hashes a file after a write when it can read it; the hash, not the content, is stored.
2. **Private and out of Git.** Mode 0700 directory and 0600 files, outside every working tree, never added to Git, never published, never uploaded.
3. **Tamper evidence, not authentication.** The hash chain detects accidental damage and naive edits. It does not authenticate the writer: the same user account, including a guarded agent running Bash, can rewrite the file and recompute the chain. Protecting control paths from the guarded agent is the job of SPEC-058's guard and the host's permission and sandbox settings. This contract therefore treats the ledger as **advisory evidence** and lets no safety property depend on its integrity.
4. **Telemetry.** Deferred; nothing is collected now. A later additive SPEC-047 vocabulary is possible only after SPEC-047 and ADR 0025 are adopted and the producing feature ships, with aggregate families only (hook or gate duration buckets could one day cover companion hook latency); granularity is no. A never-collect list is part of this contract as an exclusion with planned validator tests: paths and hashes, branch, ref and commit identifiers, prompts, messages and transcripts, free text, unit and pair identities, sub-day timestamps, exact durations, tokens and costs, exact model and host builds, per-user bypass and false-block counts, and anything from the G0 or G1 manifests.
5. **Retention and deletion (a stated precondition of G2, not an open question).** The ledger holds identifiers, repository paths of every write and session identifiers, so this rule must be stated before adoption; the proposed rule is: open runs are kept until closed; a closed run's events are kept until the operator purges them with the explicit `ledger-purge` command (which deletes only the named closed run's events from the active log after a verified compaction); nothing is purged automatically; the founder may amend the rule in the adoption record but may not adopt the contract without one.
6. **Host listings.** From an operator-supplied `claude agents --json` file only a closed field list is read (`id`, `sessionId`, `kind`, `state`, `status`); `name`, `waitingFor` and `cwd` are never persisted or echoed (a directory may be stored only as a digest in a `unit-bound` event). From host settings files, if ever read, only a closed key list is read and no other value is stored.
7. **Injection.** Repository text may carry instructions aimed at a model. Strings are escaped (the single named character set of section 5.7 removed or escaped), bounded to 256 characters, and never placed in an instruction field; adversarial fixtures must leave instruction fields byte-identical.

## 7. Compatibility and versioning

Schemas carry `agent-braid-*/v0.1` identifiers and are additive within a major version. Unknown members are rejected. The ledger adds no field to AIM `0.2.0-draft`, no change to `agent_braid/analysis.py`, no MCP tool and no change to existing grants, limits or skills. The ADR 0024 wording (no installation or session hooks in the main plugin; five unchanged product skills) is untouched: any hook, monitor or channel component is an opt-in companion whose packaging is an ADR decision.

## 8. Conformance statements (to be tested only if G2 opens)

Each statement is a future test target. Only C9 is checkable now, against the kept schema and fixtures (validation procedure 002); the others are planned after G2 and an ADR.

| # | Statement |
|---|---|
| C1 | Every ledger event is strict and content-free; unknown members, content-bearing members and `executionAuthorization` other than `false` are rejected (an event schema is drafted if G2 opens). |
| C2 | Concurrent writers across processes are serialized; a loser gets `busy` and no action occurs; `seq` is gapless and unique. |
| C3 | Unsupported platforms and unsafe locations are refused, not emulated. |
| C4 | Identity is never authority; bindings are late and superseded, not overwritten; only the operator reassigns; unattributed writers are unknown by default; `unattributed` is a reserved word that a unit declaration (SPEC-057 validator) must not use. |
| C5 | A claim never blocks and is never reclaimed automatically; staleness is a suspicion with a stated basis. |
| C6 | Replays are idempotent; a key reused with another payload is refused; notice ids are deterministic. |
| C7 | Each row of the failure matrix has a test or a recorded reason it cannot be tested offline. |
| C8 | Delivery states never claim read or acted on; duplicates, expired and superseded notices are suppressed; digests are bounded. |
| C9 | Push is effective only under the conditions of 5.5 and otherwise falls back to the Mailbox with every unmet condition named; `active` implies effective mode `push`; settings compose with SPEC-057 through the versioned extension and redefine no scope. |
| C10 | No Agent Braid code writes to another session's socket or calls a session-messaging tool. |
| C11 | Any attributed-write export is partial by construction and never yields an independent candidate. |
| C12 | The ledger stores no content and is outside the working tree and Git; nothing is collected by telemetry. |
| C13 | A refusal is a command error with no result object; an unreadable ledger never yields a view. |

## 9. Decisions

### 9.1 Recorded on 2026-10-24 (round 2; binding planning decisions, not adoption of this contract)

1. The default strategy is Mailbox + Whisper; the Megaphone and the Doorbell are opt-in in SPEC-059 only, enabled only under the gates of section 5.2.
2. Settings precedence: the most specific scope wins; a `block` set at repository or user scope is a floor; settings are operator-owned. These are SPEC-057 rules that SPEC-059 extends.
3. G2 is decided after G1, and opens for planning only after gate GN passes. Companion names and distribution are decided after G1; the notification and ledger companion is separate from `agent-braid-guard` (working names, same marketplace, publication only with release acceptance).
4. Interoperation is documentation now; import adapters wait for demand or G1 evidence.
5. The attributed-write ledger for agent teams is decided after probe HV-L7; otherwise guidance is documentation plus per-teammate checkpoints. No `PostToolUse` Bash observer is specified now.
6. Telemetry is deferred (section 6.4).
7. Host probes are launched by the orchestrating Claude session through workflows or derived sessions after the founder authorizes each probe; agents prepare log-only scripts; evidence is pinned with the host version.

### 9.2 Still only the founder can take

1. **Open or not open G2.** Adopt this contract (amended), defer it, or reject it, after G1 and only if GN passed. Whether an inconclusive GN may ever support opening G2 is a question for the G1 proposal before its freeze (the proposal says a pass is needed).
2. **Doorbell ADR reframing.** The exact wording of the reframed rule.
3. **Bounds, hook latency threshold and the retention amendment** marked proposed above.
4. **Ledger location** default (a per-user state directory keyed by repository digest) and whether `CLAUDE_PLUGIN_DATA` is acceptable.
5. **The kill-switch floor interpretation** (section 5.4) and the identifier of a "conversation" scope (SPEC-057 owns the scope).
6. **Whether the attributed-write recorder ships at all**, after HV-L7.
7. **Whether to import** mcp_agent_mail or Gas Town state at all, after demand or G1 evidence appears.
