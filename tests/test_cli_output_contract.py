"""Pin the compact CLI output contract (plan 001).

Every command prints a compact summary envelope to stdout by default; full
payloads live in artifacts and behind --full. Failures always print the full
errors array regardless of --full.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"
MINIMAL_V2 = ROOT / "fixtures" / "e2e" / "minimal-v2"
RESPONSE_REQUEST = ROOT / "fixtures" / "phase2" / "prompt-requests" / "response.json"
INCOMPLETE_LEGACY = ROOT / "fixtures" / "legacy" / "install-verify-tabs-spaces"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_prompt_build_stdout_does_not_leak_prompt_text(tmp_path: Path) -> None:
    result = run_cli("prompt-build", "--request", str(RESPONSE_REQUEST), "--out-dir", str(tmp_path / "p"))
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert "prompt" not in payload, "full prompt text leaked into stdout"
    assert "visibility" not in payload, "full visibility map leaked into stdout"
    assert payload["promptSha256"]
    assert payload["promptCharCount"] > 0
    assert isinstance(payload["visibilityCounts"], dict)
    # The full payload is still written to the artifact.
    artifact = json.loads((tmp_path / "p" / "prompt-build.json").read_text())
    assert "prompt" in artifact


def test_trace_stdout_is_compact() -> None:
    result = run_cli("trace", "--dir", str(MINIMAL_V2))
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(result.stdout) < 1500, f"trace stdout too large: {len(result.stdout)} bytes"
    payload = json.loads(result.stdout)
    assert "health" in payload and "nextAction" in payload
    assert "artifacts" not in payload and "rounds" not in payload


def test_evidence_stdout_is_compact() -> None:
    result = run_cli("evidence", "--dir", str(MINIMAL_V2))
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(result.stdout) < 2500, f"evidence stdout too large: {len(result.stdout)} bytes"
    payload = json.loads(result.stdout)
    assert "outcome" in payload and "metrics" in payload
    assert "wal" not in payload and "transport" not in payload


def test_full_flag_restores_full_payload() -> None:
    result = run_cli("trace", "--dir", str(MINIMAL_V2), "--full")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert "artifacts" in payload and "rounds" in payload


def test_failure_prints_full_errors_without_full_flag() -> None:
    result = run_cli("validate-discussion", str(INCOMPLETE_LEGACY))
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert any(error["code"] == "missing_summary" for error in payload["errors"])
