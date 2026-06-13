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

## 2026-06-09 - Runtime Plugin Contract

- Commit: this commit.
- Roadmap alignment: Runtime/plugin package boundary after adapter smoke. This
  makes the plugin integration surface explicit before migration back to the
  published `swarm-discussion` line.
- Work summary: Added `runtime-contract.json`,
  `schemas/runtime-contract.schema.json`, `runtime-contract` CLI validation,
  `runtime/swarm/contract.py`, and `docs/RUNTIME-PACKAGE-BOUNDARY.md`. The
  contract identifies stable runtime-owned commands, adapter-facing commands,
  integration gates, boundary responsibilities, forbidden runtime
  responsibilities, and stable artifact paths.
- Verification: `.venv/bin/python -m pytest` passed with the full test suite.
- Failure coverage: Added tests rejecting missing adapter gates, host-owned
  stable commands, and host responsibilities leaking into runtime.
- AgenTeam review: This follows AgenTeam's config/validation pattern: publish a
  manifest, validate it with runtime code, and keep executor/host behavior
  outside the command contract. It does not add an executor facade or mutate
  discussion state.
- Drift status: ON TRACK. The plugin boundary is now machine-readable, which
  should prevent future skill-prompt drift during integration.
- Next: Use this contract to prototype the published plugin-side wrapper that
  invokes the runtime CLI against the minimal v2 fixture.

## 2026-06-10 - Runtime-Owned Transport Artifacts

- Commit: this commit.
- Roadmap alignment: Adapter/plugin migration follow-through. This removes
  another manual parent-agent responsibility by making the runtime own the
  transport artifact package around host spawn/wait primitives.
- Work summary: Added `transport-init`, `transport-append-batch`, and
  `transport-collect` as stable runtime commands. The helpers write
  `host-step.json`, `spawn-order.json`, `wait-batches.jsonl`, and
  `collect-result.json` through validated, runtime-owned paths while preserving
  host responsibility for actual spawn and wait operations.
- Verification: targeted transport and runtime-contract tests passed; full
  suite should be run after vendoring into the Codex plugin.
- Failure coverage: Added tests for empty spawn order, path traversal phases,
  append-before-init, non-object wait batches, missing transport artifacts, and
  incomplete fan-in that still writes a diagnostic `collect-result.json`.
- AgenTeam review: This keeps the executor facade thin in the same spirit as
  AgenTeam: the host provides ids and raw batches, while the runtime owns the
  durable artifact protocol and validation surface. It does not add runtime
  spawning or waiting.
- Drift status: ON TRACK. The contract now names transport artifact helpers, so
  plugin prompts have less room to reintroduce ad hoc JSON handling.
- Next: Vendor these runtime changes into the Codex plugin wrapper and replace
  skill instructions that ask the parent agent to write transport files by hand.

## 2026-06-10 - Full-Repo Review Hardening Round

- Commit: this commit.
- Roadmap alignment: Cross-phase hardening against the Phase 1-6 acceptance
  invariants plus the Phase 3 round-monotonicity item that had no enforcement.
