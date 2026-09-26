# Research decisions

- **Domain:** immutable base-to-commit patches for two to four operations;
  `tracked-tree-v1` observes complete terminal trees only.
- **Independence candidate:** certain supported patches with no transitive
  declared dependency and disjoint changed paths, including directory-prefix
  conflicts. Unknown effects are treated as dependencies.
- **Representative construction:** connected components under legal adjacent
  independent swaps, with a lexicographically first representative. At most 24
  orders are enumerated, so the measurable benefit is fewer Git replays rather
  than cheaper order generation.
- **Exhaustive baseline:** the existing producer builds every schedule, then
  the existing verifier regenerates and checks that bundle. Both passes use the
  same replay implementation; this is a separate verification pass, not an
  independent implementation. Terminal status and observation must agree
  within each component. Raw traces are not quotient observations and remain
  in the full evidence.
- **Alternative deferred:** sleep sets or a changed public evidence schema
  could avoid constructing all orders, but would add proof and verification
  obligations without a measurable need in this four-operation domain.
- **Real-Git reducer fixture:** two base-to-commit patches change the same
  repeated-context line in a 30-line tracked file. Git applies both in either
  order to distinct final trees. A third disjoint patch is redundant, and the
  existing SPEC-015 reducer selects the verified two-operation witness. This
  resolves that narrow positive-path gap without claiming arbitrary-workload
  minimality or semantic effects.
