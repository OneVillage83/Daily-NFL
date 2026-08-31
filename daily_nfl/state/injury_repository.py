"""Append-only persistence and PIT reconstruction for M7-C injury state."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    GameId,
    InjuryEpisodeId,
    InjuryObservationId,
    KnowledgeTimestamp,
    PlayerId,
    TeamSeasonId,
)
from daily_nfl.state.contracts import StateSnapshotEnvelope
from daily_nfl.state.injury import (
    DEFAULT_INJURY_ESTIMATOR_CONFIG,
    ActiveStatus,
    GameDesignation,
    InjuryAvailabilityState,
    InjuryEpisodeRevision,
    InjuryEstimatorConfig,
    InjuryLaterality,
    InjuryObservation,
    InjuryResolutionState,
    PracticeStatus,
    build_injury_availability_snapshot,
)
from daily_nfl.state.repository import record_state_snapshot
from daily_nfl.state.uncertainty import Probability


class InjuryPersistenceConflictError(RuntimeError):
    """Raised when stored injury evidence conflicts with an immutable object."""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("injury persistence timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: object | None) -> datetime | None:
    if value is None:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InjuryPersistenceConflictError("stored injury timestamp is not timezone-aware")
    return parsed.astimezone(UTC)


def _observation_values(observation: InjuryObservation) -> tuple[object, ...]:
    knowledge = observation.knowledge
    return (
        str(observation.injury_observation_id),
        str(observation.player_id),
        str(observation.team_season_id),
        str(observation.game_id) if observation.game_id is not None else None,
        observation.provider_id,
        observation.source_id,
        observation.reported_body_region,
        observation.reported_injury_description,
        observation.practice_status.value,
        observation.game_status.value,
        observation.active_status.value,
        observation.source_text,
        observation.source_confidence.value if observation.source_confidence is not None else None,
        observation.evidence_id,
        observation.evidence_observation_id,
        _iso(knowledge.effective_at),
        _iso(knowledge.published_at),
        _iso(knowledge.observed_at),
        _iso(knowledge.ingested_at),
        _iso(knowledge.available_at),
        knowledge.availability_method.value,
        knowledge.availability_confidence.value,
        observation.provider_revision,
        observation.provider_schema_version,
        observation.parser_version,
        observation.raw_sha256,
    )


def record_injury_observation(
    connection: sqlite3.Connection,
    observation: InjuryObservation,
) -> None:
    """Persist one canonical injury observation idempotently and append-only."""

    existing = connection.execute(
        """
        SELECT injury_observation_id, player_id, team_season_id, game_id,
               provider_id, source_id, reported_body_region,
               reported_injury_description, practice_status, game_status,
               active_status, source_text, source_confidence, evidence_id,
               evidence_observation_id, effective_at, published_at, observed_at,
               ingested_at, available_at, availability_method,
               availability_confidence, provider_revision,
               provider_schema_version, parser_version, raw_sha256
        FROM injury_observations
        WHERE injury_observation_id = ?
        """,
        (str(observation.injury_observation_id),),
    ).fetchone()
    expected = _observation_values(observation)
    if existing is not None:
        if tuple(existing) != expected:
            raise InjuryPersistenceConflictError(
                "stored injury observation conflicts with immutable observation"
            )
        return

    connection.execute(
        """
        INSERT INTO injury_observations(
            injury_observation_id, player_id, team_season_id, game_id,
            provider_id, source_id, reported_body_region,
            reported_injury_description, practice_status, game_status,
            active_status, source_text, source_confidence, evidence_id,
            evidence_observation_id, effective_at, published_at, observed_at,
            ingested_at, available_at, availability_method,
            availability_confidence, provider_revision,
            provider_schema_version, parser_version, raw_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        expected,
    )