- Work summary: A full review against ROADMAP/ACCEPTANCE found and fixed
  verified invariant violations across the runtime. Fan-in: the persona
  fallback matcher could assign one agent's payload to two specs and report a
  fan-in complete while a required agent never responded; fallback matches are
  now consumed once, conflicting duplicate payloads are flagged, and
  still-running agents count as missing. WAL: `checkpoint` could resurrect a
  finalized round (then `append-message` wrote into committed state and
  `resume-plan` chose the stale partial); writes now refuse finalized rounds,
  reject state/round-id mismatches, enforce sequential round ids, survive
  corrupt state files with structured errors, and mint message ids correctly
  past sequence 999. Validation: position shifts must cite at least one
  trigger, name their expert, and be provable against a non-empty
  personaContextLog; unhashable JSON values no longer crash validators; null
  container fields error instead of silently coercing; round file names must
  match their roundId. Host adapter: empty `{}` sections no longer bypass
  host-step validation, and artifact paths must stay relative inside the
  discussion directory (checked again at smoke-replay resolution). Smoke: fixed
  an operator-precedence bug that failed all single-object `.json` wait
  results, and an empty stored collect-result no longer skips the replay
  comparison. Transport: corrupt artifacts produce structured errors,
  re-initializing a phase with a different spawn order while wait batches exist
  fails loudly, and the phase-name regex no longer accepts trailing newlines.
  Audit: unreadable collect-results mark transport incomplete, capability-gate
  failures report `outcome.result: unverified` instead of `completed`, manifest
  errors are no longer double-reported, and trace survives corrupt partials and
  non-numeric round ids. Capabilities/contract: profile errors are not
  double-counted, records under an invalid profile are not reported accepted,
  schema-required profile fields are enforced, command-spec `responsibilities`
  are type-checked (no more `set(str)` char-splitting bypass), and the
  top-level `forbiddenRuntimeResponsibilities` list is validated. CLI: all
  input loading emits structured JSON errors instead of tracebacks, artifact
  outputs are written atomically, `trace` gained `--output` to honor the
  contract's stable-artifact claim, and `planned-commands` lists itself.
  Drift cleanup: minimal-v2 trace/evidence anchors are now real CLI output that
  conforms to `schemas/evidence.schema.json`, `validate-loop` checks evidence
  content instead of file existence, and ARCHITECTURE/README/fixtures docs
  match the implemented command surface and artifact shape.
- Verification: `.venv/bin/python -m pytest` passed with 155 tests (was 103).
  Every README Quick Check command runs clean. A new end-to-end test drives the
  documented CLI pipeline (`context-build -> transport-init -> prompt-build ->
  transport-append-batch -> transport-collect -> append-message ->
  finalize-round -> trace/evidence/validate-loop`) on a fresh directory.
- Failure coverage: This round was failure coverage. 52 new pinning tests
  cover double-assigned fan-in payloads, conflicting duplicate payloads,
  checkpoint-after-finalize, round-id mismatches, non-sequential rounds,
  corrupt WAL/transport/prompt inputs, message ids past 999, trigger-less and
  expert-less shifts, empty context logs, unhashable reference targets, null
  container coercion, empty host-step sections, traversal artifact paths, stale
  wait batches, schema-incomplete evidence anchors, and CLI structured-error
  output.
- AgenTeam review: Strengthens exactly the disciplines this repo borrowed:
  validators fail loudly with stable machine-readable codes instead of
  crashing or silently repairing, WAL state transitions are now explicit and
  guarded, and evidence summaries no longer misreport transport or capability
  status. No role pipeline, executor, or packaging scope was added.
- Drift status: ON TRACK. Remaining known gaps are external-input items, not
  code: real legacy smoke fixtures are still absent, and the plugin-side
  wrapper that calls the runtime has not been built.
- Next: Import at least one real legacy discussion artifact as a fixture, then
  build the plugin-side wrapper that drives one lightweight phase through these
  primitives.

## 2026-06-11 - Phase 7 Runtime-As-Source-Of-Truth Foundations

- Commit: this commit.
- Roadmap alignment: New Phase 7 (host adapter split). Also closes two
  long-open completion items: "real legacy smoke fixtures are represented"
  and "trace/evidence works on at least one real discussion artifact".
- Work summary: Decision recorded: instead of evolving the merged plugin tree
  in `swarm-discussion`, the runtime repo becomes the host-agnostic source of
  truth with one adapter repo per coding agent (built by that host's native
  agent) and `swarm-discussion` rebuilt as a thin aggregator of certified
  releases. This round laid the runtime-side foundations: imported three real
  discussions from the published plugin line into `fixtures/legacy/`
  (one complete, two incomplete-and-diagnosed); imported the byte-identical
  protocol semantics docs from `swarm-discussion@96eb5f2` into `protocol/`
  with a legacy-mechanics-to-runtime-command mapping; added
  `scripts/vendor.py` (pinned-SHA vendoring with hash manifest, drift and
  unmanifested-file detection, self-sufficient bundle including the minimal-v2
  fixture); added `conformance/certify_adapter.py` (contract + vendor-manifest
  + adapter-smoke + validate-loop + validate-discussion verdict) and
  `docs/ADAPTER-SPEC.md` defining adapter deliverables, the entry-contract
  must-nots, and the certification bar.
