# SPDX-FileCopyrightText: 2023 Michael Reuter
#
# SPDX-License-Identifier: MIT

import adafruit_ntp
import adafruit_veml7700
import board
import os
import rtc
import socketpool
import wifi

from battery_helper import BatteryHelper
from mqtt_helper import Fields, MqttHelper

WAIT_TIME = 5 * 60

# Defaults for values
light = None
lux = None
white = None
gain = None
integration_time = None

pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=0)
rtc.RTC().datetime = ntp.datetime

i2c = board.STEMMA_I2C()
battery_monitor = BatteryHelper(i2c)
veml7700 = adafruit_veml7700.VEML7700(i2c)
veml7700.light_gain = veml7700.ALS_GAIN_1_8
veml7700.light_integration_time = veml7700.ALS_100MS

writer = MqttHelper(os.getenv("MQTT_SENSOR_NAME"), pool, WAIT_TIME + 10)

while True:
    writer.mark_time()

    battery_percent, battery_voltage, battery_temperature = battery_monitor.measure()

    light = veml7700.light
    lux = veml7700.lux
    autolux = veml7700.autolux
    white = veml7700.white
    gain = veml7700.gain_value()
    integration_time = veml7700.integration_time_value()

    battery_measurements_and_tags = [os.getenv("MQTT_BATTERY_MEASUREMENT")]
    battery_fields = Fields(
        percent=battery_percent,
        voltage=battery_voltage,
        temperature=battery_temperature,
    )

    light_measurements_and_tags = [os.getenv("MQTT_LIGHT_MEASUREMENT")]
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

    veml7700.wait_autolux(WAIT_TIME)
