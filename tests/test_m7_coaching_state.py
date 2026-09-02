from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    CoachingAssignmentObservationId,
    CoachingSchemeEvidenceObservationId,
    CoachingStint,
    CoachingStintId,
    GameId,
    KnowledgeTimestamp,
    PersonId,
    PublicSchemeLabelObservationId,
    TeamSeasonId,
)
from daily_nfl.persistence import SCHEMA_VERSION, apply_migrations, connect_database
from daily_nfl.persistence.migrations import MIGRATIONS, current_schema_version
from daily_nfl.state import (
    CoachingAssignmentObservation,
    CoachingEvidenceScope,
    CoachingGameStateCondition,
    CoachingResponsibility,
    CoachingRoleType,
    CoachingSchemeEvidenceObservation,
    CoachingStateComponent,
    CoachingStateEstimatorConfig,
    NamedMoments,
    NumericMoments,
    Probability,
    PublicSchemeLabelObservation,
    PublicSchemeSide,
    StateSubjectType,
    build_coaching_state_as_of,
    build_coaching_state_snapshot,
    coaching_assignments_as_of,
    coaching_regime_id,
    coaching_scheme_evidence_as_of,
    public_scheme_labels_as_of,
    record_coaching_assignment_observation,
    record_coaching_scheme_evidence,
    record_public_scheme_label_observation,
    state_snapshot_is_sealed,
)

TEAM_ID = TeamSeasonId("team-coaching-2026")
AWAY_TEAM_ID = TeamSeasonId("team-coaching-away-2026")
GAME_ID = GameId("game-coaching-target")
OTHER_GAME_ID = GameId("game-coaching-other")
PRIOR_GAME_ID = GameId("game-coaching-prior")
HC_ID = PersonId("coach-hc")
OC_ID = PersonId("coach-oc")
DC_ID = PersonId("coach-dc")
ALT_ID = PersonId("coach-alt")
BASE = datetime(2026, 9, 13, 16, 0, tzinfo=UTC)
CHANGE = BASE - timedelta(days=2)


def _connection() -> sqlite3.Connection:
    connection = connect_database(":memory:")
    apply_migrations(connection)
    _seed_core(connection)
    return connection


def _seed_core(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO providers(provider_id, name, provider_type) "
        "VALUES ('coaching-test', 'Coaching Test', 'TEST')"
    )
    connection.execute(
        "INSERT INTO franchises(franchise_id, canonical_name) "
        "VALUES ('fr-coaching', 'Coaching')"
    )
    connection.execute(
        "INSERT INTO franchises(franchise_id, canonical_name) "
        "VALUES ('fr-coaching-away', 'Coaching Away')"
    )
    connection.execute(
        """
        INSERT INTO team_seasons(team_season_id, franchise_id, season, display_name)
        VALUES ('team-coaching-2026', 'fr-coaching', 2026, 'Coaching 2026')
        """
    )
    connection.execute(
        """
        INSERT INTO team_seasons(team_season_id, franchise_id, season, display_name)
        VALUES (
            'team-coaching-away-2026', 'fr-coaching-away', 2026,
            'Coaching Away 2026'
        )
        """
    )
    for person_id, name in (
        (HC_ID, "Head Coach"),
        (OC_ID, "Offensive Coordinator"),
        (DC_ID, "Defensive Coordinator"),
        (ALT_ID, "Alternate Coach"),
    ):
        connection.execute(
            "INSERT INTO persons(person_id, canonical_name) VALUES (?, ?)",
            (str(person_id), name),
        )
    for game_id, event_id, week, kickoff in (
        (PRIOR_GAME_ID, "event-coaching-prior", 1, "2026-09-06T20:00:00Z"),
        (GAME_ID, "event-coaching-target", 2, "2026-09-13T20:00:00Z"),
        (OTHER_GAME_ID, "event-coaching-other", 3, "2026-09-20T20:00:00Z"),
    ):
        connection.execute(
            """
            INSERT INTO games(
                game_id, event_id, season, season_phase, week, ruleset_version,
                home_team_season_id, away_team_season_id, scheduled_kickoff,
                neutral_site, competition_id
            ) VALUES (?, ?, 2026, 'REGULAR', ?, 'NFL-2026', ?, ?, ?, 0, 'nfl')
            """,
            (
                str(game_id),
                event_id,
                week,
                str(TEAM_ID),
                str(AWAY_TEAM_ID),
                kickoff,
            ),
        )


