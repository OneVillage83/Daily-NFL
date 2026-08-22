"""Point-in-time reconstruction contracts for Daily NFL."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod, GameId


type PITFeatureScalar = str | int | float | bool | None


class PITHorizon(StrEnum):
    T_168H = "T-168h"
    T_72H = "T-72h"
    T_24H = "T-24h"
    T_6H = "T-6h"
    T_90M = "T-90m"
    T_15M = "T-15m"

    @property
    def offset(self) -> timedelta:
        return {
            PITHorizon.T_168H: timedelta(hours=168),
            PITHorizon.T_72H: timedelta(hours=72),
            PITHorizon.T_24H: timedelta(hours=24),
            PITHorizon.T_6H: timedelta(hours=6),
            PITHorizon.T_90M: timedelta(minutes=90),
            PITHorizon.T_15M: timedelta(minutes=15),
        }[self]


class PITInputKind(StrEnum):
    SCHEDULE = "SCHEDULE"
    INJURY = "INJURY"
    DEPTH_CHART = "DEPTH_CHART"
    WEATHER_FORECAST = "WEATHER_FORECAST"
    WEATHER_ACTUAL = "WEATHER_ACTUAL"
    MARKET_QUOTE = "MARKET_QUOTE"
    CURRENT_GAME_RESULT = "CURRENT_GAME_RESULT"
    CURRENT_GAME_STAT = "CURRENT_GAME_STAT"
    CURRENT_GAME_PLAY = "CURRENT_GAME_PLAY"
    FUTURE_GAME = "FUTURE_GAME"
    SEASON_FINAL_AGGREGATE = "SEASON_FINAL_AGGREGATE"
    PROVIDER_CORRECTION = "PROVIDER_CORRECTION"
    OTHER = "OTHER"


class PITLeakageCode(StrEnum):
    SOURCE_AFTER_CUTOFF = "SOURCE_AFTER_CUTOFF"
    INDEFENSIBLE_AVAILABILITY = "INDEFENSIBLE_AVAILABILITY"
    MISSING_REQUIRED_CONTEXT = "MISSING_REQUIRED_CONTEXT"
    CURRENT_GAME_OUTCOME = "CURRENT_GAME_OUTCOME"
    ACTUAL_WEATHER_FOR_CURRENT_GAME = "ACTUAL_WEATHER_FOR_CURRENT_GAME"
    LATER_MARKET_QUOTE = "LATER_MARKET_QUOTE"
    FUTURE_GAME_INFORMATION = "FUTURE_GAME_INFORMATION"
    END_OF_SEASON_INFORMATION = "END_OF_SEASON_INFORMATION"
    LATE_PROVIDER_CORRECTION = "LATE_PROVIDER_CORRECTION"


class PITValidationResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


def _require_aware(value: datetime | None, label: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{label} must be timezone-aware")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdefABCDEF" for character in value
    )


def _validate_optional_text(value: str | None, label: str) -> None:
    if value is not None and not value.strip():
        raise ValueError(f"{label} cannot be blank when present")


@dataclass(frozen=True, slots=True)
class PredictionCutoff:
    game_id: GameId
    kickoff: datetime
    prediction_time: datetime
    horizon: PITHorizon | None = None

    def __post_init__(self) -> None:
        _require_aware(self.kickoff, "kickoff")
        _require_aware(self.prediction_time, "prediction_time")
        if self.prediction_time >= self.kickoff:
            raise ValueError("prediction_time must be before official kickoff")
        if self.horizon is not None:
            expected = self.kickoff - self.horizon.offset
            if self.prediction_time != expected:
                raise ValueError("prediction_time does not match the configured horizon")

    @classmethod
    def from_horizon(
        cls,
        *,
        game_id: GameId,
        kickoff: datetime,
        horizon: PITHorizon,
    ) -> PredictionCutoff:
        _require_aware(kickoff, "kickoff")
        return cls(
            game_id=game_id,
            kickoff=kickoff,
            prediction_time=kickoff - horizon.offset,
            horizon=horizon,
        )


@dataclass(frozen=True, slots=True)
class PITPolicy:
    version: str = "NFL_PIT_POLICY_V1"
    minimum_confidence: AvailabilityConfidence = AvailabilityConfidence.MEDIUM
    allow_inferred_report_date: bool = False
    allow_unknown_method: bool = False
    require_context_metadata: bool = True

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("PIT policy version cannot be blank")


DEFAULT_PIT_POLICY = PITPolicy()


@dataclass(frozen=True, slots=True)
class PITInputRef:
    input_kind: PITInputKind
    input_id: str
    available_at: datetime
    availability_method: AvailabilityMethod
    availability_confidence: AvailabilityConfidence
    source_table: str
    evidence_id: str | None = None
    evidence_observation_id: str | None = None
    provider_id: str | None = None
    provider_revision: str | None = None
    provider_schema_version: str | None = None
    parser_version: str | None = None
    subject_game_id: GameId | None = None
    effective_at: datetime | None = None
    published_at: datetime | None = None
    observed_at: datetime | None = None
    ingested_at: datetime | None = None
    source_game_kickoff: datetime | None = None
    market_quote_at: datetime | None = None
    season_complete_at: datetime | None = None
    payload_sha256: str | None = None
    raw_sha256: str | None = None

    def __post_init__(self) -> None:
        for text_value, label in (
            (self.input_id, "input_id"),
            (self.source_table, "source_table"),
        ):
            if not text_value.strip():
                raise ValueError(f"{label} cannot be blank")
        for value, label in (
            (self.evidence_id, "evidence_id"),
            (self.evidence_observation_id, "evidence_observation_id"),
            (self.provider_id, "provider_id"),
            (self.provider_revision, "provider_revision"),
            (self.provider_schema_version, "provider_schema_version"),
            (self.parser_version, "parser_version"),
        ):
            _validate_optional_text(value, label)
        if self.evidence_observation_id is not None and self.evidence_id is None:
            raise ValueError("evidence_observation_id requires evidence_id")
        if (
            any(
                value is not None
                for value in (
                    self.provider_revision,
                    self.provider_schema_version,
                    self.parser_version,
                )
            )
            and self.provider_id is None
        ):
            raise ValueError("provider version metadata requires provider_id")
        if self.subject_game_id is not None and not str(self.subject_game_id).strip():
            raise ValueError("subject_game_id cannot be blank when present")
        for value, label in (
            (self.payload_sha256, "payload_sha256"),
            (self.raw_sha256, "raw_sha256"),
        ):
            if value is not None and not _is_sha256(value):
                raise ValueError(f"{label} must be a SHA-256 hex digest")
        for timestamp, label in (
            (self.available_at, "available_at"),
            (self.effective_at, "effective_at"),
            (self.published_at, "published_at"),
            (self.observed_at, "observed_at"),
            (self.ingested_at, "ingested_at"),
            (self.source_game_kickoff, "source_game_kickoff"),
            (self.market_quote_at, "market_quote_at"),
            (self.season_complete_at, "season_complete_at"),
        ):
            _require_aware(timestamp, label)
        if (
            self.observed_at is not None
            and self.ingested_at is not None
            and self.ingested_at < self.observed_at
        ):
            raise ValueError("ingested_at cannot precede observed_at")
        if self.observed_at is not None and self.available_at > self.observed_at:
            raise ValueError("available_at cannot be later than observed_at")
        if self.ingested_at is not None and self.available_at > self.ingested_at:
            raise ValueError("available_at cannot be later than ingested_at")
        if self.availability_method is AvailabilityMethod.OUR_OBSERVATION_TIME:
            if self.observed_at is None:
                raise ValueError("OUR_OBSERVATION_TIME requires observed_at")
            if self.available_at != self.observed_at:
                raise ValueError("OUR_OBSERVATION_TIME requires available_at == observed_at")


@dataclass(frozen=True, slots=True)
class PITFeatureValue:
    name: str
    value: PITFeatureScalar

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("feature name cannot be blank")
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError("feature float values must be finite")


@dataclass(frozen=True, slots=True)
class PITFeatureSnapshotSpec:
    """M5 snapshot metadata without defining the later M9 feature registry."""

    feature_contract: str
    feature_version: str
    feature_values: tuple[PITFeatureValue, ...] = ()
    missing_features: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.feature_contract.strip():
            raise ValueError("feature_contract cannot be blank")
        if not self.feature_version.strip():
            raise ValueError("feature_version cannot be blank")
        names = [feature.name for feature in self.feature_values]
        if len(names) != len(set(names)):
            raise ValueError("feature values cannot contain duplicate names")
        if any(not feature.strip() for feature in self.missing_features):
            raise ValueError("missing feature names cannot be blank")
        if len(self.missing_features) != len(set(self.missing_features)):
            raise ValueError("missing feature names cannot repeat")
        overlap = set(names).intersection(self.missing_features)
        if overlap:
            raise ValueError("a feature cannot be both present and missing")


@dataclass(frozen=True, slots=True)
class PITLeakageViolation:
    code: PITLeakageCode
    input_id: str
    explanation: str

    def __post_init__(self) -> None:
        if not self.input_id.strip():
            raise ValueError("input_id cannot be blank")
        if not self.explanation.strip():
            raise ValueError("leakage explanation cannot be blank")
