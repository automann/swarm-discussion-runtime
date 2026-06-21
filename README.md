# swarm-discussion-runtime

Host-agnostic discussion runtime and source of truth for the
`swarm-discussion` plugin family.

This repository started as a greenfield incubator proving the v2 runtime
model. The proof point passed; the repo now owns the runtime mechanics, the
protocol semantics, the artifact schemas, the vendorable adapter bundle, and
the adapter certification gates. It is never folded back into a plugin —
host adapters vendor it at a pinned SHA.

## Thesis

`swarm-discussion` should be a local discussion runtime, not a long skill prompt
that asks the parent agent to manually execute a protocol.

The parent agent should provide a brief, select a mode, launch host primitives
when necessary, and consume final evidence. The runtime should own prompt
construction, fan-in collection, WAL checkpoints, validation, trace, and
portable evidence. Host adapters stay thin shells that map spawn/wait
primitives and call runtime commands.

## Current Status

The runtime is complete and the host-adapter split has shipped. Core mechanics —
fan-in merge, artifact validation, context summary, prompt-build, WAL helpers,
trace/evidence with capability summaries, host-step validation, capability
profiles, transport helpers, and the machine-readable runtime contract — are
hardened behind 200+ tests, anchored by the minimal-v2 fixture and real legacy
discussions. The proof pipeline is pinned end-to-end on a fresh directory:

```text
brief -> prompt-build -> collect-merge -> WAL -> validate -> trace/evidence
```

**v0.3.0 — dynamic custom-agent topology.** Both host adapters are built and
certified on the shared topology: the parent projects per-topic custom expert
agents, a coordinator (background session on Claude, dedicated thread on Codex)
runs the runtime loop and spawns them, and the runtime owns the projection
provenance — a host-agnostic `agentDescriptor` plus a projection manifest,
enforced by `certify_adapter.py --require-projection`. See
`docs/adr/0001-v0.3.0-dynamic-custom-agent-topology.md` and `plans/007`–`008`.

- `swarm-discussion-claude` — certified, released `v0.3.0`.
- `swarm-discussion-codex` — certified, released `v0.3.0`.
- `swarm-discussion` — thin aggregator pinning both certified adapters.

## Topology

This repository is the host-agnostic source of truth. Host adapters live in
separate repos (one per coding agent, owned by that host's native agent) and
vendor this runtime at a pinned SHA via `scripts/vendor.py`. The published
`swarm-discussion` repo becomes a thin aggregator of certified adapter
releases. See `docs/ADAPTER-SPEC.md`.

## Repository Map

```text
AGENTS.md                 agent operating contract for this incubator
ARCHITECTURE.md           target model and responsibility split
ROADMAP.md                staged implementation plan
PROGRESS.md               per-round roadmap alignment and drift review ledger
ACCEPTANCE.md             proof points and falsifiers
NON_GOALS.md              explicit exclusions
SMOKE-AUDIT-CHECKLIST.md  trace/evidence review checklist
docs/ADAPTER-SPEC.md      host adapter contract and certification definition
docs/HOST-ADAPTERS.md     Codex and Claude thin host-adapter recipes
docs/RUNTIME-PACKAGE-BOUNDARY.md runtime/plugin ownership contract
docs/CAPABILITY-PROFILES.md expert capability profile contract
docs/FUTURE-EXECUTORS.md  coordinator/executor research notes
docs/adr/                 architecture decision records (ADR 0001: v0.3.0 topology)
protocol/                 host-agnostic discussion protocol semantics
profiles/                 built-in expert capability profiles
runtime-contract.json     machine-readable plugin/runtime contract
runtime/swarm_rt.py       minimal CLI entrypoint
runtime/swarm/            runtime package skeleton
scripts/vendor.py         pinned-SHA vendoring into adapter repos
conformance/              adapter certification kit
plans/                    landed implementation plans (001-008)
tests/                    contract and smoke tests
fixtures/                 phase fixtures, minimal-v2 e2e anchor, real legacy
                          discussions under fixtures/legacy/
schemas/                  runtime artifact schemas
references/               source-plan and legacy-reference notes
```

## Design Principles

- Parent agent is not the runtime.
- WAL is the source of truth.
- Prompt-build must be artifact-backed.
- Raw Codex/Claude session logs are secondary evidence, not primary evidence.
- Ordinary experts remain no-tools by default.
- No free-form peer-to-peer inbox.
- Legacy code may be used as fixture or reference, not copied as architecture.

## Quick Check

```bash
python3 runtime/swarm_rt.py health
python3 runtime/swarm_rt.py planned-commands
python3 runtime/swarm_rt.py runtime-contract
python3 runtime/swarm_rt.py context-build --brief fixtures/phase2/brief.json --out /tmp/swarm-summary.md
python3 runtime/swarm_rt.py prompt-build --request fixtures/phase2/prompt-requests/response.json --out-dir /tmp/swarm-prompt
python3 runtime/swarm_rt.py collect-merge --spawn-order fixtures/phase1/spawn-order.json --wait-result fixtures/phase1/wait-partial-1.json --wait-result fixtures/phase1/wait-partial-2.json
python3 runtime/swarm_rt.py resume-plan --dir fixtures/phase1/discussions/complete
python3 runtime/swarm_rt.py trace --dir fixtures/e2e/minimal-v2
python3 runtime/swarm_rt.py evidence --dir fixtures/e2e/minimal-v2 --output /tmp/swarm-evidence.json
python3 runtime/swarm_rt.py adapter-smoke --dir fixtures/e2e/minimal-v2
python3 runtime/swarm_rt.py validate-loop fixtures/e2e/minimal-v2
python3 runtime/swarm_rt.py validate-loop fixtures/e2e/projected-minimal-v2 --require-projection
python3 runtime/swarm_rt.py validate-host-step fixtures/phase5/codex-host-step.json
python3 runtime/swarm_rt.py capability-doctor
python3 runtime/swarm_rt.py validate-round fixtures/phase1/discussions/complete/rounds/001.json
python3 runtime/swarm_rt.py validate-discussion fixtures/phase1/discussions/complete
python3 runtime/swarm_rt.py validate-discussion fixtures/legacy/tauri-vs-electron-kanban
python3 scripts/vendor.py vendor --dest /tmp/swarm-vendor
python3 conformance/certify_adapter.py --discussion fixtures/e2e/minimal-v2 --vendored /tmp/swarm-vendor
python3 -m pytest
```

## Relationship To Existing Repos

- `swarm-discussion`: thin aggregator marketplace pinning the certified per-host
  adapter releases (Claude + Codex, both `v0.3.0`). The v0.1 single-repo line is
  preserved at the `v0.1.16` tag / `v0.1.x` branch.
- `swarm-discussion-claude`, `swarm-discussion-codex`: the per-host adapters,
  each vendoring this runtime at a pinned SHA.
- `codex-agenteam`: reference architecture for runtime/state/events/prompt/evidence
  discipline, not a role model to copy wholesale.
