"""Plan 008: projected custom-agent fan-out certification gate.

The gate is opt-in (fires when a phase declares projection) and adds a
require-projection release mode (ADR 0001 D4). Tests the projected fixture
through every certify-surface validator, the old-path back-compat + require
failure, and each negative code.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import jsonschema

from swarm.audit import build_evidence
from swarm.loop import validate_minimal_loop
from swarm.projection import validate_projection
from swarm.smoke import adapter_smoke
from swarm.validation import validate_discussion_dir

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
PROJECTED = ROOT / "fixtures" / "e2e" / "projected-minimal-v2"
MINIMAL = ROOT / "fixtures" / "e2e" / "minimal-v2"


def _phase(d: Path) -> Path:
    return d / "transport" / "r001" / "response"


def _load(p: Path):
    return json.loads(p.read_text())


def _dump(p: Path, obj) -> None:
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _copy(tmp_path: Path) -> Path:
    dst = tmp_path / "projected"
    shutil.copytree(PROJECTED, dst)
    return dst


def _codes(result) -> set[str]:
    return {e["code"] for e in result["errors"]}


def _schema_errors(instance, schema_name: str) -> list[str]:
    schema = json.loads((SCHEMAS / schema_name).read_text())
    validator = jsonschema.validators.validator_for(schema)(schema)
    return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in validator.iter_errors(instance)]


# --- the projected fixture is fully certifiable ------------------------------


def test_projected_fixture_passes_every_certify_validator() -> None:
    assert validate_projection(PROJECTED)["ok"] is True
    assert validate_projection(PROJECTED, require_projection=True)["ok"] is True
    assert validate_minimal_loop(PROJECTED)["ok"] is True
    assert validate_minimal_loop(PROJECTED, require_projection=True)["ok"] is True
    assert adapter_smoke(PROJECTED)["ok"] is True
    assert validate_discussion_dir(PROJECTED)["ok"] is True
    assert validate_minimal_loop(PROJECTED)["summary"]["projectedPhases"] == 1


def test_projected_fixture_artifacts_conform_to_schemas() -> None:
    ph = _phase(PROJECTED)
    assert _schema_errors(_load(ph / "host-step.json"), "host-transport.schema.json") == []
    assert _schema_errors(_load(ph / "spawn-order.json"), "spawn-order.schema.json") == []
    assert _schema_errors(_load(ph / "collect-result.json"), "collect-result.schema.json") == []
    assert _schema_errors(_load(PROJECTED / "projection-manifest.json"), "projection-manifest.schema.json") == []


# --- old path: inert without the flag, rejected with it (ADR D4) -------------


def test_minimal_v2_inert_without_flag() -> None:
    assert validate_minimal_loop(MINIMAL)["ok"] is True
    assert validate_minimal_loop(MINIMAL)["summary"]["projectedPhases"] == 0


def test_minimal_v2_rejected_under_require_projection() -> None:
    result = validate_minimal_loop(MINIMAL, require_projection=True)
    assert result["ok"] is False
    assert "projection_required" in _codes(result)


# --- negative codes (each tamper on a fixture copy) --------------------------


def test_missing_descriptor_on_result(tmp_path: Path) -> None:
    d = _copy(tmp_path)
    cr = _load(_phase(d) / "collect-result.json")
    cr["results"][0].pop("agentDescriptor")
    _dump(_phase(d) / "collect-result.json", cr)
    assert "missing_agent_descriptor" in _codes(validate_projection(d))


def test_invalid_projected_sha(tmp_path: Path) -> None:
    d = _copy(tmp_path)
    cr = _load(_phase(d) / "collect-result.json")
    cr["results"][0]["agentDescriptor"]["projectedSha256"] = "nothex"
    _dump(_phase(d) / "collect-result.json", cr)
    assert "invalid_projected_sha" in _codes(validate_projection(d))


def test_unresolved_prompt_ref(tmp_path: Path) -> None:
    d = _copy(tmp_path)
    cr = _load(_phase(d) / "collect-result.json")
    cr["results"][0]["agentDescriptor"]["promptRef"] = "prompts/does-not-exist.txt"
    _dump(_phase(d) / "collect-result.json", cr)
    assert "unresolved_prompt_ref" in _codes(validate_projection(d))


def test_missing_projection_manifest(tmp_path: Path) -> None:
    d = _copy(tmp_path)
    (d / "projection-manifest.json").unlink()
    assert "missing_projection_manifest" in _codes(validate_projection(d))


def test_non_run_scoped_agent_name(tmp_path: Path) -> None:
    d = _copy(tmp_path)
    manifest = _load(d / "projection-manifest.json")
    manifest["runId"] = "a-different-run"  # descriptor names no longer embed runId
    _dump(d / "projection-manifest.json", manifest)
    assert "non_run_scoped_agent_name" in _codes(validate_projection(d))


def test_projection_manifest_mismatch(tmp_path: Path) -> None:
    d = _copy(tmp_path)
    manifest = _load(d / "projection-manifest.json")
    manifest["createdPaths"] = [{"path": ".codex/agents/unrelated.toml", "sha256": "a" * 64}]
    _dump(d / "projection-manifest.json", manifest)
    assert "projection_manifest_mismatch" in _codes(validate_projection(d))


def test_invalid_custom_agent_projection_count(tmp_path: Path) -> None:
    d = _copy(tmp_path)
    host_step = _load(_phase(d) / "host-step.json")
    host_step["transport"]["customAgentProjection"]["count"] = 0
    _dump(_phase(d) / "host-step.json", host_step)
    assert "invalid_custom_agent_projection" in _codes(validate_projection(d))


# --- Codex adversarial-review findings: bind provenance to in-tree artifacts ---


def test_prompt_ref_absolute_path_rejected(tmp_path: Path) -> None:
    # An absolute promptRef must not escape the discussion tree even when it points
    # at a real host file (the old `discussion_dir / ref` join silently honored it).
    d = _copy(tmp_path)
    cr = _load(_phase(d) / "collect-result.json")
    cr["results"][0]["agentDescriptor"]["promptRef"] = "/etc/hosts"
    _dump(_phase(d) / "collect-result.json", cr)
    assert "unresolved_prompt_ref" in _codes(validate_projection(d))


def test_prompt_ref_traversal_rejected(tmp_path: Path) -> None:
    d = _copy(tmp_path)
    cr = _load(_phase(d) / "collect-result.json")
    cr["results"][0]["agentDescriptor"]["promptRef"] = "prompts/../../etc/hosts"
    _dump(_phase(d) / "collect-result.json", cr)
    assert "unresolved_prompt_ref" in _codes(validate_projection(d))


def test_projected_path_required_when_projected(tmp_path: Path) -> None:
    d = _copy(tmp_path)
    cr = _load(_phase(d) / "collect-result.json")
    cr["results"][0]["agentDescriptor"].pop("projectedPath")
    _dump(_phase(d) / "collect-result.json", cr)
    assert "missing_agent_descriptor" in _codes(validate_projection(d))


def test_descriptor_sha_must_match_manifest(tmp_path: Path) -> None:
    # A well-formed sha that does NOT match the manifest's recorded hash for that
    # path must fail — the file->payload binding has to be real, not just hex.
    d = _copy(tmp_path)
    cr = _load(_phase(d) / "collect-result.json")
    cr["results"][0]["agentDescriptor"]["projectedSha256"] = "b" * 64
    _dump(_phase(d) / "collect-result.json", cr)
    codes = _codes(validate_projection(d))
    assert "projection_manifest_mismatch" in codes
    assert "invalid_projected_sha" not in codes  # the sha is well-formed; only the binding is wrong


# --- plan 009 B-1: manifest off the byte anchor, freshness via the cleanup gate ---


def test_manifest_finalization_does_not_shift_byte_anchor(tmp_path: Path) -> None:
    # The parent finalizes projection-manifest.json (pending -> clean, + removed/
    # remaining) AFTER the coordinator builds evidence. That legitimate growth must
    # not move artifactTotalBytes, or --require-projection trips a false stale check.
    d = _copy(tmp_path)
    full = _load(d / "projection-manifest.json")
    _dump(
        d / "projection-manifest.json",
        {"runId": full["runId"], "createdPaths": full["createdPaths"], "deletionStatus": "pending"},
    )
    before = build_evidence(d)["metrics"]["artifactTotalBytes"]
    _dump(d / "projection-manifest.json", full)  # clean + removedPaths + remainingPaths
    after = build_evidence(d)["metrics"]["artifactTotalBytes"]
    assert after == before


def test_terminal_cleanup_gate_requires_clean(tmp_path: Path) -> None:
    d = _copy(tmp_path)
    manifest = _load(d / "projection-manifest.json")
    manifest["deletionStatus"] = "pending"
    _dump(d / "projection-manifest.json", manifest)
    assert validate_projection(d)["ok"] is True  # inert without the flag
    assert "projection_cleanup_incomplete" in _codes(validate_projection(d, require_projection=True))


def test_terminal_cleanup_gate_rejects_residue(tmp_path: Path) -> None:
    d = _copy(tmp_path)
    manifest = _load(d / "projection-manifest.json")
    manifest["remainingPaths"] = [".codex/agents/swarm-projmin1-architect.toml"]
    _dump(d / "projection-manifest.json", manifest)
    assert "projection_residue_present" in _codes(validate_projection(d, require_projection=True))


def test_invalid_deletion_status_rejected(tmp_path: Path) -> None:
    d = _copy(tmp_path)
    manifest = _load(d / "projection-manifest.json")
    manifest["deletionStatus"] = "bogus"
    _dump(d / "projection-manifest.json", manifest)
    assert "invalid_deletion_status" in _codes(validate_projection(d))


# --- Codex review of the step 1-2 implementation (2026-06-23) ----------------


def test_stale_projection_in_committed_evidence_is_caught(tmp_path: Path) -> None:
    # The byte total no longer anchors the manifest, so the cleanup state must be
    # freshness-checked: committed evidence that lies about deletionStatus while the
    # live manifest is clean must trip the stale check (finding 1).
    d = _copy(tmp_path)
    ev = _load(d / "artifacts" / "evidence.json")
    ev["projection"]["deletionStatus"] = "pending"  # manifest on disk is still clean
    _dump(d / "artifacts" / "evidence.json", ev)
    assert "stale_evidence_artifact" in _codes(validate_minimal_loop(d))


def test_terminal_cleanup_requires_remaining_paths_recorded(tmp_path: Path) -> None:
    # Absence or a non-list remainingPaths is NOT zero residue under certification (finding 2).
    d = _copy(tmp_path)
    manifest = _load(d / "projection-manifest.json")
    manifest.pop("remainingPaths", None)
    _dump(d / "projection-manifest.json", manifest)
    assert "projection_residue_unrecorded" in _codes(validate_projection(d, require_projection=True))

    manifest["remainingPaths"] = {}  # wrong type, not a list
    _dump(d / "projection-manifest.json", manifest)
    assert "projection_residue_unrecorded" in _codes(validate_projection(d, require_projection=True))


def test_persisted_invalid_stress_policy_rejected(tmp_path: Path) -> None:
    # validate-discussion (not just init) must enforce the manifest stressPolicy enum (finding 3).
    d = _copy(tmp_path)
    manifest = _load(d / "manifest.json")
    manifest["stressPolicy"] = "bogus"
    _dump(d / "manifest.json", manifest)
    assert "invalid_stress_policy" in _codes(validate_discussion_dir(d))
