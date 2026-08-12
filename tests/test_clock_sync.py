"""The one write this device map has: setting the real-time clock."""

from __future__ import annotations

from datetime import datetime

import pytest
from modbus_connection import IllegalDataAddressError
from modbus_connection.mock import MockModbusUnit, WriteEvent

from swatten_modbus import Clock, SwattenInverter


async def test_sync_writes_six_holding_registers(seeded_unit: MockModbusUnit) -> None:
    writes: list[WriteEvent] = []
    seeded_unit.on_write(writes.append)

    await Clock(seeded_unit).async_sync(datetime(2026, 8, 12, 14, 35, 7))

    assert len(writes) == 1
    write = writes[0]
    assert write.register_type == "holding"  # the clock is read from input, set here
    assert write.address == 4050
    assert write.values == [26, 8, 12, 14, 35, 7]  # year is two digits
    assert write.function_code == 0x10  # one atomic multi-register write


async def test_sync_defaults_to_now(seeded_unit: MockModbusUnit) -> None:
    await Clock(seeded_unit).async_sync()

    now = datetime.now()
    assert seeded_unit.holding[4050] == now.year % 100
    assert seeded_unit.holding[4051] == now.month
    assert seeded_unit.holding[4052] == now.day


async def test_sync_then_read_back(
    inverter: SwattenInverter, seeded_unit: MockModbusUnit
) -> None:
    """The device's own clock registers are the input-space copy of the write."""
    when = datetime(2027, 1, 2, 3, 4, 5)
    await inverter.async_update()

    await inverter.clock.async_sync(when)
    seeded_unit.input[4050] = [27, 1, 2, 3, 4, 5]  # the device applies it
    await inverter.async_update()

    assert inverter.clock.time == when


async def test_sync_propagates_a_refusal(seeded_unit: MockModbusUnit) -> None:
    seeded_unit.fail_write(4050, IllegalDataAddressError())

    with pytest.raises(IllegalDataAddressError):
        await Clock(seeded_unit).async_sync(datetime(2026, 8, 12, 14, 35, 7))
