# SPDX-FileCopyrightText: 2023 Michael Reuter
#
# SPDX-License-Identifier: MIT

import argparse
import pathlib
import subprocess

__all__ = ["runner"]


def main(opts: argparse.Namespace) -> None:
    output_stem = opts.font_file.stem
    output_font_file = pathlib.Path(f"{output_stem}-{opts.size}.bdf")

    cmd = [
        "otf2bdf",
        opts.font_file.name,
        "-p",
        str(opts.size),
        "-o",
        output_font_file.name,
    ]

    subprocess.run(cmd)


def runner() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("size", type=int, help="Font size to create.")
    parser.add_argument(
        "font_file", type=pathlib.Path, help="The font file to convert."
    )

    args = parser.parse_args()

    main(args)
