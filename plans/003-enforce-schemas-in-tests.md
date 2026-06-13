# Plan 003: Enforce the JSON Schemas in tests so hand-rolled validators and schemas can no longer drift silently

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bed47da..HEAD -- schemas/ pyproject.toml tests/ runtime/swarm/audit.py runtime/swarm/prompt.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW (test-only dependency; may surface real conformance bugs — that is the point)
- **Depends on**: none (should land BEFORE plan 004, which changes the evidence shape)
- **Category**: tests / tech-debt
- **Planned at**: commit `bed47da`, 2026-06-11

## Why this matters

`schemas/*.json` (6 files) are shipped to adapters in the vendor bundle as the
machine-readable contract, but nothing in the repo validates anything against
them — all runtime validation is hand-rolled Python. This drift channel has
already fired once: the committed minimal-v2 `evidence.json` was missing 8 of
the keys its own schema marked required, and nothing noticed until a manual
audit. After this plan, pytest validates fixtures AND live builder outputs
against the schemas, so any future divergence fails CI immediately.

## Current state

- `schemas/` contains: `capability-profile.schema.json`,
  `evidence.schema.json`, `host-transport.schema.json`,
  `prompt-build.schema.json`, `runtime-contract.schema.json`,
  `tool-evidence.schema.json`.
- No `jsonschema` import anywhere (`grep -rn jsonschema runtime/ tests/` → 0 hits).
  Tests read schemas only to assert documentation keys (e.g.
  `tests/test_phase5_host_adapter.py`, `test_host_transport_schema_documents_thin_parent_context`).
- `pyproject.toml` declares dev deps:

  ```toml
  [project.optional-dependencies]
  dev = ["pytest"]
  ```

  The venv is `.venv/` (gitignored); pytest is installed there.
- Builders whose outputs the schemas describe:
  - `runtime/swarm/audit.py:build_evidence(discussion_dir)` ↔ `evidence.schema.json`
  - `runtime/swarm/prompt.py:build_prompt(request)` ↔ `prompt-build.schema.json`
  - `runtime-contract.json` (static) ↔ `runtime-contract.schema.json`
  - `profiles/*.json` (static) ↔ `capability-profile.schema.json`
  - host-step fixtures (`fixtures/phase5/codex-host-step.json`,
    `fixtures/phase5/claude-host-step.json`,
    `fixtures/e2e/minimal-v2/transport/r001/response/host-step.json`) ↔
    `host-transport.schema.json`
  - `fixtures/e2e/minimal-v2/capabilities/tool-evidence.jsonl` (one JSON
    object per line) ↔ `tool-evidence.schema.json`
- Repo conventions: tests in `tests/test_*.py`, `ROOT = Path(__file__).resolve().parents[1]`
  pattern, plain pytest functions.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Install dev dep | `.venv/bin/python -m pip install jsonschema` | exit 0 |
| Tests | `.venv/bin/python -m pytest -q` | all pass |
| New file only | `.venv/bin/python -m pytest tests/test_schema_conformance.py -q` | all pass |

## Scope

**In scope**:
- `pyproject.toml` (add `jsonschema` to the `dev` extra)
- `tests/test_schema_conformance.py` (create)
- `schemas/*.json` — ONLY if a conformance failure traces to a schema that is
  wrong relative to deliberate, tested runtime behavior (see STOP conditions
  for how to decide)
- `PROGRESS.md` (round entry)

**Out of scope**:
- Any `runtime/swarm/*.py` behavior change. If a builder output violates a
  schema, do NOT change the builder in this plan — see STOP conditions.
- Adding `jsonschema` as a RUNTIME dependency — the runtime stays
  stdlib-only (AGENTS.md principle). It is a test-only dependency.
- `scripts/vendor.py` — schemas are already in the bundle.

## Git workflow

- Work on `main`; one commit: `test: enforce JSON schemas over fixtures and builders`.
- Do NOT push.

## Steps

### Step 1: Add the dev dependency

Edit `pyproject.toml`: `dev = ["pytest", "jsonschema"]`. Install:
`.venv/bin/python -m pip install jsonschema`.

**Verify**: `.venv/bin/python -c "import jsonschema; print(jsonschema.__version__)"` → prints a version.

### Step 2: Write the conformance tests

