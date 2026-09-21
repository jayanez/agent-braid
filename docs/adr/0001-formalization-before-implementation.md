# ADR 0001: Formalization before production implementation

- **Status:** accepted
- **Date:** 2026-09-13
- **Deciders:** Juan Antonio Yáñez García
- **Constitutional articles:** 3, 13, 23, 24

## Context

Agent Braid is intended to become both useful agent infrastructure and a credible research program. Prematurely fixing types around a single host, LLM, Git workflow, or metaphor would make later claims ambiguous and portability expensive.

## Decision

M0 defines the semantic objects, evidence hierarchy, experiment protocol, and interoperability drafts before a production runtime is selected or implemented. Small executable models are encouraged when they test definitions, but they do not establish the final architecture.

## Alternatives considered

- **Build a worktree conflict CLI first:** faster demo, but risks reducing the project to file overlap and retrofitting semantics later.
- **Start with a mathematical proof assistant:** rigorous for selected structures, but too early while carrier objects and operational relevance remain unsettled.
- **Start with an MCP server:** useful distribution surface, but protocol concerns would distort the internal semantic model.

## Consequences

Initial visible progress is documentation- and fixture-heavy. In exchange, implementation choices become testable against stable concepts, and scientific claims have explicit boundaries.

## Validation

M0 exits only when two or more host-specific workloads can be represented by the same canonical concepts and the reference validator enforces the foundational repository rules.
