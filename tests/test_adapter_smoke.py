from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from swarm.smoke import adapter_smoke


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"
FIXTURE = ROOT / "fixtures" / "e2e" / "minimal-v2"


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


def test_adapter_smoke_reports_success_for_minimal_v2_fixture() -> None:
    result = adapter_smoke(FIXTURE)

    assert result["ok"] is True
    assert result["summary"]["discussionId"] == "minimal-v2"
    assert result["summary"]["hostStepCount"] == 1
    assert result["summary"]["transportReplayOk"] is True
    assert result["summary"]["loopOk"] is True
    assert result["transportReplays"][0]["replay"]["ok"] is True


def test_adapter_smoke_cli_reports_success() -> None:
    result = run_cli("adapter-smoke", "--dir", str(FIXTURE))

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["summary"]["capabilityProfile"] == "expert-readonly"
    assert payload["summary"]["transportReplayCount"] == 1


def test_adapter_smoke_cli_accepts_explicit_host_step_path() -> None:
    result = run_cli(
        "adapter-smoke",
        "--dir",
        str(FIXTURE),
        "--host-step",
        "transport/r001/response/host-step.json",
        "--full",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["hostSteps"][0]["summary"]["parentContextSurface"]["agentIds"] == [
        "agent-architect",
        "agent-contrarian",
    ]


def test_adapter_smoke_rejects_collect_result_that_does_not_match_wait_batches(tmp_path: Path) -> None:
    fixture = copy_fixture(tmp_path)
    wait_batches = fixture / "transport" / "r001" / "response" / "wait-batches.jsonl"
    wait_batch = json.loads(wait_batches.read_text())
    del wait_batch["status"]["agent-contrarian"]
    wait_batches.write_text(json.dumps(wait_batch, sort_keys=True) + "\n")

    result = adapter_smoke(fixture)

    assert result["ok"] is False
    codes = {error["code"] for error in result["errors"]}
    assert "collect_replay_mismatch" in codes
    assert "collect_replay_failed" in codes
    assert result["summary"]["transportReplayOk"] is False


def test_adapter_smoke_rejects_bloated_parent_context(tmp_path: Path) -> None:
    fixture = copy_fixture(tmp_path)
    host_step_path = fixture / "transport" / "r001" / "response" / "host-step.json"
    host_step = json.loads(host_step_path.read_text())
    host_step["parentContext"]["fullDiscussionHistory"] = ["r1-msg-001"]
    host_step_path.write_text(json.dumps(host_step, indent=2, sort_keys=True) + "\n")

    result = adapter_smoke(fixture)

    assert result["ok"] is False
    assert any(error["code"] == "forbidden_parent_context" for error in result["errors"])


def test_adapter_smoke_cli_fails_for_missing_host_step(tmp_path: Path) -> None:
    fixture = copy_fixture(tmp_path)
    (fixture / "transport" / "r001" / "response" / "host-step.json").unlink()

    result = run_cli("adapter-smoke", "--dir", str(fixture))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(error["code"] == "missing_host_step" for error in payload["errors"])


def test_adapter_smoke_flags_empty_stored_collect_result_as_replay_mismatch(tmp_path: Path) -> None:
    discussion = copy_fixture(tmp_path)
    collect_result = discussion / "transport" / "r001" / "response" / "collect-result.json"
    collect_result.write_text("{}")

    result = adapter_smoke(discussion)

    assert result["ok"] is False
    assert any(error["code"] == "collect_replay_mismatch" for error in result["errors"])


def test_adapter_smoke_accepts_single_object_json_wait_result(tmp_path: Path) -> None:
    discussion = copy_fixture(tmp_path)
    transport_dir = discussion / "transport" / "r001" / "response"
    batches = [
        json.loads(line)
        for line in (transport_dir / "wait-batches.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(batches) == 1
    (transport_dir / "wait-result.json").write_text(json.dumps(batches[0]))
    host_step = json.loads((transport_dir / "host-step.json").read_text())
    host_step["artifacts"]["waitBatchesPath"] = "transport/r001/response/wait-result.json"
    (transport_dir / "host-step.json").write_text(json.dumps(host_step))

    result = adapter_smoke(discussion)

    assert not any(error["code"] == "invalid_wait_result" for error in result["errors"]), result["errors"]
    assert result["summary"]["transportReplayOk"] is True


def test_adapter_smoke_rejects_traversal_artifact_path_without_reading_it(tmp_path: Path) -> None:
    discussion = copy_fixture(tmp_path)
    transport_dir = discussion / "transport" / "r001" / "response"
    host_step = json.loads((transport_dir / "host-step.json").read_text())
    host_step["artifacts"]["spawnOrderPath"] = "../outside-spawn-order.json"
    (transport_dir / "host-step.json").write_text(json.dumps(host_step))
    (tmp_path / "outside-spawn-order.json").write_text("[]")

    result = adapter_smoke(discussion)

    assert result["ok"] is False
    codes = {error["code"] for error in result["errors"]}
    assert "invalid_artifact_path" in codes
