"""F-8 Unit State contracts and deterministic V1 estimation."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from daily_nfl.domain import (
    GameId,
    KnowledgeTimestamp,
    PlayerId,
    StateSnapshotId,
    TeamSeasonId,
    UnitConfigurationId,
    UnitConfigurationObservationId,
    UnitStateEvidenceObservationId,
)
from daily_nfl.pit import PITInputKind, PITInputRef
from daily_nfl.state.contracts import (
    StateCoverage,
    StateSnapshotEnvelope,
    StateSubjectType,
    StateType,
)
from daily_nfl.state.player import (
    PlayerStateDimension,
    PlayerStatePayload,
)
from daily_nfl.state.snapshot import (
    build_state_snapshot,
    canonical_state_json,
    verify_state_snapshot_identity,
)
from daily_nfl.state.uncertainty import (
    CategoricalDistribution,
    CategoryProbability,
    MissingnessReason,
    NamedCategoricalDistribution,
    NamedMoments,
    NumericMoments,
    Probability,
    StateUncertainty,
    UnknownQuantity,
)


class UnitType(StrEnum):
    QB_ROOM = "QB_ROOM"
    OFFENSIVE_LINE = "OFFENSIVE_LINE"
    RECEIVING = "RECEIVING"
    BACKFIELD = "BACKFIELD"
    PASS_PROTECTION = "PASS_PROTECTION"
    RUN_BLOCKING = "RUN_BLOCKING"
    DEFENSIVE_FRONT = "DEFENSIVE_FRONT"
    PASS_RUSH = "PASS_RUSH"
    RUN_DEFENSE = "RUN_DEFENSE"
    LINEBACKER = "LINEBACKER"
    COVERAGE = "COVERAGE"
    SECONDARY = "SECONDARY"
    FIELD_GOAL = "FIELD_GOAL"
    PUNT = "PUNT"
    PUNT_COVERAGE = "PUNT_COVERAGE"
    KICKOFF = "KICKOFF"
    KICK_COVERAGE = "KICK_COVERAGE"
    PUNT_RETURN = "PUNT_RETURN"
    KICK_RETURN = "KICK_RETURN"


class UnitConfigurationAvailabilityBasis(StrEnum):
    ROLE_PRIOR_ONLY = "ROLE_PRIOR_ONLY"


class UnitEvidenceKind(StrEnum):
    CONTINUITY = "CONTINUITY"
    EXPERIENCE_TOGETHER = "EXPERIENCE_TOGETHER"
    ROLE_COMPATIBILITY = "ROLE_COMPATIBILITY"
    SYNERGY = "SYNERGY"
    RECENT_PERFORMANCE = "RECENT_PERFORMANCE"


_RESIDUALIZED_KINDS = {
    UnitEvidenceKind.ROLE_COMPATIBILITY,
    UnitEvidenceKind.SYNERGY,
    UnitEvidenceKind.RECENT_PERFORMANCE,
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
        raise ValueError("unit evidence metric names cannot repeat")
    return tuple(sorted(metrics, key=lambda metric: metric.name))


@dataclass(frozen=True, slots=True)
class UnitMemberAssignment:
    player_id: PlayerId
    role: str
    expected_share: Probability = Probability(1.0)

    def __post_init__(self) -> None:
        _require_nonblank(str(self.player_id), "unit member player_id")
        _require_nonblank(self.role, "unit member role")
        if self.expected_share.value <= 0.0:
            raise ValueError("unit member expected_share must be greater than zero")


@dataclass(frozen=True, slots=True)
class UnitConfigurationAlternative:
    members: tuple[UnitMemberAssignment, ...]
    prior_probability: Probability

    def __post_init__(self) -> None:
        if not self.members:
            raise ValueError("unit configuration requires at least one member")
        player_ids = [str(member.player_id) for member in self.members]
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("unit configuration cannot repeat a player")

    @property
    def configuration_id(self) -> UnitConfigurationId:
        payload = {
            "members": [
                {
                    "player_id": str(member.player_id),
                    "role": member.role,
                    "expected_share": member.expected_share.value,
                }
                for member in sorted(
                    self.members,
                    key=lambda item: (str(item.player_id), item.role),
                )
            ]
        }
        digest = hashlib.sha256(canonical_state_json(payload).encode()).hexdigest()
        return UnitConfigurationId(f"unit_config_{digest}")


def unit_configuration_distribution_sha256(
    alternatives: tuple[UnitConfigurationAlternative, ...],
) -> str:
    payload = [
        {
            "configuration_id": str(alternative.configuration_id),
            "prior_probability": alternative.prior_probability.value,
            "members": [
                {
                    "player_id": str(member.player_id),
                    "role": member.role,
                    "expected_share": member.expected_share.value,
                }
                for member in sorted(
                    alternative.members,
                    key=lambda item: (str(item.player_id), item.role),
                )
            ],
        }
        for alternative in sorted(
            alternatives,
            key=lambda item: str(item.configuration_id),
        )
    ]
    return hashlib.sha256(canonical_state_json(payload).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class UnitConfigurationObservation:
    observation_id: UnitConfigurationObservationId
    team_season_id: TeamSeasonId
    game_id: GameId
    unit_type: UnitType
    logical_key: str
    revision: int
    alternatives: tuple[UnitConfigurationAlternative, ...]
    configuration_contract: str
    configuration_version: str
    knowledge: KnowledgeTimestamp
    availability_basis: UnitConfigurationAvailabilityBasis = (
        UnitConfigurationAvailabilityBasis.ROLE_PRIOR_ONLY
    )
    provider_id: str | None = None
    evidence_id: str | None = None
    evidence_observation_id: str | None = None
    provider_revision: str | None = None
    provider_schema_version: str | None = None
    parser_version: str | None = None
    raw_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_nonblank(str(self.observation_id), "unit configuration observation_id")
        _require_nonblank(str(self.team_season_id), "unit configuration team_season_id")
        _require_nonblank(str(self.game_id), "unit configuration game_id")
        _require_nonblank(self.logical_key, "unit configuration logical_key")
        _require_nonblank(self.configuration_contract, "unit configuration contract")
        _require_nonblank(self.configuration_version, "unit configuration version")
        if self.revision < 1:
            raise ValueError("unit configuration revision must be >= 1")
        if not self.alternatives:
            raise ValueError("unit configuration observation requires alternatives")
        configuration_ids = [str(item.configuration_id) for item in self.alternatives]
        if len(configuration_ids) != len(set(configuration_ids)):
            raise ValueError("unit configuration alternatives cannot repeat")
        total = math.fsum(item.prior_probability.value for item in self.alternatives)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("unit configuration prior probability mass must sum to 1")
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
    def distribution_sha256(self) -> str:
        return unit_configuration_distribution_sha256(self.alternatives)

    @property
    def payload_sha256(self) -> str:
        payload = {
            "team_season_id": str(self.team_season_id),
            "game_id": str(self.game_id),
            "unit_type": self.unit_type.value,
            "logical_key": self.logical_key,
            "revision": self.revision,
            "availability_basis": self.availability_basis.value,
            "distribution_sha256": self.distribution_sha256,
            "configuration_contract": self.configuration_contract,
            "configuration_version": self.configuration_version,
        }
        return hashlib.sha256(canonical_state_json(payload).encode()).hexdigest()

    def to_pit_input_ref(self) -> PITInputRef:
        return PITInputRef(
            input_kind=PITInputKind.OTHER,
            input_id=str(self.observation_id),
            available_at=self.knowledge.available_at,
            availability_method=self.knowledge.availability_method,
            availability_confidence=self.knowledge.availability_confidence,
            source_table="unit_configuration_observations",
            evidence_id=self.evidence_id,
            evidence_observation_id=self.evidence_observation_id,
            provider_id=self.provider_id,
            provider_revision=self.provider_revision,
            provider_schema_version=self.provider_schema_version,
            parser_version=self.parser_version,
            subject_game_id=self.game_id,
            effective_at=self.knowledge.effective_at,
            published_at=self.knowledge.published_at,
            observed_at=self.knowledge.observed_at,
            ingested_at=self.knowledge.ingested_at,
            payload_sha256=self.payload_sha256,
            raw_sha256=self.raw_sha256,
        )


@dataclass(frozen=True, slots=True)
class UnitStateEvidenceObservation:
    observation_id: UnitStateEvidenceObservationId
    team_season_id: TeamSeasonId
    unit_type: UnitType
    logical_key: str
    revision: int
    evidence_kind: UnitEvidenceKind
    metrics: tuple[NamedMoments, ...]
    sample_weight: float
    source_confidence: Probability
    residualized_against_player_state: bool
    evidence_contract: str
    evidence_version: str
    knowledge: KnowledgeTimestamp
    source_game_id: GameId | None = None
    provider_id: str | None = None
    evidence_id: str | None = None
    evidence_observation_id: str | None = None
    provider_revision: str | None = None
    provider_schema_version: str | None = None
    parser_version: str | None = None
    raw_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_nonblank(str(self.observation_id), "unit evidence observation_id")
        _require_nonblank(str(self.team_season_id), "unit evidence team_season_id")
        _require_nonblank(self.logical_key, "unit evidence logical_key")
        _require_nonblank(self.evidence_contract, "unit evidence contract")
        _require_nonblank(self.evidence_version, "unit evidence version")
        if self.revision < 1:
            raise ValueError("unit evidence revision must be >= 1")
        if not math.isfinite(self.sample_weight) or self.sample_weight <= 0.0:
            raise ValueError("unit evidence sample_weight must be finite and > 0")
        if not self.metrics:
            raise ValueError("unit evidence requires at least one metric")
        _canonical_named_moments(self.metrics)
        if (
            self.evidence_kind in _RESIDUALIZED_KINDS
            and not self.residualized_against_player_state
        ):
            raise ValueError(
                "role compatibility, synergy, and recent performance unit evidence "
                "must be residualized against Player State"
            )
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
    def metrics_sha256(self) -> str:
        encoded = canonical_state_json(_canonical_named_moments(self.metrics)).encode()
        return hashlib.sha256(encoded).hexdigest()

    @property
    def payload_sha256(self) -> str:
        payload = {
            "team_season_id": str(self.team_season_id),
            "source_game_id": (
                str(self.source_game_id) if self.source_game_id is not None else None
            ),
            "unit_type": self.unit_type.value,
            "logical_key": self.logical_key,
            "revision": self.revision,
            "evidence_kind": self.evidence_kind.value,
            "metrics_sha256": self.metrics_sha256,
            "sample_weight": self.sample_weight,
            "source_confidence": self.source_confidence.value,
            "residualized_against_player_state": self.residualized_against_player_state,
            "evidence_contract": self.evidence_contract,
            "evidence_version": self.evidence_version,
        }
        return hashlib.sha256(canonical_state_json(payload).encode()).hexdigest()

    def to_pit_input_ref(self) -> PITInputRef:
        return PITInputRef(
            input_kind=PITInputKind.OTHER,
            input_id=str(self.observation_id),
            available_at=self.knowledge.available_at,
            availability_method=self.knowledge.availability_method,
            availability_confidence=self.knowledge.availability_confidence,
            source_table="unit_state_evidence_observations",
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
class UnitStateDimension:
    metrics: tuple[NamedMoments, ...]
    evidence_count: int
    effective_weight: float
    low_sample: bool

    def __post_init__(self) -> None:
        if self.evidence_count < 0:
            raise ValueError("unit state evidence_count cannot be negative")
        if not math.isfinite(self.effective_weight) or self.effective_weight < 0.0:
            raise ValueError("unit state effective_weight must be finite and non-negative")
        _canonical_named_moments(self.metrics)


@dataclass(frozen=True, slots=True)
class PosteriorUnitConfiguration:
    configuration_id: UnitConfigurationId
    prior_probability: Probability
    posterior_probability: Probability
    members: tuple[UnitMemberAssignment, ...]


@dataclass(frozen=True, slots=True)
class UnitHealthState:
    expected_active_share: NumericMoments
    expected_participation_share: NumericMoments
    expected_effectiveness_if_participating: NumericMoments
    expected_early_exit_share: NumericMoments


@dataclass(frozen=True, slots=True)
class UnitStatePayload:
    team_season_id: TeamSeasonId
    game_id: GameId
    unit_type: UnitType
    member_distribution: tuple[PosteriorUnitConfiguration, ...]
    intrinsic_quality_state: UnitStateDimension
    member_form_state: UnitStateDimension
    continuity_state: UnitStateDimension
    experience_together_state: UnitStateDimension
    role_compatibility_state: UnitStateDimension
    synergy_state: UnitStateDimension
    recent_performance_residual_state: UnitStateDimension
    health_state: UnitHealthState
    scheme_state_id: StateSnapshotId | None
    scheme_fit_state: UnitStateDimension
    player_state_ids: tuple[StateSnapshotId, ...]


@dataclass(frozen=True, slots=True)
class UnitStateEstimatorConfig:
    version: str = "NFL_UNIT_STATE_BASELINE_V1"
    continuity_half_life_days: float = 180.0
    experience_half_life_days: float = 365.0
    role_compatibility_half_life_days: float = 90.0
    synergy_half_life_days: float = 90.0
    recent_performance_half_life_days: float = 35.0
    low_sample_effective_weight: float = 2.0

    def __post_init__(self) -> None:
        _require_nonblank(self.version, "unit state estimator version")
        for value in (
            self.continuity_half_life_days,
            self.experience_half_life_days,
            self.role_compatibility_half_life_days,
            self.synergy_half_life_days,
            self.recent_performance_half_life_days,
            self.low_sample_effective_weight,
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError("unit state estimator weights must be finite and > 0")

    def half_life_days(self, kind: UnitEvidenceKind) -> float:
        return {
            UnitEvidenceKind.CONTINUITY: self.continuity_half_life_days,
            UnitEvidenceKind.EXPERIENCE_TOGETHER: self.experience_half_life_days,
            UnitEvidenceKind.ROLE_COMPATIBILITY: self.role_compatibility_half_life_days,
            UnitEvidenceKind.SYNERGY: self.synergy_half_life_days,
            UnitEvidenceKind.RECENT_PERFORMANCE: self.recent_performance_half_life_days,
        }[kind]


DEFAULT_UNIT_STATE_ESTIMATOR_CONFIG = UnitStateEstimatorConfig()


def _empty_dimension() -> UnitStateDimension:
    return UnitStateDimension(metrics=(), evidence_count=0, effective_weight=0.0, low_sample=True)


def _validate_configuration_observations(
    observations: tuple[UnitConfigurationObservation, ...],
    *,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    unit_type: UnitType,
    as_of: datetime,
) -> UnitConfigurationObservation:
    if not observations:
        raise ValueError("Unit State requires at least one configuration observation")
    for observation in observations:
        if observation.team_season_id != team_season_id:
            raise ValueError("unit configuration belongs to a different team")
        if observation.game_id != game_id:
            raise ValueError("unit configuration belongs to a different game")
        if observation.unit_type is not unit_type:
            raise ValueError("unit configuration belongs to a different unit type")
        if observation.knowledge.available_at > as_of:
            raise ValueError("unit configuration cannot be available after Unit State as_of")
        if (
            observation.availability_basis
            is not UnitConfigurationAvailabilityBasis.ROLE_PRIOR_ONLY
        ):
            raise ValueError("Unit State V1 requires a health-neutral role prior")
    hashes = {observation.distribution_sha256 for observation in observations}
    if len(hashes) != 1:
        raise ValueError("conflicting unit configuration distributions at PIT cutoff")
    return min(observations, key=lambda item: str(item.observation_id))


def _validate_player_snapshots(
    player_snapshots: tuple[StateSnapshotEnvelope[PlayerStatePayload], ...],
    *,
    required_player_ids: set[PlayerId],
    team_season_id: TeamSeasonId,
    game_id: GameId,
    as_of: datetime,
) -> dict[PlayerId, StateSnapshotEnvelope[PlayerStatePayload]]:
    by_player: dict[PlayerId, StateSnapshotEnvelope[PlayerStatePayload]] = {}
    for snapshot in player_snapshots:
        verify_state_snapshot_identity(snapshot)
        if snapshot.state_type is not StateType.PLAYER:
            raise ValueError("Unit State parents must be Player State snapshots")
        if snapshot.subject_type is not StateSubjectType.PLAYER:
            raise ValueError("Unit State parent must have PLAYER subject type")
        if snapshot.team_season_id != team_season_id:
            raise ValueError("Player State parent belongs to a different team")
        if snapshot.game_id != game_id:
            raise ValueError("Player State parent belongs to a different game")
        if snapshot.as_of > as_of:
            raise ValueError("Player State parent cannot be later than Unit State as_of")
        payload = snapshot.state_payload
        if payload.player_id in by_player:
            raise ValueError("Unit State cannot receive duplicate Player State parents")
        if snapshot.subject_id != str(payload.player_id):
            raise ValueError("Player State subject identity disagrees with payload")
        by_player[payload.player_id] = snapshot
    if set(by_player) != required_player_ids:
        raise ValueError(
            "Unit State Player State parents must exactly match configuration members"
        )
    return by_player


def _posterior_configurations(
    observation: UnitConfigurationObservation,
    player_map: dict[PlayerId, StateSnapshotEnvelope[PlayerStatePayload]],
) -> tuple[PosteriorUnitConfiguration, ...]:
    raw_weights: list[tuple[UnitConfigurationAlternative, float]] = []
    for alternative in observation.alternatives:
        weight = alternative.prior_probability.value
        for member in alternative.members:
            weight *= player_map[member.player_id].state_payload.availability_probability.value
        raw_weights.append((alternative, weight))
    total = math.fsum(weight for _, weight in raw_weights)
    if total <= 0.0:
        raise ValueError("no viable unit configuration remains after availability adjustment")
    posterior = [
        PosteriorUnitConfiguration(
            configuration_id=alternative.configuration_id,
            prior_probability=alternative.prior_probability,
            posterior_probability=Probability(weight / total),
            members=alternative.members,
        )
        for alternative, weight in raw_weights
    ]
    return tuple(sorted(posterior, key=lambda item: str(item.configuration_id)))


def _member_exposures(
    configurations: tuple[PosteriorUnitConfiguration, ...],
) -> dict[PlayerId, float]:
    contributions: dict[PlayerId, list[float]] = {}
    for configuration in configurations:
        probability = configuration.posterior_probability.value
        for member in configuration.members:
            contributions.setdefault(member.player_id, []).append(
                probability * member.expected_share.value
            )
    return {
        player_id: math.fsum(weights)
        for player_id, weights in contributions.items()
    }


def _aggregate_player_dimension(
    player_map: dict[PlayerId, StateSnapshotEnvelope[PlayerStatePayload]],
    exposures: dict[PlayerId, float],
    *,
    dimension_name: str,
    low_sample_threshold: float,
) -> UnitStateDimension:
    weighted_metrics: dict[str, list[tuple[NumericMoments, float]]] = {}
    contributing_players: set[PlayerId] = set()
    for player_id, exposure in exposures.items():
        payload = player_map[player_id].state_payload
        dimension = getattr(payload, dimension_name)
        if not isinstance(dimension, PlayerStateDimension):
            raise TypeError("Player State dimension contract is invalid")
        if exposure <= 0.0 or not dimension.metrics:
            continue
        contributing_players.add(player_id)
        for metric in dimension.metrics:
            weighted_metrics.setdefault(metric.name, []).append((metric.estimate, exposure))

    metrics: list[NamedMoments] = []
    metric_weights: list[float] = []
    for name in sorted(weighted_metrics):
        members = weighted_metrics[name]
        total_weight = math.fsum(weight for _, weight in members)
        if total_weight <= 0.0:
            continue
        metric_weights.append(total_weight)
        mean = math.fsum(estimate.mean * weight for estimate, weight in members) / total_weight
        variance = math.fsum(
            weight * (estimate.variance + (estimate.mean - mean) ** 2)
            for estimate, weight in members
        ) / total_weight
        metrics.append(NamedMoments(name=name, estimate=NumericMoments(mean, variance)))
    effective_weight = math.fsum(exposures[player_id] for player_id in contributing_players)
    return UnitStateDimension(
        metrics=tuple(metrics),
        evidence_count=len(contributing_players),
        effective_weight=effective_weight,
        low_sample=(
            not metrics
            or effective_weight < low_sample_threshold
            or math.fsum(metric_weights) <= 0.0
        ),
    )


def _unit_evidence_weight(
    observation: UnitStateEvidenceObservation,
    *,
    as_of: datetime,
    config: UnitStateEstimatorConfig,
) -> float:
    age_days = max(
        0.0,
        (as_of - observation.knowledge.available_at).total_seconds() / 86400.0,
    )
    recency_weight = math.exp2(-age_days / config.half_life_days(observation.evidence_kind))
    return observation.sample_weight * observation.source_confidence.value * recency_weight


def _aggregate_unit_evidence(
    evidence: tuple[UnitStateEvidenceObservation, ...],
    *,
    kind: UnitEvidenceKind,
    as_of: datetime,
    config: UnitStateEstimatorConfig,
) -> UnitStateDimension:
    selected = [observation for observation in evidence if observation.evidence_kind is kind]
    weighted_metrics: dict[str, list[tuple[NumericMoments, float]]] = {}
    weights: list[float] = []
    for observation in selected:
        weight = _unit_evidence_weight(observation, as_of=as_of, config=config)
        if weight <= 0.0:
            continue
        weights.append(weight)
        for metric in observation.metrics:
            weighted_metrics.setdefault(metric.name, []).append((metric.estimate, weight))

    metrics: list[NamedMoments] = []
    for name in sorted(weighted_metrics):
        members = weighted_metrics[name]
        total_weight = math.fsum(weight for _, weight in members)
        mean = math.fsum(estimate.mean * weight for estimate, weight in members) / total_weight
        variance = math.fsum(
            weight * (estimate.variance + (estimate.mean - mean) ** 2)
            for estimate, weight in members
        ) / total_weight
        metrics.append(NamedMoments(name=name, estimate=NumericMoments(mean, variance)))
    effective_weight = math.fsum(weights)
    return UnitStateDimension(
        metrics=tuple(metrics),
        evidence_count=len(weights),
        effective_weight=effective_weight,
        low_sample=(not metrics or effective_weight < config.low_sample_effective_weight),
    )


def _weighted_moments(
    values: tuple[tuple[NumericMoments, float], ...],
) -> NumericMoments:
    total_weight = math.fsum(weight for _, weight in values)
    if total_weight <= 0.0:
        return NumericMoments(0.0, 0.0)
    mean = math.fsum(value.mean * weight for value, weight in values) / total_weight
    variance = math.fsum(
        weight * (value.variance + (value.mean - mean) ** 2)
        for value, weight in values
    ) / total_weight
    return NumericMoments(mean, variance)


def _health_state(
    player_map: dict[PlayerId, StateSnapshotEnvelope[PlayerStatePayload]],
    exposures: dict[PlayerId, float],
) -> UnitHealthState:
    active_values: list[tuple[NumericMoments, float]] = []
    participation_values: list[tuple[NumericMoments, float]] = []
    effectiveness_values: list[tuple[NumericMoments, float]] = []
    early_exit_values: list[tuple[NumericMoments, float]] = []
    for player_id, exposure in exposures.items():
        payload = player_map[player_id].state_payload
        active = payload.availability_probability.value
        active_values.append(
            (NumericMoments(active, active * (1.0 - active)), exposure)
        )
        participation = payload.participation_if_active
        unconditional_participation_mean = active * participation.mean
        participation_values.append(
            (
                NumericMoments(
                    unconditional_participation_mean,
                    active * participation.variance
                    + active * (1.0 - active) * participation.mean**2,
                ),
                exposure,
            )
        )
        effectiveness_values.append(
            (payload.effectiveness_if_participates, exposure * active * participation.mean)
        )
        early_exit = payload.early_exit_probability_if_active.value
        unconditional_early_exit = active * early_exit
        early_exit_values.append(
            (
                NumericMoments(
                    unconditional_early_exit,
                    unconditional_early_exit * (1.0 - unconditional_early_exit),
                ),
                exposure,
            )
        )
    return UnitHealthState(
        expected_active_share=_weighted_moments(tuple(active_values)),
        expected_participation_share=_weighted_moments(tuple(participation_values)),
        expected_effectiveness_if_participating=_weighted_moments(
            tuple(effectiveness_values)
        ),
        expected_early_exit_share=_weighted_moments(tuple(early_exit_values)),
    )


def _coverage(
    *,
    intrinsic: UnitStateDimension,
    member_form: UnitStateDimension,
    continuity: UnitStateDimension,
    experience: UnitStateDimension,
    role_compatibility: UnitStateDimension,
    synergy: UnitStateDimension,
    recent_performance: UnitStateDimension,
) -> StateCoverage:
    expected = (
        "member_distribution",
        "intrinsic_quality_state",
        "member_form_state",
        "continuity_state",
        "experience_together_state",
        "role_compatibility_state",
        "synergy_state",
        "recent_performance_residual_state",
        "health_state",
        "scheme_fit_state",
    )
    present = {"member_distribution", "health_state"}
    dimensions = (
        ("intrinsic_quality_state", intrinsic),
        ("member_form_state", member_form),
        ("continuity_state", continuity),
        ("experience_together_state", experience),
        ("role_compatibility_state", role_compatibility),
        ("synergy_state", synergy),
        ("recent_performance_residual_state", recent_performance),
    )
    for name, dimension in dimensions:
        if dimension.metrics:
            present.add(name)
    present_fields = tuple(field for field in expected if field in present)
    missing_fields = tuple(field for field in expected if field not in present)
    return StateCoverage(
        expected_fields=expected,
        present_fields=present_fields,
        missing_fields=missing_fields,
    )


def _uncertainty(
    *,
    configurations: tuple[PosteriorUnitConfiguration, ...],
    health: UnitHealthState,
    dimensions: tuple[tuple[str, UnitStateDimension], ...],
) -> StateUncertainty:
    unknowns: list[UnknownQuantity] = []
    for name, dimension in dimensions:
        if not dimension.metrics:
            unknowns.append(
                UnknownQuantity(
                    name=name,
                    reason=MissingnessReason.DATA_UNAVAILABLE,
                    detail="No PIT-safe evidence supports this Unit State dimension.",
                )
            )
        elif dimension.low_sample:
            unknowns.append(
                UnknownQuantity(
                    name=f"{name}_low_sample",
                    reason=MissingnessReason.INSUFFICIENT_SAMPLE,
                    detail="Unit State evidence remains below the V1 weight threshold.",
                )
            )
    unknowns.append(
        UnknownQuantity(
            name="scheme_fit_state",
            reason=MissingnessReason.DATA_UNAVAILABLE,
            detail="Scheme fit is deferred until the F-9 coaching/scheme parent exists.",
        )
    )
    categorical = NamedCategoricalDistribution(
        name="unit_configuration",
        estimate=CategoricalDistribution(
            entries=tuple(
                CategoryProbability(
                    category=str(configuration.configuration_id),
                    probability=configuration.posterior_probability,
                )
                for configuration in configurations
            )
        ),
    )
    return StateUncertainty(
        moments=(
            NamedMoments("expected_active_share", health.expected_active_share),
            NamedMoments(
                "expected_participation_share",
                health.expected_participation_share,
            ),
            NamedMoments(
                "expected_effectiveness_if_participating",
                health.expected_effectiveness_if_participating,
            ),
            NamedMoments(
                "expected_early_exit_share",
                health.expected_early_exit_share,
            ),
        ),
        categorical=(categorical,),
        unknowns=tuple(unknowns),
    )


def build_unit_state_snapshot(
    *,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    unit_type: UnitType,
    as_of: datetime,
    configuration_observations: tuple[UnitConfigurationObservation, ...],
    unit_evidence: tuple[UnitStateEvidenceObservation, ...],
    player_snapshots: tuple[StateSnapshotEnvelope[PlayerStatePayload], ...],
    config: UnitStateEstimatorConfig = DEFAULT_UNIT_STATE_ESTIMATOR_CONFIG,
    created_at: datetime,
) -> StateSnapshotEnvelope[UnitStatePayload]:
    """Build an immutable F-8 Unit State from exact Player State parents."""

    _require_aware(as_of, "Unit State as_of")
    _require_aware(created_at, "Unit State created_at")
    representative = _validate_configuration_observations(
        configuration_observations,
        team_season_id=team_season_id,
        game_id=game_id,
        unit_type=unit_type,
        as_of=as_of,
    )
    required_player_ids = {
        member.player_id
        for alternative in representative.alternatives
        for member in alternative.members
    }
    player_map = _validate_player_snapshots(
        player_snapshots,
        required_player_ids=required_player_ids,
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
    )
    for observation in unit_evidence:
        if observation.team_season_id != team_season_id:
            raise ValueError("unit evidence belongs to a different team")
        if observation.unit_type is not unit_type:
            raise ValueError("unit evidence belongs to a different unit type")
        if observation.knowledge.available_at > as_of:
            raise ValueError("unit evidence cannot be available after Unit State as_of")
        if observation.source_game_id == game_id:
            raise ValueError("current pregame target game cannot enter Unit State evidence")

    configurations = _posterior_configurations(representative, player_map)
    exposures = _member_exposures(configurations)
    intrinsic = _aggregate_player_dimension(
        player_map,
        exposures,
        dimension_name="talent_state",
        low_sample_threshold=config.low_sample_effective_weight,
    )
    member_form = _aggregate_player_dimension(
        player_map,
        exposures,
        dimension_name="form_state",
        low_sample_threshold=config.low_sample_effective_weight,
    )
    continuity = _aggregate_unit_evidence(
        unit_evidence,
        kind=UnitEvidenceKind.CONTINUITY,
        as_of=as_of,
        config=config,
    )
    experience = _aggregate_unit_evidence(
        unit_evidence,
        kind=UnitEvidenceKind.EXPERIENCE_TOGETHER,
        as_of=as_of,
        config=config,
    )
    role_compatibility = _aggregate_unit_evidence(
        unit_evidence,
        kind=UnitEvidenceKind.ROLE_COMPATIBILITY,
        as_of=as_of,
        config=config,
    )
    synergy = _aggregate_unit_evidence(
        unit_evidence,
        kind=UnitEvidenceKind.SYNERGY,
        as_of=as_of,
        config=config,
    )
    recent_performance = _aggregate_unit_evidence(
        unit_evidence,
        kind=UnitEvidenceKind.RECENT_PERFORMANCE,
        as_of=as_of,
        config=config,
    )
    health = _health_state(player_map, exposures)
    scheme_fit = _empty_dimension()
    ordered_player_snapshots = tuple(
        sorted(player_snapshots, key=lambda snapshot: str(snapshot.snapshot_id))
    )
    payload = UnitStatePayload(
        team_season_id=team_season_id,
        game_id=game_id,
        unit_type=unit_type,
        member_distribution=configurations,
        intrinsic_quality_state=intrinsic,
        member_form_state=member_form,
        continuity_state=continuity,
        experience_together_state=experience,
        role_compatibility_state=role_compatibility,
        synergy_state=synergy,
        recent_performance_residual_state=recent_performance,
        health_state=health,
        scheme_state_id=None,
        scheme_fit_state=scheme_fit,
        player_state_ids=tuple(snapshot.snapshot_id for snapshot in ordered_player_snapshots),
    )
    dimensions = (
        ("intrinsic_quality_state", intrinsic),
        ("member_form_state", member_form),
        ("continuity_state", continuity),
        ("experience_together_state", experience),
        ("role_compatibility_state", role_compatibility),
        ("synergy_state", synergy),
        ("recent_performance_residual_state", recent_performance),
    )
    inputs = tuple(
        observation.to_pit_input_ref() for observation in configuration_observations
    ) + tuple(observation.to_pit_input_ref() for observation in unit_evidence)
    subject_id = f"unit:{team_season_id}:{game_id}:{unit_type.value}"
    return build_state_snapshot(
        state_type=StateType.UNIT,
        subject_type=StateSubjectType.UNIT,
        subject_id=subject_id,
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
        calculation_contract="NFL_UNIT_STATE_V1",
        model_version=config.version,
        state_payload=payload,
        uncertainty=_uncertainty(
            configurations=configurations,
            health=health,
            dimensions=dimensions,
        ),
        coverage=_coverage(
            intrinsic=intrinsic,
            member_form=member_form,
            continuity=continuity,
            experience=experience,
            role_compatibility=role_compatibility,
            synergy=synergy,
            recent_performance=recent_performance,
        ),
        input_observations=inputs,
        parent_snapshots=ordered_player_snapshots,
        created_at=created_at,
    )
