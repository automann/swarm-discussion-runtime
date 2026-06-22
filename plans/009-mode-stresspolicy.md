# Plan 009: `mode` × `stressPolicy` — runtime disagreement signal + quality contract + `--require-stress`

> **Executor instructions**: Follow step by step; run every verification and
> confirm the expected result before moving on. Honor STOP conditions. When done,
> append a `PROGRESS.md` round entry and update this plan's row in
> `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat <planned-at>..HEAD -- runtime/swarm/wal.py runtime/swarm/trace.py runtime/swarm/evidence.py runtime/swarm/loop.py runtime/swarm/adapter.py runtime/swarm/projection.py runtime/swarm_rt.py conformance/ fixtures/ schemas/ protocol/ docs/`
> On any in-scope change since planning, reconcile before proceeding.

## Status

- **Priority**: P1 (makes engineered disagreement enforceable; the headline 0.4.x gap)
- **Effort**: M/L
- **Risk**: MED (adds a quality gate; must be opt-in like `--require-projection` so existing discussions stay green)
- **Depends on**: **plan 008** (projected fixture + certification plumbing this extends); ADR 0002. Folds **ROADMAP-NEXT B-1** in as Step 1 (same evidence path).
- **Category**: feature (0.4.x debate depth) — runtime-first slice of ADR 0002
- **Planned at**: commit `93aab72`, 2026-06-22
- **Decision record**: `docs/adr/0002-mode-stresspolicy-debate-depth.md`

## Why this matters

The first real cross-host run (`govspec-20260622-182432`) and two independent
evaluations showed the same gap: a single-pass fan-out of N experts collapses into
synthesis with **zero `counters` edges and no position shifts**, and nothing in the
runtime forces disagreement or notices its absence. `protocol/PROTOCOL.md` already
*describes* the mechanics; this plan makes them a **runtime-owned, certifiable
contract** (ADR 0002 D2) so an adapter cannot pass a consensus fan-out off as a
discussion. This is the runtime-first slice (ADR 0002 rollout step 1); adapter
orchestration of the phases is the follow-on (step 2, out of scope here).

It also folds in ROADMAP-NEXT **B-1**: `--require-projection` currently fails on real
runs because `projection-manifest.json` is counted in `artifactTotalBytes` but is
finalized by the parent *after* the coordinator writes trace/evidence. That bug lives
in the same evidence path this plan extends, so fix it first (Step 1).

## Steps

1. **B-1 — fix the stale-artifact false positive *without* losing cleanup freshness.**
   In the trace/evidence artifact-byte accounting (`runtime/swarm/` — the
   `_artifact_paths` / `artifactTotalBytes` helper that already excludes
   `trace.json`/`evidence.json`), exclude the `projection-manifest.json` **file** from
   the byte anchor: it legitimately changes after evidence is built (only the parent
   finalizes cleanup, and the parent stays thin), so it must not trip the stale check.
   But excluding it wholesale would also hide a forged or partial-cleanup mutation
   (review finding 3), so add a **replacement invariant** under `--require-projection`:
   a **terminal-cleanup content gate** in the projection validator — `deletionStatus`
   must be a valid enum value, and where zero-residue is required (a completed certified
   discussion) `deletionStatus == clean` **and** `remainingPaths == []`; surface
   `deletionStatus` in `evidence.json` so cleanup state stays visible to audit. The
   immutable fields (`runId`, `createdPaths` + sha256) keep their existing gate.
   **Verify**: a real parent-finalized run no longer emits
   `stale_evidence_artifact`/`stale_trace_artifact` from manifest finalization, **and**
   a manifest flipped to `clean` with a non-empty `remainingPaths` (or an invalid
   `deletionStatus`) now FAILS the terminal-cleanup gate. Closes ROADMAP-NEXT B-1 and
   C-1; record in PROGRESS.

2. **`stressPolicy` on the discussion.** Add `init --stress-policy {auto|required|off}`
   (`runtime/swarm_rt.py` + `runtime/swarm/wal.py:init_discussion`), stored in
   `manifest.json` beside `mode`. If omitted, **derive from `mode`**:
   `lightweight → off`, `standard → auto`, `deep → required` (ADR 0002 D1). Validate
   the enum; non-tier/legacy manifests with no `stressPolicy` are treated as `off`
   (back-compat — no assertion). Update the manifest schema (additive, `schemaVersion`
   stays 1).

