# SPDX-FileCopyrightText: 2024 Michael Reuter
#
# SPDX-License-Identifier: MIT
import os
import pathlib


CIRCUITPY_DIR = "CIRCUITPY"
BOOT_OUT_FILE = "boot_out.txt"


def main() -> None:
    top_dir = pathlib.Path(".").resolve()
    circuitboard_location = (
        pathlib.Path("/media") / top_dir.parents[2].name / CIRCUITPY_DIR
    )
    boot_file = circuitboard_location / BOOT_OUT_FILE
    lines = boot_file.read_text().strip()
    for line in lines.split(os.linesep):
        if line.startswith("UID"):
            print(f"Board {line}")


def runner() -> None:
    main()
