import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    DriveId,
    GameId,
    PlayId,
    PossessionSegmentId,
)
from daily_nfl.persistence import SCHEMA_VERSION, apply_migrations, open_database
from daily_nfl.persistence.migrations import MIGRATIONS
from daily_nfl.providers import (
    NFLVERSE_DESCRIPTOR,
    AcquisitionRequest,
    AcquisitionService,
    DatasetKind,
    FileSystemRawEvidenceStore,
    NflverseAdapter,
    ProviderPayload,
    record_provider,
    record_stored_acquisition,
)
from daily_nfl.reconciliation import (
    FRANCHISE_ENTITY_TYPE,
    TEAM_SEASON_ENTITY_TYPE,
    CanonicalEntityType,
    CrosswalkConflictError,
    DriveIdentityHint,
    ExternalIdentity,
    IdentityReconciler,
    IdentityRepository,
    PlayIdentityHint,
    ReconciliationEvidence,
    ReconciliationReason,
    ReconciliationStatus,
    drive_id_for,
    game_id_for_event,
    new_coach_role_id,
    new_depth_chart_snapshot_id,
    new_event_id,
    new_franchise_id,
    new_injury_observation_id,
    new_roster_stint_id,
    play_id_for,
    possession_id_for,
    possession_segment_id_for,
    team_season_id_for,
)

COMPETITION_ID = "core-competition-nfl"


@contextmanager
def _open_identity_database(path: Path) -> Iterator[sqlite3.Connection]:
    with open_database(path) as connection:
        apply_migrations(connection)
        record_provider(connection, NFLVERSE_DESCRIPTOR)
        yield connection


