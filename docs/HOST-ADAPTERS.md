# Host Adapter Recipes

Phase 5 keeps Codex and Claude usable while moving discussion mechanics into
runtime helpers. A host adapter is intentionally thin: it spawns agents, waits
for host results, writes transport artifacts, and calls the next runtime helper.

For the package boundary shared by the skill prompt, host adapters, and runtime,
see `docs/RUNTIME-PACKAGE-BOUNDARY.md` and `runtime-contract.json`.

The host adapter does not construct prompts, demux partial wait batches by
guessing, mutate round state by hand, validate quality, or decide audit health.

## Parent Context Surface

The parent agent may carry only this discussion packet between host steps:

- `briefPath`: path to the compact context summary or brief artifact.
- `phase`: current discussion phase.
- `agentIds`: host identifiers or stable agent names expected in this fan-in.
- `nextHelperCommand`: exact runtime command the adapter should call next.

Everything else must be written as an artifact and loaded by runtime helpers.
In particular, the parent context must not include full discussion history,
generated prompt text, raw wait results, round state, manual demux maps, or raw
host logs.

## Shared Runtime Flow

1. `context-build` turns the user's brief into `context/summary.md`.
2. `prompt-build` creates one prompt artifact per agent for the current phase.
3. The host adapter spawns agents from those prompt artifacts.
4. The host adapter writes `transport/<round>/<phase>/spawn-order.json`.
5. The host adapter writes each wait result batch to
   `transport/<round>/<phase>/wait-batches.jsonl`.
6. `collect-merge` normalizes host batches in declared spawn order.
7. `append-message`, `checkpoint`, and `finalize-round` own WAL mutation.
8. `trace` and `evidence` summarize health and portable audit data.

## Codex Recipe

Codex-specific duties:

- Spawn `swarm-expert` subagents with prompt text produced by `prompt-build`.
- Record the returned `agent_id` values in `spawn-order.json`.
- Poll `wait_agent` until all required `agent_id` values have completed.
- Append every partial `wait_agent` response to `wait-batches.jsonl`.
- Call `collect-merge` with the recorded spawn order and wait batches.

Codex-specific caution: partial batches are expected. Completion must be keyed by
`agent_id`, not by arrival order or persona order. The adapter should treat raw
session logs as optional secondary evidence and rely on runtime artifacts for
primary audit.

## Claude Recipe

Claude-specific duties:

- Dispatch named agents from prompt artifacts.
- Record stable agent names in `spawn-order.json`.
- Collect one or more result batches into `wait-batches.jsonl`.
- Call the same `collect-merge`, WAL, trace, and evidence helpers as Codex.

Claude adapters may use a different host primitive shape, but the metadata file
must still identify the spawn primitive, wait primitive, and result key. The
runtime contract remains the same, so downstream validation and evidence do not
branch on host internals.

## Host Transport Metadata

Each host step should write a `host-step.json` matching
`schemas/host-transport.schema.json`. The runtime validator checks the same
contract:

```bash
swarm-rt validate-host-step transport/r001/response/host-step.json
```

The metadata records where transport artifacts live and how the host identifies
results. It is not a transcript. It references artifact paths instead of
embedding raw outputs.

## Adapter Smoke

After a host adapter writes `host-step.json`, `spawn-order.json`,
`wait-batches.jsonl`, and `collect-result.json`, run:

```bash
swarm-rt adapter-smoke --dir .swarm/discussions/<id>
```

For a single host step:

```bash
swarm-rt adapter-smoke \
  --dir .swarm/discussions/<id> \
  --host-step transport/r001/response/host-step.json
```

`adapter-smoke` validates the host-step contract, replays `collect-merge` from
the recorded spawn order and wait batches, compares the replay with the stored
collect result, then summarizes trace, evidence, capability, and loop status. It
does not spawn agents and does not mutate discussion state.

## Acceptance Check

The Phase 5 acceptance proof is this invariant:

```text
parent context = briefPath + phase + agentIds + nextHelperCommand
```

If a host adapter needs more data, that data belongs in a runtime artifact and
should be consumed through a helper command.
