# ADR 0002 — `mode` × `stressPolicy`: enforced debate depth

- **Status:** Accepted (2026-06-22)
- **Deciders:** maintainer (`automann`); Claude (runtime + Claude adapter, evaluation); Codex (Codex adapter, evaluation + `stressPolicy` proposal)
- **Applies to:** `swarm-discussion-runtime` (owner of the quality contract), `swarm-discussion-claude`, `swarm-discussion-codex`. The `swarm-discussion` aggregator only documents it.
- **Related:**
  - `ROADMAP-NEXT.md` — F-1 (mode × stressPolicy) and F-2 (disagreement signal); this ADR ratifies that design
  - `protocol/PROTOCOL.md` — existing modes, fixed roles (Moderator/Contrarian/Cross-Domain/Historian), and phases this enforces
  - `docs/adr/0001-…-dynamic-custom-agent-topology.md` — the precedent and the "runtime owns the cross-host contract" principle (D3 there)
  - `docs/ADAPTER-SPEC.md` — certification; this adds an enforceable quality dimension
  - Evidence: the real run `swarm-discussion-playground/.swarm/discussions/govspec-20260622-182432`; two independent evaluations (Claude, this session; Codex thread `019ed4b1`)
  - Implementation: `plans/009` (to be drafted, runtime-first)

## Context

v0.3.0 proved the *plumbing* (projection, coordinator, runtime-owned provenance, certification) but never the *panel*. The first real cross-host run — `govspec-20260622-182432`, a substantive multi-agent governance-spec topic on the Codex adapter — made the gap concrete:

- one round, one `response` phase, 3 dynamic experts, `mode: "normal"` (not a tier);
- the argument graph was **100% `supports`/`extends` — zero `counters`**, and `positionShifts: []`;
- the synthesis was genuinely good (self-scored 0.92), but it was a *consensus workshop*, not a debate.

**Two independent evaluations reached the same verdict** ("no effective debate was conducted"): a single-pass fan-out of N experts collapsed straight into synthesis. This is precisely the failure mode the product exists to prevent — *"stop your AI from agreeing with itself."* The lifecycle met the design requirements; the **discussion quality did not**, and nothing in the runtime *forced* disagreement or *detected* its absence.

`protocol/PROTOCOL.md` already describes the right mechanics (blind positions, a Contrarian that stress-tests the strongest consensus, position-shift tracking, a quality gate, multi-round convergence). The gap is that those mechanics are **documented but neither enforced nor certifiable**: an adapter can run a one-pass fan-out and still pass every gate. This ADR makes engineered disagreement a **runtime-owned, certifiable contract** controlled by a new orthogonal option.

The Codex evaluation proposed the control as `stressPolicy` and framed a phase-1 *adapter-led* implementation. This ADR adopts `stressPolicy` and ratifies the control surface, but, consistent with ADR 0001's "runtime owns the cross-host contract" principle, fixes the **quality contract as runtime-owned** (both adapters have the identical gap; only a runtime contract keeps them from drifting).

## Decision

### D1 — `stressPolicy` is an orthogonal secondary option, not a fourth mode

The two controls are orthogonal and both flow through the brief → `init` → runtime:

- **`mode`** (`lightweight | standard | deep`, existing) — **cost/depth**: number of dynamic experts, rounds, whether Cross-Domain/Historian run, artifact complexity.
- **`stressPolicy`** (`auto | required | off`, new) — **disagreement enforcement**: whether an anti-consensus *stress pass* must run, and whether genuine disagreement is verified before synthesis.
  - `auto` — run a stress pass **when the runtime disagreement signal is empty** (no `counters`/`questions` edges, or `genuineDisagreement` below threshold). See D4.
  - `required` — always run the stress pass and require expert responses, however smooth the round looks.
  - `off` — explicit fast convergence; no stress pass.

Default pairing (an adapter may override per request):

| `mode` | default `stressPolicy` |
|---|---|
| `lightweight` | `off` (or `auto` when cheap) |
| `standard` | `auto` |
| `deep` | `required` |

