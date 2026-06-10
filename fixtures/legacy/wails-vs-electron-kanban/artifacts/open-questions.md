# Open questions — Wails vs Electron for a Kanban Board

These are the two live experiments whose outcomes select within the decision rule (`synthesis.md`). Both are kept open because no further *argument* can close them — only *measurement*.

## 1. Does dnd-kit drag/animation actually diverge across WebKit / WebView2 / WebKitGTK on the target fleet — and at what severity?

**Why it's open:** the entire decision pivots on this and there is *zero* data. The cross-webview drag-identity claim was conceded **UNTESTED** in `r1-msg-004` and never tested. This is the load-bearing empirical crux the whole round circled (`r1-msg-002` vs `r1-msg-007`/`r1-msg-008`).

**Suggested approach — the fleet-matrix PoC.** Build one dnd-kit Kanban prototype that exercises **all 5 named failure modes**:
1. Pointer-capture loss mid-drag (`setPointerCapture` survival on a fast flick)
2. `transform: translate3d` DragOverlay subpixel jitter / layer-promotion differences
3. Auto-scroll-during-drag (long column) with pointer capture held
4. `backdrop-filter` on the drag overlay
5. `position: sticky` column headers during scroll

Run it across a **representative matrix**, not three clean dev laptops:
- Old **+** new GPU drivers on Windows WebView2 (incl. an older Intel iGPU)
- **Two** distro WebKitGTK versions — current **and** a ~18-month-stale LTS
- Fractional DPI at **125% and 150%** — check pointer offset
- **IME active** (CJK) — verify `pointercancel` isn't stolen mid-drag
- **Accessibility / screen-reader** pass

**Crucial:** define the PASS threshold **and an acceptable residual-risk bound BEFORE running**, so a green result has agreed meaning. A matrix is still a sample (`r1-msg-006`, un-refuted) — decide up front how much un-sampled fleet you'll accept. The same matrix must also pass on **Tauri's** Linux WebKitGTK, since it is the same risk surface.

## 2. What is the quantified 3-year TCO: Electron's Chromium-treadmill + npm-CVE triage vs Wails/Tauri's webview-variance support + thinner-ecosystem tax?

**Why it's open:** both sides conceded TCO matters (`r1-msg-007`, `r1-msg-008`) and scoped it *rhetorically* — "scheduled chore + Renovate" vs "treadmill" — but produced **no numbers**. The Contrarian's point (`r1-msg-006`) that the expensive thing went unmeasured stands.

**Suggested approach:** estimate engineer-days/year for —
- **(a) Electron:** Chromium major bumps, `electron-builder`/`electron-updater` upkeep, npm CVE triage cadence, native-module rebuilds across Electron majors.
- **(b) Wails / Tauri:** per-OS webview regression handling, reimplementing components missing from the thinner ecosystem, hand-built signed/notarized/delta auto-update (the one residual Electron edge left unanswered).

Multiply by the **actual team's skill mix** (Go/Rust depth vs React depth) — team skill is a stated success axis and likely dominates delivery more than the framework itself.
