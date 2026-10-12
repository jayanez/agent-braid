# Operational subscription capture policy

Status: owner-approved scope on 2026-10-11; additive source implementation and
synthetic controls are present, while operational evidence remains subject to
the tasks below. This policy defines conditions; it
does not authorize launch or capture without exact full-registration approval
and all other required approvals. This is an additive contract for
registration-v5. It does not amend the strict behavior of registration-v1/v2,
subscription-policy-v1, or the existing native-process-route-policy-v2.

## Purpose and boundary

This policy authorizes a bounded technical launch using an authenticated native
Codex or Claude Code subscription route when the process and its operational
quota state can be verified. The provider quota is an operational boundary for
the launched process. It is not a per-internal-request client-side veto and it
does not assert account-wide API billing state. Actual cohort cash remains
unknown until independently verified; verified actual cash remains a separate
acceptance and positive-utility gate.

The additional-spend cap remains EUR 0. No purchase, overage, paid API, paid
fallback, or alternate-provider fallback is permitted. Existing host, build,
configuration, candidate, model, slot, rights, time, token, RSS, disk, human
review, and evidence requirements remain in force. The selected estimated
subscription accounting convention remains a separate estimate route; it is
not actual allocation, provider accounting, or cash. Private price inputs remain
private and must not be copied into public documentation.

## Launch binding and admission

Before launch, the trusted observer must bind all of the following to the
registered slot and candidate:

- the authenticated native subscription route and account namespace;
- host identity and native host build;
- executable identity and digest, effective configuration identity, and exact
  argument vector;
- requested model route and candidate identity; and
- the registered slot identity.

The observer must obtain a fresh authoritative observation that confirms the
route's included quota, remaining quota, credits, extra-usage state, and
auto-recharge state. Admission requires extra usage and auto-recharge disabled,
no API key, no helper credential, no provider override, and no paid fallback
available to the launched process. Missing, stale, conflicting, or
unverifiable values refuse launch. The process must be launched with the
verified identity and configuration; identity or configuration drift stops
the cohort before another launch.

## Bounded supervisor and quota exhaustion

A trusted bounded supervisor polls authoritative quota state during operation
and enforces the registered polling and operation bounds. It stops and refuses
further work when quota is exhausted, the observation becomes stale or
unavailable, route or process identity drifts, a paid control changes, or a
supervisor limit is reached. Unknown quota state fails closed. A refusal or
interruption remains an outcome in its registered slot; it is not retried or
reclassified as success. No path may switch to API credentials, extra usage,
credits, a paid route, or another provider.

The supervisor's operational quota check is not a per-request client veto
implemented by the application. It bounds the provider session and launch
lifecycle; provider-native authorization and the trusted supervisor remain the
enforcement boundary.

## Cash and interpretation

This policy does not claim EUR 0 actual cohort cash and does not require an
independent cash measurement before every internal provider request. Actual
cohort cash remains `unknown`/null until independently verified by an
authoritative source covering setup, every started slot, and completion
reconciliation. Nonzero, incomplete, or unverifiable cash prevents the
acceptance and positive-utility gates from passing. It does not convert
unknown cash into zero or permit spend beyond the EUR 0 additional-spend cap.

The estimated subscription reservation and active-time bound remain separately
reported under the selected estimate route. They may support bounded technical
accounting only; they do not populate actual allocation, provider accounting,
actual cash, full economic completion, or positive utility. Deferred human
reviewer time and fees remain unknown, and the existing human-review and
acceptance gates remain unchanged.

## Versioning and evidence limits

The implementation contract is `agent-braid-m45-operational-subscription-policy-v3`
and the additive registration route is `registration-v5`. These names identify
the intended contract version; they do not establish that implementation,
native observation, registration approval, or capture authorization is complete.
Registration-v1/v2 and subscription-policy-v1 retain their exact prior strict
semantics. The route is not a migration or weakening of historical records.

## Recorded API verification reference

On 2026-10-12 the owner requested that the completed API observations and their
acquisition procedure become the reference for later checks. The
[platform API verification reference](platform-api-verification-reference.md)
records the dated Codex and Claude quota/control observations, the read-only
methods, private evidence location and repeat procedure. Use that route with
existing native authentication when fresh verification is needed; provider
support contact is not the selected method.

This is historical preparation. Codex payment-setting fields and Claude
auto-reload remain unverified. Reuse of the reviewed method does not reuse old
quota as fresh evidence or authorize any launch. All admission, freshness,
isolation, supervision, cash, registration and human conditions above remain
in force. Keep the original receipts private and immutable; retain new API
responses as separate dated observations.

## Operational tasks

These stable tasks track this additive policy. Keep each unchecked until its
paired candidate-bound evidence is independently inspected. Completion does
not itself approve registration, authorize capture, establish actual cash, or
close SPEC-044.

- [ ] OP001: Bind the authenticated native subscription route, account
  namespace, host/build, executable, effective configuration, exact argv,
  model route, candidate, and slot to a launch identity. Evidence must show
  mismatch and missing-field refusals.
- [ ] OP002: Validate fresh-observation parsing and fail-closed behavior for
  included quota, remaining quota, credits, extra usage, and auto-recharge with
  synthetic controls. Authentic authoritative source observation remains a
  separate pending operational requirement. Evidence must show stale,
  unavailable, conflicting, and unknown-state refusals.
- [ ] OP003: Validate policy controls for API keys, helper credentials,
  provider overrides, paid fallback, and alternate-provider routes with
  synthetic negative controls. Authentic verification of the launched
  process's environment and accessible credentials remains a separate pending
  operational requirement.
- [ ] OP004: Implement and validate bounded supervisor polling and refusal on
  quota exhaustion, stale/lost observation, route/configuration drift, or
  supervisor bounds. Retain interrupted slot outcomes without retry or
  success reclassification.
- [ ] OP005: Keep actual cohort cash unknown/null absent independent
  authoritative verification; demonstrate that incomplete, nonzero, or
  unverifiable cash blocks acceptance and positive utility while the
  additional-spend cap remains EUR 0.
- [ ] OP006: Verify registration-v5 composition with the separate estimate
  route, preserved historical v1/v2 validation, unchanged 108-slot roster,
  and unchanged human, candidate, host, resource, rights, and acceptance
  gates.

## Source controls and validation

Focused source controls are `tests.test_tooling_subscription.SubscriptionPolicyTests`
for strict v3 policy/binding, fresh-quota/refusal, and cash-free serialization;
`tests.test_tooling_evaluation.ToolingEvaluationTests` for required v5
schema/108-slot contracts and estimate carry-forward;
`tests.test_tooling_capture.CaptureAdmissionTests` for null
unknown cash, positive-cash refusal, and operational prelaunch admission; and
`tests.test_tooling_supervisor.ToolingSupervisorTests` for
prelaunch/running/completed observations and verifier refusal before stdin or
release. These synthetic controls establish deterministic binding, freshness,
refusal, supervisor-bound, no-fallback, and schema compatibility behavior for
the tested candidate only. Cash/report controls are in `tests.test_tooling_money`,
`tests.test_tooling_full_cost`, and `tests.test_tooling_evaluation_report`.
Their outputs should be candidate-bound receipts
mapped to OP001–OP006. Synthetic controls do not
establish an authentic quota provider, account namespace, process environment,
native host launch, live quota supervision, actual cohort cash, complete
registration approval, or capture authorization. Keep OP002 and OP003 open
until the relevant authoritative native sources are observed and bound; keep
every OP task open until its own acceptance evidence is recorded.
