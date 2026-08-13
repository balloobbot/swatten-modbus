"""The component base every sub-system builds on."""

from __future__ import annotations

from modbus_connection.model import Component


class SwattenComponent(Component):
    """A Swatten sub-system."""

    max_span = 100  # the plugin's block_size
