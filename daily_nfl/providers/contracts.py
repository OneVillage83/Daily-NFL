"""Provider-neutral acquisition contracts for Daily NFL.

Providers return exact raw payloads and provenance first. Provider-shaped data
must not flow directly into features or football state calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Generic, Protocol, TypeVar, runtime_checkable

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod


class DatasetKind(StrEnum):
    """NFL source-data families understood by the acquisition layer."""

    SCHEDULE = "SCHEDULE"
    PLAY_BY_PLAY = "PLAY_BY_PLAY"
    ROSTER = "ROSTER"
    PARTICIPATION = "PARTICIPATION"
    PLAYER_STATS = "PLAYER_STATS"
    TEAM_STATS = "TEAM_STATS"
    INJURY = "INJURY"
    DEPTH_CHART = "DEPTH_CHART"
    TRANSACTION = "TRANSACTION"
    DRAFT = "DRAFT"
    OTHER = "OTHER"


class PointInTimeFidelity(StrEnum):
    """How defensibly a provider can support historical as-of reconstruction."""

    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    CURRENT_STATE_ONLY = "CURRENT_STATE_ONLY"
    UNKNOWN = "UNKNOWN"


class CostClass(StrEnum):
    FREE = "FREE"
    PAID = "PAID"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    dataset: DatasetKind
    point_in_time_fidelity: PointInTimeFidelity
    cadence: str
    license_class: str
    cost_class: CostClass = CostClass.UNKNOWN
    earliest_season: int | None = None
    latest_season: int | None = None
    reliability_note: str | None = None

    def __post_init__(self) -> None:
        if not self.cadence.strip():
            raise ValueError("cadence cannot be blank")
        if not self.license_class.strip():
            raise ValueError("license_class cannot be blank")
        if self.earliest_season is not None and self.earliest_season < 1920:
            raise ValueError("earliest_season is outside supported professional-football history")
        if self.latest_season is not None and self.latest_season < 1920:
            raise ValueError("latest_season is outside supported professional-football history")
        if (
            self.earliest_season is not None
            and self.latest_season is not None
            and self.latest_season < self.earliest_season
        ):
            raise ValueError("latest_season cannot precede earliest_season")


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    provider_id: str
    name: str
    provider_type: str
    parser_version: str
    provider_schema_version: str | None = None
    capabilities: tuple[ProviderCapability, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.provider_id, "provider_id"),
            (self.name, "name"),
            (self.provider_type, "provider_type"),
            (self.parser_version, "parser_version"),
        ):
            if not value.strip():
                raise ValueError(f"{label} cannot be blank")
        datasets = [capability.dataset for capability in self.capabilities]
        if len(datasets) != len(set(datasets)):
            raise ValueError("provider capabilities cannot repeat a dataset")

    def capability_for(self, dataset: DatasetKind) -> ProviderCapability | None:
        return next(
            (capability for capability in self.capabilities if capability.dataset is dataset),
            None,
        )


@dataclass(frozen=True, slots=True)
class AcquisitionRequest:
    dataset: DatasetKind
    seasons: tuple[int, ...] = ()
    parameters: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if any(season < 1920 for season in self.seasons):
            raise ValueError("requested seasons must be 1920 or later")
        if len(self.seasons) != len(set(self.seasons)):
            raise ValueError("requested seasons cannot contain duplicates")
        keys = [key for key, _ in self.parameters]
        if len(keys) != len(set(keys)):
            raise ValueError("acquisition parameter keys must be unique")
        if any(not key.strip() for key in keys):
            raise ValueError("acquisition parameter keys cannot be blank")


@dataclass(frozen=True, slots=True)
class ProviderPayload:
    """One exact raw provider asset plus source/provenance clocks."""

    content: bytes = field(repr=False)
    content_type: str
    source_uri: str | None
    observed_at: datetime
    available_at: datetime
    availability_method: AvailabilityMethod
    availability_confidence: AvailabilityConfidence
    effective_at: datetime | None = None
    published_at: datetime | None = None
    provider_schema_version: str | None = None

    def __post_init__(self) -> None:
        if not self.content:
            raise ValueError("provider payload cannot be empty")
        if not self.content_type.strip():
            raise ValueError("content_type cannot be blank")
        for value, label in (
            (self.observed_at, "observed_at"),
            (self.available_at, "available_at"),
            (self.effective_at, "effective_at"),
            (self.published_at, "published_at"),
        ):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{label} must be timezone-aware")
        if self.available_at > self.observed_at:
            raise ValueError("available_at cannot be later than our observed_at")


@runtime_checkable
class ProviderAdapter(Protocol):
    """Boundary implemented by every external NFL data provider."""

    @property
    def descriptor(self) -> ProviderDescriptor: ...

    def acquire(self, request: AcquisitionRequest) -> tuple[ProviderPayload, ...]: ...


NormalizedT = TypeVar("NormalizedT")


@dataclass(frozen=True, slots=True)
class NormalizedAcquisition(Generic[NormalizedT]):
    """Typed normalized records linked back to every contributing raw asset."""

    provider_id: str
    dataset: DatasetKind
    parser_version: str
    provider_schema_version: str | None
    evidence_ids: tuple[str, ...]
    records: tuple[NormalizedT, ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.provider_id, "provider_id"),
            (self.parser_version, "parser_version"),
        ):
            if not value.strip():
                raise ValueError(f"{label} cannot be blank")
        if not self.evidence_ids:
            raise ValueError("normalized acquisition requires at least one evidence_id")
        if any(not evidence_id.strip() for evidence_id in self.evidence_ids):
            raise ValueError("evidence_ids cannot contain blanks")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("evidence_ids cannot contain duplicates")
