# Host Adapter Specification

This is the contract for building a `swarm-discussion` host adapter (Claude
Code, Codex, or any future coding agent). The runtime repo is the source of
truth; an adapter is a thin, host-specific shell around it.

## Topology

```text
swarm-discussion-runtime    host-agnostic core (this repo, source of truth)
swarm-discussion-<host>     one adapter repo per host, owned by that host's
                            native agent, vendoring the runtime at a pinned SHA
swarm-discussion            thin aggregation repo: marketplace manifests and
                            release bundles assembled from pinned adapter
                            releases; no protocol or runtime logic
```

Each adapter repo is developed and tested by the agent native to that host.
Cross-host consistency comes from this spec, `runtime-contract.json`, and the
certification gates — not from shared code or cross-agent code review.

## Required reading

- `runtime-contract.json` — stable commands, integration gates, boundary
  responsibilities, forbidden runtime responsibilities, stable artifact paths.
- `docs/HOST-ADAPTERS.md` — concrete Codex and Claude recipes.
- `docs/RUNTIME-PACKAGE-BOUNDARY.md` — ownership boundaries.
- `protocol/` — discussion semantics (single source of truth; do not fork).
- `schemas/host-transport.schema.json` — the host-step metadata packet.

## Adapter deliverables

1. **Vendored runtime** at `vendor/swarm-runtime/`, produced by
   `python3 <runtime-repo>/scripts/vendor.py vendor --dest vendor/swarm-runtime`.
   The tree is read-only; `vendor-manifest.json` pins the runtime SHA and
   per-file hashes. Never edit vendored files — re-vendor from a new runtime
   SHA instead.
2. **A thin wrapper** (single script): runtime discovery (env override →
   bundled vendored copy), a `doctor` command that validates the runtime
   contract and runs the bundled minimal-v2 fixture through the gates, and
   pass-through delegation to runtime commands. The wrapper contains no
   discussion mechanics. Reference: the wrapper at `swarm-discussion`
   HEAD `plugins/codex/runtime/swarm_runtime_wrapper.py` (~400 lines).
3. **Skill / entry document** carrying the host entry contract (below) and the
   host-specific bootstrap (installed-path resolution, spawn primitive names).
4. **Host agent definition** for the generic persona expert (e.g.
   `swarm-expert`), spawned with runtime-produced `prompt.txt` only.
5. **Host-native smoke**: at least one real discussion driven end-to-end on
   the host through the adapter, kept (or referenced) in the adapter repo.

## Entry contract (must-nots)

The orchestrating root thread may prepare compact temp input files, call host
spawn/wait/close primitives, and pass raw host results into runtime commands.
It must NOT:

- derive persona prompt text without `prompt-build`;
- merge wait statuses outside `transport-collect` / `collect-merge`;
- mint message ids, edit committed round files, or patch WAL partials
  directly;
- reimplement any helper in the `protocol/README.md` legacy-mechanics table;
- expand parent context beyond brief path, current phase, agent ids, and the
  next helper command (`validate-host-step` enforces this);
- treat fixture-only gate results as a substitute for validating the real
  discussion artifact tree.

## Certification

An adapter is certified when, from the runtime repo:

```bash
python3 conformance/certify_adapter.py \
  --discussion <real discussion dir produced on the host> \
  --vendored <adapter>/vendor/swarm-runtime \
  --runtime <adapter>/vendor/swarm-runtime/runtime/swarm_rt.py
```

exits 0, meaning: the vendored runtime is contract-true and drift-free, and a
REAL host-driven discussion passes `adapter-smoke`, `validate-loop`, and
`validate-discussion`. The bundled fixture proves the runtime; certification
proves the adapter. Re-certify on every runtime re-vendor and before every
adapter release.

## Versioning

- The adapter's release notes must state the pinned `runtimeSha` from
  `vendor-manifest.json` and the runtime `compatibility` string
  (`runtime-contract.json: runtime.compatibility`).
- The aggregation repo only accepts adapter releases whose certification
  output is attached and whose pinned runtime SHA is current or explicitly
  grandfathered.
