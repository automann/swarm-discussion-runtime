from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from swarm.adapter import parent_context_surface, validate_host_transport_metadata


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"
FIXTURES = ROOT / "fixtures" / "phase5"


def load_json(path: Path) -> object:
    return json.loads(path.read_text())


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_codex_host_step_fixture_keeps_parent_context_thin() -> None:
    payload = load_json(FIXTURES / "codex-host-step.json")

    result = validate_host_transport_metadata(payload)

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["summary"]["host"] == "codex"
    assert result["summary"]["parentContextSurface"] == {
        "agentIds": ["agent-b", "agent-a"],
        "briefPath": "context/summary.md",
        "nextHelperCommand": "swarm-rt transport-collect --dir . --round 1 --phase response",
        "phase": "response",
    }


def test_claude_host_step_fixture_uses_same_runtime_contract() -> None:
    payload = load_json(FIXTURES / "claude-host-step.json")

    result = validate_host_transport_metadata(payload)

    assert result["ok"] is True
    assert result["summary"]["host"] == "claude"
    assert result["summary"]["parentContextSurface"]["agentIds"] == ["architect", "contrarian"]


def test_validate_host_step_cli_reports_success() -> None:
    result = run_cli("validate-host-step", str(FIXTURES / "codex-host-step.json"))

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["summary"]["host"] == "codex"


def test_parent_context_surface_drops_non_contract_fields_for_audit_display() -> None:
    payload = load_json(FIXTURES / "invalid-parent-context-too-wide.json")

    assert parent_context_surface(payload) == {
        "agentIds": ["agent-b", "agent-a"],
        "briefPath": "context/summary.md",
        "nextHelperCommand": "swarm-rt transport-collect --dir . --round 1 --phase response",
        "phase": "response",
    }


def test_host_step_rejects_parent_context_bloat() -> None:
    payload = load_json(FIXTURES / "invalid-parent-context-too-wide.json")

    result = validate_host_transport_metadata(payload)

    assert result["ok"] is False
    codes = {error["code"] for error in result["errors"]}
    assert "forbidden_parent_context" in codes
    paths = {error["path"] for error in result["errors"]}
    assert "hostStep.parentContext.fullDiscussionHistory" in paths
    assert "hostStep.parentContext.promptText" in paths
    assert "hostStep.parentContext.roundState" in paths
    assert "hostStep.parentContext.manualDemuxMap" in paths


def test_host_step_rejects_missing_transport_result_key() -> None:
    payload = load_json(FIXTURES / "codex-host-step.json")
    del payload["transport"]["resultKey"]

    result = validate_host_transport_metadata(payload)

    assert result["ok"] is False
    assert any(error["path"] == "hostStep.transport.resultKey" for error in result["errors"])


def test_host_step_rejects_unknown_host_and_phase_mismatch() -> None:
    payload = load_json(FIXTURES / "codex-host-step.json")
    payload["host"] = "generic"
    payload["parentContext"]["phase"] = "argumentation"

    result = validate_host_transport_metadata(payload)

    assert result["ok"] is False
    codes = {error["code"] for error in result["errors"]}
    assert "invalid_host" in codes
    assert "phase_mismatch" in codes


def test_host_transport_schema_documents_thin_parent_context() -> None:
    schema = load_json(ROOT / "schemas" / "host-transport.schema.json")

    assert "parentContext" in schema["required"]
    parent_context = schema["properties"]["parentContext"]
    assert parent_context["additionalProperties"] is False
    assert parent_context["required"] == ["briefPath", "phase", "agentIds", "nextHelperCommand"]
    assert schema["properties"]["transport"]["properties"]["resultKey"]["enum"] == ["agent_id", "name"]
