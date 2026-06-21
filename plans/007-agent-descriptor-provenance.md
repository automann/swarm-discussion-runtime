# Plan 007: Runtime-owned `agentDescriptor` provenance for projected custom agents

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If a
> "STOP conditions" item occurs, stop and report — do not improvise. When done,
> append a `PROGRESS.md` round entry and update this plan's row in
> `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat <planned-at>..HEAD -- runtime/swarm/transport.py runtime/swarm/collect.py runtime/swarm_rt.py schemas/ tests/`
> If any in-scope file changed since this plan was written, compare the "Current
> state" excerpts against the live code before proceeding; on a mismatch, treat
> it as a STOP condition.

## Status

- **Priority**: P1 (gates the whole v0.3.0 line; ADR 0001 D3)
- **Effort**: M
- **Risk**: MED (changes transport/collect output shapes and a stable schema; additive/optional, so backward compatible — but adapters and fixtures depend on these shapes)
- **Depends on**: none (first v0.3.0 runtime change). Plan 008 depends on this.
- **Category**: feature (v0.3.0 topology)
- **Planned at**: commit `8378415`, 2026-06-21
- **Decision record**: `docs/adr/0001-v0.3.0-dynamic-custom-agent-topology.md`

## Why this matters

v0.3.0 fans out to **dynamic, project-scoped custom expert agents** on both
hosts. The runtime is the source of truth and certification must be able to
prove *which projected custom agent produced which payload* (ADR 0001 D3, and
the Codex P1 in `docs/codex-dynamic-custom-agent-provenance-decision-handoff-20260621.md`).
Today it cannot: `transport.py:_validate_spawn_order` normalizes every
spawn-order entry to `{agentId, persona, token?}` and **drops** any projection
metadata, and `collect-result.json` results carry no link back to a projected
agent. This plan makes provenance runtime-owned and host-agnostic via an
optional `agentDescriptor`, preserved end-to-end. (Schema-shape consumers, the
certification gate, and fixtures land in plan 008.)

## Design (host-agnostic, additive, `schemaVersion` stays 1)

Per spawn-order entry, an optional `agentDescriptor`:

```jsonc
{
  "agentId": "...", "persona": "...", "token": "...",
  "agentDescriptor": {
    "projectedName":   "swarm-<runId>-<roleSlug>",     // required when descriptor present
    "projectedPath":   ".claude/agents/...md | .codex/agents/...toml",
    "projectedSha256": "<64 hex chars>",
    "agentType":       "<host agent type, usually projectedName>",
    "invocationForm":  "explicit_spawn" | "at_mention",
    "promptRef":       "prompts/r001/<phase>/<agent-id>/prompt.txt"
  }
}
```

`host-step.json` gains an optional `transport.customAgentProjection`
`{projected: bool, agentSourceDir: str, count: int}`. `collect-result.json`
results gain the matching `agentDescriptor` beside each `{persona, agentId, result}`.

## Current state (verify against live code)

`runtime/swarm/transport.py` — `_validate_spawn_order` drops everything except id/persona/token:

```python
        seen.add(agent_id)
        normalized_item = {"agentId": agent_id, "persona": persona}
        if item.get("token"):
            normalized_item["token"] = str(item["token"])
        normalized.append(normalized_item)
    return normalized, errors
```

`write_transport_step` builds `host_step["transport"]` with only
`spawnPrimitive/waitPrimitive/resultKey/partialBatches/rawHostLogs` (no
projection block).

`runtime/swarm/collect.py` — `collect_merge` appends results without a descriptor:

```python
        results.append(
            {
                "persona": persona,
                "agentId": actual_agent_id,
                "result": payload,
            }
        )
```

`schemas/host-transport.schema.json` — `transport` already has
`"additionalProperties": true` (so the new block is allowed but undocumented);
`schemaVersion` is `{"const": 1}`. There is **no** `schemas/spawn-order.schema.json`
or `schemas/collect-result.schema.json` today (confirm with `ls schemas`).

`runtime/swarm_rt.py` — the `transport-init` subparser/handler reads the
spawn-order JSON and calls `write_transport_step` (read the live handler before
editing; it is the CLI seam where the descriptor enters).

## Steps

1. **Preserve + validate the descriptor in `_validate_spawn_order`** (`transport.py`).
   - Carry `agentDescriptor` onto `normalized_item` when present.
   - Validate when present: `projectedName` non-empty str (required); `projectedSha256`
     if present matches `^[0-9a-f]{64}$`; `invocationForm` in
     `{"explicit_spawn","at_mention"}`; `projectedPath`/`agentType`/`promptRef`
     non-empty str if present. Emit `_issue("invalid_agent_descriptor", …)` per bad field.
   - Keep all existing normalization/dedup behavior unchanged.

2. **Summarize projection in `write_transport_step`** (`transport.py`).
   - Add an optional `agent_source_dir: str | None = None` parameter.
   - After building `normalized_spawn_order`, if any entry has an `agentDescriptor`,
     set `host_step["transport"]["customAgentProjection"] = {"projected": True,
     "agentSourceDir": agent_source_dir or <dirname of first projectedPath or "">,
     "count": <number of entries with a descriptor>}`. Omit the block entirely
     when no descriptors are present (keeps existing fixtures byte-identical).
   - The block must pass `validate_host_transport_metadata` (it already allows
     `additionalProperties` under `transport`; no schema change strictly required
     for validity, but step 5 documents it).

