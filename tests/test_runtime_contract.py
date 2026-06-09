from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

from swarm.contract import REQUIRED_INTEGRATION_GATES, REQUIRED_PLUGIN_COMMANDS, validate_runtime_contract


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"
CONTRACT = ROOT / "runtime-contract.json"


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text())


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_runtime_contract_manifest_is_valid() -> None:
    result = validate_runtime_contract(load_contract())

    assert result["ok"] is True
    assert result["summary"]["compatibility"] == "swarm-runtime-v2-alpha"
    assert set(result["summary"]["integrationGates"]) >= REQUIRED_INTEGRATION_GATES


def test_runtime_contract_cli_emits_manifest_and_validation() -> None:
    result = run_cli("runtime-contract")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["contract"]["kind"] == "swarm.runtime_contract"
    assert payload["validation"]["summary"]["commandCount"] >= len(REQUIRED_PLUGIN_COMMANDS)


def test_runtime_contract_declares_required_plugin_commands_as_runtime_owned() -> None:
    contract = load_contract()

    assert REQUIRED_PLUGIN_COMMANDS <= set(contract["commands"])
    for command in REQUIRED_PLUGIN_COMMANDS:
        spec = contract["commands"][command]
        assert spec["owner"] == "runtime"
        assert spec["stability"] == "contract"


def test_runtime_contract_marks_adapter_gates() -> None:
    contract = load_contract()

    assert REQUIRED_INTEGRATION_GATES <= set(contract["adapterFacingCommands"])
    assert REQUIRED_INTEGRATION_GATES <= set(contract["integrationGates"])
    for gate in REQUIRED_INTEGRATION_GATES:
        assert contract["commands"][gate]["adapterFacing"] is True


def test_runtime_contract_keeps_host_and_skill_responsibilities_out_of_runtime_boundary() -> None:
    contract = load_contract()

    runtime_boundary = contract["boundaries"]["runtime"]
    assert "spawn-host-agents" not in runtime_boundary["responsibilities"]
    assert "wait-host-agents" not in runtime_boundary["responsibilities"]
    assert "parent-conversation-orchestration" in runtime_boundary["forbidden"]
    assert "construct-prompts" in contract["boundaries"]["skillPrompt"]["forbidden"]
    assert "mutate-wal-state" in contract["boundaries"]["hostAdapter"]["forbidden"]


def test_runtime_contract_rejects_missing_adapter_gate() -> None:
    contract = copy.deepcopy(load_contract())
    contract["commands"].pop("adapter-smoke")
    contract["adapterFacingCommands"].remove("adapter-smoke")
    contract["integrationGates"].remove("adapter-smoke")

    result = validate_runtime_contract(contract)

    assert result["ok"] is False
    assert any(error["code"] == "missing_required_command" for error in result["errors"])
    assert any(error["code"] == "missing_integration_gate" for error in result["errors"])


def test_runtime_contract_rejects_host_responsibility_inside_runtime() -> None:
    contract = copy.deepcopy(load_contract())
    contract["boundaries"]["runtime"]["responsibilities"].append("spawn-host-agents")

    result = validate_runtime_contract(contract)

    assert result["ok"] is False
    assert any(error["code"] == "forbidden_runtime_responsibility" for error in result["errors"])


def test_runtime_contract_rejects_host_owned_stable_command() -> None:
    contract = copy.deepcopy(load_contract())
    contract["commands"]["prompt-build"]["owner"] = "hostAdapter"

    result = validate_runtime_contract(contract)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_command_owner" for error in result["errors"])


def test_runtime_contract_schema_documents_boundary_sections() -> None:
    schema = json.loads((ROOT / "schemas" / "runtime-contract.schema.json").read_text())

    assert "commands" in schema["required"]
    assert "boundaries" in schema["required"]
    assert "integrationGates" in schema["required"]
    assert "stableArtifacts" in schema["required"]
