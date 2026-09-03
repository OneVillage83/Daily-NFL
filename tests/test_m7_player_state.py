from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    GameId,
    InjuryObservationId,
    KnowledgeTimestamp,
    PlayerId,
    PlayerStateEvidenceObservationId,
    TeamSeasonId,
)
from daily_nfl.persistence import SCHEMA_VERSION, apply_migrations, connect_database
from daily_nfl.persistence.migrations import MIGRATIONS, current_schema_version
from daily_nfl.state import (
    ActiveStatus,
    GameDesignation,
    InjuryAvailabilityState,
    InjuryObservation,
    NamedMoments,
    NumericMoments,
    PlayerEvidenceKind,
    PlayerPosition,
    PlayerStateEstimatorConfig,
    PlayerStateEvidenceObservation,
    PracticeStatus,
    Probability,
    StateSnapshotEnvelope,
    build_injury_availability_snapshot,
    build_player_state_as_of,
    build_player_state_snapshot,
    canonical_position_metrics,
    player_state_evidence_as_of,
    record_player_state_evidence,
    record_state_snapshot,
    resolve_player_position,
    state_snapshot_is_sealed,
)

PLAYER_ID = PlayerId("player-state-1")
TEAM_ID = TeamSeasonId("team-current-2026")
OLD_TEAM_ID = TeamSeasonId("team-old-2025")
AWAY_TEAM_ID = TeamSeasonId("team-away-2026")
TARGET_GAME_ID = GameId("game-target-2026")
PRIOR_GAME_ID = GameId("game-prior-2026")
BASE = datetime(2026, 9, 13, 16, 0, tzinfo=UTC)


def _connection() -> sqlite3.Connection:
    connection = connect_database(":memory:")
    apply_migrations(connection)
    _seed_core(connection)
    return connection


def _seed_core(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO providers(provider_id, name, provider_type) "
        "VALUES ('player-test', 'Player Test', 'TEST')"
    )
    connection.execute(
        "INSERT INTO franchises(franchise_id, canonical_name) VALUES ('fr-current', 'Current')"
    )
    connection.execute(
        "INSERT INTO franchises(franchise_id, canonical_name) VALUES ('fr-old', 'Old')"
    )
    connection.execute(
        "INSERT INTO franchises(franchise_id, canonical_name) VALUES ('fr-away', 'Away')"
    )
    connection.execute(
        """
        INSERT INTO team_seasons(team_season_id, franchise_id, season, display_name)
        VALUES ('team-current-2026', 'fr-current', 2026, 'Current 2026')
        """
    )
    connection.execute(
        """
        INSERT INTO team_seasons(team_season_id, franchise_id, season, display_name)
        VALUES ('team-old-2025', 'fr-old', 2025, 'Old 2025')
        """
    )
    connection.execute(
        """
        INSERT INTO team_seasons(team_season_id, franchise_id, season, display_name)
        VALUES ('team-away-2026', 'fr-away', 2026, 'Away 2026')
        """
    )
    connection.execute(
        "INSERT INTO persons(person_id, canonical_name) VALUES ('person-state-1', 'Player One')"
    )
    connection.execute(
        "INSERT INTO players(player_id, person_id) VALUES ('player-state-1', 'person-state-1')"
    )
    connection.execute(
        """
        INSERT INTO games(
            game_id, event_id, season, season_phase, week, ruleset_version,
            home_team_season_id, away_team_season_id, scheduled_kickoff,
            neutral_site, competition_id
        ) VALUES (
            'game-prior-2026', 'event-prior-2026', 2026, 'REGULAR', 1, 'NFL-2026',
            'team-current-2026', 'team-away-2026', '2026-09-06T20:00:00Z',
            0, 'nfl'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO games(
            game_id, event_id, season, season_phase, week, ruleset_version,
            home_team_season_id, away_team_season_id, scheduled_kickoff,
            neutral_site, competition_id
        ) VALUES (
            'game-target-2026', 'event-target-2026', 2026, 'REGULAR', 2, 'NFL-2026',
            'team-current-2026', 'team-away-2026', '2026-09-13T20:00:00Z',
            0, 'nfl'
        )
        """
    )


def _metric(name: str, mean: float, variance: float = 0.04) -> NamedMoments:
    return NamedMoments(name=name, estimate=NumericMoments(mean, variance))


