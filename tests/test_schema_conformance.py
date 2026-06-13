"""Validate fixtures and live builder outputs against schemas/ (plan 003).

Closes the drift channel where hand-rolled validators and the published JSON
Schemas could diverge silently (the committed evidence anchor once dropped 8
required keys). jsonschema is a test-only dependency; the runtime stays
stdlib-only.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from swarm.audit import build_evidence
from swarm.prompt import build_prompt

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def _load(path: Path):
    return json.loads(path.read_text())


def _errors(instance, schema_name: str) -> list[str]:
    schema = _load(SCHEMAS / schema_name)
    validator = jsonschema.validators.validator_for(schema)(schema)
    return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in validator.iter_errors(instance)]


def test_runtime_contract_conforms_to_schema() -> None:
    assert _errors(_load(ROOT / "runtime-contract.json"), "runtime-contract.schema.json") == []


@pytest.mark.parametrize("profile", sorted((ROOT / "profiles").glob("*.json")), ids=lambda p: p.name)
def test_profiles_conform_to_schema(profile: Path) -> None:
    assert _errors(_load(profile), "capability-profile.schema.json") == []


@pytest.mark.parametrize(
    "host_step",
    [
        ROOT / "fixtures" / "phase5" / "codex-host-step.json",
        ROOT / "fixtures" / "phase5" / "claude-host-step.json",
        ROOT / "fixtures" / "e2e" / "minimal-v2" / "transport" / "r001" / "response" / "host-step.json",
    ],
    ids=lambda p: p.name,
)
def test_valid_host_steps_conform_to_schema(host_step: Path) -> None:
    assert _errors(_load(host_step), "host-transport.schema.json") == []


def test_tool_evidence_lines_conform_to_schema() -> None:
    path = ROOT / "fixtures" / "e2e" / "minimal-v2" / "capabilities" / "tool-evidence.jsonl"
    lines = [line for line in path.read_text().splitlines() if line.strip()]
    assert lines
    for line in lines:
        assert _errors(json.loads(line), "tool-evidence.schema.json") == []


def test_committed_minimal_v2_evidence_conforms_to_schema() -> None:
    evidence = _load(ROOT / "fixtures" / "e2e" / "minimal-v2" / "artifacts" / "evidence.json")
    assert _errors(evidence, "evidence.schema.json") == []


@pytest.mark.parametrize(
    "discussion",
    [
        ROOT / "fixtures" / "e2e" / "minimal-v2",
        ROOT / "fixtures" / "legacy" / "tauri-vs-electron-kanban",
    ],
    ids=lambda p: p.name,
)
def test_live_evidence_conforms_to_schema(discussion: Path) -> None:
    evidence = build_evidence(discussion)
    assert evidence["ok"] is True, evidence.get("errors")
    assert _errors(evidence, "evidence.schema.json") == []


@pytest.mark.parametrize(
    "request_path",
    sorted((ROOT / "fixtures" / "phase2" / "prompt-requests").glob("*.json")),
    ids=lambda p: p.name,
)
def test_live_prompt_build_conforms_to_schema(request_path: Path) -> None:
    result = build_prompt(_load(request_path), base_dir=request_path.parent)
    if not result.get("ok"):
        pytest.skip(f"request {request_path.name} is a negative fixture")
    assert _errors(result, "prompt-build.schema.json") == []
