"""One failing block must not take the rest of the poll with it.

The upstream integration reads its blocks independently and tolerates a failure
(``auto_block_ignore_readerror=True``): the failing block's sensors keep their
last values while everything else refreshes. The library mirrors that at
component granularity.
"""

from __future__ import annotations

import pytest
from modbus_connection import (
    IllegalFunctionError,
    ModbusConnectionError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusUnit

from swatten_modbus import SwattenInverter

from .conftest import u32

POLLED = {
    "clock",
    "solar",
    "phases_component",
    "grid",
    "power_factor",
    "battery",
    "energy",
}


async def test_a_failed_component_leaves_the_rest_fresh(
    inverter: SwattenInverter, seeded_unit: MockModbusUnit
) -> None:
    await inverter.async_update()
    before = inverter.grid.total_output_power

    seeded_unit.input[4081] = u32(6000)  # grid power changes on the device
    seeded_unit.input[10023] = 42  # so does the battery's state of charge
    seeded_unit.fail_read(
        4081, ModbusTimeoutError("slow grid block"), register_type="input"
    )
    report = await inverter.async_update()

    assert not report.complete
    assert set(report.failed) == {"grid"}
    assert isinstance(report.failed["grid"], ModbusTimeoutError)
    assert report.updated == POLLED - {"grid"}
    assert inverter.grid.total_output_power == before
    assert inverter.battery.battery_soc == 42


async def test_a_failed_component_fails_as_one_across_all_its_blocks(
    inverter: SwattenInverter, seeded_unit: MockModbusUnit
) -> None:
    """Containment is per component, which for Grid is coarser than upstream.

    Its four fields sit in three far-apart blocks (4081, 4198, 5401) that the
    integration would tolerate one at a time; here the first refusal ends the
    component, and the later blocks are not even asked for.
    """
    await inverter.async_update()
    before = inverter.grid.grid_frequency
    seen = len(seeded_unit.read_events)

    seeded_unit.input[4198] = 4999
    seeded_unit.fail_read(
        4081, ModbusTimeoutError("slow grid block"), register_type="input"
    )
    await inverter.async_update()

    assert not any(event.address == 4198 for event in seeded_unit.read_events[seen:])
    assert inverter.grid.grid_frequency == before


async def test_listeners_fire_at_the_end_and_only_for_fresh_components(
    inverter: SwattenInverter, seeded_unit: MockModbusUnit
) -> None:
    await inverter.async_update()
    seen: list[int] = []
    inverter.battery.add_update_listener(
        lambda: seen.append(len(seeded_unit.read_events))
    )
    inverter.grid.add_update_listener(lambda: seen.append(-1))

    seeded_unit.fail_read(
        4081, ModbusTimeoutError("slow grid block"), register_type="input"
    )
    seeded_unit.read_events.clear()
    await inverter.async_update()

    # One notification, after every component was tried; none for the failure.
    assert seen == [len(seeded_unit.read_events)]


async def test_a_dead_link_raises_instead_of_reporting(
    inverter: SwattenInverter, seeded_unit: MockModbusUnit
) -> None:
    await inverter.async_update()
    seeded_unit.fail_requests(ModbusConnectionError("link down"))
    with pytest.raises(ModbusConnectionError):
        await inverter.async_update()


async def test_every_component_refreshes_on_a_healthy_device(
    inverter: SwattenInverter,
) -> None:
    report = await inverter.async_update()

    assert report.complete
    assert report.failed == {}
    assert report.updated == POLLED


async def test_a_failed_setup_raises_and_retries(seeded_unit: MockModbusUnit) -> None:
    """The model type is the poll's foundation; without it nothing is partial."""
    seeded_unit.fail_read(
        5809, ModbusTimeoutError("no model type"), register_type="input"
    )
    inverter = SwattenInverter(seeded_unit)
    with pytest.raises(ModbusTimeoutError):
        await inverter.async_update()

    seeded_unit.fail_read(5809, None, register_type="input")
    report = await inverter.async_update()

    assert report.complete
    assert inverter.model_type == "SiH8KTH"


async def test_a_refused_power_factor_is_dropped(seeded_unit: MockModbusUnit) -> None:
    """A device may refuse holding 4085 by function code as well as by address."""
    seeded_unit.fail_read(4085, IllegalFunctionError(), register_type="holding")
    inverter = SwattenInverter(seeded_unit)

    report = await inverter.async_update()

    assert inverter.power_factor is None
    assert report.complete
    assert "power_factor" not in report.updated


async def test_a_transient_probe_failure_does_not_drop_power_factor(
    seeded_unit: MockModbusUnit,
) -> None:
    """A timed-out probe means "not this time", never "this device lacks it"."""
    seeded_unit.fail_read(4085, ModbusTimeoutError("busy"), register_type="holding")
    inverter = SwattenInverter(seeded_unit)

    report = await inverter.async_update()

    assert inverter.power_factor is not None
    assert set(report.failed) == {"power_factor"}

    seeded_unit.fail_read(4085, None, register_type="holding")
    report = await inverter.async_update()

    assert report.complete
    assert inverter.power_factor.power_factor == -950
