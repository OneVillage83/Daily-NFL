import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    KnowledgeTimestamp,
)
from daily_nfl.normalization import (
    NflverseGameContext,
    NflversePlayRecord,
    NormalizationProvenance,
    NormalizedPlayConflictError,
    ProviderPenaltyRecord,
    normalize_nflverse_play,
    normalized_play_observation_id,
    record_normalized_play,
)
from daily_nfl.persistence import apply_migrations, open_database
from daily_nfl.providers import (
    NFLVERSE_DESCRIPTOR,
    DatasetKind,
    record_provider,
    record_provider_capability,
)
from daily_nfl.reconciliation import (
    IdentityRepository,
    game_id_for_event,
    new_event_id,
    new_franchise_id,
    play_id_for,
    team_season_id_for,
)

COMPETITION_ID = "core-competition-nfl"
EVIDENCE_ID = "evidence-m6-fixture"
EVIDENCE_OBSERVATION_ID = "reo_m6_fixture"
RAW_SHA256 = "a" * 64


def _context_and_game(connection: sqlite3.Connection) -> NflverseGameContext:
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
            game_id,
            event_id,
            season,
            season_phase,
            week,
            ruleset_version,
            home_team_season_id,
            away_team_season_id,
            scheduled_kickoff,
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
            "2026-09-13T20:20:00+00:00",
            COMPETITION_ID,
        ),
    )
    return NflverseGameContext(
        game_id=game_id,
        home_team_code="HOM",
        away_team_code="AWY",
        home_team_season_id=home_team,
        away_team_season_id=away_team,
    )


def _record(*, yards: int, penalty: bool = False) -> NflversePlayRecord:
    penalties = (
        ProviderPenaltyRecord(team_code="AWY", penalty_type="Offside", yards=5),
    ) if penalty else ()
    return NflversePlayRecord(
        provider_game_id="2026_01_AWY_HOM",
        provider_play_id="100",
        provider_drive_id="1",
        offense_team_code="HOM",
        defense_team_code="AWY",
        period=1,
        quarter_seconds_remaining=840,
        down=1,
        distance=10,
        yards_to_goal=75,
        home_score_before=0,
        away_score_before=0,
        source_row_index=1,
        pass_attempt=True,
        complete_pass=True,
        official_yards_gained=yards,
        first_down=yards >= 10,
        penalties=penalties,
    )


def _knowledge(offset_seconds: int = 0) -> KnowledgeTimestamp:
    observed = datetime(2026, 9, 13, 19, 0, tzinfo=UTC) + timedelta(
        seconds=offset_seconds
    )
    return KnowledgeTimestamp(
        available_at=observed,
        effective_at=observed - timedelta(seconds=30),
        published_at=observed - timedelta(seconds=5),
        observed_at=observed,
        ingested_at=observed + timedelta(seconds=1),
        availability_method=AvailabilityMethod.OUR_OBSERVATION_TIME,
        availability_confidence=AvailabilityConfidence.HIGH,
    )


def _required_iso(value: datetime | None, label: str) -> str:
    if value is None:
        raise AssertionError(f"fixture knowledge requires {label}")
    return value.isoformat()


def _seed_raw_acquisition(connection: sqlite3.Connection) -> None:
    record_provider(connection, NFLVERSE_DESCRIPTOR)
    capability = NFLVERSE_DESCRIPTOR.capability_for(DatasetKind.PLAY_BY_PLAY)
    assert capability is not None
    capability_id = record_provider_capability(
        connection,
        NFLVERSE_DESCRIPTOR,
        capability,
    )
    knowledge = _knowledge()
    connection.execute(
        """
        INSERT INTO raw_evidence(
            evidence_id,
            provider_id,
            endpoint_category,
            source_uri,
            content_type,
            sha256,
            object_path,
            observed_at,
            ingested_at,
            available_at,
            availability_method,
            availability_confidence,
            provider_schema_version,
            parser_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            EVIDENCE_ID,
            "nflverse",
            DatasetKind.PLAY_BY_PLAY.value,
            "fixture://m6/pbp",
            "application/octet-stream",
            RAW_SHA256,
            "fixture/m6-pbp.bin",
            _required_iso(knowledge.observed_at, "observed_at"),
            _required_iso(knowledge.ingested_at, "ingested_at"),
            knowledge.available_at.isoformat(),
            knowledge.availability_method.value,
            knowledge.availability_confidence.value,
            capability.schema_version,
            NFLVERSE_DESCRIPTOR.parser_version,
        ),
    )
    connection.execute(
        """
        INSERT INTO raw_evidence_observations(
            evidence_observation_id,
            evidence_id,
            provider_id,
            dataset,
            capability_id,
            source_uri,
            observed_at,
            ingested_at,
            available_at,
            availability_method,
            availability_confidence,
            provider_schema_version,
            parser_version,
            license_id,
            license_url,
            attribution_required,
            attribution_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            EVIDENCE_OBSERVATION_ID,
            EVIDENCE_ID,
            "nflverse",
            DatasetKind.PLAY_BY_PLAY.value,
            capability_id,
            "fixture://m6/pbp",
            _required_iso(knowledge.observed_at, "observed_at"),
            _required_iso(knowledge.ingested_at, "ingested_at"),
            knowledge.available_at.isoformat(),
            knowledge.availability_method.value,
            knowledge.availability_confidence.value,
            capability.schema_version,
            NFLVERSE_DESCRIPTOR.parser_version,
            capability.license_id,
            capability.license_url,
            int(capability.attribution_required),
            capability.attribution_text,
        ),
    )