"Deep design discussion" is therefore **`mode: deep` + `stressPolicy: required`** — *not* a new mode. Reusing the three tiers avoids a combinatorial mode space ("deep + stress?", "stress only?") and keeps `stressPolicy` a single, composable axis.

### D2 — The discussion-quality contract is runtime-owned and certifiable

The runtime computes a structural **disagreement signal** at round finalize and records a host-agnostic `quality` block on the round and in `evidence.json`. Adapters MUST NOT invent a parallel quality store (same reasoning as ADR 0001 D3 for provenance).

```jsonc
// round record + evidence.json
"quality": {
  "stressPolicy":          "auto" | "required" | "off",
  "stressRequired":        true,            // runtime pre-synthesis decision (see below)
  "stressTriggered":       true,            // a stress pass actually ran this discussion
  "counterEdgeCount":      2,               // argumentGraph edges with relation counters|questions
  "positionShiftCount":    1,               // entries in positionShifts[]
  "genuineDisagreement":   4,               // 0–10 gate sub-score (advisory; see R1)
  "minorityReportPresent": true            // synthesis carried a minority report or explicit "none"
}
```

`counterEdgeCount`, `positionShiftCount`, and `stressTriggered` are **computed by the runtime** from the artifacts (argument graph, phases present, `positionShifts`) — they are not adapter self-reports. `genuineDisagreement` and `minorityReportPresent` are LLM/coordinator-produced but must be artifact-backed.

**The `auto` trigger must act *before* synthesis (pre-synthesis decision).** A signal computed only at `finalize-round` can *detect* a fan-out but cannot *prevent* one — by then the round is synthesized and committed. So the runtime owns a **pre-synthesis decision primitive** (`stress-check`): after the `argument` phase and before synthesis, the coordinator calls it; it computes the disagreement signal over the argument-phase messages and returns `{ stressRequired, reason, counterEdgeCount }`. `stressRequired` is true when `stressPolicy == required`, or `stressPolicy == auto` and the argument round has no `counters`/`questions` edges. **Both adapters MUST consult it and run a stress pass before they may finalize** — the trigger is computed once, in the runtime, so the hosts cannot drift (each re-implementing the trigger is the exact failure this ADR prevents). The decision is recorded as `quality.stressRequired`, and round messages are **phase-tagged** so certification can re-derive the pre-stress signal over the argument-phase subset alone — a coordinator cannot back-date or hide that stress was required.

Certification gains an enforceable `--require-stress` mode (parallel to `--require-projection`):

- **whenever `stressTriggered == true` (any policy):** fail unless at least one `response`-phase message references the stress message (`stress_response_missing`) — a stress step nobody answers does not count;
- `stressPolicy: required` → additionally fail unless `stressTriggered == true` (`stress_required_not_triggered`);
- `stressPolicy: auto` → fail if the recorded pre-synthesis decision was `stressRequired == true` and no stress pass ran (`auto_stress_skipped`); validation re-derives the pre-stress signal from the phase-tagged argument messages, so the decision cannot be back-dated;
- `stressPolicy: off` → no debate-depth assertion (everything else still gates).

This makes "did this actually engineer disagreement?" a machine-checkable property, not a reviewer's impression.

### D3 — The stress loop is bounded

No "loop until satisfied" — it burns context/threads and is not reproducible. Caps:

- `standard`: **≤ 1** stress pass per round;
- `deep`: **≤ 2** rounds + a final synthesis.

When the gate is still unsatisfied at the cap, the **quality gate emits a next-step recommendation** (`synthesize | continue | deep-dive | different-angle`) for the parent/user to decide. The coordinator never auto-escalates past the cap on its own.

The enforced debate loop (the phases the coordinator orchestrates; all already expressible as runtime `prompt-build` phases over the existing arbitrary-phase transport):

