# Synthesis — Rust Tauri vs Electron for a Kanban Board desktop application

**Mode:** lightweight · **Rounds:** 1 · **Panel:** velocity-lead (leans Electron) ⇄ runtime-architect (leans Tauri) + Moderator + Contrarian
**Final confidence:** Electron 0.58 / Tauri ~0.54 (near coin-flip) · **1 position shift** (runtime-architect 0.60 → ~0.54)

## Executive summary

**Default to Electron unless a specific gate flips you to Tauri.** The discussion's headline risk against Tauri — that Linux **WebKitGTK** would wreck the drag-and-drop board — turned out to be **moot**: `dnd-kit` doesn't use the HTML5 drag API at all (it uses `setPointerCapture` + CSS transforms), so the classic WebKitGTK drag-image bug never fires (r1-msg-005). Once that crux dissolved, both experts landed near a coin-flip, which means **context inputs decide, not framework superiority**.

- **Electron wins if** *any* hold: Linux is first-class across many distros (WebKitGTK version skew is the one genuinely unbounded risk), the team lacks Rust fluency and launch speed matters, you lean on Chromium-uniform ecosystem edges (data-grid / offline-sync / charting), or projected usage stays **below ~50k installs / ~100k–250k always-open DAU**.
- **Tauri wins if** the inverse holds: narrow/controlled Linux (or Win/mac-only), existing Rust fluency, a hard footprint requirement (<10MB installer / low idle RAM), always-open scale **above** the crossover, or a supply-chain ban on bundled Chromium.
- **Either way:** gate the decision on a **broadened 5-engineer-day spike** (drag-and-drop *and* the non-DnD long tail) on your actual first-class distros.
- **Don't over-invest:** both conceded the shell is likely **lower-stakes than the sync/collaboration moat**. Picking Electron removes a launch-risk dependency and frees engineering weeks for the real differentiator.

## Load-bearing findings (resolved by argument)

1. **The headline WebKitGTK drag bug is moot** — `dnd-kit` avoids HTML5 drag, so the scariest Linux failure mode doesn't apply; DnD becomes a bounded perf/polish question, not a disqualifier. *(r1-msg-005; high)*
2. **The "long tail" splits in two** — **bounded** by stable Tauri v2 plugins / OS APIs (file dialogs, notifications, updater, signing/notarization, and IME/CJK via the OS webview — actually a *Tauri strength*) vs **genuinely unbounded** (WebKitGTK version skew across distros, print/PDF fidelity, codecs via system GStreamer). The unbounded risk is almost entirely **Linux**. *(r1-msg-008; high — conceded against interest)*
3. **Electron pays engine-divergence once** — it bundles one Chromium everywhere; WebKitGTK is the engine that *varies* per distro, so the unbounded tail is structurally Electron's advantage. *(r1-msg-007; high)*
4. **Footprint is an aggregate-RAM cost, not a bandwidth one** — delta-updates make Electron's update bandwidth negligible (~1.5 eng-weeks/yr maintenance); the real cost is idle RAM (~250–400MB vs ~80–150MB) across an always-open tool. *(r1-msg-004; high, self-corrected against interest)*

## Decision gates (answer these to close it)

| Gate | If… | Lean |
|---|---|---|
| **Linux first-class, broad-distro?** | Yes | Electron (or Tauri+Electron Linux split) |
| | No / narrow / Win+mac only | Tauri |
| **Projected always-open scale** | < ~50k installs / ~100k DAU | Electron |
| | > crossover (esp. with security SLA) | Tauri |
| **Team Rust fluency today?** | No + launch pressure | Electron |
| | Yes | Tauri costs shrink |
| **Hard footprint req / Chromium ban?** | Yes | Tauri |

## Minority report (un-refuted dissent — preserved)

- **Accessible keyboard DnD + live ARIA on WebKitGTK** (velocity-lead) — survives the "drag bug is moot" finding as an *untested polish* risk; it's one of the spike's numeric gates. Open until measured, not a disqualifier.
- **IME/CJK via OS-native webview is a Tauri strength** (runtime-architect) — qualifies, doesn't overturn, the "pays divergence once" counter.
- **Linux-only split build** (runtime-architect) — viable fallback, but doubles cross-platform QA surface.

## Recommendation (priority order)

1. **Default to Electron** and redirect saved weeks to the sync/collaboration moat — *high confidence*, given no footprint hard-req, no Chromium ban, scale below crossover.
2. **Run the broadened spike** (4 numeric DnD gates + non-DnD long-tail probe: IME/CJK, print/PDF, codecs, distro skew) before committing — *high confidence*; define the first-class distro list first.
3. **Choose Tauri** if Linux is narrow AND (footprint req | Rust fluency | scale > crossover | Chromium ban) AND the spike passes — *medium confidence*.
4. **Linux split build** as a fallback if Win/mac footprint matters but Linux fails the spike — *low confidence* (QA cost).

## Meta-observation

The most load-bearing moves were **concessions against interest** (velocity-lead's delta-update self-correction; runtime-architect's downshift to 0.54), so confidence here tracks *argument quality*, not the near-even 0.58/0.54 vote. The near coin-flip is a real finding, not indecision: once the drag bug fell, framework superiority stopped being the variable. The one structural gap — the decisive inputs (Linux scope, scale, Rust-readiness, sync moat) were ruled *out of scope* by the problem definition, so the discussion mapped the answer's shape precisely but couldn't close it without those inputs.

*All claims trace to `rounds/001.json`; argument graph in `argument-graph.json`; position evolution in `position-evolution.md`; open questions in `open-questions.md`.*
