# Host Adapter Specification

This is the contract for building a `swarm-discussion` host adapter (Claude
Code, Codex, or any future coding agent). The runtime repo is the source of
truth; an adapter is a thin, host-specific shell around it.

## Repository topology

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

## Execution topology (nested orchestrator)

Verified on Claude Code 2.1.177 (2026-06-11): a sub-agent can spawn its own
sub-agents to at least depth 3. Older hosts capped nesting at depth 1, which
forced the orchestrator to run on the parent/root thread and carry all
discussion mechanics in the user's context window. Where the host permits
nesting, the adapter SHOULD use this shape:

```text
parent agent (root, depth 0)
  -> skill: collect brief, spawn ONE orchestrator sub-agent, wait, relay synthesis
       orchestrator (depth 1)   owns the whole loop in ITS OWN context:
         context-build . prompt-build . transport . WAL . rounds . synthesis
         -> persona experts (depth 2)   one-shot structured contributions
              -> readonly researcher (depth 3, optional)   evidence-gathering
  <- parent receives only the final synthesis / evidence
```

This keeps the verbose mechanical middle inside the orchestrator's disposable
context; the parent's window holds only the brief it sent down and the
synthesis it gets back. It is the runtime's "parent agent is not the runtime"
thesis realized end to end, and it relies on the artifact-first / WAL design to
keep the orchestrator lean across rounds.

Host capability gate: use this shape only if the host actually permits a
sub-agent to spawn sub-agents. If the host caps nesting at depth 1, fall back
to running the orchestrator on the root thread (the pre-nesting shape) and keep
the parent context minimal by other means. The adapter's `doctor` command
SHOULD probe and record the host's nesting support so the shape is chosen from
evidence, not assumption.

## Required reading

- `runtime-contract.json` — stable commands, integration gates, boundary
  responsibilities, forbidden runtime responsibilities, stable artifact paths.
- `docs/HOST-ADAPTERS.md` — concrete Codex and Claude recipes.
- `docs/RUNTIME-PACKAGE-BOUNDARY.md` — ownership boundaries.
- `protocol/` — discussion semantics (single source of truth; do not fork).
- `protocol/templates/context-generator.md` — the parent-brief authoring guide
  consumed by `context-build`.
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
   HEAD `plugins/codex/runtime/swarm_runtime_wrapper.py` (~400 lines). Runtime
   commands print a compact summary to stdout by default and accept `--full`
   for the complete payload; failures always print the full `errors`. Parse the
   compact keys and pass `--full` only when you genuinely need the whole
   artifact (which otherwise lives in the `--out`/`--output` file).
3. **Skill / entry document** — thin. On a nesting-capable host it collects the
   brief, spawns ONE orchestrator sub-agent (see Execution topology), waits,
   and relays the returned synthesis; it does NOT run the protocol inline. It
   also carries the host-specific bootstrap (installed-path resolution, spawn
   primitive names) and the entry contract (below).
4. **Orchestrator agent definition** — the agent the skill spawns. Granted the
   host's agent-spawning tool plus shell access to the runtime CLI; runs the
   full runtime loop and spawns persona experts. This agent type MUST be able
   to spawn sub-agents.
5. **Persona expert agent definition** — the generic one-shot expert (e.g.
   `swarm-expert`), spawned with the runtime-produced `prompt.txt` only, and
   restricted to no broad tools by default. It must NOT carry the
   agent-spawning tool unless a capability profile explicitly authorizes a
   deeper readonly researcher.
6. **Host-native smoke**: at least one real discussion driven end-to-end on
   the host through the adapter, kept (or referenced) in the adapter repo.

## Entry contract (must-nots)

The orchestrator (a sub-agent on a nesting-capable host, otherwise the root
thread) may prepare compact temp input files, call host spawn/wait/close
primitives, and pass raw host results into runtime commands. It must NOT:

- derive persona prompt text without `prompt-build`;
- merge wait statuses outside `transport-collect` / `collect-merge`;
- mint message ids, edit committed round files, or patch WAL partials
  directly;
- reimplement any helper in the `protocol/README.md` legacy-mechanics table;
- expand parent context beyond brief path, current phase, agent ids, and the
  next helper command (`validate-host-step` enforces this);
- treat fixture-only gate results as a substitute for validating the real
  discussion artifact tree;
- grant the agent-spawning tool to ordinary persona experts — only the
  orchestrator (and an explicitly profiled readonly researcher) may nest;
- spawn any sub-agent with a self-replicating or "how deep can you go" prompt.
  Give every sub-agent a concrete, bounded, role-specific task: capable hosts
  refuse self-similar recursive prompts (verified 2026-06-11), and the
  protocol never needs one.

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
