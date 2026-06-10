from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from swarm.context import build_context_summary
from swarm.prompt import build_prompt


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"
FIXTURES = ROOT / "fixtures" / "phase2"
REQUESTS = FIXTURES / "prompt-requests"


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


def test_context_build_writes_summary_artifact_and_metadata(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.md"

    result = run_cli(
        "context-build",
        "--brief",
        str(FIXTURES / "brief.json"),
        "--out",
        str(summary_path),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["summaryPath"] == str(summary_path)
    assert len(payload["summarySha256"]) == 64
    summary = summary_path.read_text()
    assert "## Objective" in summary
    assert "formatter determinism" in summary


def test_context_build_rejects_missing_objective() -> None:
    brief = load_json(FIXTURES / "brief.json")
    del brief["objective"]

    result = build_context_summary(brief)

    assert result["ok"] is False
    assert any(error["code"] == "missing_field" for error in result["errors"])


def test_declaration_prompt_is_deterministic_and_blind_to_peer_messages() -> None:
    request = load_json(REQUESTS / "declaration.json")

    first = build_prompt(request)
    second = build_prompt(request)

    assert first == second
    assert first["ok"] is True
    assert first["phase"] == "declaration"
    assert first["visibility"] == {}
    assert first["injectedIds"] == []
    assert "r1-msg-001" not in first["prompt"]
    assert "Peer content that must not be visible" not in first["prompt"]


def test_argumentation_prompt_injects_only_declarations_and_moderator_opening() -> None:
    result = build_prompt(load_json(REQUESTS / "argumentation.json"))

    assert result["ok"] is True
    assert result["visibility"] == {
        "r1-msg-001": "full",
        "r1-msg-002": "full",
        "r1-msg-003": "full",
    }
    assert "r1-msg-004" not in result["prompt"]


def test_response_prompt_records_full_and_gist_visibility() -> None:
    result = build_prompt(load_json(REQUESTS / "response.json"))

    assert result["ok"] is True
    assert result["visibility"]["r1-msg-001"] == "full"
    assert result["visibility"]["r1-msg-002"] == "gist"
    assert result["visibility"]["r1-msg-003"] == "full"
    assert result["visibility"]["r1-msg-004"] == "full"
    assert "shiftTriggerIds" in result["prompt"]
    assert "(elided)" in result["prompt"]


def test_prompt_build_rejects_unknown_phase() -> None:
    request = load_json(REQUESTS / "declaration.json")
    request["phase"] = "brainstorm"

    result = build_prompt(request)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_phase" for error in result["errors"])


def test_prompt_build_rejects_response_without_valid_messages() -> None:
    request = load_json(REQUESTS / "response.json")
    request["messages"][0].pop("id")

    result = build_prompt(request)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_message_id" for error in result["errors"])


def test_prompt_build_cli_writes_prompt_artifacts(tmp_path: Path) -> None:
    result = run_cli(
        "prompt-build",
        "--request",
        str(REQUESTS / "fixed-role-contrarian.json"),
        "--out-dir",
        str(tmp_path),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert (tmp_path / "prompt-build.json").exists()
    assert (tmp_path / "prompt.txt").exists()
    artifact = json.loads((tmp_path / "prompt-build.json").read_text())
    assert artifact["phase"] == "contrarian"
    assert artifact["visibility"] == {"r1-msg-001": "full", "r1-msg-002": "full"}


def test_prompt_build_schema_documents_auditable_visibility_contract() -> None:
    schema = load_json(ROOT / "schemas" / "prompt-build.schema.json")

    assert "visibility" in schema["required"]
    assert "injectedIds" in schema["required"]
    assert schema["properties"]["visibility"]["additionalProperties"]["enum"] == [
        "full",
        "gist",
    ]


def test_prompt_build_reports_unreadable_context_summary_instead_of_crashing(tmp_path: Path) -> None:
    request = load_json(REQUESTS / "response.json")
    del request["contextSummary"]
    request["contextSummaryPath"] = str(tmp_path)

    result = build_prompt(request)

    assert result["ok"] is False
    assert any(error["code"] == "unreadable_context_summary" for error in result["errors"])


def test_prompt_build_rejects_boolean_visibility_budget() -> None:
    request = load_json(REQUESTS / "response.json")
    request["visibilityBudget"] = True

    result = build_prompt(request, base_dir=REQUESTS)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_visibility_budget" for error in result["errors"])
