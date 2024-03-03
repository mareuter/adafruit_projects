# SPDX-FileCopyrightText: 2024 Michael Reuter
#
# SPDX-License-Identifier: MIT
import argparse
import pathlib

__all__ = ["make_parser"]


def make_parser() -> argparse.ArgumentParser:
    """Create a common parser for scripts.

    Returns
    -------
    argparse.ArgumentParser
        The created common parser.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--debug-dir",
        type=pathlib.Path,
        help="Alternate directory to test project installation.",
    )

    return parser
