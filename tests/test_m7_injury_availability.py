from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

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
from daily_nfl.persistence import (
    SCHEMA_VERSION,
    apply_migrations,
    connect_database,
)
from daily_nfl.persistence.migrations import MIGRATIONS, current_schema_version
from daily_nfl.state import (
    ActiveStatus,
    GameDesignation,
    InjuryEpisodeRevision,
    InjuryEstimatorConfig,
    InjuryLaterality,
    InjuryObservation,
    InjuryResolutionState,
    PracticeStatus,
    Probability,
    build_injury_availability_snapshot,
    build_injury_state_as_of,
    injury_episode_revisions_as_of,
    injury_observations_as_of,
    record_injury_episode_revision,
    record_injury_observation,
    state_snapshot_is_sealed,
)

PLAYER_ID = PlayerId("player-injury-1")
TEAM_ID = TeamSeasonId("team-home-2026")
GAME_ID = GameId("game-injury-1")
BASE = datetime(2026, 9, 13, 16, 0, tzinfo=UTC)


def _connection() -> sqlite3.Connection:
    connection = connect_database(":memory:")
    apply_migrations(connection)
    _seed_core(connection)
    return connection


def _seed_core(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO providers(provider_id, name, provider_type) "
        "VALUES ('injury-test', 'Injury Test', 'TEST')"
    )
    connection.execute(
        "INSERT INTO franchises(franchise_id, canonical_name) VALUES ('fr-home', 'Home')"
    )
    connection.execute(
        "INSERT INTO franchises(franchise_id, canonical_name) VALUES ('fr-away', 'Away')"
    )
    connection.execute(
        """
        INSERT INTO team_seasons(team_season_id, franchise_id, season, display_name)
        VALUES ('team-home-2026', 'fr-home', 2026, 'Home 2026')
        """
    )
    connection.execute(
        """
        INSERT INTO team_seasons(team_season_id, franchise_id, season, display_name)
        VALUES ('team-away-2026', 'fr-away', 2026, 'Away 2026')
        """
    )
    connection.execute(
        "INSERT INTO persons(person_id, canonical_name) VALUES ('person-injury-1', 'Player One')"
    )
    connection.execute(
        "INSERT INTO players(player_id, person_id) VALUES ('player-injury-1', 'person-injury-1')"
    )
    connection.execute(
        """
        INSERT INTO games(
            game_id, event_id, season, season_phase, week, ruleset_version,
            home_team_season_id, away_team_season_id, scheduled_kickoff,
            neutral_site, competition_id
        ) VALUES (
            'game-injury-1', 'event-injury-1', 2026, 'REGULAR', 1, 'NFL-2026',
            'team-home-2026', 'team-away-2026', '2026-09-13T20:00:00Z',
            0, 'nfl'
        )
        """
    )


def _observation(
    number: int,
    *,
    available_at: datetime,
    practice: PracticeStatus = PracticeStatus.UNKNOWN,
    game_status: GameDesignation = GameDesignation.UNKNOWN,
    active_status: ActiveStatus = ActiveStatus.UNKNOWN,
    description: str | None = "leg soreness",
) -> InjuryObservation:
    return InjuryObservation(
        injury_observation_id=InjuryObservationId(f"injury-obs-{number}"),
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        provider_id="injury-test",
        source_id=f"source-{number}",
        reported_body_region="leg",
        reported_injury_description=description,
        practice_status=practice,
        game_status=game_status,
        active_status=active_status,
        source_text=description,
        source_confidence=Probability(0.95),
        knowledge=KnowledgeTimestamp(
            available_at=available_at,
            published_at=available_at,
            observed_at=available_at,
            ingested_at=available_at,
            availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
            availability_confidence=AvailabilityConfidence.HIGH,
        ),
    )


