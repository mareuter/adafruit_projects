# SPDX-FileCopyrightText: 2024 Michael Reuter
#
# SPDX-License-Identifier: MIT
import argparse

from .common_parser import make_parser
from .project_handler import ProjectHandler

__all__ = ["runner"]


def main(opts: argparse.Namespace) -> None:
    if opts.debug_dir is None:
        debug_dir = opts.debug_dir
    else:
        debug_dir = opts.debug_dir.expanduser()

    ph = ProjectHandler(debug_dir=debug_dir)
    ph.web_development(opts.undo)


def runner() -> None:
    parser = make_parser()

    parser.add_argument(
        "-u",
        "--undo",
        action="store_true",
        help="Undo web developement mode. Just prints directions.",
    )

    args = parser.parse_args()
    main(args)
