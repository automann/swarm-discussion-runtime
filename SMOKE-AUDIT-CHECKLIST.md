# Smoke Audit Checklist

Use this checklist when reviewing a fixture-backed or live discussion artifact.
The goal is to inspect local runtime evidence before opening raw host session
logs.

## Commands

```bash
python3 runtime/swarm_rt.py trace --dir .swarm/discussions/<id>
python3 runtime/swarm_rt.py evidence --dir .swarm/discussions/<id> --output .swarm/discussions/<id>/artifacts/evidence.json
python3 runtime/swarm_rt.py validate-discussion .swarm/discussions/<id>
```

## Trace Gate

- `health` is `on-track`, or `nextAction` clearly says how to resume, poll, or
  inspect failure.
- `validation.ok` is true for completed discussions.
- Partial WAL state is reported as resumable, not mistaken for completed state.
- `events.counts` reflects checkpoint/finalization activity when WAL helpers
  were used.
- `capabilities` reports the effective expert profile. Missing discussion-local
  profile artifacts should resolve to default `expert-basic`.
- If `nextAction.kind` is `inspect_capabilities`, tool-derived evidence must be
  treated as non-citable until the profile/evidence errors are fixed.

## Evidence Gate

- `transport` summarizes spawn order, wait batches, collect results, missing
  agents, and timeouts.
- `prompts` summarizes prompt-build artifacts, phases, personas, injected IDs,
  and full/gist visibility.
- `validation` summarizes directory and round validation.
- `quality` records synthesis/recommendation or quality score when available.
- `capabilities` records profile id, allowed tools, tool-evidence counts, and
  citable status without embedding raw tool artifact payloads.
- `rawHostLogs.required` is false; host logs are secondary evidence and should
  only be opened when local artifacts are insufficient.
