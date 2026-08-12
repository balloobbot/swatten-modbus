"""The top-level Swatten device object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection import IllegalDataAddressError
from modbus_connection.model import Component, ComponentGroup

from .battery import Battery
from .clock import Clock
from .energy import Energy
from .grid import Grid, GridSinglePhase, GridThreePhase, PowerFactor
from .identity import Identity
from .models import Phases, phases_for
from .solar import Solar

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit


class SwattenInverter:
    """A Swatten SiH-series hybrid inverter reached through a ``ModbusUnit``.

    The device sets itself up once — reading the model type and settling which
    sub-systems it serves — then polls everything else in one pooled group::

        inverter = SwattenInverter(unit)
        await inverter.async_update()
        inverter.solar.pv_voltage_1
        inverter.battery.battery_soc
        inverter.phases_component.grid_current_l1  # three-phase models

    :attr:`identity` is read in setup and not polled again. :attr:`phases` and
    :attr:`phases_component` follow the model type, so a single-phase model
    never reads the L2/L3 registers and a three-phase one never reads the
    single-phase aliases of L1.
    """

    def __init__(self, unit: ModbusUnit) -> None:
        self._unit = unit
        self.identity = Identity(unit)
        self.clock = Clock(unit)
        self.solar = Solar(unit)
        self.grid = Grid(unit)
        self.battery = Battery(unit)
        self.energy = Energy(unit)
        # All settled by async_setup(), which needs the model type off the device.
        self.phases: Phases | None = None
        self.phases_component: GridSinglePhase | GridThreePhase | None = None
        self.power_factor: PowerFactor | None = None
        self._group: ComponentGroup | None = None

    @property
    def model_type(self) -> str | None:
        """The model-type string the device reports, e.g. ``SiH8KTH``."""
        return self.identity.model_type

    @property
    def polled_components(self) -> tuple[Component, ...]:
        """The sub-systems a poll refreshes."""
        return tuple(
            component
            for component in (
                self.clock,
                self.solar,
                self.grid,
                self.phases_component,
                self.power_factor,
                self.battery,
                self.energy,
            )
            if component is not None
        )

    async def async_setup(self) -> None:
        """Read the model type and settle what to poll.

        Run by the first :meth:`async_update` if the caller does not run it
        itself. Raises
        :class:`~swatten_modbus.models.UnsupportedModelError` for a model this
        library has no map for; a failure leaves the device unset up, so the
        next :meth:`async_update` tries again.
        """
        await self.identity.async_update()
        self.phases = phases_for(self.identity.model_type)
        self.phases_component = (
            GridSinglePhase(self._unit)
            if self.phases is Phases.SINGLE
            else GridThreePhase(self._unit)
        )
        # Holding 4085 is the odd one out on this device (see PowerFactor); a
        # unit that refuses it should cost that value, not every poll.
        self.power_factor = await _optional(PowerFactor(self._unit))
        self._group = ComponentGroup(self._unit, self.polled_components)

    async def async_update(self) -> None:
        """Refresh every polled sub-system in as few Modbus calls as possible."""
        if self._group is None:
            await self.async_setup()
        assert self._group is not None  # async_setup() always builds it
        await self._group.async_update()


async def _optional[C: Component](component: C) -> C | None:
    """Read a component the device may not serve; ``None`` if it refuses."""
    try:
        await component.async_update()
    except IllegalDataAddressError:
        return None
    return component
