# Roadmap — Next (post-v0.3.0)

The build roadmap in [`ROADMAP.md`](ROADMAP.md) (phases 0–7) is **complete**: the
runtime shipped, both host adapters certified on the v0.3.0 dynamic custom-agent
topology, and the `swarm-discussion` aggregator publishes them at v0.3.1.

This is the **forward, living backlog** for the whole plugin family. During testing
and real-world runs, record issues, fixes, and feature ideas here and triage each
into a target release. The runtime repo is the source of truth, so this single doc
tracks items across **all repos** — each entry names its lane.

Graduating an item:
- a **0.3.x** fix usually lands directly (with a test) and is noted in the repo's CHANGELOG;
- a **0.4.x** feature gets a numbered plan under [`plans/`](plans/) before implementation.

## Release themes

- **0.3.x — harden the certified plumbing.** Bug fixes, conformance gaps found in
  real testing, doc accuracy, minor adapter polish. No protocol or topology change.
- **0.4.x — make the discussion actually *debate*.** Bring the coordinator up to the
  full [`protocol/PROTOCOL.md`](protocol/PROTOCOL.md): engineered disagreement
  (moderator framing, blind parallel positions, contrarian stress-test, fixed roles,
  multi-round convergence, quality/disagreement gate) and mode-tier scaling. May
  extend runtime support, not just the adapters.

## How to use this doc

Append a row to the right table. IDs: `B-n` bug, `F-n` feature, `C-n` chore/doc.
Lanes: `runtime`, `claude`, `codex`, `aggregator`. Status: `open` → `planned` →
`in-progress` → `done`. Add an expanded note below the table for anything
non-trivial, with evidence (a discussion id, validator code, file:line, or thread id).

## 0.3.x — hardening backlog

| ID | Type | Lane | Sev | Status | Summary |
|----|------|------|-----|--------|---------|
| B-1 | bug | runtime | high | **done** | `projection-manifest.json` mutation after evidence makes real runs fail `--require-projection` (plan 009 step 1) |
| C-1 | chore | runtime / conformance | high | **done** | certification only runs on tidied smokes; add a real parent-finalized projected run (plan 009 step 1 + stress fixture) |
| C-2 | chore | claude / codex | med | **done** | map the request to a protocol mode tier instead of free-text — both adapter skills now map to `lightweight\|standard\|deep` (plan 010 + Codex step 2); both v0.4.0 stress smokes ran `deep`. (Runtime alias-vs-reject for non-tier strings stays parked below.) |
| C-3 | chore | codex | low | open | prefer `@mention` expert invocation over explicit spawn (contract-preferred) |
| C-4 | doc | runtime / claude / codex / aggregator | low | open | Modes table duplicated across READMEs — keep in sync or dedupe |

**B-1 — projection-manifest staleness breaks `--require-projection`.**
The parent finalizes `projection-manifest.json` (`deletionStatus` pending→clean, plus
`removedPaths`/`remainingPaths`) *after* the coordinator generated `trace.json` /
`evidence.json`. Because the manifest is counted in `artifactTotalBytes`, the byte
anchor baked into trace/evidence goes stale, so `validate-loop --require-projection`
fails (`stale_evidence_artifact` + `stale_trace_artifact`). Confirmed on the vendored
`04f4974` *and* HEAD against
`swarm-discussion-playground/.swarm/discussions/govspec-20260622-182432` (+493 B).
Fix: exclude `projection-manifest.json` from the `_artifact_paths` byte-total (as
`trace.json` / `evidence.json` already are); the manifest keeps its own gate
(createdPaths sha + deletionStatus). Re-confirm against a real run.

**C-1 — certification blind spot.** The retained smokes pass `--require-projection`,
but a naturally-sequenced real run (coordinator writes evidence → parent finalizes
manifest) trips B-1. Add a certification fixture/case that finalizes the manifest
*after* evidence so this class is caught by the gate, not by manual testing.

**C-2 — mode tiers not applied.** `govspec-20260622-182432` ran with `mode: "normal"`
(free text), so no panel/round scaling happened. Adapters should resolve the request
to `lightweight | standard | deep` (default `standard`) and pass it to `init --mode`.
(Pairs with F-1.)

## 0.4.x — debate-depth backlog

| ID | Type | Lane | Sev | Status | Summary |
|----|------|------|-----|--------|---------|
| F-1 | feat | runtime / codex / claude | high | **done** | `mode` × `stressPolicy`: coordinator runs the full PROTOCOL.md debate (enforced anti-consensus) — runtime (plan 009) + both adapters certified `--require-projection --require-stress` on live/retained stress smokes (plan 010); **released v0.4.0** across both adapters + the aggregator |
| F-2 | feat | runtime | high | **done** | runtime disagreement signal (counter-edges, `genuineDisagreement`, `stressTriggered`) — powers `stressPolicy: auto` + certifies quality (plan 009) |
| F-3 | feat | runtime | low | parking | advisory alignment-check / drift-score phase (founding "periodic alignment") |
| F-4 | feat | runtime / adapters | med | parking | old-vs-new cost/quality benchmark (now unblocked: plan 004 done) |
| F-5 | feat | runtime | low | parking | persona-roster JSON validator (generation stays LLM-owned) |

