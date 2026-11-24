"""Command line entry point: ``firstline <command>``."""

from __future__ import annotations

import argparse
import json
import sys

from firstline import __version__
from firstline.config import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="firstline", description=__doc__)
    parser.add_argument("--version", action="version", version=f"firstline {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("config", help="print the effective settings (secrets masked)")

    args = parser.parse_args(argv)
    if args.command == "config":
        print(json.dumps(Settings().public_view(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