def _provenance(
    *,
    observation_id: str,
    offset_seconds: int = 0,
    revision: str,
) -> NormalizationProvenance:
    return NormalizationProvenance(
        observation_id=observation_id,
        knowledge=_knowledge(offset_seconds),
        evidence_id=EVIDENCE_ID,
        evidence_observation_id=EVIDENCE_OBSERVATION_ID,
        provider_revision=revision,
    )


def test_normalized_play_persistence_is_idempotent_and_provider_neutral(tmp_path: Path) -> None:
    database = tmp_path / "m6.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        _seed_raw_acquisition(connection)
        context = _context_and_game(connection)
        bundle = normalize_nflverse_play(
            _record(yards=12, penalty=True),
            context=context,
            canonical_sequence=1,
            drive_sequence=1,
            possession_sequence=1,
        )
        observation_id = normalized_play_observation_id(
            evidence_id=EVIDENCE_ID,
            evidence_observation_id=EVIDENCE_OBSERVATION_ID,
            provider_id="nflverse",
            provider_play_id="100",
            provider_revision="r1",
        )
        provenance = _provenance(observation_id=observation_id, revision="r1")

        record_normalized_play(connection, bundle, provenance)
        record_normalized_play(connection, bundle, provenance)

        assert connection.execute("SELECT COUNT(*) FROM possessions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM possession_segments").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM drives").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM plays").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM play_events").fetchone()[0] == 4
        assert connection.execute("SELECT COUNT(*) FROM penalties").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM play_observations").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM penalty_observations").fetchone()[0] == 1
        row = connection.execute(
            """
            SELECT play_id, evidence_observation_id, normalized_payload_json
            FROM play_observations
            """
        ).fetchone()
        penalty_row = connection.execute(
            """
            SELECT penalty_id, evidence_observation_id, effective_at,
                   published_at, provider_revision
            FROM penalty_observations
            """
        ).fetchone()
        relation_row = connection.execute(
            """
            SELECT d.possession_segment_id, p.possession_segment_id
            FROM drives d
            JOIN plays p ON p.drive_id = d.drive_id
            """
        ).fetchone()

    assert row is not None
    assert row[0] == str(play_id_for(context.game_id, 1))
    assert row[1] == EVIDENCE_OBSERVATION_ID
    payload = json.loads(str(row[2]))
    assert payload["contract_version"] == "NFL_CANONICAL_PLAY_V1"
    assert payload["execution"]["primary_play_type"] == "PASS"
    assert payload["pre_play_state"]["possession_segment_id"] is not None
    assert payload["penalties"][0]["penalty_id"] is not None
    assert "pass_attempt" not in payload
    assert penalty_row is not None
    assert penalty_row[0] == payload["penalties"][0]["penalty_id"]
    assert penalty_row[1] == EVIDENCE_OBSERVATION_ID
    assert penalty_row[2] == "2026-09-13T18:59:30Z"
    assert penalty_row[3] == "2026-09-13T18:59:55Z"
    assert penalty_row[4] == "r1"
    assert relation_row is not None
    assert relation_row[0] == relation_row[1]


def test_provider_revision_adds_observation_without_replacing_canonical_play(
    tmp_path: Path,
) -> None:
    database = tmp_path / "m6-revisions.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        _seed_raw_acquisition(connection)
        context = _context_and_game(connection)
        first = normalize_nflverse_play(
            _record(yards=9),
            context=context,
            canonical_sequence=1,
            drive_sequence=1,
            possession_sequence=1,
        )
        corrected = normalize_nflverse_play(
            _record(yards=11),
            context=context,
            canonical_sequence=1,
            drive_sequence=1,
            possession_sequence=1,
        )
        first_provenance = _provenance(
            observation_id="pob_revision_1",
            revision="r1",
        )
        corrected_provenance = _provenance(
            observation_id="pob_revision_2",
            offset_seconds=30,
            revision="r2",
        )

        record_normalized_play(connection, first, first_provenance)
        record_normalized_play(connection, corrected, corrected_provenance)

        play_count = connection.execute("SELECT COUNT(*) FROM plays").fetchone()[0]
        segment_count = connection.execute(
            "SELECT COUNT(*) FROM possession_segments"
        ).fetchone()[0]
        observations = connection.execute(
            """
            SELECT provider_revision, normalized_payload_json
            FROM play_observations
            ORDER BY available_at
            """
        ).fetchall()

    assert play_count == 1
    assert segment_count == 1
    assert [row[0] for row in observations] == ["r1", "r2"]
    yards = [
        json.loads(str(row[1]))["result"]["official_yards_gained"]
        for row in observations
    ]
    assert yards == [9, 11]


def test_bad_acquisition_provenance_fails_before_canonical_play_survives(tmp_path: Path) -> None:
    database = tmp_path / "m6-bad-provenance.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        _seed_raw_acquisition(connection)
        context = _context_and_game(connection)
        bundle = normalize_nflverse_play(
            _record(yards=12),
            context=context,
            canonical_sequence=1,
            drive_sequence=1,
            possession_sequence=1,
        )
        bad = NormalizationProvenance(
            observation_id="pob_bad_provenance",
            knowledge=_knowledge(),
            evidence_id=EVIDENCE_ID,
            evidence_observation_id="reo_missing",
            provider_revision="r1",
        )

        with pytest.raises(NormalizedPlayConflictError, match="exact raw acquisition"):
            record_normalized_play(connection, bundle, bad)

        assert connection.execute("SELECT COUNT(*) FROM plays").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM play_observations").fetchone()[0] == 0
