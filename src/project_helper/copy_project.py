# SPDX-FileCopyrightText: 2023-2024 Michael Reuter
#
# SPDX-License-Identifier: MIT
import argparse
import pathlib

from .common_parser import make_parser
from .project_handler import MqttInformation, ProjectHandler

__all__ = ["runner"]


def main(opts: argparse.ArgumentParser) -> None:
    if opts.debug_dir is None:
        debug_dir = opts.debug_dir
    else:
        debug_dir = opts.debug_dir.expanduser()

    mqtt_info = MqttInformation(
        no_test=opts.mqtt_no_test, sensor_name=opts.mqtt_sensor_name
    )

    ph = ProjectHandler(opts.project_file, mqtt_info, debug_dir)
    ph.copy_project()


def runner() -> None:
    parser = make_parser()

    parser.add_argument("project_file", type=pathlib.Path, help="Project file.")

    parser.add_argument(
        "--mqtt-no-test",
        action="store_true",
        help="Remove test prefixes to MQTT measurements",
    )

    parser.add_argument("--mqtt-sensor-name", help="Set a MQTT sensor name.")

    args = parser.parse_args()

    if args.mqtt_no_test and args.mqtt_sensor_name is None:
        parser.error("mqtt-sensor-name must be set if using mqtt-no-test")

    main(args)