```
position    blind: stance, confidence, conditions, wouldChangeIf      (anti-anchoring)
argument    must cite ≥1 peer message; relation ∈ supports|counters|extends|questions;
            ≥1 counters|questions edge, else → stress
stress      contrarian attacks the STRONGEST consensus (not the weakest):
            load-bearing assumption, failure scenario, what would disprove it
response    original expert responds; declares positionShift none|minor|major (cite trigger id)
gate        synthesize | continue | deep-dive | different-angle  (+ genuineDisagreement sub-score)
synthesis   Historian separates: argued-consensus / majority-only /
            unrefuted-minority / open-questions
```

### D4 — `stressPolicy: auto` is data-driven; rollout is runtime-first

`auto` triggers the stress pass off the runtime's **pre-synthesis** decision (`stress-check`, D2) — computed once in the runtime and consulted by both coordinators *before* they synthesize — so a smooth round self-corrects and the hosts cannot drift. Because the decision, the signal, and the contract are all runtime-owned, **rollout is runtime-first** (overriding the Codex proposal's adapter-led phase 1 on the *ownership* question — adapters may still move first on *orchestration*, but the contract lands in the runtime, not in one adapter):

1. **runtime** exposes the pre-synthesis `stress-check` decision primitive, computes the signal, records the `quality` block (incl. `stressRequired`), supports the `position/argument/stress/response` phases in `prompt-build`, and adds the `--require-stress` certification mode + acceptance checks;
2. **then both adapters** carry `mode` + `stressPolicy` in the parent packet / coordinator contract and orchestrate the phases — building to the **same** runtime contract so Codex and Claude cannot diverge.

## Consequences

**Positive**
- The product's core value — engineered disagreement — becomes **enforceable and certifiable**, not aspirational. A one-pass fan-out can no longer silently pass as a "discussion."
- One quality contract across hosts; certification (not cross-agent review) keeps Claude and Codex consistent, exactly as for v0.3.0 provenance.
- `auto` makes stress cost-aware: it only fires when a round actually lacks disagreement, so cheap discussions stay cheap.
- Orthogonal control reuses the existing three tiers — no mode explosion.

**Negative / costs**
- New runtime surface: a disagreement signal, a `quality` schema block, and a new certification mode + fixtures.
- More coordinator discipline and more host calls per `deep`/`required` discussion (multiple phases vs one).
- `genuineDisagreement` is a produced score, not ground truth (R1); the gate must lean on the **structural** signal, not the self-score.

## Alternatives considered

| Option | Why not |
|---|---|
| **A fourth `deep_design` mode** | Stress is an *action*, not a depth tier; a lightweight discussion can need a short stress, and a deep one needs more than stress. As a mode it combines badly with the existing tiers ("deep + stress?"). Rejected in favor of an orthogonal `stressPolicy` (D1). |
| **A standalone `stress_test` command** that bypasses normal discussion | With no prior `position`/`argument` context, pure stress degenerates into generic nitpicking. Stress must attach to a real round. |
| **Unbounded auto-multi-round until "satisfied"** | Sounds smart; burns context and threads and is hard to reproduce. Replaced by bounded caps + a quality-gate recommendation the human decides on (D3). |
| **Adapter-owned quality logic (Codex phase-1 framing) as the end state** | Two hosts would drift; "did it debate?" would mean different things on each. The contract must be runtime-owned (D2/D4); adapters may orchestrate, the runtime defines and certifies. |
| **Gate on the self-reported `qualityScore` alone** | A coordinator can score its own consensus 0.92 (it did). The objective gate is the **structural** signal (`counterEdgeCount`, `stressTriggered`); the score stays advisory. |

## Risks & mitigations

