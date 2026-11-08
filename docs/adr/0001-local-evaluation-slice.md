# ADR-0001: Dependency-free local evaluation slice

- Status: Accepted for the initial prototype
- Date: 2026-11-08

## Context

The first deliverable must be runnable by a solo entrant without external credit, infrastructure, or a long installation. The existing architecture discussion identified an evaluation harness as the fastest testable slice.

## Decision

Use Python 3.11+, SQLite, unittest, and static browser assets. Default to deterministic scripted agents and zero external spend. Record the effect as a database release, not a filesystem copy or network publication. Keep a future model adapter behind the same explicit role inputs and proposal/controller interface.

## Alternatives

Rust throughout is consistent with the owner's long-term preference, but adds integration work before the experiment is established. A distributed service stack adds failure modes without improving this first experiment. Both remain future options.

## Consequences

The baseline demonstrates mechanisms, not real model robustness or process isolation. A later Rust port must pass the same boundary tests. No placeholder API claims or automatic sponsor spending.

## Validation

A fresh checkout runs the demo and tests using Python alone. README states the scripted baseline and unimplemented integrations.
