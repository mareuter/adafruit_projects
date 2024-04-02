# SPDX-FileCopyrightText: 2023-2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

from adafruit_lc709203f import LC709203F, PackSize
from adafruit_max1704x import MAX17048


class BatteryHelper:
    def __init__(self, i2c, pack_size: str | None = None) -> None:
        """Class constructor

        Parameters
        ----------
        i2c : _type_
            Instance of the board I2C system
        pack_size : str | None, optional
            Battery pack size for estimation, by default None
        """
        self.lc_monitor = False
        if pack_size is not None:
            self.lc_monitor = True
            self.monitor = LC709203F(i2c)
            self.monitor.pack_size = getattr(PackSize, pack_size)
        else:
            self.monitor = MAX17048(i2c)

    def measure(self) -> tuple[float, float, float]:
        """Retrieve measurements from the battery.

        Returns
        -------
        percent : `float` | `None`
            The current percentage of the battery.
        voltage : `float` | `None`
            The current voltage of the battery.
        temperature : `float` | `None`
            The current temperature of the battery. Only available with
            LC709203F monitor.
        """
        percent = None
        voltage = None
        temperature = None
        try:
            percent = self.monitor.cell_percent
            voltage = self.monitor.cell_voltage
            if self.lc_monitor:
                temperature = self.monitor.cell_temperature
        except OSError as e:
            print(f"Battery monitor not available!: {e}")

        return (percent, voltage, temperature)
