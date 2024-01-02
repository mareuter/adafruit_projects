# SPDX-FileCopyrightText: 2023 Michael Reuter
#
# SPDX-License-Identifier: MIT
import argparse
import pathlib

from .project_handler import ProjectHandler

__all__ = ["runner"]


def main(opts: argparse.ArgumentParser) -> None:
    if opts.debug_dir is None:
        debug_dir = opts.debug_dir
    else:
        debug_dir = opts.debug_dir.expanduser()

    ph = ProjectHandler(opts.project_file, debug_dir)
    ph.copy_project()


def runner() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("project_file", type=pathlib.Path, help="Project file.")

    parser.add_argument(
        "--debug-dir",
        type=pathlib.Path,
        help="Alternate directory to test project installation.",
    )

    args = parser.parse_args()
    main(args)
