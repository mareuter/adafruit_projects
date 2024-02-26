# SPDX-FileCopyrightText: 2023-2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

import adafruit_sht4x
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
relative_humidity = None

pool = wifi_helper.setup_wifi_and_rtc(start_delay=True)

if pool is not None:
    # power_helper.i2c_power(True)
    power_helper.neopixel_power(False)

    time.sleep(5)

    i2c = board.STEMMA_I2C()
    battery_monitor = BatteryHelper(i2c)
    temperature_sensor = adafruit_sht4x.SHT4x(i2c)

    writer = MqttHelper(os.getenv("MQTT_SENSOR_NAME"), pool, 120)

    writer.mark_time()

    battery_percent, battery_voltage, battery_temperature = battery_monitor.measure()
    temperature, relative_humidity = temperature_sensor.measurements

    battery_measurements_and_tags = [os.getenv("MQTT_BATTERY_MEASUREMENT")]
    battery_fields = Fields(
        percent=battery_percent,
        voltage=battery_voltage,
        temperature=battery_temperature,
    )

    environment_measurements_and_tags = [os.getenv("MQTT_ENVIRONMENT_MEASUREMENT")]
    environment_fields = Fields(
        temperature=temperature, relative_humidity=relative_humidity
    )

    writer.publish(battery_measurements_and_tags, battery_fields)
    writer.publish(environment_measurements_and_tags, environment_fields)

    # power_helper.i2c_power(False)

alarm_time = time.monotonic() + ALARM_TIME
print(f"Alarm time: {alarm_time}")

time_alarm = alarm.time.TimeAlarm(monotonic_time=alarm_time)
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