def _episode(
    episode_id: str,
    revision: int,
    *,
    as_of: datetime,
    observation_ids: tuple[InjuryObservationId, ...],
    body_region: str | None = "leg",
    injury_family: str | None = None,
) -> InjuryEpisodeRevision:
    return InjuryEpisodeRevision(
        injury_episode_id=InjuryEpisodeId(episode_id),
        player_id=PLAYER_ID,
        revision=revision,
        as_of=as_of,
        observation_ids=observation_ids,
        body_region=body_region,
        laterality=InjuryLaterality.UNKNOWN,
        injury_family=injury_family,
        first_observed_at=as_of - timedelta(hours=1),
        source_description="source wording only",
        resolution_state=InjuryResolutionState.OPEN,
        confidence=Probability(0.8),
        created_at=as_of + timedelta(minutes=1),
    )


def test_schema_v9_applies_from_fresh_database() -> None:
    connection = connect_database(":memory:")
    try:
        assert apply_migrations(connection) == 9
        assert SCHEMA_VERSION == 9
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {
            "injury_observations",
            "injury_episodes",
            "injury_episode_revisions",
            "injury_episode_revision_observations",
            "injury_episode_revision_seals",
        }.issubset(tables)
    finally:
        connection.close()


def test_schema_v9_upgrades_applied_v8_without_rewriting_history() -> None:
    connection = connect_database(":memory:")
    try:
        for migration in MIGRATIONS[:8]:
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (migration.version, migration.name),
            )
        rows_before = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert current_schema_version(connection) == 8
        assert apply_migrations(connection) == 9
        rows_after = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert [tuple(row) for row in rows_after[:8]] == [tuple(row) for row in rows_before]
        assert tuple(rows_after[8]) == (9, "m7_injury_availability_foundation")
    finally:
        connection.close()


def test_injury_observation_is_idempotent_append_only_and_pit_selectable() -> None:
    connection = _connection()
    try:
        observation = _observation(
            1,
            available_at=BASE - timedelta(hours=24),
            practice=PracticeStatus.LIMITED,
            game_status=GameDesignation.QUESTIONABLE,
        )
        record_injury_observation(connection, observation)
        record_injury_observation(connection, observation)
        selected = injury_observations_as_of(
            connection,
            player_id=PLAYER_ID,
            game_id=GAME_ID,
            as_of=BASE,
        )
        assert selected == (observation,)
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE injury_observations SET game_status = 'OUT' "
                "WHERE injury_observation_id = ?",
                (str(observation.injury_observation_id),),
            )
    finally:
        connection.close()


def test_pit_selection_excludes_later_inactive_observation() -> None:
    connection = _connection()
    try:
        early = _observation(
            1,
            available_at=BASE - timedelta(hours=24),
            game_status=GameDesignation.QUESTIONABLE,
        )
        late = _observation(
            2,
            available_at=BASE - timedelta(minutes=90),
            active_status=ActiveStatus.INACTIVE,
        )
        record_injury_observation(connection, early)
        record_injury_observation(connection, late)
        selected = injury_observations_as_of(
            connection,
            player_id=PLAYER_ID,
            game_id=GAME_ID,
            as_of=BASE - timedelta(hours=6),
        )
        assert selected == (early,)
    finally:
        connection.close()


def test_episode_revisions_are_sealed_versioned_interpretations() -> None:
    connection = _connection()
    try:
        observation = _observation(1, available_at=BASE - timedelta(hours=24))
        record_injury_observation(connection, observation)
        first = _episode(
            "episode-1",
            1,
            as_of=BASE - timedelta(hours=20),
            observation_ids=(observation.injury_observation_id,),
            body_region="leg",
            injury_family=None,
        )
        second = _episode(
            "episode-1",
            2,
            as_of=BASE - timedelta(hours=10),
            observation_ids=(observation.injury_observation_id,),
            body_region="leg",
            injury_family="hamstring",
        )
        record_injury_episode_revision(connection, first)
        record_injury_episode_revision(connection, second)

        earlier = injury_episode_revisions_as_of(
            connection,
            player_id=PLAYER_ID,
            as_of=BASE - timedelta(hours=15),
        )
        later = injury_episode_revisions_as_of(
            connection,
            player_id=PLAYER_ID,
            as_of=BASE - timedelta(hours=5),
        )
        assert earlier == (first,)
        assert later == (second,)
        assert earlier[0].injury_family is None
    finally:
        connection.close()


