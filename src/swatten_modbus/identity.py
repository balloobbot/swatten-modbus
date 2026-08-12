"""The device's model-type string."""

from __future__ import annotations

from modbus_connection.model import Component, string


class Identity(Component):
    """The model type, read once at setup and never polled.

    The upstream integration reads the same eight input registers both as the
    "Model Type" sensor and as the serial number it derives the inverter type
    from; this library keeps the one field and does both jobs with it.
    """

    register_space = "input"

    model_type = string(5809, 8)
    """Model type, e.g. ``SiH8KTH`` — up to 16 ASCII characters."""
