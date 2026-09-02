"""F-9 Coaching & Scheme State contracts and deterministic V1 estimation."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from daily_nfl.domain import (
    CoachingAssignmentObservationId,
    CoachingRegimeId,
    CoachingSchemeEvidenceObservationId,
    CoachingStintId,
    GameId,
    KnowledgeTimestamp,
    PersonId,
    PublicSchemeLabelObservationId,
    TeamSeasonId,
)
from daily_nfl.pit import PITInputKind, PITInputRef
from daily_nfl.state.contracts import (
    StateCoverage,
    StateSnapshotEnvelope,
    StateSubjectType,
    StateType,
)
from daily_nfl.state.snapshot import build_state_snapshot, canonical_state_json
from daily_nfl.state.uncertainty import (
    MissingnessReason,
    NamedMoments,
    NumericMoments,
    Probability,
    StateUncertainty,
    UnknownQuantity,
)


class CoachingRoleType(StrEnum):
    HEAD_COACH = "HEAD_COACH"
    OFFENSIVE_COORDINATOR = "OFFENSIVE_COORDINATOR"
    DEFENSIVE_COORDINATOR = "DEFENSIVE_COORDINATOR"
    SPECIAL_TEAMS_COORDINATOR = "SPECIAL_TEAMS_COORDINATOR"
    QB_COACH = "QB_COACH"
    OL_COACH = "OL_COACH"
    RB_COACH = "RB_COACH"
    WR_COACH = "WR_COACH"
    TE_COACH = "TE_COACH"
    DL_COACH = "DL_COACH"
    LB_COACH = "LB_COACH"
    DB_COACH = "DB_COACH"
    OTHER = "OTHER"


class CoachingResponsibility(StrEnum):
    OFFENSIVE_PLAY_CALLER = "OFFENSIVE_PLAY_CALLER"
    DEFENSIVE_PLAY_CALLER = "DEFENSIVE_PLAY_CALLER"


class CoachingStateComponent(StrEnum):
    OFFENSIVE_SCHEME = "OFFENSIVE_SCHEME"
    DEFENSIVE_SCHEME = "DEFENSIVE_SCHEME"
    SPECIAL_TEAMS_SCHEME = "SPECIAL_TEAMS_SCHEME"
    DECISION_POLICY = "DECISION_POLICY"
    ADAPTATION = "ADAPTATION"
    COACHING_EFFECTIVENESS = "COACHING_EFFECTIVENESS"


class CoachingEvidenceScope(StrEnum):
    BASE = "BASE"
    GAME_SPECIFIC_DEVIATION = "GAME_SPECIFIC_DEVIATION"


class PublicSchemeSide(StrEnum):
    OFFENSE = "OFFENSE"
    DEFENSE = "DEFENSE"
    SPECIAL_TEAMS = "SPECIAL_TEAMS"


_CONDITIONED_COMPONENTS = {
    CoachingStateComponent.OFFENSIVE_SCHEME,
    CoachingStateComponent.DEFENSIVE_SCHEME,
    CoachingStateComponent.SPECIAL_TEAMS_SCHEME,
    CoachingStateComponent.DECISION_POLICY,
}
_GAME_DEVIATION_COMPONENTS = _CONDITIONED_COMPONENTS
_UNIQUE_ROLE_TYPES = {
    CoachingRoleType.HEAD_COACH,
    CoachingRoleType.OFFENSIVE_COORDINATOR,
    CoachingRoleType.DEFENSIVE_COORDINATOR,
    CoachingRoleType.SPECIAL_TEAMS_COORDINATOR,
}


def _require_nonblank(value: str, label: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be blank")


def _require_aware(value: datetime | None, label: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{label} must be timezone-aware")


def _optional_text(value: str | None, label: str) -> None:
    if value is not None and not value.strip():
        raise ValueError(f"{label} cannot be blank when present")


def _canonical_named_moments(
    metrics: tuple[NamedMoments, ...],
) -> tuple[NamedMoments, ...]:
    names = [metric.name for metric in metrics]
    if len(names) != len(set(names)):
        raise ValueError("coaching evidence metric names cannot repeat")
    return tuple(sorted(metrics, key=lambda metric: metric.name))


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_state_json(value).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CoachingGameStateCondition:
    """Machine-readable conditioning for empirical coaching-policy evidence."""

    contract: str = "NFL_COACHING_GAME_STATE_CONDITION_V1"
    version: str = "1"
    neutral_situation: bool | None = None
    down_bucket: str | None = None
    distance_bucket: str | None = None
    score_state: str | None = None
    time_state: str | None = None
    field_position_state: str | None = None
    personnel_state: str | None = None
    opponent_context: str | None = None

    def __post_init__(self) -> None:
        _require_nonblank(self.contract, "coaching condition contract")
        _require_nonblank(self.version, "coaching condition version")
        for value, label in (
            (self.down_bucket, "down_bucket"),
            (self.distance_bucket, "distance_bucket"),
            (self.score_state, "score_state"),
            (self.time_state, "time_state"),
            (self.field_position_state, "field_position_state"),
            (self.personnel_state, "personnel_state"),
            (self.opponent_context, "opponent_context"),
        ):
            _optional_text(value, label)

    @property
    def is_conditioned(self) -> bool:
        return any(
            value is not None
            for value in (
                self.neutral_situation,
                self.down_bucket,
                self.distance_bucket,
                self.score_state,
                self.time_state,
                self.field_position_state,
                self.personnel_state,
                self.opponent_context,
            )
        )

    @property
    def conditioning_sha256(self) -> str:
        return _sha256(self)


@dataclass(frozen=True, slots=True)
class CoachingAssignmentObservation:
    observation_id: CoachingAssignmentObservationId
    coaching_stint_id: CoachingStintId
    person_id: PersonId
    team_season_id: TeamSeasonId
    logical_key: str
    revision: int
    role_type: CoachingRoleType
    responsibilities: tuple[CoachingResponsibility, ...]
    assignment_contract: str
    assignment_version: str
    knowledge: KnowledgeTimestamp
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    provider_id: str | None = None
    evidence_id: str | None = None
    evidence_observation_id: str | None = None
    provider_revision: str | None = None
    provider_schema_version: str | None = None
    parser_version: str | None = None
    raw_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_nonblank(str(self.observation_id), "coaching assignment observation_id")
        _require_nonblank(str(self.coaching_stint_id), "coaching stint_id")
        _require_nonblank(str(self.person_id), "coaching person_id")
        _require_nonblank(str(self.team_season_id), "coaching team_season_id")
        _require_nonblank(self.logical_key, "coaching assignment logical_key")
        _require_nonblank(self.assignment_contract, "coaching assignment contract")
        _require_nonblank(self.assignment_version, "coaching assignment version")
        if self.revision < 1:
            raise ValueError("coaching assignment revision must be >= 1")
        responsibility_values = [item.value for item in self.responsibilities]
        if len(responsibility_values) != len(set(responsibility_values)):
            raise ValueError("coaching assignment responsibilities cannot repeat")
        _require_aware(self.effective_from, "coaching assignment effective_from")
        _require_aware(self.effective_to, "coaching assignment effective_to")
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError("coaching assignment cannot end before it starts")
        for value, label in (
            (self.provider_id, "provider_id"),
            (self.evidence_id, "evidence_id"),
            (self.evidence_observation_id, "evidence_observation_id"),
            (self.provider_revision, "provider_revision"),
            (self.provider_schema_version, "provider_schema_version"),
            (self.parser_version, "parser_version"),
            (self.raw_sha256, "raw_sha256"),
        ):
            _optional_text(value, label)
        if self.evidence_observation_id is not None and self.evidence_id is None:
            raise ValueError("evidence_observation_id requires evidence_id")
        if self.raw_sha256 is not None and self.evidence_id is None:
            raise ValueError("raw_sha256 requires evidence_id")

    @property
    def canonical_responsibilities(self) -> tuple[CoachingResponsibility, ...]:
        return tuple(sorted(self.responsibilities, key=lambda item: item.value))

    @property
    def responsibilities_sha256(self) -> str:
        return _sha256(tuple(item.value for item in self.canonical_responsibilities))

    @property
    def payload_sha256(self) -> str:
        return _sha256(
            {
                "coaching_stint_id": str(self.coaching_stint_id),
                "person_id": str(self.person_id),
                "team_season_id": str(self.team_season_id),
                "logical_key": self.logical_key,
                "revision": self.revision,
                "role_type": self.role_type.value,
                "responsibilities": [
                    item.value for item in self.canonical_responsibilities
                ],
                "effective_from": self.effective_from,
                "effective_to": self.effective_to,
                "assignment_contract": self.assignment_contract,
                "assignment_version": self.assignment_version,
            }
        )

    def is_active_at(self, as_of: datetime) -> bool:
        _require_aware(as_of, "coaching assignment as_of")
        if self.effective_from is not None and as_of < self.effective_from:
            return False
        if self.effective_to is not None and as_of >= self.effective_to:
            return False
        return True

    def to_pit_input_ref(self) -> PITInputRef:
        return PITInputRef(
            input_kind=PITInputKind.OTHER,
            input_id=str(self.observation_id),
            available_at=self.knowledge.available_at,
            availability_method=self.knowledge.availability_method,
            availability_confidence=self.knowledge.availability_confidence,
            source_table="coaching_assignment_observations",
            evidence_id=self.evidence_id,
            evidence_observation_id=self.evidence_observation_id,
            provider_id=self.provider_id,
            provider_revision=self.provider_revision,
            provider_schema_version=self.provider_schema_version,
            parser_version=self.parser_version,
            effective_at=self.knowledge.effective_at,
            published_at=self.knowledge.published_at,
            observed_at=self.knowledge.observed_at,
            ingested_at=self.knowledge.ingested_at,
            payload_sha256=self.payload_sha256,
            raw_sha256=self.raw_sha256,
        )


@dataclass(frozen=True, slots=True)
class CoachingSchemeEvidenceObservation:
    observation_id: CoachingSchemeEvidenceObservationId
    team_season_id: TeamSeasonId
    logical_key: str
    revision: int
    component: CoachingStateComponent
    evidence_scope: CoachingEvidenceScope
    condition: CoachingGameStateCondition
    metrics: tuple[NamedMoments, ...]
    sample_weight: float
    source_confidence: Probability
    evidence_contract: str
    evidence_version: str
    knowledge: KnowledgeTimestamp
    source_game_id: GameId | None = None
    applies_to_game_id: GameId | None = None
    provider_id: str | None = None
    evidence_id: str | None = None
    evidence_observation_id: str | None = None
    provider_revision: str | None = None
    provider_schema_version: str | None = None
    parser_version: str | None = None
    raw_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_nonblank(str(self.observation_id), "coaching scheme observation_id")
        _require_nonblank(str(self.team_season_id), "coaching scheme team_season_id")
        _require_nonblank(self.logical_key, "coaching scheme logical_key")
        _require_nonblank(self.evidence_contract, "coaching scheme evidence contract")
        _require_nonblank(self.evidence_version, "coaching scheme evidence version")
        if self.revision < 1:
            raise ValueError("coaching scheme evidence revision must be >= 1")
        if not math.isfinite(self.sample_weight) or self.sample_weight <= 0.0:
            raise ValueError("coaching scheme sample_weight must be finite and > 0")
        if not self.metrics:
            raise ValueError("coaching scheme evidence requires at least one metric")
        _canonical_named_moments(self.metrics)
        if self.component in _CONDITIONED_COMPONENTS and not self.condition.is_conditioned:
            raise ValueError(
                "coaching tendency evidence must be explicitly game-state conditioned"
            )
        if self.evidence_scope is CoachingEvidenceScope.GAME_SPECIFIC_DEVIATION:
            if self.component not in _GAME_DEVIATION_COMPONENTS:
                raise ValueError(
                    "game-specific coaching deviation is only valid for policy/scheme components"
                )
            if self.applies_to_game_id is None:
                raise ValueError("game-specific coaching deviation requires applies_to_game_id")
        elif self.applies_to_game_id is not None:
            raise ValueError("base coaching evidence cannot declare applies_to_game_id")
        for value, label in (
            (self.provider_id, "provider_id"),
            (self.evidence_id, "evidence_id"),
            (self.evidence_observation_id, "evidence_observation_id"),
            (self.provider_revision, "provider_revision"),
            (self.provider_schema_version, "provider_schema_version"),
            (self.parser_version, "parser_version"),
            (self.raw_sha256, "raw_sha256"),
        ):
            _optional_text(value, label)
        if self.evidence_observation_id is not None and self.evidence_id is None:
            raise ValueError("evidence_observation_id requires evidence_id")
        if self.raw_sha256 is not None and self.evidence_id is None:
            raise ValueError("raw_sha256 requires evidence_id")

    @property
    def game_state_conditioned(self) -> bool:
        return self.condition.is_conditioned

    @property
    def conditioning_sha256(self) -> str:
        return self.condition.conditioning_sha256

    @property
    def metrics_sha256(self) -> str:
        return _sha256(_canonical_named_moments(self.metrics))

    @property
    def payload_sha256(self) -> str:
        return _sha256(
            {
                "team_season_id": str(self.team_season_id),
                "source_game_id": (
                    str(self.source_game_id) if self.source_game_id is not None else None
                ),
                "applies_to_game_id": (
                    str(self.applies_to_game_id)
                    if self.applies_to_game_id is not None
                    else None
                ),
                "logical_key": self.logical_key,
                "revision": self.revision,
                "component": self.component.value,
                "evidence_scope": self.evidence_scope.value,
                "conditioning_sha256": self.conditioning_sha256,
                "metrics_sha256": self.metrics_sha256,
                "sample_weight": self.sample_weight,
                "source_confidence": self.source_confidence.value,
                "evidence_contract": self.evidence_contract,
                "evidence_version": self.evidence_version,
            }
        )

    def to_pit_input_ref(self) -> PITInputRef:
        return PITInputRef(
            input_kind=PITInputKind.OTHER,
            input_id=str(self.observation_id),
            available_at=self.knowledge.available_at,
            availability_method=self.knowledge.availability_method,
            availability_confidence=self.knowledge.availability_confidence,
            source_table="coaching_scheme_evidence_observations",
            evidence_id=self.evidence_id,
            evidence_observation_id=self.evidence_observation_id,
            provider_id=self.provider_id,
            provider_revision=self.provider_revision,
            provider_schema_version=self.provider_schema_version,
            parser_version=self.parser_version,
            subject_game_id=self.source_game_id,
            effective_at=self.knowledge.effective_at,
            published_at=self.knowledge.published_at,
            observed_at=self.knowledge.observed_at,
            ingested_at=self.knowledge.ingested_at,
            payload_sha256=self.payload_sha256,
            raw_sha256=self.raw_sha256,
        )


@dataclass(frozen=True, slots=True)
class PublicSchemeLabelObservation:
    observation_id: PublicSchemeLabelObservationId
    team_season_id: TeamSeasonId
    side: PublicSchemeSide
    logical_key: str
    revision: int
    label: str
    knowledge: KnowledgeTimestamp
    provider_id: str | None = None
    evidence_id: str | None = None
    evidence_observation_id: str | None = None
    provider_revision: str | None = None
    provider_schema_version: str | None = None
    parser_version: str | None = None
    raw_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_nonblank(str(self.observation_id), "public scheme label observation_id")
        _require_nonblank(str(self.team_season_id), "public scheme label team_season_id")
        _require_nonblank(self.logical_key, "public scheme label logical_key")
        _require_nonblank(self.label, "public scheme label")
        if self.revision < 1:
            raise ValueError("public scheme label revision must be >= 1")
        for value, label in (
            (self.provider_id, "provider_id"),
            (self.evidence_id, "evidence_id"),
            (self.evidence_observation_id, "evidence_observation_id"),
            (self.provider_revision, "provider_revision"),
            (self.provider_schema_version, "provider_schema_version"),
            (self.parser_version, "parser_version"),
            (self.raw_sha256, "raw_sha256"),
        ):
            _optional_text(value, label)
        if self.evidence_observation_id is not None and self.evidence_id is None:
            raise ValueError("evidence_observation_id requires evidence_id")
        if self.raw_sha256 is not None and self.evidence_id is None:
            raise ValueError("raw_sha256 requires evidence_id")

    @property
    def payload_sha256(self) -> str:
        return _sha256(
            {
                "team_season_id": str(self.team_season_id),
                "side": self.side.value,
                "logical_key": self.logical_key,
                "revision": self.revision,
                "label": self.label,
            }
        )

    def to_pit_input_ref(self) -> PITInputRef:
        return PITInputRef(
            input_kind=PITInputKind.OTHER,
            input_id=str(self.observation_id),
            available_at=self.knowledge.available_at,
            availability_method=self.knowledge.availability_method,
            availability_confidence=self.knowledge.availability_confidence,
            source_table="public_scheme_label_observations",
            evidence_id=self.evidence_id,
            evidence_observation_id=self.evidence_observation_id,
            provider_id=self.provider_id,
            provider_revision=self.provider_revision,
            provider_schema_version=self.provider_schema_version,
            parser_version=self.parser_version,
            effective_at=self.knowledge.effective_at,
            published_at=self.knowledge.published_at,
            observed_at=self.knowledge.observed_at,
            ingested_at=self.knowledge.ingested_at,
            payload_sha256=self.payload_sha256,
            raw_sha256=self.raw_sha256,
        )


@dataclass(frozen=True, slots=True)
class ActiveCoachingAssignment:
    coaching_stint_id: CoachingStintId
    person_id: PersonId
    role_type: CoachingRoleType
    responsibilities: tuple[CoachingResponsibility, ...]
    logical_key: str


@dataclass(frozen=True, slots=True)
class CoachingStateDimension:
    metrics: tuple[NamedMoments, ...]
    evidence_count: int
    effective_weight: float
    low_sample: bool

    def __post_init__(self) -> None:
        if self.evidence_count < 0:
            raise ValueError("coaching state evidence_count cannot be negative")
        if not math.isfinite(self.effective_weight) or self.effective_weight < 0.0:
            raise ValueError("coaching state effective_weight must be finite and non-negative")
        _canonical_named_moments(self.metrics)


@dataclass(frozen=True, slots=True)
class ConditionedCoachingEstimate:
    condition: CoachingGameStateCondition
    metrics: tuple[NamedMoments, ...]
    evidence_count: int
    effective_weight: float
    low_sample: bool

    def __post_init__(self) -> None:
        if not self.condition.is_conditioned:
            raise ValueError("conditioned coaching estimate requires game-state condition")
        if self.evidence_count < 1:
            raise ValueError("conditioned coaching estimate requires evidence")
        if not math.isfinite(self.effective_weight) or self.effective_weight <= 0.0:
            raise ValueError("conditioned coaching effective_weight must be finite and > 0")
        _canonical_named_moments(self.metrics)


@dataclass(frozen=True, slots=True)
class EmpiricalSchemeState:
    base_estimates: tuple[ConditionedCoachingEstimate, ...]
    game_specific_deviation_estimates: tuple[ConditionedCoachingEstimate, ...]


@dataclass(frozen=True, slots=True)
class CoachingStatePayload:
    team_season_id: TeamSeasonId
    game_id: GameId
    regime_id: CoachingRegimeId
    active_assignments: tuple[ActiveCoachingAssignment, ...]
    head_coach_id: PersonId | None
    offensive_coordinator_id: PersonId | None
    defensive_coordinator_id: PersonId | None
    special_teams_coordinator_id: PersonId | None
    offensive_play_caller_id: PersonId | None
    defensive_play_caller_id: PersonId | None
    public_scheme_labels: tuple[PublicSchemeLabelObservation, ...]
    offensive_scheme_state: EmpiricalSchemeState
    defensive_scheme_state: EmpiricalSchemeState
    special_teams_state: EmpiricalSchemeState
    decision_policy_state: EmpiricalSchemeState
    adaptation_state: CoachingStateDimension
    coaching_effectiveness_state: CoachingStateDimension


@dataclass(frozen=True, slots=True)
class CoachingStateEstimatorConfig:
    version: str = "NFL_COACHING_STATE_BASELINE_V1"
    offensive_scheme_half_life_days: float = 90.0
    defensive_scheme_half_life_days: float = 90.0
    special_teams_half_life_days: float = 120.0
    decision_policy_half_life_days: float = 120.0
    adaptation_half_life_days: float = 365.0
    coaching_effectiveness_half_life_days: float = 365.0
    low_sample_effective_weight: float = 2.0

    def __post_init__(self) -> None:
        _require_nonblank(self.version, "coaching state estimator version")
        for value in (
            self.offensive_scheme_half_life_days,
            self.defensive_scheme_half_life_days,
            self.special_teams_half_life_days,
            self.decision_policy_half_life_days,
            self.adaptation_half_life_days,
            self.coaching_effectiveness_half_life_days,
            self.low_sample_effective_weight,
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError("coaching state estimator weights must be finite and > 0")

    def half_life_days(self, component: CoachingStateComponent) -> float:
        return {
            CoachingStateComponent.OFFENSIVE_SCHEME: self.offensive_scheme_half_life_days,
            CoachingStateComponent.DEFENSIVE_SCHEME: self.defensive_scheme_half_life_days,
            CoachingStateComponent.SPECIAL_TEAMS_SCHEME: self.special_teams_half_life_days,
            CoachingStateComponent.DECISION_POLICY: self.decision_policy_half_life_days,
            CoachingStateComponent.ADAPTATION: self.adaptation_half_life_days,
            CoachingStateComponent.COACHING_EFFECTIVENESS: (
                self.coaching_effectiveness_half_life_days
            ),
        }[component]


DEFAULT_COACHING_STATE_ESTIMATOR_CONFIG = CoachingStateEstimatorConfig()


def coaching_regime_id(
    assignments: tuple[CoachingAssignmentObservation, ...],
) -> CoachingRegimeId:
    if not assignments:
        raise ValueError("coaching regime requires at least one active assignment")
    payload = [
        {
            "logical_key": assignment.logical_key,
            "coaching_stint_id": str(assignment.coaching_stint_id),
            "person_id": str(assignment.person_id),
            "role_type": assignment.role_type.value,
            "responsibilities": [
                responsibility.value
                for responsibility in assignment.canonical_responsibilities
            ],
        }
        for assignment in sorted(
            assignments,
            key=lambda item: (
                item.logical_key,
                str(item.person_id),
                item.role_type.value,
            ),
        )
    ]
    return CoachingRegimeId(f"coaching_regime_{_sha256(payload)}")


def _latest_assignments_as_of(
    assignments: tuple[CoachingAssignmentObservation, ...],
    *,
    team_season_id: TeamSeasonId,
    as_of: datetime,
) -> tuple[CoachingAssignmentObservation, ...]:
    latest: dict[str, CoachingAssignmentObservation] = {}
    for assignment in assignments:
        if assignment.team_season_id != team_season_id:
            raise ValueError("coaching assignment belongs to a different team")
        if assignment.knowledge.available_at > as_of:
            raise ValueError("coaching assignment cannot be available after Coaching State as_of")
        existing = latest.get(assignment.logical_key)
        if existing is None or assignment.revision > existing.revision:
            latest[assignment.logical_key] = assignment
        elif assignment.revision == existing.revision:
            if assignment.payload_sha256 != existing.payload_sha256:
                raise ValueError("conflicting coaching assignment revisions at PIT cutoff")
            if str(assignment.observation_id) < str(existing.observation_id):
                latest[assignment.logical_key] = assignment
    active = tuple(
        sorted(
            (item for item in latest.values() if item.is_active_at(as_of)),
            key=lambda item: (item.logical_key, str(item.person_id)),
        )
    )
    if not active:
        raise ValueError("Coaching State requires at least one active coaching assignment")
    return active


def _validate_unique_assignments(
    assignments: tuple[CoachingAssignmentObservation, ...],
) -> None:
    for role_type in _UNIQUE_ROLE_TYPES:
        members = [item for item in assignments if item.role_type is role_type]
        if len(members) > 1:
            raise ValueError(f"multiple active coaching assignments claim {role_type.value}")
    for responsibility in CoachingResponsibility:
        members = [
            item
            for item in assignments
            if responsibility in item.canonical_responsibilities
        ]
        if len(members) > 1:
            raise ValueError(
                f"multiple active coaching assignments claim {responsibility.value}"
            )


def _person_for_role(
    assignments: tuple[CoachingAssignmentObservation, ...],
    role_type: CoachingRoleType,
) -> PersonId | None:
    for assignment in assignments:
        if assignment.role_type is role_type:
            return assignment.person_id
    return None


def _person_for_responsibility(
    assignments: tuple[CoachingAssignmentObservation, ...],
    responsibility: CoachingResponsibility,
) -> PersonId | None:
    for assignment in assignments:
        if responsibility in assignment.canonical_responsibilities:
            return assignment.person_id
    return None


def _evidence_weight(
    observation: CoachingSchemeEvidenceObservation,
    *,
    as_of: datetime,
    config: CoachingStateEstimatorConfig,
) -> float:
    age_days = max(
        0.0,
        (as_of - observation.knowledge.available_at).total_seconds() / 86400.0,
    )
    recency_weight = math.exp2(-age_days / config.half_life_days(observation.component))
    return observation.sample_weight * observation.source_confidence.value * recency_weight


def _aggregate_metric_rows(
    observations: tuple[CoachingSchemeEvidenceObservation, ...],
    *,
    as_of: datetime,
    config: CoachingStateEstimatorConfig,
) -> CoachingStateDimension:
    weighted_metrics: dict[str, list[tuple[NumericMoments, float]]] = {}
    weights: list[float] = []
    for observation in observations:
        weight = _evidence_weight(observation, as_of=as_of, config=config)
        if weight <= 0.0:
            continue
        weights.append(weight)
        for metric in observation.metrics:
            weighted_metrics.setdefault(metric.name, []).append((metric.estimate, weight))
    metrics: list[NamedMoments] = []
    for name in sorted(weighted_metrics):
        members = weighted_metrics[name]
        total_weight = math.fsum(weight for _, weight in members)
        if total_weight <= 0.0:
            continue
        mean = math.fsum(estimate.mean * weight for estimate, weight in members) / total_weight
        variance = math.fsum(
            weight * (estimate.variance + (estimate.mean - mean) ** 2)
            for estimate, weight in members
        ) / total_weight
        metrics.append(NamedMoments(name=name, estimate=NumericMoments(mean, variance)))
    effective_weight = math.fsum(weights)
    return CoachingStateDimension(
        metrics=tuple(metrics),
        evidence_count=len(observations),
        effective_weight=effective_weight,
        low_sample=(
            not metrics or effective_weight < config.low_sample_effective_weight
        ),
    )


def _aggregate_conditioned(
    observations: tuple[CoachingSchemeEvidenceObservation, ...],
    *,
    component: CoachingStateComponent,
    scope: CoachingEvidenceScope,
    as_of: datetime,
    config: CoachingStateEstimatorConfig,
) -> tuple[ConditionedCoachingEstimate, ...]:
    groups: dict[str, list[CoachingSchemeEvidenceObservation]] = {}
    conditions: dict[str, CoachingGameStateCondition] = {}
    for observation in observations:
        if observation.component is not component or observation.evidence_scope is not scope:
            continue
        key = observation.conditioning_sha256
        groups.setdefault(key, []).append(observation)
        conditions[key] = observation.condition
    estimates: list[ConditionedCoachingEstimate] = []
    for key in sorted(groups):
        rows = tuple(groups[key])
        dimension = _aggregate_metric_rows(rows, as_of=as_of, config=config)
        if not dimension.metrics or dimension.effective_weight <= 0.0:
            continue
        estimates.append(
            ConditionedCoachingEstimate(
                condition=conditions[key],
                metrics=dimension.metrics,
                evidence_count=dimension.evidence_count,
                effective_weight=dimension.effective_weight,
                low_sample=dimension.low_sample,
            )
        )
    return tuple(estimates)


def _empirical_scheme_state(
    observations: tuple[CoachingSchemeEvidenceObservation, ...],
    *,
    component: CoachingStateComponent,
    as_of: datetime,
    config: CoachingStateEstimatorConfig,
) -> EmpiricalSchemeState:
    return EmpiricalSchemeState(
        base_estimates=_aggregate_conditioned(
            observations,
            component=component,
            scope=CoachingEvidenceScope.BASE,
            as_of=as_of,
            config=config,
        ),
        game_specific_deviation_estimates=_aggregate_conditioned(
            observations,
            component=component,
            scope=CoachingEvidenceScope.GAME_SPECIFIC_DEVIATION,
            as_of=as_of,
            config=config,
        ),
    )


def _validate_scheme_evidence(
    observations: tuple[CoachingSchemeEvidenceObservation, ...],
    *,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    as_of: datetime,
) -> tuple[CoachingSchemeEvidenceObservation, ...]:
    for observation in observations:
        if observation.team_season_id != team_season_id:
            raise ValueError("coaching scheme evidence belongs to a different team")
        if observation.knowledge.available_at > as_of:
            raise ValueError("coaching scheme evidence cannot be available after Coaching State as_of")
        if observation.source_game_id == game_id:
            raise ValueError("current pregame target game cannot be coaching source evidence")
        if (
            observation.evidence_scope is CoachingEvidenceScope.GAME_SPECIFIC_DEVIATION
            and observation.applies_to_game_id != game_id
        ):
            raise ValueError("game-specific coaching evidence applies to a different game")
    return tuple(sorted(observations, key=lambda item: str(item.observation_id)))


def _validate_public_labels(
    observations: tuple[PublicSchemeLabelObservation, ...],
    *,
    team_season_id: TeamSeasonId,
    as_of: datetime,
) -> tuple[PublicSchemeLabelObservation, ...]:
    for observation in observations:
        if observation.team_season_id != team_season_id:
            raise ValueError("public scheme label belongs to a different team")
        if observation.knowledge.available_at > as_of:
            raise ValueError("public scheme label cannot be available after Coaching State as_of")
    return tuple(
        sorted(
            observations,
            key=lambda item: (item.side.value, item.logical_key, str(item.observation_id)),
        )
    )


def _unknown_if_none(
    name: str,
    value: object | None,
    detail: str,
) -> UnknownQuantity | None:
    if value is not None:
        return None
    return UnknownQuantity(
        name=name,
        reason=MissingnessReason.DATA_UNAVAILABLE,
        detail=detail,
    )


def _unknown_if_empty(
    name: str,
    values: tuple[object, ...],
    detail: str,
) -> UnknownQuantity | None:
    if values:
        return None
    return UnknownQuantity(
        name=name,
        reason=MissingnessReason.DATA_UNAVAILABLE,
        detail=detail,
    )


def build_coaching_state_snapshot(
    *,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    as_of: datetime,
    assignment_observations: tuple[CoachingAssignmentObservation, ...],
    scheme_evidence: tuple[CoachingSchemeEvidenceObservation, ...],
    public_scheme_labels: tuple[PublicSchemeLabelObservation, ...] = (),
    config: CoachingStateEstimatorConfig = DEFAULT_COACHING_STATE_ESTIMATOR_CONFIG,
    created_at: datetime,
) -> StateSnapshotEnvelope[CoachingStatePayload]:
    """Build one immutable PIT-safe F-9 Coaching State snapshot."""

    _require_aware(as_of, "Coaching State as_of")
    _require_aware(created_at, "Coaching State created_at")
    active = _latest_assignments_as_of(
        assignment_observations,
        team_season_id=team_season_id,
        as_of=as_of,
    )
    _validate_unique_assignments(active)
    evidence = _validate_scheme_evidence(
        scheme_evidence,
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
    )
    labels = _validate_public_labels(
        public_scheme_labels,
        team_season_id=team_season_id,
        as_of=as_of,
    )

    regime_id = coaching_regime_id(active)
    active_payload = tuple(
        ActiveCoachingAssignment(
            coaching_stint_id=item.coaching_stint_id,
            person_id=item.person_id,
            role_type=item.role_type,
            responsibilities=item.canonical_responsibilities,
            logical_key=item.logical_key,
        )
        for item in active
    )

    offensive = _empirical_scheme_state(
        evidence,
        component=CoachingStateComponent.OFFENSIVE_SCHEME,
        as_of=as_of,
        config=config,
    )
    defensive = _empirical_scheme_state(
        evidence,
        component=CoachingStateComponent.DEFENSIVE_SCHEME,
        as_of=as_of,
        config=config,
    )
    special_teams = _empirical_scheme_state(
        evidence,
        component=CoachingStateComponent.SPECIAL_TEAMS_SCHEME,
        as_of=as_of,
        config=config,
    )
    decision_policy = _empirical_scheme_state(
        evidence,
        component=CoachingStateComponent.DECISION_POLICY,
        as_of=as_of,
        config=config,
    )
    adaptation_rows = tuple(
        item
        for item in evidence
        if item.component is CoachingStateComponent.ADAPTATION
        and item.evidence_scope is CoachingEvidenceScope.BASE
    )
    effectiveness_rows = tuple(
        item
        for item in evidence
        if item.component is CoachingStateComponent.COACHING_EFFECTIVENESS
        and item.evidence_scope is CoachingEvidenceScope.BASE
    )
    adaptation = _aggregate_metric_rows(adaptation_rows, as_of=as_of, config=config)
    effectiveness = _aggregate_metric_rows(
        effectiveness_rows,
        as_of=as_of,
        config=config,
    )

    head_coach_id = _person_for_role(active, CoachingRoleType.HEAD_COACH)
    offensive_coordinator_id = _person_for_role(
        active,
        CoachingRoleType.OFFENSIVE_COORDINATOR,
    )
    defensive_coordinator_id = _person_for_role(
        active,
        CoachingRoleType.DEFENSIVE_COORDINATOR,
    )
    special_teams_coordinator_id = _person_for_role(
        active,
        CoachingRoleType.SPECIAL_TEAMS_COORDINATOR,
    )
    offensive_play_caller_id = _person_for_responsibility(
        active,
        CoachingResponsibility.OFFENSIVE_PLAY_CALLER,
    )
    defensive_play_caller_id = _person_for_responsibility(
        active,
        CoachingResponsibility.DEFENSIVE_PLAY_CALLER,
    )

    payload = CoachingStatePayload(
        team_season_id=team_season_id,
        game_id=game_id,
        regime_id=regime_id,
        active_assignments=active_payload,
        head_coach_id=head_coach_id,
        offensive_coordinator_id=offensive_coordinator_id,
        defensive_coordinator_id=defensive_coordinator_id,
        special_teams_coordinator_id=special_teams_coordinator_id,
        offensive_play_caller_id=offensive_play_caller_id,
        defensive_play_caller_id=defensive_play_caller_id,
        public_scheme_labels=labels,
        offensive_scheme_state=offensive,
        defensive_scheme_state=defensive,
        special_teams_state=special_teams,
        decision_policy_state=decision_policy,
        adaptation_state=adaptation,
        coaching_effectiveness_state=effectiveness,
    )

    expected_fields = (
        "head_coach",
        "offensive_play_caller",
        "defensive_play_caller",
        "offensive_scheme_base",
        "defensive_scheme_base",
        "special_teams_scheme_base",
        "decision_policy_base",
        "adaptation_state",
        "coaching_effectiveness_state",
    )
    present: list[str] = []
    if head_coach_id is not None:
        present.append("head_coach")
    if offensive_play_caller_id is not None:
        present.append("offensive_play_caller")
    if defensive_play_caller_id is not None:
        present.append("defensive_play_caller")
    if offensive.base_estimates:
        present.append("offensive_scheme_base")
    if defensive.base_estimates:
        present.append("defensive_scheme_base")
    if special_teams.base_estimates:
        present.append("special_teams_scheme_base")
    if decision_policy.base_estimates:
        present.append("decision_policy_base")
    if adaptation.metrics:
        present.append("adaptation_state")
    if effectiveness.metrics:
        present.append("coaching_effectiveness_state")
    missing = tuple(field for field in expected_fields if field not in present)

    unknown_candidates = (
        _unknown_if_none(
            "head_coach",
            head_coach_id,
            "no PIT-safe active head-coach assignment was available",
        ),
        _unknown_if_none(
            "offensive_play_caller",
            offensive_play_caller_id,
            "offensive play-caller responsibility is unresolved",
        ),
        _unknown_if_none(
            "defensive_play_caller",
            defensive_play_caller_id,
            "defensive play-caller responsibility is unresolved",
        ),
        _unknown_if_empty(
            "offensive_scheme_base",
            offensive.base_estimates,
            "no conditioned empirical offensive-scheme evidence is available",
        ),
        _unknown_if_empty(
            "defensive_scheme_base",
            defensive.base_estimates,
            "no conditioned empirical defensive-scheme evidence is available",
        ),
        _unknown_if_empty(
            "special_teams_scheme_base",
            special_teams.base_estimates,
            "no conditioned empirical special-teams scheme evidence is available",
        ),
        _unknown_if_empty(
            "decision_policy_base",
            decision_policy.base_estimates,
            "no conditioned empirical decision-policy evidence is available",
        ),
        _unknown_if_empty(
            "adaptation_state",
            adaptation.metrics,
            "no PIT-safe coaching adaptation evidence is available",
        ),
        _unknown_if_empty(
            "coaching_effectiveness_state",
            effectiveness.metrics,
            "no PIT-safe coaching-effectiveness evidence is available",
        ),
    )
    unknowns = tuple(item for item in unknown_candidates if item is not None)

    inputs = tuple(
        [item.to_pit_input_ref() for item in active]
        + [item.to_pit_input_ref() for item in evidence]
        + [item.to_pit_input_ref() for item in labels]
    )
    return build_state_snapshot(
        state_type=StateType.COACHING,
        subject_type=StateSubjectType.COACHING_REGIME,
        subject_id=str(regime_id),
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
        calculation_contract="NFL_COACHING_STATE_V1",
        model_version=config.version,
        state_payload=payload,
        uncertainty=StateUncertainty(unknowns=unknowns),
        coverage=StateCoverage(
            expected_fields=expected_fields,
            present_fields=tuple(present),
            missing_fields=missing,
        ),
        input_observations=inputs,
        created_at=created_at,
    )
