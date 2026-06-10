# Architecture

## Repository Topology

`swarm-discussion-runtime` is the host-agnostic source of truth. Host adapters
and the published distribution repo are built around it:

```text
swarm-discussion-runtime    this repo: runtime mechanics, protocol semantics,
                            schemas, profiles, vendor bundle, certification
swarm-discussion-<host>     one adapter repo per coding agent, owned by that
                            host's native agent; vendors this runtime at a
                            pinned SHA (scripts/vendor.py)
swarm-discussion            thin aggregation repo: marketplace manifests and
                            release bundles assembled from certified adapter
                            releases
```

| Repo | Owns | Must Not Own |
|---|---|---|
| runtime (this repo) | protocol semantics, runtime mechanics, schemas, profiles, vendor bundle + manifest tooling, certification gates, adapter spec | host-specific skill text or spawn primitives, marketplace/installer packaging, subjective product decisions |
| adapter (`swarm-discussion-<host>`) | host bootstrap, thin wrapper (discovery/doctor/gate delegation), host agent definitions, host-native smoke, read-only vendored runtime | protocol semantics, runtime mechanics, forked validators, edits to vendored files |
| aggregation (`swarm-discussion`) | marketplace manifests, release assembly from certified adapter releases, install docs | protocol logic, runtime logic, adapter logic |

Cross-host consistency comes from `runtime-contract.json`,
`docs/ADAPTER-SPEC.md`, and `conformance/certify_adapter.py` — not from shared
code or cross-agent code review. Each adapter is built and tested by the agent
native to its host.

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
swarm-rt planned-commands
swarm-rt runtime-contract
swarm-rt init
swarm-rt context-build
swarm-rt persona-plan
swarm-rt prompt-build
swarm-rt collect-merge
swarm-rt transport-init
swarm-rt transport-append-batch
swarm-rt transport-collect
swarm-rt append-message
swarm-rt checkpoint
swarm-rt finalize-round
swarm-rt resume-plan
swarm-rt validate-round
swarm-rt validate-discussion
swarm-rt validate-host-step
swarm-rt capability-doctor
swarm-rt validate-loop
swarm-rt adapter-smoke
swarm-rt trace
swarm-rt evidence
```

Commands are added behind tests and fixtures. `init` and `persona-plan` remain
planned until their runtime contracts are proven; everything else above is
implemented.

## Artifact Shape

Target discussion directory:

```text
.swarm/discussions/<id>/
  manifest.json
  progress.md
  events.jsonl
  context/summary.md
  rounds/001.json.partial
  rounds/001.json
  prompts/r001/<phase>/<persona>/prompt-build.json
  prompts/r001/<phase>/<persona>/prompt.txt
  transport/r001/<phase>/host-step.json
  transport/r001/<phase>/spawn-order.json
  transport/r001/<phase>/wait-batches.jsonl
  transport/r001/<phase>/collect-result.json
  capabilities/profile.json
  capabilities/tool-evidence.jsonl
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

## Distribution And Versioning

- Adapters consume the runtime via `scripts/vendor.py vendor --dest ...`,
  which copies the adapter-facing bundle (runtime, schemas, profiles,
  `protocol/`, `runtime-contract.json`, the minimal-v2 fixture) and writes
  `vendor-manifest.json` pinning the runtime git SHA plus a sha256 per file.
- The vendored tree is read-only for adapters; `scripts/vendor.py verify`
  fails loudly on drifted or unmanifested files. Updating means re-vendoring
  from a new runtime SHA, never editing in place.
- `runtime-contract.json: runtime.compatibility` is the compatibility string
  adapters must surface in their release notes alongside the pinned SHA.
- An adapter release is acceptable only with a passing
  `conformance/certify_adapter.py` verdict against a real host-driven
  discussion (see `docs/ADAPTER-SPEC.md`). Re-certify on every re-vendor.

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
