# Implementation plan

1. Extract the schedule-to-`tracked-tree-v1` observation as a private, pure
   helper used by replay result classification; reject malformed internal
   schedule states rather than silently classifying them.
2. Keep the serialized evidence, public CLI, schemas and source Git state
   unchanged. Add focused equivalence, divergence, incomplete and regression
   tests against the existing replay behavior.
3. Run proportional and PR validation, freeze obtained evidence and request
   scoped founder review. Record external validation as pending.
