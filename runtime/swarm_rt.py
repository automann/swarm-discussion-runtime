#!/usr/bin/env python3
"""Minimal CLI entrypoint for the swarm discussion runtime incubator."""

from __future__ import annotations

import argparse
import json
from typing import Any

from swarm import __version__, planned_commands


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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
