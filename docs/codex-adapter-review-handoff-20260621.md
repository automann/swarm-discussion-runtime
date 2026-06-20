# Codex Adapter Review Handoff — Targeted Fixes (2026-06-21)

**From:** Claude (two-axis `/review`: Standards + Spec)
**To:** Codex, building `swarm-discussion-codex`
**Subject repos:** adapter `swarm-discussion-codex` @ `06395bd`; aggregator entry it
added in `swarm-discussion` @ `28dd77b` (diff base: tag `v0.2.1`).

## Context (read first)

The adapter is well-built and contract-faithful in code. Verified, no action
needed:

- `conformance/certify_adapter.py` passes **5/5** (run against the vendored
  fixture — see Fix 1), `scripts/vendor.py verify` is clean, vendored runtime
  `fb7f869` includes the latest runtime fixes.
- `bin/swarm_runtime_wrapper.py` is stdlib-only, uses `runtime-contract --full`,
  includes `init` in `PRIMITIVE_COMMANDS`, verifies per-file sha256, and has a
  top-level error guard.
- `agents/swarm-coordinator.toml` and `agents/swarm-expert.toml` honor every
  entry-contract must-not (runtime owns prompt-build/fan-in/transport/WAL/
  validation; experts are no-tools leaves; no id-minting; raw `wait_agent`
  batches persisted before merge). No correctness defects found.

The findings below are about **shipped certification evidence** and **release
provenance**, not the adapter's mechanics.

**Boundaries.** Fix ONLY in `swarm-discussion-codex` (and tag its release). Do
NOT edit `swarm-discussion-runtime` or `swarm-discussion-claude`. Fix 4's
aggregator pin bump is a shared step — coordinate with the maintainer; don't
edit the aggregator unilaterally if that's out of your lane. Re-certify from the
runtime repo (commands at the end) and report the verdict against a REAL
discussion, not the fixture.

---

## Fix 1 (HIGH) — Ship a retained, certified real Codex discussion

**Finding.** The tracked public tree (`git ls-files`) ships NO
`smoke/discussions/<id>` tree, so certification currently only passes against the
vendored fixture `vendor/swarm-runtime/fixtures/e2e/minimal-v2`. A retained smoke
existed earlier (`a0415b7 "certify retained codex smoke"`, `caa76b1`) but was
dropped in `9d4a54e "Pivot to root plugin public tree"`. (`smoke/` is **not**
gitignored — it was just removed from tracking.)

**Why it matters (spec).**
- ADAPTER-SPEC §Adapter deliverables #6: *"at least one real discussion driven
  end-to-end on the host through the adapter, kept (or referenced) in the
  adapter repo."*
- ADAPTER-SPEC §Certification: *"The bundled fixture proves the runtime;
  certification proves the adapter."*
- Entry contract (ADAPTER-SPEC §Entry contract / handoff §7): must NOT *"treat
  fixture-only gate results as a substitute for validating the real discussion
  artifact tree."*
- Definition of done (handoff §9): *"ONE real Codex-driven discussion certifies
  (all five gates) with the adapter's vendored bundle."*

Consequence today: nobody (CI or a reviewer) can re-certify the *shipped* release
against a real discussion — only the fixture. The sibling Claude adapter ships
`smoke/discussions/cert-config-layout` for exactly this purpose.

**Fix.** Re-drive one real Codex discussion through the host primitives (your
coordinator-thread flow), retain its full artifact tree under
`smoke/discussions/<id>`, and TRACK it (`git add`). Keep it minimal but real — it
must pass `validate-discussion`, not just `adapter-smoke` / `validate-loop`.

**Acceptance.** `certify_adapter.py --discussion <repo>/smoke/discussions/<id> …`
exits 0 (5/5), and `<id>` appears in `git ls-files`.

---

## Fix 2 (MED) — State the pinned runtimeSha + compatibility in release notes

**Finding.** Neither `README.md` nor any tracked CHANGELOG states the pinned
`runtimeSha` (`fb7f869…`) or the compatibility string (`swarm-runtime-v2-alpha`).
The fact lives only inside `vendor-manifest.json`.

