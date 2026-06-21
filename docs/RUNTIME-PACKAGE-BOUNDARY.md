# Runtime Package Boundary

This document defines the in-process ownership split between skill prompt,
host adapter, and runtime. It applies to every host adapter built against this
runtime; repo-level topology, vendoring, and certification live in
`docs/ADAPTER-SPEC.md`.

The machine-readable source of truth is `runtime-contract.json`.

## Contract Check

Before a plugin or host adapter depends on the runtime command surface, run:

```bash
swarm-rt runtime-contract
```

The command emits the contract manifest and a validation report. A non-zero exit
means the plugin should not continue with a discussion run.

## Ownership Split

Skill prompt owns:

- Collecting the user's brief and intent.
- Selecting a mode or asking the user for missing high-level input.
- Calling runtime commands.
- Presenting evidence summaries back to the parent agent.

Skill prompt must not construct prompts, demux wait results, mint message IDs,
mutate WAL state, cite unvalidated tool evidence, or carry full discussion
history in parent context.

Host adapter owns:

- Spawning host agents.
- Waiting for host results.
- Calling `transport-init`, `transport-append-batch`, and `transport-collect`
  with host-produced ids and wait batches.
- Calling runtime gates such as `validate-host-step`, `adapter-smoke`, and
  `validate-loop`.
- (v0.3.0) Projecting per-topic custom-agent files, writing
  `projection-manifest.json`, and cleaning those files up (zero-residue) — the
  runtime cannot see the host agent directory, so actual deletion is the
  adapter's release gate.

Host adapter must not construct prompts, demux wait results, mint message IDs,
mutate WAL state, or decide audit health.

Runtime owns:

- Context summaries and prompt-build artifacts.
- Transport artifact writes, fan-in merge, and host transport validation.
- WAL mutation, checkpointing, and finalization.
- Directory, round, capability, trace, evidence, adapter smoke, and loop
  validation.
- (v0.3.0) Projected custom-agent provenance: preserving `agentDescriptor`,
  and validating `customAgentProjection` + the projection-manifest shape and
  run-scoped naming (`validate-loop [--require-projection]`).

Runtime must not spawn host agents, wait on host agents, own parent conversation
orchestration, install plugins, or manage marketplaces.

## Stable Commands

The stable plugin-facing commands are listed in `runtime-contract.json` under
`commands`. The current required command set is:

```text
context-build
prompt-build
collect-merge
transport-init
transport-append-batch
transport-collect
append-message
checkpoint
finalize-round
trace
evidence
validate-host-step
adapter-smoke
validate-loop
```

Additional stable helpers such as `runtime-contract`, `resume-plan`,
`validate-round`, `validate-discussion`, and `capability-doctor` are also part of
the manifest. `collect-merge` remains the pure merge primitive; plugin flows
should prefer `transport-collect` when they want the standard
`collect-result.json` artifact written.

## Integration Gates

The plugin should treat these commands as gates:

- `validate-host-step`: after `transport-init`.
- `adapter-smoke`: after `transport-collect`.
- `validate-loop`: before accepting a completed fixture or live discussion as a
  minimal complete loop.

## Stable Artifact Paths

The runtime contract records stable artifact paths for context, prompts,
transport, rounds, capabilities, trace, and evidence. Plugin code should pass
paths to runtime commands instead of reading and reinterpreting these artifacts
inside skill prompt text.

## Vendoring Rule

Adapters consume this runtime by vendoring the bundle at a pinned SHA with
`scripts/vendor.py` (see `docs/ADAPTER-SPEC.md`). The vendored tree is
read-only; updating means re-vendoring and re-certifying, never editing in
place.

Do not paste runtime semantics into `SKILL.md`. The skill should remain a thin
operator guide over the package boundary.
