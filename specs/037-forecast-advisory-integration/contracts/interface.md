# Proposed forecast-advice consumer contract v1

`ForecastRequest` and `ForecastResult` are numeric contracts defined in SPEC-035.
`ParallelismAdvice` is a separate finite choice over an immutable deterministic
candidate catalogue. No free-form plan generation, wave editing or grant method.

Advice: contract/capability revision, source/window/resource/manifest/artifact/
transform/cutoff digests, finite candidate IDs and constraints, reference action,
proposed action or abstention, economic rationale with registered units, forecast
summary, numerical uncertainty/coverage status, expiry, cost receipt, precise
reason codes, `evidenceClass: heuristic`, `executionAuthorization: false`.

Initial candidate modes are the existing supported serial/parallel preparation
policies. The reviewed local resource receipt does not introduce a new placement
mechanism. Deterministic ready waves, isolation, final serial publication and
per-step evidence checks remain unchanged. An option not admitted by these rules
cannot appear in the advisory candidate catalogue.

At point of use the host recomputes identities, freshness and constraints. It
obtains any operator grant via the existing external operator path, bound to the
exact selected existing policy/manifest. Forecasts cannot supply grants or reuse
a serial grant for a parallel choice. Missing/inconsistent authority refuses
execution even when a serial economic fallback would otherwise be attractive.

Optional System 1 bridge: pass an immutable versioned numeric summary as approved
state/context for a registered finite-choice capability. Do not insert trajectories
or continuous regression into legacy boolean/choice/score responses. Model option
confidence and nominal forecast interval coverage keep distinct labels. If the
consumer contract is not accepted/available, runtime-only advice works and the
bridge explicitly defers.

Modes: off (default), shadow (reference action only), promoted-exact-capability
(only after distinct accepted utility/adoption records; operator authority still
independent). Candidate score alone cannot switch modes. OOM/timeout/unknown
resource/staleness/drift/unsupported intervals trigger registered refusal or
non-model fallback; semantic unknowns remain unknown. Rollback stops new advice
and preserves each active run's immutable policy, grant and recovery record.
