# Plan 002: Stop forcing the orchestrator to hand-assemble JSON — finalize-round derives metadata, new `init` scaffolds the discussion

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bed47da..HEAD -- runtime/swarm/wal.py runtime/swarm_rt.py runtime/swarm/__init__.py runtime-contract.json tests/test_phase3_wal.py tests/test_e2e_fresh_loop.py tests/test_runtime_contract.py docs/`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (API contract additions; backward compatible by design)
- **Depends on**: none (coordinates with plan 001 if both land — see notes)
- **Category**: tech-debt (intent-alignment)
- **Planned at**: commit `bed47da`, 2026-06-11

## Why this matters

`ARCHITECTURE.md`'s responsibility table says the parent agent must not own
"JSON artifact construction" — yet the runtime's own API forces exactly that
in two places. (1) `finalize-round` requires the caller to hand-assemble
`metadata` (`messageCount`, `referenceCount`, `participants`) and `timestamp`
even though the runtime already computes those counts during validation.
(2) There is no `init` command, so the orchestrator hand-writes
`manifest.json`. Both violate the founding goal (reduce parent
responsibility) and both shapes freeze the moment the first host adapter
ships, so this is the last cheap moment to fix them.

## Current state

- `runtime/swarm/wal.py:357` — `finalize_round(discussion_dir, round_id, final_state)`
  runs `_round_guard`, then `validate_round_record(final_state)`. The
  validator (`runtime/swarm/validation.py`, `validate_round_record`) errors
  with `missing_field` for absent `topic`, `mode`, `timestamp`, `metadata`,
  `synthesis`, and with `metadata_mismatch` when
  `metadata.messageCount != len(messages)`,
  `metadata.referenceCount != len(argumentGraph)`, or
  `metadata.participants != distinct senders`.
- `tests/test_e2e_fresh_loop.py:138-151` shows the orchestrator burden today:

  ```python
  final_state = dict(partial)
  final_state.update(
      {
          "topic": "Fresh loop",
          "mode": "lightweight",
          "timestamp": "2026-06-10T00:00:00Z",
          "synthesis": {"recommendation": "..."},
          "metadata": {
              "messageCount": 2,
              "referenceCount": 0,
              "participants": ["architect", "contrarian"],
          },
      }
  )
  ```

  and earlier (line ~37) it hand-writes the manifest:

  ```python
  (discussion / "manifest.json").write_text(
      json.dumps({"schemaVersion": 1, "id": "fresh-loop", "mode": "lightweight", "status": "active"})
  )
  ```

- `runtime/swarm/__init__.py` — `planned_commands()` already lists `"init"`
  (planned, unimplemented). `runtime/swarm_rt.py` has no `init` subparser.
- `runtime-contract.json` — `commands` map lists stable commands;
  `runtime/swarm/contract.py` validates each entry (owner=runtime,
  stability=contract, booleans `adapterFacing`/`mutatesState`,
  `responsibilities` and `produces` as string lists) and requires each command
  name to appear in `planned_commands()`.
- Conventions: errors are `{"code","path","message","value?"}` dicts built by
  a module-local `_issue()`; WAL writes are atomic tmp+rename with dir fsync
  (`wal.py:checkpoint`); timestamps elsewhere use
  `time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())` (`wal.py:append_event`).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Tests | `.venv/bin/python -m pytest -q` | all pass, exit 0 |
| WAL tests | `.venv/bin/python -m pytest tests/test_phase3_wal.py -q` | all pass |
| Contract | `python3 runtime/swarm_rt.py runtime-contract` | exit 0 |

## Scope

**In scope**:
- `runtime/swarm/wal.py` (finalize_round derivation; new `init_discussion`)
- `runtime/swarm_rt.py` (new `init` subcommand; `finalize-round` unchanged CLI surface)
- `runtime-contract.json` (add `init` command spec)
- `tests/test_phase3_wal.py`, `tests/test_e2e_fresh_loop.py`, `tests/test_runtime_contract.py`
- `docs/ADAPTER-SPEC.md`, `docs/HOST-ADAPTERS.md` (flow updates)
- `PROGRESS.md` (round entry)

**Out of scope**:
- `runtime/swarm/validation.py` — the validator stays strict; derivation
  happens BEFORE validation in `finalize_round`, so the validator still
  catches inconsistent caller-supplied metadata.
- `persona-plan` — explicitly deferred (requires LLM judgment; see
  `plans/README.md` rejected list).
- `scripts/vendor.py` BUNDLE — no new files are vendored (code changes only).

## Git workflow

- Work on `main`; one commit, message style: `feat: derive finalize metadata and add init command`.
- Do NOT push.

## Steps

### Step 1: Derivation in `finalize_round`

In `runtime/swarm/wal.py`, at the top of `finalize_round` (after the
`_round_guard` call, before `validate_round_record`), insert derivation on a
copy of the input:

```python
final_state = dict(final_state) if isinstance(final_state, dict) else final_state
if isinstance(final_state, dict):
    messages = final_state.get("messages") or []
    graph = final_state.get("argumentGraph") or []
    if isinstance(messages, list) and "metadata" not in final_state:
        final_state["metadata"] = {
            "messageCount": len(messages),
            "referenceCount": len(graph) if isinstance(graph, list) else 0,
            "participants": sorted(
                {m.get("from") for m in messages if isinstance(m, dict) and isinstance(m.get("from"), str)}
            ),
        }
    final_state.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
