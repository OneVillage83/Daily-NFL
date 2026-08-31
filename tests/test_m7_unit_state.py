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
    UnitConfigurationObservationId,
    UnitStateEvidenceObservationId,
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
    PlayerStateEvidenceObservation,
    PlayerStatePayload,
    PracticeStatus,
    Probability,
    StateSnapshotConflictError,
    StateSnapshotEnvelope,
    StateSubjectType,
    UnitConfigurationAlternative,
    UnitConfigurationObservation,
    UnitEvidenceKind,
    UnitMemberAssignment,
    UnitStateEvidenceObservation,
    UnitStatePayload,
    UnitType,
    build_injury_availability_snapshot,
    build_player_state_snapshot,
    build_unit_state_as_of,
    build_unit_state_snapshot,
    record_state_snapshot,
    record_unit_configuration_observation,
    record_unit_state_evidence,
    state_snapshot_is_sealed,
    unit_configuration_observations_as_of,
    unit_state_evidence_as_of,
)

TEAM_ID = TeamSeasonId("team-unit-2026")
AWAY_TEAM_ID = TeamSeasonId("team-unit-away-2026")
GAME_ID = GameId("game-unit-target")
PRIOR_GAME_ID = GameId("game-unit-prior")
STARTER_ID = PlayerId("player-unit-starter")
BACKUP_ID = PlayerId("player-unit-backup")
ANCHOR_ID = PlayerId("player-unit-anchor")
BASE = datetime(2026, 9, 13, 16, 0, tzinfo=UTC)
UNIT_TYPE = UnitType.OFFENSIVE_LINE


def _connection() -> sqlite3.Connection:
    connection = connect_database(":memory:")
    apply_migrations(connection)
    _seed_core(connection)
    return connection


def _seed_core(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO providers(provider_id, name, provider_type) "
        "VALUES ('unit-test', 'Unit Test', 'TEST')"
    )
    connection.execute(
        "INSERT INTO franchises(franchise_id, canonical_name) VALUES ('fr-unit', 'Unit')"
    )
    connection.execute(
        "INSERT INTO franchises(franchise_id, canonical_name) "
        "VALUES ('fr-unit-away', 'Unit Away')"
    )
    connection.execute(
        """
        INSERT INTO team_seasons(team_season_id, franchise_id, season, display_name)
        VALUES ('team-unit-2026', 'fr-unit', 2026, 'Unit 2026')
        """
    )
    connection.execute(
        """
        INSERT INTO team_seasons(team_season_id, franchise_id, season, display_name)
        VALUES ('team-unit-away-2026', 'fr-unit-away', 2026, 'Unit Away 2026')
        """
    )
    for suffix in ("starter", "backup", "anchor"):
        connection.execute(
            "INSERT INTO persons(person_id, canonical_name) VALUES (?, ?)",
            (f"person-unit-{suffix}", f"Unit {suffix.title()}"),
        )
        connection.execute(
            "INSERT INTO players(player_id, person_id) VALUES (?, ?)",
            (f"player-unit-{suffix}", f"person-unit-{suffix}"),
        )
    connection.execute(
        """
        INSERT INTO games(
            game_id, event_id, season, season_phase, week, ruleset_version,
            home_team_season_id, away_team_season_id, scheduled_kickoff,
            neutral_site, competition_id
        ) VALUES (
            'game-unit-prior', 'event-unit-prior', 2026, 'REGULAR', 1,
            'NFL-2026', 'team-unit-2026', 'team-unit-away-2026',
            '2026-09-06T20:00:00Z', 0, 'nfl'
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
            'game-unit-target', 'event-unit-target', 2026, 'REGULAR', 2,
            'NFL-2026', 'team-unit-2026', 'team-unit-away-2026',
            '2026-09-13T20:00:00Z', 0, 'nfl'
        )
        """
    )


def _metric(name: str, mean: float, variance: float = 0.04) -> NamedMoments:
    return NamedMoments(name=name, estimate=NumericMoments(mean, variance))


