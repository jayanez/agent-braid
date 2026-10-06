# Predeclared deterministic product controls

These files freeze synthetic input and expected control outcomes before SPEC-032
feature implementation. They are prepared data, not executed evidence, test results,
installed capability discovery, accepted interfaces or model/utility validation.
No feature module, evaluator, router, compiler or observation buffer was imported or
executed to create them. Expected classification, scalar values, order, pointer
mapping and buffer outcomes were declared independently from the written contract.
Python stdlib JSON/SHA-256 was used only to serialize and bind those declared values;
it did not produce outcomes by calling the future implementation.

- [metadata-router.json](metadata-router.json): 23 declared en/es, unknown/mixed/
  missing task/tag, stale pin, absent capability, real source, private extra field,
  cancellation/deadline cases. Its synthetic registry body illustrates future
  installed inventory and cannot establish that those modules are installed now.
- [schema-compiler.json](schema-compiler.json): eight full expected positive packets
  and sixteen negative controls. Full expected questions/bindings pin nullable enum,
  explicit ordinal values, scalar types, boolean-enum choice, nested/ref pointers
  and property order. Raw/canonical digests bind these hand-declared mappings.
- [pull-hooks.json](pull-hooks.json): ten record/drain/mutation/refusal sequences,
  three invalid capacities and exact stored metadata allowlists. Input responses
  are manually authored core prevalidation-refusal envelopes with null request
  identity and no answers; their valid digest does not authenticate an evaluation.
- [boundary-controls.json](boundary-controls.json): explicit byte/shape recipes for
  duplicate JSON members, size/depth/question limits, nonfinite costs and oversized
  metadata. Recipes generate only synthetic test input, never runtime work.

For router fixtures the illustrative body is exactly `version`/`routes`; its digest
excludes any digest field. `syntheticManifestBodies` are declared metadata examples,
not learned artifacts or observed installation manifests. Test adapters must replace
this registry with the exact reviewed installed manifest when implementing the
real installed-package check, preserving the expected matching/unavailable outcomes.
No fixture grants execution, selects a neural model, detects a language from text
or establishes support for English/Spanish natural-language interpretation.

Compiler numeric scalar kinds distinguish literal signed integer from binary64
number; booleans remain distinct. Numeric equality rejects `[1, 1.0]` before IDs
are generated. All question/option hashes in positive packets derive from the
explicit pointer/value table under the contract's canonical-byte rule. For a ref,
`schemaPointer` is the original referencing property node and
`resolvedSchemaPointer` is its final local target. Fixtures do not prescribe an
implementation algorithm or permit changed semantics to make a test pass.

`controls` and byte/schema recipes are harness instructions outside feature input;
never send them as additional request/schema/response fields. Fake monotonic times
make exact-deadline refusal deterministic. Lock and cancellation controls must use
barriers/tokens, not arbitrary callback execution or sleep-based timing. `expected*`
fields are assertions, not authority. Some APIs' complete refusal envelopes remain
in the reviewed contract; negative cases assert the precise stated reason and
absence of partial questions/routes/buffer mutation without inventing new fields.

Future focused tests must independently materialize input bytes, call the reviewed
implementation, compare frozen expectations, exercise zero-dispatch spies and
record actual candidate/environment/commands/results. All task/assurance/utility
statuses remain unchanged until that evidence and appropriate reviews exist.
