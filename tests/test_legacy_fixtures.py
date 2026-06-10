"""Pin runtime behavior against real legacy plugin discussion artifacts.

These fixtures were produced by the published swarm-discussion plugin line
(see fixtures/legacy/README.md). They satisfy the ACCEPTANCE.md completion
items "real legacy smoke fixtures are represented" and "trace/evidence works
on at least one real discussion artifact".
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from swarm.audit import build_evidence, build_trace
from swarm.validation import validate_discussion_dir, validate_round_file

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"
LEGACY = ROOT / "fixtures" / "legacy"
COMPLETE = LEGACY / "tauri-vs-electron-kanban"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_real_completed_discussion_validates_clean() -> None:
    result = validate_discussion_dir(COMPLETE)

    assert result["ok"] is True, result["errors"]
    assert result["summary"]["roundCount"] >= 1
    assert result["summary"]["validatedRounds"] == result["summary"]["roundCount"]


def test_real_completed_round_file_passes_round_validation() -> None:
    result = validate_round_file(COMPLETE / "rounds" / "001.json")

    assert result["ok"] is True, result["errors"]
    assert result["summary"]["messageCount"] > 0
    assert result["summary"]["argumentEdgeCount"] > 0


def test_real_completed_discussion_traces_on_track() -> None:
    trace = build_trace(COMPLETE)

    assert trace["ok"] is True
    assert trace["health"] == "on-track"
    assert trace["nextAction"]["kind"] == "none"
    assert trace["validation"]["ok"] is True


def test_real_completed_discussion_produces_completed_evidence() -> None:
    evidence = build_evidence(COMPLETE)

    assert evidence["ok"] is True
    assert evidence["outcome"]["result"] == "completed"
    assert evidence["metrics"]["finalRoundCount"] >= 1
    assert evidence["quality"]["synthesisPresent"] is True


def test_real_incomplete_discussions_are_diagnosed_not_accepted() -> None:
    expectations = {
        "wails-vs-electron-kanban": {"missing_summary"},
        "install-verify-tabs-spaces": {"missing_summary", "missing_artifact"},
    }
    for name, expected_codes in expectations.items():
        result = validate_discussion_dir(LEGACY / name)
        assert result["ok"] is False, name
        codes = {error["code"] for error in result["errors"]}
        assert expected_codes <= codes, (name, codes)

        trace = build_trace(LEGACY / name)
        assert trace["health"] == "off-track", name
        assert trace["nextAction"]["kind"] == "inspect_validation", name


def test_real_fixture_cli_round_trip() -> None:
    result = run_cli("validate-discussion", str(COMPLETE))
    assert result.returncode == 0, result.stdout + result.stderr

    result = run_cli("evidence", "--dir", str(COMPLETE))
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["outcome"]["result"] == "completed"
