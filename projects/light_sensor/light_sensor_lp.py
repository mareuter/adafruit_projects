# SPDX-FileCopyrightText: 2023-2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

import adafruit_veml7700
import alarm
import board
import os
import time

from battery_helper import BatteryHelper
from mqtt_helper import Fields, MqttHelper
import power_helper
import wifi_helper

ALARM_TIME = 5 * 60

# Defaults for values
light = None
lux = None
white = None
gain = None
integration_time = None

pool = wifi_helper.setup_wifi_and_rtc(start_delay=True)

if pool is not None:
    power_helper.neopixel_power(False)

    time.sleep(5)

    i2c = board.STEMMA_I2C()
    battery_monitor = BatteryHelper(i2c)
    veml7700 = adafruit_veml7700.VEML7700(i2c)
    veml7700.light_gain = veml7700.ALS_GAIN_1_8
    veml7700.light_integration_time = veml7700.ALS_100MS

    writer = MqttHelper(os.getenv("MQTT_SENSOR_NAME"), pool, 120)
    writer.mark_time()

    battery_percent, battery_voltage, battery_temperature = battery_monitor.measure()

    light = veml7700.light
    lux = veml7700.lux
    autolux = veml7700.autolux
    white = veml7700.white
    gain = veml7700.gain_value()
    integration_time = veml7700.integration_time_value()

    battery_measurements_and_tags = ["testbattery"]
    battery_fields = Fields(
        percent=battery_percent,
        voltage=battery_voltage,
        temperature=battery_temperature,
    )

    light_measurements_and_tags = ["testlight"]
    light_fields = Fields(
        light=light,
        lux=lux,
        autolux=autolux,
        white=white,
        gain=gain,
        integration_time=integration_time,
    )

    writer.publish(battery_measurements_and_tags, battery_fields)
    writer.publish(light_measurements_and_tags, light_fields)

alarm_time = time.monotonic() + ALARM_TIME
print(f"Alarm time: {alarm_time}")

time_alarm = alarm.time.TimeAlarm(monotonic_time=alarm_time)
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
