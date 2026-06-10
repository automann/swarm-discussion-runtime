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


def test_planned_commands_include_the_planned_commands_listing_itself() -> None:
    assert "planned-commands" in swarm.planned_commands()


def test_protocol_package_is_present_and_maps_to_real_commands() -> None:
    protocol_dir = ROOT / "protocol"
    for name in (
        "README.md",
        "PROTOCOL.md",
        "SCHEMA.md",
        "SEAM.md",
        "durability.md",
        "windowing.md",
        "prompts.md",
        "templates/persona-generator.md",
    ):
        assert (protocol_dir / name).exists(), name

    readme = (protocol_dir / "README.md").read_text()
    referenced = {
        token.split("`")[0]
        for token in readme.split("swarm-rt ")[1:]
    }
    implemented = set(swarm.planned_commands())
    assert referenced, "mapping table must reference runtime commands"
    assert referenced <= implemented, referenced - implemented


def test_governance_docs_reflect_source_of_truth_role() -> None:
    # The artifacts the governance docs lean on must exist.
    for path in (
        "docs/ADAPTER-SPEC.md",
        "scripts/vendor.py",
        "conformance/certify_adapter.py",
        "protocol/README.md",
        "fixtures/legacy/README.md",
    ):
        assert (ROOT / path).exists(), path

    agents = (ROOT / "AGENTS.md").read_text()
    assert "ADAPTER-SPEC" in agents
    assert "scripts/vendor.py" in agents

    acceptance = (ROOT / "ACCEPTANCE.md").read_text()
    assert "certify_adapter.py" in acceptance
    assert "fixtures/legacy" in acceptance

    architecture = (ROOT / "ARCHITECTURE.md").read_text()
    assert "Repository Topology" in architecture
    assert "vendor-manifest.json" in architecture

    non_goals = (ROOT / "NON_GOALS.md").read_text()
    assert "Not A Host Adapter" in non_goals
    assert "Not The Distribution Repo" in non_goals