def _knowledge(available_at: datetime) -> KnowledgeTimestamp:
    return KnowledgeTimestamp(
        available_at=available_at,
        published_at=available_at,
        observed_at=available_at,
        ingested_at=available_at,
        availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
        availability_confidence=AvailabilityConfidence.HIGH,
    )


def _metric(name: str, mean: float, variance: float = 0.04) -> NamedMoments:
    return NamedMoments(name=name, estimate=NumericMoments(mean, variance))


def _condition(
    *,
    neutral: bool = True,
    down: str | None = "EARLY_DOWN",
    score: str | None = "ONE_SCORE",
) -> CoachingGameStateCondition:
    return CoachingGameStateCondition(
        neutral_situation=neutral,
        down_bucket=down,
        score_state=score,
        time_state="FIRST_THREE_QUARTERS",
    )


def _assignment(
    number: int,
    *,
    person_id: PersonId,
    role_type: CoachingRoleType,
    logical_key: str,
    available_at: datetime,
    responsibilities: tuple[CoachingResponsibility, ...] = (),
    revision: int = 1,
    effective_from: datetime | None = None,
    effective_to: datetime | None = None,
    stint_key: str | None = None,
) -> CoachingAssignmentObservation:
    return CoachingAssignmentObservation(
        observation_id=CoachingAssignmentObservationId(f"coach-assignment-{number}"),
        coaching_stint_id=CoachingStintId(
            f"coach-stint-{stint_key or str(person_id)}"
        ),
        person_id=person_id,
        team_season_id=TEAM_ID,
        logical_key=logical_key,
        revision=revision,
        role_type=role_type,
        responsibilities=responsibilities,
        effective_from=effective_from,
        effective_to=effective_to,
        assignment_contract="NFL_COACHING_ASSIGNMENT_TEST_V1",
        assignment_version="1",
        provider_id="coaching-test",
        knowledge=_knowledge(available_at),
    )


def _base_assignments(
    *,
    as_of: datetime,
    include_callers: bool = True,
) -> tuple[CoachingAssignmentObservation, ...]:
    assignments = [
        _assignment(
            1,
            person_id=HC_ID,
            role_type=CoachingRoleType.HEAD_COACH,
            logical_key="head-coach",
            available_at=as_of - timedelta(days=60),
            effective_from=as_of - timedelta(days=200),
        ),
        _assignment(
            2,
            person_id=OC_ID,
            role_type=CoachingRoleType.OFFENSIVE_COORDINATOR,
            logical_key="offensive-coordinator",
            available_at=as_of - timedelta(days=60),
            effective_from=as_of - timedelta(days=200),
        ),
        _assignment(
            3,
            person_id=DC_ID,
            role_type=CoachingRoleType.DEFENSIVE_COORDINATOR,
            logical_key="defensive-coordinator",
            available_at=as_of - timedelta(days=60),
            effective_from=as_of - timedelta(days=200),
        ),
    ]
    if include_callers:
        assignments.extend(
            (
                _assignment(
                    4,
                    person_id=OC_ID,
                    role_type=CoachingRoleType.OTHER,
                    logical_key="offensive-play-caller",
                    available_at=as_of - timedelta(days=60),
                    responsibilities=(CoachingResponsibility.OFFENSIVE_PLAY_CALLER,),
                    effective_from=as_of - timedelta(days=200),
                    stint_key="oc",
                ),
                _assignment(
                    5,
                    person_id=DC_ID,
                    role_type=CoachingRoleType.OTHER,
                    logical_key="defensive-play-caller",
                    available_at=as_of - timedelta(days=60),
                    responsibilities=(CoachingResponsibility.DEFENSIVE_PLAY_CALLER,),
                    effective_from=as_of - timedelta(days=200),
                    stint_key="dc",
                ),
            )
        )
    return tuple(assignments)


