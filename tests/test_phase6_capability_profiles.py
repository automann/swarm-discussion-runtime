from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from swarm.capabilities import capability_doctor_report, load_jsonl, validate_capability_profile


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "swarm_rt.py"
PROFILES = ROOT / "profiles"
FIXTURES = ROOT / "fixtures" / "phase6"


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


def test_expert_basic_profile_is_default_and_grants_no_tools() -> None:
    profile = load_json(PROFILES / "expert-basic.json")

    result = validate_capability_profile(profile)

    assert result["ok"] is True
    assert result["summary"]["id"] == "expert-basic"
    assert result["summary"]["default"] is True
    assert result["summary"]["allowedTools"] == []
    assert result["summary"]["broadTools"] == []


def test_readonly_profile_is_optional_and_excludes_broad_tools() -> None:
    profile = load_json(PROFILES / "expert-readonly.json")

    result = validate_capability_profile(profile)

    assert result["ok"] is True
    assert result["summary"]["default"] is False
    assert result["summary"]["readonlyTools"] == ["glob", "grep", "read"]
    assert result["summary"]["broadTools"] == []


def test_capability_doctor_cli_defaults_to_expert_basic() -> None:
    result = run_cli("capability-doctor")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["profile"]["id"] == "expert-basic"
    assert payload["effective"]["allowedTools"] == []
    assert payload["effective"]["canCiteToolDerivedEvidence"] is False


def test_capability_doctor_allows_only_logged_validated_readonly_evidence() -> None:
    result = run_cli(
        "capability-doctor",
        "--profile",
        str(PROFILES / "expert-readonly.json"),
        "--tool-evidence",
        str(FIXTURES / "tool-evidence-valid.jsonl"),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["toolEvidence"]["citable"] is True
    assert payload["toolEvidence"]["acceptedCount"] == 1
    assert payload["effective"]["canCiteToolDerivedEvidence"] is True


def test_default_profile_rejects_added_tools() -> None:
    profile = load_json(PROFILES / "expert-basic.json")
    profile["allowedTools"] = ["read"]

    result = validate_capability_profile(profile)

    assert result["ok"] is False
    assert any(error["code"] == "default_profile_tools" for error in result["errors"])


def test_ordinary_expert_rejects_broad_tools() -> None:
    profile = load_json(FIXTURES / "invalid-broad-tools-profile.json")

    result = validate_capability_profile(profile)

    assert result["ok"] is False
    assert any(error["code"] == "broad_tool_access" for error in result["errors"])


def test_unvalidated_tool_evidence_cannot_be_cited() -> None:
    result = run_cli(
        "capability-doctor",
        "--profile",
        str(PROFILES / "expert-readonly.json"),
        "--tool-evidence",
        str(FIXTURES / "tool-evidence-unvalidated.jsonl"),
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["toolEvidence"]["citable"] is False
    assert any(error["code"] == "unvalidated_tool_evidence" for error in payload["errors"])


def test_disallowed_tool_evidence_cannot_be_cited() -> None:
    profile = load_json(PROFILES / "expert-readonly.json")
    records = [load_json(FIXTURES / "tool-evidence-bash.json")]

    result = capability_doctor_report(profile, records, tool_evidence_base_dir=FIXTURES)

    assert result["ok"] is False
    assert result["effective"]["canCiteToolDerivedEvidence"] is False
    assert any(error["code"] == "tool_not_allowed" for error in result["errors"])


def test_tool_evidence_profile_mismatch_cannot_be_cited() -> None:
    profile = load_json(PROFILES / "expert-readonly.json")
    record = load_json(FIXTURES / "tool-evidence-bash.json")
    record["tool"] = "read"
    record["profileId"] = "expert-basic"

    result = capability_doctor_report(profile, [record], tool_evidence_base_dir=FIXTURES)

    assert result["ok"] is False
    assert result["effective"]["canCiteToolDerivedEvidence"] is False
    assert any(error["code"] == "profile_mismatch" for error in result["errors"])


def test_missing_tool_artifact_cannot_be_cited() -> None:
    profile = load_json(PROFILES / "expert-readonly.json")
    record = load_json(FIXTURES / "tool-evidence-bash.json")
    record["tool"] = "read"
    record["profileId"] = "expert-readonly"
    record["artifactPath"] = "artifacts/missing.json"

    result = capability_doctor_report(profile, [record], tool_evidence_base_dir=FIXTURES)

    assert result["ok"] is False
    assert result["effective"]["canCiteToolDerivedEvidence"] is False
    assert any(error["code"] == "missing_artifact" for error in result["errors"])


def test_capability_profile_schema_documents_default_and_readonly_contracts() -> None:
    schema = load_json(ROOT / "schemas" / "capability-profile.schema.json")

    assert "allowedTools" in schema["required"]
    assert schema["properties"]["allowedTools"]["items"]["enum"] == [
        "read",
        "glob",
        "grep",
        "bash",
        "edit",
        "write",
    ]
    assert "toolEvidencePolicy" in schema["required"]


def test_doctor_does_not_double_count_profile_errors() -> None:
    profile = load_json(PROFILES / "expert-readonly.json")
    profile["role"] = "superuser"
    records, errors = load_jsonl(FIXTURES / "tool-evidence-valid.jsonl")
    assert not errors

    report = capability_doctor_report(profile, records, tool_evidence_base_dir=FIXTURES)

    invalid_role_errors = [error for error in report["errors"] if error["code"] == "invalid_role"]
    assert len(invalid_role_errors) == 1


def test_records_are_not_accepted_under_an_invalid_profile() -> None:
    profile = load_json(PROFILES / "expert-readonly.json")
    profile["role"] = "superuser"
    records, errors = load_jsonl(FIXTURES / "tool-evidence-valid.jsonl")
    assert not errors

    report = capability_doctor_report(profile, records, tool_evidence_base_dir=FIXTURES)

    assert report["ok"] is False
    assert report["toolEvidence"]["acceptedCount"] == 0
    assert report["toolEvidence"]["accepted"] == []
    assert report["toolEvidence"]["citable"] is False


def test_profile_validation_requires_schema_documented_fields() -> None:
    profile = load_json(PROFILES / "expert-basic.json")
    del profile["title"]
    del profile["status"]
    del profile["toolEvidencePolicy"]["citation"]

    result = validate_capability_profile(profile)

    assert result["ok"] is False
    paths = {error["path"] for error in result["errors"]}
    assert "profile.title" in paths
    assert "profile.status" in paths
    assert "profile.toolEvidencePolicy.citation" in paths
