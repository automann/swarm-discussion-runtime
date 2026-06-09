from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from swarm.audit import build_evidence, build_trace
from swarm.prompt import build_prompt


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"
PHASE1_DISCUSSION = ROOT / "fixtures" / "phase1" / "discussions" / "complete"
PHASE2_RESPONSE = ROOT / "fixtures" / "phase2" / "prompt-requests" / "response.json"
PHASE6_FIXTURES = ROOT / "fixtures" / "phase6"
READONLY_PROFILE = ROOT / "profiles" / "expert-readonly.json"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def copy_complete_discussion(tmp_path: Path) -> Path:
    target = tmp_path / "tabs-vs-spaces"
    shutil.copytree(PHASE1_DISCUSSION, target)
    return target


def enrich_discussion_for_audit(discussion: Path) -> None:
    prompt_dir = discussion / "prompts" / "r001" / "response" / "architect"
    prompt_dir.mkdir(parents=True)
    prompt_artifact = build_prompt(json.loads(PHASE2_RESPONSE.read_text()))
    prompt_dir.joinpath("prompt-build.json").write_text(
        json.dumps(prompt_artifact, indent=2, sort_keys=True) + "\n"
    )
    prompt_dir.joinpath("prompt.txt").write_text(prompt_artifact["prompt"])

    transport_dir = discussion / "transport" / "r001" / "response"
    transport_dir.mkdir(parents=True)
    spawn_order = [
        {"agentId": "agent-b", "persona": "architect"},
        {"agentId": "agent-a", "persona": "contrarian"},
    ]
    wait_batch = {
        "status": {
            "agent-b": {"completed": "{\"name\":\"architect\",\"claim\":\"done\"}"},
            "agent-a": {"completed": "{\"name\":\"contrarian\",\"claim\":\"done\"}"},
        },
        "timed_out": False,
    }
    collect_result = {
        "ok": True,
        "complete": True,
        "timedOut": False,
        "requiredAgentIds": ["agent-b", "agent-a"],
        "receivedAgentIds": ["agent-a", "agent-b"],
        "missingAgentIds": [],
        "missingPersonas": [],
        "results": [
            {"persona": "architect", "agentId": "agent-b", "result": {"claim": "done"}},
            {"persona": "contrarian", "agentId": "agent-a", "result": {"claim": "done"}},
        ],
        "errors": [],
    }
    transport_dir.joinpath("spawn-order.json").write_text(json.dumps(spawn_order, indent=2))
    transport_dir.joinpath("wait-batches.jsonl").write_text(json.dumps(wait_batch) + "\n")
    transport_dir.joinpath("collect-result.json").write_text(json.dumps(collect_result, indent=2))

    events = [
        {
            "seq": 1,
            "ts": "2026-06-09T00:00:00Z",
            "type": "checkpoint_written",
            "data": {"round": 1, "phase": "response", "messageCount": 3},
        },
        {
            "seq": 2,
            "ts": "2026-06-09T00:00:01Z",
            "type": "round_finalized",
            "data": {"round": 1, "messageCount": 3},
        },
    ]
    discussion.joinpath("events.jsonl").write_text("\n".join(json.dumps(event) for event in events) + "\n")


def attach_capabilities(discussion: Path, tool_evidence_fixture: str = "tool-evidence-valid.jsonl") -> None:
    capability_dir = discussion / "capabilities"
    capability_dir.mkdir()
    shutil.copyfile(READONLY_PROFILE, capability_dir / "profile.json")
    shutil.copyfile(PHASE6_FIXTURES / tool_evidence_fixture, capability_dir / "tool-evidence.jsonl")
    shutil.copytree(PHASE6_FIXTURES / "artifacts", capability_dir / "artifacts")


