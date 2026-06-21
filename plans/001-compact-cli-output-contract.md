# Plan 001: Make CLI stdout compact by default so command output stops polluting the orchestrator's context

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bed47da..HEAD -- runtime/swarm_rt.py runtime/swarm/prompt.py tests/ docs/ADAPTER-SPEC.md docs/HOST-ADAPTERS.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2 (was P1 — see re-scope note below)
- **Effort**: M
- **Risk**: MED (changes CLI stdout shapes; no external adapter exists yet, so this is the last cheap moment)
- **Depends on**: none
- **Category**: tech-debt (intent-alignment)
- **Planned at**: commit `bed47da`, 2026-06-11

## Re-scope note (2026-06-11, nested-orchestrator verification)

This plan was P1 on the premise that verbose CLI stdout pollutes the *parent
agent's* scarce context window. Sub-agent nesting is now verified on Claude
Code (depth >= 3; see `docs/FUTURE-EXECUTORS.md`), so the adapter runs the
orchestrator as a *disposable sub-agent* (`docs/ADAPTER-SPEC.md` Execution
topology). Verbose stdout now pollutes the orchestrator's own context, which is
discarded when it returns to the parent — not the user's main thread. That
makes this an orchestrator efficiency/cost optimization rather than a
parent-context protection, so it drops to P2. Still worth doing (a leaner loop
is cheaper and lets the orchestrator survive longer discussions), and still the
last cheap moment to change stdout shapes before an adapter depends on them.

## Why this matters

This runtime exists to keep discussion mechanics OUT of the parent LLM
orchestrator's context window (see the README "Thesis" section). But every CLI
command prints its full JSON result to stdout,
and the orchestrator pays context tokens for every byte. Worst case:
`prompt-build` prints the ENTIRE generated expert prompt to stdout (measured
2,606 bytes on the small phase2 fixture) even when `--out-dir` already wrote
it to disk — the parent receives the exact text the architecture says it must
never carry. `trace` (4,955 B), `evidence` (5,540 B), and `adapter-smoke`
(4,671 B) are similar on small fixtures and grow with discussion size. After
this plan, every command prints a compact summary envelope by default, full
payloads go to artifact files, and a `--full` flag restores the old behavior
for debugging.

## Current state

- `runtime/swarm_rt.py` — the only CLI entrypoint. `emit()` at line ~31:

  ```python
  def emit(payload: dict[str, Any]) -> None:
      print(json.dumps(payload, indent=2, sort_keys=True))
  ```

  Every `cmd_*` function ends with `emit(result)` and `return 0 if result["ok"] else 1`.

- `cmd_prompt_build` (line ~130) emits the full result of `build_prompt`,
  which includes `"prompt"` (the full prompt text, `runtime/swarm/prompt.py:383`),
  `"visibility"` (a dict with one entry per message id), and
  `"injectedMessageIds"` — even when `--out-dir` wrote `prompt.txt` and
  `prompt-build.json`.

- `cmd_trace` (line ~170) and `cmd_evidence` (line ~178) support `--output`
  but ALSO always emit the full payload to stdout.

- `cmd_transport_collect` (line ~213) emits the full merge result including
  every expert's completed payload, which is also written to
  `collect-result.json`.

- Repo conventions: stdlib only (no new runtime deps); results are dicts with
  `ok`/`errors`; errors use `{"code","path","message","value?"}` shape; tests
  live in `tests/test_*.py` and call the CLI via a `run_cli(*args)` helper
  (see `tests/test_phase1_collect_merge.py:20-27` for the pattern).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Tests | `.venv/bin/python -m pytest -q` | all pass, exit 0 |
| One file | `.venv/bin/python -m pytest tests/test_cli_output_contract.py -q` | all pass |
| Smoke | `python3 runtime/swarm_rt.py trace --dir fixtures/e2e/minimal-v2` | exit 0, compact JSON |

Note: `python3 -m pytest` does NOT work (pytest only in `.venv`).

## Scope

**In scope** (the only files you should modify):
- `runtime/swarm_rt.py`
- `tests/test_cli_output_contract.py` (create)
- Existing tests that assert on full stdout payloads (listed in Step 5)
- `docs/ADAPTER-SPEC.md`, `docs/HOST-ADAPTERS.md` (document the envelope + `--full`)
- `PROGRESS.md` (append a round entry; follow the existing entry template at the top of the file)

**Out of scope** (do NOT touch):
- `runtime/swarm/*.py` library functions and their return values — the
  compaction happens ONLY at the CLI layer in `swarm_rt.py`. Library callers
  (tests, `smoke.py`, `loop.py`) must keep receiving full dicts.
