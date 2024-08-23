# SPDX-FileCopyrightText: 2024 Michael Reuter
#
# SPDX-License-Identifier: MIT
import argparse
import pathlib

__all__ = ["make_parser"]


def make_parser(use_option: bool = True) -> argparse.ArgumentParser:
    """Create a common parser for scripts.

    Parameters
    ----------
    use_option : bool
        Flag to create option or argument.

    Returns
    -------
    argparse.ArgumentParser
        The created common parser.
    """
    if use_option:
        option_name = "--debug-dir"
    else:
        option_name = "debug_dir"

    parser = argparse.ArgumentParser()

    parser.add_argument(
        option_name,
        type=pathlib.Path,
        help="Alternate directory to test project installation.",
    )

    return parser
