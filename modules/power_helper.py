# SPDX-FileCopyrightText: 2023 Michael Reuter
#
# SPDX-License-Identifier: MIT

import board
import digitalio


def i2c_power(state: bool, is_tft: bool = False) -> None:
    """Function to switch I2C power bus on/off.

    Parameters
    ----------
    state : `bool`
        Switch setting.
    is_tft : `bool,` optional
        Is the bus on a TFT microcontroller, by default False
    """
    if is_tft:
        pin = board.TFT_I2C_POWER
    else:
        pin = board.I2C_POWER
    i2c_power_pin = digitalio.DigitalInOut(pin)
    i2c_power_pin.direction = digitalio.Direction.OUTPUT
    i2c_power_pin.value = state


def neopixel_power(state: bool) -> None:
    """Function to switch the NEOPIXEL power bus on/off.

    Parameters
    ----------
    state : `bool`
        Switch setting.
    """
    np_power_pin = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
    np_power_pin.direction = digitalio.Direction.OUTPUT
    np_power_pin.value = state