def _evidence(
    number: int,
    *,
    kind: PlayerEvidenceKind,
    available_at: datetime,
    metrics: tuple[NamedMoments, ...] = (),
    logical_key: str | None = None,
    revision: int = 1,
    team_season_id: TeamSeasonId | None = TEAM_ID,
    source_game_id: GameId | None = PRIOR_GAME_ID,
    position: PlayerPosition = PlayerPosition.QB,
    sample_weight: float = 1.0,
    source_confidence: float = 0.9,
) -> PlayerStateEvidenceObservation:
    return PlayerStateEvidenceObservation(
        observation_id=PlayerStateEvidenceObservationId(f"player-evidence-{number}"),
        player_id=PLAYER_ID,
        logical_key=logical_key or f"logical-{number}",
        revision=revision,
        team_season_id=team_season_id,
        source_game_id=source_game_id,
        position=position,
        evidence_kind=kind,
        metrics=metrics,
        sample_weight=sample_weight,
        source_confidence=Probability(source_confidence),
        evidence_contract="NFL_PLAYER_EVIDENCE_TEST_V1",
        evidence_version="1",
        knowledge=KnowledgeTimestamp(
            available_at=available_at,
            published_at=available_at,
            observed_at=available_at,
            ingested_at=available_at,
            availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
            availability_confidence=AvailabilityConfidence.HIGH,
        ),
    )


def _injury_snapshot(
    *,
    as_of: datetime,
    active_status: ActiveStatus = ActiveStatus.ACTIVE,
    practice_status: PracticeStatus = PracticeStatus.FULL,
    game_status: GameDesignation = GameDesignation.NO_DESIGNATION,
) -> StateSnapshotEnvelope[InjuryAvailabilityState]:
    observation = InjuryObservation(
        injury_observation_id=InjuryObservationId(
            f"injury-{int(as_of.timestamp())}-{active_status.value}"
        ),
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=TARGET_GAME_ID,
        provider_id="player-test",
        source_id=f"injury-source-{int(as_of.timestamp())}",
        practice_status=practice_status,
        game_status=game_status,
        active_status=active_status,
        source_confidence=Probability(0.95),
        knowledge=KnowledgeTimestamp(
            available_at=as_of,
            published_at=as_of,
            observed_at=as_of,
            ingested_at=as_of,
            availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
            availability_confidence=AvailabilityConfidence.HIGH,
        ),
    )
    return build_injury_availability_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=TARGET_GAME_ID,
        as_of=as_of,
        observations=(observation,),
        created_at=as_of + timedelta(seconds=1),
    )


def test_schema_contains_v10_player_foundation_after_current_migrations() -> None:
    connection = connect_database(":memory:")
    try:
        assert apply_migrations(connection) == SCHEMA_VERSION
        assert SCHEMA_VERSION >= 10
        assert MIGRATIONS[9].version == 10
        assert MIGRATIONS[9].name == "m7_player_state_evidence_foundation"
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "player_state_evidence_observations" in tables
    finally:
        connection.close()


def test_schema_v10_upgrades_applied_v9_without_rewriting_history() -> None:
    connection = connect_database(":memory:")
    try:
        for migration in MIGRATIONS[:9]:
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (migration.version, migration.name),
            )
        rows_before = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert current_schema_version(connection) == 9
        migration_v10 = MIGRATIONS[9]
        connection.executescript(migration_v10.sql)
        connection.execute(
            "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
            (migration_v10.version, migration_v10.name),
        )
        rows_after = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert current_schema_version(connection) == 10
        assert [tuple(row) for row in rows_after[:9]] == [
            tuple(row) for row in rows_before
        ]
        assert tuple(rows_after[9]) == (10, "m7_player_state_evidence_foundation")
    finally:
        connection.close()


def test_player_evidence_is_idempotent_append_only_and_hash_verified() -> None:
    connection = _connection()
    try:
        observation = _evidence(
            1,
            kind=PlayerEvidenceKind.PERFORMANCE,
            available_at=BASE - timedelta(days=3),
            metrics=(_metric("passing_efficiency", 0.7),),
        )
        record_player_state_evidence(connection, observation)
        record_player_state_evidence(connection, observation)
        rows = player_state_evidence_as_of(
            connection,
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            target_game_id=TARGET_GAME_ID,
            as_of=BASE,
        )
        assert rows == (observation,)
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE player_state_evidence_observations "
                "SET sample_weight = 2.0 WHERE observation_id = ?",
                (str(observation.observation_id),),
            )
    finally:
        connection.close()


