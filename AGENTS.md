# Agent Operating Contract

This repository is the host-agnostic source of truth for the
`swarm-discussion` plugin family: runtime mechanics, protocol semantics,
artifact schemas, the vendorable adapter bundle, and the adapter certification
gates. Keep every change aligned with that role. It is not an incubator
anymore; adapters and users depend on what ships from here.

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
9. Protocol semantics live in `protocol/` only; runtime mechanics live in
   `runtime/` only. Adapters must never need to fork either.
10. The adapter-facing surface — stable commands, schemas,
    `runtime-contract.json`, the vendor bundle, and the certification gates —
    is a public contract. Change any part of it only with the contract,
    `docs/ADAPTER-SPEC.md`, schemas, and tests updated in the same round.
11. The vendored bundle must stay self-sufficient and host-agnostic: the
    vendored CLI plus the bundled fixture must pass the gates with no access
    to this repo.

## Push Cadence

The maintainer has opted into auto-push: after any work turn that commits to
this repo, push the new commits to `origin/main` without asking first. The same
applies to the adapter repos (`swarm-discussion-claude`,
`swarm-discussion-codex`).

## Boundaries

- Do not add host-specific adapter code here: no skill text, spawn/wait
  primitives, host wrappers, or host agent definitions. Adapters live in
  per-host repos (`swarm-discussion-<host>`), each built and tested by that
  host's native agent against `docs/ADAPTER-SPEC.md`.
- Do not add marketplace, npm, or installer packaging here; distribution
  assembly belongs to the thin `swarm-discussion` aggregation repo.
- Do not import the old plugin layout wholesale.
- Do not add compatibility shims without naming the real user-facing contract
  that requires them.
- Do not make a spawned Coordinator the core design until the host runtime can
  support that safely and it is empirically verified.
- Do not grant bash/edit/write to ordinary experts.
- When an adapter-facing file is added or moved, update the `BUNDLE` list in
  `scripts/vendor.py` and `docs/ADAPTER-SPEC.md` in the same change, and keep
  the vendored-bundle self-sufficiency test passing.

## Implementation Style

- Prefer small JSON-producing CLI primitives.
- Preserve raw evidence separately from synthesized judgments.
- Keep state transitions explicit.
- Treat validators and certification gates as part of the product, not as
  test-only helpers.
- Add fixtures before relying on live host behavior; prefer real legacy
  fixtures (`fixtures/legacy/`) over synthetic ones when pinning behavior.
- Design failure tests alongside passing tests; bad inputs, partial artifacts,
  stale state, ambiguous transport results, and invalid provenance must fail
  loudly with stable machine-readable error codes.
- Before each substantial task, read `ROADMAP.md`, `ACCEPTANCE.md`, and
  `PROGRESS.md` to recover intent and avoid re-inventing the target.
- After each implementation round, update `PROGRESS.md` before committing.
  Record roadmap alignment, verification, failure coverage, AgenTeam review,
  drift status, and the next task.
- After implementing a round, review the work against
  `/Users/syfq/dev/harness/codex-agenteam` design discipline: artifact-first
  runtime state, progress snapshots, trace/evidence, scope containment, and
  explicit design-drift review. Adopt the discipline, not the full AgenTeam role
  pipeline.

## Standing Bar

The original proof point —

```text
brief -> prompt-build -> collect-merge -> WAL -> validate -> trace/evidence
```

— passed and is pinned by an end-to-end test on a fresh directory
(`tests/test_e2e_fresh_loop.py`). The standing bar is now Phase 7 acceptance
(`ROADMAP.md`): real legacy fixtures validate clean from this repo alone, the
vendored bundle certifies on its own, and a host adapter built only from
`docs/ADAPTER-SPEC.md` plus the bundle passes
`conformance/certify_adapter.py` on a real host-driven discussion. Anything
that does not serve the runtime, the protocol semantics, or the adapter
contract is secondary.
