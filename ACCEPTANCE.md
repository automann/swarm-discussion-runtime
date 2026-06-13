# Acceptance Criteria

## First Proof Point (met)

The first implementation proof point was:

```text
brief -> prompt-build -> collect-merge -> WAL -> validate -> trace/evidence
```

Status: PASSED and pinned. `tests/test_e2e_fresh_loop.py` drives the full
documented CLI pipeline on a fresh directory and asserts prompt-build
artifacts, merged fan-in, committed round JSON, directory validation, trace,
and evidence. Treat that test as the guard for this proof point; if it has to
be weakened, the architecture question reopens.

## Runtime Acceptance (standing)

For any fixture or real discussion:

- `collect-merge` reports missing agent ids until all required results exist,
  never reuses one agent's payload for two specs, and flags conflicting
  duplicate payloads.
- Message ids are gapless, round-scoped, and minted only by the runtime.
- Round ids are sequential; finalized rounds cannot be reopened or
  re-checkpointed.
- References resolve to present message ids.
- Relation labels are closed over the allowed enum:
  `supports`, `counters`, `extends`, `questions`.
- Position shifts name their expert, cite at least one trigger, and triggers
  must be provably visible to the persona in full.
- `validate-discussion` catches missing summary, stale partials, leftover tmp,
  and missing artifacts.
- Trace suggests a next action for incomplete or failed discussions.
- Evidence is enough for a smoke audit before opening host JSONL logs.
- Validators fail loudly with stable machine-readable error codes; malformed
  input never produces a traceback or silent repair.

## Source-Of-Truth Acceptance (Phase 7, standing)

This repo is the host-agnostic source of truth for the plugin family. That
claim holds only while all of the following stay true:

- A real legacy discussion (`fixtures/legacy/tauri-vs-electron-kanban`)
  validates clean and traces `on-track` from this repo alone.
- Incomplete real discussions are diagnosed, not accepted.
- The vendored bundle is self-sufficient: the vendored CLI plus the bundled
  minimal-v2 fixture pass the integration gates with no access to this repo.
- `scripts/vendor.py verify` fails on any drifted or unmanifested vendored
  file.
- An adapter built only from `docs/ADAPTER-SPEC.md` and the vendored bundle
  passes `conformance/certify_adapter.py` against a real discussion driven on
  its host.
- Changes to the adapter-facing surface (stable commands, schemas,
  `runtime-contract.json`, bundle contents, certification gates) land together
  with contract, spec, and test updates.

## Adapter Milestones

- [x] `swarm-discussion-claude` certified on a real Claude-driven discussion
      (re-certified 2026-06-11 against runtime `ecd447b`, released as `v0.2.0`;
      nested orchestrator topology, all five certify_adapter gates pass).
- [ ] `swarm-discussion-codex` certified on a real Codex-driven discussion,
      built by Codex from the spec without cross-agent code review.
- [x] `swarm-discussion` rebuilt as a thin aggregator that only accepts
      certified adapter releases (2026-06-11, `v0.2.0`; marketplace pins the
      certified Claude adapter; v0.1 line preserved at the `v0.1.x` tag/branch).
- The published plugin line keeps shipping until the first two boxes are
  checked.

## Falsifiers

Revise the architecture if:

- runtime helpers increase parent-agent context burden instead of reducing it,
- prompt-build artifacts are too noisy to audit,
- evidence cannot prove transport behavior without host logs,
- an adapter must patch vendored runtime files or fork `protocol/` documents
  to work on its host — the source-of-truth model has failed,
- certification passes but real host-driven discussions break in practice —
  the gates are insufficient and must grow before adapter work continues,
- supporting a new host requires changing runtime semantics rather than
  writing a thin adapter — the host-agnostic claim has failed,
- host runtimes expose a stable top-level coordinator that makes this shape
  obsolete,
- the project goal shifts from discussion/decision runtime to autonomous code
  delivery.

## Historical: Incubator Completion Definition

The original incubator exit bar is retained for the record. Every item was
met or consciously superseded:

- the first proof point passes — MET (pinned by the fresh-loop e2e test).
- real legacy smoke fixtures are represented — MET (`fixtures/legacy/`).
- CLI commands are documented — MET (README quick check + ARCHITECTURE).
- core commands have tests — MET (166-test suite, failure-path heavy).
- trace/evidence works on at least one real discussion artifact — MET.
- "the old plugin can call the runtime for one lightweight phase" —
  SUPERSEDED: the integration direction reversed. Adapters vendor the runtime
  (`docs/ADAPTER-SPEC.md`); the old plugin line is fixture and reference
  material until the aggregation repo replaces it.
