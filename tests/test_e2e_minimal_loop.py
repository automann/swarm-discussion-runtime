from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from swarm.adapter import validate_host_transport_metadata
from swarm.audit import build_evidence, build_trace
from swarm.loop import validate_minimal_loop


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"
FIXTURE = ROOT / "fixtures" / "e2e" / "minimal-v2"


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


def copy_fixture(tmp_path: Path) -> Path:
    target = tmp_path / "minimal-v2"
    shutil.copytree(FIXTURE, target)
    return target


def test_minimal_v2_fixture_validates_complete_loop() -> None:
    result = validate_minimal_loop(FIXTURE)

    assert result["ok"] is True
    assert result["summary"]["discussionId"] == "minimal-v2"
    assert result["summary"]["health"] == "on-track"
    assert result["summary"]["hostStepCount"] == 1
    assert result["summary"]["promptBuildCount"] == 2
    assert result["summary"]["collectResultCount"] == 1
    assert result["summary"]["finalRoundCount"] == 1
    assert result["summary"]["capabilityProfile"] == "expert-readonly"
    assert result["summary"]["citableToolEvidence"] is True


def test_validate_loop_cli_reports_success() -> None:
    result = run_cli("validate-loop", str(FIXTURE))

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["summary"]["hostStepCount"] == 1


def test_fixture_host_step_keeps_parent_context_thin() -> None:
    host_step = load_json(FIXTURE / "transport" / "r001" / "response" / "host-step.json")

    result = validate_host_transport_metadata(host_step)

    assert result["ok"] is True
    assert result["summary"]["parentContextSurface"] == {
        "agentIds": ["agent-architect", "agent-contrarian"],
        "briefPath": "context/summary.md",
        "nextHelperCommand": "swarm-rt transport-collect --dir . --round 1 --phase response",
        "phase": "response",
    }


def test_fixture_trace_and_evidence_show_complete_artifact_backed_loop() -> None:
    trace = build_trace(FIXTURE)
    evidence = build_evidence(FIXTURE)

    assert trace["health"] == "on-track"
    assert trace["nextAction"]["kind"] == "none"
    assert trace["capabilities"]["toolEvidence"]["citable"] is True
    assert evidence["outcome"]["result"] == "completed"
    assert evidence["metrics"]["toolEvidenceRecordCount"] == 1
    assert evidence["rawHostLogs"]["required"] is False


def test_static_evidence_artifact_omits_raw_tool_payload() -> None:
    evidence_text = (FIXTURE / "artifacts" / "evidence.json").read_text()

    assert "excerptSha256" not in evidence_text
    assert "command" not in evidence_text
    assert "capabilities/artifacts/read-001.json" in evidence_text


def test_validate_loop_rejects_missing_host_step(tmp_path: Path) -> None:
    fixture = copy_fixture(tmp_path)
    (fixture / "transport" / "r001" / "response" / "host-step.json").unlink()

    result = validate_minimal_loop(fixture)

    assert result["ok"] is False
    assert any(error["code"] == "missing_host_step" for error in result["errors"])


def test_validate_loop_rejects_non_citable_tool_evidence(tmp_path: Path) -> None:
    fixture = copy_fixture(tmp_path)
    evidence_path = fixture / "capabilities" / "tool-evidence.jsonl"
    evidence = json.loads(evidence_path.read_text())
    evidence["validated"] = False
    evidence["validation"]["ok"] = False
    evidence_path.write_text(json.dumps(evidence, sort_keys=True) + "\n")

    result = validate_minimal_loop(fixture)

    assert result["ok"] is False
    assert result["summary"]["health"] == "at-risk"
    assert any(error["code"] == "unvalidated_tool_evidence" for error in result["errors"])
