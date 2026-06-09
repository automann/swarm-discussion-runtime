# Architecture

## Target Model

`swarm-discussion-runtime` is a local discussion runtime. It turns a parent
brief into durable, auditable discussion artifacts.

The runtime is not an autonomous agent. It is a set of explicit protocol
primitives that a parent agent, host adapter, or future coordinator can invoke.

```text
parent agent
  -> brief / mode / final decision

host adapter
  -> spawn / wait / close primitives

swarm runtime
  -> state machine
  -> prompt-build
  -> collect-merge
  -> WAL checkpoint
  -> validators
  -> trace / evidence

expert agents
  -> one-shot structured reasoning outputs
```

## Responsibility Split

| Layer | Owns | Must Not Own |
|---|---|---|
| Parent agent | user collaboration, brief, mode selection, final decision | manual prompt assembly, wait demux, JSON artifact construction |
| Host adapter | spawn/wait/close transport mapping and host metadata | discussion protocol semantics |
| Runtime | state machine, prompt-build, fan-in, WAL, validation, evidence | subjective product decision after the discussion |
| Expert | one-shot structured contribution | direct mutation of discussion state |
| Validator | schema/provenance/directory checks | silent repair or hidden normalization |

## Runtime Concept Map

```text
brief
  -> context summary
  -> persona plan
  -> phase prompt-build
  -> host spawn batch
  -> wait batch capture
  -> collect-merge
  -> append/checkpoint
  -> validate
  -> trace/evidence
```

## Runtime Commands

Initial planned command surface:

```text
swarm-rt health
swarm-rt init
swarm-rt context-build
swarm-rt persona-plan
swarm-rt prompt-build
swarm-rt collect-merge
swarm-rt append-message
swarm-rt checkpoint
swarm-rt finalize-round
swarm-rt validate-round
swarm-rt validate-discussion
swarm-rt trace
swarm-rt evidence
```

Only `health` and `planned-commands` exist in the skeleton. Other commands must
be added behind tests and fixtures.

## Artifact Shape

Target discussion directory:

```text
.swarm/discussions/<id>/
  manifest.json
  state.json
  events.jsonl
  context/summary.md
  rounds/001.json.partial
  rounds/001.json
  prompts/r001/<phase>/<persona>/prompt-build.json
  prompts/r001/<phase>/<persona>/prompt.txt
  transport/r001/<phase>/spawn-order.json
  transport/r001/<phase>/wait-batches.jsonl
  transport/r001/<phase>/collect-result.json
  artifacts/trace.json
  artifacts/evidence.json
  artifacts/synthesis.md
  tmp/
```

The WAL round state remains the source of truth for round content. Events,
transport records, prompt artifacts, trace, and evidence are audit surfaces.

## Capability Profiles

| Profile | Tools | Writes | Status |
|---|---|---|---|
| `expert-basic` | none | none | default |
| `expert-readonly` | read/glob/grep if host supports scoped tools | none | future experiment |
| `researcher-readonly` | bounded read/search | evidence ledger only | future experiment |
| `coordinator-root` | runtime helper access through parent/root | helper-mediated artifacts | target internal role |
| `coordinator-agent` | TBD | TBD | future only |

Default experts must stay conservative. Toolful profiles require explicit
opt-in, separate names, and validator support.

## Influences

The main reference pattern from `codex-agenteam` is runtime discipline:

- CLI primitives,
- durable state,
- event logs,
- prompt-build artifacts,
- trace/evidence,
- role/capability contracts,
- contract tests.

The role taxonomy and feature-delivery pipeline are not copied.
