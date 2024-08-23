# SPDX-FileCopyrightText: 2023-2024 Michael Reuter
#
# SPDX-License-Identifier: MIT
import argparse

from .common_parser import make_parser
from .project_handler import ProjectHandler

__all__ = ["runner"]


def main(opts: argparse.ArgumentParser) -> None:
    ph = ProjectHandler(debug_dir=opts.debug_dir.expanduser())
    ph.clean_debug_dir()


def runner() -> None:
    parser = make_parser(use_option=False)

    args = parser.parse_args()

    main(args)
