# Bounded developer SDK endpoint v1 delivery

Status: local engineering acceptance for the finite owned-fixture domain, Python 3.12 SDK and direct Codex MCP calls. This is not release, global activation, general repository readiness or scientific/human acceptance. No product commit or remote publication was performed.

## Implementation and scope

SPEC-031 REQ-002/004/005/006 and SC-002/004/005/006 are addressed by the separately planned developer endpoint increment. The optional lazy MCP 2.3.0 module exposes `agent_braid_verified_prepare` only through explicit `--owned-root` launch. Exact `{requestJson: string}` preserves inner JSON bytes until bounded admission; outer JSONRPC is bounded separately. The consumer's new `prepare()` factors the existing convenience lifecycle without changing its tuple API. Producer getters retain exact original immutable bodies. No frozen contract, default catalog, production policy or legacy behavior is widened.

One request owns one context, cancellation token and aggregate native budget through interpretation, acquisition, selection, handoff revalidation, native prepare, cleanup and sealing. One worker is admitted at a time. SDK cancellation/timeout signals that same token and awaits cleanup; no detached success is published. A monotonic deadline is checked after response encoding. Input is capped at 1 MiB, encoded response at 8 MiB and SDK wait at 180 seconds. These cooperative bounds are not a hard termination or universal latency guarantee. SDK frame/encoding costs are separate from the already immutable native usage fields.

The `s1-verified-dev-mcp-v1` envelope carries complete producer decision/evidence, proposal, consumer result, prepared and final decision bodies, with full-body digests and `executionAuthorization: false`. Native `proposalDigest` excludes its own field; the envelope proposal digest covers the complete body. No missing evidence is replaced by an inaccessible hash. Source acquisition still accepts only marked ordinary descendant owned fixtures, flat `.txt` paths, two to four named operations and the finite grammar; ordinary Python/Markdown/nested repository work is unsupported. No execute, recover, grant, persistent run, ML call, global installation or automatic host registration is introduced.

## Obtained software checks

- Final source composition: 31 tests, zero failures/errors/skips, 117.579 seconds (21 existing Core plus 10 endpoint tests).
- Installed wheel, Python 3.12.13 with real MCP 2.3.0: 10 tests, zero failures/errors/skips, 34.489 seconds; 149 RECORD hashes verified. Eight related EN/ES controls cover answer, defer, refusal and invalid k0 with valid k1; complete bodies/digests verified; child exited zero and was reaped.
- Actual installed Codex 0.163.0-alpha.10.2 app-server invoked the installed endpoint directly for eight related EN/ES controls. Native MCP discovery/call, expected statuses, evidence and k1 selection passed; child exited zero and was reaped. Private config and sandbox denied network; no model turn or inference RPC was sent. Raw stderr records a blocked background Responses websocket connection attempt: absence of network attempts is not claimed.
- Final quick: 2,094 tests, 2,071 passed, 23 skipped; unit 2,091.806 seconds, complete profile 2,271.391145458001 seconds, exit zero.
- Final pr: 2,094 tests, 2,071 passed, 23 skipped; unit 2,087.543 seconds, complete profile 2,267.390424666999 seconds, exit zero.

Both profiles used SDK-less isolated existing dependencies; four new optional SDK cases were skipped there and exercised by the separate installed SDK lane. The other 19 skips are retained in raw logs. Counts overlap and are not independent scientific observations. All 2,629 profiled input hashes equal the installed artifact source registration and current pre-packaging candidate. No tests were rerun to decorate this delivery.

## Failures, review and qualification limits

The first focused attempt ran nine tests with three failures and one error due to incorrect fixture expectations for self-excluded proposal digest and null unmeasured Git command counters; the SDK exception group wrapped the assertion. Attempts remain available. Coordinator review also found and fixed a missing post-encoding deadline guard before the frozen candidate and added a regression check. The corrected attempt passed ten tests before final composition and installed capture. This increment had coordinator review only; earlier Luna T07 does not constitute independent review of this new source.

Pinned Python 3.13.11 environment creation succeeded but offline installation lacked pydantic-core 2.50.0's cp313 macOS wheel. Its qualification remains pending. The separately registered 3.12 lane used cached fixed versions and hash-bound artifacts with no downloads or global installation; it does not satisfy the 3.13 contract.

Claude 2.1.292's first private metadata invocation had a variadic argument ordering error. The corrected invocation could not resolve the dynamic per-session server through static `mcp get`. Both attempts are retained. No Claude tool call, model-driven workflow or zero-cost inference route is claimed. Claude actual-call qualification remains pending; it does not invalidate the separately scoped SDK/Codex proof.

## Acceptance boundary and continuation

Stop refining this finite v1 after the obtained final validation round. Accept it only as a local opt-in engineering component within its declared domain. These controls do not estimate independent decision accuracy, general EN/ES understanding, coverage/productivity in actual development, Laya parity or a hard SLA. Earlier negative native-workflow utility is not erased by software checks. No comparative performance claim follows from different nested/inclusive timing scopes.

The next user-authorized chat will evaluate real current Agent Braid backlog work in an independent lane, preserve unsupported/refused attempts and avoid renaming `.py` or `.md` work as `.txt`. It must register source/route authority and causal observation rules first, use generic analyzers only where supported with separate attribution, and propose a new versioned domain only if actual coverage requires it. The local ten-task RF-T01–RF-T10 forecasting/telemetry supplement is planned, not adopted or implemented. A private admitted lineage ledger stays separate from SPEC-047 numeric identity-free aggregates. Real data must not be mislabeled `authentic-on-synthetic`; compatible permissioned windows and source verification can be reused. Feedback produces evidence and tasks, never automatic fitting or promotion.

Training, calibration, human/scientific review, source/data admission for future observations, promotion, activation and product publication remain pending. No issue/milestone is closed by this packet. External spend for the bounded increment is EUR 0.

## Evidence and preservation

The adjacent evidence packet binds the exact final sources, profiles, selected lossless raw records and artifact. The external completion/readback bind the local source archive and binary patch; they are not published packages. The 2,626 previous candidate files have only the one authorized consumer delta; the three new source/plan files form the 2,629 checked inputs. The original 2,529-file product WIP remains byte-exact. Prior packets and source bindings stay historical; the consumer seam is explicitly superseded, never silently rewritten. Full environments, private runtime homes, credentials and scratch state are excluded.