- Verification: `.venv/bin/python -m pytest` passed with 166 tests. The real
  `tauri-vs-electron-kanban` discussion validates clean and traces
  on-track/none; vendor/verify round-trips and detects tampering; the
  certification kit passes on the minimal-v2 fixture against both the local
  and a vendored runtime, and fails on a corrupted discussion.
- Failure coverage: New tests pin incomplete real discussions being diagnosed
  (not accepted), vendored-tree drift and unmanifested files failing verify,
  and certification failing on a broken collect-result.
- AgenTeam review: This adopts the AgenTeam disciplines at the repo-topology
  level: a contract-validated core, manifest-pinned distribution, and
  certification gates instead of cross-agent code review. The role pipeline is
  still not copied; adapters stay thin shells per NON_GOALS.
- Drift status: ON TRACK. The runtime did not change this round; only
  fixtures, protocol docs, distribution tooling, and specs were added.
- Next: Build `swarm-discussion-claude` natively (first adapter, per
  decision), certify it against a real Claude-driven discussion, then hand
  `docs/ADAPTER-SPEC.md` plus the salvaged wrapper reference to Codex for
  `swarm-discussion-codex`.

## 2026-06-11 - Governance Refresh For Source-Of-Truth Role

- Commit: this commit.
- Roadmap alignment: Phase 7 cross-cutting guardrail. The repository's
  responsibilities changed (incubator -> host-agnostic source of truth), so
  the governance docs that steer every future agent round had to change with
  them before adapter work begins.
- Work summary: Rewrote `AGENTS.md` for the steward role: three new
  non-negotiable principles (single-copy protocol/runtime semantics, the
  adapter-facing surface as a public contract changed only with
  contract/spec/schema/tests together, vendored-bundle self-sufficiency), new
  boundaries (no host-specific code, no distribution packaging, keep
  `scripts/vendor.py` BUNDLE and `docs/ADAPTER-SPEC.md` in sync), and replaced
  the spent First Proof Point section with the Phase 7 standing bar.
  Restructured `ACCEPTANCE.md`: first proof point marked met and pinned,
  standing runtime acceptance updated to the hardened invariants, a new
  Source-Of-Truth Acceptance section, adapter milestone checklist, expanded
  falsifiers (vendored-file patching, gates-pass-but-hosts-break, per-host
  semantic divergence), and the incubator completion definition retired to a
  historical record with per-item status. `ARCHITECTURE.md` gained the
  repository topology with a per-repo owns/must-not-own table and a
  Distribution And Versioning section. `NON_GOALS.md` rewritten for the new
  topology: Not A Host Adapter, Not The Distribution Repo, Not A Per-Host
  Fork Farm; legacy sections retained. README intro/status updated from
  incubator language to the steward role; `docs/RUNTIME-PACKAGE-BOUNDARY.md`
  reframed as the in-process ownership split with the migration rule replaced
  by the vendoring rule.
- Verification: `.venv/bin/python -m pytest` passed with 167 tests, including
  a new governance drift-guard test asserting the docs reference the real
  spec/vendor/certification artifacts and keep the topology sections.
- Failure coverage: Process-level change. The drift guard fails loudly if a
  future round deletes the adapter spec, vendor script, certification kit, or
  the topology/non-goal sections the governance now depends on.
- AgenTeam review: Keeps the AgenTeam-inspired governance discipline current
  with reality: the operating contract, acceptance bar, and non-goals now
  describe the actual repository role, so drift review in future rounds
  compares against the right target. No role pipeline or packaging scope was
  added.
- Drift status: ON TRACK. No runtime or protocol semantics changed; only
  governance and one drift-guard test.
- Next: Scaffold `swarm-discussion-claude`, vendor the runtime at the current
  SHA, implement the thin wrapper and Claude skill per `docs/ADAPTER-SPEC.md`,
  and certify against a real Claude-driven discussion.

## 2026-06-11 - Verified Sub-Agent Nesting; Nested-Orchestrator Topology

- Commit: pending (verification + docs round; not yet committed).
- Roadmap alignment: Phase 7 host-adapter split. A Claude Code capability that
  changes the adapter's execution topology was verified before building the
  first adapter, and the governing docs/plans were updated to match.