def test_episode_cannot_seal_with_post_as_of_observation() -> None:
    connection = _connection()
    try:
        observation = _observation(1, available_at=BASE - timedelta(hours=2))
        record_injury_observation(connection, observation)
        revision = _episode(
            "episode-late",
            1,
            as_of=BASE - timedelta(hours=3),
            observation_ids=(observation.injury_observation_id,),
        )
        with pytest.raises(sqlite3.IntegrityError, match="PIT-safe membership"):
            record_injury_episode_revision(connection, revision)
    finally:
        connection.close()


def test_questionable_limited_estimates_separate_three_quantities() -> None:
    observation = _observation(
        1,
        available_at=BASE - timedelta(hours=24),
        practice=PracticeStatus.LIMITED,
        game_status=GameDesignation.QUESTIONABLE,
    )
    snapshot = build_injury_availability_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE - timedelta(hours=6),
        observations=(observation,),
        created_at=BASE - timedelta(hours=6) + timedelta(seconds=1),
    )
    assert snapshot.state_payload.availability_probability.value == pytest.approx(0.45)
    assert snapshot.state_payload.participation_if_active.mean == pytest.approx(0.82)
    assert snapshot.state_payload.effectiveness_if_participates.mean == pytest.approx(0.90)


def test_confirmed_active_does_not_force_full_effectiveness_or_workload() -> None:
    observation = _observation(
        1,
        available_at=BASE - timedelta(minutes=90),
        practice=PracticeStatus.LIMITED,
        game_status=GameDesignation.QUESTIONABLE,
        active_status=ActiveStatus.ACTIVE,
    )
    snapshot = build_injury_availability_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE - timedelta(minutes=60),
        observations=(observation,),
        created_at=BASE - timedelta(minutes=59),
    )
    assert snapshot.state_payload.availability_probability.value == 1.0
    assert snapshot.state_payload.participation_if_active.mean < 1.0
    assert snapshot.state_payload.effectiveness_if_participates.mean < 1.0


def test_late_inactive_creates_new_snapshot_and_collapses_only_availability() -> None:
    early = _observation(
        1,
        available_at=BASE - timedelta(hours=24),
        practice=PracticeStatus.LIMITED,
        game_status=GameDesignation.QUESTIONABLE,
    )
    late = _observation(
        2,
        available_at=BASE - timedelta(minutes=90),
        active_status=ActiveStatus.INACTIVE,
    )
    first = build_injury_availability_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE - timedelta(hours=6),
        observations=(early,),
        created_at=BASE - timedelta(hours=6) + timedelta(seconds=1),
    )
    second = build_injury_availability_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE - timedelta(minutes=60),
        observations=(early, late),
        created_at=BASE - timedelta(minutes=59),
    )
    assert first.state_payload.availability_probability.value > 0.0
    assert second.state_payload.availability_probability.value == 0.0
    assert second.state_payload.participation_if_active.mean == pytest.approx(0.82)
    assert second.state_payload.effectiveness_if_participates.mean == pytest.approx(0.90)
    assert first.snapshot_id != second.snapshot_id


def test_explicit_post_cutoff_observation_fails_closed() -> None:
    late = _observation(1, available_at=BASE - timedelta(minutes=30))
    with pytest.raises(ValueError, match="after snapshot as_of"):
        build_injury_availability_snapshot(
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            as_of=BASE - timedelta(hours=1),
            observations=(late,),
            created_at=BASE,
        )


