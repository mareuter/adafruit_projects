# SPDX-FileCopyrightText: 2023-2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

import adafruit_ds18x20
from adafruit_onewire.bus import OneWireBus
import adafruit_thermistor
import alarm
import board
import os
import time

from aio_helper import AioHelper
from battery_helper import BatteryHelper
import power_helper
import wifi_helper

ALARM_TIME = 5 * 60  # seconds
NTC_THERM_RESISTOR = 10000.0  # ohms
THERM_VDIV_RESISTOR = 10000.0  # ohms
NOMINAL_THERM_TEMP = 25.0  # C
THERM_BETA = 3950.0
GROUP_FEED = os.getenv("ADAFRUIT_AIO_GROUP")

# Defaults for values
water_temperature = None
battery_temperature = None

pool = wifi_helper.setup_wifi_and_rtc(start_delay=True, num_retries=1)

if pool is not None:
    # power_helper.i2c_power(True)
    power_helper.neopixel_power(False)

    time.sleep(5)

    try:
        ow_bus = OneWireBus(board.D5)
        ds18b20 = adafruit_ds18x20.DS18X20(ow_bus, ow_bus.scan()[0])

        thermistor = adafruit_thermistor.Thermistor(
            board.A1,
            NTC_THERM_RESISTOR,
            THERM_VDIV_RESISTOR,
            NOMINAL_THERM_TEMP,
            THERM_BETA,
            high_side=False,
        )

        i2c = board.STEMMA_I2C()
        battery_monitor = BatteryHelper(i2c)

        writer = AioHelper(pool)
        if writer.is_connected:
            battery_temperature = thermistor.temperature
            try:
                water_temperature = ds18b20.temperature
            except RuntimeError:
                print("Cannot read water temperature sensor")
                pass

            writer.publish(f"{GROUP_FEED}.temperature", water_temperature)

            (
                battery_percent,
                battery_voltage,
                _,
            ) = battery_monitor.measure()

            writer.publish(f"{GROUP_FEED}.battery-percent", battery_percent)
            writer.publish(f"{GROUP_FEED}.battery-voltage", battery_voltage)
            writer.publish(f"{GROUP_FEED}.battery-temperature", battery_temperature)

            print(battery_voltage)
            print(battery_percent)
            print(battery_temperature)
            print(thermistor.resistance)
            print(water_temperature)

            # Delay to ensure last value gets published
            time.sleep(1)

    except Exception as e:
        print(type(e).__name__)
        pass
    # power_helper.i2c_power(False)

alarm_time = time.monotonic() + ALARM_TIME
print(f"Alarm time: {alarm_time}")

time_alarm = alarm.time.TimeAlarm(monotonic_time=alarm_time)
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