- Work summary: Empirically verified that Claude Code 2.1.177 sub-agents can
  spawn their own sub-agents (the old `agents.max_depth = 1` cap is gone).
  Evidence: (a) a control sub-agent's tool set includes `Agent`; (b) a
  root-spawned coordinator spawned two worker sub-agents whose unpredictable
  tokens appeared only in their own separate transcripts (depth 2); (c) a
  three-role chain reached depth 3, proven by child-before-parent completion
  ordering in a shared log, correct returned data, distinct per-agent
  transcripts, and orchestrator telemetry showing it did not do the work
  itself. Depth >= 3 covers all realistic adapter needs; the documented
  5-level ceiling was not pinned because the only instrument for it
  (self-propagating chains) is correctly refused by capable agents — itself a
  design constraint now recorded. Updated `docs/ADAPTER-SPEC.md` (new
  Execution topology: parent -> orchestrator sub-agent -> personas -> optional
  researcher; orchestrator + persona agent deliverables split; entry-contract
  must-nots for no-self-replication and personas-must-not-nest; host nesting
  capability gate + doctor probe), `docs/FUTURE-EXECUTORS.md` (verified-nesting
  section; coordinator unblocked from root-thread constraint; depth-3 readonly
  researcher now reachable), and re-scoped `plans/001` P1 -> P2 with a note in
  `plans/README.md` (verbose stdout now pollutes a disposable orchestrator
  context, not the user's main thread).
- Verification: nesting proven via transcripts + ordered logs + correct data
  (not agent self-report). `.venv/bin/python -m pytest` re-run after the
  docs-only changes to confirm the suite is unaffected.
- Failure coverage: not applicable (no runtime code changed). The probe's two
  refusals of self-replicating prompts are captured as an adapter design rule.
- AgenTeam review: stays within scope — this round verified a host capability
  and updated specs/plans; it added no host-specific code, no packaging, and
  no runtime semantics. The orchestrator-as-sub-agent topology is the cleanest
  realization of the "parent agent is not the runtime" principle.
- Drift status: ON TRACK. The verification strengthens the Phase 7 direction
  rather than changing it; the runtime core is untouched.
- Next: Scaffold `swarm-discussion-claude` (vendor at the current SHA, thin
  spawn-the-orchestrator skill, swarm-orchestrator + swarm-expert agents,
  doctor with a nesting probe) and certify it against a real Claude-driven
  discussion.

## 2026-06-11 - First Adapter Certified (swarm-discussion-claude)

- Commit: this entry (the adapter itself lives in the swarm-discussion-claude repo).
- Roadmap alignment: Phase 7 adapter milestone + ADAPTER-SPEC deliverable 6.
- Work summary: Scaffolded the Claude adapter in a separate repo (thin
  spawn-the-orchestrator skill, swarm-orchestrator agent that nests persona
  sub-agents, swarm-expert persona, runtime-discovery wrapper with a host
  nesting probe, runtime vendored at bed47da). Drove one real lightweight
  discussion end to end through the nested orchestrator topology and certified
  the produced artifact tree. Checked the swarm-discussion-claude box in the
  ACCEPTANCE adapter-milestone list.
- Verification: conformance/certify_adapter.py CERTIFIED=True against the
  adapter's vendored bundle and a real discussion (all five gates:
  runtime-contract, vendor-manifest, adapter-smoke, validate-loop,
  validate-discussion). 20 runtime commands ok; depth-2 persona spawning
  confirmed.
- Failure coverage: certification runs the strict validators against a real
  (non-fixture) discussion; the run surfaced and fixed one orchestrator bug
  (manifest status must be set to completed for on-track / nextAction:none).
- AgenTeam review: in scope — runtime core unchanged; adapter integration
  validated through existing gates. The orchestrator-as-sub-agent topology
  keeps mechanics out of the parent context (the founding goal).
- Drift status: ON TRACK. First adapter certified; Codex adapter and the thin
  aggregator remain.
- Next: Codex adapter (built by Codex from ADAPTER-SPEC), then rebuild
  swarm-discussion as the thin aggregator. Optionally land runtime plans
  002/001 and re-vendor so the orchestrator can use init + metadata derivation
  + compact output.

## 2026-06-11 - Auto-Push Cadence + Codex Adapter Handoff

