# Non-Goals

These are intentionally out of scope for the incubator until the runtime proof
point passes.

## Not A Product Fork Yet

This repo is not the published plugin line. Do not start with marketplace,
plugin bundle, or npm wrapper work.

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

Old plugin behavior is evidence and fixture material. It is not automatically
the target architecture.

## Not A Host Runtime Replacement

This repo does not own Codex or Claude spawn/wait primitives. It defines the
runtime contract around those primitives.
