from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from swarm.collect import collect_merge


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"
FIXTURES = ROOT / "fixtures" / "phase1"


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


def test_partial_wait_batch_is_incomplete_until_all_required_agent_ids_arrive() -> None:
    result = collect_merge(
        load_json(FIXTURES / "spawn-order.json"),
        [load_json(FIXTURES / "wait-partial-1.json")],
    )

    assert result["ok"] is False
    assert result["complete"] is False
    assert result["missingAgentIds"] == ["agent-c"]
    assert result["missingPersonas"] == ["maintainer"]


def test_collect_merge_accumulates_partial_batches_in_spawn_order() -> None:
    result = collect_merge(
        load_json(FIXTURES / "spawn-order.json"),
        [
            load_json(FIXTURES / "wait-partial-1.json"),
            load_json(FIXTURES / "wait-partial-2.json"),
        ],
    )

    assert result["ok"] is True
    assert result["complete"] is True
    assert [item["persona"] for item in result["results"]] == [
        "architect",
        "contrarian",
        "maintainer",
    ]


def test_collect_merge_cli_reports_partial_batches_as_not_ok() -> None:
    result = run_cli(
        "collect-merge",
        "--spawn-order",
        str(FIXTURES / "spawn-order.json"),
        "--wait-result",
        str(FIXTURES / "wait-partial-1.json"),
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["complete"] is False
    assert payload["missingAgentIds"] == ["agent-c"]


def test_collect_merge_cli_accepts_jsonl_wait_batches(tmp_path: Path) -> None:
    wait_batches = tmp_path / "wait-batches-stream"
    wait_batches.write_text(
        "\n".join(
            [
                json.dumps(load_json(FIXTURES / "wait-partial-1.json")),
                json.dumps(load_json(FIXTURES / "wait-partial-2.json")),
            ]
        )
        + "\n"
    )

    result = run_cli(
        "collect-merge",
        "--spawn-order",
        str(FIXTURES / "spawn-order.json"),
        "--wait-result",
        str(wait_batches),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["complete"] is True
    assert payload["receivedAgentIds"] == ["agent-a", "agent-b", "agent-c"]


def test_collect_merge_rejects_non_object_status() -> None:
    result = collect_merge(
        [{"agentId": "agent-a", "persona": "architect"}],
        [{"status": [], "timed_out": False}],
    )

    assert result["ok"] is False
    assert any(error["code"] == "invalid_status" for error in result["errors"])


def test_collect_merge_keeps_completed_payload_when_later_batch_reports_same_agent_incomplete() -> None:
    result = collect_merge(
        [{"agentId": "agent-a", "persona": "architect"}],
        [
            {
                "status": {
                    "agent-a": {
                        "completed": "{\"name\":\"architect\",\"claim\":\"done\"}"
                    }
                },
                "timed_out": False,
            },
            {
                "status": {
                    "agent-a": {
                        "running": True
                    }
                },
                "timed_out": False,
            },
        ],
    )

    assert result["ok"] is True
    assert result["results"][0]["result"]["claim"] == "done"


def test_collect_merge_rejects_ambiguous_name_fallback_matches() -> None:
    result = collect_merge(
        [{"agentId": "missing-agent", "persona": "architect"}],
        [
            {
                "status": {
                    "agent-a": {
                        "completed": "{\"name\":\"architect\",\"claim\":\"first\"}"
                    },
                    "agent-b": {
                        "completed": "{\"name\":\"architect\",\"claim\":\"second\"}"
                    },
                },
                "timed_out": False,
            }
        ],
    )

    assert result["ok"] is False
    assert any(error["code"] == "ambiguous_fallback_match" for error in result["errors"])


def test_collect_merge_marks_timed_out_batches_not_ok_even_when_results_are_complete() -> None:
    result = collect_merge(
        [{"agentId": "agent-a", "persona": "architect"}],
        [
            {
                "status": {
                    "agent-a": {
                        "completed": "{\"name\":\"architect\",\"claim\":\"done\"}"
                    }
                },
                "timed_out": True,
            }
        ],
    )

    assert result["complete"] is True
    assert result["timedOut"] is True
    assert result["ok"] is False
