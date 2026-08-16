#!/usr/bin/env python3

"""Query a Swatten SiH-series inverter and print every value.

Reads one inverter once and dumps it to the terminal — the quickest way to check
real hardware with no application around it.

::

    uv run script/query.py /dev/ttyUSB0 --transport serial --unit 1
    uv run script/query.py 192.168.1.50 --unit 1
"""

from __future__ import annotations

import argparse
import asyncio

from modbus_connection import ModbusError
from modbus_connection.cli_helper import (
    CountingUnit,
    add_connection_args,
    connect_from_args,
    print_component,
)

from swatten_modbus import SwattenInverter, UnsupportedModelError

# The inverter is RS-485 RTU; over TCP it is reached through a gateway, which
# presents it either as native Modbus TCP (socket) or transparently (rtu).
# ASCII framing is not supported. tcp leads: it is the default transport.
CONNECTIONS = (("tcp", "socket"), ("tcp", "rtu"), ("serial", "rtu"))


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_connection_args(parser, connections=CONNECTIONS)
    parser.add_argument("--unit", type=int, default=1, help="Modbus unit id")
    args = parser.parse_args()

    try:
        connection = await connect_from_args(args)
    except ModbusError as err:
        print(f"Could not connect: {err}")
        return 1

    counting = CountingUnit(connection.for_unit(args.unit))
    inverter = SwattenInverter(counting)
    try:
        report = await inverter.async_update()
    except UnsupportedModelError as err:
        print(f"Unsupported model: {err}")
        return 1
    except ModbusError as err:
        print(f"Could not read the inverter: {err}")
        return 1
    finally:
        await connection.close()

    # A failed sub-system still prints, holding its previous values — say so,
    # or its empty values read as the inverter's answer.
    for name, error in report.failed.items():
        print(f"{name} was not read: {error}")

    print_component(inverter.identity, title="Identity")
    # phases_component and power_factor are settled at setup: the phase block
    # this model has, and the power factor only if the unit serves it.
    for title, component in (
        ("Clock", inverter.clock),
        ("Solar", inverter.solar),
        ("Phases", inverter.phases_component),
        ("Grid", inverter.grid),
        ("Power factor", inverter.power_factor),
        ("Battery", inverter.battery),
        ("Energy", inverter.energy),
    ):
        if component is not None:
            print_component(component, title=title)
    print(f"\n{counting.reads} Modbus reads")
    return 0


raise SystemExit(asyncio.run(main()))
