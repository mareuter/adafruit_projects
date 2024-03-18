# SPDX-FileCopyrightText: 2023-2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

from adafruit_bitmap_font import bitmap_font
from adafruit_datetime import datetime, time, timedelta, timezone
from adafruit_display_text import bitmap_label
import adafruit_requests
import adafruit_veml7700
import asyncio
import board
import displayio
import json
import os
import random
import ssl

from mqtt_helper import Fields, MqttHelper
import wifi_helper

# Defaults for values
light = None
lux = None
white = None
gain = None
integration_time = None

pool = wifi_helper.setup_wifi_and_rtc(start_delay=True)
ssl_default_context = ssl.create_default_context()
requests = adafruit_requests.Session(pool, ssl_default_context)

i2c = board.STEMMA_I2C()
veml7700 = adafruit_veml7700.VEML7700(i2c)
veml7700.light_gain = veml7700.ALS_GAIN_1_8
veml7700.light_integration_time = veml7700.ALS_100MS

# Setup display area
DISPLAY_FONT = bitmap_font.load_font("fonts/SpartanMB-Regular-12.bdf")
main_display = board.DISPLAY
label_height = main_display.height // 4
main_group = displayio.Group()
for i in range(4):
    label = bitmap_label.Label(DISPLAY_FONT)
    label.anchor_point = (0, 0)
    label.anchored_position = (0, i * label_height)
    main_group.append(label)
main_display.root_group = main_group


TIME_ZONE_NAME = os.getenv("LOCATION_TIMEZONE_NAME")
TIME_ZONE_OFFSET = timedelta(hours=int(os.getenv("LOCATION_TIMEZONE_OFFSET")))
TIME_ZONE = timezone(offset=TIME_ZONE_OFFSET, name=TIME_ZONE_NAME)
CHECK_TIME = time(0, 10, 0)
ONE_DAY = timedelta(days=1)
FIVE_MINUTES = timedelta(seconds=300)
TEN_MINUTES = timedelta(seconds=600)
LAMP_OFF_TIME = time.fromisoformat(os.getenv("LAMP_OFF_TIME"))
LOCATION_LONGITUDE = os.getenv("LOCATION_LONGITUDE")
LOCATION_LATITUDE = os.getenv("LOCATION_LATITUDE")
LOCATION_HEIGHT = os.getenv("LOCATION_HEIGHT")
HELIOS_WEBSERVICE = os.getenv("HELIOS_WEBSERVICE")
MEASURE_TIME = 5 * 60


class TimerCondition:
    def __init__(self):
        self.initialized = False
        self.next_check_time = None
        self.lamp_on_time = None
        self.lamp_off_time = None


def get_current_time() -> datetime:
    return datetime.now() + TIME_ZONE_OFFSET


def get_seconds_from_now(dt: datetime) -> int:
    now = get_current_time()
    return (dt - now).total_seconds()


def get_on_variation_from_range() -> timedelta:
    value = random.randrange(-FIVE_MINUTES.seconds, FIVE_MINUTES.seconds)
    return timedelta(seconds=value)


def get_off_variation_from_range() -> timedelta:
    value = random.randrange(-TEN_MINUTES.seconds, TEN_MINUTES.seconds)
    return timedelta(seconds=value)


async def time_setter(tc: TimerCondition) -> None:
    while True:
        current_time = get_current_time()
        current_date = current_time.date()
        print(current_time)
        print("Setting up conditions")

        url = [
            HELIOS_WEBSERVICE,
            "?",
            f"cdatetime={int((current_time - TIME_ZONE_OFFSET).timestamp())}",
            "&",
            f"tz={TIME_ZONE_NAME}",
            "&",
            f"lat={LOCATION_LATITUDE}",
            "&",
            f"lon={LOCATION_LONGITUDE}",
        ]

        print("".join(url))
        response = requests.get("".join(url))
        info = json.loads(response.content.decode())
        print(int((current_time - TIME_ZONE_OFFSET).timestamp()))
        print(int(info["sunset"]))
        print(datetime.fromtimestamp(float(info["sunset"])) + TIME_ZONE_OFFSET)
        tc.lamp_on_time = (
            datetime.fromtimestamp(float(info["sunset"]))
            + TIME_ZONE_OFFSET
            + get_on_variation_from_range()
        )
        tc.lamp_off_time = (
            datetime.combine(current_date, LAMP_OFF_TIME)
            + get_off_variation_from_range()
        )
        tc.initialized = True
        main_group[2].text = f"Lamp On: {str(tc.lamp_on_time).split()[-1]}"
        main_group[3].text = f"Lamp Off: {str(tc.lamp_off_time).split()[-1]}"

        tc.next_check_time = datetime.combine(current_date, CHECK_TIME) + ONE_DAY
        current_delta = get_seconds_from_now(tc.next_check_time)
        print(f"Next check time in {current_delta} seconds")
        await asyncio.sleep(current_delta)
        tc.initialized = False


async def lamp_control(tc: TimerCondition) -> None:
    while True:
        while not tc.initialized:
            print("Waiting for conditions")
            await asyncio.sleep(1)
        current_delta = get_seconds_from_now(tc.lamp_on_time)
        print(f"Lamp on time in {current_delta} seconds")
        await asyncio.sleep(current_delta)
        print(f"Turning on lamp at {get_current_time()}")
        current_delta = get_seconds_from_now(tc.lamp_off_time)
        # GPIO on
        print(f"Lamp off time in {current_delta} seconds")
        await asyncio.sleep(current_delta)
        print(f"Turning off lamp at {get_current_time()}")
        current_delta = get_seconds_from_now(tc.next_check_time) + 10
        # GPIO off
        print(f"Next lamp control check in {current_delta} seconds")
        await asyncio.sleep(current_delta)


async def measure_light() -> None:
    while True:
        if pool is not None:
            writer = MqttHelper(os.getenv("MQTT_SENSOR_NAME"), pool, 120)
            writer.mark_time()

            light = veml7700.light
            lux = veml7700.lux
            autolux = veml7700.autolux
            white = veml7700.white
            gain = veml7700.gain_value()
            integration_time = veml7700.integration_time_value()

            main_group[1].text = f"Lux: {autolux}"

            light_measurements_and_tags = [os.getenv("MQTT_LIGHT_MEASUREMENT")]
            light_fields = Fields(
                light=light,
                lux=lux,
                autolux=autolux,
                white=white,
                gain=gain,
                integration_time=integration_time,
            )

            writer.publish(light_measurements_and_tags, light_fields)

        await asyncio.sleep(MEASURE_TIME)


async def display_information() -> None:
    while True:
        now = get_current_time()
        date_str, time_str = now.isoformat().split("T")
        time_str = ":".join(time_str.split(":")[:-1])
        main_group[0].text = f"{date_str} {time_str}"
        await asyncio.sleep(60)


async def main():
    print("Setup")
    tc = TimerCondition()
    await asyncio.gather(
        display_information(), time_setter(tc), lamp_control(tc), measure_light()
    )


asyncio.run(main())
