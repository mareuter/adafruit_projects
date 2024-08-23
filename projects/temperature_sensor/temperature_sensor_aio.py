# SPDX-FileCopyrightText: 2023-2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

import adafruit_sht4x
import alarm
import board
import os
import time

from aio_helper import AioHelper
from battery_helper import BatteryHelper
import power_helper
import wifi_helper

ALARM_TIME = 5 * 60  # seconds
GROUP_FEED = os.getenv("ADAFRUIT_AIO_GROUP")

# Defaults for values
temperature = None
relative_humidity = None

pool = wifi_helper.setup_wifi_and_rtc(start_delay=True, num_retries=1)

if pool is not None:
    # power_helper.i2c_power(True)
    power_helper.neopixel_power(False)

    time.sleep(5)

    i2c = board.STEMMA_I2C()
    battery_monitor = BatteryHelper(i2c)
    temperature_sensor = adafruit_sht4x.SHT4x(i2c)

    writer = AioHelper(pool)

    temperature, relative_humidity = temperature_sensor.measurements

    writer.publish(f"{GROUP_FEED}.temperature", (temperature * 1.8) + 32)
    writer.publish(f"{GROUP_FEED}.relative-humidity", relative_humidity)

    time.sleep(2)

    battery_percent, battery_voltage, battery_temperature = battery_monitor.measure()

    writer.publish(f"{GROUP_FEED}.battery-percent", battery_percent)
    writer.publish(f"{GROUP_FEED}.battery-voltage", battery_voltage)
    writer.publish(f"{GROUP_FEED}.battery-temperature", battery_temperature)

    # power_helper.i2c_power(False)

alarm_time = time.monotonic() + ALARM_TIME
print(f"Alarm time: {alarm_time}")

time_alarm = alarm.time.TimeAlarm(monotonic_time=alarm_time)
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
