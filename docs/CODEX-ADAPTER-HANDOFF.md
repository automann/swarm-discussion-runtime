# Codex Adapter Build Handoff — `swarm-discussion-codex`

**Audience:** the Codex coding agent, building the Codex host adapter for the
swarm-discussion family in a NEW repo `swarm-discussion-codex`. You have your
own environment and test loop. This document is the spec + onboarding so you
can build and certify the adapter without the Claude session's context. Build
and **test it in your own Codex environment** — the Claude side does not write
or test Codex host code (that host-isolation split is the whole point).

## 0. One-paragraph picture

`swarm-discussion-runtime` (this repo) is the host-agnostic source of truth:
the runtime CLI, protocol semantics, schemas, the vendorable bundle, and the
certification gates. A host adapter is a THIN shell that vendors the runtime at
a pinned SHA and maps the host's spawn/wait primitives to runtime commands. The
Claude adapter (`swarm-discussion-claude`) is built, certified, and
install-validated; you are building the Codex equivalent. The published
`swarm-discussion` repo will later become a thin aggregator of certified
adapter releases.

## 1. Read these first (authoritative, in order)

- `docs/ADAPTER-SPEC.md` — THE contract: deliverables, entry-contract must-nots,
  certification definition, versioning. Non-negotiable.
- `docs/HOST-ADAPTERS.md` — the Codex recipe, shared runtime flow, transport
  metadata, adapter-smoke.
- `docs/RUNTIME-PACKAGE-BOUNDARY.md` — skill / adapter / runtime ownership split.
- `runtime-contract.json` — machine-readable stable commands, integration gates,
  and the compatibility string (`swarm-runtime-v2-alpha`).
- `protocol/` — discussion semantics (modes, roles, phases, schema, prompts,
  persona generation). Vendored into your adapter; never fork it.

## 2. Two codebases to mirror / salvage

- **Reference implementation (mirror its structure):** `swarm-discussion-claude`
  (github.com/automann/swarm-discussion-claude). Layout: `.claude-plugin/`,
  `agents/`, `skills/swarm-discussion/SKILL.md`, `bin/swarm_runtime_wrapper.py`,
  `vendor/swarm-runtime/`, `README.md`, `AGENTS.md`. Your repo mirrors this with
  Codex-native equivalents.
- **Salvage source (Codex-native, already works):** the EXISTING Codex plugin at
  the `swarm-discussion` repo HEAD, `plugins/codex/`. It already contains:
  - `runtime/swarm_runtime_wrapper.py` — a working runtime-discovery wrapper.
  - `skills/swarm-discussion/SKILL.md` — a working ROOT-THREAD orchestrator skill
    with Codex installed-path resolution (`CODEX_HOME` / `find`-based).
  - `agents/swarm-expert.toml` — the Codex persona agent definition.
  - `protocol/` docs and a vendored runtime.
  REUSE these heavily — they encode hard-won Codex specifics (path resolution,
  `multi_agent_v1` primitives, the `max_depth` constraint).

## 3. THE pivotal design fork: nesting / topology

The Claude adapter uses a NESTED orchestrator: the skill spawns a
`swarm-orchestrator` SUB-agent that runs the whole discussion in its own context
and itself spawns persona sub-agents. That is possible only because Claude Code
supports sub-agent nesting (verified to depth ≥ 3).

Codex historically caps nesting at `agents.max_depth = 1`. The existing Codex
`SKILL.md` states: *"agents.max_depth = 1 forbids the orchestrator from being a
subagent that spawns personas. Run on the ROOT thread."* If that still holds on
your target Codex version, you MUST use the ROOT-THREAD topology: the skill runs
the protocol on the root thread and spawns persona experts directly (depth 1).
There is NO `swarm-orchestrator` sub-agent in that shape.

**Do this first, empirically — do not assume:**
- Verify your host's nesting: can a Codex sub-agent receive the spawn primitive
  and spawn its own sub-agent? (The Claude side proved nesting for Claude by
  spawning a coordinator that spawned workers and checking per-agent
  transcripts. Use an analogous concrete, non-self-replicating probe.)
- If depth-1 only (expected): build the ROOT-THREAD adapter (salvage the existing
  Codex `SKILL.md` shape). Your `doctor` records `hostNesting.supported=false`
  and the skill must NOT try to spawn an orchestrator sub-agent.
- If Codex now supports nesting: you MAY adopt the nested orchestrator shape
  (mirror `swarm-discussion-claude/agents/swarm-orchestrator.md`), but
  root-thread is the safe default and remains valid.

Either way the parent/root context stays thin: brief path, current phase, agent
ids, next helper command (`validate-host-step` enforces this).

## 4. Deliverables (ADAPTER-SPEC §Adapter deliverables, Codex-instantiated)

1. **Vendored runtime** at `vendor/swarm-runtime/` via this repo's
   `scripts/vendor.py`. Pin the SHA; never edit vendored files; re-vendor to
   update. Vendor at the latest runtime `main`; check what you actually vendored
   with `runtime-contract` (see §8 about the command surface).
2. **Thin wrapper:** adapt `plugins/codex/runtime/swarm_runtime_wrapper.py`. FIX
   the discovery paths to the vendor-bundle layout — runtime CLI at
   `vendor/swarm-runtime/runtime/swarm_rt.py`, fixture at
   `vendor/swarm-runtime/fixtures/e2e/minimal-v2`. Keep
   `COMPATIBILITY = "swarm-runtime-v2-alpha"`. Add a host nesting probe to
   `doctor`. The wrapper contains NO discussion mechanics.
