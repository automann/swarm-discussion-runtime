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


def test_validate_round_rejects_message_id_gaps() -> None:
    record = json.loads(ROUND.read_text())
    record["messages"][2]["id"] = "r1-msg-004"
    record["argumentGraph"][1]["from"] = "r1-msg-004"
    record["argumentGraph"][2]["from"] = "r1-msg-004"

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "message_id_gap" for error in result["errors"])


def test_validate_round_rejects_unresolved_references() -> None:
    record = json.loads(ROUND.read_text())
    record["messages"][1]["references"][0]["targetId"] = "r1-msg-999"

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "unresolved_reference" for error in result["errors"])


def test_validate_round_rejects_position_shifts_that_are_not_a_list() -> None:
    record = json.loads(ROUND.read_text())
    record["positionShifts"] = {"expert": "maintainer"}

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_position_shifts" for error in result["errors"])


def test_validate_round_rejects_shift_triggers_that_do_not_resolve() -> None:
    record = json.loads(ROUND.read_text())
    record["positionShifts"] = [
        {
            "type": "position_shift",
            "expert": "maintainer",
            "from": "mixed",
            "to": "formatter-defined",
            "trigger": ["r1-msg-999"],
            "reasoning": "Changed after reading a non-existent message.",
        }
    ]
    record["personaContextLog"]["maintainer"]["r1-msg-999"] = "full"

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "unresolved_shift_trigger" for error in result["errors"])


def test_validate_round_rejects_shift_triggers_not_visible_in_full() -> None:
    record = json.loads(ROUND.read_text())
    record["positionShifts"] = [
        {
            "type": "position_shift",
            "expert": "maintainer",
            "from": "mixed",
            "to": "formatter-defined",
            "trigger": ["r1-msg-002"],
            "reasoning": "Changed after reading a gist-only message.",
        }
    ]
    record["personaContextLog"]["maintainer"]["r1-msg-002"] = "gist"

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "shift_trigger_not_visible" for error in result["errors"])


def test_validate_round_rejects_unhashable_reference_target_without_crashing() -> None:
    record = json.loads(ROUND.read_text())
    record["messages"][1]["references"][0]["targetId"] = {"oops": 1}

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "unresolved_reference" for error in result["errors"])


def test_validate_round_rejects_unhashable_edge_endpoint_without_crashing() -> None:
    record = json.loads(ROUND.read_text())
    record["argumentGraph"][0]["to"] = ["r1-msg-001"]

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "unresolved_edge" for error in result["errors"])


def test_validate_round_rejects_shift_without_any_trigger() -> None:
    record = json.loads(ROUND.read_text())
    record["positionShifts"] = [
        {
            "type": "position_shift",
            "expert": "maintainer",
            "from": "mixed",
            "to": "formatter-defined",
            "reasoning": "Changed mind with no cited trigger.",
        }
    ]

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "missing_shift_trigger" for error in result["errors"])


def test_validate_round_rejects_shift_with_unhashable_trigger_without_crashing() -> None:
    record = json.loads(ROUND.read_text())
    record["positionShifts"] = [
        {
            "type": "position_shift",
            "expert": "maintainer",
            "trigger": [["r1-msg-001"]],
            "reasoning": "Trigger is a nested list.",
        }
    ]

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "unresolved_shift_trigger" for error in result["errors"])


def test_validate_round_rejects_shift_without_expert() -> None:
    record = json.loads(ROUND.read_text())
    record["positionShifts"] = [
        {
            "type": "position_shift",
            "trigger": ["r1-msg-001"],
            "reasoning": "No expert named.",
        }
    ]

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_shift_expert" for error in result["errors"])


def test_validate_round_rejects_shift_when_persona_context_log_is_empty() -> None:
    record = json.loads(ROUND.read_text())
    record["positionShifts"] = [
        {
            "type": "position_shift",
            "expert": "maintainer",
            "trigger": ["r1-msg-001"],
            "reasoning": "Log is empty so provenance cannot be proven.",
        }
    ]
    record["personaContextLog"] = {}

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "shift_provenance_unverifiable" for error in result["errors"])


def test_validate_round_rejects_null_container_fields_instead_of_coercing() -> None:
    record = json.loads(ROUND.read_text())
    record["messages"] = None
    record["argumentGraph"] = None
    record["positionShifts"] = None

    result = validate_round_record(record)

    assert result["ok"] is False
    codes = {error["code"] for error in result["errors"]}
    assert {"invalid_messages", "invalid_argument_graph", "invalid_position_shifts"} <= codes


def test_validate_round_rejects_null_references_instead_of_coercing() -> None:
    record = json.loads(ROUND.read_text())
    record["messages"][1]["references"] = None
    record["argumentGraph"] = []
    record["metadata"]["referenceCount"] = 0

    result = validate_round_record(record)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_references" for error in result["errors"])


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


def test_validate_discussion_catches_round_file_name_round_id_mismatch(tmp_path: Path) -> None:
    discussion = copy_discussion(tmp_path)
    record = json.loads((discussion / "rounds" / "001.json").read_text())
    record["roundId"] = 2
    for index, message in enumerate(record["messages"], start=1):
        message["id"] = f"r2-msg-{index:03d}"
    for message in record["messages"]:
        for ref in message["references"]:
            ref["targetId"] = ref["targetId"].replace("r1-", "r2-")
    for edge in record["argumentGraph"]:
        edge["from"] = edge["from"].replace("r1-", "r2-")
        edge["to"] = edge["to"].replace("r1-", "r2-")
    (discussion / "rounds" / "001.json").write_text(json.dumps(record))

    result = validate_discussion_dir(discussion)

    assert result["ok"] is False
    assert any(error["code"] == "round_file_mismatch" for error in result["errors"])