def _knowledge(available_at: datetime) -> KnowledgeTimestamp:
    return KnowledgeTimestamp(
        available_at=available_at,
        published_at=available_at,
        observed_at=available_at,
        ingested_at=available_at,
        availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
        availability_confidence=AvailabilityConfidence.HIGH,
    )


def _injury_snapshot(
    player_id: PlayerId,
    *,
    as_of: datetime,
    active_status: ActiveStatus,
) -> StateSnapshotEnvelope[InjuryAvailabilityState]:
    if active_status is ActiveStatus.UNKNOWN:
        practice = PracticeStatus.LIMITED
        designation = GameDesignation.QUESTIONABLE
    else:
        practice = PracticeStatus.FULL
        designation = GameDesignation.NO_DESIGNATION
    observation = InjuryObservation(
        injury_observation_id=InjuryObservationId(
            f"injury-unit-{player_id}-{int(as_of.timestamp())}-{active_status.value}"
        ),
        player_id=player_id,
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        provider_id="unit-test",
        source_id=f"injury-source-{player_id}-{int(as_of.timestamp())}",
        practice_status=practice,
        game_status=designation,
        active_status=active_status,
        source_confidence=Probability(0.95),
        knowledge=_knowledge(as_of),
    )
    return build_injury_availability_snapshot(
        player_id=player_id,
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=as_of,
        observations=(observation,),
        created_at=as_of + timedelta(seconds=1),
    )


def _player_snapshot(
    player_id: PlayerId,
    *,
    as_of: datetime,
    active_status: ActiveStatus = ActiveStatus.ACTIVE,
    talent: float = 0.7,
    form: float = 0.65,
) -> tuple[
    StateSnapshotEnvelope[InjuryAvailabilityState],
    StateSnapshotEnvelope[PlayerStatePayload],
]:
    injury = _injury_snapshot(
        player_id,
        as_of=as_of - timedelta(minutes=5),
        active_status=active_status,
    )
    suffix = str(player_id).removeprefix("player-unit-")
    evidence = (
        PlayerStateEvidenceObservation(
            observation_id=PlayerStateEvidenceObservationId(
                f"talent-unit-{suffix}-{int(as_of.timestamp())}"
            ),
            player_id=player_id,
            logical_key=f"talent-{suffix}",
            revision=1,
            team_season_id=TEAM_ID,
            source_game_id=None,
            position=PlayerPosition.OT,
            evidence_kind=PlayerEvidenceKind.TALENT,
            metrics=(_metric("pass_protection", talent),),
            sample_weight=4.0,
            source_confidence=Probability(0.95),
            evidence_contract="NFL_PLAYER_UNIT_TEST_V1",
            evidence_version="1",
            knowledge=_knowledge(as_of - timedelta(days=30)),
        ),
        PlayerStateEvidenceObservation(
            observation_id=PlayerStateEvidenceObservationId(
                f"form-unit-{suffix}-{int(as_of.timestamp())}"
            ),
            player_id=player_id,
            logical_key=f"form-{suffix}",
            revision=1,
            team_season_id=TEAM_ID,
            source_game_id=PRIOR_GAME_ID,
            position=PlayerPosition.OT,
            evidence_kind=PlayerEvidenceKind.PERFORMANCE,
            metrics=(_metric("pass_protection_form", form),),
            sample_weight=4.0,
            source_confidence=Probability(0.95),
            evidence_contract="NFL_PLAYER_UNIT_TEST_V1",
            evidence_version="1",
            knowledge=_knowledge(as_of - timedelta(days=3)),
        ),
    )
    player = build_player_state_snapshot(
        player_id=player_id,
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=as_of,
        position=PlayerPosition.OT,
        evidence=evidence,
        injury_snapshot=injury,
        created_at=as_of + timedelta(seconds=1),
    )
    return injury, player


