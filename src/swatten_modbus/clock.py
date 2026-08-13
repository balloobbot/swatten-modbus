"""The inverter's real-time clock."""

from __future__ import annotations

from datetime import datetime

from modbus_connection.model import integer

from .component import SwattenComponent

RTC_ADDRESS = 4050
"""Year, month, day, hour, minute, second — one register each, in that order."""


class Clock(SwattenComponent):
    """The real-time clock: read from input registers, set through holding.

    The clock reads back from the input space but is set by writing the same
    six addresses in the holding space, so :meth:`async_sync` writes through the
    unit rather than through a field.
    """

    register_space = "input"

    _year = integer(RTC_ADDRESS, signed=False)
    _month = integer(RTC_ADDRESS + 1, signed=False)
    _day = integer(RTC_ADDRESS + 2, signed=False)
    _hour = integer(RTC_ADDRESS + 3, signed=False)
    _minute = integer(RTC_ADDRESS + 4, signed=False)
    _second = integer(RTC_ADDRESS + 5, signed=False)

    @property
    def time(self) -> datetime | None:
        """The device clock, or ``None`` if it reports an invalid date."""
        parts = (
            self._year,
            self._month,
            self._day,
            self._hour,
            self._minute,
            self._second,
        )
        if any(part is None for part in parts):
            return None
        year, month, day, hour, minute, second = (int(part) for part in parts)  # type: ignore[arg-type]
        try:
            return datetime(2000 + year % 100, month, day, hour, minute, second)
        except ValueError:
            return None

    async def async_sync(self, when: datetime | None = None) -> None:
        """Set the clock, defaulting to now, in one six-register write (FC16)."""
        now = when if when is not None else datetime.now()
        await self.modbus_unit.write_registers(
            RTC_ADDRESS,
            [now.year % 100, now.month, now.day, now.hour, now.minute, now.second],
        )
