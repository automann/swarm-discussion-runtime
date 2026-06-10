# Resume Context — Tauri vs Electron for a Kanban Board

**Status:** completed (1 round, lightweight) · **Decision posture:** near coin-flip, Electron-by-default pending decision gates.

## Theme & purpose
Choose Rust/Tauri vs Electron for a Kanban board desktop app, trading delivery speed/ecosystem against runtime footprint/native quality. Success = a conditional recommendation with explicit flip conditions, not a universal winner.

## Key progress (what was established)
- The framed crux — "WebKitGTK wrecks the drag-and-drop board" — was **dissolved**: `dnd-kit` uses `setPointerCapture` + transforms, not HTML5 drag, so the classic WebKitGTK drag bug is moot (r1-msg-005).
- The non-DnD "long tail" was **split**: bounded (Tauri v2 plugins/OS APIs: dialogs, notifications, updater, signing, IME/CJK) vs genuinely unbounded (WebKitGTK distro skew, print/PDF, codecs) — the unbounded part is almost entirely **Linux** (r1-msg-008).
- Counter that the unbounded tail **favors Electron**: it pays engine-divergence once; WebKitGTK is the engine that varies (r1-msg-007).
- Footprint = aggregate idle RAM (~250–400MB vs ~80–150MB), not bandwidth (delta-updates ≈ 1.5 eng-weeks/yr) (r1-msg-004).
- Quantified crossover: ~50k installs / ~100k–250k always-open DAU, or a Chromium 0-day under SLA (r1-msg-004).

## Current positions (after shifts)
- **velocity-lead:** Electron @ 0.58 (held; reasoning re-grounded to engine-variance + team-readiness).
- **runtime-architect:** Tauri @ ~0.54 (shifted down from 0.60; wants a broadened spike).

## Active disagreements / open inputs (would decide it)
1. Does the broadened spike pass on the target distros? (not yet run)
2. Is Linux first-class broad-distro, or narrow/Win+mac-only? (out of scope, unfixed)
3. Projected scale vs the crossover? (out of scope)
4. Team Rust-readiness + one-time plumbing cost? (unvalidated)
5. How load-bearing is the (out-of-scope) sync/collaboration moat?

## Quality trajectory
Round 1 overall **4/5** (steel-manning 5, genuine disagreement 4). Convergence judged genuine, not premature → synthesized. Provenance gate clean; round record validated ALL PASS.

## If resumed
Most valuable next round = resolve the scope inputs (gates #2–#4) or design the broadened WebKitGTK long-tail probe (gate #1) into a concrete go/no-go test plan. See `artifacts/synthesis.md` for the full recommendation and `artifacts/open-questions.md` for the gates.
