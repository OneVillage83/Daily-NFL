"""F-7 player-state contracts and deterministic V1 estimation."""

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
    PlayerStateEvidenceObservationId,
    StateSnapshotId,
    TeamSeasonId,
)
from daily_nfl.pit import PITInputKind, PITInputRef
from daily_nfl.state.contracts import (
    StateCoverage,
    StateSnapshotEnvelope,
    StateSubjectType,
    StateType,
)
from daily_nfl.state.injury import InjuryAvailabilityState
from daily_nfl.state.snapshot import (
    build_state_snapshot,
    canonical_state_json,
    verify_state_snapshot_identity,
)
from daily_nfl.state.uncertainty import (
    MissingnessReason,
    NamedMoments,
    NamedProbability,
    NumericMoments,
    Probability,
    StateUncertainty,
    UnknownQuantity,
)


class PlayerPosition(StrEnum):
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    OT = "OT"
    OG = "OG"
    C = "C"
    EDGE = "EDGE"
    DT = "DT"
    LB = "LB"
    CB = "CB"
    S = "S"
    K = "K"
    P = "P"
    RETURNER = "RETURNER"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class PlayerEvidenceKind(StrEnum):
    POSITION = "POSITION"
    TALENT = "TALENT"
    PERFORMANCE = "PERFORMANCE"
    ROLE = "ROLE"
    WORKLOAD = "WORKLOAD"
    POSITION_SPECIFIC = "POSITION_SPECIFIC"