```

Rules: derive ONLY when the key is absent. If the caller supplies `metadata`
or `timestamp`, pass it through untouched so the existing
`metadata_mismatch` validation still fires on inconsistent input (no silent
repair of wrong data — repo principle). `topic`, `mode`, `synthesis` remain
required from the caller (they are judgment, not derivation).

**Verify**: `.venv/bin/python -m pytest tests/test_phase3_wal.py -q` → all pass (existing tests supply full state and must be unaffected).

### Step 2: Pin the derivation with tests

In `tests/test_phase3_wal.py` add:

1. `test_finalize_derives_metadata_and_timestamp_when_absent` — build a state
   via `append_message` (see `test_finalize_round_flushes_final_state_before_commit`
   as the pattern), add only `topic`/`mode`/`synthesis`, call
   `finalize_round`, assert ok and that the committed `001.json` contains
   correct `metadata.messageCount`, `referenceCount`, sorted `participants`,
   and a non-empty `timestamp`.
2. `test_finalize_still_rejects_wrong_caller_metadata` — same setup but pass
   `metadata` with `messageCount` off by one; assert `ok is False` with a
   `metadata_mismatch` error (proves no silent repair).

**Verify**: `.venv/bin/python -m pytest tests/test_phase3_wal.py -q` → all pass including 2 new.

### Step 3: Implement `init_discussion` in `wal.py`

New function:

```python
def init_discussion(discussion_dir: Path, discussion_id: str, mode: str = "standard", title: str | None = None) -> dict[str, Any]:
```

Behavior:
- Validate `discussion_id`: non-empty string matching
  `^[A-Za-z0-9][A-Za-z0-9_-]*$` (reuse the anchored style of
  `transport.py:PHASE_NAME`, with `\Z`); error code `invalid_discussion_id`.
- If `discussion_dir / "manifest.json"` already exists → `{"ok": False}` with
  error code `already_initialized` (fail loud; no overwrite).
- Create `discussion_dir`, subdirs `context/`, `rounds/`, `artifacts/`.
- Write `manifest.json` atomically (tmp + `os.replace`, fsync dir — copy the
  pattern from `checkpoint` in the same file):
  `{"schemaVersion": 1, "id": discussion_id, "mode": mode, "status": "active", "createdAt": <UTC ISO>}`
  plus `"title": title` when provided.
- Append an `events.jsonl` event `discussion_initialized` via the existing
  `append_event`.
- Return `{"ok": True, "errors": [], "manifestPath": ..., "discussionId": ..., "nextHelperCommand": "swarm-rt context-build --brief <brief.json> --out context/summary.md"}`.

**Verify**: `.venv/bin/python -c "import sys; sys.path.insert(0,'runtime'); from swarm.wal import init_discussion; from pathlib import Path; import tempfile, json; d=Path(tempfile.mkdtemp())/'x'; r=init_discussion(d,'demo-1'); assert r['ok'] and json.loads((d/'manifest.json').read_text())['status']=='active'; r2=init_discussion(d,'demo-1'); assert not r2['ok'] and r2['errors'][0]['code']=='already_initialized'; print('init OK')"` → `init OK`

### Step 4: Wire the `init` CLI subcommand

In `runtime/swarm_rt.py`: add `cmd_init` and a subparser
`init --dir <path> --discussion-id <id> [--mode standard] [--title ...]`,
following the existing subparser style (e.g. the `transport-init` block).
`planned_commands()` already lists `init` — no change there.

**Verify**: `T=$(mktemp -d) && python3 runtime/swarm_rt.py init --dir "$T/d" --discussion-id demo-1 && test -f "$T/d/manifest.json" && echo CLI-OK` → `CLI-OK`

### Step 5: Add `init` to the runtime contract

In `runtime-contract.json` add under `commands`:

```json
"init": {
  "owner": "runtime",
  "stability": "contract",
  "adapterFacing": true,
  "mutatesState": true,
  "responsibilities": ["discussion-scaffold"],
  "produces": ["manifest.json", "events.jsonl"]
}
```

Because `adapterFacing` is true, also add `"init"` to the
`adapterFacingCommands` array (the validator cross-checks flag vs list).

**Verify**: `python3 runtime/swarm_rt.py runtime-contract` → exit 0. Then
`.venv/bin/python -m pytest tests/test_runtime_contract.py -q` → all pass.

### Step 6: Simplify the fresh-loop e2e test to use the new surface

In `tests/test_e2e_fresh_loop.py`: replace the hand-written
`manifest.json` block with `run_cli("init", "--dir", str(discussion), "--discussion-id", "fresh-loop", "--mode", "lightweight")`
(then the later "status → completed" update reads/rewrites the manifest as
today), and drop `timestamp` + `metadata` from the `final_state.update(...)`
block so the test now exercises derivation end-to-end.

**Verify**: `.venv/bin/python -m pytest tests/test_e2e_fresh_loop.py -q` → 1 passed.

### Step 7: Docs + PROGRESS

- `docs/HOST-ADAPTERS.md`: prepend `swarm-rt init` to the documented flow.
- `docs/ADAPTER-SPEC.md`: note that finalize-round derives
  `metadata`/`timestamp` when absent and that supplied values are still
  validated strictly.
- Append a `PROGRESS.md` round entry (template at top of file).

**Verify**: `.venv/bin/python -m pytest -q` → all pass.

## Test plan

Steps 2/3/6 add: two derivation tests, an `already_initialized` failure test
(add it as a proper pytest test in `tests/test_phase3_wal.py`, mirroring the
Step 3 inline check), and the e2e test now covering init + derivation. Model
new tests after `tests/test_phase3_wal.py` existing style.

## Done criteria

- [ ] `.venv/bin/python -m pytest -q` exits 0 (with ≥3 new tests)
- [ ] `python3 runtime/swarm_rt.py runtime-contract` exits 0 with `init` in the contract
- [ ] `grep -n '"metadata"' tests/test_e2e_fresh_loop.py` → no hand-assembled metadata block remains
- [ ] Step 3 inline check passes (`init OK`)
- [ ] `git status` clean outside in-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- `finalize_round` or `validate_round_record` no longer match the excerpts
  (drift).
- Deriving metadata makes any existing WAL test fail in a way that suggests
  the validator semantics must change (validator is out of scope).
- The contract validator rejects the `init` entry for a reason other than a
  typo (suggests contract rules changed).
- Plan 001 landed first and changed `cmd_finalize_round`'s emit path in a way
  that conflicts — reconcile by keeping 001's compact envelope and report
  what you did.

## Maintenance notes

- `init` is the natural future home for capability-profile scaffolding
  (`capabilities/profile.json`) — deferred; today the default profile resolves
  implicitly.
- If a future round adds `topic`/`mode` lookup from `manifest.json` so
  finalize-round needs only `synthesis`, the derivation block in Step 1 is
  where it goes.
- Reviewer should scrutinize: derivation must never overwrite caller-supplied
  fields (no-silent-repair principle).
