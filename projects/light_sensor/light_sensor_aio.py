# SPDX-FileCopyrightText: 2023-2025 Michael Reuter
#
# SPDX-License-Identifier: MIT

import adafruit_veml7700
import alarm
import board
import os
import time

from aio_helper import AioHelper
from battery_helper import BatteryHelper
import power_helper
import wifi_helper

ALARM_TIME = 5 * 60
GROUP_FEED = os.getenv("ADAFRUIT_AIO_GROUP")

# Defaults for values
light = None
autolux = None
white = None
gain = None
integration_time = None

pool = wifi_helper.setup_wifi_and_rtc(start_delay=True, num_retries=1)

if pool is not None:
    power_helper.neopixel_power(False)

    time.sleep(5)

    i2c = board.STEMMA_I2C()
    battery_monitor = BatteryHelper(i2c)
    veml7700 = adafruit_veml7700.VEML7700(i2c)

    writer = AioHelper(pool)

    battery_percent, battery_voltage, battery_temperature = battery_monitor.measure()
    writer.publish(f"{GROUP_FEED}.ls-battery-percent", battery_percent)
    writer.publish(f"{GROUP_FEED}.ls-battery-voltage", battery_voltage)
    writer.publish(f"{GROUP_FEED}.ls-battery-temperature", battery_temperature)

    autolux, light = veml7700.autolux_plus
    white = veml7700.white
    gain = veml7700.gain_value()
    integration_time = veml7700.integration_time_value()

    writer.publish(f"{GROUP_FEED}.light", light)
    writer.publish(f"{GROUP_FEED}.autolux", autolux)
    writer.publish(f"{GROUP_FEED}.white", white)
    writer.publish(f"{GROUP_FEED}.gain", gain)
    writer.publish(f"{GROUP_FEED}.integration-time", integration_time)

    # Delay to ensure last value gets published
    time.sleep(1)

alarm_time = time.monotonic() + ALARM_TIME
print(f"Alarm time: {alarm_time}")

time_alarm = alarm.time.TimeAlarm(monotonic_time=alarm_time)
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
