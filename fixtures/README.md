# Fixtures

Future fixture categories:

```text
fixtures/
  legacy-rounds/          committed rounds from the published plugin line
  wait-results/           raw and partial wait_agent payloads
  prompt-build/           deterministic prompt-build inputs and outputs
  discussions/            complete discussion directories for trace/evidence
```

Fixtures are the bridge from the old plugin to the new runtime. Prefer adding a
small, named fixture over relying on live host behavior.
