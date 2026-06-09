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
