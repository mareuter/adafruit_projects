# SPDX-FileCopyrightText: 2023-2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

from adafruit_datetime import datetime, time, timedelta, timezone
import adafruit_requests
import asyncio
import json
import os
import random
import ssl

import wifi_helper


pool = wifi_helper.setup_wifi_and_rtc(start_delay=True)
ssl_default_context = ssl.create_default_context()
requests = adafruit_requests.Session(pool, ssl_default_context)


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


async def time_setter(tc):
    while True:
        current_time = get_current_time()
        current_date = current_time.date()
        print(current_time)
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
        ]

        response = requests.get("".join(url))
        info = json.loads(response.content.decode())

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

        tc.next_check_time = datetime.combine(current_date, CHECK_TIME) + ONE_DAY
        current_delta = get_seconds_from_now(tc.next_check_time)
        print(f"Next check time in {current_delta} seconds")
        await asyncio.sleep(current_delta)
        tc.initialized = False


async def lamp_control(tc):
    while True:
        while not tc.initialized:
            print("Waiting for conditions")
            await asyncio.sleep(1)
        current_delta = get_seconds_from_now(tc.lamp_on_time)
        print(f"Lamp on time in {current_delta} seconds")
        await asyncio.sleep(current_delta)
        print(f"Turning on lamp at {get_current_time()}")
        current_delta = get_seconds_from_now(tc.lamp_off_time)
        print(f"Lamp off time in {current_delta} seconds")
        await asyncio.sleep(current_delta)
        print(f"Turning off lamp at {get_current_time()}")
        current_delta = get_seconds_from_now(tc.next_check_time) + 10
        print(f"Next lamp control check in {current_delta} seconds")
        await asyncio.sleep(current_delta)


async def main():
    print("Setup")
    tc = TimerCondition()
    await asyncio.gather(time_setter(tc), lamp_control(tc))


asyncio.run(main())
