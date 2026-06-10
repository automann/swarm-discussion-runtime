# Progress — Rust Tauri vs Electron for a Kanban Board desktop application

- Mode: **lightweight** (2 dynamic experts + Moderator + Contrarian)
- Discussion id: `tauri-vs-electron-kanban`
- Created: 2026-06-07

## Phase 1 — Initialization
Panel: `velocity-lead` (leans Electron) ⇄ `runtime-architect` (leans Tauri). Tension axis: ship-fast/uniform-stack vs. lean/native-footprint. User confirmed composition → **Start**.

r1-msg-001 emitted
r1-msg-002 emitted

## Round 1 — Step 1: Position Declarations (BLIND)
- **r1-msg-001 velocity-lead** → Electron (conf 0.60). Bet: dnd-kit + React/TS reuse hits launch in weeks; flips on hard <10MB/low-RAM req or proven Tauri DnD spike.
- **r1-msg-002 runtime-architect** → Tauri (conf 0.60). Bet: 5-15MB installer / ~80-150MB RAM vs Electron's 80-150MB / 250-400MB; flips if WebKitGTK breaks board DnD or ecosystem gaps bite.
- **Key takeaway:** Both at 0.60 confidence and — notably — both named the *same* hinge as their flip condition: whether Tauri's Linux WebKitGTK webview can deliver buttery drag-and-drop. That convergence on the crux is the seam to pry open.
r1-msg-003 emitted
r1-msg-004 emitted
r1-msg-005 emitted

## Round 1 — Step 2: Moderator Framing (r1-msg-003)
Reframed to two answerable questions: (a) does WebKitGTK degrade multi-column DnD enough to erase Tauri's footprint savings? (b) at what install base does Chromium maintenance overtake launch-velocity? Disagreement budget target **4/10**.
- **Key takeaway:** A "Rust vs JS" preference fight was converted into an empirical spike + a cost-crossover threshold.

## Round 1 — Step 3: Cited Argumentation
- **r1-msg-004 velocity-lead** → softened to Electron conf **0.58** (from 0.60), "near coin-flip on 12-24mo". Self-corrected: Electron delta-updates make bandwidth negligible (~1.5 eng-weeks/yr maint, not 150MB/user) — cutting against own keyRisk. Crossover ≈ 100k-250k always-open DAU on low-RAM, or ~50k installs under a 0-day SLA. Last-stand bet: dnd-kit accessible KeyboardSensor + live ARIA on WebKitGTK.
- **r1-msg-005 runtime-architect** → held Tauri conf **0.60**, gated on a **concrete 5-eng-day spike** (4 pass/fail behaviors). Key technical point: dnd-kit avoids HTML5 drag (uses setPointerCapture+transforms) so the classic WebKitGTK drag-image bug is **moot**; real risks are perf/polish (autoscroll jank, pointer coalescing). Concession path: Linux-only split build or full concede if 2+ behaviors fail.
- **Key takeaway:** Both now agree the decision hinges on a measurable spike — and runtime-architect partly *dissolved* velocity-lead's central fear (dnd-kit isn't HTML5-drag, so the scariest WebKitGTK bug doesn't apply). Strong emerging consensus = prime Contrarian target.
r1-msg-006 emitted
r1-msg-007 emitted
r1-msg-008 emitted

## Round 1 — Step 4: Contrarian Stress Test (r1-msg-006)
Targeted the "DnD spike is a sufficient statistic" consensus. Load-bearing assumption exposed: the spike measures the *safest* path (dnd-kit uses setPointerCapture, not HTML5 drag), leaving the real recurring tax untested — the **non-DnD long tail** (CJK/IME, native file dialogs, drag-out-to-OS, print/PDF, codecs, IndexedDB/SW, WebKitGTK version skew) + hidden Rust CI/signing/notarization plumbing. Also: both at 0.58-0.60 on opposite picks ⇒ maybe low-stakes vs sync/collaboration differentiator.
- **Key takeaway:** Reframed the spike as *necessary-but-not-sufficient*; put a 3-part falsifiable burden on the table.

## Round 1 — Step 5: Responses & Position Shifts
- **r1-msg-007 velocity-lead** → **HELD Electron @ 0.58** (shift: none). Counter-judo: the long-tail critique *favors* Chromium uniformity (Electron pays per-engine divergence once; WebKitGTK is the engine that *varies*). Conceded the choice is lower-stakes than team-Rust-readiness + sync moat — but says those still favor Electron.
- **r1-msg-008 runtime-architect** → **SHIFTED Tauri 0.60 → ~0.54** (shift: **minor**; triggers r1-msg-006, r1-msg-004). Conceded spike selection-bias + Rust plumbing cost; split the long tail honestly: **bounded** (file dialogs, notifications, updater, IME via OS webview — actually a Tauri strength) vs **genuinely unbounded** (WebKitGTK version skew, print/PDF, codecs). Proposes broadening the spike to a long-tail probe pass.
- **Provenance gate: PASS** (0 violations).
- **Key takeaway:** Genuine convergence toward "near coin-flip, decided by team-Rust-readiness + the non-DnD long tail + sync architecture" — not by DnD. One real position shift; the held position got *sturdier*, not just stubborn.

## Round 1 — Step 7: Quality Gate (committed to rounds/001.json)
Scores — genuineDisagreement 4 · evidenceQuality 4 · steelManning 5 · novelInsights 4 · positionEvolution 3 · **overall 4/5**. Recommendation: **synthesize** (convergence judged genuine, not premature). Round record validated: ALL PASS (schema, id grammar, 19 graph edges resolve, provenance clean).
- **Key takeaway:** The headline fault line dissolved; residual risk localized to a narrow unbounded set; true deciders are scope/context inputs (Linux-first?, projected scale vs crossover, Rust-readiness, sync moat) that further debate can't resolve. → Proceed to synthesis.

## Phase 3 — Synthesis (Historian)
Wrote artifacts: synthesis.json, synthesis.md, open-questions.md, argument-graph.json (8 nodes / 19 edges), position-evolution.md.
Headline: **Default to Electron unless a footprint/Linux/scale gate flips to Tauri** — the WebKitGTK drag bug is moot (dnd-kit ≠ HTML5 drag), so context inputs decide, not framework superiority.

## Phase 4 — Termination
manifest → status:completed, currentPhase:synthesis, currentRound:1. context/summary.md written (resume-ready). No runtime team to release (Agent-tool mapping is ephemeral).