def _observation_from_row(row: sqlite3.Row) -> InjuryObservation:
    available_at = _parse_time(row[19])
    if available_at is None:
        raise InjuryPersistenceConflictError("stored injury observation lacks available_at")
    return InjuryObservation(
        injury_observation_id=InjuryObservationId(str(row[0])),
        player_id=PlayerId(str(row[1])),
        team_season_id=TeamSeasonId(str(row[2])),
        game_id=GameId(str(row[3])) if row[3] is not None else None,
        provider_id=str(row[4]),
        source_id=str(row[5]),
        reported_body_region=str(row[6]) if row[6] is not None else None,
        reported_injury_description=str(row[7]) if row[7] is not None else None,
        practice_status=PracticeStatus(str(row[8])),
        game_status=GameDesignation(str(row[9])),
        active_status=ActiveStatus(str(row[10])),
        source_text=str(row[11]) if row[11] is not None else None,
        source_confidence=Probability(float(row[12])) if row[12] is not None else None,
        evidence_id=str(row[13]) if row[13] is not None else None,
        evidence_observation_id=str(row[14]) if row[14] is not None else None,
        knowledge=KnowledgeTimestamp(
            effective_at=_parse_time(row[15]),
            published_at=_parse_time(row[16]),
            observed_at=_parse_time(row[17]),
            ingested_at=_parse_time(row[18]),
            available_at=available_at,
            availability_method=AvailabilityMethod(str(row[20])),
            availability_confidence=AvailabilityConfidence(str(row[21])),
        ),
        provider_revision=str(row[22]) if row[22] is not None else None,
        provider_schema_version=str(row[23]) if row[23] is not None else None,
        parser_version=str(row[24]) if row[24] is not None else None,
        raw_sha256=str(row[25]) if row[25] is not None else None,
    )


def injury_observations_as_of(
    connection: sqlite3.Connection,
    *,
    player_id: PlayerId,
    as_of: datetime,
    game_id: GameId | None = None,
) -> tuple[InjuryObservation, ...]:
    """Return only injury observations knowable by ``as_of`` for the player/game."""

    cutoff = _iso(as_of)
    if cutoff is None:
        raise ValueError("as_of is required")
    parameters: tuple[object, ...]
    if game_id is None:
        game_clause = ""
        parameters = (str(player_id), cutoff)
    else:
        game_clause = " AND (game_id IS NULL OR game_id = ?)"
        parameters = (str(player_id), cutoff, str(game_id))
    rows = connection.execute(
        f"""
        SELECT injury_observation_id, player_id, team_season_id, game_id,
               provider_id, source_id, reported_body_region,
               reported_injury_description, practice_status, game_status,
               active_status, source_text, source_confidence, evidence_id,
               evidence_observation_id, effective_at, published_at, observed_at,
               ingested_at, available_at, availability_method,
               availability_confidence, provider_revision,
               provider_schema_version, parser_version, raw_sha256
        FROM injury_observations
        WHERE player_id = ? AND available_at <= ?{game_clause}
        ORDER BY available_at, injury_observation_id
        """,
        parameters,
    ).fetchall()
    return tuple(_observation_from_row(row) for row in rows)


def _episode_values(revision: InjuryEpisodeRevision) -> tuple[object, ...]:
    return (
        str(revision.injury_episode_id),
        revision.revision,
        _iso(revision.as_of),
        revision.body_region,
        revision.laterality.value,
        revision.injury_family,
        _iso(revision.episode_start),
        _iso(revision.episode_end),
        _iso(revision.first_observed_at),
        revision.source_description,
        None if revision.recurrence_flag is None else int(revision.recurrence_flag),
        (
            str(revision.related_prior_episode_id)
            if revision.related_prior_episode_id is not None
            else None
        ),
        revision.resolution_state.value,
        revision.confidence.value,
        len(revision.observation_ids),
        _iso(revision.created_at),
    )


def _episode_is_sealed(
    connection: sqlite3.Connection,
    injury_episode_id: InjuryEpisodeId,
    revision: int,
) -> bool:
    row = connection.execute(
        """
        SELECT 1 FROM injury_episode_revision_seals
        WHERE injury_episode_id = ? AND revision = ?
        """,
        (str(injury_episode_id), revision),
    ).fetchone()
    return row is not None


