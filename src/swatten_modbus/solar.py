"""The two PV strings."""

from __future__ import annotations

from modbus_connection.model import Component, gauge, uint32


class Solar(Component):
    """PV string voltages and currents, and total PV power."""

    register_space = "input"

    pv_voltage_1 = gauge(4061, 0.1, signed=False, unit="V")
    pv_current_1 = gauge(4062, 0.1, signed=False, unit="A")
    pv_voltage_2 = gauge(4063, 0.1, signed=False, unit="V")
    pv_current_2 = gauge(4064, 0.1, signed=False, unit="A")
    pv_power_total = uint32(4067, unit="W")

    @property
    def pv_power_1(self) -> float | None:
        """String 1 power, computed — the device has no register for it."""
        return _product(self.pv_voltage_1, self.pv_current_1)

    @property
    def pv_power_2(self) -> float | None:
        """String 2 power, computed — the device has no register for it."""
        return _product(self.pv_voltage_2, self.pv_current_2)


def _product(voltage: float | None, current: float | None) -> float | None:
    if voltage is None or current is None:
        return None
    return voltage * current
