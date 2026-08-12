"""Decoding: every field, against the synthetic register set in conftest."""

from __future__ import annotations

from datetime import datetime

import pytest
from modbus_connection.mock import MockModbusUnit

from swatten_modbus import (
    Gen2Grid,
    GridSinglePhase,
    GridThreePhase,
    Phases,
    SwattenInverter,
    UnsupportedModelError,
)

from .conftest import ascii_words


async def test_identity_and_variant(inverter: SwattenInverter) -> None:
    await inverter.async_update()

    assert inverter.model_type == "SiH8KTH"
    assert inverter.phases is Phases.THREE


async def test_clock(inverter: SwattenInverter) -> None:
    await inverter.async_update()

    assert inverter.clock.time == datetime(2026, 8, 12, 14, 35, 7)


async def test_clock_rejects_an_impossible_date(
    inverter: SwattenInverter, seeded_unit: MockModbusUnit
) -> None:
    seeded_unit.input[4051] = 13  # month 13
    await inverter.async_update()

    assert inverter.clock.time is None


async def test_solar(inverter: SwattenInverter) -> None:
    await inverter.async_update()

    solar = inverter.solar
    assert solar.pv_voltage_1 == pytest.approx(352.1)
    assert solar.pv_current_1 == pytest.approx(8.3)
    assert solar.pv_voltage_2 == pytest.approx(298.4)
    assert solar.pv_current_2 == pytest.approx(6.1)
    assert solar.pv_power_total == 4750
    # Computed in the integration, not registers on the device.
    assert solar.pv_power_1 == pytest.approx(352.1 * 8.3)
    assert solar.pv_power_2 == pytest.approx(298.4 * 6.1)


async def test_computed_pv_power_is_none_before_a_read(
    seeded_unit: MockModbusUnit,
) -> None:
    inverter = SwattenInverter(seeded_unit)

    assert inverter.solar.pv_power_1 is None


async def test_grid(inverter: SwattenInverter) -> None:
    await inverter.async_update()

    grid = inverter.grid
    assert grid.total_output_power == 5210
    assert grid.reactive_power == 120
    assert grid.grid_frequency == pytest.approx(50.01)
    assert grid.measured_power == -1500  # signed: importing


async def test_three_phase_grid(inverter: SwattenInverter) -> None:
    await inverter.async_update()

    phases = inverter.phases_component
    assert isinstance(phases, GridThreePhase)
    assert phases.grid_voltage_l1 == pytest.approx(230.1)
    assert phases.grid_voltage_l2 == pytest.approx(231.2)
    assert phases.grid_voltage_l3 == pytest.approx(229.5)
    assert phases.grid_current_l1 == pytest.approx(7.6)
    assert phases.grid_current_l2 == pytest.approx(8.1)
    assert phases.grid_current_l3 == pytest.approx(6.9)


async def test_single_phase_grid(seeded_unit: MockModbusUnit) -> None:
    seeded_unit.input[5809] = ascii_words("SiH5KSH", 8)
    inverter = SwattenInverter(seeded_unit)

    await inverter.async_update()

    assert inverter.phases is Phases.SINGLE
    phases = inverter.phases_component
    assert isinstance(phases, GridSinglePhase)
    # The same two registers the three-phase model calls L1.
    assert phases.inverter_voltage == pytest.approx(230.1)
    assert phases.grid_current == pytest.approx(7.6)


async def test_power_factor(inverter: SwattenInverter) -> None:
    await inverter.async_update()

    assert inverter.power_factor is not None
    assert inverter.power_factor.power_factor == -950


async def test_battery(inverter: SwattenInverter) -> None:
    await inverter.async_update()

    battery = inverter.battery
    assert battery.battery_current == pytest.approx(10.5)
    assert battery.battery_power == -800  # signed: charging
    assert battery.battery_soc == 87
    assert battery.battery_soh == 99


async def test_battery_voltage_is_always_zero(inverter: SwattenInverter) -> None:
    """Upstream declares register 10020 with scale 0.0; carried over as declared."""
    await inverter.async_update()

    assert inverter.battery.battery_voltage == 0.0


async def test_energy(inverter: SwattenInverter) -> None:
    await inverter.async_update()

    energy = inverter.energy
    assert energy.total_consumption == pytest.approx(45.6)
    assert energy.today_import_energy == pytest.approx(5.5)
    assert energy.total_import_energy == pytest.approx(1234.5)
    assert energy.today_export_energy == pytest.approx(7.8)
    assert energy.total_export_energy == pytest.approx(5432.1)


async def test_pv_generation_totals_overlap(inverter: SwattenInverter) -> None:
    """Upstream declares both PV generation counters at register 10002."""
    await inverter.async_update()

    energy = inverter.energy
    assert energy.today_pv_generation == pytest.approx(12.3)  # word 10002 alone
    # The same word 10002 as the high half of a 32-bit value with 10003.
    assert energy.total_pv_generation == pytest.approx((123 << 16 | 4567) * 0.1)


async def test_gen2_apparent_power(seeded_unit: MockModbusUnit) -> None:
    """The GEN2-only register, reachable by constructing the component directly."""
    gen2 = Gen2Grid(seeded_unit)

    await gen2.async_update()

    assert gen2.apparent_power == 1234


@pytest.mark.parametrize(
    ("model", "phases"),
    [
        ("SiH3KSH", Phases.SINGLE),
        ("SiH4KSH", Phases.SINGLE),
        ("SiH5KSH", Phases.SINGLE),
        ("SiH6KSH", Phases.SINGLE),
        ("SiH5KTH", Phases.THREE),
        ("SiH6KTH", Phases.THREE),
        ("SiH8KTH", Phases.THREE),
        ("SiH10KTH", Phases.THREE),
    ],
)
async def test_every_known_model(
    seeded_unit: MockModbusUnit, model: str, phases: Phases
) -> None:
    seeded_unit.input[5809] = ascii_words(model, 8)
    inverter = SwattenInverter(seeded_unit)

    await inverter.async_update()

    assert inverter.phases is phases


async def test_unknown_model_is_rejected(seeded_unit: MockModbusUnit) -> None:
    seeded_unit.input[5809] = ascii_words("X1-Hybrid-G4", 8)
    inverter = SwattenInverter(seeded_unit)

    with pytest.raises(UnsupportedModelError):
        await inverter.async_update()