def _scheme(
    number: int,
    *,
    component: CoachingStateComponent,
    available_at: datetime,
    metric_name: str,
    metric_value: float,
    scope: CoachingEvidenceScope = CoachingEvidenceScope.BASE,
    condition: CoachingGameStateCondition | None = None,
    source_game_id: GameId | None = PRIOR_GAME_ID,
    applies_to_game_id: GameId | None = None,
    logical_key: str | None = None,
    revision: int = 1,
) -> CoachingSchemeEvidenceObservation:
    if condition is None:
        condition = _condition()
    if scope is CoachingEvidenceScope.GAME_SPECIFIC_DEVIATION:
        applies_to_game_id = applies_to_game_id or GAME_ID
    return CoachingSchemeEvidenceObservation(
        observation_id=CoachingSchemeEvidenceObservationId(f"coach-scheme-{number}"),
        team_season_id=TEAM_ID,
        source_game_id=source_game_id,
        applies_to_game_id=applies_to_game_id,
        logical_key=logical_key or f"coach-scheme-key-{number}",
        revision=revision,
        component=component,
        evidence_scope=scope,
        condition=condition,
        metrics=(_metric(metric_name, metric_value),),
        sample_weight=4.0,
        source_confidence=Probability(0.95),
        evidence_contract="NFL_COACHING_SCHEME_TEST_V1",
        evidence_version="1",
        provider_id="coaching-test",
        knowledge=_knowledge(available_at),
    )


def _label(number: int, *, available_at: datetime) -> PublicSchemeLabelObservation:
    return PublicSchemeLabelObservation(
        observation_id=PublicSchemeLabelObservationId(f"public-scheme-{number}"),
        team_season_id=TEAM_ID,
        side=PublicSchemeSide.OFFENSE,
        logical_key="public-offense-label",
        revision=1,
        label="West Coast offense",
        provider_id="coaching-test",
        knowledge=_knowledge(available_at),
    )


def test_schema_contains_forward_only_v12_coaching_foundation() -> None:
    connection = connect_database(":memory:")
    try:
        assert apply_migrations(connection) == SCHEMA_VERSION
        assert SCHEMA_VERSION >= 12
        assert MIGRATIONS[11].version == 12
        assert MIGRATIONS[11].name == "m7_coaching_scheme_state_evidence_foundation"
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {
            "coaching_stints",
            "coaching_assignment_observations",
            "coaching_scheme_evidence_observations",
            "public_scheme_label_observations",
        }.issubset(tables)
    finally:
        connection.close()


def test_migration_v12_upgrades_applied_v11_without_rewriting_history() -> None:
    connection = connect_database(":memory:")
    try:
        for migration in MIGRATIONS[:11]:
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (migration.version, migration.name),
            )
        rows_before = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert current_schema_version(connection) == 11
        migration_v12 = MIGRATIONS[11]
        connection.executescript(migration_v12.sql)
        connection.execute(
            "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
            (migration_v12.version, migration_v12.name),
        )
        rows_after = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert current_schema_version(connection) == 12
        assert [tuple(row) for row in rows_after[:11]] == [
            tuple(row) for row in rows_before
        ]
        assert tuple(rows_after[11]) == (
            12,
            "m7_coaching_scheme_state_evidence_foundation",
        )
    finally:
        connection.close()


def test_coaching_stint_is_distinct_from_role_assignment() -> None:
    stint = CoachingStint(
        coaching_stint_id=CoachingStintId("stint-hc"),
        person_id=HC_ID,
        team_season_id=TEAM_ID,
        started_at=BASE - timedelta(days=200),
    )
    assert stint.person_id == HC_ID
    assert stint.team_season_id == TEAM_ID


def test_assignment_repository_is_idempotent_append_only_and_pit_selectable() -> None:
    connection = _connection()
    try:
        assignment = _base_assignments(as_of=BASE)[0]
        record_coaching_assignment_observation(connection, assignment)
        record_coaching_assignment_observation(connection, assignment)
        selected = coaching_assignments_as_of(
            connection,
            team_season_id=TEAM_ID,
            as_of=BASE,
        )
        assert selected == (assignment,)
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE coaching_assignment_observations SET revision = 2 "
                "WHERE observation_id = ?",
                (str(assignment.observation_id),),
            )
    finally:
        connection.close()


