# Developer verified-plan MCP endpoint

Status: implementation increment, qualification pending. This is an opt-in local
software fixture lane, not default host activation or product publication.

Integration prerequisites passed on base `69e7d374`: quick and PR each ran 2,084
tests (2,065 passed, 19 skipped), exit 0, with 2,626 identical inputs. Their
receipts are retained outside this repository in the coordinator's delivery
workspace. They do not validate this subsequent endpoint increment.

## Contract and tasks

- SDK-01 (REQ-002/004, SC-002/004): retain the exact immutable producer decision
  and evidence in CoreRequestContext; factor its existing one-call preparation
  error path into `prepare`. Existing `prepare_core` keeps its tuple return.
  This internal seam is needed because an endpoint must expose complete original
  bodies rather than substitute a final decision with a different digest.
- SDK-02 (REQ-004/005, SC-004/005): add explicit module launch
  `python -m agent_braid.system_one_verified_mcp --owned-root ABSOLUTE_ROOT`.
  It advertises only `agent_braid_verified_prepare`, with exact arguments
  `{requestJson: string}`. The inner existing request remains raw until bounded
  admission. Root authority comes only from launch configuration and the existing
  owned ordinary-repository/fixture-marker gate. Outer JSON-RPC frames use the
  existing bounded duplicate/nonfinite/depth validator before SDK parsing.
- SDK-03 (REQ-002/006, SC-002/006): one RPC shares the original request context,
  CancellationToken and all native budgets through preparation and sealing.
  The response `s1-verified-dev-mcp-v1` includes original producer decision and
  evidence, proposal, ConsumerResult, checked prepared body and final decision,
  plus their distinct digests. Every response has executionAuthorization false.
  `bodyDigests.proposal` hashes the complete proposal body; the native
  `proposalDigest` excludes its own field, as in the unchanged native contract.
  Refusals preserve original reasons; response-size refusal has no dangling
  evidence. SDK response/frame accounting is separate from native usage.
- SDK-04 (REQ-004/005/006, SC-004/005/006): use the real optional pinned SDK 2.3.0
  ClientSession against a stdio subprocess; test EN/ES success, correct defer,
  technical refusal, k0 invalid/k1 valid, malformed inner/outer JSON, root bounds,
  cancellation, timeout, concurrency, repeated requests and cleanup. Core-only
  import checks remain separate. Related fixture views are not independent
  accuracy observations. SDK omissions must be reported as omissions.
- SDK-05 (REQ-005/006, SC-005/006): prepare private Codex/Claude launch examples
  and isolated discovery if supported without model calls. Actual native-host
  tools/call and verified zero-cost routing remain separate pending gates.

## Limits and qualification

The endpoint has one admitted native worker at a time; concurrent calls refuse.
Cancellation signals the same token and awaits owned worker cleanup before
unwinding. The SDK wait cap is 180 seconds, raw request cap 1 MiB, encoded
response cap 8 MiB. The existing bounded outer input independently caps its
JSON-RPC frame at 1 MiB. These are cooperative controls, not hard filesystem
termination or SLA claims. Full evidence is inline; no global evidence cache or
resource chunk service is advertised. There are no execute/recover/grants,
persisted trusted contexts, default catalog changes or learned components.

The exact pinned Python 3.13.11 offline SDK setup failed because the
pydantic-core 2.50.0 cp313 wheel is absent from cache. That lane remains pending.
A separately registered Python 3.12.13 lane resolved and installed all 28 fixed
dependency versions with generated hashes from cache, including real MCP 2.3.0.
No dependency or model download was used; the original failed attempt is retained.
Passing this lane cannot be labeled a passing pinned Python 3.13 qualification.

The coordinator owns runtime/tests and records focused checks and final quick/PR
profiles in new receipt directories. The documentary chat owns local evidence
reconciliation only. Existing historical packets, approvals and task checkboxes
remain unchanged. Human/scientific acceptance, training/calibration, admission,
promotion, global activation, product publication and parity remain pending.