def _record_fixture_evidence(
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> ReconciliationEvidence:
    observed = datetime(2026, 8, 20, 20, 0, tzinfo=UTC)
    payload = ProviderPayload(
        content=b"fixture-schedule-row",
        content_type="application/octet-stream",
        source_uri="fixture://schedule",
        observed_at=observed,
        available_at=observed,
        availability_method=AvailabilityMethod.OUR_OBSERVATION_TIME,
        availability_confidence=AvailabilityConfidence.HIGH,
    )
    acquisition = AcquisitionService(FileSystemRawEvidenceStore(tmp_path / "raw")).acquire(
        NflverseAdapter(loader=lambda _: (payload,)),
        AcquisitionRequest(dataset=DatasetKind.SCHEDULE),
    )
    record_stored_acquisition(connection, acquisition)
    stored = acquisition.evidence[0]
    return ReconciliationEvidence(
        source_record_id="2026_01_FIXTURE",
        evidence_id=stored.artifact.evidence_id,
        evidence_observation_id=stored.evidence_observation_id,
        evidence_kind="NFLVERSE_SCHEDULE_ROW",
        facts=(("season", "2026"), ("home_team", "FIX")),
    )


def _seed_game_drive_play(
    connection: sqlite3.Connection,
) -> tuple[GameId, PossessionSegmentId, DriveId, PlayId]:
    repository = IdentityRepository(connection)
    home = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    away = new_franchise_id(UUID("22222222-2222-2222-2222-222222222222"))
    repository.ensure_franchise(home)
    repository.ensure_franchise(away)
    home_team = team_season_id_for(home, 2026)
    away_team = team_season_id_for(away, 2026)
    repository.ensure_team_season(home_team, home, 2026)
    repository.ensure_team_season(away_team, away, 2026)

    event_id = new_event_id(UUID("33333333-3333-3333-3333-333333333333"))
    game_id = game_id_for_event(event_id)
    connection.execute(
        """
        INSERT INTO games(
            game_id, event_id, season, season_phase, week, ruleset_version,
            home_team_season_id, away_team_season_id, scheduled_kickoff,
            competition_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(game_id),
            str(event_id),
            2026,
            "REGULAR",
            1,
            "NFL_2026",
            str(home_team),
            str(away_team),
            "2026-09-10T17:20:00Z",
            COMPETITION_ID,
        ),
    )

    possession_id = possession_id_for(game_id, 1)
    segment_id = possession_segment_id_for(game_id, 1)
    drive_id = drive_id_for(game_id, 1)
    play_id = play_id_for(game_id, 1)
    connection.execute(
        """
        INSERT INTO possessions(
            possession_id, game_id, offense_team_season_id, defense_team_season_id
        ) VALUES (?, ?, ?, ?)
        """,
        (str(possession_id), str(game_id), str(home_team), str(away_team)),
    )
    connection.execute(
        """
        INSERT INTO possession_segments(
            possession_segment_id, game_id, canonical_sequence,
            offense_team_season_id, defense_team_season_id
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (str(segment_id), str(game_id), 1, str(home_team), str(away_team)),
    )
    connection.execute(
        """
        INSERT INTO drives(
            drive_id, game_id, possession_id, canonical_sequence, possession_segment_id
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (str(drive_id), str(game_id), str(possession_id), 1, str(segment_id)),
    )
    connection.execute(
        """
        INSERT INTO plays(
            play_id, game_id, drive_id, possession_id,
            canonical_sequence, possession_segment_id
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(play_id),
            str(game_id),
            str(drive_id),
            str(possession_id),
            1,
            str(segment_id),
        ),
    )
    return game_id, segment_id, drive_id, play_id


def _apply_through_v5(connection: sqlite3.Connection) -> None:
    for migration in MIGRATIONS:
        if migration.version > 5:
            break
        escaped_name = migration.name.replace("'", "''")
        connection.executescript(
            "BEGIN IMMEDIATE;\n"
            f"{migration.sql}\n"
            "INSERT INTO schema_migrations(version, name) "
            f"VALUES ({migration.version}, '{escaped_name}');\n"
            "COMMIT;"
        )


def test_f3_identity_vocabulary_and_opaque_generators_are_complete() -> None:
    required = {
        "FRANCHISE",
        "TEAM_SEASON",
        "PLAYER",
        "ROSTER_STINT",
        "COACH_ROLE",
        "GAME",
        "DRIVE",
        "PLAY",
        "PLAY_EVENT",
        "INJURY_OBSERVATION",
        "DEPTH_CHART_SNAPSHOT",
        "PARTICIPATION",
    }
    assert required.issubset({entity.value for entity in CanonicalEntityType})

    roster = new_roster_stint_id(UUID("11111111-1111-1111-1111-111111111111"))
    coach = new_coach_role_id(UUID("22222222-2222-2222-2222-222222222222"))
    injury = new_injury_observation_id(UUID("33333333-3333-3333-3333-333333333333"))
    depth = new_depth_chart_snapshot_id(UUID("44444444-4444-4444-4444-444444444444"))

    assert str(roster).startswith("rst_")
    assert str(coach).startswith("cor_")
    assert str(injury).startswith("inj_")
    assert str(depth).startswith("dcs_")
    assert all("nflverse" not in value for value in map(str, (roster, coach, injury, depth)))


def test_same_team_external_id_maps_to_distinct_team_seasons(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    franchise_id = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))

    with _open_identity_database(database) as connection:
        repository = IdentityRepository(connection)
        reconciler = IdentityReconciler(repository)
        repository.ensure_franchise(franchise_id)
        reconciler.bind_verified(
            external=ExternalIdentity("nflverse", FRANCHISE_ENTITY_TYPE, "SF"),
            canonical_entity_type=CanonicalEntityType.FRANCHISE,
            canonical_entity_id=str(franchise_id),
        )

        season_2025 = reconciler.resolve_team_season(
            provider_id="nflverse",
            external_team_id="SF",
            season=2025,
        )
        season_2026 = reconciler.resolve_team_season(
            provider_id="nflverse",
            external_team_id="SF",
            season=2026,
        )

        assert season_2025.resolved and season_2026.resolved
        assert season_2025.selected_canonical_entity_id == str(
            team_season_id_for(franchise_id, 2025)
        )
        assert season_2026.selected_canonical_entity_id == str(
            team_season_id_for(franchise_id, 2026)
        )
        assert season_2025.selected_canonical_entity_id != season_2026.selected_canonical_entity_id

        rows = connection.execute(
            """
            SELECT canonical_entity_id, valid_from, valid_to
            FROM entity_crosswalk
            WHERE provider_entity_type = ? AND external_id = 'SF'
            ORDER BY valid_from
            """,
            (TEAM_SEASON_ENTITY_TYPE,),
        ).fetchall()
        assert len(rows) == 2
        assert rows[0][1] != rows[1][1]
        assert rows[0][2] < rows[1][1]


def test_legacy_timeless_team_season_mapping_fails_closed_for_other_season(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"
    franchise_id = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))

    with _open_identity_database(database) as connection:
        repository = IdentityRepository(connection)
        reconciler = IdentityReconciler(repository)
        repository.ensure_franchise(franchise_id)
        team_2025 = team_season_id_for(franchise_id, 2025)
        repository.ensure_team_season(team_2025, franchise_id, 2025)
        reconciler.bind_verified(
            external=ExternalIdentity("nflverse", TEAM_SEASON_ENTITY_TYPE, "SF"),
            canonical_entity_type=CanonicalEntityType.TEAM_SEASON,
            canonical_entity_id=str(team_2025),
        )

        decision = reconciler.resolve_team_season(
            provider_id="nflverse",
            external_team_id="SF",
            season=2026,
        )

        assert decision.status is ReconciliationStatus.CONFLICT
        assert decision.reason is ReconciliationReason.EXISTING_MAPPING_CONTEXT_MISMATCH
        assert decision.selected_canonical_entity_id is None