- **R1 — `genuineDisagreement` is LLM-judged → subjective/gameable.** *Mitigation:* certification gates on the **structural** signals the runtime computes (`counterEdgeCount`, `positionShiftCount`, `stressTriggered`, `minorityReportPresent`), not the self-score; the score is advisory context only.
- **R2 — "Stress theater":** experts emit token `counters` edges to pass the gate without real disagreement. *Mitigation:* stress targets the *strongest* consensus and must produce a load-bearing assumption + failure scenario + what-would-disprove-it; the response must declare a `positionShift` with a cited trigger. The runtime proves *structure*; semantic quality is still proven only by the retained smoke + human review (ADR 0001 R6 analogue).
- **R3 — Cross-host drift if an adapter ships stress logic before the runtime contract.** *Mitigation:* runtime-first rollout (D4); neither adapter claims the feature until it certifies against the shared `--require-stress` gate.
- **R4 — Cost blow-up on `deep`+`required`.** *Mitigation:* bounded caps (D3); `auto` fires only when needed; document expected call counts per `mode × stressPolicy` in the adapter notes.
- **R5 — Non-tier `mode` strings** (e.g. the real run's `"normal"`) bypass scaling and default-policy selection. *Mitigation:* ROADMAP-NEXT `C-2` (map request → tier); the alias-vs-reject decision for non-tier strings is an open question below.

## Per-repo rollout

Execute **runtime-first**; do not re-vendor adapters until the runtime contract lands.

1. **runtime** — `plans/009`: compute the disagreement signal at finalize-round; add the `quality` block to the round + evidence schemas; ensure `prompt-build` covers the `position/argument/stress/response` phases; add `certify_adapter.py --require-stress` (+ `validate-loop`) with the D2 acceptance checks; add a fixture that exercises a stress pass with a real `counters` edge. Tag a runtime commit for vendoring.
2. **swarm-discussion-codex** & **swarm-discussion-claude** — carry `mode` + `stressPolicy` in the parent packet / coordinator contract; orchestrate `position → argument → stress → response → synthesis`; re-vendor; retain a real `deep` + `required` projected smoke; certify with `--require-stress` (and still `--require-projection`). Same contract on both hosts.
3. **swarm-discussion** — add a `stressPolicy` note to the Modes section when shipped. No structural change.

## Open questions

- Exact `genuineDisagreement` scoring and the `auto` threshold — is the trigger purely `counterEdgeCount == 0`, or a score below `k`? Decide in `plans/009` with real-run data.
- Who runs the stress: reuse the `protocol/PROTOCOL.md` **Contrarian** fixed role (present in `standard`/`deep`), or a coordinator-generated stress prompt for `lightweight` + `auto`? Leaning: Contrarian where the panel includes it, coordinator prompt otherwise.
- Alias-vs-reject for non-tier `mode` strings (carried from ROADMAP-NEXT parking lot) — accept `"normal"` → `standard`, or reject at `init`?
- Does `--require-stress` default on for `deep`, or is it always derived from the discussion's declared `stressPolicy`? Leaning: derived from the declared policy, never a separate default.

## Review incorporated (2026-06-22, Codex adversarial review)

A Codex adversarial review of this ADR + `ROADMAP-NEXT.md` + `plans/009` (`--base e4f9f6f`, verdict *needs-attention*) raised three findings, now addressed:

- **[high] `auto` was computed only post-finalize, so it could not trigger the stress pass** — the default `standard → auto` path could still ship a single-pass fan-out, and each adapter would re-derive the trigger (the drift this ADR exists to prevent). Added the **pre-synthesis `stress-check` decision primitive** (D2): the runtime computes `stressRequired` from the argument phase *before* synthesis; both coordinators must consult it and run stress before finalizing. The decision is recorded (`quality.stressRequired`) and re-derivable from phase-tagged messages.
- **[high] `auto` could pass with a stress phase nobody answered.** Tightened the gate (D2): a `response` referencing the stress message is required **whenever `stressTriggered == true`**, for any policy (`stress_response_missing`) — not only `required`.
- **[medium] Dropping `projection-manifest.json` from the byte anchor (plan 009 B-1) removed its only freshness check.** Resolved in `plans/009`: the manifest file leaves the byte total (so legitimate post-evidence finalization no longer trips `stale_*`), but a **terminal-cleanup content gate** is added under `--require-projection` (`deletionStatus` enum valid, and `== clean` with empty `remainingPaths` where zero-residue is required) and `deletionStatus` is surfaced in evidence — so a forged or partial-cleanup mutation is still caught.
