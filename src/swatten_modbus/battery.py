"""The battery."""

from __future__ import annotations

from modbus_connection.model import Component, gauge, integer


class Battery(Component):
    """Battery voltage, current, power and state."""

    register_space = "input"

    battery_voltage = gauge(10020, 0.0, signed=False, unit="V")
    """Always ``0.0``: upstream declares this register with ``scale = 0.0``."""

    battery_current = gauge(10021, 0.1, signed=False, unit="A")
    battery_power = integer(10022, unit="W")
    """Charge/discharge power, signed."""

    battery_soc = integer(10023, signed=False, unit="%")
    battery_soh = integer(10024, signed=False, unit="%")
