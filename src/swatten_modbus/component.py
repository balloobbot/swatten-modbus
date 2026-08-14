"""The component base every sub-system builds on, and what a poll reports."""

from __future__ import annotations

from dataclasses import dataclass

from modbus_connection import ModbusError
from modbus_connection.model import Component


class SwattenComponent(Component):
    """A Swatten sub-system."""

    max_span = 100  # the plugin's block_size


@dataclass(frozen=True)
class UpdateReport:
    """What one poll refreshed, by the device's component attribute names.

    A failed component kept its previous values and did not notify; the error
    that failed it rides along. A dead link is never in here — the update
    raises ``ModbusConnectionError`` instead of reporting partial silence, and
    nor is a timeout that hit before anything at all had answered.
    """

    updated: set[str]
    failed: dict[str, ModbusError]

    @property
    def complete(self) -> bool:
        """Whether every polled component refreshed."""
        return not self.failed