def test_multiple_simultaneous_episodes_are_preserved() -> None:
    first_observation = _observation(1, available_at=BASE - timedelta(hours=24))
    second_observation = _observation(
        2,
        available_at=BASE - timedelta(hours=12),
        description="illness",
    )
    first_episode = _episode(
        "episode-leg",
        1,
        as_of=BASE - timedelta(hours=10),
        observation_ids=(first_observation.injury_observation_id,),
    )
    second_episode = _episode(
        "episode-illness",
        1,
        as_of=BASE - timedelta(hours=10),
        observation_ids=(second_observation.injury_observation_id,),
        body_region=None,
        injury_family="illness",
    )
    snapshot = build_injury_availability_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE - timedelta(hours=6),
        observations=(first_observation, second_observation),
        episode_revisions=(first_episode, second_episode),
        created_at=BASE - timedelta(hours=6) + timedelta(seconds=1),
    )
    assert snapshot.state_payload.injury_episode_ids == (
        InjuryEpisodeId("episode-illness"),
        InjuryEpisodeId("episode-leg"),
    )


def test_vague_source_does_not_require_invented_diagnosis() -> None:
    observation = _observation(
        1,
        available_at=BASE - timedelta(hours=24),
        description="leg issue",
    )
    episode = _episode(
        "episode-vague",
        1,
        as_of=BASE - timedelta(hours=20),
        observation_ids=(observation.injury_observation_id,),
        body_region="leg",
        injury_family=None,
    )
    assert episode.body_region == "leg"
    assert episode.injury_family is None


def test_versioned_estimator_configuration_changes_state_identity() -> None:
    observation = _observation(
        1,
        available_at=BASE - timedelta(hours=24),
        game_status=GameDesignation.QUESTIONABLE,
    )
    default_snapshot = build_injury_availability_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE - timedelta(hours=6),
        observations=(observation,),
        created_at=BASE - timedelta(hours=6) + timedelta(seconds=1),
    )
    alternate = InjuryEstimatorConfig(
        version="NFL_INJURY_AVAILABILITY_TEST_V2",
        questionable_active_probability=0.60,
    )
    alternate_snapshot = build_injury_availability_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE - timedelta(hours=6),
        observations=(observation,),
        config=alternate,
        created_at=BASE - timedelta(hours=6) + timedelta(seconds=1),
    )
    assert default_snapshot.snapshot_id != alternate_snapshot.snapshot_id
    assert alternate_snapshot.state_payload.availability_probability.value == pytest.approx(0.60)


def test_repository_build_records_exact_pit_safe_state_snapshot() -> None:
    connection = _connection()
    try:
        early = _observation(
            1,
            available_at=BASE - timedelta(hours=24),
            practice=PracticeStatus.LIMITED,
            game_status=GameDesignation.QUESTIONABLE,
        )
        late = _observation(
            2,
            available_at=BASE - timedelta(minutes=90),
            active_status=ActiveStatus.INACTIVE,
        )
        record_injury_observation(connection, early)
        record_injury_observation(connection, late)
        episode = _episode(
            "episode-1",
            1,
            as_of=BASE - timedelta(hours=20),
            observation_ids=(early.injury_observation_id,),
        )
        record_injury_episode_revision(connection, episode)

        snapshot = build_injury_state_as_of(
            connection,
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            as_of=BASE - timedelta(hours=6),
            created_at=BASE - timedelta(hours=6) + timedelta(seconds=1),
        )
        assert state_snapshot_is_sealed(connection, snapshot.snapshot_id)
        assert [item.input_id for item in snapshot.input_observations] == [
            str(early.injury_observation_id)
        ]
        assert snapshot.state_payload.availability_probability.value == pytest.approx(0.45)
    finally:
        connection.close()


def test_episode_cannot_reference_itself_as_prior_episode() -> None:
    with pytest.raises(ValueError, match="cannot reference itself"):
        InjuryEpisodeRevision(
            injury_episode_id=InjuryEpisodeId("episode-self"),
            player_id=PLAYER_ID,
            revision=1,
            as_of=BASE,
            observation_ids=(),
            resolution_state=InjuryResolutionState.OPEN,
            confidence=Probability(0.5),
            created_at=BASE + timedelta(seconds=1),
            related_prior_episode_id=InjuryEpisodeId("episode-self"),
        )


def test_estimator_configuration_rejects_invalid_probability() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        InjuryEstimatorConfig(questionable_active_probability=1.2)
