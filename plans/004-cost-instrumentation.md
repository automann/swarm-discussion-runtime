# Plan 004: Instrument prompt sizes, artifact sizes, and phase durations so the founding "too slow, too many tokens" complaint becomes measurable

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bed47da..HEAD -- runtime/swarm/prompt.py runtime/swarm/audit.py schemas/prompt-build.schema.json schemas/evidence.schema.json tests/`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition. NOTE: plans 001 and 003 are
> EXPECTED to have landed first — their changes to `swarm_rt.py` stdout and
> the new `tests/test_schema_conformance.py` are not drift.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW (additive fields only)
- **Depends on**: plans/001 (evidence compact envelope includes `metrics`), plans/003 (schema conformance tests force the schema updates here)
- **Category**: direction (intent-alignment)
- **Planned at**: commit `bed47da`, 2026-06-11

## Why this matters

The founding problem statement (`original-intent-of-why-to-rewrite.md`)
complains that "even lightweight discussions require longer times and more
token overhead". The repo has ZERO instrumentation for this: no prompt sizes,
no artifact sizes, no durations. `ACCEPTANCE.md` even lists the falsifier
"runtime helpers increase parent-agent context burden instead of reducing it"
— currently untestable. After this plan, every prompt-build artifact records
its size, trace/evidence aggregate size and duration metrics, and the
old-vs-new benchmark (deferred until the first adapter ships) has the data it
needs on the runtime side.

## Current state

- `runtime/swarm/prompt.py:374-390` — `build_prompt` returns (excerpt):

  ```python
  return {
      "ok": True,
      ...
      "prompt": prompt,
      "promptSha256": _sha256(prompt),
      ...
  }
  ```

  There is no `promptCharCount`. The context-summary builder
  (`runtime/swarm/context.py:109-114`) already records a `charCount` in its
  summary block — use the same naming style.

- `runtime/swarm/audit.py` —
  - `_prompt_summary(discussion_dir)` (~line 150) loads every
    `prompts/**/prompt-build.json`, counts phases/personas/visibility, but no
    sizes.
  - `_events_summary` loads `events.jsonl`; events carry an ISO-8601 UTC
    `ts` field (written by `wal.py:append_event`) but nothing computes a time
    span.
  - `_metrics(trace)` (~line 520) returns counts only: `artifactCount`,
    `promptBuildCount`, `collectResultCount`, `toolEvidenceRecordCount`,
    `citableToolEvidenceCount`, `finalRoundCount`, `partialRoundCount`,
    `eventCount`, `validationErrorCount`.
  - `_artifact_paths(discussion_dir)` walks all files (excluding `tmp/`) and
    returns paths — sizes are one `stat` away.
- `schemas/prompt-build.schema.json` and `schemas/evidence.schema.json`
  describe these artifacts; plan 003's conformance tests validate builder
  outputs against them, so schema updates are REQUIRED here, in the same
  commit.
- Convention: all new fields additive and optional; deterministic where
  possible (sizes are deterministic; durations derive from recorded `ts`
  values in artifacts, never from wall-clock at trace time).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Tests | `.venv/bin/python -m pytest -q` | all pass |
| Conformance only | `.venv/bin/python -m pytest tests/test_schema_conformance.py -q` | all pass |
| Live check | `python3 runtime/swarm_rt.py evidence --dir fixtures/legacy/tauri-vs-electron-kanban --full` | exit 0 |

## Scope

**In scope**:
- `runtime/swarm/prompt.py` (add `promptCharCount`, `contextSummaryCharCount`)
- `runtime/swarm/audit.py` (size + duration aggregation in `_prompt_summary`,
  `_events_summary`, `_artifact_paths` callers, `_metrics`)
- `schemas/prompt-build.schema.json`, `schemas/evidence.schema.json`
  (declare the new optional fields)
- `fixtures/e2e/minimal-v2/artifacts/trace.json` and `evidence.json` —
  regenerate via the CLI after the change (they are CLI-generated anchors;
  see the regeneration commands in Step 5)
- `tests/test_phase2_context_prompt.py`, `tests/test_phase4_trace_evidence.py`
  (new assertions)
- `PROGRESS.md` (round entry)

**Out of scope**:
- Token counting. Record CHAR counts only — tokens are model-specific and
  belong to adapters/hosts. Do not add a tokenizer or estimate ratios.
- Host wall-clock measurement (spawn-to-completion latency) — that data lives
  in host adapters; the runtime only aggregates the timestamps it already
  records in `events.jsonl`.
- `runtime/swarm/wal.py` — `append_event` already records `ts`; no change.

## Git workflow

- Work on `main`; one commit: `feat: record prompt sizes and duration metrics in audit artifacts`.
- Do NOT push.

## Steps

### Step 1: `promptCharCount` in prompt-build artifacts

In `runtime/swarm/prompt.py`'s success return (line ~374), add:

```python
"promptCharCount": len(prompt),
"contextSummaryCharCount": len(context_summary),
```

(`context_summary` is the variable already in scope, used for
`contextSummarySha256`.) Update `schemas/prompt-build.schema.json`: add both
as optional `"type": "integer"` properties (do NOT add to `required` — old
artifacts must stay valid).

**Verify**: `.venv/bin/python -m pytest tests/test_schema_conformance.py tests/test_phase2_context_prompt.py -q` → all pass.

### Step 2: Aggregate prompt sizes in `_prompt_summary`

In `runtime/swarm/audit.py:_prompt_summary`, while iterating artifacts, sum
`payload.get("promptCharCount")` when it is an `int` (skip otherwise — old
artifacts lack it) and track the max. Add to the returned dict:

```python
"promptCharTotal": prompt_char_total,
"promptCharMax": prompt_char_max,
"promptCharCounted": counted,   # how many artifacts actually carried the field
```

### Step 3: Duration span in `_events_summary`

`events.jsonl` events carry `ts` (ISO `YYYY-MM-DDTHH:MM:SSZ`). In
`_events_summary`, when ≥2 events parse, compute:

```python
"firstTs": <ts of first event>, "lastTs": <ts of last event>,
"spanSeconds": <int difference>,
```

Parse with `datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")` inside a
`try/except (ValueError, TypeError)` — on any unparseable ts, set all three
to `None` (never raise; trace must survive malformed artifacts — repo
principle).

