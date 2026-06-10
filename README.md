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

Phases 0-6 are complete and hardened: fan-in merge, artifact validation,
context summary, prompt-build, WAL helpers, trace/evidence with capability
summaries, thin host-step validation, capability profiles, transport artifact
helpers, and the machine-readable runtime contract — all behind 160+ tests,
anchored by the minimal-v2 fixture and real legacy discussion fixtures. The
original proof pipeline is pinned end-to-end on a fresh directory:

```text
brief -> prompt-build -> collect-merge -> WAL -> validate -> trace/evidence
```

Phase 7 (host adapter split) is in progress: the protocol package, legacy
fixtures, vendoring tooling, and certification kit have landed. Next are the
per-host adapter repos (`swarm-discussion-claude` first), then the published
`swarm-discussion` repo thins into an aggregator of certified releases.

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
protocol/                 host-agnostic discussion protocol semantics
profiles/                 built-in expert capability profiles
runtime-contract.json     machine-readable plugin/runtime contract
runtime/swarm_rt.py       minimal CLI entrypoint
runtime/swarm/            runtime package skeleton
scripts/vendor.py         pinned-SHA vendoring into adapter repos
conformance/              adapter certification kit
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

- `swarm-discussion`: stable published plugin line and source of real smoke
  artifacts.
- `swarm-discussion-runtime`: isolated incubator for the v2 runtime model.
- `codex-agenteam`: reference architecture for runtime/state/events/prompt/evidence
  discipline, not a role model to copy wholesale.
