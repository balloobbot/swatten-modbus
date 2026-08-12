"""Fixtures: a Swatten SiH inverter over modbus-connection's in-memory mock.

The mock backend (and its ``mock_modbus_unit`` fixture) ship with
``modbus-connection`` as an auto-registered pytest plugin, so there is no real
server or socket here — just address-keyed stores loaded with Swatten-shaped
register values.

Almost every register on this device is an input register (FC04); holding 4085
(power factor) is the one exception.
"""

from __future__ import annotations

import pytest
from modbus_connection.mock import MockModbusUnit

from swatten_modbus import SwattenInverter


def ascii_words(text: str, length: int) -> list[int]:
    """Pack ASCII into ``length`` null-padded registers, two chars per register."""
    padded = text.ljust(length * 2, "\0")
    return [(ord(padded[i]) << 8) | ord(padded[i + 1]) for i in range(0, length * 2, 2)]


def u16(value: int) -> int:
    """Two's-complement 16-bit word for a signed value."""
    return value & 0xFFFF


def u32(value: int) -> list[int]:
    """A 32-bit value as two big-word-order registers."""
    return [value >> 16, value & 0xFFFF]


# Raw input-register words keyed by address; decoded view inline.
INPUT: dict[int, int | list[int]] = {
    # -- real-time clock: year, month, day, hour, minute, second --
    4050: [26, 8, 12, 14, 35, 7],  # 2026-08-12 14:35:07
    # -- apparent power (GEN2 only, not polled by SwattenInverter) --
    4059: u32(1234),  # 1234 VA
    # -- PV strings --
    4061: 3521,  # pv_voltage_1 -> 352.1 V
    4062: 83,  # pv_current_1 -> 8.3 A
    4063: 2984,  # pv_voltage_2 -> 298.4 V
    4064: 61,  # pv_current_2 -> 6.1 A
    4067: u32(4750),  # pv_power_total -> 4750 W
    # -- grid phases (L1 doubles as the single-phase voltage/current) --
    4069: 2301,  # -> 230.1 V
    4070: 2312,  # -> 231.2 V
    4071: 2295,  # -> 229.5 V
    4072: 76,  # -> 7.6 A
    4073: 81,  # -> 8.1 A
    4074: 69,  # -> 6.9 A
    # -- grid output --
    4081: u32(5210),  # total_output_power -> 5210 W
    4083: u32(120),  # reactive_power -> 120 var
    4198: 5001,  # grid_frequency -> 50.01 Hz
    5401: u16(-1500),  # measured_power -> -1500 W (importing)
    # -- identity --
    5809: ascii_words("SiH8KTH", 8),  # three-phase 8 kW
    # -- energy --
    10002: [123, 4567],  # today_pv_generation -> 12.3 kWh; also the total's words
    10008: 456,  # total_consumption -> 45.6 kWh
    10036: 55,  # today_import_energy -> 5.5 kWh
    10037: u32(12345),  # total_import_energy -> 1234.5 kWh
    10045: 78,  # today_export_energy -> 7.8 kWh
    10046: u32(54321),  # total_export_energy -> 5432.1 kWh
    # -- battery --
    10020: 512,  # battery_voltage -> 0.0 V (upstream scale is 0.0)
    10021: 105,  # battery_current -> 10.5 A
    10022: u16(-800),  # battery_power -> -800 W (charging)
    10023: 87,  # battery_soc -> 87 %
    10024: 99,  # battery_soh -> 99 %
}

HOLDING: dict[int, int | list[int]] = {
    4085: u16(-950),  # power_factor -> -950
}


@pytest.fixture
def seeded_unit(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    """A mock unit preloaded with a three-phase SiH8KTH's registers."""
    mock_modbus_unit.input.update(INPUT)
    mock_modbus_unit.holding.update(HOLDING)
    return mock_modbus_unit


@pytest.fixture
def inverter(seeded_unit: MockModbusUnit) -> SwattenInverter:
    """A three-phase inverter over the seeded unit."""
    return SwattenInverter(seeded_unit)
