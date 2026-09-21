# ADR 0003: Copyleft licensing and trademark protection

- **Status:** accepted
- **Date:** 2026-09-14
- **Deciders:** Juan Antonio Yáñez García
- **Constitutional articles:** 16, 21, 25

## Context

Agent Braid is intended to be open infrastructure and a public research program.
The project must permit inspection, use, modification, and commercial adoption
while preventing downstream recipients from closing shared software improvements,
removing required attribution, or presenting an unofficial fork as the original
project.

Copyright licensing and trademark protection solve different problems. An open
source license cannot prohibit commercial use, while a permissive license would
allow proprietary derivatives. Documentation also needs attribution and
share-alike terms suited to research and explanatory works.

## Decision

Software, schemas, executable examples, and automation are licensed under
`AGPL-3.0-only`. Documentation and research are licensed under
`CC-BY-SA-4.0`. The exact path mapping and canonical license texts are maintained
in the repository's `LICENSE` and `LICENSES/` files.

The project also maintains a trademark policy. Copyright licenses do not grant
rights to use the Agent Braid name or visual identity as the primary branding of
a modified distribution, product, or service. Truthful referential use remains
permitted.

Contributions are licensed under the terms applicable to the target material.
A contributor license agreement is not required at this stage.

## Alternatives considered

- **Apache-2.0:** strong adoption and patent terms, but permits proprietary
  derivatives and therefore does not meet the founder's reciprocity objective.
- **AGPL-3.0-only for the entire repository:** simpler, but less natural and less
  explicit for standalone research and documentation reuse.
- **Non-commercial source-available terms:** stronger commercial restriction,
  but incompatible with the project's commitment to genuine open source.
- **No trademark policy:** rejected because copyright attribution alone does not
  adequately prevent confusion about an unofficial fork's origin or endorsement.

## Consequences

Network-deployed modifications to covered software remain subject to AGPL source
availability obligations. Adapted documentation must preserve attribution and
CC BY-SA terms. Some companies may avoid AGPL dependencies or require a separate
commercial license, reducing frictionless adoption while preserving reciprocity.

The policy reserves project identity but does not register a trademark. Formal
registration and jurisdiction-specific enforcement require separate legal work.
The project must maintain a clear file classification as new artifact types are
introduced.

## Validation

Repository validation requires the license map, canonical license texts, notice,
trademark policy, and both SPDX identifiers. Pull requests introducing new
artifact classes must state which licensing category applies.

## References

- [GNU Affero General Public License](https://www.gnu.org/licenses/agpl-3.0.html)
- [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- [Open Source Definition](https://opensource.org/osd)
