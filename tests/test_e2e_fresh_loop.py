"""Drive the documented runtime pipeline on a fresh directory via the CLI.

This pins the Phase 5 acceptance shape: a lightweight discussion driven with
parent context limited to brief, current phase, agent ids, and the next helper
command, while runtime helpers own context, prompt, transport, WAL, and audit
artifacts.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"
BRIEF = ROOT / "fixtures" / "phase2" / "brief.json"
PROMPT_REQUEST = ROOT / "fixtures" / "phase2" / "prompt-requests" / "response.json"


def run_cli(*args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def test_full_runtime_loop_on_a_fresh_directory(tmp_path: Path) -> None:
    discussion = tmp_path / "fresh-loop"
    discussion.mkdir()
    (discussion / "manifest.json").write_text(
        json.dumps({"schemaVersion": 1, "id": "fresh-loop", "mode": "lightweight", "status": "active"})
    )

    run_cli("context-build", "--brief", str(BRIEF), "--out", str(discussion / "context" / "summary.md"))

    spawn_order_path = tmp_path / "spawn-order.json"
    spawn_order_path.write_text(
        json.dumps(
            [
                {"agentId": "agent-architect", "persona": "architect"},
                {"agentId": "agent-contrarian", "persona": "contrarian"},
            ]
        )
    )
    init_result = run_cli(
        "transport-init",
        "--dir",
        str(discussion),
        "--host",
        "codex",
        "--discussion-id",
        "fresh-loop",
        "--round",
        "1",
        "--phase",
        "response",
        "--spawn-order",
        str(spawn_order_path),
    )
    parent_context = init_result["parentContext"]
    assert sorted(parent_context) == ["agentIds", "briefPath", "nextHelperCommand", "phase"]

    run_cli(
        "prompt-build",
        "--request",
        str(PROMPT_REQUEST),
        "--out-dir",
        str(discussion / "prompts" / "r001" / "response" / "architect"),
    )

    wait_result_path = tmp_path / "wait-result.json"
    wait_result_path.write_text(
        json.dumps(
            {
                "status": {
                    "agent-architect": {
                        "completed": json.dumps({"name": "architect", "claim": "runtime owns the loop"})
                    },
                    "agent-contrarian": {
                        "completed": json.dumps({"name": "contrarian", "claim": "prove it on a fresh dir"})
                    },
                },
                "timed_out": False,
            }
        )
    )
    run_cli(
        "transport-append-batch",
        "--dir",
        str(discussion),
        "--round",
        "1",
        "--phase",
        "response",
        "--wait-result",
        str(wait_result_path),
    )
    collect_result = run_cli("transport-collect", "--dir", str(discussion), "--round", "1", "--phase", "response")
    assert collect_result["complete"] is True

    for sender, summary in (
        ("architect", "Runtime owns the loop."),
        ("contrarian", "Prove it on a fresh directory."),
    ):
        message_path = tmp_path / f"message-{sender}.json"
        message_path.write_text(
            json.dumps(
                {
                    "from": sender,
                    "type": "argument",
                    "content": {"summary": summary},
                    "references": [],
                }
            )
        )
        run_cli(
            "append-message",
            "--dir",
            str(discussion),
            "--round",
            "1",
            "--phase",
            "response",
            "--message",
            str(message_path),
        )

    partial = json.loads((discussion / "rounds" / "001.json.partial").read_text())
    assert [item["id"] for item in partial["messages"]] == ["r1-msg-001", "r1-msg-002"]

    final_state = dict(partial)
    final_state.update(
        {
            "topic": "Fresh loop",
            "mode": "lightweight",
            "timestamp": "2026-06-10T00:00:00Z",
            "synthesis": {"recommendation": "Runtime helpers drive the loop end to end."},
            "metadata": {
                "messageCount": 2,
                "referenceCount": 0,
                "participants": ["architect", "contrarian"],
            },
        }
    )
    final_state_path = tmp_path / "final-state.json"
    final_state_path.write_text(json.dumps(final_state))
    run_cli(
        "finalize-round",
        "--dir",
        str(discussion),
        "--round",
        "1",
        "--state",
        str(final_state_path),
    )
    assert (discussion / "rounds" / "001.json").exists()
    assert not (discussion / "rounds" / "001.json.partial").exists()

    artifacts_dir = discussion / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "synthesis.md").write_text("# Synthesis\n\nRuntime helpers drive the loop end to end.\n")
    manifest = json.loads((discussion / "manifest.json").read_text())
    manifest["status"] = "completed"
    (discussion / "manifest.json").write_text(json.dumps(manifest))

    validation = run_cli("validate-discussion", str(discussion))
    assert validation["ok"] is True

    trace = run_cli("trace", "--dir", str(discussion), "--output", str(artifacts_dir / "trace.json"))
    assert trace["health"] == "on-track"
    assert trace["nextAction"]["kind"] == "none"
    assert (artifacts_dir / "trace.json").exists()

    evidence = run_cli("evidence", "--dir", str(discussion), "--output", str(artifacts_dir / "evidence.json"))
    assert evidence["outcome"]["result"] == "completed"

    loop = run_cli("validate-loop", str(discussion))
    assert loop["ok"] is True