def test_player_evidence_hash_is_metric_order_invariant_but_semantic() -> None:
    first = _evidence(
        1,
        kind=PlayerEvidenceKind.TALENT,
        available_at=BASE - timedelta(days=30),
        metrics=(_metric("b", 0.6), _metric("a", 0.7)),
        source_game_id=None,
    )
    second = _evidence(
        2,
        kind=PlayerEvidenceKind.TALENT,
        available_at=BASE - timedelta(days=30),
        metrics=(_metric("a", 0.7), _metric("b", 0.6)),
        logical_key=first.logical_key,
        source_game_id=None,
    )
    different_confidence = _evidence(
        3,
        kind=PlayerEvidenceKind.TALENT,
        available_at=BASE - timedelta(days=30),
        metrics=(_metric("a", 0.7), _metric("b", 0.6)),
        logical_key=first.logical_key,
        source_game_id=None,
        source_confidence=0.5,
    )
    assert first.metrics_sha256 == second.metrics_sha256
    assert first.payload_sha256 == second.payload_sha256
    assert first.payload_sha256 != different_confidence.payload_sha256


def test_revision_selection_uses_latest_revision_known_at_cutoff() -> None:
    connection = _connection()
    try:
        first = _evidence(
            1,
            kind=PlayerEvidenceKind.PERFORMANCE,
            available_at=BASE - timedelta(days=5),
            metrics=(_metric("passing_efficiency", 0.5),),
            logical_key="week-one-performance",
            revision=1,
        )
        correction = _evidence(
            2,
            kind=PlayerEvidenceKind.PERFORMANCE,
            available_at=BASE - timedelta(days=1),
            metrics=(_metric("passing_efficiency", 0.7),),
            logical_key="week-one-performance",
            revision=2,
        )
        record_player_state_evidence(connection, first)
        record_player_state_evidence(connection, correction)
        early = player_state_evidence_as_of(
            connection,
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            target_game_id=TARGET_GAME_ID,
            as_of=BASE - timedelta(days=3),
        )
        late = player_state_evidence_as_of(
            connection,
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            target_game_id=TARGET_GAME_ID,
            as_of=BASE,
        )
        assert early == (first,)
        assert late == (correction,)
    finally:
        connection.close()


def test_repository_excludes_current_target_game_evidence() -> None:
    connection = _connection()
    try:
        current_game = _evidence(
            1,
            kind=PlayerEvidenceKind.PERFORMANCE,
            available_at=BASE - timedelta(hours=1),
            metrics=(_metric("passing_efficiency", 0.9),),
            source_game_id=TARGET_GAME_ID,
        )
        record_player_state_evidence(connection, current_game)
        selected = player_state_evidence_as_of(
            connection,
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            target_game_id=TARGET_GAME_ID,
            as_of=BASE,
        )
        assert selected == ()
    finally:
        connection.close()


def test_team_change_preserves_talent_but_not_prior_team_role() -> None:
    connection = _connection()
    try:
        talent = _evidence(
            1,
            kind=PlayerEvidenceKind.TALENT,
            available_at=BASE - timedelta(days=100),
            metrics=(_metric("arm_talent", 0.8),),
            team_season_id=OLD_TEAM_ID,
            source_game_id=None,
        )
        old_role = _evidence(
            2,
            kind=PlayerEvidenceKind.ROLE,
            available_at=BASE - timedelta(days=100),
            metrics=(_metric("snap_share", 0.95),),
            team_season_id=OLD_TEAM_ID,
            source_game_id=None,
        )
        current_role = _evidence(
            3,
            kind=PlayerEvidenceKind.ROLE,
            available_at=BASE - timedelta(days=2),
            metrics=(_metric("snap_share", 0.70),),
            team_season_id=TEAM_ID,
        )
        for observation in (talent, old_role, current_role):
            record_player_state_evidence(connection, observation)
        selected = player_state_evidence_as_of(
            connection,
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            target_game_id=TARGET_GAME_ID,
            as_of=BASE,
        )
        assert talent in selected
        assert current_role in selected
        assert old_role not in selected
    finally:
        connection.close()


def test_position_resolution_uses_latest_current_team_observation() -> None:
    older = _evidence(
        1,
        kind=PlayerEvidenceKind.POSITION,
        available_at=BASE - timedelta(days=10),
        position=PlayerPosition.WR,
        source_game_id=None,
    )
    newer = _evidence(
        2,
        kind=PlayerEvidenceKind.POSITION,
        available_at=BASE - timedelta(days=1),
        position=PlayerPosition.QB,
        source_game_id=None,
    )
    assert resolve_player_position((older, newer), team_season_id=TEAM_ID) is PlayerPosition.QB


