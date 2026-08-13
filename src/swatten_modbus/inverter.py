"""The top-level Swatten device object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection import (
    IllegalDataAddressError,
    IllegalFunctionError,
    ModbusConnectionError,
    ModbusError,
)

from .battery import Battery
from .clock import Clock
from .component import SwattenComponent, UpdateReport
from .energy import Energy
from .grid import Grid, GridSinglePhase, GridThreePhase, PowerFactor
from .identity import Identity
from .models import Phases, phases_for
from .solar import Solar

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

# Every component attribute a poll may refresh, in address order. identity is
# absent: it is read once in setup and never polled again.
_POLLED = (
    "clock",
    "solar",
    "phases_component",
    "grid",
    "power_factor",
    "battery",
    "energy",
)


class SwattenInverter:
    """A Swatten SiH-series hybrid inverter reached through a ``ModbusUnit``.

    The device sets itself up once — reading the model type and settling which
    sub-systems it serves — then polls each of them independently::

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
        self._polled: list[str] | None = None

    @property
    def model_type(self) -> str | None:
        """The model-type string the device reports, e.g. ``SiH8KTH``."""
        return self.identity.model_type

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
        self.power_factor = await self._async_probe_power_factor()
        self._polled = [name for name in _POLLED if getattr(self, name) is not None]

    async def async_update(self) -> UpdateReport:
        """Refresh every sub-system this inverter serves, one at a time.

        Components are read independently, the way the integration reads its
        blocks: a sub-system whose read fails keeps its previous values while
        the rest still refresh. Listeners fire only after every component has
        been tried, and only on the ones that refreshed. A failure of the link
        itself raises ``ModbusConnectionError`` instead of reporting.
        """
        if self._polled is None:
            await self.async_setup()
        assert self._polled is not None  # async_setup() builds it
        updated: set[str] = set()
        failed: dict[str, ModbusError] = {}
        for name in self._polled:
            component: SwattenComponent = getattr(self, name)
            try:
                await component.async_update(notify=False)
            except ModbusConnectionError:
                raise
            except ModbusError as err:
                failed[name] = err
            else:
                updated.add(name)
        for name in updated:
            fresh: SwattenComponent = getattr(self, name)
            fresh.notify()
        return UpdateReport(updated, failed)

    async def _async_probe_power_factor(self) -> PowerFactor | None:
        """Read holding 4085 once; ``None`` if the device does not serve it.

        It is the odd one out on this device (see :class:`PowerFactor`), so a
        unit that refuses it should cost that value rather than every poll.
        Only a refusal means absent — anything else is this time, not for good,
        and leaves the component in the poll to report on its own.
        """
        power_factor = PowerFactor(self._unit)
        try:
            await power_factor.async_update()
        except (IllegalDataAddressError, IllegalFunctionError):
            return None
        except ModbusError:
            pass
        return power_factor
