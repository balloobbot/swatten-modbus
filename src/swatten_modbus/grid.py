"""The grid side: phase voltages and currents, output power, frequency."""

from __future__ import annotations

from modbus_connection.model import gauge, integer, uint32

from .component import SwattenComponent


class Grid(SwattenComponent):
    """Grid quantities every SiH model reports, whatever its phase count."""

    register_space = "input"

    total_output_power = uint32(4081, unit="W")
    reactive_power = uint32(4083, unit="var")
    grid_frequency = gauge(4198, 0.01, signed=False, unit="Hz")
    measured_power = integer(5401, unit="W")
    """Power at the meter: negative is import, positive is export."""


class GridSinglePhase(SwattenComponent):
    """The single-phase (X1) grid connection: SiH3/4/5/6KSH."""

    register_space = "input"

    inverter_voltage = gauge(4069, 0.1, signed=False, unit="V")
    grid_current = gauge(4072, 0.1, signed=False, unit="A")


class GridThreePhase(SwattenComponent):
    """The three-phase (X3) grid connection: SiH5/6/8/10KTH.

    L1 shares its two registers with the single-phase model's grid voltage and
    current; L2 and L3 sit in the two registers after each.
    """

    register_space = "input"

    grid_voltage_l1 = gauge(4069, 0.1, signed=False, unit="V")
    grid_voltage_l2 = gauge(4070, 0.1, signed=False, unit="V")
    grid_voltage_l3 = gauge(4071, 0.1, signed=False, unit="V")
    grid_current_l1 = gauge(4072, 0.1, signed=False, unit="A")
    grid_current_l2 = gauge(4073, 0.1, signed=False, unit="A")
    grid_current_l3 = gauge(4074, 0.1, signed=False, unit="A")


class PowerFactor(SwattenComponent):
    """Power factor — the one register upstream reads from the holding space.

    Every other grid quantity is an input register; upstream leaves this one
    description's ``register_type`` at the dataclass default (holding), which
    looks like an oversight but is carried over as declared. It is read as an
    optional component so a device that does not serve holding 4085 costs this
    value rather than the whole poll.
    """

    register_space = "holding"

    power_factor = integer(4085)


class Gen2Grid(SwattenComponent):
    """Apparent power, which upstream declares for the GEN2 generation only.

    No model string the upstream plugin recognises resolves to GEN2, so this is
    unreachable there and is not part of :class:`~swatten_modbus.SwattenInverter`.
    It is kept as a component of its own so the register knowledge survives and
    a GEN2 device can be read by constructing it directly.
    """

    register_space = "input"

    apparent_power = uint32(4059, unit="VA")
