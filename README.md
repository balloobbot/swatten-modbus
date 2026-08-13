# swatten-modbus

Read a **Swatten** (Sieyuan Watten Technology) SiH-series hybrid solar inverter over
Modbus, as typed Python objects.

The library is a device model only: you own the connection and hand it a
`ModbusUnit`, and it reads and writes registers. It is built on
[modbus-connection](https://github.com/home-assistant-libs/modbus-connection), so it
runs over any backend that library supports — or its in-memory mock, in tests.

## Supported models

Two variants, told apart by the model-type string the inverter reports in input
registers 5809–5816:

| Grid connection | Models |
| --- | --- |
| Single phase | `SiH3KSH`, `SiH4KSH`, `SiH5KSH`, `SiH6KSH` |
| Three phase | `SiH5KTH`, `SiH6KTH`, `SiH8KTH`, `SiH10KTH` |

A single-phase model reports one grid voltage and current; a three-phase model
reports L1/L2/L3. `SwattenInverter` detects which at setup and reads only that
model's registers. An unrecognised model string raises `UnsupportedModelError`.

## Usage

```python
import asyncio

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from swatten_modbus import SwattenInverter


async def main() -> None:
    connection = ModbusConnection(ModbusTcpParams(host="192.168.1.50", port=502))
    try:
        inverter = SwattenInverter(connection.for_unit(1))
        await inverter.async_update()

        print("Model:", inverter.model_type)
        print("PV power:", inverter.solar.pv_power_total, "W")
        print("Battery:", inverter.battery.battery_soc, "%")
        print("Today's generation:", inverter.energy.today_pv_generation, "kWh")
        if inverter.phases_component is not None:
            print("Grid:", inverter.phases_component)
    finally:
        await connection.close()


asyncio.run(main())
```

A poll reads each sub-system independently, the way the integration reads its
blocks: one slow or refused block does not take the rest of the poll with it.
`async_update()` returns an `UpdateReport` — a failed sub-system keeps its
previous values, does not notify its listeners, and is listed by attribute name
with its error, while every other one refreshes and notifies once the whole
poll is done. Only a dead link (`ModbusConnectionError`) raises:

```python
report = await inverter.async_update()
for name, error in report.failed.items():
    print(f"{name} kept its previous values: {error}")
```

Sub-systems: `identity`, `clock`, `solar`, `grid`, `phases_component`,
`power_factor`, `battery`, `energy`. Each is a `Component` that can also be
refreshed on its own. `await inverter.clock.async_sync()` sets the device clock.

**ASCII-over-TCP is not supported, under any circumstance.** This library never
builds a connection — you hand it a `ModbusUnit`, so framing is entirely your
choice — but it offers no connect helper that could take or forward
`framer="ascii"`, and a unit built with ASCII framing over TCP is outside what
this register map was extracted for and is not supported. Use `framer="socket"`
(the modbus-connection default) or `framer="rtu"`.

## Where the register map comes from

The register map is based on the `plugin_swatten.py` plugin of
[homeassistant-solax-modbus](https://github.com/wills106/homeassistant-solax-modbus)
(Apache-2.0), and this library keeps that licence. Every field name is that
plugin's entity key, so each attribute traces back to one entity description
upstream.

Three quirks are carried over from upstream as declared rather than "fixed", and
are documented where they are declared:

- `Battery.battery_voltage` is declared with a scale of `0.0` upstream, so it
  always reads `0.0` V.
- `Energy.total_pv_generation` is a 32-bit value at register 10002, overlapping
  the 16-bit `today_pv_generation` at the same address.
- `PowerFactor.power_factor` is the only value read from the holding space; every
  other value on the device is an input register.

`Gen2Grid` holds an apparent-power register upstream declares for a `GEN2`
generation that no recognised model string resolves to. It is not part of
`SwattenInverter`; construct it directly if you have such a device.