- `runtime-contract.json` / `schemas/` — the contract names commands and
  artifacts, not stdout shapes; no change needed.
- Artifact file contents (`prompt-build.json`, `collect-result.json`,
  `--output` files) — these stay FULL payloads, unchanged.
- Error behavior: when `ok` is false, ALWAYS print the full `errors` array
  (fail-loud is a repo principle; never truncate errors).

## Git workflow

- Work on `main` (repo convention: single-commit rounds on main).
- One commit, message style from `git log`: `feat: compact CLI output contract` style (`<type>: <imperative>`).
- Do NOT push.

## Steps

### Step 1: Add the summary layer in `swarm_rt.py`

Add a module-level helper and a shared `--full` flag:

```python
def emit_summary(result: dict[str, Any], summary: dict[str, Any], full: bool) -> None:
    if full or not result.get("ok", False):
        emit(result)
        return
    emit(summary)
```

Rules: on failure (`ok: false`) the FULL result is always printed. On success
with `--full`, full result. Otherwise the compact summary. Add
`parser.add_argument("--full", action="store_true", help="Print the full JSON result instead of the compact summary")`
to every subcommand listed in Step 2 (add it per-subparser, not globally —
argparse subparsers do not inherit root flags).

**Verify**: `python3 runtime/swarm_rt.py health` → unchanged output, exit 0.

### Step 2: Apply per-command compact summaries

Target stdout envelope per command (each always includes `"ok"`; keys below
in addition). Where a path is mentioned, it is a string path to the artifact
holding the full payload.

| Command | Compact stdout keys |
|---|---|
| `prompt-build` | `phase`, `persona` (id only), `promptSha256`, `promptCharCount` (= `len(result["prompt"])`), `visibilityCounts` (e.g. `{"full": 2, "gist": 1}`), `artifactPaths` (when `--out-dir` given) |
| `context-build` | `summarySha256`, `summary` (the small dict from `build_context_summary`: discussionId/topic/mode/charCount), `summaryPath` (when `--out` given) |
| `collect-merge` | `complete`, `timedOut`, `missingAgentIds`, `receivedAgentIds`, `resultCount` (= `len(results)`), `errors` |
| `transport-collect` | `complete` (from `result["result"]["complete"]`), `timedOut`, `missingAgentIds`, `resultCount`, `collectResultPath` (from `result["paths"]["collectResultPath"]`), `errors` |
| `transport-init` | `paths`, `parentContext` (the 4-field surface from `result["hostStep"]["parentContext"]`) |
| `transport-append-batch` | `path` |
| `append-message` | `messageId` (= `result["message"]["id"]`), `from` (sender), `checkpointPath` (= `result["checkpoint"]["path"]`) |
| `checkpoint` | `round`, `phase`, `path` |
| `finalize-round` | `round`, `path`, `warnings` |
| `resume-plan` | unchanged (already compact) |
| `trace` | `health`, `nextAction`, `validationOk` (= `result["validation"]["ok"]`), `errorCounts` (validation error count), `outputPath` (when `--output` given) |
| `evidence` | `outcome`, `metrics`, `health` (= `result["trace"]["health"]`), `outputPath` (when `--output` given) |
| `adapter-smoke` | `summary` (the existing summary block), `errors` |
| `validate-loop` | `summary`, `errors` |
| `validate-round` / `validate-discussion` | `summary`, `warnings` count, `errors` |
| `runtime-contract` | `validation.summary` + `ok` (drop the full contract echo) |
| `capability-doctor` | `effective`, `toolEvidence` counts (`recordCount`, `acceptedCount`, `citable`), `errors` |

Implementation note: build each summary dict inside the `cmd_*` function from
the full `result` you already have; do not change the library functions.

**Verify**: `python3 runtime/swarm_rt.py prompt-build --request fixtures/phase2/prompt-requests/response.json --out-dir /tmp/p001 | python3 -c "import json,sys; r=json.load(sys.stdin); assert 'prompt' not in r, 'prompt text leaked'; assert r['promptCharCount'] > 0; print('compact OK')"` → `compact OK`

### Step 3: Confirm failure outputs stay full

**Verify**: `python3 runtime/swarm_rt.py validate-discussion fixtures/legacy/wails-vs-electron-kanban | python3 -c "import json,sys; r=json.load(sys.stdin); assert r['ok'] is False and any(e['code']=='missing_summary' for e in r['errors']); print('failure stays full')"` → `failure stays full` (exit code of the CLI is 1 — pipe still works).

### Step 4: Confirm `--full` restores old behavior

**Verify**: `python3 runtime/swarm_rt.py trace --dir fixtures/e2e/minimal-v2 --full | python3 -c "import json,sys; r=json.load(sys.stdin); assert 'artifacts' in r and 'rounds' in r; print('full OK')"` → `full OK`