CANONICAL_POSITION_METRICS: dict[PlayerPosition, tuple[str, ...]] = {
    PlayerPosition.QB: (
        "passing_talent",
        "decision_quality",
        "accuracy",
        "pressure_response",
        "sack_avoidance",
        "scramble_value",
        "designed_run_value",
        "explosive_play_generation",
        "turnover_avoidance",
        "short_passing_profile",
        "intermediate_passing_profile",
        "deep_passing_profile",
        "play_action_performance",
        "rpo_performance",
        "timing",
        "mobility_state",
    ),
    PlayerPosition.RB: (
        "rushing_efficiency",
        "receiving_value",
        "pass_protection",
        "explosive_run_generation",
        "short_yardage_value",
        "goal_line_value",
    ),
    PlayerPosition.WR: (
        "route_efficiency",
        "target_earning",
        "catch_efficiency",
        "yac_value",
        "deep_receiving_value",
        "blocking_value",
    ),
    PlayerPosition.TE: (
        "route_efficiency",
        "target_earning",
        "catch_efficiency",
        "yac_value",
        "inline_blocking",
        "pass_protection",
    ),
    PlayerPosition.OT: ("pass_protection", "run_blocking", "penalty_avoidance"),
    PlayerPosition.OG: ("pass_protection", "run_blocking", "penalty_avoidance"),
    PlayerPosition.C: ("pass_protection", "run_blocking", "penalty_avoidance"),
    PlayerPosition.EDGE: (
        "pass_rush_value",
        "pressure_generation",
        "run_defense",
        "contain_value",
    ),
    PlayerPosition.DT: ("interior_rush_value", "run_defense", "double_team_response"),
    PlayerPosition.LB: ("run_defense", "coverage_value", "blitz_value", "tackle_value"),
    PlayerPosition.CB: (
        "coverage_value",
        "target_suppression",
        "ball_disruption",
        "tackle_value",
    ),
    PlayerPosition.S: ("coverage_value", "range", "run_support", "tackle_value"),
    PlayerPosition.K: ("field_goal_value", "extra_point_value", "kickoff_value"),
    PlayerPosition.P: ("punt_distance_value", "punt_placement_value", "hang_time_value"),
    PlayerPosition.RETURNER: ("punt_return_value", "kick_return_value", "ball_security"),
    PlayerPosition.OTHER: (),
    PlayerPosition.UNKNOWN: (),
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


def _metric_names(metrics: tuple[NamedMoments, ...]) -> list[str]:
    return [metric.name for metric in metrics]


def _canonical_metrics(metrics: tuple[NamedMoments, ...]) -> tuple[NamedMoments, ...]:
    return tuple(sorted(metrics, key=lambda metric: metric.name))


def player_evidence_metrics_sha256(metrics: tuple[NamedMoments, ...]) -> str:
    encoded = canonical_state_json(_canonical_metrics(metrics)).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class PlayerStateEvidenceObservation:
    """Append-only PIT observation used to estimate one dimension of player state."""

    observation_id: PlayerStateEvidenceObservationId
    player_id: PlayerId
    logical_key: str
    revision: int
    position: PlayerPosition
    evidence_kind: PlayerEvidenceKind
    metrics: tuple[NamedMoments, ...]
    sample_weight: float
    source_confidence: Probability
    evidence_contract: str
    evidence_version: str
    knowledge: KnowledgeTimestamp
    team_season_id: TeamSeasonId | None = None
    source_game_id: GameId | None = None
    provider_id: str | None = None
    evidence_id: str | None = None
    evidence_observation_id: str | None = None
    provider_revision: str | None = None
    provider_schema_version: str | None = None
    parser_version: str | None = None
    raw_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_nonblank(str(self.observation_id), "player evidence observation_id")
        _require_nonblank(str(self.player_id), "player_id")
        _require_nonblank(self.logical_key, "player evidence logical_key")
        _require_nonblank(self.evidence_contract, "player evidence contract")
        _require_nonblank(self.evidence_version, "player evidence version")
        if self.revision < 1:
            raise ValueError("player evidence revision must be >= 1")
        if not math.isfinite(self.sample_weight) or self.sample_weight <= 0.0:
            raise ValueError("player evidence sample_weight must be finite and > 0")
        names = _metric_names(self.metrics)
        if len(names) != len(set(names)):
            raise ValueError("player evidence metric names cannot repeat")
        if self.evidence_kind is not PlayerEvidenceKind.POSITION and not self.metrics:
            raise ValueError("non-position player evidence requires at least one metric")
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
        return player_evidence_metrics_sha256(self.metrics)

    @property
    def payload_sha256(self) -> str:
        return player_evidence_payload_sha256(self)

    def to_pit_input_ref(self) -> PITInputRef:
        return PITInputRef(
            input_kind=PITInputKind.OTHER,
            input_id=str(self.observation_id),
            available_at=self.knowledge.available_at,
            availability_method=self.knowledge.availability_method,
            availability_confidence=self.knowledge.availability_confidence,
            source_table="player_state_evidence_observations",
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


def player_evidence_payload_sha256(observation: PlayerStateEvidenceObservation) -> str:
    payload = {
        "player_id": str(observation.player_id),
        "logical_key": observation.logical_key,
        "revision": observation.revision,
        "team_season_id": (
            str(observation.team_season_id) if observation.team_season_id is not None else None
        ),
        "source_game_id": (
            str(observation.source_game_id) if observation.source_game_id is not None else None
        ),
        "position": observation.position.value,
        "evidence_kind": observation.evidence_kind.value,
        "metrics": _canonical_metrics(observation.metrics),
        "sample_weight": observation.sample_weight,
        "source_confidence": observation.source_confidence.value,
        "evidence_contract": observation.evidence_contract,
        "evidence_version": observation.evidence_version,
    }
    encoded = canonical_state_json(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class PlayerStateDimension:
    metrics: tuple[NamedMoments, ...]
    evidence_count: int
    effective_weight: float
    low_sample: bool

    def __post_init__(self) -> None:
        if self.evidence_count < 0:
            raise ValueError("player state evidence_count cannot be negative")
        if not math.isfinite(self.effective_weight) or self.effective_weight < 0.0:
            raise ValueError("player state effective_weight must be finite and non-negative")
        names = _metric_names(self.metrics)
        if len(names) != len(set(names)):
            raise ValueError("player state dimension metric names cannot repeat")


@dataclass(frozen=True, slots=True)
class PlayerStatePayload:
    player_id: PlayerId
    team_season_id: TeamSeasonId
    game_id: GameId
    position: PlayerPosition
    talent_state: PlayerStateDimension
    form_state: PlayerStateDimension
    role_state: PlayerStateDimension
    workload_state: PlayerStateDimension
    position_specific_state: PlayerStateDimension
    health_snapshot_id: StateSnapshotId
    availability_probability: Probability
    participation_if_active: NumericMoments
    effectiveness_if_participates: NumericMoments
    early_exit_probability_if_active: Probability
    fatigue_estimate: NumericMoments | None


@dataclass(frozen=True, slots=True)
class PlayerStateEstimatorConfig:
    """Versioned V1 weighting assumptions; they are replaceable model choices."""

    version: str = "NFL_PLAYER_STATE_BASELINE_V1"
    talent_half_life_days: float = 365.0
    performance_half_life_days: float = 35.0
    role_half_life_days: float = 21.0
    workload_half_life_days: float = 14.0
    position_specific_half_life_days: float = 35.0
    low_sample_effective_weight: float = 2.0

    def __post_init__(self) -> None:
        _require_nonblank(self.version, "player state estimator version")
        for value in (
            self.talent_half_life_days,
            self.performance_half_life_days,
            self.role_half_life_days,
            self.workload_half_life_days,
            self.position_specific_half_life_days,
            self.low_sample_effective_weight,
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError("player state estimator weights must be finite and > 0")

    def half_life_days(self, kind: PlayerEvidenceKind) -> float:
        return {
            PlayerEvidenceKind.TALENT: self.talent_half_life_days,
            PlayerEvidenceKind.PERFORMANCE: self.performance_half_life_days,
            PlayerEvidenceKind.ROLE: self.role_half_life_days,
            PlayerEvidenceKind.WORKLOAD: self.workload_half_life_days,
            PlayerEvidenceKind.POSITION_SPECIFIC: self.position_specific_half_life_days,
            PlayerEvidenceKind.POSITION: self.role_half_life_days,
        }[kind]


DEFAULT_PLAYER_STATE_ESTIMATOR_CONFIG = PlayerStateEstimatorConfig()


def canonical_position_metrics(position: PlayerPosition) -> tuple[str, ...]:
    """Return the locked V1 extension vocabulary for one player position family."""

    return CANONICAL_POSITION_METRICS[position]


def resolve_player_position(
    evidence: tuple[PlayerStateEvidenceObservation, ...],
    *,
    team_season_id: TeamSeasonId,
) -> PlayerPosition:
    """Resolve current position from the latest current-team POSITION evidence."""

    candidates = [
        observation
        for observation in evidence
        if observation.evidence_kind is PlayerEvidenceKind.POSITION
        and observation.team_season_id == team_season_id
    ]
    if not candidates:
        return PlayerPosition.UNKNOWN
    latest_at = max(observation.knowledge.available_at for observation in candidates)
    latest = [
        observation for observation in candidates if observation.knowledge.available_at == latest_at
    ]
    positions = {observation.position for observation in latest}
    if len(positions) != 1:
        raise ValueError("conflicting current player positions at the same PIT timestamp")
    return next(iter(positions))


def _observation_weight(
    observation: PlayerStateEvidenceObservation,
    *,
    as_of: datetime,
    config: PlayerStateEstimatorConfig,
) -> float:
    age_days = max(
        0.0,
        (as_of - observation.knowledge.available_at).total_seconds() / 86400.0,
    )
    recency_weight = math.exp2(
        -age_days / config.half_life_days(observation.evidence_kind)
    )
    return observation.sample_weight * observation.source_confidence.value * recency_weight


def _aggregate_dimension(
    observations: tuple[PlayerStateEvidenceObservation, ...],
    *,
    as_of: datetime,
    config: PlayerStateEstimatorConfig,
) -> PlayerStateDimension:
    weighted_metrics: dict[str, list[tuple[NumericMoments, float]]] = {}
    contributing_weights: list[float] = []
    contributing_observations = 0
    for observation in observations:
        weight = _observation_weight(observation, as_of=as_of, config=config)
        if weight <= 0.0:
            continue
        contributing_weights.append(weight)
        contributing_observations += 1
        for metric in observation.metrics:
            weighted_metrics.setdefault(metric.name, []).append((metric.estimate, weight))

    effective_weight = math.fsum(contributing_weights)
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

    return PlayerStateDimension(
        metrics=tuple(metrics),
        evidence_count=contributing_observations,
        effective_weight=effective_weight,
        low_sample=effective_weight < config.low_sample_effective_weight,
    )


def _dimension_evidence(
    evidence: tuple[PlayerStateEvidenceObservation, ...],
    *,
    kind: PlayerEvidenceKind,
    team_season_id: TeamSeasonId,
    position: PlayerPosition,
) -> tuple[PlayerStateEvidenceObservation, ...]:
    selected: list[PlayerStateEvidenceObservation] = []
    for observation in evidence:
        if observation.evidence_kind is not kind:
            continue
        if kind is PlayerEvidenceKind.TALENT:
            selected.append(observation)
            continue
        if observation.team_season_id not in (None, team_season_id):
            continue
        if kind is PlayerEvidenceKind.POSITION_SPECIFIC:
            if observation.position not in (PlayerPosition.UNKNOWN, position):
                continue
        selected.append(observation)
    return tuple(selected)


def _coverage(
    *,
    position: PlayerPosition,
    talent: PlayerStateDimension,
    form: PlayerStateDimension,
    role: PlayerStateDimension,
    workload: PlayerStateDimension,
    position_specific: PlayerStateDimension,
) -> StateCoverage:
    expected = (
        "position",
        "talent_state",
        "form_state",
        "role_state",
        "health_state",
        "workload_state",
        "fatigue_state",
        "position_specific_state",
        "availability_distribution",
        "participation_distribution",
        "effectiveness_distribution",
    )
    present = {
        "health_state",
        "availability_distribution",
        "participation_distribution",
        "effectiveness_distribution",
    }
    if position is not PlayerPosition.UNKNOWN:
        present.add("position")
    if talent.metrics:
        present.add("talent_state")
    if form.metrics:
        present.add("form_state")
    if role.metrics:
        present.add("role_state")
    if workload.metrics:
        present.add("workload_state")
    if position_specific.metrics:
        present.add("position_specific_state")
    present_fields = tuple(field for field in expected if field in present)
    missing_fields = tuple(field for field in expected if field not in present)
    return StateCoverage(
        expected_fields=expected,
        present_fields=present_fields,
        missing_fields=missing_fields,
    )


def _state_uncertainty(
    *,
    position: PlayerPosition,
    talent: PlayerStateDimension,
    form: PlayerStateDimension,
    role: PlayerStateDimension,
    workload: PlayerStateDimension,
    position_specific: PlayerStateDimension,
    health: InjuryAvailabilityState,
) -> StateUncertainty:
    unknowns: list[UnknownQuantity] = []
    dimensions = (
        ("talent_state", talent),
        ("form_state", form),
        ("role_state", role),
        ("workload_state", workload),
        ("position_specific_state", position_specific),
    )
    for name, dimension in dimensions:
        if not dimension.metrics:
            unknowns.append(
                UnknownQuantity(
                    name=name,
                    reason=MissingnessReason.DATA_UNAVAILABLE,
                    detail="No PIT-safe evidence supported this player-state dimension.",
                )
            )
        elif dimension.low_sample:
            unknowns.append(
                UnknownQuantity(
                    name=f"{name}_low_sample",
                    reason=MissingnessReason.INSUFFICIENT_SAMPLE,
                    detail="Evidence exists but effective V1 weight remains below the threshold.",
                )
            )
    if position is PlayerPosition.UNKNOWN:
        unknowns.append(
            UnknownQuantity(
                name="position",
                reason=MissingnessReason.DATA_UNAVAILABLE,
                detail="Current player position is not resolved at this PIT cutoff.",
            )
        )
    unknowns.append(
        UnknownQuantity(
            name="fatigue_state",
            reason=MissingnessReason.UNKNOWN,
            detail=(
                "V1 preserves workload evidence but does not assume an unvalidated causal "
                "fatigue penalty."
            ),
        )
    )
    return StateUncertainty(
        probabilities=(
            NamedProbability("availability", health.availability_probability),
            NamedProbability("early_exit_if_active", health.early_exit_probability_if_active),
        ),
        moments=(
            NamedMoments("participation_if_active", health.participation_if_active),
            NamedMoments(
                "effectiveness_if_participates",
                health.effectiveness_if_participates,
            ),
        ),
        unknowns=tuple(unknowns),
    )


def _validate_injury_parent(
    injury_snapshot: StateSnapshotEnvelope[InjuryAvailabilityState],
    *,
    player_id: PlayerId,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    as_of: datetime,
) -> None:
    verify_state_snapshot_identity(injury_snapshot)
    if injury_snapshot.state_type is not StateType.INJURY_AVAILABILITY:
        raise ValueError("Player State requires an injury-availability parent snapshot")
    if injury_snapshot.subject_type is not StateSubjectType.PLAYER:
        raise ValueError("injury parent must have PLAYER subject type")
    if injury_snapshot.subject_id != str(player_id):
        raise ValueError("injury parent player does not match Player State player")
    if injury_snapshot.team_season_id != team_season_id:
        raise ValueError("injury parent team does not match Player State team")
    if injury_snapshot.game_id != game_id:
        raise ValueError("injury parent game does not match Player State game")
    if injury_snapshot.as_of > as_of:
        raise ValueError("injury parent cannot be later than Player State as_of")
    health = injury_snapshot.state_payload
    if health.player_id != player_id or health.team_season_id != team_season_id:
        raise ValueError("injury parent payload identity does not match Player State")
    if health.game_id != game_id:
        raise ValueError("injury parent payload game does not match Player State")


def build_player_state_snapshot(
    *,
    player_id: PlayerId,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    as_of: datetime,
    position: PlayerPosition,
    evidence: tuple[PlayerStateEvidenceObservation, ...],
    injury_snapshot: StateSnapshotEnvelope[InjuryAvailabilityState],
    config: PlayerStateEstimatorConfig = DEFAULT_PLAYER_STATE_ESTIMATOR_CONFIG,
    created_at: datetime,
) -> StateSnapshotEnvelope[PlayerStatePayload]:
    """Build a PIT-safe F-7 state with explicit F-10 parent lineage."""

    _require_aware(as_of, "player state as_of")
    _require_aware(created_at, "player state created_at")
    _validate_injury_parent(
        injury_snapshot,
        player_id=player_id,
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
    )

    for observation in evidence:
        if observation.player_id != player_id:
            raise ValueError("player evidence belongs to a different player")
        if observation.knowledge.available_at > as_of:
            raise ValueError("player evidence cannot be available after Player State as_of")
        if observation.source_game_id == game_id:
            raise ValueError("current pregame target game cannot enter Player State evidence")
        if observation.evidence_kind is not PlayerEvidenceKind.TALENT:
            if observation.team_season_id not in (None, team_season_id):
                raise ValueError("team-conditioned player evidence belongs to a different team")
        if observation.evidence_kind is PlayerEvidenceKind.POSITION_SPECIFIC:
            if observation.position not in (PlayerPosition.UNKNOWN, position):
                raise ValueError("position-specific evidence does not match current position")

    talent = _aggregate_dimension(
        _dimension_evidence(
            evidence,
            kind=PlayerEvidenceKind.TALENT,
            team_season_id=team_season_id,
            position=position,
        ),
        as_of=as_of,
        config=config,
    )
    form = _aggregate_dimension(
        _dimension_evidence(
            evidence,
            kind=PlayerEvidenceKind.PERFORMANCE,
            team_season_id=team_season_id,
            position=position,
        ),
        as_of=as_of,
        config=config,
    )
    role = _aggregate_dimension(
        _dimension_evidence(
            evidence,
            kind=PlayerEvidenceKind.ROLE,
            team_season_id=team_season_id,
            position=position,
        ),
        as_of=as_of,
        config=config,
    )
    workload = _aggregate_dimension(
        _dimension_evidence(
            evidence,
            kind=PlayerEvidenceKind.WORKLOAD,
            team_season_id=team_season_id,
            position=position,
        ),
        as_of=as_of,
        config=config,
    )
    position_specific = _aggregate_dimension(
        _dimension_evidence(
            evidence,
            kind=PlayerEvidenceKind.POSITION_SPECIFIC,
            team_season_id=team_season_id,
            position=position,
        ),
        as_of=as_of,
        config=config,
    )

    health = injury_snapshot.state_payload
    payload = PlayerStatePayload(
        player_id=player_id,
        team_season_id=team_season_id,
        game_id=game_id,
        position=position,
        talent_state=talent,
        form_state=form,
        role_state=role,
        workload_state=workload,
        position_specific_state=position_specific,
        health_snapshot_id=injury_snapshot.snapshot_id,
        availability_probability=health.availability_probability,
        participation_if_active=health.participation_if_active,
        effectiveness_if_participates=health.effectiveness_if_participates,
        early_exit_probability_if_active=health.early_exit_probability_if_active,
        fatigue_estimate=None,
    )
    input_refs = tuple(observation.to_pit_input_ref() for observation in evidence)
    return build_state_snapshot(
        state_type=StateType.PLAYER,
        subject_type=StateSubjectType.PLAYER,
        subject_id=str(player_id),
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
        calculation_contract="NFL_PLAYER_STATE_V1",
        model_version=config.version,
        state_payload=payload,
        uncertainty=_state_uncertainty(
            position=position,
            talent=talent,
            form=form,
            role=role,
            workload=workload,
            position_specific=position_specific,
            health=health,
        ),
        coverage=_coverage(
            position=position,
            talent=talent,
            form=form,
            role=role,
            workload=workload,
            position_specific=position_specific,
        ),
        input_observations=input_refs,
        parent_snapshots=(injury_snapshot,),
        created_at=created_at,
    )