def _configuration(
    number: int,
    *,
    available_at: datetime,
    starter_probability: float = 0.8,
    logical_key: str = "offensive-line-role-prior",
    revision: int = 1,
) -> UnitConfigurationObservation:
    starter = UnitConfigurationAlternative(
        members=(
            UnitMemberAssignment(STARTER_ID, "LT"),
            UnitMemberAssignment(ANCHOR_ID, "LG"),
        ),
        prior_probability=Probability(starter_probability),
    )
    backup = UnitConfigurationAlternative(
        members=(
            UnitMemberAssignment(BACKUP_ID, "LT"),
            UnitMemberAssignment(ANCHOR_ID, "LG"),
        ),
        prior_probability=Probability(1.0 - starter_probability),
    )
    return UnitConfigurationObservation(
        observation_id=UnitConfigurationObservationId(f"unit-config-observation-{number}"),
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        unit_type=UNIT_TYPE,
        logical_key=logical_key,
        revision=revision,
        alternatives=(starter, backup),
        configuration_contract="NFL_UNIT_CONFIGURATION_ROLE_PRIOR_V1",
        configuration_version="1",
        provider_id="unit-test",
        knowledge=_knowledge(available_at),
    )


def _unit_evidence(
    number: int,
    *,
    kind: UnitEvidenceKind,
    available_at: datetime,
    source_game_id: GameId | None = PRIOR_GAME_ID,
    logical_key: str | None = None,
    revision: int = 1,
    residualized: bool | None = None,
) -> UnitStateEvidenceObservation:
    if residualized is None:
        residualized = kind in {
            UnitEvidenceKind.ROLE_COMPATIBILITY,
            UnitEvidenceKind.SYNERGY,
            UnitEvidenceKind.RECENT_PERFORMANCE,
        }
    return UnitStateEvidenceObservation(
        observation_id=UnitStateEvidenceObservationId(f"unit-evidence-{number}"),
        team_season_id=TEAM_ID,
        source_game_id=source_game_id,
        unit_type=UNIT_TYPE,
        logical_key=logical_key or f"unit-evidence-key-{number}",
        revision=revision,
        evidence_kind=kind,
        metrics=(_metric(kind.value.lower(), 0.7),),
        sample_weight=3.0,
        source_confidence=Probability(0.9),
        residualized_against_player_state=residualized,
        evidence_contract="NFL_UNIT_EVIDENCE_TEST_V1",
        evidence_version="1",
        provider_id="unit-test",
        knowledge=_knowledge(available_at),
    )


def _players(
    *,
    as_of: datetime,
    starter_status: ActiveStatus = ActiveStatus.ACTIVE,
) -> tuple[
    tuple[StateSnapshotEnvelope[InjuryAvailabilityState], ...],
    tuple[StateSnapshotEnvelope[PlayerStatePayload], ...],
]:
    pairs = (
        _player_snapshot(STARTER_ID, as_of=as_of, active_status=starter_status, talent=0.8),
        _player_snapshot(BACKUP_ID, as_of=as_of, talent=0.6),
        _player_snapshot(ANCHOR_ID, as_of=as_of, talent=0.75),
    )
    return tuple(pair[0] for pair in pairs), tuple(pair[1] for pair in pairs)


def _unit_snapshot(
    *,
    as_of: datetime,
    starter_status: ActiveStatus = ActiveStatus.ACTIVE,
    evidence: tuple[UnitStateEvidenceObservation, ...] = (),
) -> StateSnapshotEnvelope[UnitStatePayload]:
    _, players = _players(as_of=as_of - timedelta(minutes=5), starter_status=starter_status)
    return build_unit_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        unit_type=UNIT_TYPE,
        as_of=as_of,
        configuration_observations=(
            _configuration(1, available_at=as_of - timedelta(hours=1)),
        ),
        unit_evidence=evidence,
        player_snapshots=players,
        created_at=as_of + timedelta(seconds=1),
    )


def test_schema_contains_v11_unit_foundation_after_current_migrations() -> None:
    connection = connect_database(":memory:")
    try:
        assert apply_migrations(connection) == SCHEMA_VERSION
        assert SCHEMA_VERSION >= 11
        assert MIGRATIONS[10].version == 11
        assert MIGRATIONS[10].name == "m7_unit_state_evidence_foundation"
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {
            "unit_configuration_observations",
            "unit_state_evidence_observations",
        }.issubset(tables)
    finally:
        connection.close()


