# Future Executors Research Notes

This repository is not ready to grant broad tools to discussion experts. Phase 6
defines the shape of future executor work without enabling it by default.

## Host Nesting Capability (verified 2026-06-11)

Earlier hosts capped sub-agent nesting at depth 1: a spawned agent could not
spawn its own sub-agents, so a coordinator HAD to be the root thread. That cap
is the main reason the coordinator role below was deferred.

On Claude Code 2.1.177 this was re-tested empirically and the cap is gone.
A root-spawned coordinator sub-agent spawned its own worker sub-agents (depth 2,
confirmed at the transcript level), and a three-role chain reached depth 3
(parent -> orchestrator -> persona-analogue -> scanner), proven by
child-before-parent completion ordering in a shared log, correct returned data,
and distinct per-agent transcripts. Depth >= 3 covers every realistic adapter
need; the documented "5 levels" ceiling was not pinned.

Methodology caveat that is itself a design constraint: capable agents correctly
REFUSE self-replicating ("spawn a copy of yourself") and limit-probing ("how
deep can you go") prompts. The depth measurement only succeeded with concrete,
distinct-role tasks. So any nested design here must give each sub-agent a
bounded, role-specific task — never a self-similar recursive prompt.

The adapter-facing consequence (orchestrator-as-sub-agent execution topology)
is specified in `docs/ADAPTER-SPEC.md`.

## Coordinator Adapter

With nesting verified (above), the coordinator can finally be a spawned
orchestrator sub-agent rather than the root thread: the parent spawns it, it
owns phase planning, agent selection, and fan-in timing, and it spawns persona
experts itself. It must still call runtime helpers for prompt-build,
collect-merge, WAL, trace, and evidence. The Phase 5 parent context surface now
bounds what the PARENT sends the orchestrator and what the orchestrator returns
— the verbose middle stays in the orchestrator's own (disposable) context.

Open questions:

- How should the coordinator choose between lightweight and deeper rounds?
- Which quality gates should be hard failures versus advisory trace findings?
- How should human intervention be represented in events?

## Readonly Executor

The first executor candidate is readonly inspection with `read`, `glob`, and
`grep`. It should write tool-evidence JSONL records and artifact files for every
claim it wants downstream agents to cite. With depth-3 nesting verified, such a
researcher can run as a sub-agent spawned by a persona expert (depth 3) — but
only when a capability profile authorizes that persona to spawn it, and only on
a host that permits the depth. The default persona stays no-tools and cannot
nest.

Readonly executor falsifiers:

- It cites repository facts without tool-evidence records.
- It asks for `bash`, `edit`, or `write` under an ordinary expert profile.
- It makes parent context larger instead of moving findings into artifacts.

## Broad Executor

Broad tools such as `bash`, `edit`, and `write` are intentionally out of scope
for ordinary experts in this phase. A future broad executor would need stronger
isolation, write scopes, artifact validation, and rollback semantics before it
can be considered.
