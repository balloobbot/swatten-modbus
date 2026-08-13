"""Daily and lifetime energy counters."""

from __future__ import annotations

from modbus_connection.model import gauge, uint32

from .component import SwattenComponent


class Energy(SwattenComponent):
    """PV generation, house consumption, and grid import/export energy."""

    register_space = "input"

    today_pv_generation = gauge(10002, 0.1, signed=False, unit="kWh")

    total_pv_generation = uint32(10002, scale=0.1, unit="kWh")
    """Overlaps ``today_pv_generation``: upstream declares both at 10002.

    Every other today/total pair here puts the 32-bit total in the register
    after the daily counter (10036/10037, 10045/10046), so 10002 looks like a
    typo for 10003 — but it is what upstream reads, and is kept as declared.
    """

    total_consumption = gauge(10008, 0.1, signed=False, unit="kWh")
    today_import_energy = gauge(10036, 0.1, signed=False, unit="kWh")
    total_import_energy = uint32(10037, scale=0.1, unit="kWh")
    today_export_energy = gauge(10045, 0.1, signed=False, unit="kWh")
    total_export_energy = uint32(10046, scale=0.1, unit="kWh")