3. **Pre-synthesis `stress-check` + `quality` block (runtime-owned, tamper-evident).**
   **(a) Pre-synthesis decision — review finding 1, the load-bearing fix.** Add a
   runtime command the coordinator calls after the `argument` phase and **before
   synthesis** (e.g. `stress-check --dir <dir> --round N`): it computes the disagreement
   signal over the argument-phase messages so far and returns
   `{ stressRequired, reason, counterEdgeCount }`. `stressRequired` = (`stressPolicy ==
   required`) or (`auto` and the argument round has no `counters`/`questions` edges).
   Both adapters MUST consult it and run a stress pass before they may finalize — the
   trigger is computed once, in the runtime, so the hosts cannot drift. (A post-finalize
   signal can only *detect* a fan-out; this *prevents* one.)
   **(b) Quality block at finalize.** The runtime derives the **structural** signal from
   artifacts and records a host-agnostic `quality` block on the round record (at
   `finalize-round`) and surfaces it in `evidence.json`:
   ```jsonc
   "quality": {
     "stressPolicy":          "auto|required|off",   // effective policy (from manifest)
     "stressRequired":        <bool>,   // recorded pre-synthesis stress-check decision
     "stressTriggered":       <bool>,   // a `stress` phase ran in this discussion
     "counterEdgeCount":      <int>,    // argumentGraph edges with relation counters|questions
     "positionShiftCount":    <int>,    // len(positionShifts)
     "genuineDisagreement":   <0-10>,   // coordinator/LLM-produced, advisory (ADR R1)
     "minorityReportPresent": <bool>    // synthesis carried a minority report or explicit "none"
   }
   ```
   `counterEdgeCount`, `positionShiftCount`, `stressTriggered` are **computed by the
   runtime**, not accepted from the adapter. If a coordinator stores a `quality` block,
   validation MUST recompute the structural fields and reject a mismatch
   (`quality_signal_mismatch`) — the same anti-forgery stance as the descriptor↔manifest
   sha match in plan 008. Validate the produced fields: `genuineDisagreement` is an int
   0–10, `minorityReportPresent`/`stressTriggered` are bools, counts are non-negative.
   Round messages must be **phase-tagged** (argument / stress / response) so validation
   can re-derive the *pre-stress* signal over the argument-phase subset — this is what
   proves the `auto` decision (3a) was not back-dated. Add the `quality` schema to `schemas/`.

4. **prompt-build phases.** Confirm `prompt-build` (and `protocol/prompts.md`) cover
   the bounded-loop phases (ADR 0002 D3): `position` (blind — stance, confidence,
   conditions, `wouldChangeIf`), `argument` (must cite ≥1 peer; relation ∈
   `supports|counters|extends|questions`), `stress` (contrarian attacks the *strongest*
   consensus — load-bearing assumption, failure scenario, what would disprove it),
   `response` (declares `positionShift: none|minor|major` with a cited trigger). Extend
   the prompt templates for any missing phase. **Open question to settle here**: does
   `stress` reuse the `protocol/PROTOCOL.md` **Contrarian** fixed role (present in
   `standard`/`deep`) or a coordinator-generated stress prompt for `lightweight + auto`?
   Decide and record in PROGRESS.

5. **`--require-stress` certification mode (ADR 0002 D2).** Add the flag to
   `validate-loop` and `conformance/certify_adapter.py`, behavior **derived from the
   declared `stressPolicy`** (never a separate default):
   - **whenever `stressTriggered == true` (any policy):** FAIL unless ≥1 `response`-phase
     message references the stress message (`stress_response_missing`) — a stress step
     nobody answers does not count (review finding 2).
   - `required` → additionally FAIL unless `stressTriggered == true`
     (`stress_required_not_triggered`).
   - `auto` → FAIL if the recorded pre-synthesis decision was `stressRequired == true`
     and no stress pass ran (`auto_stress_skipped`); validation re-derives the pre-stress
     signal from the phase-tagged argument messages so the decision can't be back-dated.
   - `off` → no debate-depth assertion (everything else still gates).
   Opt-in: with no `--require-stress`, or a discussion that declares no policy,
   behavior is unchanged (v0.2.x/v0.3.0 back-compat). **Settle here**: per ADR leaning,
   `--require-stress` is always policy-derived — record the decision.

6. **Fixture.** Add `fixtures/e2e/stress-minimal-v2/` (build on `projected-minimal-v2`):
   a discussion that runs `position → argument → stress → response → synthesis`, whose
   `argumentGraph` has ≥1 `counters` edge, `positionShifts` is non-empty, the `quality`
   block has `stressTriggered: true` and matching structural counts, `manifest.json`
   declares `stressPolicy: required`, and the synthesis carries a `minorityReport`. It
   must pass `validate-loop`, `validate-discussion`, `certify_adapter.py
   --require-projection --require-stress`. Keep `minimal-v2` and `projected-minimal-v2`
   as baselines (do not modify them).

7. **Negative tests** (pin every gate):
   - a `quality` block with a forged `counterEdgeCount` (≠ recomputed) → `quality_signal_mismatch`.
   - a `stressPolicy: required` discussion with no `stress` phase / `stressTriggered: false`
     → `stress_required_not_triggered` under `--require-stress`.
   - a `required` discussion with a stress phase but no `response` referencing it →
     `stress_response_missing`.
   - a `stressPolicy: auto` discussion whose argument round closed with zero
     `counters`/`questions` and that ran no stress → `auto_stress_skipped` under
     `--require-stress` (pre-stress signal re-derived from phase-tagged argument
     messages); the same with a stress pass + response → passes (review finding 1).
   - a `stressPolicy: auto` discussion with a `stress` phase but **no `response`**
     referencing it → `stress_response_missing` (review finding 2).
   - a `projection-manifest.json` flipped to `deletionStatus: clean` with a non-empty
     `remainingPaths` (or an invalid `deletionStatus`) → terminal-cleanup gate FAILS
     under `--require-projection` (review finding 3).
   - `stressPolicy: off` → no debate-depth assertion (passes regardless).
   - back-compat: `minimal-v2` / `projected-minimal-v2` (declare no policy) stay `ok`
     under plain validation and `--require-projection`; `--require-stress` is inert for them.
   - schema conformance for the `quality` block + the stress fixture (plan 003 pattern).

