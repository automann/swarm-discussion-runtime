# Plan 010: Claude adapter — `mode` × `stressPolicy` phase orchestration (ADR 0002 step 2)

> **Note:** unlike plans 001–009 (runtime), this plan's implementation lands in the
> **`swarm-discussion-claude`** adapter repo. The runtime contract (plan 009) is done; this
> is the Claude side of ADR 0002 rollout **step 2** (ROADMAP-NEXT `F-1` remainder). The
> Codex adapter is the same shape in Codex's lane (handoff:
> `/tmp/runtime-009-vendoring-handoff-20260623.md`).
>
> **Drift check:** `git -C <claude-adapter> diff --stat <planned-at>..HEAD`.

## Status

- **Priority**: P1 (ADR 0002 rollout step 2, Claude side)
- **Effort**: M/L
- **Risk**: MED — depends on a research-preview background session; the gate is proven only
  by a live coordinator-driven retained smoke.
- **Depends on**: plan 009 (runtime contract) + runtime vendor `c843931` (60 files).
- **Decision record**: `docs/adr/0002-mode-stresspolicy-debate-depth.md`.

## Why this matters

The runtime owns and certifies the debate-depth contract (plan 009). The Claude coordinator
must now *orchestrate* it — otherwise it keeps doing the single-pass fan-out that the real
`govspec` run exposed, just on the Claude host. This makes the Claude adapter run an actual
engineered-disagreement loop and certify it.

## Steps

1. **Re-vendor** the runtime at `c843931` into `vendor/swarm-runtime`; `vendor.py verify`.
2. **Coordinator** (`agents/swarm-coordinator.md`): accept `stressPolicy`; run the bounded loop:
   `position` (`declaration`) → `argument` (`argumentation`) → call **`stress-check`** and
   record `{stressRequired, argumentDigest}` → **if `stressRequired`** run the `contrarian`
   stress phase (emits a `stress_test` message targeting the strongest consensus) + a
   `response` phase (each challenged expert cites the stress in its OWN `references` and
   declares a `positionShift`) → synthesis carrying a `minorityReport`. Finalize the round
   with a `quality` block carrying `stressPolicy` + the recorded `stressRequired` +
   `argumentDigest` (the runtime computes the structural fields). Self-check
   `validate-loop --require-projection --require-stress`.
3. **Skill** (`skills/swarm-discussion/SKILL.md`): map the request to a real `mode` tier
   (`lightweight|standard|deep`, not free text) and choose `stressPolicy` (default from mode);
   pass `stressPolicy` in the dispatch packet; **after cleanup** (manifest `deletionStatus`
   → `clean`) **regenerate `trace` + `evidence`** so the retained evidence reflects the clean
   manifest (B-1: the parent's manifest finalization makes the coordinator's evidence stale).
4. **Doctor/validate**: `doctor --smoke-fixture` + `claude plugin validate`.
5. **Retained smoke**: drive a real `claude --bg` coordinator on a `deep` + `required` topic;
   retain the discussion under `smoke/discussions/<id>`.
6. **Certify**: `certify_adapter.py --require-projection --require-stress` (5/5) + the
   zero-residue cleanup check.
7. **Release**: bump the vendor SHA + plugin version; tag; bump the aggregator pin.

## STOP conditions

- `doctor` reports background sessions / nesting unsupported.
- The retained smoke can only pass by relaxing a real gate (e.g. a `stress_test` message with
  no citing `response`, or a `required` run with no stress pass).
- The coordinator still collapses to a single-pass fan-out.

## Out of scope

- Runtime changes — plan 009 owns the contract; this only orchestrates it.
- The Codex adapter (Codex's lane; same handoff + contract).
