# SPEC-030: Data model proposal

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

For this feature: A causal backbone with its language-model head removed scores dynamically provided option representations against a final decision representation. A bidirectional encoder alternative scores option markers with shared parameters. Train own heads/adapters. Compare frozen encoders, supervised cross-entropy, ordinal soft targets and narrowly approved distillation; add proper-scoring/reward training only through a separately preregistered ablation. Pointer addressing removes slot-specific weights but does not prove order invariance under causal positions.
