# SPEC-028: Data model proposal

DecisionContext binds state digest, operation/resource identities and versions,
declared and observed effects, normalizer/observation contract and capability domain.
DecisionQuestion binds instruction, primitive, ordered stable option IDs and rubric.
DecisionAnswer binds distribution, predicted value, top probability, raw concentration,
calibration/domain support, uncertainty/refusal reason and input coverage.
ModelManifest binds base/tokenizer/head/adapter/backend revisions and licenses.
CalibrationManifest binds labeled construct, eligible population, split hashes,
type/cardinality/language/task groups, fitting algorithm and validation result.
PolicyManifest binds capability, thresholds, risk/budget constraints and fallback chain.
DecisionTrace binds all prior IDs and measured queue/load/render/inference/fallback/
verifier costs. Private text is omitted by default; access and retention are explicit.

Research records additionally bind source rights/windows/eligibility, annotation
attempts and reviewer disagreements, grouped split manifests, negative controls,
candidate/seed/device matrix and missingness. Reuse does not overwrite declarations,
observations, old calibration or historical accepted evidence.

For this feature: Use standard-library immutable records, strict JSON validation and a backend protocol. Keep optional ML imports outside core imports. The first rule backend returns explicit unknown or uncalibrated outputs where it lacks evidence. Implement a feature-local additive CLI namespace only after its contract is reviewed.