def test_assignment_revision_selection_is_point_in_time() -> None:
    connection = _connection()
    try:
        first = _assignment(
            1,
            person_id=OC_ID,
            role_type=CoachingRoleType.OFFENSIVE_COORDINATOR,
            logical_key="oc-correction",
            revision=1,
            available_at=BASE - timedelta(days=10),
            effective_from=BASE - timedelta(days=100),
            stint_key="oc",
        )
        correction = _assignment(
            2,
            person_id=OC_ID,
            role_type=CoachingRoleType.OFFENSIVE_COORDINATOR,
            logical_key="oc-correction",
            revision=2,
            available_at=BASE - timedelta(days=2),
            responsibilities=(CoachingResponsibility.OFFENSIVE_PLAY_CALLER,),
            effective_from=BASE - timedelta(days=100),
            stint_key="oc",
        )
        record_coaching_assignment_observation(connection, first)
        record_coaching_assignment_observation(connection, correction)
        early = coaching_assignments_as_of(
            connection,
            team_season_id=TEAM_ID,
            as_of=BASE - timedelta(days=5),
        )
        late = coaching_assignments_as_of(
            connection,
            team_season_id=TEAM_ID,
            as_of=BASE,
        )
        assert early == (first,)
        assert late == (correction,)
    finally:
        connection.close()


def test_coaching_regime_identity_is_assignment_order_independent() -> None:
    assignments = _base_assignments(as_of=BASE)
    assert coaching_regime_id(assignments) == coaching_regime_id(
        tuple(reversed(assignments))
    )


def test_play_caller_change_creates_new_regime_without_changing_head_coach() -> None:
    early_assignments = _base_assignments(as_of=BASE)
    early = build_coaching_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE - timedelta(days=3),
        assignment_observations=early_assignments,
        scheme_evidence=(),
        created_at=BASE - timedelta(days=3) + timedelta(seconds=1),
    )
    late_assignments = tuple(
        item
        for item in early_assignments
        if item.logical_key != "offensive-play-caller"
    ) + (
        _assignment(
            20,
            person_id=ALT_ID,
            role_type=CoachingRoleType.OTHER,
            logical_key="new-offensive-play-caller",
            available_at=CHANGE,
            responsibilities=(CoachingResponsibility.OFFENSIVE_PLAY_CALLER,),
            effective_from=CHANGE,
            stint_key="alt",
        ),
    )
    late = build_coaching_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE - timedelta(days=1),
        assignment_observations=late_assignments,
        scheme_evidence=(),
        created_at=BASE - timedelta(days=1) + timedelta(seconds=1),
    )
    assert early.state_payload.head_coach_id == late.state_payload.head_coach_id == HC_ID
    assert early.state_payload.offensive_play_caller_id == OC_ID
    assert late.state_payload.offensive_play_caller_id == ALT_ID
    assert early.state_payload.regime_id != late.state_payload.regime_id
    assert early.snapshot_id != late.snapshot_id


def test_unknown_play_callers_remain_unknown_not_fabricated() -> None:
    snapshot = build_coaching_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE,
        assignment_observations=_base_assignments(as_of=BASE, include_callers=False),
        scheme_evidence=(),
        created_at=BASE + timedelta(seconds=1),
    )
    assert snapshot.state_payload.offensive_play_caller_id is None
    assert snapshot.state_payload.defensive_play_caller_id is None
    unknown_names = {item.name for item in snapshot.uncertainty.unknowns}
    assert "offensive_play_caller" in unknown_names
    assert "defensive_play_caller" in unknown_names


def test_multiple_active_head_coaches_fail_closed() -> None:
    assignments = _base_assignments(as_of=BASE) + (
        _assignment(
            30,
            person_id=ALT_ID,
            role_type=CoachingRoleType.HEAD_COACH,
            logical_key="second-head-coach",
            available_at=BASE - timedelta(days=1),
            effective_from=BASE - timedelta(days=1),
            stint_key="alt",
        ),
    )
    with pytest.raises(ValueError, match="multiple active coaching assignments claim HEAD_COACH"):
        build_coaching_state_snapshot(
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            as_of=BASE,
            assignment_observations=assignments,
            scheme_evidence=(),
            created_at=BASE + timedelta(seconds=1),
        )


def test_multiple_active_offensive_play_callers_fail_closed() -> None:
    assignments = _base_assignments(as_of=BASE) + (
        _assignment(
            31,
            person_id=ALT_ID,
            role_type=CoachingRoleType.OTHER,
            logical_key="second-offensive-caller",
            available_at=BASE - timedelta(days=1),
            responsibilities=(CoachingResponsibility.OFFENSIVE_PLAY_CALLER,),
            effective_from=BASE - timedelta(days=1),
            stint_key="alt",
        ),
    )
    with pytest.raises(
        ValueError,
        match="multiple active coaching assignments claim OFFENSIVE_PLAY_CALLER",
    ):
        build_coaching_state_snapshot(
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            as_of=BASE,
            assignment_observations=assignments,
            scheme_evidence=(),
            created_at=BASE + timedelta(seconds=1),
        )