def test_migration_v11_upgrades_applied_v10_without_rewriting_history() -> None:
    connection = connect_database(":memory:")
    try:
        for migration in MIGRATIONS[:10]:
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (migration.version, migration.name),
            )
        rows_before = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert current_schema_version(connection) == 10
        migration_v11 = MIGRATIONS[10]
        connection.executescript(migration_v11.sql)
        connection.execute(
            "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
            (migration_v11.version, migration_v11.name),
        )
        rows_after = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert current_schema_version(connection) == 11
        assert [tuple(row) for row in rows_after[:10]] == [
            tuple(row) for row in rows_before
        ]
        assert tuple(rows_after[10]) == (11, "m7_unit_state_evidence_foundation")
    finally:
        connection.close()


def test_configuration_identity_and_hash_are_order_invariant() -> None:
    first = UnitConfigurationAlternative(
        members=(
            UnitMemberAssignment(STARTER_ID, "LT"),
            UnitMemberAssignment(ANCHOR_ID, "LG"),
        ),
        prior_probability=Probability(1.0),
    )
    second = UnitConfigurationAlternative(
        members=(
            UnitMemberAssignment(ANCHOR_ID, "LG"),
            UnitMemberAssignment(STARTER_ID, "LT"),
        ),
        prior_probability=Probability(1.0),
    )
    assert first.configuration_id == second.configuration_id


def test_configuration_observation_is_idempotent_append_only_and_pit_selectable() -> None:
    connection = _connection()
    try:
        observation = _configuration(1, available_at=BASE - timedelta(hours=8))
        record_unit_configuration_observation(connection, observation)
        record_unit_configuration_observation(connection, observation)
        selected = unit_configuration_observations_as_of(
            connection,
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE - timedelta(hours=6),
        )
        assert selected == (observation,)
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE unit_configuration_observations SET revision = 2 "
                "WHERE observation_id = ?",
                (str(observation.observation_id),),
            )
    finally:
        connection.close()


def test_configuration_revision_selection_is_point_in_time() -> None:
    connection = _connection()
    try:
        first = _configuration(
            1,
            available_at=BASE - timedelta(hours=8),
            revision=1,
            starter_probability=0.8,
        )
        second = _configuration(
            2,
            available_at=BASE - timedelta(hours=2),
            revision=2,
            starter_probability=0.6,
        )
        record_unit_configuration_observation(connection, first)
        record_unit_configuration_observation(connection, second)
        early = unit_configuration_observations_as_of(
            connection,
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE - timedelta(hours=6),
        )
        late = unit_configuration_observations_as_of(
            connection,
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE - timedelta(hours=1),
        )
        assert early == (first,)
        assert late == (second,)
    finally:
        connection.close()


def test_interaction_unit_evidence_requires_player_state_residualization() -> None:
    for kind in (
        UnitEvidenceKind.ROLE_COMPATIBILITY,
        UnitEvidenceKind.SYNERGY,
        UnitEvidenceKind.RECENT_PERFORMANCE,
    ):
        with pytest.raises(ValueError, match="residualized against Player State"):
            _unit_evidence(
                1,
                kind=kind,
                available_at=BASE - timedelta(days=1),
                residualized=False,
            )


def test_continuity_evidence_does_not_require_residualization() -> None:
    observation = _unit_evidence(
        1,
        kind=UnitEvidenceKind.CONTINUITY,
        available_at=BASE - timedelta(days=1),
        residualized=False,
    )
    assert observation.residualized_against_player_state is False


def test_unit_evidence_repository_excludes_current_target_game() -> None:
    connection = _connection()
    try:
        current_game = _unit_evidence(
            1,
            kind=UnitEvidenceKind.CONTINUITY,
            available_at=BASE - timedelta(hours=1),
            source_game_id=GAME_ID,
        )
        record_unit_state_evidence(connection, current_game)
        selected = unit_state_evidence_as_of(
            connection,
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE,
        )
        assert selected == ()
    finally:
        connection.close()


