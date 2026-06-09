# Agent Operating Contract

This repository is a runtime incubator. Keep every change aligned with that
purpose.

## Non-Negotiable Principles

1. Parent agent is not the runtime.
2. WAL is the source of truth for discussion state.
3. Prompt-build must produce auditable artifacts.
4. Trace and evidence must be derivable from local artifacts.
5. Ordinary experts remain no-tools by default.
6. No free-form peer-to-peer inbox.
7. Legacy code is reference material or fixture material, not the target model.
8. Every runtime primitive must be testable without a live Codex or Claude
   session when possible.

## Boundaries

- Do not import the old plugin layout wholesale.
- Do not start with marketplace, npm, or installer packaging.
- Do not add compatibility shims without naming the real user-facing contract
  that requires them.
- Do not make a spawned Coordinator the core design until the host runtime can
  support that safely and it is empirically verified.
- Do not grant bash/edit/write to ordinary experts.

## Implementation Style

- Prefer small JSON-producing CLI primitives.
- Preserve raw evidence separately from synthesized judgments.
- Keep state transitions explicit.
- Treat validators as part of the product, not as test-only helpers.
- Add fixtures before relying on live host behavior.
- Design failure tests alongside passing tests; bad inputs, partial artifacts,
  stale state, ambiguous transport results, and invalid provenance must fail
  loudly with stable machine-readable error codes.

## First Proof Point

The first useful implementation proves:

```text
brief -> prompt-build -> collect-merge -> WAL -> validate -> trace/evidence
```

Anything outside that path is secondary until this proof point passes.