def test_position_resolution_fails_closed_on_same_time_conflict() -> None:
    first = _evidence(
        1,
        kind=PlayerEvidenceKind.POSITION,
        available_at=BASE - timedelta(days=1),
        position=PlayerPosition.QB,
        source_game_id=None,
    )
    second = _evidence(
        2,
        kind=PlayerEvidenceKind.POSITION,
        available_at=BASE - timedelta(days=1),
        position=PlayerPosition.WR,
        source_game_id=None,
    )
    with pytest.raises(ValueError, match="conflicting current player positions"):
        resolve_player_position((first, second), team_season_id=TEAM_ID)


def test_player_state_keeps_talent_form_role_and_workload_separate() -> None:
    injury = _injury_snapshot(as_of=BASE - timedelta(hours=6))
    evidence = (
        _evidence(
            1,
            kind=PlayerEvidenceKind.TALENT,
            available_at=BASE - timedelta(days=100),
            metrics=(_metric("overall_talent", 0.8),),
            source_game_id=None,
        ),
        _evidence(
            2,
            kind=PlayerEvidenceKind.PERFORMANCE,
            available_at=BASE - timedelta(days=2),
            metrics=(_metric("recent_efficiency", 0.6),),
        ),
        _evidence(
            3,
            kind=PlayerEvidenceKind.ROLE,
            available_at=BASE - timedelta(days=1),
            metrics=(_metric("snap_share", 0.75),),
        ),
        _evidence(
            4,
            kind=PlayerEvidenceKind.WORKLOAD,
            available_at=BASE - timedelta(days=1),
            metrics=(_metric("recent_snaps", 62.0, 9.0),),
        ),
    )
    snapshot = build_player_state_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=TARGET_GAME_ID,
        as_of=BASE - timedelta(hours=5),
        position=PlayerPosition.QB,
        evidence=evidence,
        injury_snapshot=injury,
        created_at=BASE - timedelta(hours=5) + timedelta(seconds=1),
    )
    assert snapshot.state_payload.talent_state.metrics[0].name == "overall_talent"
    assert snapshot.state_payload.form_state.metrics[0].name == "recent_efficiency"
    assert snapshot.state_payload.role_state.metrics[0].name == "snap_share"
    assert snapshot.state_payload.workload_state.metrics[0].name == "recent_snaps"
    assert snapshot.state_payload.health_snapshot_id == injury.snapshot_id


def test_player_state_propagates_active_without_forcing_full_effectiveness() -> None:
    injury = _injury_snapshot(
        as_of=BASE - timedelta(minutes=90),
        active_status=ActiveStatus.ACTIVE,
        practice_status=PracticeStatus.LIMITED,
        game_status=GameDesignation.QUESTIONABLE,
    )
    snapshot = build_player_state_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=TARGET_GAME_ID,
        as_of=BASE - timedelta(minutes=60),
        position=PlayerPosition.QB,
        evidence=(),
        injury_snapshot=injury,
        created_at=BASE - timedelta(minutes=59),
    )
    assert snapshot.state_payload.availability_probability.value == 1.0
    assert snapshot.state_payload.participation_if_active.mean < 1.0
    assert snapshot.state_payload.effectiveness_if_participates.mean < 1.0


def test_player_state_does_not_invent_fatigue_from_workload() -> None:
    injury = _injury_snapshot(as_of=BASE - timedelta(hours=6))
    workload = _evidence(
        1,
        kind=PlayerEvidenceKind.WORKLOAD,
        available_at=BASE - timedelta(days=1),
        metrics=(_metric("recent_snaps", 80.0, 16.0),),
    )
    snapshot = build_player_state_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=TARGET_GAME_ID,
        as_of=BASE - timedelta(hours=5),
        position=PlayerPosition.QB,
        evidence=(workload,),
        injury_snapshot=injury,
        created_at=BASE - timedelta(hours=5) + timedelta(seconds=1),
    )
    assert snapshot.state_payload.fatigue_estimate is None
    assert any(item.name == "fatigue_state" for item in snapshot.uncertainty.unknowns)


