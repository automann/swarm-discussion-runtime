# Plan 005: Add the context-generator template the founding document asked for

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bed47da..HEAD -- protocol/ runtime/swarm/context.py docs/ADAPTER-SPEC.md tests/test_skeleton_contract.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW (documentation + one test)
- **Depends on**: none
- **Category**: docs (intent-alignment)
- **Planned at**: commit `bed47da`, 2026-06-11

## Why this matters

The founding document (`original-intent-of-why-to-rewrite.md`) proposed: "the
plugin internally maintains a context-generator.md (placed in the same
directory as persona-generator.md). When the parent agent calls the
swarm-discussion skill, the parent agent generates a context-summary.md based
on this template". The mechanism exists (`swarm-rt context-build` turns a
brief JSON into `context/summary.md`, injected into every expert prompt), but
the template does not: `protocol/templates/` contains only
`persona-generator.md`, so adapter authors must reverse-engineer the brief
schema from Python source. This plan ships the missing template as the
parent-facing guide for producing a good brief.

## Current state

- `protocol/templates/` contains exactly one file: `persona-generator.md`
  (imported from the legacy plugin; use its tone/structure as the exemplar).
- The brief schema is defined in code at `runtime/swarm/context.py:45-99`
  (`build_context_summary`). Authoritative field list:

  | Field | Type | Required | Notes |
  |---|---|---|---|
  | `topic` | string | yes | non-empty |
  | `objective` | string | yes | non-empty |
  | `mode` | string | no | defaults to `"standard"` |
  | `discussionId` | string | no | |
  | `parentContext` | string | no | free-text narrative of the parent's situation |
  | `constraints` | list of non-empty strings | no | |
  | `knownFacts` | list of non-empty strings | no | |
  | `successCriteria` | list of non-empty strings | no | |

  Error codes on bad input: `invalid_brief` (non-object), `missing_field`
  (topic/objective), `invalid_list` (list fields).
- The generated summary always ends with an "Alignment Rule" section
  (`context.py:92-99`) instructing experts to stay anchored to
  topic/objective/constraints/facts/criteria — this is the continuous
  re-alignment mechanism; the template should explain that whatever the
  parent puts in these fields is what experts re-read every phase.
- A working example brief exists at `fixtures/phase2/brief.json`.
- `protocol/README.md` has a "## Files" list enumerating the protocol docs.
- `docs/ADAPTER-SPEC.md` has a "## Required reading" list.
- `tests/test_skeleton_contract.py::test_protocol_package_is_present_and_maps_to_real_commands`
  asserts the protocol file inventory — the new file must be added there.
- `scripts/vendor.py` BUNDLE already vendors `protocol/` recursively — no
  script change needed, but the vendor manifest test
  (`tests/test_adapter_certification.py::test_vendor_produces_pinned_manifest_and_runnable_bundle`)
  asserts specific required files; optionally extend it.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Tests | `.venv/bin/python -m pytest -q` | all pass |
| Live render | `python3 runtime/swarm_rt.py context-build --brief fixtures/phase2/brief.json --out /tmp/ctx.md` | exit 0 |

## Scope

**In scope**:
- `protocol/templates/context-generator.md` (create)
- `protocol/README.md` (add to Files list)
- `docs/ADAPTER-SPEC.md` (reference from Required reading)
- `tests/test_skeleton_contract.py` (add the file to the inventory test)
- `tests/test_adapter_certification.py` (add `protocol/templates/context-generator.md` to the required-files assertion)
- `PROGRESS.md` (round entry)

**Out of scope**:
- `runtime/swarm/context.py` — the schema is fine; this plan documents it,
  never changes it.
- `protocol/templates/persona-generator.md` — do not edit; it is imported
  legacy material.

## Git workflow

- Work on `main`; one commit: `docs: add context-generator template for parent briefs`.
- Do NOT push.

## Steps

### Step 1: Write the template

Create `protocol/templates/context-generator.md`. Read
`protocol/templates/persona-generator.md` first and match its voice
(instructional template addressed to the parent agent). Required content:

