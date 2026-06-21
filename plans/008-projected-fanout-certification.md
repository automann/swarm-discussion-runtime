# Plan 008: Certify projected custom-agent fan-out (gate + fixture + topology docs)

> **Executor instructions**: Follow step by step; run every verification and
> confirm the expected result before moving on. Honor STOP conditions. When done,
> append a `PROGRESS.md` round entry and update this plan's row in
> `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat <planned-at>..HEAD -- runtime/swarm/adapter.py runtime/swarm/loop.py conformance/ fixtures/ docs/ schemas/`
> On any in-scope change since planning, reconcile before proceeding.

## Status

- **Priority**: P1 (makes the v0.3.0 topology certifiable; ADR 0001 D3 Q4)
- **Effort**: M
- **Risk**: MED (adds a certification gate; must be opt-in via the projection flag so non-projected discussions are unaffected)
- **Depends on**: **plan 007** (the `agentDescriptor` shape must exist and be preserved before it can be required/certified)
- **Category**: feature (v0.3.0 topology)
- **Planned at**: commit `8378415`, 2026-06-21
- **Decision record**: `docs/adr/0001-v0.3.0-dynamic-custom-agent-topology.md`

## Why this matters

Plan 007 lets the runtime *carry* projected-agent provenance. This plan makes it
*provable*: a discussion that declares projected custom agents must demonstrate
that every expert payload is attributable to a named projected agent driven by a
runtime prompt — so `certified: true` means real projected fan-out, not the old
generic-expert path (the Codex P1: a retained smoke that records
`multi_agent_v1.spawn_agent` with personas but no projected name must NOT count).
Per ADR 0001 D3, the gate is **opt-in**: it fires only when
`host-step.transport.customAgentProjection.projected == true`, so existing
non-projected fixtures/discussions stay green.

## Steps

1. **Projection-consistency gate (runtime validators).**
   - In `runtime/swarm/adapter.py:validate_host_transport_metadata`: when
     `transport.customAgentProjection.projected == true`, require
     `customAgentProjection.count >= 1` and a non-empty `agentSourceDir`.
   - In the loop/discussion validator (`runtime/swarm/loop.py`, where
     `collect-result.json` and host-step are already read): when the phase's
     host-step declares projection, require that **every** `collect-result`
     result carries an `agentDescriptor` with a non-empty `projectedName`, a
     `projectedSha256` matching `^[0-9a-f]{64}$`, and a `promptRef` that resolves
     to an existing file under the discussion dir. Emit precise codes:
     `missing_agent_descriptor`, `invalid_projected_sha`, `unresolved_prompt_ref`.
   - Non-projected discussions: gate is inert (no behavior change).

2. **Projected fixture.** Add `fixtures/e2e/projected-minimal-v2/` (copy
   `minimal-v2` and add projection): spawn-order entries with valid
   `agentDescriptor`s, host-step `customAgentProjection {projected:true,...}`,
   `collect-result` results carrying descriptors, prompt artifacts at the
   referenced `promptRef`s, regenerated `trace.json`/`evidence.json`. It must
   pass `adapter-smoke`, `validate-loop`, and `validate-discussion`. Keep
   `minimal-v2` as the non-projected baseline (do not modify it).

3. **Certification.** Confirm `conformance/certify_adapter.py` needs no new flags
   — the gate rides inside `validate-host-step`/`validate-loop`/`validate-discussion`,
   so `certify_adapter.py --discussion fixtures/e2e/projected-minimal-v2 …` exercises
   it. If certify has an explicit check list, add a `projected-fan-out` check that
   asserts the discussion's host-step declares projection and the linkage holds
   (so an operator can certify *as a projected discussion* explicitly).

4. **Negative tests** (the Codex P1, pinned):
   - A projected host-step whose `collect-result` lacks descriptors →
     `validate-loop` fails with `missing_agent_descriptor` (would have passed before).
   - A descriptor with a bad sha / unresolved `promptRef` → the matching code.
   - The non-projected `minimal-v2` → still `ok` (gate inert).
   - schema conformance for the projected fixture (plan 003 pattern).

5. **Optional metric (ADR open question).** If cheap, surface
   `metrics.projectedAgentCount` in `evidence` (and a `customAgentProjection`
   note in `trace`) so auditability doesn't require parsing transport. Decide
   yes/no here and record the decision in PROGRESS.

6. **Topology docs (both hosts).**
   - `docs/ADAPTER-SPEC.md`: new "Dynamic custom-agent projection" subsection —
     the parent→coordinator-background-session→projected-expert shape, the
     `agentDescriptor` contract, the entry-contract addition (parent projects &
     cleans up the agent files; coordinator never creates/cleans them; experts
     are no-tools leaves spawned with runtime prompts only), and **what
     certification proves vs. host truth** (Risk R6: the runtime proves
     descriptor↔payload consistency; only the retained real-host smoke proves the
     host actually invoked the named agent).
   - `docs/HOST-ADAPTERS.md`: per-host recipe — Claude (`.claude/agents/*.md`,
     `claude --bg --agent swarm-coordinator`, `claude agents --json`/`logs`/`stop`/`rm`,
     `worktree.bgIsolation:"none"`, resultKey `name`) and Codex (`.codex/agents/*.toml`,
     dedicated coordinator thread, `multi_agent_v1.spawn_agent`, resultKey `agent_id`).
   - `docs/RUNTIME-PACKAGE-BOUNDARY.md`: state that projection provenance is
     runtime-owned (`agentDescriptor`), and adapters must not write a second
     provenance store.

7. **Plans index.** Update `plans/README.md`: add 007/008 rows (status DONE when
   landed), a dependency note (008 → 007), and a short "Update — v0.3.0 dynamic
   custom-agent topology" section pointing at ADR 0001.

8. **Verify.**
   - `.venv/bin/python -m pytest -q` → green (record count).
   - `python3 runtime/swarm_rt.py validate-loop fixtures/e2e/projected-minimal-v2` → `ok: true`.
   - `python3 runtime/swarm_rt.py validate-loop fixtures/e2e/minimal-v2` → `ok: true` (gate inert).
   - `python3 conformance/certify_adapter.py --discussion fixtures/e2e/projected-minimal-v2 --vendored . --runtime runtime/swarm_rt.py` (or the standard invocation) → CERTIFIED.

## STOP conditions

- The gate fires on a non-projected discussion (must be opt-in via the projection
  flag) — stop; it would break existing adapters.
- `certify_adapter.py` against the **old** non-projected `minimal-v2` stops
  passing — stop; backward compatibility is broken.
- The projected fixture can only pass by relaxing a real check (e.g. accepting a
  missing descriptor) — stop; the fixture must be genuinely well-formed.

## Out of scope

- Adapter implementation, re-vendor, real host-driven smokes, tags — the adapter
  repos, after this plan lands and a runtime commit is cut for vendoring
  (ADR 0001 rollout steps 2–4).
