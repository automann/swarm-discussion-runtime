# Acceptance Criteria

## First Proof Point

The first implementation proof point is:

```text
brief -> prompt-build -> collect-merge -> WAL -> validate -> trace/evidence
```

This proof point passes when a fixture-backed discussion can be processed by
runtime commands without a live host session and produces:

- prompt-build artifacts,
- merged fan-in result,
- committed round JSON,
- directory validation result,
- trace JSON,
- evidence JSON.

## Skeleton Acceptance

- Repository has governance docs.
- Runtime package has a minimal CLI.
- Planned command set is explicit.
- Tests pass locally.

## Runtime Acceptance

For a fixture discussion:

- `collect-merge` reports missing agent ids until all required results exist.
- Message ids are gapless and round-scoped.
- References resolve to present message ids.
- Relation labels are closed over the allowed enum:
  `supports`, `counters`, `extends`, `questions`.
- Position shifts cite trigger ids visible to the persona in full.
- `validate-discussion` catches missing summary, stale partials, leftover tmp,
  and missing artifacts.
- Trace suggests a next action for incomplete or failed discussions.
- Evidence is enough for a smoke audit before opening host JSONL logs.

## Falsifiers

Revise the architecture if:

- runtime helpers increase parent-agent context burden instead of reducing it,
- prompt-build artifacts are too noisy to audit,
- evidence cannot prove transport behavior without host logs,
- host runtimes expose a stable top-level coordinator that makes this shape
  obsolete,
- the project goal shifts from discussion/decision runtime to autonomous code
  delivery.

## Completion Definition For Incubator

The incubator is ready to integrate back into the plugin line when:

- the first proof point passes,
- real legacy smoke fixtures are represented,
- CLI commands are documented,
- core commands have tests,
- trace/evidence works on at least one real discussion artifact,
- the old plugin can call the runtime for one lightweight phase without manual
  JSON assembly.
