# SPDX-FileCopyrightText: 2023-2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

import adafruit_veml7700
import board
import os
import time

from aio_helper import AioHelper
from battery_helper import BatteryHelper
import wifi_helper

WAIT_TIME = 5 * 60
GROUP_FEED = os.getenv("ADAFRUIT_AIO_GROUP")

# Defaults for values
light = None
lux = None
white = None
gain = None
integration_time = None

pool = wifi_helper.setup_wifi_and_rtc(start_delay=True)
if pool is not None:
    i2c = board.STEMMA_I2C()
    battery_monitor = BatteryHelper(i2c)
    veml7700 = adafruit_veml7700.VEML7700(i2c)
    veml7700.light_gain = veml7700.ALS_GAIN_1_8
    veml7700.light_integration_time = veml7700.ALS_100MS

    writer = AioHelper(pool)

    while True:
        # battery_percent, battery_voltage,
        # battery_temperature = battery_monitor.measure()

        light = veml7700.light
        lux = veml7700.lux
        autolux = veml7700.autolux
        white = veml7700.white
        gain = veml7700.gain_value()
        integration_time = veml7700.integration_time_value()

        writer.publish(f"{GROUP_FEED}.light", light)
        writer.publish(f"{GROUP_FEED}.lux", lux)
        writer.publish(f"{GROUP_FEED}.autolux", autolux)
        # writer.publish(f"{GROUP_FEED}.white", white)
        writer.publish(f"{GROUP_FEED}.gain", gain)
        writer.publish(f"{GROUP_FEED}.integration-time", integration_time)

        # Delay to ensure last value gets published
        time.sleep(1)

        veml7700.wait_autolux(WAIT_TIME)
