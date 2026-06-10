# swarm-discussion-runtime

Greenfield runtime incubator for the next `swarm-discussion` architecture.

This repository is not a replacement plugin yet. It exists to prove the new
runtime model before it is folded back into the published `swarm-discussion`
plugin line.

## Thesis

`swarm-discussion` should be a local discussion runtime, not a long skill prompt
that asks the parent agent to manually execute a protocol.

The parent agent should provide a brief, select a mode, launch host primitives
when necessary, and consume final evidence. The runtime should own prompt
construction, fan-in collection, WAL checkpoints, validation, trace, and
portable evidence.

## Current Status

Phase 6 runtime primitives are underway. The CLI now includes fan-in merge,
artifact validation, context summary, prompt-build helpers, WAL helpers,
trace/evidence with capability summaries, thin host-step validation, and
capability profile reports. The first end-to-end fixture and adapter smoke
command now anchor the smallest complete v2 loop.

The first milestone is not feature parity. It is proving the smallest runtime
pipeline:

```text
brief -> prompt-build -> collect-merge -> WAL -> validate -> trace/evidence
```

## Repository Map

```text
AGENTS.md                 agent operating contract for this incubator
ARCHITECTURE.md           target model and responsibility split
ROADMAP.md                staged implementation plan
PROGRESS.md               per-round roadmap alignment and drift review ledger
ACCEPTANCE.md             proof points and falsifiers
NON_GOALS.md              explicit exclusions
SMOKE-AUDIT-CHECKLIST.md  trace/evidence review checklist
docs/HOST-ADAPTERS.md     Codex and Claude thin host-adapter recipes
docs/RUNTIME-PACKAGE-BOUNDARY.md runtime/plugin ownership contract
docs/CAPABILITY-PROFILES.md expert capability profile contract
docs/FUTURE-EXECUTORS.md  coordinator/executor research notes
profiles/                 built-in expert capability profiles
runtime-contract.json     machine-readable plugin/runtime contract
runtime/swarm_rt.py       minimal CLI entrypoint
runtime/swarm/            runtime package skeleton
tests/                    contract and smoke tests
fixtures/                 phase fixtures and the minimal-v2 e2e loop anchor
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
python3 -m pytest
```

## Relationship To Existing Repos

- `swarm-discussion`: stable published plugin line and source of real smoke
  artifacts.
- `swarm-discussion-runtime`: isolated incubator for the v2 runtime model.
- `codex-agenteam`: reference architecture for runtime/state/events/prompt/evidence
  discipline, not a role model to copy wholesale.
