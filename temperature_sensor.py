# SPDX-FileCopyrightText: 2023 Michael Reuter
#
# SPDX-License-Identifier: MIT

import adafruit_ntp
import adafruit_sht4x
import alarm
import board
import os
import rtc
import socketpool
import time
import wifi

from battery_helper import BatteryHelper
from mqtt_helper import Fields, MqttHelper
import power_helper

ALARM_TIME = 5 * 60  # seconds

# Defaults for values
temperature = None
relative_humidity = None

pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=0)
rtc.RTC().datetime = ntp.datetime

power_helper.i2c_power(True)
power_helper.neopixel_power(False)

time.sleep(5)

i2c = board.STEMMA_I2C()
battery_monitor = BatteryHelper(i2c)
temperature_sensor = adafruit_sht4x.SHT4x(i2c)

writer = MqttHelper(os.getenv("MQTT_SENSOR_NAME"), pool, 120)

writer.mark_time()

battery_percent, battery_voltage, battery_temperature = battery_monitor.measure()
temperature, relative_humidity = temperature_sensor.measurements

battery_measurements_and_tags = ["testbattery"]
battery_fields = Fields(
    percent=battery_percent, voltage=battery_voltage, temperature=battery_temperature
)

environment_measurements_and_tags = ["testenvironment"]
environment_fields = Fields(
    temperature=temperature, relative_humidity=relative_humidity
)

writer.publish(battery_measurements_and_tags, battery_fields)
writer.publish(environment_measurements_and_tags, environment_fields)

time.sleep(5)

power_helper.i2c_power(False)

alarm_time = time.monotonic() + ALARM_TIME
print(f"Alarm time: {alarm_time}")

time_alarm = alarm.time.TimeAlarm(monotonic_time=alarm_time)
alarm.exit_and_deep_sleep_until_alarms(time_alarm)