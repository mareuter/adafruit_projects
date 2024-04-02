# SPDX-FileCopyrightText: 2024 Michael Reuter
#
# SPDX-License-Identifier: MIT
import argparse

from .common_parser import make_parser
from .project_handler import DownloadOptions, ProjectHandler

__all__ = ["runner"]


def main(opts: argparse.Namespace) -> None:
    dl = DownloadOptions(opts.boards, opts.cross_compiler, opts.bundles)
    ph = ProjectHandler(download_options=dl)
    ph.get_circuitpython(opts.circuitpython_version, opts.bundle_date)


def runner() -> None:
    parser = make_parser()

    parser.add_argument(
        "circuitpython_version", type=str, help="The CircuitPython version to retrieve."
    )
    parser.add_argument(
        "bundle_date", type=str, help="The bundle date to retrieve in YYYYMMDD format."
    )

    parser.add_argument(
        "-c",
        "--cross-compiler",
        action="store_true",
        help="Download a new cross-compiler.",
    )
    parser.add_argument(
        "-b", "--boards", action="store_true", help="Download new UF2 bootloaders."
    )
    parser.add_argument(
        "-u",
        "--bundles",
        action="store_true",
        help="Download new CircuitPython bundles.",
    )

    args = parser.parse_args()
    main(args)
