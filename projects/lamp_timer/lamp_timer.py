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
from digitalio import DigitalInOut, Direction
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
TEXT_COLOR = 0xFFFFFF
LIGHT_COLOR = 0xF0E442
DARK_COLOR = 0x0072B2
OFF_CIRCLE_BMP = displayio.OnDiskBitmap("images/Off_Circle.bmp")
ON_CIRCLE_BMP = displayio.OnDiskBitmap("images/On_Circle.bmp")
SUNRISE_BMP = displayio.OnDiskBitmap("images/Sunrise.bmp")
SUNSET_BMP = displayio.OnDiskBitmap("images/Sunset.bmp")
main_display = board.DISPLAY
half_label_width = main_display.width // 2
label_height = 33
time_label_width = 87
main_group = displayio.Group()
datetime_label = bitmap_label.Label(DISPLAY_FONT, color=TEXT_COLOR)
datetime_label.anchor_point = (0, 0)
datetime_label.anchored_position = (0, 2)
white_label = bitmap_label.Label(DISPLAY_FONT, color=TEXT_COLOR)
white_label.anchor_point = (0, 0)
white_label.anchored_position = (0, 35)
lux_label = bitmap_label.Label(DISPLAY_FONT, color=TEXT_COLOR)
lux_label.anchor_point = (0, 0)
lux_label.anchored_position = (half_label_width, 35)
sunrise_img = displayio.TileGrid(
    SUNRISE_BMP, pixel_shader=SUNRISE_BMP.pixel_shader, x=0, y=68
)
sunrise_time_label = bitmap_label.Label(DISPLAY_FONT, color=LIGHT_COLOR)
sunrise_time_label.anchor_point = (0, 0)
sunrise_time_label.anchored_position = (33, 68)
sunset_img = displayio.TileGrid(
    SUNSET_BMP, pixel_shader=SUNSET_BMP.pixel_shader, x=120, y=68
)
sunset_time_label = bitmap_label.Label(DISPLAY_FONT, color=DARK_COLOR)
sunset_time_label.anchor_point = (0, 0)
sunset_time_label.anchored_position = (153, 68)
on_circle_img = displayio.TileGrid(
    ON_CIRCLE_BMP, pixel_shader=ON_CIRCLE_BMP.pixel_shader, x=0, y=101
)
on_time_label = bitmap_label.Label(DISPLAY_FONT, color=LIGHT_COLOR)
on_time_label.anchor_point = (0, 0)
on_time_label.anchored_position = (33, 101)
off_circle_img = displayio.TileGrid(
    OFF_CIRCLE_BMP, pixel_shader=OFF_CIRCLE_BMP.pixel_shader, x=120, y=101
)
off_time_label = bitmap_label.Label(DISPLAY_FONT, color=DARK_COLOR)
off_time_label.anchor_point = (0, 0)
off_time_label.anchored_position = (153, 101)

main_group.append(datetime_label)
main_group.append(white_label)
main_group.append(lux_label)
main_group.append(sunrise_img)
main_group.append(sunrise_time_label)
main_group.append(sunset_img)
main_group.append(sunset_time_label)
main_group.append(on_circle_img)
main_group.append(on_time_label)
main_group.append(off_circle_img)
main_group.append(off_time_label)
main_display.root_group = main_group

# Setup power relay control
power_relay_pin = DigitalInOut(board.D5)
power_relay_pin.direction = Direction.OUTPUT

# Setup buttons
display_on_btn = DigitalInOut(board.D2)
display_on_btn.direction = Direction.INPUT
display_off_btn = DigitalInOut(board.D1)
display_off_btn.direction = Direction.INPUT

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
        main_group[8].text = f" {str(tc.lamp_on_time).split()[-1]}"
        main_group[10].text = f" {str(tc.lamp_off_time).split()[-1]}"

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
        # power_relay_pin.value = True
        print(f"Lamp off time in {current_delta} seconds")
        await asyncio.sleep(current_delta)
        print(f"Turning off lamp at {get_current_time()}")
        current_delta = get_seconds_from_now(tc.next_check_time) + 10
        # GPIO off
        # power_relay_pin.value = False
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

            main_group[1].text = f"W: {white} adc"
            main_group[2].text = f"L: {autolux:.2f} lux"

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


async def monitor_buttons() -> None:
    while True:
        if display_off_btn.value:
            main_display.root_group = None
        if display_on_btn.value:
            main_display.root_group = main_group
        await asyncio.sleep(0)


async def main():
    print("Setup")
    tc = TimerCondition()
    await asyncio.gather(
        display_information(),
        monitor_buttons(),
        measure_light(),
        time_setter(tc),
        lamp_control(tc),
    )


asyncio.run(main())
