# Roadmap

## Phase 0: Skeleton And Guardrails

Goal: establish a clean incubator with hard boundaries.

Deliverables:

- `AGENTS.md`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `ACCEPTANCE.md`
- `NON_GOALS.md`
- minimal `runtime/swarm_rt.py`
- package and test skeleton

Acceptance:

- `python3 runtime/swarm_rt.py health` returns JSON.
- `python3 runtime/swarm_rt.py planned-commands` returns the planned command set.
- `python3 -m pytest` passes.

## Phase 1: Fan-In And Validation Hardening

Goal: close the highest-risk Codex adapter behavior first.

Deliverables:

- `collect-merge` helper.
- partial wait-result fixtures.
- strengthened `validate-round`.
- new `validate-discussion`.

Acceptance:

- Partial `wait_agent` batches are incomplete until all required agent ids are present.
- Relation enum violations fail validation.
- Completed discussion directories can be validated without session JSONL.

## Phase 2: Prompt-Build And Context Summary

Goal: stop hand-assembling prompts in the parent context.

Deliverables:

- `context-build`.
- `prompt-build`.
- prompt-build JSON schema.
- prompt fixtures for declaration, argumentation, response, and fixed-role phases.

Acceptance:

- Prompt-build is deterministic for a fixed fixture.
- Response prompt-build records full/gist visibility for provenance checks.
- Prompt artifacts are sufficient for smoke-audit review.

## Phase 3: WAL Runtime Core

Goal: make round progression helper-mediated.

Deliverables:

- state/event helpers.
- `append-message`.
- `checkpoint`.
- `finalize-round`.
- resume plan.

Acceptance:

- Round ids are monotonic and seeded from WAL state.
- Final flush happens before commit.
- Resume chooses partial over final when appropriate.

## Phase 4: Trace And Evidence

Goal: make artifact-first audit possible.

Deliverables:

- `trace`.
- `evidence`.
- artifact summary schema.
- smoke audit checklist update.

Acceptance:

- A fixture discussion produces trace and evidence.
- Evidence records transport, validation, prompt, and quality summaries.
- Raw host session logs are optional secondary evidence.

## Phase 5: Thin Host Adapter

Goal: preserve current hosts while moving mechanics into runtime.

Deliverables:

- Codex adapter recipe using runtime primitives.
- Claude adapter recipe using runtime primitives.
- host transport metadata schema.

Acceptance:

- A lightweight discussion can be driven with parent context limited to brief,
  current phase, agent ids, and next helper command.

## Phase 6: Capability Profiles And Future Executors

Goal: introduce autonomy only after the runtime can audit it.

Deliverables:

- `expert-basic` profile preserved.
- optional readonly profile spec.
- doctor/report for effective capability profile.
- research notes for future coordinator/executor adapters.

Acceptance:

- Default install still grants no broad tools to ordinary experts.
- Tool-derived evidence cannot be cited unless logged and validated.

## Phase 7: Host Adapter Split

Goal: make this repo the host-agnostic source of truth, with one adapter repo
per coding agent and a thin aggregation repo for distribution.

Deliverables:

- host-agnostic `protocol/` package (single copy of discussion semantics).
- real legacy discussion fixtures under `fixtures/legacy/`.
- `scripts/vendor.py` pinned-SHA vendoring with manifest verify.
- `conformance/certify_adapter.py` certification kit and `docs/ADAPTER-SPEC.md`.
- `swarm-discussion-claude` adapter repo, built and certified natively by
  Claude Code.
- `swarm-discussion-codex` adapter repo, built and certified natively by
  Codex from the spec plus its prior wrapper work.
- `swarm-discussion` rebuilt as a thin aggregator of certified releases.

Acceptance:

- A real legacy discussion validates and traces clean from this repo alone.
- An adapter built only from `docs/ADAPTER-SPEC.md` and the vendored bundle
  passes certification on a real host-driven discussion.
- Neither adapter repo forks protocol semantics or runtime mechanics.
- The published plugin line keeps shipping until both adapters certify.
