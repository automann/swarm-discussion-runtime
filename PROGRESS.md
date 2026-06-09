# Progress Ledger

This file is the project memory for implementation rounds. It is deliberately
not a release changelog. Each entry records what changed, how it maps to
`ROADMAP.md`, what was verified, and whether the work still follows the
runtime discipline borrowed from `codex-agenteam`.

## Entry Template

Use this shape for every future implementation round:

```text
## YYYY-MM-DD - <short task name>

- Commit: <sha or pending>
- Roadmap alignment: <phase and acceptance item>
- Work summary: <what changed>
- Verification: <commands and result>
- Failure coverage: <bad-input / edge-case tests added or why not applicable>
- AgenTeam review: <compare with artifact-first runtime, progress, trace/evidence,
  scope containment, and design-drift principles>
- Drift status: <ON TRACK | WATCH | OFF TRACK> with reason
- Next: <next natural task>
```

## 2026-06-09 - Phase 0 Skeleton And Guardrails

- Commit: `418d9f7 chore: scaffold runtime incubator`
- Roadmap alignment: Phase 0, skeleton and guardrails.
- Work summary: Created the greenfield runtime repository structure, governance
  docs, minimal CLI, package skeleton, fixtures/reference placeholders, and
  skeleton contract tests.
- Verification: `python3 runtime/swarm_rt.py health`,
  `python3 runtime/swarm_rt.py planned-commands`, and skeleton tests passed.
- Failure coverage: Minimal at this phase; no protocol edge cases existed yet.
- AgenTeam review: Aligned with the `codex-agenteam` pattern of explicit runtime
  primitives and artifact-backed state rather than a long parent prompt. The
  repo intentionally did not copy AgenTeam's role pipeline.
- Drift status: ON TRACK. The incubator boundary is explicit and Phase 0 does
  not try to solve packaging, marketplace, or autonomous execution.
- Next: Build fan-in and validation hardening before prompt or WAL work.

## 2026-06-09 - Local Python Test Environment

- Commit: `1db5600 chore: ignore local virtualenv`
- Roadmap alignment: Phase 0 verification support.
- Work summary: Created a local `.venv`, installed `pytest`, and ignored
  `.venv/` in Git.
- Verification: `.venv/bin/python -m pytest` passed.
- Failure coverage: Not applicable; environment-only change.
- AgenTeam review: Aligned with AgenTeam's final-verification habit by making
  repeatable local verification cheap.
- Drift status: ON TRACK. No runtime semantics changed.
- Next: Continue Phase 1 implementation.

## 2026-06-09 - Phase 1 Fan-In And Validation Runtime

- Commit: `5898e51 feat: add phase 1 fan-in validation runtime`
- Roadmap alignment: Phase 1 deliverables: `collect-merge`, partial wait-result
  fixtures, strengthened `validate-round`, and `validate-discussion`.
- Work summary: Added `runtime/swarm/collect.py`,
  `runtime/swarm/validation.py`, Phase 1 fixtures, CLI commands, and tests for
  partial fan-in, relation enum validation, and session-log-free discussion
  directory validation.
- Verification: `.venv/bin/python -m pytest` passed with 15 tests.
- Failure coverage: Covered incomplete `wait_agent` batches, invalid relation
  labels, missing summary, stale partials, leftover tmp, and missing artifacts.
- AgenTeam review: Matches AgenTeam's local runtime discipline: host outputs are
  normalized into durable artifacts, validators are product code, and raw host
  logs remain secondary evidence.
- Drift status: ON TRACK. The parent agent no longer needs to manually demux
  partial wait results or hand-check round artifacts for these cases.
- Next: Strengthen Phase 1 with adversarial failure tests before moving on.

## 2026-06-09 - Phase 1 Failure Edge Coverage

- Commit: `0eec122 test: add phase 1 failure edge coverage`
- Roadmap alignment: Phase 1 hardening and Runtime Acceptance failure behavior.
- Work summary: Added failure tests for bad wait shapes, duplicate/incomplete
  poll updates, ambiguous fallback matches, timeouts, ID gaps, unresolved
  references, invalid `positionShifts`, and invalid shift provenance.
- Verification: `.venv/bin/python -m pytest` passed with 24 tests.
- Failure coverage: This round explicitly focused on bad inputs and edge cases.
- AgenTeam review: Aligned with AgenTeam's review and scope-audit posture:
  runtime commands should fail loudly with machine-readable reasons rather than
  silently repairing ambiguous state.
- Drift status: ON TRACK. The failure matrix reduces subjective implementation
  drift by pinning behavior in tests.
- Next: Implement Phase 2 context summary and prompt-build artifacts.

## 2026-06-09 - Phase 2 Context And Prompt Builders

- Commit: `fe0bb70 feat: add phase 2 context prompt builders`
- Roadmap alignment: Phase 2 deliverables: `context-build`, `prompt-build`,
  prompt-build JSON schema, and fixtures for declaration, argumentation,
  response, and fixed-role phases.
- Work summary: Added context summary generation, prompt-build request handling,
  prompt artifacts, response full/gist visibility, prompt schema, fixtures, and
  CLI commands.
- Verification: `.venv/bin/python -m pytest` passed with 33 tests. Manual CLI
  checks wrote context and prompt artifacts under `/tmp/swarm-runtime-phase2-check`.
- Failure coverage: Covered missing objective, unknown phase, invalid message
  IDs, and schema visibility contract. Declaration prompts are tested as blind
  even when peer messages are present.
- AgenTeam review: Aligns with AgenTeam's artifact-first model by writing
  reviewable prompt artifacts and hashes. It also follows the trace/evidence
  direction by recording injected IDs and visibility instead of leaving prompt
  construction implicit in parent context.
- Drift status: WATCH. The current prompt builder is intentionally small and
  deterministic, but future phases must keep checking it against real smoke
  artifacts so it does not become an invented protocol detached from legacy
  discussion behavior.
- Next: Before Phase 3 WAL work, preserve progress/review cadence so future
  agents continue comparing work against the roadmap and AgenTeam design.

## 2026-06-09 - Progress Ledger And Drift Review Cadence

- Commit: this commit.
- Roadmap alignment: Cross-cutting guardrail for all phases.
- Work summary: Added this progress ledger and updated agent operating rules so
  every future round records roadmap alignment, verification, failure coverage,
  AgenTeam review, drift status, and next task.
- Verification: Documentation diff and Markdown formatting check.
- Failure coverage: Process-level change; failure mode addressed is context
  compression or accumulated-window drift, not runtime input.
- AgenTeam review: Directly adopts the relevant AgenTeam discipline: progress
  snapshots, artifact references, trace/evidence thinking, scope containment,
  and explicit design-drift review. It intentionally does not adopt AgenTeam's
  full role pipeline because this repository is a runtime primitive incubator.
- Drift status: ON TRACK. This change makes future drift easier to spot during
  review and acceptance.
- Next: Continue Phase 3 WAL Runtime Core with the new ledger and review
  checklist active.
