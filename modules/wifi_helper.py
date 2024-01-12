# SPDX-FileCopyrightText: 2023 Michael Reuter
#
# SPDX-License-Identifier: MIT

import adafruit_ntp
import rtc
import socketpool
import time
import wifi

__all__ = ["setup_wifi_and_rtc"]


def setup_wifi_and_rtc(
    start_delay: bool = False, retry_delay: float = 2
) -> socketpool.SocketPool | None:
    """Setup wifi and initialize RTC with NTP.

    Parameters
    ----------
    start_delay : `bool`, optional
        Delay the function start, useful for programs coming up from deep
        sleep, by default False
    retry_delay : f`loat`, optional
        The delay time (seconds) between connection retries, by default 2

    Returns
    -------
    `socketpool.SocketPool` | None
        The socket pool for use in other network connections.
    """
    if start_delay:
        time.sleep(5)

    retries = 5
    pool: socketpool.SocketPool | None = None
    while retries > 0:
        try:
            pool = socketpool.SocketPool(wifi.radio)
            ntp = adafruit_ntp.NTP(pool, tz_offset=0)
            rtc.RTC().datetime = ntp.datetime
            break
        except Exception:
            print("Cannot connect to wifi.")
            pool = None
            retries -= 1
            if not retries:
                break
            time.sleep(retry_delay)

    return pool
