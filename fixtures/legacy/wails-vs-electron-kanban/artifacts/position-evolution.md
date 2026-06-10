# Position evolution — Wails vs Electron for a Kanban Board

Both experts **held their framework** across the round. The value was in *where* they relocated their arguments — both moves were **minor** and both were triggered by the same message, the Contrarian's stress-test **`r1-msg-006`**.

## native-go-engineer (champions Wails)

| Stage | Position | Conf |
|---|---|---|
| `r1-msg-001` (declaration) | Wails on footprint (8-15 MB / 30-60 MB RSS) + a Go backend asset | 0.62 |
| `r1-msg-004` (argument) | **Turning point.** Conceded cross-webview drag identity is *untested* and the Go backend is "closer to a red herring"; proposed a 1-week tri-webview PoC; coined "fidelity is the gate, footprint the tiebreaker" | 0.55 |
| `r1-msg-007` (response, **shift: minor**) | Hardened the gate into a **fleet matrix**; reclaimed a **bounded Go maintenance/TCO** argument (no npm CVE tree, no self-rebundled Chromium, no Electron treadmill); adopted **Tauri** so a host switch is a swap, not a rewrite | 0.55 |

**Journey:** footprint + Go-backend bet → fleet-matrix-gated *fidelity* bet + bounded Go-*maintenance* argument + Tauri portability. Never flipped.
**Trigger:** `r1-msg-006` — the n-of-1 critique forced the matrix; the maintenance critique exposed an over-generalized "red herring" and let Go's maintenance relevance be reclaimed.

## web-frontend-pragmatist (champions Electron)

| Stage | Position | Conf |
|---|---|---|
| `r1-msg-002` (declaration) | Electron — one bundled Chromium = identical dnd-kit drag fidelity; mature React ecosystem | 0.70 |
| `r1-msg-005` (argument) | Conceded footprint is real + Go backend a red herring; **sharpened** the case by naming 5 concrete WebKitGTK drag-failure modes; residual edge = `electron-builder`/`electron-updater` + React ecosystem | 0.70 |
| `r1-msg-008` (response, **shift: minor**) | **Turning point.** Turned the n-of-1 attack *into* the thesis (one Chromium = variance-reduction **insurance**); **owned** Electron's TCO treadmill as a conceded-but-scoped liability; **rejected** Tauri as a fidelity hedge (system-webview inherits the WebKitGTK risk) | ~0.68 |

**Journey:** one-Chromium drag-identity + ecosystem → variance-*reduction* insurance, owning TCO, rejecting Tauri as a fidelity hedge. Never flipped.
**Trigger:** `r1-msg-006` — the maintenance/TCO blow was the *only* thing to lower confidence (0.70→~0.68); the n-of-1 blow *strengthened* the insurance thesis; the Tauri blow was rejected.

## What the shape reveals

The Contrarian (`r1-msg-006`) did the round's real work — not by flipping anyone, but by forcing both sides onto **firmer ground**. The two shifts citing one common trigger is the signature of a productive stress-test. The deepest signal: the unresolved crux is **empirical, not architectural** — the panel didn't fail to agree; it correctly identified that whether cross-webview drag diverges is a *measurement*, not a debate. The honest output is a **decision rule + the experiment that selects within it**, not a winner.