3. **Attach the descriptor to results in `collect_merge`** (`collect.py`).
   - Build a `descriptor_by_agent_id` and `descriptor_by_persona` map from
     `spawn_order`. When appending a result, include
     `"agentDescriptor": <descriptor for that spawn-order entry>` when one exists
     (match by the resolved `actual_agent_id`, falling back to persona). Omit the
     key when the entry had no descriptor (backward compatible).
   - Do not change `ok/complete/timedOut/missing*` semantics.

4. **CLI seam** (`swarm_rt.py`).
   - `transport-init`: add optional `--agent-source-dir` and pass it to
     `write_transport_step`. The spawn-order JSON the adapter supplies already
     carries per-entry `agentDescriptor`; confirm the handler passes the raw
     spawn-order list through (it does — `_validate_spawn_order` now preserves it).
   - No new top-level command. Keep compact-output contract (plan 001): the
     descriptor lives in artifacts, not stdout summaries.

5. **Schemas.**
   - `schemas/host-transport.schema.json`: document optional
     `transport.customAgentProjection` (`projected` bool, `agentSourceDir` str,
     `count` int ≥ 0). Keep `schemaVersion: {const: 1}`.
   - Add `schemas/spawn-order.schema.json`: array of entries
     `{agentId (req), persona (req), token?, agentDescriptor?}` with the
     descriptor sub-schema from the Design section. `additionalProperties: false`
     on the descriptor; `projectedName` required within it.
   - Add `schemas/collect-result.schema.json` describing `collect_merge` output
     including the optional per-result `agentDescriptor`. (If a partial schema
     already exists, extend it instead.)
   - Add `schemas/projection-manifest.schema.json` (runtime-owned shape, written
     by the adapter, validated by the runtime — ADR 0001 D4/Q4):
     `{runId (req str), createdPaths: [{path, sha256}], deletionStatus:
     enum[pending|clean|partial|skipped|failed], removedPaths[], remainingPaths[]}`.
     Run-scoped-name *enforcement* (every `projectedName` embeds `runId`) and the
     manifest↔descriptor cross-check land in **plan 008's** gate, which has the
     manifest's `runId` available; 007 only defines the schema and keeps the
     descriptor preserved end-to-end.

6. **Tests** (`tests/`), following plan 003's jsonschema conformance pattern:
   - `transport.py`: spawn-order entries with a valid `agentDescriptor` survive
     normalization; bad descriptors (empty projectedName, non-hex sha, bad
     invocationForm) produce `invalid_agent_descriptor`; host-step gains
     `customAgentProjection` iff descriptors present; **no** descriptors → host-step
     byte-identical to pre-plan output (pin the minimal-v2 path).
   - `collect.py`: results carry the matching descriptor; entries without one omit it.
   - schema conformance: a projected spawn-order/host-step/collect-result sample
     validates against the new/updated schemas; a malformed descriptor fails.
   - Backward-compat: the existing `fixtures/e2e/minimal-v2` (no descriptors)
     still passes `validate-loop` and the full suite unchanged.

7. **Verify.**
   - `.venv/bin/python -m pytest -q` → all green (count strictly greater than the
     pre-plan baseline; record the number).
   - `python3 runtime/swarm_rt.py validate-loop fixtures/e2e/minimal-v2` → `ok: true`
     (proves the no-descriptor path is untouched).
   - `python3 runtime/swarm_rt.py runtime-contract --full` → `ok: true`.

## STOP conditions

- The no-descriptor `minimal-v2` host-step/collect-result output changes in any
  byte (regression for existing adapters/fixtures) — stop; the change must be
  strictly additive.
- Any change forces `schemaVersion` to `2` (means a field became required) —
  stop and reconcile with ADR 0001 D3 before proceeding.
- `validate_host_transport_metadata` rejects the new `customAgentProjection`
  block — stop (the schema/validator are inconsistent).

## Out of scope (later plans)

- The certification gate that *requires* descriptors for projected discussions,
  the projected fixture, and the topology doc updates → **plan 008**.
- Any adapter code, re-vendor, or smoke → the adapter repos after 008.

## Review incorporated (2026-06-21, Codex adversarial review of `40f4303`)

Three findings on the landed 007, now fixed (commit follows):

- **[high] Adapter-smoke replay stripped the descriptor.** `smoke.py:_collect_core`
  rebuilt each result without `agentDescriptor`, so a stored `collect-result`
  could drop/mutate provenance and still pass `adapter-smoke` (and thus
  `certify_adapter`). Fixed: `_result_core` now carries `agentDescriptor` into the
  replay comparison; negative tests assert dropped/mutated descriptors trigger
  `collect_replay_mismatch`.
- **[high] Host-step validator ignored `customAgentProjection`.** The hand-rolled
  `adapter.py:validate_host_transport_metadata` validated `transport` but not the
  new projection block, so malformed projection metadata passed
  `validate-host-step`/`adapter-smoke`. Fixed: explicit validation (projected
  bool required; agentSourceDir non-empty str; count non-negative int; no extra
  keys) with `invalid_custom_agent_projection`; negative tests cover each shape.
- **[medium] ADAPTER-SPEC didn't mention the new surface.** Added the three new
  schemas to Required reading and a "Dynamic custom-agent provenance (v0.3.0,
  additive)" subsection documenting `agentDescriptor`, `customAgentProjection`,
  `projection-manifest.json`, and `--agent-source-dir`, with an explicit
  "additive / not-yet-certified; enforcement in plan 008" status.

Suite after fixes: 214 passed (was 209). The full topology recipe,
`--require-projection` enforcement, and the `HOST-ADAPTERS.md` /
`runtime-contract.json` updates remain plan 008 as designed.