def test_low_sample_player_evidence_remains_explicitly_uncertain() -> None:
    injury = _injury_snapshot(as_of=BASE - timedelta(hours=6))
    talent = _evidence(
        1,
        kind=PlayerEvidenceKind.TALENT,
        available_at=BASE - timedelta(days=30),
        metrics=(_metric("prospect_prior", 0.65, 0.20),),
        source_game_id=None,
        sample_weight=0.25,
    )
    snapshot = build_player_state_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=TARGET_GAME_ID,
        as_of=BASE - timedelta(hours=5),
        position=PlayerPosition.QB,
        evidence=(talent,),
        injury_snapshot=injury,
        created_at=BASE - timedelta(hours=5) + timedelta(seconds=1),
    )
    assert snapshot.state_payload.talent_state.low_sample is True
    assert any(
        item.name == "talent_state_low_sample" for item in snapshot.uncertainty.unknowns
    )


def test_qb_position_extension_vocabulary_is_not_a_universal_player_rating() -> None:
    qb_metrics = canonical_position_metrics(PlayerPosition.QB)
    assert "pressure_response" in qb_metrics
    assert "mobility_state" in qb_metrics
    assert "passing_talent" in qb_metrics
    assert canonical_position_metrics(PlayerPosition.K) != qb_metrics


def test_position_specific_evidence_for_wrong_position_fails_closed() -> None:
    injury = _injury_snapshot(as_of=BASE - timedelta(hours=6))
    receiver_signal = _evidence(
        1,
        kind=PlayerEvidenceKind.POSITION_SPECIFIC,
        available_at=BASE - timedelta(days=1),
        metrics=(_metric("route_efficiency", 0.7),),
        position=PlayerPosition.WR,
    )
    with pytest.raises(ValueError, match="position-specific evidence"):
        build_player_state_snapshot(
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            game_id=TARGET_GAME_ID,
            as_of=BASE - timedelta(hours=5),
            position=PlayerPosition.QB,
            evidence=(receiver_signal,),
            injury_snapshot=injury,
            created_at=BASE - timedelta(hours=5) + timedelta(seconds=1),
        )


def test_direct_current_game_player_evidence_fails_closed() -> None:
    injury = _injury_snapshot(as_of=BASE - timedelta(hours=6))
    current_game = _evidence(
        1,
        kind=PlayerEvidenceKind.PERFORMANCE,
        available_at=BASE - timedelta(hours=1),
        metrics=(_metric("passing_efficiency", 0.9),),
        source_game_id=TARGET_GAME_ID,
    )
    with pytest.raises(ValueError, match="current pregame target game"):
        build_player_state_snapshot(
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            game_id=TARGET_GAME_ID,
            as_of=BASE,
            position=PlayerPosition.QB,
            evidence=(current_game,),
            injury_snapshot=injury,
            created_at=BASE + timedelta(seconds=1),
        )


def test_post_cutoff_player_evidence_fails_closed() -> None:
    injury = _injury_snapshot(as_of=BASE - timedelta(hours=6))
    late = _evidence(
        1,
        kind=PlayerEvidenceKind.PERFORMANCE,
        available_at=BASE + timedelta(minutes=1),
        metrics=(_metric("passing_efficiency", 0.9),),
    )
    with pytest.raises(ValueError, match="available after Player State as_of"):
        build_player_state_snapshot(
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            game_id=TARGET_GAME_ID,
            as_of=BASE,
            position=PlayerPosition.QB,
            evidence=(late,),
            injury_snapshot=injury,
            created_at=BASE + timedelta(seconds=1),
        )


def test_later_injury_parent_than_player_state_fails_closed() -> None:
    injury = _injury_snapshot(as_of=BASE)
    with pytest.raises(ValueError, match="injury parent cannot be later"):
        build_player_state_snapshot(
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            game_id=TARGET_GAME_ID,
            as_of=BASE - timedelta(minutes=1),
            position=PlayerPosition.QB,
            evidence=(),
            injury_snapshot=injury,
            created_at=BASE,
        )


