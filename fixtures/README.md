# Fixtures

Current fixture categories:

```text
fixtures/
  phase1/                 spawn-order, partial wait results, and a complete discussion
  phase2/                 brief and prompt-build request fixtures
  phase5/                 thin host-step metadata fixtures (valid and invalid)
  phase6/                 capability profile and tool-evidence fixtures
  e2e/minimal-v2/         smallest complete v2 loop fixture
```

Still missing (planned): `legacy-rounds/` with committed rounds from the
published plugin line and `wait-results/` with raw `wait_agent` payloads from a
real host session. All current fixtures are synthetic; importing real legacy
smoke artifacts remains an open acceptance item.

Fixtures are the bridge from the old plugin to the new runtime. Prefer adding a
small, named fixture over relying on live host behavior.

`fixtures/e2e/minimal-v2/` is the current end-to-end anchor. It includes
context, prompt-build artifacts, Codex host-step metadata, transport fan-in,
capability profile and tool evidence, WAL/final round state, CLI-generated
trace and evidence anchors, and synthesis output. Validate it with:

```bash
python3 runtime/swarm_rt.py validate-loop fixtures/e2e/minimal-v2
```
