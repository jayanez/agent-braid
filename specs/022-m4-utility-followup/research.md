# Decisions and alternatives

Use current accepted runtime semantics rather than expanding the operation domain. Existing phase overhead is the first question; workload size is registered before measurement. Compare serial/parallel total cost, not only worker overlap. Prefer a serial fallback over unsubstantiated adaptive scheduling. Existing SPEC-021 six-pair descriptive evidence cannot be reused as follow-up evidence.

The selected 1.10 ratio is a proposed practical engineering threshold for founder review, not a statistically justified population effect. Twenty pairs per block make local variation visible; they do not establish independent real-workload benefit. A confirmatory claim needs a separately reviewed population, family sampling and uncertainty protocol. Any future comparator or library version must be checked against primary documentation at experiment time.

Relevant evidence boundaries: SPEC-021 G4 decision; frozen measurement protocol; ADR 0020. Negative, null and inconclusive results remain complete reports. Phase accounting must never justify removing correctness prerequisites.
