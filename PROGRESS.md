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

## 2026-06-09 - Phase 3 WAL Runtime Core

- Commit: this commit.
- Roadmap alignment: Phase 3 deliverables: state/event helpers,
  `append-message`, `checkpoint`, `finalize-round`, and resume plan.
- Work summary: Added `runtime/swarm/wal.py`, CLI commands for WAL mutation and
  resume planning, event logging to `events.jsonl`, atomic partial writes,
  flush-then-commit finalization, and `resume-plan` in the command surface.
- Verification: `.venv/bin/python -m pytest` passed with the full test suite.
- Failure coverage: Added tests for invalid relations, finalized-round append
  attempts, missing synthesis on finalize, progress-only ID drift, and stale
  lower-round partials losing to newer finals during resume planning.
- AgenTeam review: Follows AgenTeam's artifact-first state/event discipline:
  durable JSON state files, append-only JSONL events, machine-readable command
  results, and resume behavior derived from local artifacts. It intentionally
  avoids AgenTeam's stage/gate/role pipeline because discussion WAL state is a
  smaller protocol primitive.
- Drift status: ON TRACK. The parent agent can now delegate ID minting,
  partial checkpointing, final commit, and resume choice to runtime helpers
  instead of carrying those mechanics in conversation context.
- Next: Phase 4 trace/evidence should consume the prompt, collect, WAL,
  validation, and event artifacts created so far.

## 2026-06-09 - Phase 4 Trace And Evidence

- Commit: this commit.
- Roadmap alignment: Phase 4 deliverables: `trace`, `evidence`, artifact
  summary schema, and smoke audit checklist.
- Work summary: Added `runtime/swarm/audit.py`, CLI commands for `trace` and
  `evidence`, portable `schemas/evidence.schema.json`, and
  `SMOKE-AUDIT-CHECKLIST.md`. Trace now summarizes validation, prompts,
  transport, WAL/resume, events, quality, artifacts, health, and next action.
  Evidence projects the same local artifacts into a portable audit record.
- Verification: `.venv/bin/python -m pytest` passed with the full test suite.
- Failure coverage: Added tests for missing discussion directories, validation
  failures, incomplete transport collect results, resumable partial WAL state,
  and evidence file-output parity.
- AgenTeam review: Follows AgenTeam's trace/evidence design closely at the
  discipline level: derive diagnostic health and next action from local state
  and events, then project a versioned portable evidence record that references
  artifact paths. It avoids AgenTeam's run/stage/role model and keeps the
  discussion-specific summaries focused on transport, prompts, validation, WAL,
  and quality.
- Drift status: ON TRACK. Phase 4 completes the first artifact-first audit loop
  without requiring raw host session logs.
- Next: Phase 5 Thin Host Adapter should document how Codex and Claude hosts
  call these runtime primitives with parent context limited to brief, phase,
  agent ids, and next helper command.

## 2026-06-09 - Phase 5 Thin Host Adapter Contracts

- Commit: this commit.
- Roadmap alignment: Phase 5 deliverables: Codex adapter recipe, Claude adapter
  recipe, and host transport metadata schema. The acceptance invariant is that
  parent context stays limited to brief, current phase, agent ids, and next
  helper command.
- Work summary: Added `docs/HOST-ADAPTERS.md`,
  `schemas/host-transport.schema.json`, host-step fixtures for Codex and
  Claude, `runtime/swarm/adapter.py`, and a `validate-host-step` CLI command.
  The adapter contract records host primitives and artifact paths while keeping
  prompt construction, fan-in merge, WAL mutation, trace, and evidence inside
  runtime helpers. Also taught `collect-merge` to consume JSONL wait-batch
  streams so the documented host recipe is executable.
- Verification: `.venv/bin/python -m pytest` passed with the full test suite.
- Failure coverage: Added tests rejecting parent-context bloat, missing
  transport result keys, unknown hosts, phase mismatches, and schema drift away
  from the thin parent-context surface. Added a JSONL wait-batch regression test
  so host transport artifacts stay compatible with `collect-merge`.
- AgenTeam review: This mirrors AgenTeam's runner boundary at the discipline
  level: the host runner can invoke tools and persist artifacts, but runtime
  primitives own state, prompt, transition, trace, and evidence semantics. It
  deliberately avoids copying AgenTeam's full pipeline/stage/role model because
  this phase only needs a host transport contract.
- Drift status: ON TRACK. Phase 5 preserves existing Codex and Claude hosts
  while making their allowed context and artifact duties auditable.
- Next: Phase 6 should add capability profile contracts, preserve no-tools
  expert defaults, and prepare future readonly executor notes without granting
  broad expert tools prematurely.

## 2026-06-09 - Phase 6 Capability Profiles

- Commit: this commit.
- Roadmap alignment: Phase 6 deliverables: preserved `expert-basic`,
  optional readonly profile spec, doctor/report for effective capability
  profile, and research notes for future coordinator/executor adapters.
- Work summary: Added `profiles/expert-basic.json`,
  `profiles/expert-readonly.json`, capability and tool-evidence schemas,
  `runtime/swarm/capabilities.py`, the `capability-doctor` CLI command,
  fixtures for valid and invalid tool evidence, and docs for capability
  profiles plus future executors. `expert-basic` remains the default and grants
  no tools.