def test_unconditional_tendency_evidence_is_rejected() -> None:
    empty_condition = CoachingGameStateCondition()
    with pytest.raises(ValueError, match="explicitly game-state conditioned"):
        _scheme(
            1,
            component=CoachingStateComponent.OFFENSIVE_SCHEME,
            available_at=BASE - timedelta(days=1),
            metric_name="neutral_pass_rate",
            metric_value=0.60,
            condition=empty_condition,
        )


def test_conditioned_tendencies_remain_separate_policy_buckets() -> None:
    early_down = _scheme(
        1,
        component=CoachingStateComponent.OFFENSIVE_SCHEME,
        available_at=BASE - timedelta(days=7),
        metric_name="pass_rate",
        metric_value=0.62,
        condition=_condition(down="EARLY_DOWN", score="ONE_SCORE"),
    )
    late_lead = _scheme(
        2,
        component=CoachingStateComponent.OFFENSIVE_SCHEME,
        available_at=BASE - timedelta(days=7),
        metric_name="pass_rate",
        metric_value=0.31,
        condition=CoachingGameStateCondition(
            neutral_situation=False,
            down_bucket="ANY_DOWN",
            score_state="LEADING_9_PLUS",
            time_state="FOURTH_QUARTER",
        ),
    )
    snapshot = build_coaching_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE,
        assignment_observations=_base_assignments(as_of=BASE),
        scheme_evidence=(early_down, late_lead),
        created_at=BASE + timedelta(seconds=1),
    )
    estimates = snapshot.state_payload.offensive_scheme_state.base_estimates
    assert len(estimates) == 2
    assert {item.condition.score_state for item in estimates} == {
        "ONE_SCORE",
        "LEADING_9_PLUS",
    }


def test_public_scheme_label_is_descriptive_not_empirical_scheme_state() -> None:
    label = _label(1, available_at=BASE - timedelta(days=10))
    snapshot = build_coaching_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE,
        assignment_observations=_base_assignments(as_of=BASE),
        scheme_evidence=(),
        public_scheme_labels=(label,),
        created_at=BASE + timedelta(seconds=1),
    )
    assert snapshot.state_payload.public_scheme_labels == (label,)
    assert snapshot.state_payload.offensive_scheme_state.base_estimates == ()


def test_scheme_and_coaching_effectiveness_are_separate_dimensions() -> None:
    scheme = _scheme(
        1,
        component=CoachingStateComponent.OFFENSIVE_SCHEME,
        available_at=BASE - timedelta(days=7),
        metric_name="neutral_pass_rate",
        metric_value=0.62,
    )
    effectiveness = _scheme(
        2,
        component=CoachingStateComponent.COACHING_EFFECTIVENESS,
        available_at=BASE - timedelta(days=7),
        metric_name="decision_quality",
        metric_value=0.74,
        condition=CoachingGameStateCondition(),
        source_game_id=None,
    )
    snapshot = build_coaching_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE,
        assignment_observations=_base_assignments(as_of=BASE),
        scheme_evidence=(scheme, effectiveness),
        created_at=BASE + timedelta(seconds=1),
    )
    assert (
        snapshot.state_payload.offensive_scheme_state.base_estimates[0].metrics[0].name
        == "neutral_pass_rate"
    )
    assert snapshot.state_payload.coaching_effectiveness_state.metrics[0].name == (
        "decision_quality"
    )


def test_base_scheme_and_game_specific_deviation_remain_separate() -> None:
    base = _scheme(
        1,
        component=CoachingStateComponent.DEFENSIVE_SCHEME,
        available_at=BASE - timedelta(days=7),
        metric_name="blitz_rate",
        metric_value=0.24,
    )
    deviation = _scheme(
        2,
        component=CoachingStateComponent.DEFENSIVE_SCHEME,
        available_at=BASE - timedelta(hours=12),
        metric_name="blitz_rate_delta",
        metric_value=0.10,
        scope=CoachingEvidenceScope.GAME_SPECIFIC_DEVIATION,
        applies_to_game_id=GAME_ID,
        source_game_id=None,
    )
    snapshot = build_coaching_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE,
        assignment_observations=_base_assignments(as_of=BASE),
        scheme_evidence=(base, deviation),
        created_at=BASE + timedelta(seconds=1),
    )
    state = snapshot.state_payload.defensive_scheme_state
    assert state.base_estimates[0].metrics[0].name == "blitz_rate"
    assert state.game_specific_deviation_estimates[0].metrics[0].name == (
        "blitz_rate_delta"
    )


