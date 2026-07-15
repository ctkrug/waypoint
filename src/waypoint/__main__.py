"""``python -m waypoint`` -- inspect and manage stored checkpoints."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import cli
from .storage import DEFAULT_CHECKPOINT_DIR


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="waypoint")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="list stored checkpoints")
    status_parser.add_argument(
        "--dir", default=str(DEFAULT_CHECKPOINT_DIR), help="checkpoint directory"
    )

    clear_parser = subparsers.add_parser("clear", help="delete a stored checkpoint")
    clear_parser.add_argument("key", help="checkpoint key, e.g. as shown by 'status'")
    clear_parser.add_argument(
        "--dir", default=str(DEFAULT_CHECKPOINT_DIR), help="checkpoint directory"
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "status":
        return cli.status(Path(args.dir), sys.stdout)
    return cli.clear(args.key, Path(args.dir), sys.stdout)


if __name__ == "__main__":
    sys.exit(main())
