# SPDX-FileCopyrightText: 2023 Michael Reuter
#
# SPDX-License-Identifier: MIT

from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label
import adafruit_ntp
import adafruit_veml7700
import board
from displayio import Group
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

font = bitmap_font.load_font("fonts/SpartanMB-Regular-12.bdf")
text_area = bitmap_label.Label(font, scale=1, line_spacing=1.0)
text_area.anchor_point = (0, 0.5)
text_area.anchored_position = (0, board.DISPLAY.height // 2)
main_group = Group()
main_group.append(text_area)
board.DISPLAY.show(main_group)

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
    lux = veml7700.autolux
    white = veml7700.white
    gain = veml7700.gain_value()
    integration_time = veml7700.integration_time_value()

    text = [
        f"ALS:     {light}",
        f"Lux:     {lux:.2f}",
        f"White:   {white}",
        f"Gain:    {gain}",
        f"IntTime: {integration_time}",
    ]

    text_area.text = "\n".join(text)

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
        white=white,
        gain=gain,
        integration_time=integration_time,
    )

    writer.publish(battery_measurements_and_tags, battery_fields)
    writer.publish(light_measurements_and_tags, light_fields)

    veml7700.wait_autolux(WAIT_TIME)
