# Capability Profiles

Phase 6 keeps expert autonomy behind an auditable profile contract. The default
ordinary expert remains `expert-basic`, which grants no tools.

## Profiles

`profiles/expert-basic.json`

- Default: yes.
- Role: ordinary expert.
- Allowed tools: none.
- Tool-derived evidence: cannot be cited because no tools are granted.

`profiles/expert-readonly.json`

- Default: no.
- Role: ordinary expert.
- Allowed tools: `read`, `glob`, `grep`.
- Status: experimental.
- Tool-derived evidence: may be cited only when a JSONL tool-evidence record is
  present, validated, and points at a stored artifact.

Broad tools are `bash`, `edit`, and `write`. Ordinary experts must not receive
those tools through these profiles.

## Doctor

Use `capability-doctor` to inspect the effective profile:

```bash
swarm-rt capability-doctor
swarm-rt capability-doctor --profile profiles/expert-readonly.json
swarm-rt capability-doctor \
  --profile profiles/expert-readonly.json \
  --tool-evidence fixtures/phase6/tool-evidence-valid.jsonl
```

The doctor is a report primitive. It does not grant tools or spawn agents.

## Discussion Artifacts

Trace and evidence look for capability artifacts inside a discussion directory:

```text
capabilities/profile.json
capabilities/tool-evidence.jsonl
capabilities/artifacts/<tool-artifact>.json
```

If `capabilities/profile.json` is absent, trace and evidence report the built-in
`expert-basic` profile as the effective default. If `tool-evidence.jsonl` is
present, each citable record must point at an artifact under the capabilities
directory.

## Evidence Rule

Tool-derived evidence is citable only when all of these are true:

- The active profile allows the tool.
- The tool call is logged as a `swarm.tool_evidence` JSONL record.
- The record is marked `validated: true`.
- `validation.ok` is true.
- `artifactPath` points to a persisted artifact.

If any condition fails, the runtime report marks the evidence non-citable.
