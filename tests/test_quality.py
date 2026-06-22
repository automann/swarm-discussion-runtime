"""Plan 009 step 3: discussion-quality signal + pre-synthesis stress-check decision."""

from __future__ import annotations

import json
from pathlib import Path

from swarm.quality import (
    disagreement_signal,
    effective_stress_policy,
    quality_summary,
    stress_check,
    stress_required,
    validate_quality_block,
)


def _round(messages=None, graph=None, shifts=None, **extra):
    return {
        "roundId": 1,
        "messages": messages or [],
        "argumentGraph": graph or [],
        "positionShifts": shifts or [],
        **extra,
    }


def test_disagreement_signal_counts_challenge_edges_and_stress() -> None:
    rec = _round(
        messages=[{"id": "r1-msg-001", "type": "argument"}, {"id": "r1-msg-002", "type": "stress_test"}],
        graph=[
            {"from": "r1-msg-002", "to": "r1-msg-001", "relation": "counters"},
            {"from": "r1-msg-001", "to": "r1-msg-001", "relation": "supports"},
            {"from": "r1-msg-002", "to": "r1-msg-001", "relation": "questions"},
        ],
        shifts=[{"expert": "x"}],
    )
    assert disagreement_signal(rec) == {"counterEdgeCount": 2, "positionShiftCount": 1, "stressTriggered": True}


def test_disagreement_signal_pre_stress_excludes_stress_edges() -> None:
    # a counters edge originating from a stress_test message is counted overall but
    # NOT pre-stress, so the auto decision reflects the argument phase alone.
    rec = _round(
        messages=[{"id": "r1-msg-001", "type": "argument"}, {"id": "r1-msg-002", "type": "stress_test"}],
        graph=[{"from": "r1-msg-002", "to": "r1-msg-001", "relation": "counters"}],
    )
    assert disagreement_signal(rec)["counterEdgeCount"] == 1
    assert disagreement_signal(rec, pre_stress=True)["counterEdgeCount"] == 0


def test_effective_stress_policy_defaults_off() -> None:
    assert effective_stress_policy({"stressPolicy": "required"}) == "required"
    assert effective_stress_policy({}) == "off"
    assert effective_stress_policy({"stressPolicy": "bogus"}) == "off"
    assert effective_stress_policy(None) == "off"


def test_stress_required_logic() -> None:
    assert stress_required("required", 5) is True
    assert stress_required("auto", 0) is True
    assert stress_required("auto", 1) is False
    assert stress_required("off", 0) is False


def test_validate_quality_block_rejects_forged_signal() -> None:
    rec = _round(graph=[{"from": "r1-msg-001", "to": "r1-msg-001", "relation": "counters"}])
    rec["quality"] = {"counterEdgeCount": 99, "positionShiftCount": 0, "stressTriggered": False}
    assert "quality_signal_mismatch" in {e["code"] for e in validate_quality_block(rec)}


def test_validate_quality_block_range_checks_produced_fields() -> None:
    rec = _round()
    rec["quality"] = {"genuineDisagreement": 42}
    assert "invalid_quality_block" in {e["code"] for e in validate_quality_block(rec)}


def test_validate_quality_block_inert_without_block() -> None:
    assert validate_quality_block(_round()) == []


def test_quality_summary_surfaces_signal() -> None:
    rec = _round(graph=[{"from": "r1-msg-001", "to": "r1-msg-001", "relation": "questions"}], shifts=[{}])
    block = quality_summary(rec, {"stressPolicy": "auto"})
    assert block["stressPolicy"] == "auto"
    assert block["counterEdgeCount"] == 1
    assert block["positionShiftCount"] == 1
    assert block["stressTriggered"] is False


def test_stress_check_decision(tmp_path: Path) -> None:
    def _disc(name: str, policy: str, graph) -> Path:
        d = tmp_path / name
        (d / "rounds").mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"id": "x", "stressPolicy": policy}))
        (d / "rounds" / "001.json.partial").write_text(
            json.dumps(
                _round(
                    messages=[{"id": "r1-msg-001", "type": "argument"}, {"id": "r1-msg-002", "type": "argument"}],
                    graph=graph,
                )
            )
        )
        return d

    assert stress_check(_disc("off", "off", []))["stressRequired"] is False
    assert stress_check(_disc("required", "required", []))["stressRequired"] is True
    assert stress_check(_disc("auto-empty", "auto", []))["stressRequired"] is True
    challenge = [{"from": "r1-msg-002", "to": "r1-msg-001", "relation": "counters"}]
    decision = stress_check(_disc("auto-edge", "auto", challenge))
    assert decision["stressRequired"] is False
    assert decision["counterEdgeCount"] == 1


def test_stress_check_missing_round(tmp_path: Path) -> None:
    d = tmp_path / "empty"
    (d / "rounds").mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"id": "x", "stressPolicy": "auto"}))
    result = stress_check(d)
    assert result["ok"] is False
    assert result["errors"][0]["code"] == "missing_round"
