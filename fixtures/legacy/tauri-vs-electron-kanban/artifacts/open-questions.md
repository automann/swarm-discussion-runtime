# Open Questions — Tauri vs Electron for a Kanban Board

These are the inputs the discussion could not resolve internally (several were ruled *out of scope* by the problem definition), ordered by decision-impact. Answering #1 and #2 effectively closes the decision.

## 1. Does the broadened spike pass on the actual target distros?
**Why open:** It has not been run — only proposed (r1-msg-005, r1-msg-008). This is the single most decision-relevant unknown: it converts the "unbounded Linux risk" from assertion into measurement, and it is the gate *both* experts agreed on.
**Approach:** Run a 5-engineer-day spike with the 4 numeric DnD gates (DragOverlay tracking ≤1 frame, `setPointerCapture` continuity over 50 rapid cancels, autoscroll ≥60fps, keyboard reorder + screen-reader live-region parity) **plus** a non-DnD long-tail probe (IME/CJK, native file dialogs, drag-OUT to OS, print/PDF, codecs, IndexedDB/SW) across the 2–3 distros you intend to support first-class. Any *unbounded-column* failure is a flip-to-Electron (or Linux-split) signal.

## 2. Is Linux a first-class, broad-distro target — or controlled/narrow (or Win/mac-only)?
**Why open:** The discussion localized the only genuinely unbounded risk (WebKitGTK distro skew) to Linux, but the actual Linux requirement is a context input that was excluded from the framing and never fixed.
**Approach:** Get the product/distribution requirement explicit. Broad-distro Linux first-class → Electron (or a Linux split). Narrow/controlled or no Linux → the unbounded risk largely evaporates and Tauri becomes competitive on footprint.

## 3. What is the realistic always-open DAU / install trajectory vs the crossover?
**Why open:** The thresholds are defined (~50k installs / ~100k–250k always-open DAU, r1-msg-004) but the product's own scale projection is out of scope and unknown, so we can't yet say which side of the crossover the app lands on.
**Approach:** Plot a conservative and an aggressive adoption curve against the crossover. If the aggressive curve crosses ~100k always-open DAU within the planning horizon **and** a security SLA is likely, weight Tauri's footprint/attack-surface payback more heavily.

## 4. Is the team Rust-ready, and is the Rust CI/signing/notarization plumbing genuinely one-time?
**Why open:** The Contrarian flagged Rust plumbing + hiring as a hidden cost (r1-msg-006); runtime-architect conceded the cost but claimed the plumbing is bounded via `tauri-action` (r1-msg-008). Neither was validated against this specific team.
**Approach:** Assess current Rust fluency honestly; cost the `tauri-action` signing/notarization setup as a one-time spike alongside the long-tail probe. No fluency + launch pressure → Electron; existing fluency → the Tauri-side costs shrink materially.

## 5. How load-bearing is the sync/collaboration moat, and is it really shell-independent?
**Why open:** Both experts conceded the shell may matter less than the sync/collaboration differentiator (r1-msg-006, r1-msg-007), but that differentiator was explicitly excluded from this discussion's scope.
**Approach:** A separate design pass on sync/collaboration architecture (out of scope here) — but note its existence reframes the framework choice as "which option frees the most capacity for the moat."