**Why it matters (standard).** ADAPTER-SPEC §Versioning: *"The adapter's release
notes must state the pinned `runtimeSha` from `vendor-manifest.json` and the
runtime `compatibility` string (`runtime-contract.json: runtime.compatibility`)."*
Handoff §9 repeats this in the definition of done.

**Fix.** Add a short "Release / runtime pin" note to the README (and/or a
CHANGELOG): `runtimeSha: fb7f869…`, `compatibility: swarm-runtime-v2-alpha`, plus
the certified discussion id + date.

**Acceptance.** `grep` for the sha and `swarm-runtime-v2-alpha` in tracked
release notes succeeds.

---

## Fix 3 (MED) — Resolve adapter version coherence

**Finding.** `.codex-plugin/plugin.json` is `"version": "0.1.0"`, while the family
is on 0.2.x (Claude adapter `v0.2.1`, aggregator marketplace `0.2.2`).

**Why it matters (standard, judgment).** No documented lockstep rule, but a
"0.1.0" plugin shipped by a "0.2.2" marketplace is confusing for consumers and
diverges from the sibling adapter.

**Fix.** Decide the Codex adapter's version line and apply it: either align to the
family (bump `.codex-plugin/plugin.json` into the 0.2.x line) or keep an
independent line and DOCUMENT the rationale in the README. Either way, make the
`plugin.json` version and the release tag (Fix 4) agree.

**Acceptance.** `.codex-plugin/plugin.json` version matches the chosen release
tag; rationale documented if you keep an independent line.

---

## Fix 4 (MED) — Tag the release; reconcile the aggregator pin form

**Finding.** The Codex adapter has no git tag; the aggregator pins it by bare
`sha` via `source: url` + `…/swarm-discussion-codex.git`. The sibling Claude
entry pins `source: github` + `ref: v0.2.1` (a tag).

**Why it matters (standard, judgment).** ADAPTER-SPEC §Versioning allows `ref`
OR `sha`, so the sha pin is legal — but an untagged commit pin is harder to audit
and inconsistent with the sibling. Also confirm `source: url` + `.git` + `sha` is
the intended Codex marketplace source kind (vs `github`).

**Fix (Codex side).** Create an annotated release tag at the certified commit
(matching Fix 3's version).
**Fix (shared / aggregator).** Once tagged, update
`swarm-discussion/.agents/plugins/marketplace.json` to pin that tag (and revisit
`url` vs `github` source kind). Coordinate with the maintainer.

**Acceptance.** A release tag exists on `swarm-discussion-codex`; the aggregator
Codex entry references it.

---

## Minor / optional (not among the four; fix only if cheap)

- **doctor nesting probe.** Handoff §2/§3 asked `doctor` to empirically probe and
  record host nesting; it returns `nestedSubagentTopology.supported = null`
  ("doctor is non-mutating"). This is largely MOOT because your dedicated-
  coordinator-thread topology doesn't rely on nesting — but either add a real
  (non-mutating, non-self-replicating) probe, or keep `null` and state the
  "thread topology → nesting irrelevant" rationale in the README so it reads as a
  decision, not an omission.
- **Builder vocabulary leak.** `doctor`'s `host_diagnostics()` emits `sprintRow`
  keys and `swarm-coordinator.toml` says "This row's contract" — internal
  build-process ("row") terms surfacing in host-facing output. Rename to product
  vocabulary. Cosmetic.

---

## Re-certification / acceptance commands (run from the runtime repo)

```bash
RT=/Users/syfq/dev/harness/swarm-discussion-runtime
CX=/Users/syfq/dev/harness/swarm-discussion-codex

python3 "$RT/scripts/vendor.py" verify --dest "$CX/vendor/swarm-runtime"
python3 "$CX/bin/swarm_runtime_wrapper.py" doctor --smoke-fixture
python3 "$RT/conformance/certify_adapter.py" \
  --discussion "$CX/smoke/discussions/<id>" \
  --vendored  "$CX/vendor/swarm-runtime" \
  --runtime   "$CX/vendor/swarm-runtime/runtime/swarm_rt.py"
```

Report back the certified **real-discussion** path + the `certify_adapter.py`
verdict, so the `swarm-discussion-codex` milestone can be checked in the runtime
`ACCEPTANCE.md` and the aggregator pin updated.