### Step 4: Sizes and new `_metrics` fields

Where `build_trace` calls `_artifact_paths`, also compute total bytes
(`Path(p).stat().st_size`, guarded by `OSError → skip`) and add
`"totalBytes"` to the trace `artifacts` block. Extend `_metrics(trace)` with:

```python
"promptCharTotal": trace.get("prompts", {}).get("promptCharTotal", 0),
"promptCharMax": trace.get("prompts", {}).get("promptCharMax", 0),
"artifactTotalBytes": trace.get("artifacts", {}).get("totalBytes", 0),
"eventSpanSeconds": trace.get("events", {}).get("spanSeconds"),
```

Update `schemas/evidence.schema.json`: the `metrics` object — if it declares
`additionalProperties: false`, add the four new optional properties; if it is
open, still document them as properties. Never extend `required`.

**Verify**: `.venv/bin/python -m pytest tests/test_schema_conformance.py -q` → all pass.

### Step 5: Regenerate the fixture anchors

The committed minimal-v2 anchors are real CLI output and must reflect the new
fields:

```bash
python3 runtime/swarm_rt.py trace --dir fixtures/e2e/minimal-v2 --output fixtures/e2e/minimal-v2/artifacts/trace.json
python3 runtime/swarm_rt.py evidence --dir fixtures/e2e/minimal-v2 --output fixtures/e2e/minimal-v2/artifacts/evidence.json
```

(If plan 001 landed, these print compact envelopes — fine; the `--output`
files carry the full payloads.)

**Verify**: `.venv/bin/python -m pytest -q` → all pass (validate-loop checks the anchor's required keys; conformance tests check schema fit).

### Step 6: Pin with tests

- `tests/test_phase2_context_prompt.py`: extend an existing prompt-build test
  to assert `result["promptCharCount"] == len(result["prompt"])`.
- `tests/test_phase4_trace_evidence.py`: add
  `test_metrics_include_size_and_duration` — build trace+evidence over the
  enriched tmp discussion (use the existing `copy_complete_discussion` +
  `enrich_discussion_for_audit` helpers in that file), assert
  `evidence["metrics"]["promptCharTotal"] > 0`,
  `evidence["metrics"]["artifactTotalBytes"] > 0`, and
  `evidence["metrics"]["eventSpanSeconds"] >= 0` (the enrich helper writes
  two events 1 second apart).
- Same file: add `test_metrics_survive_artifacts_without_char_counts` — run
  build_evidence over `fixtures/legacy/tauri-vs-electron-kanban` (its
  artifacts predate the field), assert it still returns `ok: True` with
  `promptCharTotal == 0` and no exception.

**Verify**: `.venv/bin/python -m pytest -q` → all pass, ≥3 new tests.

### Step 7: PROGRESS entry

Append a `PROGRESS.md` round entry. Mention that the old-vs-new benchmark
(comparing a legacy fixture topic against a runtime-backed re-run) is now
unblocked on the runtime side and deferred until the first adapter ships.

## Test plan

See Step 6 — three new assertions/tests plus the conformance suite from plan
003 acting as the schema gate. Pattern files named in each bullet.

## Done criteria

- [ ] `.venv/bin/python -m pytest -q` exits 0
- [ ] `python3 runtime/swarm_rt.py evidence --dir fixtures/e2e/minimal-v2 --full | python3 -c "import json,sys; m=json.load(sys.stdin)['metrics']; assert m['promptCharTotal']>0 and m['artifactTotalBytes']>0; print('metrics OK')"` → `metrics OK`
- [ ] Legacy fixture still builds evidence cleanly (no-crash on missing fields)
- [ ] Both schemas updated; conformance tests pass
- [ ] Fixture anchors regenerated (git diff shows them updated)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- Plan 003 has NOT landed (no `tests/test_schema_conformance.py`) — land it
  first or report; without it the schema edits here are unverified.
- `schemas/evidence.schema.json`'s `metrics` definition does not match the
  shape described above (drift) — report before editing.
- Regenerating fixture anchors changes anything beyond the expected new
  fields + `generatedAt` (suggests an unrelated behavior change leaked in).

## Maintenance notes

- These are CHAR counts; if an adapter wants token estimates it converts at
  its own layer. Resist adding tokenizers to the runtime.
- `eventSpanSeconds` only measures first-to-last recorded event; per-phase
  latency attribution needs phase-boundary events — a future round can add
  `phase_started` events to `transport-init`/`append-message` if the
  benchmark shows the need.
- The deferred benchmark (post-first-adapter): re-run one legacy kanban topic
  through the certified adapter; compare `metrics` + wall-clock + qualityScore
  against `fixtures/legacy/`. Record the obligation in ACCEPTANCE.md when the
  adapter milestone lands.
