# SPDX-FileCopyrightText: 2023-2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

import alarm
import board
import os
import time

from battery_helper import BatteryHelper
from mqtt_helper import Fields, MqttHelper
import power_helper
import wifi_helper

ALARM_TIME = 5 * 60  # seconds

pool = wifi_helper.setup_wifi_and_rtc(start_delay=True, num_retries=1)

if pool is not None:
    # power_helper.i2c_power(True)
    power_helper.neopixel_power(False)

    time.sleep(5)

    i2c = board.STEMMA_I2C()
    battery_monitor = BatteryHelper(i2c)

    writer = MqttHelper(os.getenv("MQTT_SENSOR_NAME"), pool, 120)

    writer.mark_time()

    battery_percent, battery_voltage, battery_temperature = battery_monitor.measure()

    battery_measurements_and_tags = [os.getenv("MQTT_BATTERY_MEASUREMENT")]
    battery_fields = Fields(
        percent=battery_percent,
        voltage=battery_voltage,
        temperature=battery_temperature,
    )

    writer.publish(battery_measurements_and_tags, battery_fields)

    # power_helper.i2c_power(False)

alarm_time = time.monotonic() + ALARM_TIME
print(f"Alarm time: {alarm_time}")

time_alarm = alarm.time.TimeAlarm(monotonic_time=alarm_time)
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