def test_unit_type_contract_covers_primary_functional_units() -> None:
    assert {
        UnitType.OFFENSIVE_LINE,
        UnitType.RECEIVING,
        UnitType.BACKFIELD,
        UnitType.PASS_PROTECTION,
        UnitType.RUN_BLOCKING,
        UnitType.DEFENSIVE_FRONT,
        UnitType.PASS_RUSH,
        UnitType.RUN_DEFENSE,
        UnitType.COVERAGE,
        UnitType.SECONDARY,
        UnitType.FIELD_GOAL,
        UnitType.PUNT_COVERAGE,
        UnitType.KICK_COVERAGE,
    }.issubset(set(UnitType))


def test_unit_state_reweights_role_prior_using_player_availability_once() -> None:
    healthy = _unit_snapshot(as_of=BASE - timedelta(hours=4))
    inactive = _unit_snapshot(
        as_of=BASE - timedelta(hours=1),
        starter_status=ActiveStatus.INACTIVE,
    )
    healthy_probabilities = {
        tuple(str(member.player_id) for member in item.members): item.posterior_probability.value
        for item in healthy.state_payload.member_distribution
    }
    inactive_probabilities = {
        tuple(str(member.player_id) for member in item.members): item.posterior_probability.value
        for item in inactive.state_payload.member_distribution
    }
    starter_members = (str(STARTER_ID), str(ANCHOR_ID))
    backup_members = (str(BACKUP_ID), str(ANCHOR_ID))
    assert healthy_probabilities[starter_members] == pytest.approx(0.8)
    assert healthy_probabilities[backup_members] == pytest.approx(0.2)
    assert inactive_probabilities[starter_members] == 0.0
    assert inactive_probabilities[backup_members] == 1.0


def test_unit_state_fails_closed_when_no_configuration_is_viable() -> None:
    _, players = _players(
        as_of=BASE - timedelta(hours=5),
        starter_status=ActiveStatus.INACTIVE,
    )
    inactive_players = []
    for snapshot in players:
        if snapshot.state_payload.player_id in {BACKUP_ID, ANCHOR_ID}:
            _, replacement = _player_snapshot(
                snapshot.state_payload.player_id,
                as_of=BASE - timedelta(hours=5),
                active_status=ActiveStatus.INACTIVE,
            )
            inactive_players.append(replacement)
        else:
            inactive_players.append(snapshot)
    with pytest.raises(ValueError, match="no viable unit configuration"):
        build_unit_state_snapshot(
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE - timedelta(hours=4),
            configuration_observations=(
                _configuration(1, available_at=BASE - timedelta(hours=6)),
            ),
            unit_evidence=(),
            player_snapshots=tuple(inactive_players),
            created_at=BASE - timedelta(hours=4) + timedelta(seconds=1),
        )


def test_unit_state_requires_exact_player_parent_membership() -> None:
    _, players = _players(as_of=BASE - timedelta(hours=5))
    with pytest.raises(ValueError, match="exactly match configuration members"):
        build_unit_state_snapshot(
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE - timedelta(hours=4),
            configuration_observations=(
                _configuration(1, available_at=BASE - timedelta(hours=6)),
            ),
            unit_evidence=(),
            player_snapshots=players[:-1],
            created_at=BASE - timedelta(hours=4) + timedelta(seconds=1),
        )


def test_unit_state_keeps_member_quality_form_and_residual_unit_signal_separate() -> None:
    recent = _unit_evidence(
        1,
        kind=UnitEvidenceKind.RECENT_PERFORMANCE,
        available_at=BASE - timedelta(days=1),
    )
    snapshot = _unit_snapshot(as_of=BASE - timedelta(hours=4), evidence=(recent,))
    assert snapshot.state_payload.intrinsic_quality_state.metrics[0].name == "pass_protection"
    assert snapshot.state_payload.member_form_state.metrics[0].name == "pass_protection_form"
    assert (
        snapshot.state_payload.recent_performance_residual_state.metrics[0].name
        == "recent_performance"
    )


def test_missing_unit_interactions_and_scheme_fit_remain_explicit_unknowns() -> None:
    snapshot = _unit_snapshot(as_of=BASE - timedelta(hours=4))
    unknown_names = {item.name for item in snapshot.uncertainty.unknowns}
    assert "continuity_state" in unknown_names
    assert "synergy_state" in unknown_names
    assert "scheme_fit_state" in unknown_names
    assert snapshot.state_payload.scheme_state_id is None


