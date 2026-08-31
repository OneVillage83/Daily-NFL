"""F-10 injury, health, availability, participation, and effectiveness state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, fields
from datetime import datetime
from enum import StrEnum

from daily_nfl.domain import (
    GameId,
    InjuryEpisodeId,
    InjuryObservationId,
    KnowledgeTimestamp,
    PlayerId,
    TeamSeasonId,
)
from daily_nfl.pit import PITInputKind, PITInputRef
from daily_nfl.state.contracts import (
    StateCoverage,
    StateSnapshotEnvelope,
    StateSubjectType,
    StateType,
)
from daily_nfl.state.snapshot import build_state_snapshot
from daily_nfl.state.uncertainty import (
    MissingnessReason,
    NamedMoments,
    NamedProbability,
    NumericMoments,
    Probability,
    StateUncertainty,
    UnknownQuantity,
)


class PracticeStatus(StrEnum):
    DID_NOT_PARTICIPATE = "DID_NOT_PARTICIPATE"
    LIMITED = "LIMITED"
    FULL = "FULL"
    UNKNOWN = "UNKNOWN"


class GameDesignation(StrEnum):
    OUT = "OUT"
    DOUBTFUL = "DOUBTFUL"
    QUESTIONABLE = "QUESTIONABLE"
    NO_DESIGNATION = "NO_DESIGNATION"
    UNKNOWN = "UNKNOWN"


class ActiveStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


class InjuryLaterality(StrEnum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    BILATERAL = "BILATERAL"
    MIDLINE = "MIDLINE"
    UNKNOWN = "UNKNOWN"


class InjuryResolutionState(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    UNKNOWN = "UNKNOWN"


def _require_aware(value: datetime | None, label: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{label} must be timezone-aware")


def _optional_text(value: str | None, label: str) -> None:
    if value is not None and not value.strip():
        raise ValueError(f"{label} cannot be blank when present")


def _require_nonblank(value: str, label: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be blank")


def _require_unit_interval(value: float, label: str) -> None:
    try:
        Probability(value)
    except ValueError as error:
        raise ValueError(f"{label} must be between 0 and 1") from error


@dataclass(frozen=True, slots=True)
class InjuryObservation:
    """Canonical append-only observation about a player's latent health state."""

    injury_observation_id: InjuryObservationId
    player_id: PlayerId
    team_season_id: TeamSeasonId
    provider_id: str
    source_id: str
    knowledge: KnowledgeTimestamp
    game_id: GameId | None = None
    reported_body_region: str | None = None
    reported_injury_description: str | None = None
    practice_status: PracticeStatus = PracticeStatus.UNKNOWN
    game_status: GameDesignation = GameDesignation.UNKNOWN
    active_status: ActiveStatus = ActiveStatus.UNKNOWN
    source_text: str | None = None
    source_confidence: Probability | None = None
    evidence_id: str | None = None
    evidence_observation_id: str | None = None
    provider_revision: str | None = None
    provider_schema_version: str | None = None
    parser_version: str | None = None
    raw_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_nonblank(str(self.injury_observation_id), "injury_observation_id")
        _require_nonblank(str(self.player_id), "player_id")
        _require_nonblank(str(self.team_season_id), "team_season_id")
        _require_nonblank(self.provider_id, "provider_id")
        _require_nonblank(self.source_id, "source_id")
        if self.game_id is not None:
            _require_nonblank(str(self.game_id), "game_id")
        for value, label in (
            (self.reported_body_region, "reported_body_region"),
            (self.reported_injury_description, "reported_injury_description"),
            (self.source_text, "source_text"),
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

    def to_pit_input_ref(self) -> PITInputRef:
        return PITInputRef(
            input_kind=PITInputKind.INJURY,
            input_id=str(self.injury_observation_id),
            available_at=self.knowledge.available_at,
            availability_method=self.knowledge.availability_method,
            availability_confidence=self.knowledge.availability_confidence,
            source_table="injury_observations",
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
            raw_sha256=self.raw_sha256,
        )


@dataclass(frozen=True, slots=True)
class InjuryEpisodeRevision:
    """Immutable interpretation revision for one underlying injury episode."""

    injury_episode_id: InjuryEpisodeId
    player_id: PlayerId
    revision: int
    as_of: datetime
    observation_ids: tuple[InjuryObservationId, ...]
    resolution_state: InjuryResolutionState
    confidence: Probability
    created_at: datetime
    body_region: str | None = None
    laterality: InjuryLaterality = InjuryLaterality.UNKNOWN
    injury_family: str | None = None
    episode_start: datetime | None = None
    episode_end: datetime | None = None
    first_observed_at: datetime | None = None
    source_description: str | None = None
    recurrence_flag: bool | None = None
    related_prior_episode_id: InjuryEpisodeId | None = None

    def __post_init__(self) -> None:
        _require_nonblank(str(self.injury_episode_id), "injury_episode_id")
        _require_nonblank(str(self.player_id), "player_id")
        if self.revision < 1:
            raise ValueError("injury episode revision must be >= 1")
        _require_aware(self.as_of, "episode as_of")
        _require_aware(self.created_at, "episode created_at")
        _require_aware(self.episode_start, "episode_start")
        _require_aware(self.episode_end, "episode_end")
        _require_aware(self.first_observed_at, "first_observed_at")
        if (
            self.episode_start is not None
            and self.episode_end is not None
            and self.episode_end < self.episode_start
        ):
            raise ValueError("injury episode cannot end before it starts")
        if self.first_observed_at is not None and self.first_observed_at > self.as_of:
            raise ValueError("first_observed_at cannot be later than episode as_of")
        for value, label in (
            (self.body_region, "body_region"),
            (self.injury_family, "injury_family"),
            (self.source_description, "source_description"),
        ):
            _optional_text(value, label)
        observation_ids = [str(observation_id) for observation_id in self.observation_ids]
        if any(not observation_id.strip() for observation_id in observation_ids):
            raise ValueError("injury episode observation IDs cannot be blank")
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("injury episode observation IDs cannot repeat")
        if (
            self.related_prior_episode_id is not None
            and self.related_prior_episode_id == self.injury_episode_id
        ):
            raise ValueError("injury episode cannot reference itself as a prior episode")


@dataclass(frozen=True, slots=True)
class InjuryAvailabilityState:
    player_id: PlayerId
    team_season_id: TeamSeasonId
    game_id: GameId
    injury_episode_ids: tuple[InjuryEpisodeId, ...]
    latest_practice_status: PracticeStatus
    latest_game_status: GameDesignation
    latest_active_status: ActiveStatus
    availability_probability: Probability
    participation_if_active: NumericMoments
    effectiveness_if_participates: NumericMoments
    early_exit_probability_if_active: Probability


@dataclass(frozen=True, slots=True)
class InjuryEstimatorConfig:
    """Explicit replaceable V1 assumptions; these numbers are not football truth."""

    version: str = "NFL_INJURY_AVAILABILITY_BASELINE_V1"
    unknown_active_probability: float = 0.85
    out_active_probability: float = 0.0
    doubtful_active_probability: float = 0.05
    questionable_active_probability: float = 0.50
    no_designation_active_probability: float = 0.98
    dnp_active_multiplier: float = 0.70
    limited_active_multiplier: float = 0.90
    full_active_multiplier: float = 1.00
    unknown_practice_active_multiplier: float = 1.00
    dnp_participation_mean: float = 0.65
    limited_participation_mean: float = 0.82
    full_participation_mean: float = 0.98
    unknown_participation_mean: float = 0.90
    participation_variance: float = 0.04
    dnp_effectiveness_mean: float = 0.82
    limited_effectiveness_mean: float = 0.90
    full_effectiveness_mean: float = 0.98
    unknown_effectiveness_mean: float = 0.90
    effectiveness_variance: float = 0.03
    out_early_exit_probability: float = 0.12
    doubtful_early_exit_probability: float = 0.12
    questionable_early_exit_probability: float = 0.08
    no_designation_early_exit_probability: float = 0.03
    unknown_early_exit_probability: float = 0.05

    def __post_init__(self) -> None:
        _require_nonblank(self.version, "injury estimator version")
        for field in fields(self):
            if field.name == "version":
                continue
            value = getattr(self, field.name)
            if not isinstance(value, float):
                raise TypeError(f"{field.name} must be a float")
            if field.name.endswith("variance"):
                if value < 0.0 or value > 0.25:
                    raise ValueError(f"{field.name} must be between 0 and 0.25")
            else:
                _require_unit_interval(value, field.name)


DEFAULT_INJURY_ESTIMATOR_CONFIG = InjuryEstimatorConfig()


def _latest_status[T: StrEnum](
    observations: tuple[InjuryObservation, ...],
    selector: Callable[[InjuryObservation], T],
    unknown: T,
) -> T:
    candidates = [
        (
            observation.knowledge.available_at,
            str(observation.injury_observation_id),
            selector(observation),
        )
        for observation in observations
        if selector(observation) != unknown
    ]
    if not candidates:
        return unknown
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def _game_active_probability(status: GameDesignation, config: InjuryEstimatorConfig) -> float:
    return {
        GameDesignation.OUT: config.out_active_probability,
        GameDesignation.DOUBTFUL: config.doubtful_active_probability,
        GameDesignation.QUESTIONABLE: config.questionable_active_probability,
        GameDesignation.NO_DESIGNATION: config.no_designation_active_probability,
        GameDesignation.UNKNOWN: config.unknown_active_probability,
    }[status]


def _practice_multiplier(status: PracticeStatus, config: InjuryEstimatorConfig) -> float:
    return {
        PracticeStatus.DID_NOT_PARTICIPATE: config.dnp_active_multiplier,
        PracticeStatus.LIMITED: config.limited_active_multiplier,
        PracticeStatus.FULL: config.full_active_multiplier,
        PracticeStatus.UNKNOWN: config.unknown_practice_active_multiplier,
    }[status]


def _participation_mean(status: PracticeStatus, config: InjuryEstimatorConfig) -> float:
    return {
        PracticeStatus.DID_NOT_PARTICIPATE: config.dnp_participation_mean,
        PracticeStatus.LIMITED: config.limited_participation_mean,
        PracticeStatus.FULL: config.full_participation_mean,
        PracticeStatus.UNKNOWN: config.unknown_participation_mean,
    }[status]


def _effectiveness_mean(status: PracticeStatus, config: InjuryEstimatorConfig) -> float:
    return {
        PracticeStatus.DID_NOT_PARTICIPATE: config.dnp_effectiveness_mean,
        PracticeStatus.LIMITED: config.limited_effectiveness_mean,
        PracticeStatus.FULL: config.full_effectiveness_mean,
        PracticeStatus.UNKNOWN: config.unknown_effectiveness_mean,
    }[status]


def _early_exit_probability(status: GameDesignation, config: InjuryEstimatorConfig) -> float:
    return {
        GameDesignation.OUT: config.out_early_exit_probability,
        GameDesignation.DOUBTFUL: config.doubtful_early_exit_probability,
        GameDesignation.QUESTIONABLE: config.questionable_early_exit_probability,
        GameDesignation.NO_DESIGNATION: config.no_designation_early_exit_probability,
        GameDesignation.UNKNOWN: config.unknown_early_exit_probability,
    }[status]


def _coverage(
    status_observations: tuple[InjuryObservation, ...],
    active_episodes: tuple[InjuryEpisodeRevision, ...],
    practice: PracticeStatus,
    game_status: GameDesignation,
    active_status: ActiveStatus,
) -> StateCoverage:
    expected = (
        "injury_episodes",
        "practice_status",
        "game_status",
        "active_status",
        "availability_probability",
        "participation_distribution",
        "effectiveness_distribution",
        "early_exit_uncertainty",
    )
    present = {
        "availability_probability",
        "participation_distribution",
        "effectiveness_distribution",
        "early_exit_uncertainty",
    }
    if active_episodes:
        present.add("injury_episodes")
    if status_observations and practice is not PracticeStatus.UNKNOWN:
        present.add("practice_status")
    if status_observations and game_status is not GameDesignation.UNKNOWN:
        present.add("game_status")
    if status_observations and active_status is not ActiveStatus.UNKNOWN:
        present.add("active_status")
    present_fields = tuple(field for field in expected if field in present)
    missing_fields = tuple(field for field in expected if field not in present)
    return StateCoverage(
        expected_fields=expected,
        present_fields=present_fields,
        missing_fields=missing_fields,
    )


def build_injury_availability_snapshot(
    *,
    player_id: PlayerId,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    as_of: datetime,
    observations: tuple[InjuryObservation, ...],
    episode_revisions: tuple[InjuryEpisodeRevision, ...] = (),
    config: InjuryEstimatorConfig = DEFAULT_INJURY_ESTIMATOR_CONFIG,
    created_at: datetime,
) -> StateSnapshotEnvelope[InjuryAvailabilityState]:
    """Estimate F-10 state from the exact injury information available at ``as_of``."""

    _require_aware(as_of, "injury snapshot as_of")
    _require_aware(created_at, "injury snapshot created_at")
    observation_ids = {observation.injury_observation_id for observation in observations}
    for observation in observations:
        if observation.player_id != player_id:
            raise ValueError("injury observation player does not match snapshot player")
        if observation.team_season_id != team_season_id:
            raise ValueError("injury observation team does not match snapshot team")
        if observation.knowledge.available_at > as_of:
            raise ValueError("injury observation cannot be available after snapshot as_of")

    for episode in episode_revisions:
        if episode.player_id != player_id:
            raise ValueError("injury episode player does not match snapshot player")
        if episode.as_of > as_of:
            raise ValueError("injury episode revision cannot be later than snapshot as_of")
        if not set(episode.observation_ids).issubset(observation_ids):
            raise ValueError("injury episode observations must be included in snapshot inputs")

    status_observations = tuple(
        observation
        for observation in observations
        if observation.game_id is None or observation.game_id == game_id
    )
    practice = _latest_status(
        status_observations,
        lambda observation: observation.practice_status,
        PracticeStatus.UNKNOWN,
    )
    game_status = _latest_status(
        status_observations,
        lambda observation: observation.game_status,
        GameDesignation.UNKNOWN,
    )
    active_status = _latest_status(
        status_observations,
        lambda observation: observation.active_status,
        ActiveStatus.UNKNOWN,
    )

    active_probability = min(
        1.0,
        max(
            0.0,
            _game_active_probability(game_status, config) * _practice_multiplier(practice, config),
        ),
    )
    if active_status is ActiveStatus.INACTIVE:
        active_probability = 0.0
    elif active_status is ActiveStatus.ACTIVE:
        active_probability = 1.0

    participation = NumericMoments(
        mean=_participation_mean(practice, config),
        variance=config.participation_variance,
    )
    effectiveness = NumericMoments(
        mean=_effectiveness_mean(practice, config),
        variance=config.effectiveness_variance,
    )
    early_exit = Probability(_early_exit_probability(game_status, config))
    availability = Probability(active_probability)

    active_episodes = tuple(
        episode
        for episode in episode_revisions
        if episode.resolution_state is not InjuryResolutionState.RESOLVED
    )
    episode_ids = tuple(
        sorted(
            {episode.injury_episode_id for episode in active_episodes},
            key=str,
        )
    )
    payload = InjuryAvailabilityState(
        player_id=player_id,
        team_season_id=team_season_id,
        game_id=game_id,
        injury_episode_ids=episode_ids,
        latest_practice_status=practice,
        latest_game_status=game_status,
        latest_active_status=active_status,
        availability_probability=availability,
        participation_if_active=participation,
        effectiveness_if_participates=effectiveness,
        early_exit_probability_if_active=early_exit,
    )

    unknowns: list[UnknownQuantity] = []
    if practice is PracticeStatus.UNKNOWN:
        unknowns.append(UnknownQuantity("practice_status", MissingnessReason.DATA_UNAVAILABLE))
    if game_status is GameDesignation.UNKNOWN:
        unknowns.append(UnknownQuantity("game_status", MissingnessReason.DATA_UNAVAILABLE))
    if active_status is ActiveStatus.UNKNOWN:
        unknowns.append(UnknownQuantity("active_status", MissingnessReason.DATA_UNAVAILABLE))
    uncertainty = StateUncertainty(
        probabilities=(
            NamedProbability("availability_probability", availability),
            NamedProbability("early_exit_probability_if_active", early_exit),
        ),
        moments=(
            NamedMoments("participation_if_active", participation),
            NamedMoments("effectiveness_if_participates", effectiveness),
        ),
        unknowns=tuple(unknowns),
    )

    return build_state_snapshot(
        state_type=StateType.INJURY_AVAILABILITY,
        subject_type=StateSubjectType.PLAYER,
        subject_id=str(player_id),
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
        calculation_contract="NFL_INJURY_AVAILABILITY_STATE_V1",
        model_version=config.version,
        state_payload=payload,
        uncertainty=uncertainty,
        coverage=_coverage(
            status_observations,
            active_episodes,
            practice,
            game_status,
            active_status,
        ),
        input_observations=tuple(observation.to_pit_input_ref() for observation in observations),
        created_at=created_at,
    )