### Step 5: Update existing tests that read removed stdout fields

Run `.venv/bin/python -m pytest -q` and fix failures. Expected touch points
(use `--full` in the CLI invocation OR assert on the new compact keys —
prefer asserting compact keys, since the compact envelope is now the
contract):

- `tests/test_phase1_collect_merge.py` — CLI tests read `payload["complete"]`,
  `payload["missingAgentIds"]`, `payload["receivedAgentIds"]`: all present in
  the compact envelope; should pass unchanged. Confirm.
- `tests/test_phase2_context_prompt.py` — CLI prompt-build assertions on
  `artifactPaths` keep working; any assertion on `payload["prompt"]` or
  `payload["visibility"]` must read `/tmp.../prompt-build.json` instead.
- `tests/test_phase4_trace_evidence.py` — CLI evidence round-trip reads
  `payload["outcome"]`: present in compact envelope.
- `tests/test_adapter_smoke.py`, `tests/test_e2e_minimal_loop.py` — read
  `payload["summary"]`: present.
- `tests/test_phase3_wal.py::test_checkpoint_cli_writes_partial_and_event_log`
  — reads `payload["ok"]` only: fine.
- `tests/test_e2e_fresh_loop.py` — `run_cli` parses many commands; update
  assertions: `init_result["hostStep"]["parentContext"]` →
  `init_result["parentContext"]`; `collect_result["result"]["complete"]` →
  `collect_result["complete"]`; `trace["health"]`, `evidence["outcome"]` stay.

**Verify**: `.venv/bin/python -m pytest -q` → all pass.

### Step 6: Add the contract test

Create `tests/test_cli_output_contract.py` (model after
`tests/test_phase1_collect_merge.py` for the `run_cli` helper). Cases:

1. `prompt-build` stdout contains no `"prompt"` key and no `"visibility"` map;
   contains `promptSha256`, `promptCharCount`, `visibilityCounts`.
2. `trace --dir fixtures/e2e/minimal-v2` stdout < 1500 bytes; contains
   `health` and `nextAction`.
3. `evidence --dir fixtures/e2e/minimal-v2` stdout < 2500 bytes; contains
   `outcome` and `metrics`.
4. `trace ... --full` stdout contains the `artifacts` key.
5. A failing command (e.g. `validate-discussion` on
   `fixtures/legacy/install-verify-tabs-spaces`) prints the full `errors`
   array even without `--full`.

**Verify**: `.venv/bin/python -m pytest tests/test_cli_output_contract.py -q` → 5 passed.

### Step 7: Update docs and PROGRESS

- `docs/ADAPTER-SPEC.md`: in the wrapper deliverable section, add one
  paragraph: stdout is a compact summary envelope; full payloads live in
  artifacts; `--full` exists for debugging; failures always print full errors.
- `docs/HOST-ADAPTERS.md`: same note where command output is described.
- Append a `PROGRESS.md` entry following the template at the top of that file.

**Verify**: `.venv/bin/python -m pytest -q` → all pass.

## Test plan

Covered by Steps 5–6: one new test file with 5 cases (no-leak, size caps,
`--full` escape, fail-loud) plus updated assertions in the existing CLI tests.

## Done criteria

- [ ] `.venv/bin/python -m pytest -q` exits 0
- [ ] `python3 runtime/swarm_rt.py prompt-build --request fixtures/phase2/prompt-requests/response.json | grep -c '"prompt"'` → `0` (key absent)
- [ ] `python3 runtime/swarm_rt.py trace --dir fixtures/e2e/minimal-v2 | wc -c` → less than 1500
- [ ] Failing commands still print full `errors` (Step 3 check passes)
- [ ] `git status` shows no modified files outside the in-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- `runtime/swarm_rt.py` no longer matches the excerpts (e.g. `emit()` already
  changed or a summary mode already exists).
- Making a test pass appears to require changing a library function's return
  value in `runtime/swarm/*.py` (out of scope — the compaction is CLI-only).
- More than ~10 existing tests fail after Step 2 (suggests the envelope
  design conflicts with the test suite more than anticipated).

## Maintenance notes

- Future commands must ship a compact envelope from day one; reviewers should
  reject `emit(result)` on a success path for any new command.
- Deliberately deferred: `transport-collect` still requires the orchestrator
  to read `collect-result.json` if it wants expert payloads to compose
  `append-message` calls. A future `append-from-collect` command (runtime
  composes messages directly from the collect artifact) would remove that
  last payload transfer entirely — design question, not in this plan.
- Plan 004 (metrics) extends the `evidence` compact envelope; land this first.
