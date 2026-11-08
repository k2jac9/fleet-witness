# ADR-0005: Versioned replay and read-only viewer

- Status: Accepted for the initial prototype
- Date: 2026-11-08

## Context

The demo needs inspectable evidence without creating another execution surface or inventing global telemetry.

## Decision

Export schema version 1.0 from committed records. Present scenario, agent policies, paired condition, receipts, recommendation score, execution attempts, and ordered events. Use static HTML/CSS/JavaScript with text-only rendering of untrusted strings. Validate schema and input size. Serve loopback-only using an explicit asset allowlist. The viewer cannot mutate the controller and has no model credentials.

## Alternatives

A live control dashboard creates avoidable authority and authentication requirements. A world map would imply sensors and attribution this prototype does not have. Remote CDN assets would add an unnecessary network dependency.

## Consequences

This is a local replay dashboard. A future authorized sensor feed must distinguish observed, inferred, simulated, and unknown locations and identities. The local database is not served.

## Validation

Inspect a real generated replay. Check keyboard-accessible scenario selection and event stepping. Malformed imports fail visibly; HTML payloads render as text. HTTP requests cannot retrieve the database, secrets, traversal paths, or directory listings.
