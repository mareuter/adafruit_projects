# SPDX-FileCopyrightText: 2023 Michael Reuter
#
# SPDX-License-Identifier: MIT

import adafruit_ds18x20
from adafruit_onewire.bus import OneWireBus
import alarm
import board
import os
import time

from battery_helper import BatteryHelper
from mqtt_helper import Fields, MqttHelper
import power_helper
import wifi_helper

ALARM_TIME = 5 * 60  # seconds

# Defaults for values
temperature = None

pool = wifi_helper.setup_wifi_and_rtc(start_delay=True)

if pool is None:
    # power_helper.i2c_power(True)
    power_helper.neopixel_power(False)

    time.sleep(5)

    ow_bus = OneWireBus(board.D5)
    ds18b20 = adafruit_ds18x20.DS18X20(ow_bus, ow_bus.scan()[0])
    ds18b20.resolution = 9

    i2c = board.STEMMA_I2C()
    battery_monitor = BatteryHelper(i2c)

    writer = MqttHelper(os.getenv("MQTT_SENSOR_NAME"), pool, 120)

    writer.mark_time()

    battery_percent, battery_voltage, battery_temperature = battery_monitor.measure()
    temperature = ds18b20.temperature

    battery_measurements_and_tags = ["testbattery"]
    battery_fields = Fields(
        percent=battery_percent,
        voltage=battery_voltage,
        temperature=battery_temperature,
    )

    environment_measurements_and_tags = ["testenvironment"]
    environment_fields = Fields(
        temperature=temperature,
    )

    writer.publish(battery_measurements_and_tags, battery_fields)
    writer.publish(environment_measurements_and_tags, environment_fields)

    time.sleep(5)

    # power_helper.i2c_power(False)

alarm_time = time.monotonic() + ALARM_TIME
print(f"Alarm time: {alarm_time}")

time_alarm = alarm.time.TimeAlarm(monotonic_time=alarm_time)
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
