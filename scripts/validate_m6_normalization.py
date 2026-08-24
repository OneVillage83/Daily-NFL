"""Deterministic no-network certification validator for M6 F-5 normalization."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from daily_nfl.domain import (  # noqa: E402
    AvailabilityConfidence,
    AvailabilityMethod,
    KnowledgeTimestamp,
    ParticipationSide,
)
from daily_nfl.normalization import (  # noqa: E402
    NflverseGameContext,
    NflversePlayRecord,
    NormalizationProvenance,
    NormalizedPlayConflictError,
    PlayNormalizationError,
    ProviderParticipantRecord,
    ProviderPenaltyRecord,
    normalize_drive,
    normalize_nflverse_play,
    normalized_play_observation_id,
    record_normalized_play,
    serialize_normalized_play,
)
from daily_nfl.persistence import current_schema_version, open_database  # noqa: E402
from daily_nfl.providers import (  # noqa: E402
    NFLVERSE_DESCRIPTOR,
    DatasetKind,
    record_provider,
    record_provider_capability,
)
from daily_nfl.reconciliation import (  # noqa: E402
    IdentityRepository,
    game_id_for_event,
    new_event_id,
    new_franchise_id,
    new_person_id,
    player_id_for_person,
    team_season_id_for,
)

COMPETITION_ID = "core-competition-nfl"
EVIDENCE_ID = "m6-fixture-evidence"
EVIDENCE_OBSERVATION_ID = "reo_m6_fixture_observation"
RAW_SHA256 = "b" * 64


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    return parser.parse_args()


def _knowledge() -> KnowledgeTimestamp:
    observed = datetime(2025, 9, 11, 16, 0, tzinfo=UTC)
    return KnowledgeTimestamp(
        available_at=observed,
        effective_at=observed - timedelta(minutes=1),
        published_at=observed - timedelta(seconds=10),
        observed_at=observed,
        ingested_at=observed + timedelta(seconds=1),
        availability_method=AvailabilityMethod.OUR_OBSERVATION_TIME,
        availability_confidence=AvailabilityConfidence.HIGH,
    )


def _required_iso(value: datetime | None, label: str) -> str:
    if value is None:
        raise RuntimeError(f"M6 certification fixture requires {label}")
    return value.isoformat()


def _seed_raw_acquisition(connection: sqlite3.Connection) -> None:
    record_provider(connection, NFLVERSE_DESCRIPTOR)
    capability = NFLVERSE_DESCRIPTOR.capability_for(DatasetKind.PLAY_BY_PLAY)
    if capability is None:
        raise RuntimeError("nflverse PLAY_BY_PLAY capability is unavailable")
    capability_id = record_provider_capability(
        connection,
        NFLVERSE_DESCRIPTOR,
        capability,
    )
    knowledge = _knowledge()
    connection.execute(
        """
        INSERT INTO raw_evidence(
            evidence_id, provider_id, endpoint_category, source_uri,
            content_type, sha256, object_path, observed_at, ingested_at,
            available_at, availability_method, availability_confidence,
            provider_schema_version, parser_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            EVIDENCE_ID,
            "nflverse",
            DatasetKind.PLAY_BY_PLAY.value,
            "fixture://m6/certification",
            "application/octet-stream",
            RAW_SHA256,
            "fixture/m6-certification.bin",
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
            evidence_observation_id, evidence_id, provider_id, dataset,
            capability_id, source_uri, observed_at, ingested_at, available_at,
            availability_method, availability_confidence,
            provider_schema_version, parser_version, license_id, license_url,
            attribution_required, attribution_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            EVIDENCE_OBSERVATION_ID,
            EVIDENCE_ID,
            "nflverse",
            DatasetKind.PLAY_BY_PLAY.value,
            capability_id,
            "fixture://m6/certification",
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


def _seed_game(connection: sqlite3.Connection) -> NflverseGameContext:
    repository = IdentityRepository(connection)
    home = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    away = new_franchise_id(UUID("22222222-2222-2222-2222-222222222222"))
    repository.ensure_franchise(home)
    repository.ensure_franchise(away)
    home_team = team_season_id_for(home, 2025)
    away_team = team_season_id_for(away, 2025)
    repository.ensure_team_season(home_team, home, 2025)
    repository.ensure_team_season(away_team, away, 2025)

    passer_person = new_person_id(UUID("44444444-4444-4444-4444-444444444444"))
    target_person = new_person_id(UUID("55555555-5555-5555-5555-555555555555"))
    passer = player_id_for_person(passer_person)
    target = player_id_for_person(target_person)
    repository.ensure_person_player(passer_person, passer, "Fixture Passer")
    repository.ensure_person_player(target_person, target, "Fixture Target")

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
            2025,
            "REGULAR",
            2,
            "NFL_2025",
            str(home_team),
            str(away_team),
            "2025-09-11T20:20:00+00:00",
            COMPETITION_ID,
        ),
    )
    return NflverseGameContext(
        game_id=game_id,
        home_team_code="HOM",
        away_team_code="AWY",
        home_team_season_id=home_team,
        away_team_season_id=away_team,
        player_ids_by_external_id={
            "gsis-passer": passer,
            "gsis-target": target,
        },
    )