3. **Skill / entry doc** (Codex `SKILL.md`): root-thread orchestrator (salvage
   the existing one) unless nesting is confirmed. Preflight with
   `wrapper doctor --smoke-fixture`; stop if it fails.
4. **Agent definitions:** `swarm-expert` (Codex `.toml`; read-only / no tools;
   salvage the existing `swarm-expert.toml`). Add a `swarm-orchestrator` agent
   ONLY if you adopt the nested shape.
5. **Host-native smoke:** drive ONE real Codex discussion end to end through the
   real host primitives, retain it (e.g. under `smoke/`), and certify it.

## 5. Codex host specifics (from HOST-ADAPTERS.md Codex recipe)

- Spawn primitive: `multi_agent_v1.spawn_agent`; wait: `multi_agent_v1.wait_agent`;
  `resultKey: "agent_id"`.
- Partial wait batches are EXPECTED. Pass EVERY partial `wait_agent` response to
  `transport-append-batch`; completion is keyed by `agent_id`, not arrival order.
- Per phase: `prompt-build` per persona → spawn from `prompt.txt` →
  `transport-init` with returned agent ids → `transport-append-batch` per wait
  batch → `transport-collect` → `append-message` per result → `checkpoint` →
  `finalize-round`.
- Treat raw Codex session logs as optional secondary evidence; rely on runtime
  artifacts for primary audit.

## 6. Build steps (each with a check)

1. Create repo `swarm-discussion-codex`; `git init`.
2. Vendor: `python3 <runtime>/scripts/vendor.py vendor --dest vendor/swarm-runtime`;
   then `... verify --dest vendor/swarm-runtime` (must pass).
3. Wrapper: adapt + fix paths. Check: `python3 bin/swarm_runtime_wrapper.py
   doctor --smoke-fixture` exits 0 (runtime resolved from vendored; fixture smoke
   `on-track`).
4. Skill + agent(s) per topology (root-thread default).
5. Drive a real Codex discussion → a discussion directory.
6. Certify (from THIS runtime repo):
   ```
   python3 conformance/certify_adapter.py \
     --discussion <dir> \
     --vendored  <codex-repo>/vendor/swarm-runtime \
     --runtime   <codex-repo>/vendor/swarm-runtime/runtime/swarm_rt.py
   ```
   All five gates must pass: `runtime-contract`, `vendor-manifest`,
   `adapter-smoke`, `validate-loop`, `validate-discussion`.

## 7. Entry contract — must-nots (honor exactly)

The orchestrator (root thread on Codex) may prepare compact temp inputs, call
host spawn/wait/close primitives, and pass raw host results to runtime commands.
It must NOT:
- derive persona prompt text without `prompt-build`;
- merge wait statuses outside `transport-collect` / `collect-merge`;
- mint message ids, edit committed round files, or patch WAL partials;
- reimplement any helper in `protocol/README.md`'s legacy-mechanics table;
- expand parent context beyond brief path, current phase, agent ids, next helper
  command;
- treat fixture-only gate results as a substitute for validating the real
  discussion tree;
- grant the spawn primitive to ordinary persona experts;
- spawn any agent with a self-replicating / "how deep can you go" prompt — every
  spawned agent gets a concrete, role-specific task.

## 8. Pitfalls learned building the Claude adapter (saves round-trips)

- **Align to the EXACT vendored runtime SHA's command surface.** The Claude
  adapter pinned `bed47da`, where: there is NO `init` command; `finalize-round`
  does NOT derive metadata; there is NO compact `--full` flag. So with that SHA
  you must: create `manifest.json` directly; supply `finalize-round` the full
  `metadata` (`messageCount`, `referenceCount`, `participants`) + `timestamp`;
  and do NOT pass `--full`. If you vendor a newer runtime where plans 001/002
  have landed (compact output, `init`, metadata derivation), prefer those and
  simplify — confirm against the `runtime-contract` of what you actually
  vendored.
- **Mirror the vendored fixture shapes EXACTLY** — the runtime validates
  strictly: gapless ids `r{N}-msg-NNN`; one `argumentGraph` edge
  `{from,to,relation}` per message reference; relation ∈
  {supports,counters,extends,questions}; metadata counts exact; synthesis
  non-empty. Copy shapes from
  `vendor/swarm-runtime/fixtures/e2e/minimal-v2/rounds/001.json` and
  `.../prompts/r001/response/architect/request.json`.
- **After finalize, set manifest `status` to `completed`** — required for `trace`
  `nextAction:none` / health `on-track` / `validate-loop`.
- **Use the host's namespaced agent type when plugin-installed** (the Claude
  adapter spawns `swarm-discussion:swarm-expert`, not bare `swarm-expert`); find
  the Codex equivalent.
- **Put transient inputs under `tmp/`,** not at `transport/` root.
- **Personas need no tools;** never grant them the spawn primitive.

## 9. Definition of done

- The plugin validates/installs in Codex; `doctor --smoke-fixture` passes.
- ONE real Codex-driven discussion certifies (all five gates) with the adapter's
  vendored bundle.
- ADAPTER-SPEC deliverables met; entry contract honored; `protocol/` not forked.
- Release notes state the pinned `runtimeSha` + compatibility string
  (`swarm-runtime-v2-alpha`).
- A PROGRESS/notes entry records the run and certification result.

## 10. When you finish

Report back the certified discussion path + the `certify_adapter.py` verdict so
the milestone can be checked in this repo's `ACCEPTANCE.md` (Adapter
Milestones), and so the aggregator can list your release.