def test_game_specific_deviation_for_wrong_game_fails_closed_directly() -> None:
    deviation = _scheme(
        1,
        component=CoachingStateComponent.OFFENSIVE_SCHEME,
        available_at=BASE - timedelta(hours=12),
        metric_name="motion_rate_delta",
        metric_value=0.08,
        scope=CoachingEvidenceScope.GAME_SPECIFIC_DEVIATION,
        applies_to_game_id=OTHER_GAME_ID,
        source_game_id=None,
    )
    with pytest.raises(ValueError, match="applies to a different game"):
        build_coaching_state_snapshot(
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            as_of=BASE,
            assignment_observations=_base_assignments(as_of=BASE),
            scheme_evidence=(deviation,),
            created_at=BASE + timedelta(seconds=1),
        )


def test_current_target_game_behavior_cannot_enter_pregame_coaching_state() -> None:
    leaked = _scheme(
        1,
        component=CoachingStateComponent.OFFENSIVE_SCHEME,
        available_at=BASE - timedelta(minutes=1),
        metric_name="pass_rate",
        metric_value=0.90,
        source_game_id=GAME_ID,
    )
    with pytest.raises(ValueError, match="current pregame target game"):
        build_coaching_state_snapshot(
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            as_of=BASE,
            assignment_observations=_base_assignments(as_of=BASE),
            scheme_evidence=(leaked,),
            created_at=BASE + timedelta(seconds=1),
        )


def test_post_cutoff_coaching_evidence_fails_closed() -> None:
    late = _scheme(
        1,
        component=CoachingStateComponent.OFFENSIVE_SCHEME,
        available_at=BASE + timedelta(minutes=1),
        metric_name="pass_rate",
        metric_value=0.90,
    )
    with pytest.raises(ValueError, match="cannot be available after Coaching State as_of"):
        build_coaching_state_snapshot(
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            as_of=BASE,
            assignment_observations=_base_assignments(as_of=BASE),
            scheme_evidence=(late,),
            created_at=BASE + timedelta(seconds=1),
        )


def test_repository_filters_target_game_source_and_wrong_game_deviation() -> None:
    connection = _connection()
    try:
        valid = _scheme(
            1,
            component=CoachingStateComponent.OFFENSIVE_SCHEME,
            available_at=BASE - timedelta(days=7),
            metric_name="pass_rate",
            metric_value=0.60,
        )
        leaked = _scheme(
            2,
            component=CoachingStateComponent.OFFENSIVE_SCHEME,
            available_at=BASE - timedelta(hours=1),
            metric_name="pass_rate",
            metric_value=0.95,
            source_game_id=GAME_ID,
        )
        wrong_game = _scheme(
            3,
            component=CoachingStateComponent.OFFENSIVE_SCHEME,
            available_at=BASE - timedelta(hours=1),
            metric_name="motion_delta",
            metric_value=0.10,
            scope=CoachingEvidenceScope.GAME_SPECIFIC_DEVIATION,
            applies_to_game_id=OTHER_GAME_ID,
            source_game_id=None,
        )
        for item in (valid, leaked, wrong_game):
            record_coaching_scheme_evidence(connection, item)
        selected = coaching_scheme_evidence_as_of(
            connection,
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            as_of=BASE,
        )
        assert selected == (valid,)
    finally:
        connection.close()


def test_scheme_and_public_label_rows_are_append_only() -> None:
    connection = _connection()
    try:
        scheme = _scheme(
            1,
            component=CoachingStateComponent.DEFENSIVE_SCHEME,
            available_at=BASE - timedelta(days=7),
            metric_name="blitz_rate",
            metric_value=0.24,
        )
        label = _label(1, available_at=BASE - timedelta(days=7))
        record_coaching_scheme_evidence(connection, scheme)
        record_public_scheme_label_observation(connection, label)
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE coaching_scheme_evidence_observations SET revision = 2 "
                "WHERE observation_id = ?",
                (str(scheme.observation_id),),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM public_scheme_label_observations WHERE observation_id = ?",
                (str(label.observation_id),),
            )
    finally:
        connection.close()


