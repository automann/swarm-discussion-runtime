from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from swarm.wal import append_message, checkpoint, finalize_round, resume_plan


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


def valid_round_state(messages: list[dict], synthesis: dict | None = None) -> dict:
    argument_graph = [
        {"from": message["id"], "to": ref["targetId"], "relation": ref["relation"]}
        for message in messages
        for ref in message.get("references", [])
    ]
    return {
        "roundId": 1,
        "topic": "Tabs vs spaces",
        "mode": "lightweight",
        "timestamp": "2026-06-09T00:00:00Z",
        "messages": messages,
        "argumentGraph": argument_graph,
        "positionShifts": [],
        "synthesis": synthesis or {},
        "metadata": {
            "messageCount": len(messages),
            "participants": sorted({message["from"] for message in messages}),
            "referenceCount": len(argument_graph),
        },
    }


def message(sender: str, summary: str, refs: list[dict] | None = None) -> dict:
    return {
        "from": sender,
        "type": "argument",
        "content": {"summary": summary},
        "references": refs or [],
    }


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_append_message_mints_gapless_ids_from_wal_state_not_progress_log(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    discussion.mkdir()
    (discussion / "progress.md").write_text("r1-msg-999 emitted\n")

    first = append_message(discussion, 1, "declarations", message("architect", "Use formatter."))
    second = append_message(
        discussion,
        1,
        "arguments",
        message(
            "contrarian",
            "Respect migration cost.",
            [{"targetId": "r1-msg-001", "relation": "questions"}],
        ),
    )

    assert first["ok"] is True
    assert first["message"]["id"] == "r1-msg-001"
    assert second["ok"] is True
    assert second["message"]["id"] == "r1-msg-002"
    partial = read_json(discussion / "rounds" / "001.json.partial")
    assert [item["id"] for item in partial["messages"]] == ["r1-msg-001", "r1-msg-002"]
    assert partial["phase"] == "arguments"


def test_append_message_rejects_invalid_reference_relation(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    append_message(discussion, 1, "declarations", message("architect", "Use formatter."))

    result = append_message(
        discussion,
        1,
        "arguments",
        message("contrarian", "I agree.", [{"targetId": "r1-msg-001", "relation": "agrees"}]),
    )

    assert result["ok"] is False
    assert any(error["code"] == "invalid_relation" for error in result["errors"])


def test_append_message_rejects_finalized_round_without_partial(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    messages = [
        {
            **message("architect", "Use formatter."),
            "id": "r1-msg-001",
        }
    ]
    finalize_round(
        discussion,
        1,
        valid_round_state(messages, {"recommendation": "Use formatter."}),
    )

    result = append_message(discussion, 1, "arguments", message("contrarian", "Too late."))

    assert result["ok"] is False
    assert any(error["code"] == "round_finalized" for error in result["errors"])


def test_finalize_round_persists_runtime_quality_block(tmp_path: Path) -> None:
    # plan 009 step 3: finalize-round must PERSIST the runtime-owned quality block on the
    # round (committed, tamper-evident state) with the structural fields + the
    # manifest-derived stressRequired, not leave it to a trace/evidence rebuild.
    from swarm.wal import init_discussion

    discussion = tmp_path / "disc"
    init_discussion(discussion, "demo-1", mode="deep")  # deep -> stressPolicy required
    messages = [{**message("architect", "Use event sourcing."), "id": "r1-msg-001"}]
    result = finalize_round(discussion, 1, valid_round_state(messages, {"recommendation": "x"}))

    assert result["ok"] is True, result
    quality = read_json(discussion / "rounds" / "001.json")["quality"]
    assert quality["stressPolicy"] == "required"  # read from the manifest (mode=deep)
    assert quality["stressRequired"] is True
    assert quality["stressTriggered"] is False
    assert quality["counterEdgeCount"] == 0
    assert quality["positionShiftCount"] == 0


def test_finalize_round_flushes_final_state_before_commit(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    append_message(discussion, 1, "declarations", message("architect", "Use formatter."))
    final_messages = [
        {
            **message("architect", "Use formatter."),
            "id": "r1-msg-001",
        },
        {
            **message(
                "maintainer",
                "Document migration.",
                [{"targetId": "r1-msg-001", "relation": "extends"}],
            ),
            "id": "r1-msg-002",
        },
    ]

    result = finalize_round(
        discussion,
        1,
        valid_round_state(final_messages, {"recommendation": "Use formatter with migration notes."}),
    )

    assert result["ok"] is True
    final = read_json(discussion / "rounds" / "001.json")
    assert final["synthesis"]["recommendation"] == "Use formatter with migration notes."
    assert [item["id"] for item in final["messages"]] == ["r1-msg-001", "r1-msg-002"]
    assert not (discussion / "rounds" / "001.json.partial").exists()


def test_finalize_round_rejects_missing_synthesis(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    messages = [
        {
            **message("architect", "Use formatter."),
            "id": "r1-msg-001",
        }
    ]

    result = finalize_round(discussion, 1, valid_round_state(messages))

    assert result["ok"] is False
    assert any(error["code"] == "missing_synthesis" for error in result["errors"])


def test_resume_plan_uses_highest_round_and_only_prefers_partial_on_that_round(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    rounds = discussion / "rounds"
    rounds.mkdir(parents=True)
    (rounds / "001.json.partial").write_text(
        json.dumps({"roundId": 1, "round": 1, "phase": "arguments", "messages": []})
    )
    (rounds / "002.json").write_text(
        json.dumps(
            {
                "roundId": 2,
                "round": 2,
                "phase": "complete",
                "messages": [
                    {
                        "id": "r2-msg-001",
                        "from": "architect",
                        "type": "argument",
                        "content": {"summary": "Round 2"},
                        "references": [],
                    }
                ],
            }
        )
    )

    result = resume_plan(discussion)

    assert result["ok"] is True
    assert result["source"] == "final"
    assert result["round"] == 2
    assert result["maxId"] == "r2-msg-001"
    assert result["nextMessageId"] == "r2-msg-002"

    (rounds / "003.json.partial").write_text(
        json.dumps({"roundId": 3, "round": 3, "phase": "responses", "messages": []})
    )
    result = resume_plan(discussion)

    assert result["source"] == "partial"
    assert result["round"] == 3
    assert result["phase"] == "responses"
    assert result["nextMessageId"] == "r3-msg-001"


def test_checkpoint_refuses_to_resurrect_a_finalized_round(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    messages = [
        {
            **message("architect", "Use formatter."),
            "id": "r1-msg-001",
        }
    ]
    state = valid_round_state(messages, {"recommendation": "Use formatter."})
    assert finalize_round(discussion, 1, state)["ok"] is True

    result = checkpoint(discussion, 1, "arguments", state)

    assert result["ok"] is False
    assert any(error["code"] == "round_finalized" for error in result["errors"])
    assert not (discussion / "rounds" / "001.json.partial").exists()

    appended = append_message(discussion, 1, "arguments", message("contrarian", "Too late."))
    assert appended["ok"] is False
    assert any(error["code"] == "round_finalized" for error in appended["errors"])

    resume = resume_plan(discussion)
    assert resume["source"] == "final"
    assert resume["nextAction"] == "start_next_round"


def test_checkpoint_rejects_state_round_id_mismatch(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    state = valid_round_state([])

    result = checkpoint(discussion, 2, "declarations", state)

    assert result["ok"] is False
    assert any(error["code"] == "round_id_mismatch" for error in result["errors"])
    assert not (discussion / "rounds" / "002.json.partial").exists()


def test_finalize_rejects_state_round_id_mismatch(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    messages = [
        {
            **message("architect", "Use formatter."),
            "id": "r1-msg-001",
        }
    ]
    state = valid_round_state(messages, {"recommendation": "Use formatter."})

    result = finalize_round(discussion, 2, state)

    assert result["ok"] is False
    assert any(error["code"] == "round_id_mismatch" for error in result["errors"])
    assert not (discussion / "rounds" / "002.json").exists()


def test_checkpoint_rejects_non_sequential_round(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    state = valid_round_state([])
    state["roundId"] = 3

    result = checkpoint(discussion, 3, "declarations", state)

    assert result["ok"] is False
    assert any(error["code"] == "round_not_sequential" for error in result["errors"])


def test_checkpoint_accepts_next_round_after_previous_final(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    messages = [
        {
            **message("architect", "Use formatter."),
            "id": "r1-msg-001",
        }
    ]
    assert finalize_round(
        discussion, 1, valid_round_state(messages, {"recommendation": "Use formatter."})
    )["ok"] is True
    state = valid_round_state([])
    state["roundId"] = 2

    result = checkpoint(discussion, 2, "declarations", state)

    assert result["ok"] is True, result
    assert (discussion / "rounds" / "002.json.partial").exists()


def test_append_message_reports_corrupt_partial_instead_of_crashing(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    rounds = discussion / "rounds"
    rounds.mkdir(parents=True)
    (rounds / "001.json.partial").write_text("{not json")

    result = append_message(discussion, 1, "arguments", message("architect", "Hello."))

    assert result["ok"] is False
    assert any(error["code"] == "invalid_json" for error in result["errors"])


def test_resume_plan_reports_corrupt_partial_instead_of_crashing(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    rounds = discussion / "rounds"
    rounds.mkdir(parents=True)
    (rounds / "001.json.partial").write_text("{not json")

    result = resume_plan(discussion)

    assert result["ok"] is False
    assert result["nextAction"] == "inspect_artifacts"
    assert any(error["code"] == "invalid_json" for error in result["errors"])


def test_resume_plan_reports_non_object_state_instead_of_crashing(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    rounds = discussion / "rounds"
    rounds.mkdir(parents=True)
    (rounds / "001.json.partial").write_text("[]")

    result = resume_plan(discussion)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_state" for error in result["errors"])


def test_message_id_minting_continues_past_sequence_999(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    rounds = discussion / "rounds"
    rounds.mkdir(parents=True)
    (rounds / "001.json.partial").write_text(
        json.dumps(
            {
                "roundId": 1,
                "round": 1,
                "phase": "arguments",
                "messages": [
                    {
                        "id": "r1-msg-999",
                        "from": "architect",
                        "type": "argument",
                        "content": {"summary": "message 999"},
                        "references": [],
                    }
                ],
            }
        )
    )

    first = append_message(discussion, 1, "arguments", message("contrarian", "One past the cap."))
    second = append_message(discussion, 1, "arguments", message("maintainer", "Two past the cap."))

    assert first["ok"] is True
    assert first["message"]["id"] == "r1-msg-1000"
    assert second["ok"] is True
    assert second["message"]["id"] == "r1-msg-1001"


def test_checkpoint_cli_writes_partial_and_event_log(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps(valid_round_state([])))

    result = run_cli(
        "checkpoint",
        "--dir",
        str(discussion),
        "--round",
        "1",
        "--phase",
        "declarations",
        "--state",
        str(state_path),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert (discussion / "rounds" / "001.json.partial").exists()
    events = (discussion / "events.jsonl").read_text().strip().splitlines()
    assert json.loads(events[-1])["type"] == "checkpoint_written"


def test_resume_plan_cli_reports_no_state(tmp_path: Path) -> None:
    result = run_cli("resume-plan", "--dir", str(tmp_path / "missing-discussion"))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["source"] == "none"
    assert payload["nextAction"] == "start_round"


def test_finalize_derives_metadata_and_timestamp_when_absent(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    messages = [{**message("architect", "Use formatter."), "id": "r1-msg-001"}]
    state = valid_round_state(messages, {"recommendation": "Use formatter."})
    del state["metadata"]
    del state["timestamp"]

    result = finalize_round(discussion, 1, state)

    assert result["ok"] is True, result
    final = read_json(discussion / "rounds" / "001.json")
    assert final["metadata"] == {"messageCount": 1, "referenceCount": 0, "participants": ["architect"]}
    assert final["timestamp"]


def test_finalize_does_not_overwrite_supplied_metadata(tmp_path: Path) -> None:
    discussion = tmp_path / "discussion"
    messages = [{**message("architect", "Use formatter."), "id": "r1-msg-001"}]
    state = valid_round_state(messages, {"recommendation": "x"})
    state["metadata"]["messageCount"] = 99  # caller-supplied and wrong

    result = finalize_round(discussion, 1, state)

    assert result["ok"] is False
    assert any(error["code"] == "metadata_mismatch" for error in result["errors"])


def test_init_discussion_creates_manifest_and_refuses_reinit(tmp_path: Path) -> None:
    from swarm.wal import init_discussion

    discussion = tmp_path / "d"
    result = init_discussion(discussion, "demo-1", mode="lightweight")

    assert result["ok"] is True, result
    manifest = read_json(discussion / "manifest.json")
    assert manifest["status"] == "active"
    assert manifest["mode"] == "lightweight"
    assert (discussion / "rounds").is_dir()

    again = init_discussion(discussion, "demo-1")
    assert again["ok"] is False
    assert again["errors"][0]["code"] == "already_initialized"


def test_init_discussion_rejects_bad_id(tmp_path: Path) -> None:
    from swarm.wal import init_discussion

    result = init_discussion(tmp_path / "d", "../escape")

    assert result["ok"] is False
    assert result["errors"][0]["code"] == "invalid_discussion_id"


def test_init_discussion_stress_policy_derives_from_mode(tmp_path: Path) -> None:
    from swarm.wal import init_discussion

    for mode, expected in (("lightweight", "off"), ("standard", "auto"), ("deep", "required"), ("normal", "off")):
        result = init_discussion(tmp_path / mode, "demo-1", mode=mode)
        assert result["ok"] is True, result
        assert read_json(tmp_path / mode / "manifest.json")["stressPolicy"] == expected
        assert result["stressPolicy"] == expected


def test_init_discussion_stress_policy_explicit_and_invalid(tmp_path: Path) -> None:
    from swarm.wal import init_discussion

    override = init_discussion(tmp_path / "a", "demo-1", mode="standard", stress_policy="required")
    assert override["ok"] is True
    assert read_json(tmp_path / "a" / "manifest.json")["stressPolicy"] == "required"

    bad = init_discussion(tmp_path / "b", "demo-1", stress_policy="bogus")
    assert bad["ok"] is False
    assert bad["errors"][0]["code"] == "invalid_stress_policy"
    assert not (tmp_path / "b").exists()  # no partial scaffold on invalid input