**F-1 — make the coordinator actually debate.** *The headline 0.4.x item.* Today both
adapters run a single parallel "response" pass of N dynamic experts → synthesize. Real
evidence (`govspec-20260622-182432`): argument graph is 100% `supports`/`extends` with
**zero `counters`**, `positionShifts: []`, no moderator/contrarian/cross-domain/historian,
one round. Bring the coordinator up to `protocol/PROTOCOL.md`: moderator framing +
tension map, blind/parallel position declarations, contrarian stress-test of the
strongest consensus, cross-domain/historian on standard/deep, a disagreement
budget/quality gate, and a second round when the budget warrants. This is the
product's core value ("stop your AI from agreeing with itself"); v0.3.0 proved
projection + certification, never the panel. Needs a numbered plan — see **Design:
`mode` × `stressPolicy`** below for the agreed shape (converged independently with
Codex). prompt-build already supports the documented phases and transport accepts
arbitrary phase names, so phase 1 is adapter-side orchestration; phase 2 sinks the
quality contract into the runtime schema for cross-host parity.

**F-2 — quality signal.** So a no-disagreement fan-out can be detected automatically:
have `trace` / `evidence` report counts of `counters`, position shifts, rounds, and
fixed-roles-run, and let certification optionally warn when a "discussion" engineered
no disagreement. Enables certifying *quality*, not just structure. (Supports F-1.)

### Design direction: `mode` × `stressPolicy` (converged with Codex, 2026-06-22)

Ratified as **[ADR 0002](docs/adr/0002-mode-stresspolicy-debate-depth.md)** (Accepted);
`plans/009` implements it, runtime-first.

Two independent evaluations of `govspec-20260622-182432` reached the same verdict —
the run was *too smooth* (zero `counters` edges, no position shifts). The agreed fix is
**not** a fourth mode but an **orthogonal secondary option**:

- **`mode`** (`lightweight | standard | deep`, existing) — cost/depth: expert count,
  rounds, whether Cross-Domain/Historian run, artifact complexity.
- **`stressPolicy`** (`auto | required | off`, new) — whether an anti-consensus
  **stress pass** must run and genuine disagreement is verified before synthesis.
  - `auto` — trigger a stress pass when the round's argument graph has no
    `counters`/`questions` (or the disagreement sub-score is low). *This is the F-2
    signal used as a gate.*
  - `required` — always run the stress pass and require expert responses.
  - `off` — explicit fast convergence.
  - Default pairing: `lightweight → off|auto`, `standard → auto`, `deep → required`.
    So "deep design" = `deep + required`; reuse `mode`, don't add a tier.

**Bounded loop** (no "loop until satisfied" — it burns context and isn't reproducible):
position (blind: stance, confidence, `wouldChangeIf`) → argument (must cite a peer; ≥1
`counters`/`questions` or escalate) → **contrarian stress of the *strongest* consensus**
(load-bearing assumption, failure scenario, what would disprove it) → response +
`positionShift: none|minor|major` (cite the trigger msg) → quality gate
(`synthesize|continue|deep-dive|different-angle`) → Historian synthesis separating
argued-consensus / majority-only / unrefuted-minority / open-questions. Caps:
`standard` ≤ 1 stress pass; `deep` ≤ 2 rounds + synthesis.

**Acceptance (certifiable — ties F-2 + C-1):** `argumentGraph` has ≥1
`counters`/`questions`, else `stressTriggered: true` is recorded; ≥1 expert responded to
the stress; synthesis carries a `minorityReport` (or explicit "no unrefuted minority");
the quality gate emits a `genuineDisagreement` sub-score; `positionShift: none` is
allowed but must say why.

**Landing (runtime-first, like the v0.3.0 `agentDescriptor` decision):**
1. Adapter phase plan + parent packet / coordinator contract carry `mode` + `stressPolicy`
   and orchestrate `position → argument → stress → response → synthesis` over the
   existing arbitrary-phase transport (`transport/r001/<phase>/…`) — no new transport.
2. Sink the quality fields into the runtime round/evidence schema so **both** adapters
   (Codex *and* Claude — identical gap) enforce it and certification checks it:
   `quality: { stressPolicy, stressTriggered, genuineDisagreement, counterEdgeCount,
   minorityReportPresent }`.

Decision note: phase 1 may be adapter-led to move fast, but the quality contract must
land in the runtime (phase 2) or the two hosts will drift. Codex thread: `019ed4b1`.

*(F-3 / F-4 / F-5 carried over from `plans/README.md` "deferred/rejected"; revisit
with real-run data.)*

## Parking lot / open questions

- Multi-role / sub-coordinator orchestration (S2) — see `docs/FUTURE-EXECUTORS.md`; deferred.
- Canonical mode names: accept aliases (e.g. `"normal"` → `standard`) or reject
  non-tier modes at `init`? (Resolved on the *fourth-mode* question: keep the three
  tiers and add an orthogonal `stressPolicy` — see F-1 design. The alias-vs-reject
  decision for non-tier strings is still open.)
- Is F-1 purely adapter-side, or should the runtime offer a higher-level "drive round"
  helper so both adapters don't re-implement the phase loop? (A composed `round-step`
  command was previously rejected — revisit only if both adapters show duplication.)

## Log

- 2026-06-22 — seeded from the `govspec-20260622-182432` real Codex run evaluation
  (B-1, C-1, C-2, C-3, F-1, F-2) and carried-over deferrals from `plans/README.md`.
- 2026-06-22 — folded the `mode` × `stressPolicy` design into F-1/F-2 after an
  independent Codex evaluation (thread `019ed4b1`) reached the same "no effective
  debate" verdict and proposed `stressPolicy` as an orthogonal secondary option.
- 2026-06-22 — ratified the design as **ADR 0002** (Accepted); `plans/009` to
  implement it, runtime-first.
- 2026-06-22 — incorporated a Codex adversarial review of ADR 0002 + plan 009
  (*needs-attention*): added a pre-synthesis `stress-check` decision so `auto` acts
  *before* synthesis (not post-hoc), required a stress *response* whenever stress is
  triggered, and replaced B-1's lost manifest freshness with a terminal-cleanup gate.