def test_conflicting_configuration_sources_fail_closed() -> None:
    _, players = _players(as_of=BASE - timedelta(hours=5))
    first = _configuration(
        1,
        available_at=BASE - timedelta(hours=6),
        logical_key="source-a",
        starter_probability=0.8,
    )
    second = _configuration(
        2,
        available_at=BASE - timedelta(hours=6),
        logical_key="source-b",
        starter_probability=0.6,
    )
    with pytest.raises(ValueError, match="conflicting unit configuration distributions"):
        build_unit_state_snapshot(
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE - timedelta(hours=4),
            configuration_observations=(first, second),
            unit_evidence=(),
            player_snapshots=players,
            created_at=BASE - timedelta(hours=4) + timedelta(seconds=1),
        )


def test_post_cutoff_configuration_and_unit_evidence_fail_closed() -> None:
    _, players = _players(as_of=BASE - timedelta(hours=5))
    late_config = _configuration(1, available_at=BASE + timedelta(minutes=1))
    with pytest.raises(ValueError, match="configuration cannot be available after"):
        build_unit_state_snapshot(
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE,
            configuration_observations=(late_config,),
            unit_evidence=(),
            player_snapshots=players,
            created_at=BASE + timedelta(seconds=1),
        )
    late_evidence = _unit_evidence(
        2,
        kind=UnitEvidenceKind.CONTINUITY,
        available_at=BASE + timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="unit evidence cannot be available after"):
        build_unit_state_snapshot(
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE,
            configuration_observations=(
                _configuration(2, available_at=BASE - timedelta(hours=1)),
            ),
            unit_evidence=(late_evidence,),
            player_snapshots=players,
            created_at=BASE + timedelta(seconds=1),
        )


def test_current_target_game_direct_unit_evidence_fails_closed() -> None:
    _, players = _players(as_of=BASE - timedelta(hours=5))
    evidence = _unit_evidence(
        1,
        kind=UnitEvidenceKind.CONTINUITY,
        available_at=BASE - timedelta(hours=1),
        source_game_id=GAME_ID,
    )
    with pytest.raises(ValueError, match="current pregame target game"):
        build_unit_state_snapshot(
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE,
            configuration_observations=(
                _configuration(1, available_at=BASE - timedelta(hours=2)),
            ),
            unit_evidence=(evidence,),
            player_snapshots=players,
            created_at=BASE + timedelta(seconds=1),
        )


def test_unit_state_identity_is_player_parent_order_independent() -> None:
    _, players = _players(as_of=BASE - timedelta(hours=5))
    configuration_observations = (
        _configuration(1, available_at=BASE - timedelta(hours=6)),
    )
    first = build_unit_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        unit_type=UNIT_TYPE,
        as_of=BASE - timedelta(hours=4),
        configuration_observations=configuration_observations,
        unit_evidence=(),
        player_snapshots=players,
        created_at=BASE,
    )
    second = build_unit_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        unit_type=UNIT_TYPE,
        as_of=BASE - timedelta(hours=4),
        configuration_observations=configuration_observations,
        unit_evidence=(),
        player_snapshots=tuple(reversed(players)),
        created_at=BASE + timedelta(hours=1),
    )
    assert first.snapshot_id == second.snapshot_id


def test_unit_snapshot_inputs_do_not_reingest_player_evidence() -> None:
    continuity = _unit_evidence(
        1,
        kind=UnitEvidenceKind.CONTINUITY,
        available_at=BASE - timedelta(days=1),
    )
    snapshot = _unit_snapshot(as_of=BASE - timedelta(hours=4), evidence=(continuity,))
    assert {item.source_table for item in snapshot.input_observations} == {
        "unit_configuration_observations",
        "unit_state_evidence_observations",
    }
    assert len(snapshot.input_state_snapshot_ids) == 3


