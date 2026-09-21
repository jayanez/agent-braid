# Confluence Certificate — Draft 0

A certificate records what was checked and with what assurance. It is not a universal proof unless it references a proof artifact whose assumptions cover the certified instance.

A proof reference must also be checked by a consumer that supports its formal
system; the reference alone proves nothing. This page describes historical 0.1
intent, not fields all enforced by its schema. See [draft 0.2](DRAFT_0_2.md) for
separate evidence variants and consumer verification. Confluence, terminal
agreement, serializability and task correctness are different properties.

## Required content

- schema and tool version;
- certificate and analysis identifiers;
- initial state digest;
- operation identifiers and payload digests;
- declared and observed effects;
- schedules or symbolic rules compared;
- normalizer and observation boundary;
- result: equivalent, divergent, inconclusive, or not applicable;
- assurance level;
- assumptions and excluded domains;
- trace, proof, or counterexample references.

## Example interpretation

If schedules `A,B,C` and `B,A,C` produce the same normalized repository tree and test result in three sandboxed replays, a certificate may state `equivalent-observed` at an empirical or transactional assurance level. It may not state that `A` and `B` commute for every state.

## Content addressing

Certificates should use cryptographic digests for immutable inputs. Digests establish identity, not truth: a perfectly hashed incomplete effect model remains incomplete.

See [the JSON schema](../../schemas/confluence-certificate.schema.json).