8. **Docs.**
   - `protocol/PROTOCOL.md`: note that the modes/roles it describes are now backed by a
     runtime `quality` contract + `stressPolicy`, and the bounded stress loop.
   - `docs/ADAPTER-SPEC.md`: the `quality` block, `--require-stress`, what certification
     proves vs host truth (the runtime proves *structure* — `counters` edges,
     `stressTriggered` — not that the disagreement was *substantive*; ADR 0002 R2).
   - `schemas/`: the `quality` block + `stressPolicy`.
   - `docs/RUNTIME-PACKAGE-BOUNDARY.md`: the quality contract is runtime-owned; adapters
     orchestrate phases but must not write a parallel quality store.
   - Note (do not implement here): adapters carry `mode` + `stressPolicy` in the parent
     packet / coordinator contract and orchestrate the phases — ADR 0002 rollout step 2.

9. **Plans index + roadmap.** Update `plans/README.md` (009 row → DONE; dependency note
   009 → 008; an "Update 2026-06-22 — ADR 0002 debate depth" line). In `ROADMAP-NEXT.md`,
   flip `B-1` and `C-1` to done, mark `F-2` done, and move `F-1` to in-progress
   (runtime slice landed; adapter orchestration remains).

10. **Verify.**
    - `.venv/bin/python -m pytest -q` → green (record count).
    - `python3 runtime/swarm_rt.py validate-loop fixtures/e2e/stress-minimal-v2` → `ok: true`.
    - `python3 conformance/certify_adapter.py --discussion fixtures/e2e/stress-minimal-v2 --require-projection --require-stress …` → CERTIFIED.
    - `python3 conformance/certify_adapter.py --discussion fixtures/e2e/projected-minimal-v2 --require-stress …` → behavior matches its declared policy (inert if it declares none).
    - `validate-loop fixtures/e2e/minimal-v2` and `… projected-minimal-v2` → still `ok` (gates inert without a declared policy).
    - the B-1 regression: a parent-finalized run no longer reports stale trace/evidence under `--require-projection`.

## STOP conditions

- The quality gate fires on a discussion that declares no `stressPolicy` (must be
  opt-in, like `--require-projection`) — stop; it would break existing adapters.
- A structural signal (`counterEdgeCount`, `stressTriggered`, `positionShiftCount`)
  cannot be recomputed deterministically from artifacts — stop; it must be
  runtime-derived, not adapter-asserted, or the contract is forgeable.
- The stress fixture can only pass by relaxing a real check (e.g. accepting
  `stressTriggered: true` with no `stress` phase) — stop; the fixture must be genuinely
  well-formed.
- `minimal-v2` / `projected-minimal-v2` stop passing under plain validation or
  `--require-projection` — stop; back-compat is broken.

## Out of scope

- Adapter orchestration of the phases: carrying `mode` + `stressPolicy` in the parent
  packet / coordinator contract and running `position → argument → stress → response →
  synthesis` on each host (Codex + Claude). That is ADR 0002 rollout step 2, after this
  plan lands and a runtime commit is cut for vendoring.
- The `genuineDisagreement` *scoring algorithm* — the coordinator produces it; the
  runtime only records, range-checks, and treats it as advisory (the gate uses the
  structural signal). The `auto` trigger threshold (`counterEdgeCount == 0` vs a score
  cutoff) is settled in this plan and recorded in PROGRESS.
- The alias-vs-reject decision for non-tier `mode` strings (e.g. `"normal"`) — tracked
  in ROADMAP-NEXT; this plan only adds `stressPolicy` and treats an undeclared policy
  as `off`.

## Review incorporated (2026-06-22, Codex adversarial review)

Codex reviewed this plan + ADR 0002 + ROADMAP-NEXT (`--base e4f9f6f`, *needs-attention*)
and raised three findings, folded in above:

- **[high] `auto` computed only at finalize couldn't *trigger* stress** → Step 3(a): a
  pre-synthesis `stress-check` decision the coordinator must consult before synthesis,
  recorded as `quality.stressRequired` and re-derivable from phase-tagged messages.
- **[high] `auto` could pass with a stress phase nobody answered** → Step 5:
  `stress_response_missing` now applies whenever `stressTriggered`, any policy; Step 7
  adds the negative test.
- **[medium] B-1 dropped the manifest freshness anchor** → Step 1: exclude the manifest
  *file* from the byte total but add a terminal-cleanup content gate (`deletionStatus`
  enum + `clean`/empty `remainingPaths`) and surface `deletionStatus` in evidence; Step 7
  adds the forged-cleanup negative test.
