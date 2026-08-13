"""swatten-modbus — read a Swatten SiH-series hybrid inverter over Modbus.

Construct ``SwattenInverter(unit)`` with a ``modbus_connection.ModbusUnit``,
call ``await inverter.async_update()``, then read its sub-systems as normal
Python objects::

    inverter.solar.pv_voltage_1
    inverter.grid.total_output_power
    inverter.battery.battery_soc
    inverter.energy.today_pv_generation
    inverter.clock.time

The register map is extracted from the ``plugin_swatten.py`` plugin of the
`homeassistant-solax-modbus <https://github.com/wills106/homeassistant-solax-modbus>`_
integration (Apache-2.0). Field names are that plugin's entity keys, so every
attribute here traces back to one entity description there.

Almost everything lives in the input space (FC04); the two exceptions are the
power factor (holding 4085) and the real-time clock, which reads from input but
is set through holding.
"""

from .battery import Battery
from .clock import Clock
from .component import SwattenComponent
from .energy import Energy
from .grid import Gen2Grid, Grid, GridSinglePhase, GridThreePhase, PowerFactor
from .identity import Identity
from .inverter import SwattenInverter
from .models import MODEL_PREFIXES, Phases, UnsupportedModelError, phases_for
from .solar import Solar

__all__ = [
    "MODEL_PREFIXES",
    "Battery",
    "Clock",
    "Energy",
    "Gen2Grid",
    "Grid",
    "GridSinglePhase",
    "GridThreePhase",
    "Identity",
    "Phases",
    "PowerFactor",
    "Solar",
    "SwattenComponent",
    "SwattenInverter",
    "UnsupportedModelError",
    "phases_for",
]
