"""Which Swatten model a device is, derived from its model-type string."""

from __future__ import annotations

from enum import StrEnum


class Phases(StrEnum):
    """The grid connection a model is built for."""

    SINGLE = "single"
    THREE = "three"


class UnsupportedModelError(Exception):
    """The device reports a model string this library has no register map for."""


# Model-string prefix -> grid connection, from the upstream plugin's
# async_determineInverterType(). "SiH<n>KSH" are single-phase, "SiH<n>KTH"
# three-phase, but only these eight prefixes are recognised upstream and this
# library does not extrapolate beyond them.
MODEL_PREFIXES: tuple[tuple[str, Phases], ...] = (
    ("SiH3KSH", Phases.SINGLE),
    ("SiH4KSH", Phases.SINGLE),
    ("SiH5KSH", Phases.SINGLE),
    ("SiH6KSH", Phases.SINGLE),
    ("SiH5KTH", Phases.THREE),
    ("SiH6KTH", Phases.THREE),
    ("SiH8KTH", Phases.THREE),
    ("SiH10KTH", Phases.THREE),
)


def phases_for(model: str | None) -> Phases:
    """Map a model-type string to its grid connection.

    Raises :class:`UnsupportedModelError` for anything unrecognised — where the
    upstream integration logs an error and creates no entities at all.
    """
    if model:
        for prefix, phases in MODEL_PREFIXES:
            if model.startswith(prefix):
                return phases
    raise UnsupportedModelError(f"unrecognised Swatten model type: {model!r}")
