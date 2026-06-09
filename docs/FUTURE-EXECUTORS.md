# Future Executors Research Notes

This repository is not ready to grant broad tools to discussion experts. Phase 6
defines the shape of future executor work without enabling it by default.

## Coordinator Adapter

A future coordinator may own phase planning, agent selection, and fan-in timing.
It should still call runtime helpers for prompt-build, collect-merge, WAL,
trace, and evidence. The parent context surface from Phase 5 remains the upper
bound for what the root agent carries between steps.

Open questions:

- How should the coordinator choose between lightweight and deeper rounds?
- Which quality gates should be hard failures versus advisory trace findings?
- How should human intervention be represented in events?

## Readonly Executor

The first executor candidate is readonly inspection with `read`, `glob`, and
`grep`. It should write tool-evidence JSONL records and artifact files for every
claim it wants downstream agents to cite.

Readonly executor falsifiers:

- It cites repository facts without tool-evidence records.
- It asks for `bash`, `edit`, or `write` under an ordinary expert profile.
- It makes parent context larger instead of moving findings into artifacts.

## Broad Executor

Broad tools such as `bash`, `edit`, and `write` are intentionally out of scope
for ordinary experts in this phase. A future broad executor would need stronger
isolation, write scopes, artifact validation, and rollback semantics before it
can be considered.
