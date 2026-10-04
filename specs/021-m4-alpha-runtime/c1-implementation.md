# C1 verified policy and operator grants

The initial policy revision is owned-operator-grant-v1 and wraps the accepted
serial SPEC-020 runtime. C2 parallel scheduling is not implemented by this cut.

Python imports use agent_braid.runtime_policy: prepare_policy_run,
verify_policy_plan, issue_operator_grant, execute_policy_run and recover_policy_run.
Preparation consumes M2 replay evidence and an advisory plan, independently verifies
both against the same operation/attempt/base identities, then rehearses the serial
manifest. Its canonical plan includes the complete manifest, policy, evidence and
consumer verification. Recompute all bytes at use time; a producer digest is not
verification. Legacy executionAuthorization remains false.

Only a local operator path issues a grant after exact plan acknowledgement. The
trusted owned 0700 store is separate from source/common Git storage and the private
result. Grants are owned 0600 files, purpose-bound, expiring, capacity-limited and
consumed durably under an exclusive POSIX lock before dispatch. No authentication
against hostile same-UID writers is claimed. Partial grant records fail closed.

Consumed grants never dispatch again. A duplicate call independently verifies an
existing completed/prefix/aborted result. A prefix requires a separately issued
resume/abort grant. No run after consumption is an explicit refused/unknown outcome,
not permission to retry execution. Corrupt results are never hidden by idempotence.

CLI commands: prepare-policy-run (request, --run-directory, --evidence,
--advisory-plan), verify-policy-plan (plan), grant-policy-run (plan, --grant-store,
--acknowledge, --action execute|resume|abort, --ttl-seconds), execute-policy-run
(plan, --grant-store, --grant-id), recover-policy-run (same plus --action resume|abort).
Use python -m agent_braid <command> --help. JSON success exits 0; bounded refusal
exits 2; owned Git infrastructure/cancellation exits 3. Grant issuance is an
operator command and must never appear in an MCP tool registry.

Cancellation is checked before each new phase; active M2 verification retains its
existing bounded completion behavior. Runtime stages pass cancellation to owned
Git children. The policy exposes per-stage budgets and does not claim a shared
hard deadline. No source promotion, arbitrary commands or new runtime dependency.

The 18 paired C1 tests and public CLI/schema checks passed; raw output is in
c1-evidence/policy-tests.txt. Whole-M4 closure and independent review are pending.
