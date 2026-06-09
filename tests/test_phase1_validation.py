from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from swarm.validation import validate_discussion_dir, validate_round_record


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"
DISCUSSION = ROOT / "fixtures" / "phase1" / "discussions" / "complete"
ROUND = DISCUSSION / "rounds" / "001.json"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_validate_round_accepts_valid_fixture() -> None:
    record = json.loads(ROUND.read_text())

    result = validate_round_record(record)

    assert result["ok"] is True
    assert result["errors"] == []


def test_validate_round_rejects_relation_enum_violations() -> None:
    record = json.loads(ROUND.read_text())
    record["argumentGraph"][0]["relation"] = "agrees"

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_relation" for error in result["errors"])


def test_validate_round_cli_rejects_relation_enum_violations(tmp_path: Path) -> None:
    record = json.loads(ROUND.read_text())
    record["messages"][1]["references"][0]["relation"] = "agrees"
    invalid_round = tmp_path / "001.json"
    invalid_round.write_text(json.dumps(record))

    result = run_cli("validate-round", str(invalid_round))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(error["code"] == "invalid_relation" for error in payload["errors"])


def test_validate_discussion_accepts_complete_fixture_without_session_jsonl() -> None:
    result = validate_discussion_dir(DISCUSSION)

    assert result["ok"] is True
    assert result["summary"]["roundCount"] == 1
    assert result["summary"]["validatedRounds"] == 1


def test_validate_discussion_cli_accepts_complete_fixture_without_session_jsonl() -> None:
    result = run_cli("validate-discussion", str(DISCUSSION))

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["summary"]["discussionId"] == "tabs-vs-spaces"


def copy_discussion(tmp_path: Path) -> Path:
    target = tmp_path / "discussion"
    shutil.copytree(DISCUSSION, target)
    return target


def test_validate_discussion_catches_missing_summary(tmp_path: Path) -> None:
    discussion = copy_discussion(tmp_path)
    (discussion / "context" / "summary.md").unlink()

    result = validate_discussion_dir(discussion)

    assert result["ok"] is False
    assert any(error["code"] == "missing_summary" for error in result["errors"])


def test_validate_discussion_catches_stale_partial_for_completed_discussion(tmp_path: Path) -> None:
    discussion = copy_discussion(tmp_path)
    (discussion / "rounds" / "001.json.partial").write_text("{}")

    result = validate_discussion_dir(discussion)

    assert result["ok"] is False
    assert any(error["code"] == "stale_partial" for error in result["errors"])


def test_validate_discussion_catches_leftover_tmp_for_completed_discussion(tmp_path: Path) -> None:
    discussion = copy_discussion(tmp_path)
    tmp_dir = discussion / "tmp"
    tmp_dir.mkdir()
    (tmp_dir / "wait-result.json").write_text("{}")

    result = validate_discussion_dir(discussion)

    assert result["ok"] is False
    assert any(error["code"] == "leftover_tmp" for error in result["errors"])


def test_validate_discussion_catches_missing_artifact_for_completed_discussion(tmp_path: Path) -> None:
    discussion = copy_discussion(tmp_path)
    (discussion / "artifacts" / "synthesis.md").unlink()

    result = validate_discussion_dir(discussion)

    assert result["ok"] is False
    assert any(error["code"] == "missing_artifact" for error in result["errors"])
