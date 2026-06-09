#!/usr/bin/env python3
"""Minimal CLI entrypoint for the swarm discussion runtime incubator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from swarm import __version__, planned_commands
from swarm.collect import collect_merge
from swarm.validation import validate_discussion_dir, validate_round_file


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
