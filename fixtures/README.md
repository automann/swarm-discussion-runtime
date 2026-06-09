# Fixtures

Future fixture categories:

```text
fixtures/
  legacy-rounds/          committed rounds from the published plugin line
  wait-results/           raw and partial wait_agent payloads
  prompt-build/           deterministic prompt-build inputs and outputs
  discussions/            complete discussion directories for trace/evidence
  e2e/minimal-v2/         smallest complete v2 loop fixture
```

Fixtures are the bridge from the old plugin to the new runtime. Prefer adding a
small, named fixture over relying on live host behavior.

`fixtures/e2e/minimal-v2/` is the current end-to-end anchor. It includes
context, prompt-build artifacts, Codex host-step metadata, transport fan-in,
capability profile and tool evidence, WAL/final round state, static trace and
evidence anchors, and synthesis output. Validate it with:

```bash
python3 runtime/swarm_rt.py validate-loop fixtures/e2e/minimal-v2
```
