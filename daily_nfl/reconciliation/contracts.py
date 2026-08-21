"""Typed contracts for auditable provider-to-canonical identity reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from daily_nfl.domain import TeamSeasonId


class CanonicalEntityType(StrEnum):
    FRANCHISE = "FRANCHISE"
    TEAM_SEASON = "TEAM_SEASON"
    PERSON = "PERSON"
    PLAYER = "PLAYER"
    EVENT = "EVENT"
    GAME = "GAME"


class ReconciliationStatus(StrEnum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICT = "CONFLICT"


class MatchMethod(StrEnum):
    EXISTING_CROSSWALK = "EXISTING_CROSSWALK"
    TRUSTED_EXTERNAL_ID = "TRUSTED_EXTERNAL_ID"
    CANONICAL_COMPOSITE = "CANONICAL_COMPOSITE"
    MANUAL_VERIFIED = "MANUAL_VERIFIED"
    EXACT_CANONICAL_ATTRIBUTE = "EXACT_CANONICAL_ATTRIBUTE"
    FUZZY_CANDIDATE_ONLY = "FUZZY_CANDIDATE_ONLY"


class ReconciliationReason(StrEnum):
    EXISTING_MAPPING = "EXISTING_MAPPING"
    TRUSTED_EXTERNAL_ID_CREATED = "TRUSTED_EXTERNAL_ID_CREATED"
    VERIFIED_BINDING_CREATED = "VERIFIED_BINDING_CREATED"
    FRANCHISE_SEASON_DERIVATION = "FRANCHISE_SEASON_DERIVATION"
    SINGLE_CANONICAL_GAME_MATCH = "SINGLE_CANONICAL_GAME_MATCH"
    NO_EXISTING_MAPPING = "NO_EXISTING_MAPPING"
    NO_CANONICAL_CANDIDATE = "NO_CANONICAL_CANDIDATE"
    MULTIPLE_ACTIVE_MAPPINGS = "MULTIPLE_ACTIVE_MAPPINGS"
    MULTIPLE_CANONICAL_CANDIDATES = "MULTIPLE_CANONICAL_CANDIDATES"
    TARGET_ENTITY_TYPE_MISMATCH = "TARGET_ENTITY_TYPE_MISMATCH"
    CROSSWALK_CONFLICT = "CROSSWALK_CONFLICT"
    FUZZY_REQUIRES_REVIEW = "FUZZY_REQUIRES_REVIEW"


GSIS_PLAYER_ENTITY_TYPE = "GSIS_PLAYER"
FRANCHISE_ENTITY_TYPE = "FRANCHISE"
TEAM_SEASON_ENTITY_TYPE = "TEAM_SEASON"
GAME_ENTITY_TYPE = "GAME"
PLAYER_ENTITY_TYPE = "PLAYER"


def _require_aware(value: datetime | None, label: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{label} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ExternalIdentity:
    provider_id: str
    provider_entity_type: str
    external_id: str
    valid_at: datetime | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.provider_id, "provider_id"),
            (self.provider_entity_type, "provider_entity_type"),
            (self.external_id, "external_id"),
        ):
            if not value.strip():
                raise ValueError(f"{label} cannot be blank")
        _require_aware(self.valid_at, "valid_at")


@dataclass(frozen=True, slots=True)
class IdentityCandidate:
    canonical_entity_type: CanonicalEntityType
    canonical_entity_id: str
    match_method: MatchMethod
    match_confidence: float
    explanation: str

    def __post_init__(self) -> None:
        if not self.canonical_entity_id.strip():
            raise ValueError("canonical_entity_id cannot be blank")
        if not 0.0 <= self.match_confidence <= 1.0:
            raise ValueError("match_confidence must be between 0 and 1")
        if not self.explanation.strip():
            raise ValueError("candidate explanation cannot be blank")


@dataclass(frozen=True, slots=True)
class ReconciliationDecision:
    decision_id: str
    external_identity: ExternalIdentity
    expected_entity_type: CanonicalEntityType
    status: ReconciliationStatus
    reason: ReconciliationReason
    candidates: tuple[IdentityCandidate, ...] = ()
    selected_canonical_entity_id: str | None = None
    match_method: MatchMethod | None = None
    match_confidence: float | None = None

    def __post_init__(self) -> None:
        if not self.decision_id.strip():
            raise ValueError("decision_id cannot be blank")
        if self.match_confidence is not None and not 0.0 <= self.match_confidence <= 1.0:
            raise ValueError("match_confidence must be between 0 and 1")
        if self.status is ReconciliationStatus.RESOLVED:
            if self.selected_canonical_entity_id is None:
                raise ValueError("resolved decision requires selected_canonical_entity_id")
            if self.match_method is None or self.match_confidence is None:
                raise ValueError("resolved decision requires method and confidence")
            if self.match_method is MatchMethod.FUZZY_CANDIDATE_ONLY:
                raise ValueError("fuzzy candidates cannot resolve an identity")
        elif self.selected_canonical_entity_id is not None:
            raise ValueError("unresolved/ambiguous/conflict decision cannot select an identity")

    @property
    def resolved(self) -> bool:
        return self.status is ReconciliationStatus.RESOLVED


@dataclass(frozen=True, slots=True)
class CrosswalkBinding:
    crosswalk_id: int
    canonical_entity_type: CanonicalEntityType
    canonical_entity_id: str
    external_identity: ExternalIdentity
    valid_from: datetime | None
    valid_to: datetime | None
    match_method: MatchMethod
    match_confidence: float
    verified: bool
    decision_id: str | None
    supersedes_crosswalk_id: int | None

    def __post_init__(self) -> None:
        if self.crosswalk_id < 1:
            raise ValueError("crosswalk_id must be positive")
        if not self.canonical_entity_id.strip():
            raise ValueError("canonical_entity_id cannot be blank")
        if not 0.0 <= self.match_confidence <= 1.0:
            raise ValueError("match_confidence must be between 0 and 1")
        _require_aware(self.valid_from, "valid_from")
        _require_aware(self.valid_to, "valid_to")
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to cannot precede valid_from")


@dataclass(frozen=True, slots=True)
class GameIdentityHint:
    season: int
    season_phase: str
    home_team_season_id: TeamSeasonId
    away_team_season_id: TeamSeasonId
    scheduled_kickoff: datetime
    week: int | None = None

    def __post_init__(self) -> None:
        if self.season < 1920:
            raise ValueError("season is outside the supported NFL era")
        if not self.season_phase.strip():
            raise ValueError("season_phase cannot be blank")
        if self.home_team_season_id == self.away_team_season_id:
            raise ValueError("home and away teams must differ")
        _require_aware(self.scheduled_kickoff, "scheduled_kickoff")
        if self.week is not None and self.week < 1:
            raise ValueError("week must be positive when present")
