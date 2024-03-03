# SPDX-FileCopyrightText: 2024 Michael Reuter
#
# SPDX-License-Identifier: MIT
from .project_handler import ProjectHandler

__all__ = ["runner"]


def main() -> None:
    ph = ProjectHandler()
    ph.get_board_uid()


def runner() -> None:
    main()