def _first_record() -> NflversePlayRecord:
    return NflversePlayRecord(
        provider_game_id="2025_02_AWY_HOM",
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
        source_row_index=10,
        pass_attempt=True,
        complete_pass=True,
        play_action=True,
        shotgun=True,
        official_yards_gained=12,
        first_down=True,
        participants=(
            ProviderParticipantRecord(
                player_external_id="gsis-passer",
                team_code="HOM",
                side=ParticipationSide.OFFENSE,
                role="passer",
            ),
            ProviderParticipantRecord(
                player_external_id="gsis-target",
                team_code="HOM",
                side=ParticipationSide.OFFENSE,
                role="target",
            ),
        ),
        penalties=(
            ProviderPenaltyRecord(
                team_code="AWY",
                penalty_type="Offside",
                yards=5,
            ),
        ),
    )


def _second_record() -> NflversePlayRecord:
    return NflversePlayRecord(
        provider_game_id="2025_02_AWY_HOM",
        provider_play_id="120",
        provider_drive_id="1",
        offense_team_code="HOM",
        defense_team_code="AWY",
        period=1,
        quarter_seconds_remaining=805,
        down=1,
        distance=10,
        yards_to_goal=63,
        home_score_before=0,
        away_score_before=0,
        source_row_index=11,
        rush_attempt=True,
        official_yards_gained=4,
    )


def main() -> int:
    args = parse_args()
    with open_database(args.database) as connection:
        schema_version = current_schema_version(connection)
        _seed_raw_acquisition(connection)
        context = _seed_game(connection)
        first_record = _first_record()
        second_record = _second_record()

        first = normalize_nflverse_play(
            first_record,
            context=context,
            canonical_sequence=1,
            drive_sequence=1,
            possession_sequence=1,
            next_record=second_record,
            next_drive_sequence=1,
            next_possession_sequence=1,
        )
        second = normalize_nflverse_play(
            second_record,
            context=context,
            canonical_sequence=2,
            drive_sequence=1,
            possession_sequence=1,
        )
        drive = normalize_drive((first, second))

        payload_json, payload_sha256 = serialize_normalized_play(first)
        observation_id = normalized_play_observation_id(
            evidence_id=EVIDENCE_ID,
            evidence_observation_id=EVIDENCE_OBSERVATION_ID,
            provider_id="nflverse",
            provider_play_id=first.provider_play_id,
            provider_revision="fixture-r1",
        )
        provenance = NormalizationProvenance(
            observation_id=observation_id,
            knowledge=_knowledge(),
            evidence_id=EVIDENCE_ID,
            evidence_observation_id=EVIDENCE_OBSERVATION_ID,
            provider_revision="fixture-r1",
        )
        record_normalized_play(connection, first, provenance)
        record_normalized_play(connection, first, provenance)

        stored = connection.execute(
            """
            SELECT evidence_id, evidence_observation_id, provider_id,
                   normalized_sha256
            FROM play_observations
            WHERE observation_id = ?
            """,
            (observation_id,),
        ).fetchone()
        if stored is None:
            raise RuntimeError("certified normalized observation was not persisted")

        nonadjacent_fail_closed = False
        try:
            normalize_nflverse_play(
                first_record,
                context=context,
                canonical_sequence=1,
                drive_sequence=1,
                possession_sequence=1,
                next_record=replace(second_record, source_row_index=12),
                next_drive_sequence=1,
                next_possession_sequence=1,
            )
        except PlayNormalizationError:
            nonadjacent_fail_closed = True

        bad_provenance_fail_closed = False
        play_count_before = connection.execute("SELECT COUNT(*) FROM plays").fetchone()[0]
        try:
            record_normalized_play(
                connection,
                second,
                NormalizationProvenance(
                    observation_id="pob_m6_bad_provenance",
                    knowledge=_knowledge(),
                    evidence_id=EVIDENCE_ID,
                    evidence_observation_id="reo_missing",
                    provider_revision="fixture-r1",
                ),
            )
        except NormalizedPlayConflictError:
            bad_provenance_fail_closed = True
        play_count_after = connection.execute("SELECT COUNT(*) FROM plays").fetchone()[0]

        payload = json.loads(payload_json)
        result = {
            "schema_version": schema_version,
            "game_id": str(context.game_id),
            "primary_play_type": first.execution.primary_play_type.value,
            "semantic_label": first.execution.semantic_label,
            "event_types": [event.event_type.value for event in first.events],
            "participation_count": len(first.participation),
            "penalty_count": len(first.penalties),
            "state_after_present": first.state_after is not None,
            "state_after_drive_continues": (
                first.state_after.drive_continues if first.state_after is not None else None
            ),
            "drive_play_count": drive.play_count,
            "drive_first_downs": drive.first_downs,
            "observation_id": observation_id,
            "evidence_id": stored[0],
            "evidence_observation_id": stored[1],
            "provider_id": stored[2],
            "normalized_sha256": stored[3],
            "payload_sha256": payload_sha256,
            "payload_is_provider_neutral": all(
                key not in payload
                for key in (
                    "provider_id",
                    "provider_play_id",
                    "provider_drive_id",
                    "description",
                    "pass_attempt",
                )
            ),
            "nonadjacent_state_after_fail_closed": nonadjacent_fail_closed,
            "bad_provenance_fail_closed": bad_provenance_fail_closed,
            "bad_provenance_atomic": play_count_before == play_count_after,
        }
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
