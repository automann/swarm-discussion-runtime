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

Phase 1 runtime primitives are underway. The skeleton CLI now includes
fan-in merge and artifact validation helpers.

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
ACCEPTANCE.md             proof points and falsifiers
NON_GOALS.md              explicit exclusions
runtime/swarm_rt.py       minimal CLI entrypoint
runtime/swarm/            runtime package skeleton
tests/                    contract and smoke tests
fixtures/                 future legacy rounds and wait-result fixtures
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
python3 runtime/swarm_rt.py collect-merge --spawn-order fixtures/phase1/spawn-order.json --wait-result fixtures/phase1/wait-partial-1.json --wait-result fixtures/phase1/wait-partial-2.json
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
