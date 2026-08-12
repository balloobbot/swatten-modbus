"""The block reads a poll issues: pinned, and checked for correctness.

No ``register_ranges`` are declared anywhere in this library: the upstream
plugin has no device block map, only a generic "chunk entities into blocks of
at most 100 registers" rule, so the read plan is derived from the fields alone.
Each block therefore covers a run of fields and the small gaps between them.
"""

from __future__ import annotations

from modbus_connection import IllegalDataAddressError
from modbus_connection.mock import MockModbusUnit
from modbus_connection.model import Component

from swatten_modbus import SwattenInverter

from .conftest import ascii_words

MODBUS_MAX_READ = 125  # a single request can never ask for more

SETUP_READS = [
    ("input", 5809, 8),  # model type
    ("holding", 4085, 1),  # power factor probe
]

POLL_READS_THREE_PHASE = [
    ("input", 4050, 6),  # clock
    ("input", 4061, 14),  # PV strings + the three grid phases
    ("input", 4081, 4),  # output and reactive power
    ("input", 4198, 1),  # grid frequency
    ("input", 5401, 1),  # measured power
    ("input", 10002, 7),  # PV generation + consumption
    ("input", 10020, 5),  # battery
    ("input", 10036, 12),  # import and export energy
    ("holding", 4085, 1),  # power factor
]

POLL_READS_SINGLE_PHASE = [
    *POLL_READS_THREE_PHASE[:1],
    ("input", 4061, 12),  # PV strings + one grid voltage and current
    *POLL_READS_THREE_PHASE[2:],
]


def blocks(unit: MockModbusUnit, since: int = 0) -> list[tuple[str, int, int]]:
    return [(e.register_type, e.address, e.count) for e in unit.read_events[since:]]


def covers(read_blocks: list[tuple[str, int, int]], component: Component) -> None:
    """Every register of every field of the component is inside some block."""
    for name, resolved in component.resolved_fields.items():
        for address in range(resolved.address, resolved.address + resolved.count):
            assert any(
                space == resolved.space and start <= address < start + count
                for space, start, count in read_blocks
            ), f"{type(component).__name__}.{name} at {address} is never read"


async def test_setup_reads(
    inverter: SwattenInverter, seeded_unit: MockModbusUnit
) -> None:
    await inverter.async_setup()

    assert blocks(seeded_unit) == SETUP_READS


async def test_three_phase_poll(
    inverter: SwattenInverter, seeded_unit: MockModbusUnit
) -> None:
    await inverter.async_setup()
    seen = len(seeded_unit.read_events)

    await inverter.async_update()

    poll = blocks(seeded_unit, seen)
    assert poll == POLL_READS_THREE_PHASE
    for component in inverter.polled_components:
        covers(poll, component)
    assert all(count <= MODBUS_MAX_READ for _, _, count in poll)


async def test_single_phase_poll(seeded_unit: MockModbusUnit) -> None:
    seeded_unit.input[5809] = ascii_words("SiH5KSH", 8)
    inverter = SwattenInverter(seeded_unit)
    await inverter.async_setup()
    seen = len(seeded_unit.read_events)

    await inverter.async_update()

    poll = blocks(seeded_unit, seen)
    assert poll == POLL_READS_SINGLE_PHASE
    for component in inverter.polled_components:
        covers(poll, component)
    # A single-phase model stops at the L1 registers: 4073 and 4074 are the
    # three-phase L2/L3 currents and are never asked for.
    assert not any(start <= 4073 < start + count for _, start, count in poll), (
        "single-phase poll must not reach the L2/L3 current registers"
    )


async def test_poll_plan_is_stable(
    inverter: SwattenInverter, seeded_unit: MockModbusUnit
) -> None:
    """The plan is cached, so a second poll issues exactly the same blocks."""
    await inverter.async_update()
    seen = len(seeded_unit.read_events)

    await inverter.async_update()

    assert blocks(seeded_unit, seen) == POLL_READS_THREE_PHASE


async def test_power_factor_is_optional(seeded_unit: MockModbusUnit) -> None:
    """A device refusing holding 4085 loses that value, not the whole poll."""
    seeded_unit.fail_read(4085, IllegalDataAddressError(), register_type="holding")
    inverter = SwattenInverter(seeded_unit)

    await inverter.async_setup()
    seen = len(seeded_unit.read_events)
    await inverter.async_update()

    assert inverter.power_factor is None
    poll = blocks(seeded_unit, seen)
    assert all(space == "input" for space, _, _ in poll)
    assert inverter.battery.battery_soc == 87  # the rest of the poll is unaffected