- Commit: this entry.
- Roadmap alignment: Phase 7 — enabling the Codex adapter build and workflow.
- Work summary: Validated the swarm-discussion-claude plugin-install path
  (`claude plugin validate` passes; `--plugin-dir` registers both namespaced
  agent types + the skill; the real `swarm-discussion:swarm-expert` spawns and
  returns), and fixed the orchestrator to spawn the namespaced persona type
  (committed in the adapter repo). Adopted an auto-push cadence (push committed
  work to origin/main after each work turn without asking) and recorded it in
  AGENTS.md here and in the adapter. Wrote `docs/CODEX-ADAPTER-HANDOFF.md`: a
  self-contained build spec for Codex to build `swarm-discussion-codex`
  (topology fork on `max_depth`, deliverables, Codex host specifics,
  build+certify steps, entry contract, pitfalls).
- Verification: `claude plugin validate` (pass); headless `--plugin-dir`
  registration + real persona spawn (pass). Docs/workflow round otherwise.
- Failure coverage: n/a (docs / workflow).
- AgenTeam review: in scope; no runtime code changed. The handoff is
  host-specific onboarding referencing the agnostic spec, not adapter code.
- Drift status: ON TRACK. First adapter certified + install-validated; Codex
  handoff ready.
- Next: Codex builds `swarm-discussion-codex` from the handoff; then the thin
  aggregator.

## 2026-06-11 - Plan 001: Compact CLI Output Contract

- Commit: this entry.
- Roadmap alignment: plans/001. Reduces orchestrator/parent context burden from
  verbose CLI stdout (the founding context-pollution complaint).
- Work summary: Added `emit_summary` plus a `--full` flag to every
  `swarm_rt.py` subcommand. Each command now prints a compact summary envelope
  by default (`ok` + the keys an orchestrator needs + artifact paths); full
  payloads stay in artifacts and behind `--full`; failures always print the
  full `errors`. Fixed the prompt-build stdout leak (full prompt text no longer
  printed). Updated CLI tests that read full-payload internals to use `--full`
  or compact keys, added `tests/test_cli_output_contract.py`
  (no-leak / size-caps / `--full`-escape / fail-loud), documented the contract
  in ADAPTER-SPEC + HOST-ADAPTERS.
- Verification: `.venv/bin/python -m pytest` 172 tests pass (167 + 5 new).
  trace compact stdout ~195B, evidence ~545B.
- Failure coverage: contract test pins fail-loud (full errors without `--full`)
  and the no-leak invariant.
- AgenTeam review: CLI-layer change only; library return values unchanged
  (callers/tests still receive full dicts). Artifact-first discipline preserved.
- Drift status: ON TRACK.
- Next: plan 002 (finalize derives metadata + init command). NOTE for the
  re-vendor step: the adapter wrapper calls `runtime-contract` and reads the
  full `contract` — after re-vendoring this runtime it must call
  `runtime-contract --full`.

## 2026-06-11 - Plan 002: finalize derives metadata + init command

- Commit: this entry.
- Roadmap alignment: plans/002. Removes parent JSON-assembly the architecture
  forbids; adds the missing scaffold primitive.
- Work summary: `finalize-round` now derives `metadata` (messageCount,
  referenceCount, participants) and `timestamp` from the round when the caller
  omits them, via `_derive_round_metadata`; caller-supplied values pass through
  untouched so the validator still catches inconsistent input (no silent
  repair). Added `init_discussion` + the `init` CLI command (scaffolds the
  discussion dir + manifest, fails loud on re-init or bad id), added it to
  `runtime-contract.json` (adapterFacing) and the adapter-facing list. The
  fresh-loop e2e now uses `init` and supplies only topic/mode/synthesis to
  finalize.
- Verification: `.venv/bin/python -m pytest` 177 pass (172 + 5 new). init +
  derivation smokes pass; runtime-contract still validates with `init`.
- Failure coverage: tests pin derivation-when-absent, no-overwrite of supplied
  metadata (metadata_mismatch), already_initialized, and invalid_discussion_id.
- AgenTeam review: keeps validators strict (derivation happens before
  validation, never repairs supplied data); init is a thin scaffold, not
  orchestration.
- Drift status: ON TRACK.
- Next: plan 003 (enforce JSON schemas in tests).
