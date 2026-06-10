# Synthesis — Golang Wails vs Electron for a Kanban Board desktop app

**Mode:** lightweight (1 round) · **Quality:** 4/5 · **Position shifts:** 2 (both minor) · **Date:** 2026-06-07

## Executive summary

The panel converged fast on **structure** but not on the core empirical **fact**. Both specialists held their frameworks; confidence moved only slightly (`native-go-engineer` 0.62→0.55, `web-frontend-pragmatist` 0.70→~0.68), both nudged by the Contrarian's stress-test (`r1-msg-006`).

**Settled by argument:**
1. The **Go backend is a red herring** for the *fidelity* decision — a Kanban board is not CPU-bound (`r1-msg-004`, `r1-msg-005`). (It still matters for *maintenance/TCO* — `r1-msg-007`.)
2. **Drag fidelity is the gate; footprint is the tiebreaker** (`r1-msg-004`, accepted by `r1-msg-005`/`r1-msg-008`).
3. **Electron's footprint cost is real** (~120-180 MB installer / 200-400 MB RSS) — uncontested (`r1-msg-001`, `r1-msg-005`).
4. **Electron's maintenance/TCO liability is real and conceded** — Chromium upgrade treadmill + npm CVE churn (`r1-msg-006`, `r1-msg-008`).

**Unresolved by design — the load-bearing crux:** is one bundled Chromium *essential insurance* against cross-webview drag failure, or *unnecessary weight* a fleet-matrix PoC could retire? Only measurement, not more debate, can settle it.

## The decision rule (conditional recommendation)

| Choose | When | Because | Risk |
|---|---|---|---|
| **Electron** | Fidelity is mission-critical, team is React-deep / thin on Go-Rust, fleet is broad & uncontrolled (consumer Linux distros, varied GPU/DPI), footprint not a hard limit | One bundled Chromium collapses the QA variance space from N webviews to **1** — insurance against the bugs a PoC can't sample (`r1-msg-008`) | Permanent footprint + conceded TCO treadmill; insurance whose necessity is unproven |
| **Wails** | A fleet-matrix PoC returns **green** on all 5 failure modes, footprint matters (kiosk/embedded/constrained), team has real Go strength | 8-15 MB binary + bounded Go-maintenance edge (no npm CVE tree, no self-rebundled Chromium, no Electron major treadmill) wins the tiebreaker (`r1-msg-007`) | If a matrix isn't fleet-valid (`r1-msg-006`, un-refuted), drag bugs surface post-ship on uncontrolled distros/GPUs |
| **Tauri** | You want the small footprint + a swappable host over a shared dnd-kit frontend, and can absorb the Rust tax | Footprint/portability hedge only | **Does NOT solve fidelity** — shares system WebKitGTK, inherits the identical Linux drag risk (`r1-msg-008`) |

**Meta-rule:** Gate the whole decision on **(a)** the fleet-matrix PoC and **(b)** a quantified TCO estimate. Those two inputs select among the rows above. *(confidence: high — this is process, not a framework bet.)*

## Key insights (each citation-backed)

1. **Drag fidelity, not footprint, is the gate** *(high)* — the fidelity risk was made concrete by 5 named WebKitGTK failure modes (`r1-msg-005`), un-refuted, and promoted into the PoC matrix (`r1-msg-007`).
2. **Go backend is a red herring for fidelity** *(high)* — conceded by the side it favors (`r1-msg-004`); narrowed by the Contrarian to *fidelity only*, not maintenance (`r1-msg-006`).
3. **One bundled Chromium = variance-reduction insurance, not elimination** *(medium)* — the pragmatist's strongest move turned the n-of-1 critique into a pro-Electron thesis (`r1-msg-008`); honestly bounded (Chromium has ANGLE/GL + Wayland fractional-scaling bugs too).
4. **Electron's TCO liability is real but scoped** *(medium)* — conceded (`r1-msg-008`) yet unquantified; "scheduled chore" vs "treadmill" was asserted, never measured.
5. **Tauri is a footprint hedge, not a fidelity hedge** *(high)* — verifiable architectural fact (`r1-msg-008`), un-refuted.

## Minority report (un-refuted dissent — preserved)

- **A green PoC ≠ green production** — *Contrarian (`r1-msg-006`)*. Hardening into a fleet matrix (`r1-msg-007`) expanded sampling but never proved the matrix is fleet-*valid*; the sample→population gap stands. **Still valid.** This is the strongest single argument *for* Electron's insurance and why the crux is open by design.
- **TCO may be the larger long-run cost, and it went unmeasured** — *Contrarian (`r1-msg-006`)*. Both sides accepted it matters but produced no numbers. **Still valid** — see open question 2.

## See also
- `open-questions.md` — the two live experiments that select within the decision rule.
- `position-evolution.md` — how each expert moved and what triggered it.
- `argument-graph.json` — the full citation graph (18 edges).
- `../rounds/001.json` — the committed round record (validator: ALL PASS).
