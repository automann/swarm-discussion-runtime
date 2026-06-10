# Non-Goals

These are intentionally out of scope for this repository under the
source-of-truth topology: runtime core here, one adapter repo per host, a thin
aggregation repo for distribution.

## Not A Host Adapter

No host-specific code lives here: no skill text, no spawn/wait primitives, no
host wrappers, no host agent definitions. Those belong to the per-host adapter
repos (`swarm-discussion-<host>`), each built and tested by that host's native
agent against `docs/ADAPTER-SPEC.md`. This repo ships the bundle and the
gates; it never ships a runnable plugin.

## Not The Distribution Repo

No marketplace manifests, plugin bundles for install, npm wrappers, or
installer tooling. Release assembly and distribution belong to the thin
`swarm-discussion` aggregation repo, which only accepts certified adapter
releases. This repo's distribution surface ends at `scripts/vendor.py` and the
vendor manifest.

## Not AgenTeam

Do not copy AgenTeam's role taxonomy or development delivery pipeline.

Borrow:

- runtime primitives,
- state/events,
- prompt-build,
- validators,
- trace/evidence,
- capability contracts.

Do not borrow:

- researcher/PM/dev/QA/reviewer workflow,
- code-delivery assumptions,
- write-scope semantics for ordinary discussion experts.

## Not A Free-Form P2P System

Do not introduce peer inboxes as a second source of truth. Any future bus must
be phase-windowed, WAL-backed, validated, and replayable.

## Not A Toolful Expert System By Default

Do not grant bash/edit/write to ordinary experts. Readonly capability profiles
must be separately named, explicit, and validator-backed.

## Not A Compatibility Exercise

Old plugin behavior is evidence and fixture material (`fixtures/legacy/`,
`references/`). It is not automatically the target architecture, and the
runtime is never bent to reproduce a legacy quirk without a named, tested
reason.

## Not A Host Runtime Replacement

This repo does not own Codex or Claude spawn/wait primitives. It defines the
runtime contract around those primitives; adapters map them.

## Not A Per-Host Fork Farm

There is exactly one copy of the protocol semantics (`protocol/`) and one copy
of the runtime mechanics (`runtime/`). If a host appears to need its own
variant of either, that is a falsifier (see `ACCEPTANCE.md`), not a reason to
fork.
