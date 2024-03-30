# SPDX-FileCopyrightText: 2023-2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

from adafruit_bitmap_font import bitmap_font
from adafruit_datetime import datetime, time
from adafruit_display_text import bitmap_label
import adafruit_requests
import adafruit_veml7700
import asyncio
import board
from digitalio import DigitalInOut, Direction
import displayio
import json
import os
import ssl

from battery_helper import BatteryHelper
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
battery_monitor = BatteryHelper(i2c)
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
main_display.brightness = 1.0
half_label_width = main_display.width // 2
label_height = 33
time_label_width = 87
main_group = displayio.Group()
datetime_label = bitmap_label.Label(DISPLAY_FONT, color=TEXT_COLOR)
datetime_label.anchor_point = (0.5, 0.25)
datetime_label.anchored_position = (half_label_width, 10)
white_label = bitmap_label.Label(DISPLAY_FONT, color=TEXT_COLOR)
white_label.anchor_point = (0.25, 0.25)
white_label.anchored_position = (30, 43)
lux_label = bitmap_label.Label(DISPLAY_FONT, color=TEXT_COLOR)
lux_label.anchor_point = (0.25, 0.25)
lux_label.anchored_position = (half_label_width + 30, 43)
sunrise_img = displayio.TileGrid(
    SUNRISE_BMP, pixel_shader=SUNRISE_BMP.pixel_shader, x=0, y=68
)
sunrise_time_label = bitmap_label.Label(DISPLAY_FONT, color=LIGHT_COLOR)
sunrise_time_label.anchor_point = (0.5, 0.3175)
sunrise_time_label.anchored_position = (76, 78)
sunset_img = displayio.TileGrid(
    SUNSET_BMP, pixel_shader=SUNSET_BMP.pixel_shader, x=120, y=68
)
sunset_time_label = bitmap_label.Label(DISPLAY_FONT, color=DARK_COLOR)
sunset_time_label.anchor_point = (0.5, 0.3175)
sunset_time_label.anchored_position = (196, 78)
on_circle_img = displayio.TileGrid(
    ON_CIRCLE_BMP, pixel_shader=ON_CIRCLE_BMP.pixel_shader, x=0, y=101
)
on_time_label = bitmap_label.Label(DISPLAY_FONT, color=LIGHT_COLOR)
on_time_label.anchor_point = (0.5, 0.3175)
on_time_label.anchored_position = (76, 111)
off_circle_img = displayio.TileGrid(
    OFF_CIRCLE_BMP, pixel_shader=OFF_CIRCLE_BMP.pixel_shader, x=120, y=101
)
off_time_label = bitmap_label.Label(DISPLAY_FONT, color=DARK_COLOR)
off_time_label.anchor_point = (0.5, 0.3175)
off_time_label.anchored_position = (196, 111)

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
CHECK_TIME = os.getenv("CHECK_TIME")
ON_RANGE = os.getenv("ON_RANGE")
OFF_RANGE = os.getenv("OFF_RANGE")
LAMP_OFF_TIME = time.fromisoformat(os.getenv("LAMP_OFF_TIME"))
LOCATION_LONGITUDE = os.getenv("LOCATION_LONGITUDE")
LOCATION_LATITUDE = os.getenv("LOCATION_LATITUDE")
LOCATION_HEIGHT = os.getenv("LOCATION_HEIGHT")
HELIOS_WEBSERVICE = os.getenv("HELIOS_WEBSERVICE")
MEASURE_TIME = 5 * 60
DISPLAY_TIMEOUT = 5 * 60


class TimerCondition:
    def __init__(self):
        self.initialized = False
        self.next_check_time = None
        self.lamp_on_time = None
        self.lamp_off_time = None


def get_current_time() -> float:
    return datetime.now()


def get_seconds_from_now(dt: float) -> float:
    now = get_current_time()
    print(f"Now: {now.timestamp():.0f}")
    return dt - now.timestamp()


async def dim_screen(evt: asyncio.Event) -> None:
    while True:
        interrupted = False
        await evt.wait()
        print("Starting display timeout")
        timeout = DISPLAY_TIMEOUT
        while timeout > 0:
            if not evt.is_set():
                interrupted = True
                print("Interrupt display timeout")
                break
            await asyncio.sleep(1)
            timeout -= 1
        if not interrupted:
            print("Turning off display")
            main_display.brightness = 0.0
            evt.clear()


async def time_setter(tc: TimerCondition) -> None:
    while True:
        current_time = get_current_time()
        print(int(current_time.timestamp()))
        print("Setting up conditions")

        url = [
            HELIOS_WEBSERVICE,
            "?",
            f"cdatetime={int(current_time.timestamp())}",
            "&",
            f"tz={TIME_ZONE_NAME}",
            "&",
            f"lat={LOCATION_LATITUDE}",
            "&",
            f"lon={LOCATION_LONGITUDE}",
            "&",
            f"checktime={CHECK_TIME}",
            "&",
            f"offtime={LAMP_OFF_TIME}",
            "&",
            f"onrange={ON_RANGE}",
            "&",
            f"offrange={OFF_RANGE}",
        ]

        print("".join(url))
        response = requests.get("".join(url))
        info = json.loads(response.content)

        tc.lamp_on_time = info["on_time_utc"]
        print(f"LOnT: {tc.lamp_on_time}")
        tc.lamp_off_time = info["off_time_utc"]
        print(f"LOfT: {tc.lamp_off_time}")
        tc.next_check_time = info["check_time_utc"]
        print(f"CHKT: {tc.next_check_time}")
        tc.initialized = True

        main_group[0].text = info["date"]
        main_group[4].text = info["sunrise_usno"]
        main_group[6].text = info["sunset_usno"]
        main_group[8].text = info["on_time"]
        main_group[10].text = info["off_time"]

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
        power_relay_pin.value = True
        print(f"Lamp off time in {current_delta} seconds")
        await asyncio.sleep(current_delta)
        print(f"Turning off lamp at {get_current_time()}")
        # GPIO off
        power_relay_pin.value = False
        current_delta = get_seconds_from_now(tc.next_check_time) + 10
        print(f"Next lamp control check in {current_delta} seconds")
        await asyncio.sleep(current_delta)


async def measure_light() -> None:
    while True:
        if pool is not None:
            writer = MqttHelper(os.getenv("MQTT_SENSOR_NAME"), pool, 120)
            writer.mark_time()

            (
                battery_percent,
                battery_voltage,
                battery_temperature,
            ) = battery_monitor.measure()

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

            battery_measurements_and_tags = [os.getenv("MQTT_BATTERY_MEASUREMENT")]
            battery_fields = Fields(
                percent=battery_percent,
                voltage=battery_voltage,
                temperature=battery_temperature,
            )

            writer.publish(light_measurements_and_tags, light_fields)
            writer.publish(battery_measurements_and_tags, battery_fields)

        await asyncio.sleep(MEASURE_TIME)


async def monitor_buttons(evt: asyncio.Event) -> None:
    evt.set()
    while True:
        if display_off_btn.value:
            main_display.root_group = None
            main_display.brightness = 0.0
            evt.clear()
        if display_on_btn.value:
            if main_display.brightness != 1.0:
                main_display.brightness = 1.0
            main_display.root_group = main_group
            evt.set()
        await asyncio.sleep(0)


async def main():
    print("Setup")
    tc = TimerCondition()
    display_event = asyncio.Event()
    await asyncio.gather(
        time_setter(tc),
        lamp_control(tc),
        measure_light(),
        monitor_buttons(display_event),
        dim_screen(display_event),
    )


asyncio.run(main())