def test_trace_reports_completed_fixture_health_and_artifact_summaries(tmp_path: Path) -> None:
    discussion = copy_complete_discussion(tmp_path)
    enrich_discussion_for_audit(discussion)

    trace = build_trace(discussion)

    assert trace["ok"] is True
    assert trace["health"] == "on-track"
    assert trace["nextAction"]["kind"] == "none"
    assert trace["validation"]["ok"] is True
    assert trace["prompts"]["count"] == 1
    assert trace["transport"]["collectResults"][0]["complete"] is True
    assert trace["quality"]["synthesisPresent"] is True
    assert trace["events"]["counts"]["round_finalized"] == 1


def test_trace_reports_default_no_tools_capability_when_discussion_has_no_profile(tmp_path: Path) -> None:
    discussion = copy_complete_discussion(tmp_path)
    enrich_discussion_for_audit(discussion)

    trace = build_trace(discussion)

    assert trace["capabilities"]["ok"] is True
    assert trace["capabilities"]["source"] == "default"
    assert trace["capabilities"]["profile"]["id"] == "expert-basic"
    assert trace["capabilities"]["effective"]["allowedTools"] == []
    assert trace["capabilities"]["effective"]["canCiteToolDerivedEvidence"] is False


def test_trace_surfaces_citable_readonly_tool_evidence_from_discussion_artifacts(tmp_path: Path) -> None:
    discussion = copy_complete_discussion(tmp_path)
    enrich_discussion_for_audit(discussion)
    attach_capabilities(discussion)

    trace = build_trace(discussion)

    assert trace["health"] == "on-track"
    assert trace["capabilities"]["source"] == "discussion"
    assert trace["capabilities"]["profile"]["id"] == "expert-readonly"
    assert trace["capabilities"]["toolEvidence"]["citable"] is True
    assert trace["capabilities"]["toolEvidence"]["acceptedCount"] == 1
    assert trace["capabilities"]["effective"]["canCiteToolDerivedEvidence"] is True


def test_trace_marks_unvalidated_tool_evidence_at_risk(tmp_path: Path) -> None:
    discussion = copy_complete_discussion(tmp_path)
    enrich_discussion_for_audit(discussion)
    attach_capabilities(discussion, tool_evidence_fixture="tool-evidence-unvalidated.jsonl")

    trace = build_trace(discussion)

    assert trace["health"] == "at-risk"
    assert trace["nextAction"]["kind"] == "inspect_capabilities"
    assert trace["capabilities"]["toolEvidence"]["citable"] is False
    assert any(error["code"] == "unvalidated_tool_evidence" for error in trace["capabilities"]["errors"])


def test_trace_cli_suggests_resume_for_partial_round(tmp_path: Path) -> None:
    discussion = tmp_path / "partial-discussion"
    rounds = discussion / "rounds"
    rounds.mkdir(parents=True)
    (discussion / "manifest.json").write_text(
        json.dumps(
            {
                "id": "partial-discussion",
                "title": "Partial discussion",
                "mode": "lightweight",
                "schemaVersion": 2,
                "status": "running",
                "currentRound": 1,
            }
        )
    )
    (discussion / "context").mkdir()
    (discussion / "context" / "summary.md").write_text("# Context\n\nStill running.\n")
    (rounds / "001.json.partial").write_text(
        json.dumps(
            {
                "roundId": 1,
                "round": 1,
                "phase": "response",
                "messages": [
                    {
                        "id": "r1-msg-001",
                        "from": "architect",
                        "type": "argument",
                        "content": {"summary": "Still in progress."},
                        "references": [],
                    }
                ],
            }
        )
    )

    result = run_cli("trace", "--dir", str(discussion))

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["health"] == "at-risk"
    assert payload["nextAction"]["kind"] == "resume_round"
    assert payload["resume"]["source"] == "partial"