def test_repository_requires_player_state_parents_to_be_sealed() -> None:
    connection = _connection()
    try:
        config = _configuration(1, available_at=BASE - timedelta(hours=6))
        record_unit_configuration_observation(connection, config)
        _, players = _players(as_of=BASE - timedelta(hours=5))
        with pytest.raises(StateSnapshotConflictError, match="missing or unsealed"):
            build_unit_state_as_of(
                connection,
                team_season_id=TEAM_ID,
                game_id=GAME_ID,
                unit_type=UNIT_TYPE,
                as_of=BASE - timedelta(hours=4),
                player_snapshots=players,
                created_at=BASE - timedelta(hours=4) + timedelta(seconds=1),
            )
    finally:
        connection.close()


def _persist_player_tree(
    connection: sqlite3.Connection,
    *,
    as_of: datetime,
    starter_status: ActiveStatus = ActiveStatus.ACTIVE,
) -> tuple[StateSnapshotEnvelope[PlayerStatePayload], ...]:
    injuries, players = _players(as_of=as_of, starter_status=starter_status)
    for injury, player in zip(injuries, players, strict=True):
        record_state_snapshot(connection, injury)
        record_state_snapshot(connection, player)
    return players


def test_repository_build_records_sealed_unit_with_exact_player_dependencies() -> None:
    connection = _connection()
    try:
        config = _configuration(1, available_at=BASE - timedelta(hours=6))
        continuity = _unit_evidence(
            1,
            kind=UnitEvidenceKind.CONTINUITY,
            available_at=BASE - timedelta(days=1),
        )
        record_unit_configuration_observation(connection, config)
        record_unit_state_evidence(connection, continuity)
        players = _persist_player_tree(connection, as_of=BASE - timedelta(hours=5))
        snapshot = build_unit_state_as_of(
            connection,
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE - timedelta(hours=4),
            player_snapshots=players,
            created_at=BASE - timedelta(hours=4) + timedelta(seconds=1),
        )
        assert state_snapshot_is_sealed(connection, snapshot.snapshot_id)
        dependencies = connection.execute(
            "SELECT parent_snapshot_id FROM state_snapshot_dependencies "
            "WHERE snapshot_id = ? ORDER BY parent_snapshot_id",
            (str(snapshot.snapshot_id),),
        ).fetchall()
        assert {str(row[0]) for row in dependencies} == {
            str(player.snapshot_id) for player in players
        }
        assert snapshot.subject_type is StateSubjectType.UNIT
    finally:
        connection.close()


def test_late_inactive_creates_new_unit_state_and_preserves_earlier_snapshot() -> None:
    connection = _connection()
    try:
        config = _configuration(1, available_at=BASE - timedelta(hours=8))
        record_unit_configuration_observation(connection, config)
        early_players = _persist_player_tree(
            connection,
            as_of=BASE - timedelta(hours=6),
            starter_status=ActiveStatus.UNKNOWN,
        )
        early = build_unit_state_as_of(
            connection,
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE - timedelta(hours=5),
            player_snapshots=early_players,
            created_at=BASE - timedelta(hours=5) + timedelta(seconds=1),
        )
        late_players = _persist_player_tree(
            connection,
            as_of=BASE - timedelta(minutes=90),
            starter_status=ActiveStatus.INACTIVE,
        )
        late = build_unit_state_as_of(
            connection,
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            unit_type=UNIT_TYPE,
            as_of=BASE - timedelta(minutes=60),
            player_snapshots=late_players,
            created_at=BASE - timedelta(minutes=59),
        )
        early_starter_probability = next(
            item.posterior_probability.value
            for item in early.state_payload.member_distribution
            if any(member.player_id == STARTER_ID for member in item.members)
        )
        late_starter_probability = next(
            item.posterior_probability.value
            for item in late.state_payload.member_distribution
            if any(member.player_id == STARTER_ID for member in item.members)
        )
        assert early_starter_probability > 0.0
        assert late_starter_probability == 0.0
        assert early.snapshot_id != late.snapshot_id
        assert state_snapshot_is_sealed(connection, early.snapshot_id)
        assert state_snapshot_is_sealed(connection, late.snapshot_id)
    finally:
        connection.close()
