# Progress — Wails vs Electron for a Kanban Board desktop app

**Mode:** lightweight (1 round) · **Experts:** native-go-engineer, web-frontend-pragmatist + Moderator, Contrarian

**Core tension:** runtime footprint + native Go backend (Wails) vs. rendering consistency + ecosystem + delivery speed (Electron).

---
r1-msg-001 emitted
r1-msg-002 emitted

### Round 1 — Step 1: Position Declarations (blind)
- **r1-msg-001** native-go-engineer → **Wails** (conf 0.62): 8-15MB binary / 30-60MB RAM vs Electron 120-180MB / 200-400MB; Kanban workload fits native webview.
- **r1-msg-002** web-frontend-pragmatist → **Electron** (conf 0.70): one Chromium = identical drag-drop feel across OSes + mature @dnd-kit ecosystem ships fast.
- **Key takeaway:** clean split — footprint/native-backend vs rendering-consistency/ecosystem. Both flag the *other's* core risk (Linux WebKitGTK quirks; Chromium RAM + security-hardening cost).
r1-msg-003 emitted

### Round 1 — Step 2: Moderator Framing
- **r1-msg-003** Moderator reframes the crux: not native-vs-web (both agree UI is webview HTML/CSS) but **is one bundled Chromium load-bearing for drag-fidelity parity, or just insurance paid in MB/RAM** — plus is the Go backend a real asset or a red herring.
- Surfaced 5 hidden agreements (footprint-constraint flip, Linux=danger zone, not-CPU-bound, team-conditional, PoC=decider) and aimed 3 evidence-forcing questions. Budget **5/10**.
- **Key takeaway:** the decision hinges on one empirical question — reproducible dnd-kit drag fidelity across WebView2/WKWebView/WebKitGTK.
r1-msg-004 emitted
r1-msg-005 emitted

### Round 1 — Step 3: Expert Arguments (cited + steel-manned)
- **r1-msg-004** native-go-engineer: steel-mans the drag-fidelity risk, concedes cross-webview drag identity is UNTESTED and the Go backend is "closer to a red herring"; lowers conf 0.62 to 0.55, reframes case to footprint+security+distribution, makes fidelity the GATE and footprint the TIEBREAKER. (refs 002 supports, 003 supports, 001 extends)
- **r1-msg-005** web-frontend-pragmatist: names 5 concrete WebKit/WebKitGTK drag-failure modes (pointer-capture loss, translate3d subpixel jitter, scroll-during-drag, backdrop-filter, sticky headers); concedes footprint is real and the Go backend a red herring; if PoC passes, the residual Electron edge = electron-builder/updater auto-update pipeline + React ecosystem. (refs 001 counters, 003 extends)
- **Key takeaway:** rapid convergence on a PoC-gated decision rule (fidelity gate, footprint tiebreaker) and agreement the backend is irrelevant. Consensus forming fast — Contrarian must stress-test it.
r1-msg-006 emitted

### Round 1 — Step 4: Contrarian Stress Test
- **r1-msg-006** targets the NEW consensus (the PoC-gated rule), not the old split. Three blows: (1) a 1-week PoC is n-of-1, not fleet-valid — GPU drivers, fractional DPI, IME, distro WebKitGTK lag mean green PoC != green production; (2) the dominant long-run cost is maintenance/TCO (Electron upgrade treadmill + npm CVE churn vs Go module stability), which the PoC measures nothing about — so "Go backend is a red herring" over-generalizes from fidelity to maintenance; (3) the binary one-toolchain framing ignored Tauri as a cheap 3rd-outcome hedge.
- **Key takeaway:** the consensus is real but its decisive artifact (the PoC) may be measuring the wrong horizon. Sets up the responses to either harden the PoC (fleet matrix) or re-weight maintenance.
r1-msg-007 emitted
r1-msg-008 emitted

### Round 1 — Step 5: Responses & Position Shifts
- **r1-msg-007** native-go-engineer (**shift: minor**, trigger r1-msg-006): n-of-1 critique lands -> hardens the gate into a FLEET MATRIX (old/new GPU, 2 distro WebKitGTK versions, fractional DPI, IME pointercancel, a11y); reclaims a bounded Go MAINTENANCE/TCO argument (no npm CVE tree, no self-rebundled Chromium, no Electron upgrade treadmill); adopts Tauri so a switch is a host swap, not a frontend rewrite. Holds Wails.
- **r1-msg-008** web-frontend-pragmatist (**shift: minor 0.70->~0.68**, trigger r1-msg-006): turns Blow 1 INTO its thesis (one Chromium collapses QA variance space N->1 = insurance against what the PoC cannot sample); OWNS Blow 2 (Electron treadmill + npm CVE) as a conceded liability; rejects Tauri as a fidelity hedge (system-webview inherits the WebKitGTK risk). Holds Electron.
- Provenance gate: **0 violations**.
- **Key takeaway:** both held their framework but converged on a shared, hardened DECISION STRUCTURE (fleet-matrix gate -> footprint/TCO tiebreaker, Tauri tested under the same gate). Residual disagreement is now sharp and well-defined: is OS-webview fleet variance manageable, or load-bearing enough to justify Chromium RAM+TCO?

### Round 1 — Step 6: Cross-Domain — SKIPPED (lightweight mode)

### Round 1 — Step 7: Quality Gate
- Scores: genuineDisagreement 4, evidenceQuality 4, **steelManning 5**, novelInsights 3, positionEvolution 3, **overall 4/5**.
- Recommendation: **synthesize** — convergence is genuine (resolved by argument, not majority); the residual split is one empirical unknown (cross-webview drag parity) only a PoC can settle.

### Round 1 — Step 8: Round committed -> rounds/001.json (validator: ALL PASS)

### Phase 3 — Synthesis (Historian)
- Wrote artifacts: synthesis.json, synthesis.md, open-questions.md, position-evolution.md, argument-graph.json.
- Manifest status -> completed / synthesized.
- **Outcome:** a conditional decision RULE (Electron / Wails / Tauri win-conditions) gated on a fleet-matrix PoC + a quantified-TCO estimate; minority report preserved (green PoC != green production; TCO unmeasured).