def test_trace_cli_suggests_poll_remaining_for_incomplete_transport(tmp_path: Path) -> None:
    discussion = copy_complete_discussion(tmp_path)
    enrich_discussion_for_audit(discussion)
    collect_path = discussion / "transport" / "r001" / "response" / "collect-result.json"
    collect_result = json.loads(collect_path.read_text())
    collect_result["ok"] = False
    collect_result["complete"] = False
    collect_result["missingAgentIds"] = ["agent-c"]
    collect_path.write_text(json.dumps(collect_result, indent=2))

    trace = build_trace(discussion)

    assert trace["health"] == "at-risk"
    assert trace["nextAction"]["kind"] == "poll_remaining"
    assert trace["nextAction"]["missingAgentIds"] == ["agent-c"]


def test_trace_cli_reports_validation_failure_next_action(tmp_path: Path) -> None:
    discussion = copy_complete_discussion(tmp_path)
    enrich_discussion_for_audit(discussion)
    (discussion / "context" / "summary.md").unlink()

    result = run_cli("trace", "--dir", str(discussion))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["health"] == "off-track"
    assert payload["nextAction"]["kind"] == "inspect_validation"
    assert any(error["code"] == "missing_summary" for error in payload["validation"]["errors"])


def test_trace_missing_discussion_returns_machine_readable_error(tmp_path: Path) -> None:
    result = run_cli("trace", "--dir", str(tmp_path / "missing"))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["errors"][0]["code"] == "missing_directory"


def test_evidence_records_transport_validation_prompt_and_quality_summaries(tmp_path: Path) -> None:
    discussion = copy_complete_discussion(tmp_path)
    enrich_discussion_for_audit(discussion)

    evidence = build_evidence(discussion)

    assert evidence["schemaVersion"] == 1
    assert evidence["kind"] == "swarm.discussion_evidence"
    assert evidence["discussion"]["id"] == "tabs-vs-spaces"
    assert evidence["outcome"]["result"] == "completed"
    assert evidence["validation"]["ok"] is True
    assert evidence["transport"]["collectResultCount"] == 1
    assert evidence["prompts"]["promptBuildCount"] == 1
    assert evidence["quality"]["synthesisPresent"] is True
    assert evidence["capabilities"]["profile"]["id"] == "expert-basic"
    assert evidence["rawHostLogs"]["required"] is False
    assert any(path.endswith("prompt-build.json") for path in evidence["artifacts"]["paths"])


def test_evidence_records_capability_summary_without_embedding_tool_artifact_payload(tmp_path: Path) -> None:
    discussion = copy_complete_discussion(tmp_path)
    enrich_discussion_for_audit(discussion)
    attach_capabilities(discussion)

    evidence = build_evidence(discussion)

    assert evidence["capabilities"]["profile"]["id"] == "expert-readonly"
    assert evidence["capabilities"]["toolEvidence"]["citable"] is True
    assert evidence["metrics"]["toolEvidenceRecordCount"] == 1
    assert any(path.endswith("capabilities/artifacts/read-001.json") for path in evidence["artifacts"]["paths"])
    assert "excerptSha256" not in json.dumps(evidence["capabilities"])


def test_evidence_cli_writes_same_json_as_stdout(tmp_path: Path) -> None:
    discussion = copy_complete_discussion(tmp_path)
    enrich_discussion_for_audit(discussion)
    output = tmp_path / "reports" / "evidence.json"

    result = run_cli("evidence", "--dir", str(discussion), "--output", str(output))

    assert result.returncode == 0, result.stdout + result.stderr
    stdout_payload = json.loads(result.stdout)
    file_payload = json.loads(output.read_text())
    assert stdout_payload == file_payload
    assert file_payload["trace"]["health"] == "on-track"


def test_evidence_schema_requires_core_audit_summaries() -> None:
    schema = json.loads((ROOT / "schemas" / "evidence.schema.json").read_text())

    assert "transport" in schema["required"]
    assert "validation" in schema["required"]
    assert "prompts" in schema["required"]
    assert "quality" in schema["required"]
    assert "capabilities" in schema["required"]
