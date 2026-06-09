#!/usr/bin/env python3
"""Minimal CLI entrypoint for the swarm discussion runtime incubator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from swarm import __version__, planned_commands
from swarm.collect import collect_merge
from swarm.context import build_context_summary
from swarm.prompt import build_prompt
from swarm.validation import validate_discussion_dir, validate_round_file
from swarm.wal import append_message, checkpoint, finalize_round, resume_plan


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def cmd_health(_args: argparse.Namespace) -> int:
    emit(
        {
            "ok": True,
            "name": "swarm-discussion-runtime",
            "version": __version__,
            "status": "skeleton",
        }
    )
    return 0


def cmd_planned_commands(_args: argparse.Namespace) -> int:
    emit({"commands": planned_commands()})
    return 0


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def cmd_collect_merge(args: argparse.Namespace) -> int:
    spawn_order = load_json(args.spawn_order)
    wait_results = [load_json(path) for path in args.wait_result]
    result = collect_merge(spawn_order, wait_results)
    emit(result)
    return 0 if result["ok"] else 1


def cmd_context_build(args: argparse.Namespace) -> int:
    brief = load_json(args.brief)
    result = build_context_summary(brief)
    if result["ok"] and args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result["summaryMarkdown"])
        result["summaryPath"] = str(args.out)
    emit(result)
    return 0 if result["ok"] else 1


def cmd_prompt_build(args: argparse.Namespace) -> int:
    request = load_json(args.request)
    result = build_prompt(request, base_dir=args.request.parent)
    if result["ok"] and args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = args.out_dir / "prompt.txt"
        artifact_path = args.out_dir / "prompt-build.json"
        prompt_path.write_text(result["prompt"])
        artifact_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        result["artifactPaths"] = {
            "prompt": str(prompt_path),
            "promptBuild": str(artifact_path),
        }
    emit(result)
    return 0 if result["ok"] else 1


def cmd_append_message(args: argparse.Namespace) -> int:
    result = append_message(args.dir, args.round, args.phase, load_json(args.message))
    emit(result)
    return 0 if result["ok"] else 1


def cmd_checkpoint(args: argparse.Namespace) -> int:
    result = checkpoint(args.dir, args.round, args.phase, load_json(args.state))
    emit(result)
    return 0 if result["ok"] else 1


def cmd_finalize_round(args: argparse.Namespace) -> int:
    result = finalize_round(args.dir, args.round, load_json(args.state))
    emit(result)
    return 0 if result["ok"] else 1


def cmd_resume_plan(args: argparse.Namespace) -> int:
    result = resume_plan(args.dir)
    emit(result)
    return 0 if result["ok"] else 1


def cmd_validate_round(args: argparse.Namespace) -> int:
    result = validate_round_file(args.round_path)
    emit(result)
    return 0 if result["ok"] else 1


def cmd_validate_discussion(args: argparse.Namespace) -> int:
    result = validate_discussion_dir(args.discussion_dir)
    emit(result)
    return 0 if result["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swarm-rt",
        description="Runtime incubator for swarm-discussion v2.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    health = sub.add_parser("health", help="Report skeleton runtime readiness")
    health.set_defaults(func=cmd_health)

    planned = sub.add_parser("planned-commands", help="List planned runtime command surface")
    planned.set_defaults(func=cmd_planned_commands)

    collect = sub.add_parser("collect-merge", help="Merge host wait-result batches in spawn order")
    collect.add_argument("--spawn-order", type=Path, required=True, help="JSON spawn-order list")
    collect.add_argument(
        "--wait-result",
        type=Path,
        action="append",
        required=True,
        help="JSON wait-result batch; repeat to merge partial batches",
    )
    collect.set_defaults(func=cmd_collect_merge)

    context = sub.add_parser("context-build", help="Build a compact parent-context summary")
    context.add_argument("--brief", type=Path, required=True, help="JSON parent brief")
    context.add_argument("--out", type=Path, help="Optional Markdown summary output path")
    context.set_defaults(func=cmd_context_build)

    prompt = sub.add_parser("prompt-build", help="Build an auditable prompt artifact")
    prompt.add_argument("--request", type=Path, required=True, help="JSON prompt-build request")
    prompt.add_argument("--out-dir", type=Path, help="Optional output directory for prompt artifacts")
    prompt.set_defaults(func=cmd_prompt_build)

    append = sub.add_parser("append-message", help="Mint and append one message to a round WAL")
    append.add_argument("--dir", type=Path, required=True, help="Discussion directory")
    append.add_argument("--round", type=int, required=True, help="Round number")
    append.add_argument("--phase", required=True, help="Current phase name")
    append.add_argument("--message", type=Path, required=True, help="JSON message payload without id")
    append.set_defaults(func=cmd_append_message)

    checkpoint_cmd = sub.add_parser("checkpoint", help="Atomically write a round partial")
    checkpoint_cmd.add_argument("--dir", type=Path, required=True, help="Discussion directory")
    checkpoint_cmd.add_argument("--round", type=int, required=True, help="Round number")
    checkpoint_cmd.add_argument("--phase", required=True, help="Current phase name")
    checkpoint_cmd.add_argument("--state", type=Path, required=True, help="JSON round state")
    checkpoint_cmd.set_defaults(func=cmd_checkpoint)

    finalize = sub.add_parser("finalize-round", help="Flush final state and promote partial to final")
    finalize.add_argument("--dir", type=Path, required=True, help="Discussion directory")
    finalize.add_argument("--round", type=int, required=True, help="Round number")
    finalize.add_argument("--state", type=Path, required=True, help="Final round JSON state")
    finalize.set_defaults(func=cmd_finalize_round)

    resume = sub.add_parser("resume-plan", help="Describe how to resume from WAL state")
    resume.add_argument("--dir", type=Path, required=True, help="Discussion directory")
    resume.set_defaults(func=cmd_resume_plan)

    validate_round = sub.add_parser("validate-round", help="Validate one committed round JSON file")
    validate_round.add_argument("round_path", type=Path)
    validate_round.set_defaults(func=cmd_validate_round)

    validate_discussion = sub.add_parser(
        "validate-discussion", help="Validate a discussion artifact directory"
    )
    validate_discussion.add_argument("discussion_dir", type=Path)
    validate_discussion.set_defaults(func=cmd_validate_discussion)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
