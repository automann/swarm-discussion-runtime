from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import swarm


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


def test_health_reports_skeleton_runtime() -> None:
    result = run_cli("health")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["name"] == "swarm-discussion-runtime"
    assert payload["status"] == "skeleton"


def test_planned_command_surface_is_explicit() -> None:
    commands = swarm.planned_commands()

    assert "prompt-build" in commands
    assert "collect-merge" in commands
    assert "validate-discussion" in commands
    assert "trace" in commands
    assert "evidence" in commands


def test_cli_lists_same_planned_commands() -> None:
    result = run_cli("planned-commands")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["commands"] == swarm.planned_commands()