def _verify_episode_revision(
    connection: sqlite3.Connection,
    revision: InjuryEpisodeRevision,
    existing: sqlite3.Row,
) -> None:
    expected = _episode_values(revision)
    if tuple(existing) != expected:
        raise InjuryPersistenceConflictError(
            "stored injury episode revision conflicts with immutable interpretation"
        )
    if not _episode_is_sealed(connection, revision.injury_episode_id, revision.revision):
        raise InjuryPersistenceConflictError("stored injury episode revision is unsealed")
    rows = connection.execute(
        """
        SELECT injury_observation_id
        FROM injury_episode_revision_observations
        WHERE injury_episode_id = ? AND revision = ?
        ORDER BY injury_observation_id
        """,
        (str(revision.injury_episode_id), revision.revision),
    ).fetchall()
    stored = [str(row[0]) for row in rows]
    expected_ids = sorted(str(observation_id) for observation_id in revision.observation_ids)
    if stored != expected_ids:
        raise InjuryPersistenceConflictError(
            "stored injury episode revision has conflicting observation membership"
        )


def record_injury_episode_revision(
    connection: sqlite3.Connection,
    revision: InjuryEpisodeRevision,
) -> None:
    """Atomically record and seal one immutable episode interpretation revision."""

    existing_episode = connection.execute(
        "SELECT player_id FROM injury_episodes WHERE injury_episode_id = ?",
        (str(revision.injury_episode_id),),
    ).fetchone()
    if existing_episode is not None and str(existing_episode[0]) != str(revision.player_id):
        raise InjuryPersistenceConflictError("injury episode identity belongs to another player")

    existing = connection.execute(
        """
        SELECT injury_episode_id, revision, as_of, body_region, laterality,
               injury_family, episode_start, episode_end, first_observed_at,
               source_description, recurrence_flag, related_prior_episode_id,
               resolution_state, confidence, observation_count, created_at
        FROM injury_episode_revisions
        WHERE injury_episode_id = ? AND revision = ?
        """,
        (str(revision.injury_episode_id), revision.revision),
    ).fetchone()
    if existing is not None:
        _verify_episode_revision(connection, revision, existing)
        return

    connection.execute("SAVEPOINT record_injury_episode_revision")
    try:
        if existing_episode is None:
            connection.execute(
                "INSERT INTO injury_episodes(injury_episode_id, player_id) VALUES (?, ?)",
                (str(revision.injury_episode_id), str(revision.player_id)),
            )
        connection.execute(
            """
            INSERT INTO injury_episode_revisions(
                injury_episode_id, revision, as_of, body_region, laterality,
                injury_family, episode_start, episode_end, first_observed_at,
                source_description, recurrence_flag, related_prior_episode_id,
                resolution_state, confidence, observation_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _episode_values(revision),
        )
        connection.executemany(
            """
            INSERT INTO injury_episode_revision_observations(
                injury_episode_id, revision, injury_observation_id
            ) VALUES (?, ?, ?)
            """,
            [
                (
                    str(revision.injury_episode_id),
                    revision.revision,
                    str(observation_id),
                )
                for observation_id in sorted(revision.observation_ids, key=str)
            ],
        )
        connection.execute(
            """
            INSERT INTO injury_episode_revision_seals(injury_episode_id, revision)
            VALUES (?, ?)
            """,
            (str(revision.injury_episode_id), revision.revision),
        )
        connection.execute("RELEASE SAVEPOINT record_injury_episode_revision")
    except BaseException:
        connection.execute("ROLLBACK TO SAVEPOINT record_injury_episode_revision")
        connection.execute("RELEASE SAVEPOINT record_injury_episode_revision")
        raise


def _episode_from_row(
    row: sqlite3.Row,
    observation_ids: tuple[InjuryObservationId, ...],
) -> InjuryEpisodeRevision:
    as_of = _parse_time(row[2])
    created_at = _parse_time(row[15])
    if as_of is None or created_at is None:
        raise InjuryPersistenceConflictError("stored injury episode lacks required timestamps")
    return InjuryEpisodeRevision(
        injury_episode_id=InjuryEpisodeId(str(row[0])),
        player_id=PlayerId(str(row[16])),
        revision=int(row[1]),
        as_of=as_of,
        body_region=str(row[3]) if row[3] is not None else None,
        laterality=InjuryLaterality(str(row[4])),
        injury_family=str(row[5]) if row[5] is not None else None,
        episode_start=_parse_time(row[6]),
        episode_end=_parse_time(row[7]),
        first_observed_at=_parse_time(row[8]),
        source_description=str(row[9]) if row[9] is not None else None,
        recurrence_flag=None if row[10] is None else bool(row[10]),
        related_prior_episode_id=(
            InjuryEpisodeId(str(row[11])) if row[11] is not None else None
        ),
        resolution_state=InjuryResolutionState(str(row[12])),
        confidence=Probability(float(row[13])),
        observation_ids=observation_ids,
        created_at=created_at,
    )


def injury_episode_revisions_as_of(
    connection: sqlite3.Connection,
    *,
    player_id: PlayerId,
    as_of: datetime,
) -> tuple[InjuryEpisodeRevision, ...]:
    """Return the latest sealed interpretation of each episode knowable by ``as_of``."""

    cutoff = _iso(as_of)
    if cutoff is None:
        raise ValueError("as_of is required")
    rows = connection.execute(
        """
        SELECT revision.injury_episode_id, revision.revision, revision.as_of,
               revision.body_region, revision.laterality, revision.injury_family,
               revision.episode_start, revision.episode_end,
               revision.first_observed_at, revision.source_description,
               revision.recurrence_flag, revision.related_prior_episode_id,
               revision.resolution_state, revision.confidence,
               revision.observation_count, revision.created_at, episode.player_id
        FROM injury_episode_revisions revision
        JOIN injury_episodes episode
          ON episode.injury_episode_id = revision.injury_episode_id
        JOIN injury_episode_revision_seals seal
          ON seal.injury_episode_id = revision.injury_episode_id
         AND seal.revision = revision.revision
        WHERE episode.player_id = ? AND revision.as_of <= ?
        ORDER BY revision.injury_episode_id, revision.revision DESC
        """,
        (str(player_id), cutoff),
    ).fetchall()
    latest: dict[str, sqlite3.Row] = {}
    for row in rows:
        latest.setdefault(str(row[0]), row)

    revisions: list[InjuryEpisodeRevision] = []
    for episode_id in sorted(latest):
        row = latest[episode_id]
        member_rows = connection.execute(
            """
            SELECT injury_observation_id
            FROM injury_episode_revision_observations
            WHERE injury_episode_id = ? AND revision = ?
            ORDER BY injury_observation_id
            """,
            (episode_id, int(row[1])),
        ).fetchall()
        observation_ids = tuple(
            InjuryObservationId(str(member_row[0])) for member_row in member_rows
        )
        revisions.append(_episode_from_row(row, observation_ids))
    return tuple(revisions)


def build_injury_state_as_of(
    connection: sqlite3.Connection,
    *,
    player_id: PlayerId,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    as_of: datetime,
    created_at: datetime,
    config: InjuryEstimatorConfig = DEFAULT_INJURY_ESTIMATOR_CONFIG,
) -> StateSnapshotEnvelope[InjuryAvailabilityState]:
    """Reconstruct, persist, and return the exact F-10 state knowable at a cutoff."""

    observations = injury_observations_as_of(
        connection,
        player_id=player_id,
        as_of=as_of,
        game_id=game_id,
    )
    episodes = injury_episode_revisions_as_of(
        connection,
        player_id=player_id,
        as_of=as_of,
    )
    snapshot = build_injury_availability_snapshot(
        player_id=player_id,
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
        observations=observations,
        episode_revisions=episodes,
        config=config,
        created_at=created_at,
    )
    record_state_snapshot(connection, snapshot)
    return snapshot