def test_public_label_revision_is_pit_selectable() -> None:
    connection = _connection()
    try:
        first = _label(1, available_at=BASE - timedelta(days=10))
        second = PublicSchemeLabelObservation(
            observation_id=PublicSchemeLabelObservationId("public-scheme-2"),
            team_season_id=TEAM_ID,
            side=PublicSchemeSide.OFFENSE,
            logical_key=first.logical_key,
            revision=2,
            label="Spread offense",
            provider_id="coaching-test",
            knowledge=_knowledge(BASE - timedelta(days=2)),
        )
        record_public_scheme_label_observation(connection, first)
        record_public_scheme_label_observation(connection, second)
        early = public_scheme_labels_as_of(
            connection,
            team_season_id=TEAM_ID,
            as_of=BASE - timedelta(days=5),
        )
        late = public_scheme_labels_as_of(
            connection,
            team_season_id=TEAM_ID,
            as_of=BASE,
        )
        assert early == (first,)
        assert late == (second,)
    finally:
        connection.close()


def test_coaching_state_identity_is_input_order_independent_and_model_versioned() -> None:
    assignments = _base_assignments(as_of=BASE)
    first = _scheme(
        1,
        component=CoachingStateComponent.OFFENSIVE_SCHEME,
        available_at=BASE - timedelta(days=7),
        metric_name="pass_rate",
        metric_value=0.60,
    )
    second = _scheme(
        2,
        component=CoachingStateComponent.DEFENSIVE_SCHEME,
        available_at=BASE - timedelta(days=7),
        metric_name="blitz_rate",
        metric_value=0.24,
    )
    left = build_coaching_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE,
        assignment_observations=assignments,
        scheme_evidence=(first, second),
        created_at=BASE + timedelta(seconds=1),
    )
    right = build_coaching_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE,
        assignment_observations=tuple(reversed(assignments)),
        scheme_evidence=(second, first),
        created_at=BASE + timedelta(hours=1),
    )
    alternate = build_coaching_state_snapshot(
        team_season_id=TEAM_ID,
        game_id=GAME_ID,
        as_of=BASE,
        assignment_observations=assignments,
        scheme_evidence=(first, second),
        config=CoachingStateEstimatorConfig(version="NFL_COACHING_STATE_TEST_V2"),
        created_at=BASE + timedelta(seconds=1),
    )
    assert left.snapshot_id == right.snapshot_id
    assert left.snapshot_id != alternate.snapshot_id


def test_repository_build_records_sealed_coaching_state_with_exact_inputs() -> None:
    connection = _connection()
    try:
        assignments = _base_assignments(as_of=BASE)
        scheme = _scheme(
            1,
            component=CoachingStateComponent.OFFENSIVE_SCHEME,
            available_at=BASE - timedelta(days=7),
            metric_name="pass_rate",
            metric_value=0.60,
        )
        label = _label(1, available_at=BASE - timedelta(days=7))
        for assignment in assignments:
            record_coaching_assignment_observation(connection, assignment)
        record_coaching_scheme_evidence(connection, scheme)
        record_public_scheme_label_observation(connection, label)
        snapshot = build_coaching_state_as_of(
            connection,
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            as_of=BASE,
            created_at=BASE + timedelta(seconds=1),
        )
        assert state_snapshot_is_sealed(connection, snapshot.snapshot_id)
        assert snapshot.subject_type is StateSubjectType.COACHING_REGIME
        assert snapshot.state_payload.head_coach_id == HC_ID
        assert snapshot.state_payload.offensive_play_caller_id == OC_ID
        input_tables = {item.source_table for item in snapshot.input_observations}
        assert input_tables == {
            "coaching_assignment_observations",
            "coaching_scheme_evidence_observations",
            "public_scheme_label_observations",
        }
        stored_input_count = connection.execute(
            "SELECT COUNT(*) FROM state_snapshot_inputs WHERE snapshot_id = ?",
            (str(snapshot.snapshot_id),),
        ).fetchone()
        assert stored_input_count is not None
        assert int(stored_input_count[0]) == len(snapshot.input_observations)
    finally:
        connection.close()
