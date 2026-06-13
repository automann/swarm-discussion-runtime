# Plan 006: Consolidate duplicated private helpers into one shared module

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bed47da..HEAD -- runtime/swarm/`
> This plan touches nearly every runtime module, so it is numbered LAST: run
> it only after plans 001–004 are DONE or explicitly skipped (their diffs
> would otherwise conflict with this one). If other plans are still TODO in
> `plans/README.md`, treat that as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S/M
- **Risk**: LOW (pure refactor, behavior-identical; the 167+-test suite is the gate)
- **Depends on**: plans/001, 002, 003, 004 (ordering only — avoids merge churn)
- **Category**: tech-debt
- **Planned at**: commit `bed47da`, 2026-06-11

## Why this matters

Four helper definitions are copy-pasted across the runtime package:
`_issue()` in ~11 modules, `_load_json()` in 5 modules with 3 different
signatures, `_fsync_dir()` in 2, and the `MESSAGE_ID` regex in 2. During the
recent hardening round the two `MESSAGE_ID` copies had to be changed in
lockstep (`\d{3}` → `\d{3,}`) — exactly the drift hazard this duplication
creates. One shared module removes the hazard without adding dependencies.

## Current state

All in `runtime/swarm/`:

- `_issue(code, path, message, value=None) -> dict` — defined identically in
  `wal.py`, `audit.py`, `validation.py`, `transport.py`, `loop.py`,
  `contract.py`, `prompt.py`, `smoke.py`, `context.py`, `adapter.py`,
  `capabilities.py`:

  ```python
  def _issue(code: str, path: str, message: str, value: Any = None) -> dict[str, Any]:
      issue = {"code": code, "path": path, "message": message}
      if value is not None:
          issue["value"] = value
      return issue
  ```

- `_fsync_dir(path)` — byte-identical in `wal.py:37-45` and
  `transport.py:30-38` (open dir fd, fsync, swallow OSError).
- `MESSAGE_ID = re.compile(r"^r(\d+)-msg-(\d{3,})$")` — in `wal.py:14` and
  `validation.py:11`.
- `_load_json` variants:
  - `audit.py`, `smoke.py`, `loop.py`: `(path) -> tuple[payload|None, issue|None]`
    catching FileNotFoundError → `missing_file`, JSONDecodeError → `invalid_json`.
  - `transport.py`: same tuple shape but also catches OSError →
    `unreadable_file`.
  - `validation.py`: `_load_json(path, errors, label) -> Any` — appends to a
    caller list instead of returning a tuple.
  - (`wal.py._read_json` has different semantics — requires a dict payload,
    returns `invalid_state` — treat as related but distinct; see Step 3.)
- Package layout: modules import each other as `from swarm.x import y`
  (pythonpath is `runtime/`, set in `pyproject.toml`).
- Public API note: `tests/` import library functions directly; nothing
  imports the private helpers themselves (verify in Step 1).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Tests | `.venv/bin/python -m pytest -q` | all pass |
| Helper usage scan | `grep -rn "def _issue" runtime/swarm/` | see step targets |

## Scope

**In scope**:
- `runtime/swarm/_shared.py` (create)
- All `runtime/swarm/*.py` modules listed above (imports + deletion of local copies)
- `PROGRESS.md` (round entry)

**Out of scope**:
- ANY behavior change: error codes, messages, return shapes, and error
  ordering must be byte-identical. This is verifiable: the full test suite
  pins error codes extensively.
- `runtime/swarm_rt.py` — its `CliInputError`/`load_json` are CLI-layer
  concerns with different error envelopes; leave them.
- `conformance/`, `scripts/` — standalone scripts, intentionally self-contained.
- Renaming public functions or changing `swarm/__init__.py` exports.

## Git workflow

- Work on `main`; one commit: `refactor: consolidate shared runtime helpers`.
- Do NOT push.

## Steps

### Step 1: Confirm nothing external imports the private helpers

**Verify**: `grep -rn "import _issue\|from swarm.wal import _\|from swarm.validation import _" tests/ runtime/swarm_rt.py` → 0 matches (if any appear, STOP).

### Step 2: Create `runtime/swarm/_shared.py`

Contents: `issue()` (the `_issue` body above), `fsync_dir()` (from `wal.py`),
`MESSAGE_ID` (the compiled regex), and `load_json()` standardized on the
widest variant (transport.py's: catches OSError → `unreadable_file`,
FileNotFoundError → `missing_file`, JSONDecodeError → `invalid_json`;
returns `tuple[Any | None, dict | None]`). Module docstring: "Private shared
helpers for the swarm runtime package. Not part of the adapter-facing API."

**Verify**: `.venv/bin/python -c "import sys; sys.path.insert(0,'runtime'); from swarm._shared import issue, fsync_dir, MESSAGE_ID, load_json; print('shared OK')"` → `shared OK`.

### Step 3: Migrate module by module, running tests after EACH module

For each of the 11 modules, delete the local `_issue` and add
`from swarm._shared import issue as _issue` (keeping the local `_issue` name
so call sites are untouched). Likewise `_fsync_dir` → `fsync_dir as _fsync_dir`
in `wal.py`/`transport.py`, and `MESSAGE_ID` imported in `wal.py` and
`validation.py`. For `_load_json`: migrate `audit.py`, `smoke.py`, `loop.py`,
`transport.py` to `from swarm._shared import load_json as _load_json` — note
this ADDs OSError handling to the first three; that is a strict robustness
widening with the same error shape, acceptable. Leave `validation.py`'s
list-appending `_load_json` as a thin local wrapper that CALLS the shared
one:

```python
def _load_json(path: Path, errors: list[dict[str, Any]], label: str) -> Any:
    payload, issue_ = load_json(path)
    if issue_ is not None:
        errors.append({**issue_, "path": label})
        return None
    return payload
```

CAUTION: the existing validation.py variant reports `missing_file` with the
label as path and message `f"missing file: {path}"` — preserve those exact
message/path semantics (check the current implementation and match it; the
suite pins codes, and `test_trace_does_not_double_report_missing_manifest`
counts manifest errors). Leave `wal.py:_read_json` in place but have it call
`load_json` internally and keep its extra `invalid_state` non-dict check.

**Verify after each module**: `.venv/bin/python -m pytest -q` → all pass.

### Step 4: Prove the duplication is gone

**Verify**:
- `grep -rln "def _issue" runtime/swarm/ | grep -v _shared` → 0 files
- `grep -rln "def _fsync_dir" runtime/swarm/ | grep -v _shared` → 0 files
- `grep -rn "re.compile(r\"^r" runtime/swarm/ | grep -v _shared` → 0 matches

### Step 5: PROGRESS entry

Append a `PROGRESS.md` round entry (template at top of that file).

**Verify**: `.venv/bin/python -m pytest -q` → all pass.

## Test plan

No new tests — the existing suite (167+ tests, heavily pinned on error codes
and shapes) IS the regression net; the migration is done module-by-module
with a full-suite run between each.

## Done criteria

- [ ] `.venv/bin/python -m pytest -q` exits 0
- [ ] Step 4 greps all return zero
- [ ] `runtime/swarm/_shared.py` exists with the four helpers
- [ ] `git diff --stat` shows only `runtime/swarm/*.py`, `PROGRESS.md`, `plans/README.md`
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- Any plan 001–004 is still TODO in `plans/README.md` (ordering conflict).
- Step 1 grep finds external imports of the private helpers.
- Any single module migration breaks more than 3 tests (suggests a semantic
  difference between the local helper and the shared one — diff them
  carefully and report).

## Maintenance notes

- New modules must import from `_shared` instead of pasting helpers —
  reviewers should reject new `def _issue(` definitions.
- `_shared` is private (underscore) — it must never appear in
  `docs/ADAPTER-SPEC.md` or the runtime contract; adapters call the CLI, not
  the package.
