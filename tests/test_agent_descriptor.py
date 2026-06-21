"""Plan 007: host-agnostic agentDescriptor provenance for projected custom agents.

Covers: preservation + validation through transport normalization, the
customAgentProjection host-step summary (present iff descriptors exist; absent
otherwise so existing fixtures stay byte-identical), descriptor linkage in
collect-merge, and conformance to the new/updated schemas.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from swarm.collect import collect_merge
from swarm.transport import _validate_spawn_order, write_transport_step

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
FIXTURE = ROOT / "fixtures" / "e2e" / "minimal-v2"

_FULL_DESCRIPTOR = {
    "projectedName": "swarm-run1-architect",
    "projectedPath": ".claude/agents/swarm-run1-architect.md",
    "projectedSha256": "a" * 64,
    "agentType": "swarm-run1-architect",
    "invocationForm": "explicit_spawn",
    "promptRef": "prompts/r001/response/a1/prompt.txt",
}


def _errors(instance: object, schema_name: str) -> list[str]:
    schema = json.loads((SCHEMAS / schema_name).read_text())
    validator = jsonschema.validators.validator_for(schema)(schema)
    return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in validator.iter_errors(instance)]


def _read(discussion_dir: Path, name: str) -> object:
    return json.loads((discussion_dir / "transport" / "r001" / "response" / name).read_text())


# --- preservation + projection summary ---------------------------------------


def test_descriptor_preserved_and_projection_summarized(tmp_path: Path) -> None:
    spawn_order = [
        {"agentId": "a1", "persona": "architect", "agentDescriptor": dict(_FULL_DESCRIPTOR)},
        {"agentId": "a2", "persona": "contrarian"},  # no descriptor
    ]
    result = write_transport_step(
        tmp_path, "claude", "d1", 1, "response", spawn_order, agent_source_dir=".claude/agents"
    )
    assert result["ok"], result

    spawn = _read(tmp_path, "spawn-order.json")
    assert spawn[0]["agentDescriptor"] == _FULL_DESCRIPTOR
    assert "agentDescriptor" not in spawn[1]

    host_step = _read(tmp_path, "host-step.json")
    assert host_step["transport"]["customAgentProjection"] == {
        "projected": True,
        "agentSourceDir": ".claude/agents",
        "count": 1,
    }


def test_no_descriptor_omits_projection_block(tmp_path: Path) -> None:
    spawn_order = [
        {"agentId": "a1", "persona": "architect"},
        {"agentId": "a2", "persona": "contrarian"},
    ]
    result = write_transport_step(tmp_path, "codex", "d1", 1, "response", spawn_order)
    assert result["ok"], result
    host_step = _read(tmp_path, "host-step.json")
    assert "customAgentProjection" not in host_step["transport"]


def test_committed_minimal_v2_host_step_has_no_projection() -> None:
    # Backward-compat guard: the existing non-projected fixture is unchanged.
    host_step = json.loads(
        (FIXTURE / "transport" / "r001" / "response" / "host-step.json").read_text()
    )
    assert "customAgentProjection" not in host_step["transport"]


def test_agent_source_dir_defaults_to_projected_path_parent(tmp_path: Path) -> None:
    spawn_order = [{"agentId": "a1", "persona": "architect", "agentDescriptor": dict(_FULL_DESCRIPTOR)}]
    result = write_transport_step(tmp_path, "claude", "d1", 1, "response", spawn_order)
    assert result["ok"], result
    host_step = _read(tmp_path, "host-step.json")
    assert host_step["transport"]["customAgentProjection"]["agentSourceDir"] == ".claude/agents"


# --- validation --------------------------------------------------------------


def test_valid_descriptor_survives_normalization() -> None:
    normalized, errors = _validate_spawn_order(
        [{"agentId": "a1", "persona": "p", "agentDescriptor": {"projectedName": "swarm-run1-p", "invocationForm": "explicit_spawn"}}]
    )
    assert errors == []
    assert normalized[0]["agentDescriptor"] == {"projectedName": "swarm-run1-p", "invocationForm": "explicit_spawn"}


def test_bad_descriptors_rejected() -> None:
    bad_descriptors = [
        {},  # missing projectedName
        {"projectedName": ""},  # empty projectedName
        {"projectedName": "x", "projectedSha256": "nothex"},
        {"projectedName": "x", "invocationForm": "telepathy"},
        {"projectedName": "x", "promptRef": ""},
        "not-an-object",
    ]
    for bad in bad_descriptors:
        normalized, errors = _validate_spawn_order([{"agentId": "a1", "persona": "p", "agentDescriptor": bad}])
        assert any(e["code"] == "invalid_agent_descriptor" for e in errors), bad
        assert normalized == [], bad  # the offending entry is dropped, not silently accepted


# --- collect linkage ---------------------------------------------------------


def test_collect_merge_carries_descriptor() -> None:
    spawn_order = [{"agentId": "a1", "persona": "architect", "agentDescriptor": {"projectedName": "swarm-run1-architect"}}]
    wait = [{"status": {"a1": {"completed": {"persona": "architect", "ok": True}}}}]
    merged = collect_merge(spawn_order, wait)
    assert merged["results"][0]["agentDescriptor"] == {"projectedName": "swarm-run1-architect"}


def test_collect_merge_omits_descriptor_when_absent() -> None:
    spawn_order = [{"agentId": "a1", "persona": "architect"}]
    wait = [{"status": {"a1": {"completed": {"persona": "architect"}}}}]
    merged = collect_merge(spawn_order, wait)
    assert "agentDescriptor" not in merged["results"][0]


# --- schema conformance ------------------------------------------------------


def test_projected_artifacts_conform_to_schemas(tmp_path: Path) -> None:
    spawn_order = [{"agentId": "a1", "persona": "architect", "agentDescriptor": dict(_FULL_DESCRIPTOR)}]
    result = write_transport_step(
        tmp_path, "claude", "d1", 1, "response", spawn_order, agent_source_dir=".claude/agents"
    )
    assert result["ok"], result

    host_step = _read(tmp_path, "host-step.json")
    spawn = _read(tmp_path, "spawn-order.json")
    assert _errors(host_step, "host-transport.schema.json") == []
    assert _errors(spawn, "spawn-order.schema.json") == []

    merged = collect_merge(spawn, [{"status": {"a1": {"completed": {"persona": "architect"}}}}])
    assert _errors(merged, "collect-result.schema.json") == []


def test_malformed_descriptor_fails_spawn_order_schema() -> None:
    spawn = [{"agentId": "a1", "persona": "p", "agentDescriptor": {"projectedSha256": "nothex"}}]
    assert _errors(spawn, "spawn-order.schema.json") != []  # missing projectedName + bad sha


def test_projection_manifest_schema_accepts_and_rejects() -> None:
    good = {
        "runId": "run1",
        "createdPaths": [{"path": ".claude/agents/swarm-run1-architect.md", "sha256": "a" * 64}],
        "deletionStatus": "clean",
        "removedPaths": [".claude/agents/swarm-run1-architect.md"],
        "remainingPaths": [],
    }
    assert _errors(good, "projection-manifest.schema.json") == []

    bad = {"runId": "run1", "createdPaths": [{"path": "x"}], "deletionStatus": "nope"}
    assert _errors(bad, "projection-manifest.schema.json") != []
