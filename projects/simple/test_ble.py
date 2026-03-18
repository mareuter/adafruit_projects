# SPDX-FileCopyrightText: 2023-2026 Michael Reuter
#
# SPDX-License-Identifier: MIT
import time

from adafruit_ble_radio import Radio

r = Radio(channel=7)

while True:
    print(time.time())
    r.send("Hello from Board1")
    time.sleep(10)