def test_unresolved_decision_persists_raw_source_evidence(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"

    with _open_identity_database(database) as connection:
        evidence = _record_fixture_evidence(connection, tmp_path)
        decision = IdentityReconciler(IdentityRepository(connection)).resolve(
            ExternalIdentity("nflverse", "PLAYER", "missing-player"),
            CanonicalEntityType.PLAYER,
            evidence=(evidence,),
        )
        row = connection.execute(
            """
            SELECT source_record_id, evidence_id, evidence_observation_id,
                   evidence_kind, facts_json
            FROM identity_reconciliation_evidence
            WHERE decision_id = ?
            """,
            (decision.decision_id,),
        ).fetchone()

        assert decision.status is ReconciliationStatus.UNRESOLVED
        assert row is not None
        assert row[0] == "2026_01_FIXTURE"
        assert row[1] == evidence.evidence_id
        assert row[2] == evidence.evidence_observation_id
        assert row[3] == "NFLVERSE_SCHEDULE_ROW"
        assert json.loads(str(row[4])) == {"home_team": "FIX", "season": "2026"}


def test_drive_and_play_provider_ids_can_change_without_canonical_identity_change(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"

    with _open_identity_database(database) as connection:
        game_id, segment_id, drive_id, play_id = _seed_game_drive_play(connection)
        reconciler = IdentityReconciler(IdentityRepository(connection))
        drive_hint = DriveIdentityHint(
            game_id=game_id,
            canonical_sequence=1,
            possession_segment_id=segment_id,
        )
        play_hint = PlayIdentityHint(
            game_id=game_id,
            canonical_sequence=1,
            drive_id=drive_id,
        )

        first_drive = reconciler.reconcile_drive(
            provider_id="nflverse",
            external_drive_id="provider-drive-old",
            hint=drive_hint,
        )
        second_drive = reconciler.reconcile_drive(
            provider_id="nflverse",
            external_drive_id="provider-drive-new",
            hint=drive_hint,
        )
        first_play = reconciler.reconcile_play(
            provider_id="nflverse",
            external_play_id="provider-play-old",
            hint=play_hint,
        )
        second_play = reconciler.reconcile_play(
            provider_id="nflverse",
            external_play_id="provider-play-new",
            hint=play_hint,
        )

        assert first_drive.selected_canonical_entity_id == str(drive_id)
        assert second_drive.selected_canonical_entity_id == str(drive_id)
        assert first_play.selected_canonical_entity_id == str(play_id)
        assert second_play.selected_canonical_entity_id == str(play_id)


def test_resolution_metadata_change_requires_explicit_supersession(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    franchise_id = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))

    with _open_identity_database(database) as connection:
        repository = IdentityRepository(connection)
        reconciler = IdentityReconciler(repository)
        repository.ensure_franchise(franchise_id)
        reconciler.bind_verified(
            external=ExternalIdentity("nflverse", FRANCHISE_ENTITY_TYPE, "SF"),
            canonical_entity_type=CanonicalEntityType.FRANCHISE,
            canonical_entity_id=str(franchise_id),
        )
        derived = reconciler.resolve_team_season(
            provider_id="nflverse",
            external_team_id="SF",
            season=2026,
        )
        assert derived.selected_canonical_entity_id is not None
        existing = repository.active_crosswalks(
            ExternalIdentity(
                "nflverse",
                TEAM_SEASON_ENTITY_TYPE,
                "SF",
                datetime(2026, 9, 1, tzinfo=UTC),
            )
        )[0]
        external = ExternalIdentity("nflverse", TEAM_SEASON_ENTITY_TYPE, "SF")

        before = connection.execute(
            "SELECT COUNT(*) FROM identity_reconciliation_decisions"
        ).fetchone()[0]
        with pytest.raises(CrosswalkConflictError, match="explicit supersession"):
            reconciler.bind_verified(
                external=external,
                canonical_entity_type=CanonicalEntityType.TEAM_SEASON,
                canonical_entity_id=derived.selected_canonical_entity_id,
                valid_from=existing.valid_from,
                valid_to=existing.valid_to,
            )
        after = connection.execute(
            "SELECT COUNT(*) FROM identity_reconciliation_decisions"
        ).fetchone()[0]
        assert after == before

        reconciler.bind_verified(
            external=external,
            canonical_entity_type=CanonicalEntityType.TEAM_SEASON,
            canonical_entity_id=derived.selected_canonical_entity_id,
            valid_from=existing.valid_from,
            valid_to=existing.valid_to,
            supersedes_crosswalk_id=existing.crosswalk_id,
        )
        current = repository.active_crosswalks(
            ExternalIdentity(
                "nflverse",
                TEAM_SEASON_ENTITY_TYPE,
                "SF",
                datetime(2026, 9, 1, tzinfo=UTC),
            )
        )
        assert len(current) == 1
        assert current[0].verified is True
        assert current[0].supersedes_crosswalk_id == existing.crosswalk_id


def test_reconciliation_evidence_is_append_only(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"

    with _open_identity_database(database) as connection:
        evidence = _record_fixture_evidence(connection, tmp_path)
        decision = IdentityReconciler(IdentityRepository(connection)).resolve(
            ExternalIdentity("nflverse", "PLAYER", "missing-player"),
            CanonicalEntityType.PLAYER,
            evidence=(evidence,),
        )

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                """
                UPDATE identity_reconciliation_evidence
                SET evidence_kind = 'CHANGED'
                WHERE decision_id = ?
                """,
                (decision.decision_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM identity_reconciliation_evidence WHERE decision_id = ?",
                (decision.decision_id,),
            )


def test_v6_migration_preserves_v5_identity_history(tmp_path: Path) -> None:
    database = tmp_path / "m3-to-m4.db"

    with open_database(database) as connection:
        _apply_through_v5(connection)
        connection.execute(
            "INSERT INTO providers(provider_id, name, provider_type) VALUES (?, ?, ?)",
            ("legacy-provider", "Legacy Provider", "TEST"),
        )
        connection.execute(
            "INSERT INTO franchises(franchise_id, canonical_name) VALUES (?, ?)",
            ("frn_legacy", "Legacy Franchise"),
        )
        connection.execute(
            """
            INSERT INTO identity_reconciliation_decisions(
                decision_id, provider_id, provider_entity_type, external_id,
                expected_canonical_entity_type, status, selected_canonical_entity_id,
                match_method, match_confidence, candidate_count, reason_code, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "idr_legacy",
                "legacy-provider",
                "FRANCHISE",
                "LEG",
                "FRANCHISE",
                "RESOLVED",
                "frn_legacy",
                "MANUAL_VERIFIED",
                1.0,
                1,
                "VERIFIED_BINDING_CREATED",
                '{"candidates":[]}',
            ),
        )
        connection.execute(
            """
            INSERT INTO entity_crosswalk(
                canonical_entity_type, canonical_entity_id, provider_id,
                provider_entity_type, external_id, match_method,
                match_confidence, verified, decision_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "FRANCHISE",
                "frn_legacy",
                "legacy-provider",
                "FRANCHISE",
                "LEG",
                "MANUAL_VERIFIED",
                1.0,
                1,
                "idr_legacy",
            ),
        )
        connection.commit()

        assert apply_migrations(connection) == SCHEMA_VERSION
        legacy = connection.execute(
            """
            SELECT canonical_entity_id, decision_id
            FROM entity_crosswalk
            WHERE provider_id = 'legacy-provider'
            """
        ).fetchone()
        table = connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type='table' AND name='identity_reconciliation_evidence'
            """
        ).fetchone()

        assert legacy is not None
        assert tuple(legacy) == ("frn_legacy", "idr_legacy")
        assert table is not None