1. Purpose: the parent agent fills a brief; `swarm-rt context-build` renders
   it into `context/summary.md`; every expert prompt injects that summary in
   every phase — so this brief IS the alignment mechanism. One sentence each.
2. The brief JSON schema — reproduce the field table from "Current state"
   exactly (it mirrors `context.py`; on conflict, code wins — say so in the
   template).
3. Field-writing guidance: `objective` = the decision the parent needs, one
   sentence; `parentContext` = background an expert needs to avoid intent
   drift (problem origin, who is affected, what was tried); `constraints` =
   hard boundaries; `knownFacts` = verified data points with sources;
   `successCriteria` = what a useful synthesis must answer.
4. A complete worked example: copy `fixtures/phase2/brief.json` verbatim as
   the example brief, followed by the command:
   `swarm-rt context-build --brief brief.json --out context/summary.md`.
5. The error codes table (`invalid_brief`, `missing_field`, `invalid_list`)
   so adapters can surface failures.
6. A note that the rendered summary ends with the Alignment Rule and that
   updating the brief and re-running context-build between rounds is how the
   parent re-aligns a drifting discussion.

**Verify**: `test -f protocol/templates/context-generator.md && grep -c "objective" protocol/templates/context-generator.md` → ≥ 2.

### Step 2: Wire references

- `protocol/README.md`: add `templates/context-generator.md` to the Files
  list with a one-line description.
- `docs/ADAPTER-SPEC.md`: in "Required reading", add the template path with
  "the parent-brief authoring guide consumed by `context-build`".

**Verify**: `grep -n "context-generator" protocol/README.md docs/ADAPTER-SPEC.md` → one hit in each.

### Step 3: Pin in tests

- `tests/test_skeleton_contract.py`: in
  `test_protocol_package_is_present_and_maps_to_real_commands`, add
  `"templates/context-generator.md"` to the tuple of required protocol files.
- `tests/test_adapter_certification.py`: in
  `test_vendor_produces_pinned_manifest_and_runnable_bundle`, add
  `"protocol/templates/context-generator.md"` to the `required` tuple.

**Verify**: `.venv/bin/python -m pytest tests/test_skeleton_contract.py tests/test_adapter_certification.py -q` → all pass.

### Step 4: Cross-check the template against the code

Confirm every field named in the template exists in
`runtime/swarm/context.py` (`grep -n '"topic"\|"objective"\|"mode"\|"discussionId"\|"parentContext"\|"constraints"\|"knownFacts"\|"successCriteria"' runtime/swarm/context.py`)
and that the template names no field the code does not read.

**Verify**: the grep above shows all 8 fields; manual diff of the template
table against them shows no extras.

### Step 5: PROGRESS entry

Append a `PROGRESS.md` round entry (template at top of that file).

**Verify**: `.venv/bin/python -m pytest -q` → all pass.

## Test plan

Step 3 covers it: the protocol-inventory test and the vendor-manifest test
both gain the new file, which also proves it ships in the adapter bundle.

## Done criteria

- [ ] `protocol/templates/context-generator.md` exists with schema table, worked example, error codes
- [ ] `.venv/bin/python -m pytest -q` exits 0
- [ ] `python3 scripts/vendor.py vendor --dest /tmp/v005 >/dev/null && grep -c context-generator /tmp/v005/vendor-manifest.json` → ≥ 1
- [ ] `git status` clean outside in-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- `context.py`'s field set no longer matches the table in this plan (drift —
  the template must document the live schema, so re-derive it first and note
  the difference).
- `protocol/templates/persona-generator.md` is missing (the exemplar and
  co-location premise are gone).

## Maintenance notes

- Any future change to the brief schema in `context.py` must update this
  template in the same round — reviewers should ask for it (consider adding a
  consistency test later that parses the template's field table).
- The founding doc's "periodic alignment" idea beyond per-phase injection
  (an advisory drift-check phase) was deliberately deferred — see
  `plans/README.md` rejected/deferred list.