def test_player_state_identity_is_order_independent_and_model_versioned() -> None:
    injury = _injury_snapshot(as_of=BASE - timedelta(hours=6))
    first = _evidence(
        1,
        kind=PlayerEvidenceKind.PERFORMANCE,
        available_at=BASE - timedelta(days=2),
        metrics=(_metric("passing_efficiency", 0.6),),
    )
    second = _evidence(
        2,
        kind=PlayerEvidenceKind.PERFORMANCE,
        available_at=BASE - timedelta(days=1),
        metrics=(_metric("passing_efficiency", 0.7),),
    )
    left = build_player_state_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=TARGET_GAME_ID,
        as_of=BASE - timedelta(hours=5),
        position=PlayerPosition.QB,
        evidence=(first, second),
        injury_snapshot=injury,
        created_at=BASE,
    )
    right = build_player_state_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=TARGET_GAME_ID,
        as_of=BASE - timedelta(hours=5),
        position=PlayerPosition.QB,
        evidence=(second, first),
        injury_snapshot=injury,
        created_at=BASE + timedelta(hours=1),
    )
    alternate = build_player_state_snapshot(
        player_id=PLAYER_ID,
        team_season_id=TEAM_ID,
        game_id=TARGET_GAME_ID,
        as_of=BASE - timedelta(hours=5),
        position=PlayerPosition.QB,
        evidence=(first, second),
        injury_snapshot=injury,
        config=PlayerStateEstimatorConfig(version="NFL_PLAYER_STATE_TEST_V2"),
        created_at=BASE,
    )
    assert left.snapshot_id == right.snapshot_id
    assert left.snapshot_id != alternate.snapshot_id


def test_repository_build_records_sealed_player_state_and_injury_dependency() -> None:
    connection = _connection()
    try:
        injury = _injury_snapshot(as_of=BASE - timedelta(hours=6))
        record_state_snapshot(connection, injury)
        position = _evidence(
            1,
            kind=PlayerEvidenceKind.POSITION,
            available_at=BASE - timedelta(days=30),
            source_game_id=None,
        )
        form = _evidence(
            2,
            kind=PlayerEvidenceKind.PERFORMANCE,
            available_at=BASE - timedelta(days=2),
            metrics=(_metric("passing_efficiency", 0.65),),
        )
        record_player_state_evidence(connection, position)
        record_player_state_evidence(connection, form)
        snapshot = build_player_state_as_of(
            connection,
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            game_id=TARGET_GAME_ID,
            as_of=BASE - timedelta(hours=5),
            injury_snapshot=injury,
            created_at=BASE - timedelta(hours=5) + timedelta(seconds=1),
        )
        assert state_snapshot_is_sealed(connection, snapshot.snapshot_id)
        dependency = connection.execute(
            "SELECT parent_snapshot_id FROM state_snapshot_dependencies "
            "WHERE snapshot_id = ?",
            (str(snapshot.snapshot_id),),
        ).fetchone()
        assert dependency is not None
        assert str(dependency[0]) == str(injury.snapshot_id)
        assert snapshot.state_payload.position is PlayerPosition.QB
    finally:
        connection.close()


def test_late_inactive_rebuilds_player_state_without_rewriting_earlier_state() -> None:
    connection = _connection()
    try:
        evidence = _evidence(
            1,
            kind=PlayerEvidenceKind.POSITION,
            available_at=BASE - timedelta(days=30),
            source_game_id=None,
        )
        record_player_state_evidence(connection, evidence)
        early_injury = _injury_snapshot(
            as_of=BASE - timedelta(hours=6),
            active_status=ActiveStatus.UNKNOWN,
            practice_status=PracticeStatus.LIMITED,
            game_status=GameDesignation.QUESTIONABLE,
        )
        late_injury = _injury_snapshot(
            as_of=BASE - timedelta(minutes=90),
            active_status=ActiveStatus.INACTIVE,
            practice_status=PracticeStatus.LIMITED,
            game_status=GameDesignation.QUESTIONABLE,
        )
        record_state_snapshot(connection, early_injury)
        record_state_snapshot(connection, late_injury)
        early = build_player_state_as_of(
            connection,
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            game_id=TARGET_GAME_ID,
            as_of=BASE - timedelta(hours=5),
            injury_snapshot=early_injury,
            created_at=BASE - timedelta(hours=5) + timedelta(seconds=1),
        )
        late = build_player_state_as_of(
            connection,
            player_id=PLAYER_ID,
            team_season_id=TEAM_ID,
            game_id=TARGET_GAME_ID,
            as_of=BASE - timedelta(minutes=60),
            injury_snapshot=late_injury,
            created_at=BASE - timedelta(minutes=59),
        )
        assert early.state_payload.availability_probability.value > 0.0
        assert late.state_payload.availability_probability.value == 0.0
        assert early.snapshot_id != late.snapshot_id
        assert state_snapshot_is_sealed(connection, early.snapshot_id)
        assert state_snapshot_is_sealed(connection, late.snapshot_id)
    finally:
        connection.close()
