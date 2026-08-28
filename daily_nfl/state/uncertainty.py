"""Structured uncertainty primitives shared by all M7 state engines."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


def _require_finite(value: float, label: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")


def _require_name(value: str, label: str = "name") -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be blank")


@dataclass(frozen=True, slots=True)
class Probability:
    """Validated probability mass in the closed interval [0, 1]."""

    value: float

    def __post_init__(self) -> None:
        _require_finite(self.value, "probability")
        if not 0.0 <= self.value <= 1.0:
            raise ValueError("probability must be between 0 and 1 inclusive")


@dataclass(frozen=True, slots=True)
class NumericMoments:
    """First two moments for a numeric state quantity."""

    mean: float
    variance: float

    def __post_init__(self) -> None:
        _require_finite(self.mean, "mean")
        _require_finite(self.variance, "variance")
        if self.variance < 0.0:
            raise ValueError("variance cannot be negative")

    @property
    def standard_deviation(self) -> float:
        return math.sqrt(self.variance)


@dataclass(frozen=True, slots=True)
class BoundedInterval:
    """Finite ordered interval with optional probability/confidence mass."""

    lower: float
    upper: float
    mass: Probability | None = None

    def __post_init__(self) -> None:
        _require_finite(self.lower, "interval lower bound")
        _require_finite(self.upper, "interval upper bound")
        if self.upper < self.lower:
            raise ValueError("interval upper bound cannot be below lower bound")


@dataclass(frozen=True, slots=True)
class CategoryProbability:
    category: str
    probability: Probability

    def __post_init__(self) -> None:
        _require_name(self.category, "category")


@dataclass(frozen=True, slots=True)
class CategoricalDistribution:
    """Normalized probability distribution over named discrete outcomes."""

    entries: tuple[CategoryProbability, ...]

    def __post_init__(self) -> None:
        if not self.entries:
            raise ValueError("categorical distribution requires at least one entry")
        categories = [entry.category for entry in self.entries]
        if len(categories) != len(set(categories)):
            raise ValueError("categorical distribution categories must be unique")
        total = math.fsum(entry.probability.value for entry in self.entries)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("categorical probability mass must sum to 1")


class MissingnessReason(StrEnum):
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
    UNRESOLVED_IDENTITY = "UNRESOLVED_IDENTITY"
    UNSUPPORTED_ERA = "UNSUPPORTED_ERA"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class UnknownQuantity:
    name: str
    reason: MissingnessReason
    detail: str | None = None

    def __post_init__(self) -> None:
        _require_name(self.name)
        if self.detail is not None and not self.detail.strip():
            raise ValueError("unknown-quantity detail cannot be blank when present")


@dataclass(frozen=True, slots=True)
class NamedProbability:
    name: str
    estimate: Probability

    def __post_init__(self) -> None:
        _require_name(self.name)


@dataclass(frozen=True, slots=True)
class NamedMoments:
    name: str
    estimate: NumericMoments

    def __post_init__(self) -> None:
        _require_name(self.name)


@dataclass(frozen=True, slots=True)
class NamedInterval:
    name: str
    estimate: BoundedInterval

    def __post_init__(self) -> None:
        _require_name(self.name)


@dataclass(frozen=True, slots=True)
class NamedCategoricalDistribution:
    name: str
    estimate: CategoricalDistribution

    def __post_init__(self) -> None:
        _require_name(self.name)


def _require_unique_names(values: tuple[object, ...], label: str) -> None:
    names = [str(getattr(value, "name")) for value in values]
    if len(names) != len(set(names)):
        raise ValueError(f"{label} names must be unique")


@dataclass(frozen=True, slots=True)
class StateUncertainty:
    """Structured, immutable uncertainty bundle for a state snapshot."""

    probabilities: tuple[NamedProbability, ...] = ()
    moments: tuple[NamedMoments, ...] = ()
    intervals: tuple[NamedInterval, ...] = ()
    categorical: tuple[NamedCategoricalDistribution, ...] = ()
    unknowns: tuple[UnknownQuantity, ...] = ()

    def __post_init__(self) -> None:
        _require_unique_names(self.probabilities, "probability")
        _require_unique_names(self.moments, "moments")
        _require_unique_names(self.intervals, "interval")
        _require_unique_names(self.categorical, "categorical distribution")
        _require_unique_names(self.unknowns, "unknown quantity")

    @property
    def is_empty(self) -> bool:
        return not any(
            (
                self.probabilities,
                self.moments,
                self.intervals,
                self.categorical,
                self.unknowns,
            )
        )
