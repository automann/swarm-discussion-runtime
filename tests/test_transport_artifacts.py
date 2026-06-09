from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from swarm.adapter import parent_context_surface
from swarm.transport import append_wait_batch, collect_transport_step, write_transport_step


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def spawn_order() -> list[dict[str, str]]:
    return [
        {"agentId": "agent-architect", "persona": "architect"},
        {"agentId": "agent-contrarian", "persona": "contrarian"},
    ]


def wait_batch() -> dict:
    return {
        "status": {
            "agent-architect": {
                "completed": json.dumps({"name": "architect", "claim": "keep runtime in charge"})
            },
            "agent-contrarian": {
                "completed": json.dumps({"name": "contrarian", "claim": "fail loudly on partial artifacts"})
            },
        },
        "timed_out": False,
    }


def test_transport_init_writes_thin_host_step_and_empty_wait_stream(tmp_path: Path) -> None:
    discussion_dir = tmp_path / "discussion"

    result = write_transport_step(discussion_dir, "codex", "disc-1", 1, "response", spawn_order())

    assert result["ok"] is True
    host_step = json.loads((discussion_dir / "transport" / "r001" / "response" / "host-step.json").read_text())
    assert parent_context_surface(host_step) == {
        "agentIds": ["agent-architect", "agent-contrarian"],
        "briefPath": "context/summary.md",
        "nextHelperCommand": "swarm-rt transport-collect --dir . --round 1 --phase response",
        "phase": "response",
    }
    assert (discussion_dir / "transport" / "r001" / "response" / "spawn-order.json").exists()
    assert (discussion_dir / "transport" / "r001" / "response" / "wait-batches.jsonl").read_text() == ""


def test_transport_cli_roundtrip_writes_collect_result(tmp_path: Path) -> None:
    discussion_dir = tmp_path / "discussion"
    spawn_path = tmp_path / "spawn-order.json"
    wait_path = tmp_path / "wait-result.json"
    spawn_path.write_text(json.dumps(spawn_order()) + "\n")
    wait_path.write_text(json.dumps(wait_batch()) + "\n")

    init = run_cli(
        "transport-init",
        "--dir",
        str(discussion_dir),
        "--host",
        "codex",
        "--discussion-id",
        "disc-1",
        "--round",
        "1",
        "--phase",
        "response",
        "--spawn-order",
        str(spawn_path),
    )
    append = run_cli(
        "transport-append-batch",
        "--dir",
        str(discussion_dir),
        "--round",
        "1",
        "--phase",
        "response",
        "--wait-result",
        str(wait_path),
    )
    collect = run_cli(
        "transport-collect",
        "--dir",
        str(discussion_dir),
        "--round",
        "1",
        "--phase",
        "response",
    )

    assert init.returncode == 0, init.stdout + init.stderr
    assert append.returncode == 0, append.stdout + append.stderr
    assert collect.returncode == 0, collect.stdout + collect.stderr
    payload = json.loads(collect.stdout)
    assert payload["ok"] is True
    assert [item["persona"] for item in payload["result"]["results"]] == ["architect", "contrarian"]
    stored = json.loads((discussion_dir / "transport" / "r001" / "response" / "collect-result.json").read_text())
    assert stored == payload["result"]


def test_transport_init_rejects_empty_spawn_order_without_writing_artifacts(tmp_path: Path) -> None:
    discussion_dir = tmp_path / "discussion"

    result = write_transport_step(discussion_dir, "codex", "disc-1", 1, "response", [])

    assert result["ok"] is False
    assert any(error["code"] == "invalid_spawn_order" for error in result["errors"])
    assert not (discussion_dir / "transport").exists()


def test_transport_init_rejects_path_traversal_phase_without_writing_artifacts(tmp_path: Path) -> None:
    discussion_dir = tmp_path / "discussion"

    result = write_transport_step(discussion_dir, "codex", "disc-1", 1, "../escape", spawn_order())

    assert result["ok"] is False
    assert any(error["code"] == "invalid_phase" for error in result["errors"])
    assert not (tmp_path / "escape").exists()
    assert not (discussion_dir / "transport").exists()


def test_transport_append_requires_transport_init(tmp_path: Path) -> None:
    discussion_dir = tmp_path / "discussion"

    result = append_wait_batch(discussion_dir, 1, "response", wait_batch())

    assert result["ok"] is False
    codes = {error["code"] for error in result["errors"]}
    assert {"missing_host_step", "missing_spawn_order"} <= codes
    assert not (discussion_dir / "transport" / "r001" / "response" / "wait-batches.jsonl").exists()


def test_transport_append_rejects_non_object_wait_result_after_init(tmp_path: Path) -> None:
    discussion_dir = tmp_path / "discussion"
    write_transport_step(discussion_dir, "codex", "disc-1", 1, "response", spawn_order())

    result = append_wait_batch(discussion_dir, 1, "response", ["not", "an", "object"])

    assert result["ok"] is False
    assert any(error["code"] == "invalid_wait_result" for error in result["errors"])
    assert (discussion_dir / "transport" / "r001" / "response" / "wait-batches.jsonl").read_text() == ""


def test_transport_collect_reports_missing_artifacts(tmp_path: Path) -> None:
    result = collect_transport_step(tmp_path / "discussion", 1, "response")

    assert result["ok"] is False
    codes = {error["code"] for error in result["errors"]}
    assert {"missing_spawn_order", "missing_wait_batches", "missing_host_step"} <= codes


def test_transport_collect_writes_incomplete_result_for_partial_batches(tmp_path: Path) -> None:
    discussion_dir = tmp_path / "discussion"
    write_transport_step(discussion_dir, "codex", "disc-1", 1, "response", spawn_order())
    append_wait_batch(
        discussion_dir,
        1,
        "response",
        {
            "status": {
                "agent-architect": {
                    "completed": json.dumps({"name": "architect", "claim": "partial"})
                }
            },
            "timed_out": False,
        },
    )

    result = collect_transport_step(discussion_dir, 1, "response")

    assert result["ok"] is False
    assert result["result"]["complete"] is False
    assert result["result"]["missingAgentIds"] == ["agent-contrarian"]
    assert (discussion_dir / "transport" / "r001" / "response" / "collect-result.json").exists()