- Verification: `.venv/bin/python -m pytest` passed with the full test suite.
- Failure coverage: Added tests rejecting default profile tool grants, broad
  tools on ordinary experts, unvalidated tool evidence, and tool evidence for
  disallowed tools, mismatched profiles, or missing artifacts. The doctor
  reports tool-derived evidence as non-citable unless it is logged, validated,
  allowed by the active profile, tied to that profile, and backed by an artifact
  path.
- AgenTeam review: This follows AgenTeam's effective-profile and
  artifact-evidence discipline: resolve and report a small effective
  configuration, reference artifacts by path, and keep runner/executor power out
  of the default path. It does not adopt AgenTeam's write scopes or branch
  isolation yet because ordinary swarm experts still have no broad tools.
- Drift status: ON TRACK. Phase 6 adds autonomy scaffolding without enabling
  autonomy by default.
- Next: Start the next roadmap slice by wiring trace/evidence to surface
  capability profile summaries from real discussion directories, then use a
  smoke fixture to verify the end-to-end audit view.

## 2026-06-09 - Capability Trace And Evidence

- Commit: this commit.
- Roadmap alignment: Phase 6 acceptance follow-through: tool-derived evidence
  cannot be cited unless logged and validated, and default expert installs
  remain no-tools in the trace/evidence audit view.
- Work summary: Wired `trace` and `evidence` to summarize discussion-local
  capability artifacts from `capabilities/profile.json` and
  `capabilities/tool-evidence.jsonl`, with default fallback to built-in
  `expert-basic`. Evidence now includes capability profile, effective tools,
  tool-evidence counts, citable status, and capability artifact paths without
  embedding raw tool artifact payloads.
- Verification: `.venv/bin/python -m pytest` passed with the full test suite.
- Failure coverage: Added tests for missing discussion-local profiles resolving
  to default no-tools, citable readonly evidence, and unvalidated evidence
  forcing `health: at-risk` with `nextAction.kind: inspect_capabilities`.
- AgenTeam review: This extends the AgenTeam-inspired evidence rule directly:
  trace/evidence reference artifacts and effective configuration, while raw
  tool outputs stay behind artifact paths. It still avoids enabling a runner or
  granting tools inside the trace layer.
- Drift status: ON TRACK. The autonomy scaffolding is now visible in audit
  artifacts but remains non-operative by default.
- Next: Build an end-to-end discussion fixture that includes host-step,
  capability, prompt, transport, WAL, trace, and evidence artifacts so the
  runtime can prove the smallest complete v2 discussion loop.

## 2026-06-09 - Minimal V2 Loop Fixture

- Commit: this commit.
- Roadmap alignment: Cross-phase acceptance anchor after Phase 6. The fixture
  proves the smallest artifact-backed runtime loop using the primitives already
  implemented across prompt-build, host adapter, fan-in, WAL, capability,
  trace, and evidence.
- Work summary: Added `fixtures/e2e/minimal-v2/` with context summary,
  prompt-build artifacts, Codex host-step metadata, transport fan-in artifacts,
  capability profile and validated tool evidence, final WAL round, events,
  synthesis, and static trace/evidence anchors. Added `validate-loop` as a thin
  verifier for completed fixture directories.
- Verification: `.venv/bin/python -m pytest` passed with the full test suite.
- Failure coverage: Added tests rejecting missing host-step metadata and
  non-citable tool evidence in the end-to-end loop. Existing trace/evidence and
  capability failure tests remain active.
- AgenTeam review: The loop validator mirrors AgenTeam's evidence posture: it
  validates an artifact tree and references summaries rather than executing a
  runner or embedding raw logs. It deliberately stays out of orchestration and
  does not mutate discussion state.
- Drift status: ON TRACK. The runtime now has a concrete fixture anchor that
  should reduce future implementation drift during migration back to the plugin.
- Next: Use the minimal v2 loop as the basis for designing the first real
  adapter-facing smoke command or package boundary for the runtime/plugin
  integration.

## 2026-06-09 - Adapter-Facing Smoke Command

- Commit: this commit.
- Roadmap alignment: Adapter/plugin integration follow-through after the
  minimal v2 loop fixture. The goal is to give Codex and Claude adapters a real
  runtime command they can run after writing host artifacts.
- Work summary: Added `adapter-smoke --dir <discussion-dir>` with optional
  `--host-step`. The command validates host-step metadata, replays
  `collect-merge` from host-step artifact paths, compares replayed fan-in with
  stored `collect-result.json`, and summarizes trace, evidence, capability, and
  loop status without spawning agents or mutating state.
- Verification: `.venv/bin/python -m pytest` passed with the full test suite.
- Failure coverage: Added tests for collect replay mismatch, bloated parent
  context, missing host-step metadata, explicit host-step path handling, and the
  successful minimal v2 fixture path.
- AgenTeam review: This mirrors AgenTeam's separation between executor facade
  and runtime validation: smoke checks host-produced artifacts and projections,
  but it does not dispatch workers, modify state, or depend on raw session logs.
- Drift status: ON TRACK. Adapter integration now has a concrete command-line
  contract instead of an implicit checklist.
- Next: Define the runtime/plugin package boundary so the published
  `swarm-discussion` plugin can call these primitives without copying runtime
  logic back into skill text.
