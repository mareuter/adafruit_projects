# SPDX-FileCopyrightText: 2023 Michael Reuter
#
# SPDX-License-Identifier: MIT
import argparse
import pathlib
import shutil

__all__ = ["runner"]


def main(opts: argparse.ArgumentParser) -> None:
    circuitpy_dir: pathlib.Path = opts.debug_dir.expanduser() / "CIRCUITPY"
    shutil.rmtree(circuitpy_dir, ignore_errors=True)
    (circuitpy_dir / "lib").mkdir(0o755, parents=True)


def runner() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "debug_dir", type=pathlib.Path, help="The debugging directory to cleanup."
    )

    args = parser.parse_args()

    main(args)
