"""Point-in-time reconstruction contracts for Daily NFL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod, GameId


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
    CURRENT_GAME_OUTCOME = "CURRENT_GAME_OUTCOME"
    ACTUAL_WEATHER_FOR_CURRENT_GAME = "ACTUAL_WEATHER_FOR_CURRENT_GAME"
    LATER_MARKET_QUOTE = "LATER_MARKET_QUOTE"
    FUTURE_GAME_INFORMATION = "FUTURE_GAME_INFORMATION"
    END_OF_SEASON_INFORMATION = "END_OF_SEASON_INFORMATION"
    LATE_PROVIDER_CORRECTION = "LATE_PROVIDER_CORRECTION"


def _require_aware(value: datetime | None, label: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{label} must be timezone-aware")


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
    subject_game_id: GameId | None = None
    effective_at: datetime | None = None
    published_at: datetime | None = None
    observed_at: datetime | None = None
    ingested_at: datetime | None = None
    source_game_kickoff: datetime | None = None
    market_quote_at: datetime | None = None
    season_complete_at: datetime | None = None
    payload_sha256: str | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.input_id, "input_id"),
            (self.source_table, "source_table"),
        ):
            if not value.strip():
                raise ValueError(f"{label} cannot be blank")
        for value, label in (
            (self.available_at, "available_at"),
            (self.effective_at, "effective_at"),
            (self.published_at, "published_at"),
            (self.observed_at, "observed_at"),
            (self.ingested_at, "ingested_at"),
            (self.source_game_kickoff, "source_game_kickoff"),
            (self.market_quote_at, "market_quote_at"),
            (self.season_complete_at, "season_complete_at"),
        ):
            _require_aware(value, label)


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
