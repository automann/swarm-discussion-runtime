# Legacy Fixtures

Real discussion artifacts produced by the published `swarm-discussion` plugin
line, imported verbatim (minus `.DS_Store`) from
`swarm-discussion/.swarm/discussions/` on 2026-06-11. These are the
"real legacy smoke fixtures" required by the incubator completion definition
in `ACCEPTANCE.md`.

| Fixture | State | What it pins |
|---|---|---|
| `tauri-vs-electron-kanban/` | complete | A real completed discussion that passes `validate-discussion` clean and traces `on-track` with `nextAction: none`. |
| `wails-vs-electron-kanban/` | incomplete | Real discussion missing `context/summary.md`; trace must diagnose `inspect_validation`. |
| `install-verify-tabs-spaces/` | incomplete | Real discussion missing summary and synthesis artifacts; trace must diagnose `inspect_validation`. |

These directories predate the v2 transport/WAL helpers, so they contain no
`transport/`, `prompts/`, or `events.jsonl` trees. They prove the validators
and trace/evidence work on artifacts the old plugin actually produced, not
just on synthetic shapes. Do not edit them; add new fixtures instead.
