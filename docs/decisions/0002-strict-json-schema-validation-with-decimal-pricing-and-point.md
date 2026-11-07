# Strict JSON schema validation with Decimal pricing and point-in-time evaluation

Status: accepted (generated, pending human review)

## Context

Model pricing and capabilities change over time. Storing floating-point numbers introduces rounding anomalies in cost calculations, and missing validation could allow malformed configuration files to corrupt routing or billing.

## Decision

Implement a strict validation parser enforcing decimal strings for token prices, fixed capability vocabularies, exact schema structure without extraneous keys, and pure date-driven point-in-time lookup without clock reads.

## Consequences

Callers get predictable, reproducible evaluations as of any date without network or clock dependencies, with precise Decimal arithmetic and typed CatalogErrors.