Create `tests/test_schema_conformance.py`. Use
`jsonschema.Draft202012Validator` if the schemas declare no `$schema`
dialect; otherwise `jsonschema.validators.validator_for(schema)`. Check the
schema files' headers first and match. Structure:

```python
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def load(path: Path):
    return json.loads(path.read_text())


def validate(instance, schema_name: str) -> list[str]:
    schema = load(SCHEMAS / schema_name)
    validator = jsonschema.validators.validator_for(schema)(schema)
    return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in validator.iter_errors(instance)]
```

Test cases (one test function each; on failure, assert with the error list in
the message so the report is actionable):

1. `runtime-contract.json` validates against `runtime-contract.schema.json`.
2. Every `profiles/*.json` validates against `capability-profile.schema.json`
   (parametrize with `pytest.mark.parametrize`).
3. The three host-step fixtures (paths in Current state) validate against
   `host-transport.schema.json`.
4. Every line of `fixtures/e2e/minimal-v2/capabilities/tool-evidence.jsonl`
   validates against `tool-evidence.schema.json`.
5. The committed `fixtures/e2e/minimal-v2/artifacts/evidence.json` validates
   against `evidence.schema.json`.
6. LIVE evidence: `build_evidence(ROOT / "fixtures" / "e2e" / "minimal-v2")`
   (import `from swarm.audit import build_evidence`) validates against
   `evidence.schema.json`. Repeat for
   `ROOT / "fixtures" / "legacy" / "tauri-vs-electron-kanban"`.
7. LIVE prompt-build: for each request in
   `fixtures/phase2/prompt-requests/*.json`, `build_prompt(request, base_dir=<request dir>)`
   (import `from swarm.prompt import build_prompt`) — skip any request file
   whose result has `ok: False` — validates against `prompt-build.schema.json`.

**Verify**: `.venv/bin/python -m pytest tests/test_schema_conformance.py -q` →
either all pass, or failures that you triage in Step 3.

### Step 3: Triage failures (expected: zero to a few)

For each failure decide which side is wrong:

- The runtime behavior is pinned by an existing test in `tests/` → the SCHEMA
  is stale → fix the schema (e.g. add a missing optional property, widen an
  enum) and note it in the PROGRESS entry.
- The schema documents the published contract and no test pins the deviating
  behavior → this is a REAL bug in a builder → STOP and report (builder
  changes are out of scope here; the finding becomes its own fix).

A likely benign class: schemas with `additionalProperties: false` rejecting
fields builders legitimately added later — that is a stale schema; fix the
schema.

**Verify**: `.venv/bin/python -m pytest -q` → all pass.

### Step 4: PROGRESS entry

Append a `PROGRESS.md` round entry (template at top of that file), listing
any schema corrections made in Step 3.

**Verify**: `.venv/bin/python -m pytest -q` → all pass.

## Test plan

The plan IS the test plan: ~7 conformance test functions in
`tests/test_schema_conformance.py`, parametrized where listed. Model file
layout after `tests/test_legacy_fixtures.py` (same ROOT/load conventions).

## Done criteria

- [ ] `.venv/bin/python -m pytest -q` exits 0 (incl. new conformance tests)
- [ ] `grep -n "jsonschema" pyproject.toml` → present in `dev` extra only
- [ ] `grep -rn "import jsonschema" runtime/` → 0 matches (runtime stays stdlib-only)
- [ ] Live `build_evidence` output for both minimal-v2 and the legacy fixture passes `evidence.schema.json`
- [ ] `git status` clean outside in-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- A conformance failure traces to a BUILDER producing output that the schema
  forbids AND no existing test pins that builder behavior (real bug —
  out of scope to fix here; report the exact validator error list).
- More than 5 distinct schema files need edits (suggests systematic drift
  that deserves its own review, not piecemeal patching).
- `jsonschema` cannot be installed in `.venv` (offline environment) — report;
  do not vendor the library.

## Maintenance notes

- Plan 004 (metrics) adds fields to evidence/prompt-build outputs; these
  conformance tests are exactly what forces it to update the schemas in the
  same commit. Land this plan first.
- Future builders that gain artifacts (e.g. a trace schema) should add a
  conformance case here in the same round — reviewers should ask for it.
