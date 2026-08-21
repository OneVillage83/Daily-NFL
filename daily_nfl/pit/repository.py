"""SQLite as-of query helpers for historical PIT reconstruction."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    GameId,
)
from daily_nfl.pit.contracts import PITInputKind, PITInputRef, PITPolicy, PredictionCutoff
from daily_nfl.pit.selector import PITObservation, select_latest_as_of


def _parse_time(value: object | None) -> datetime | None:
    if value is None:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("stored PIT timestamp must be timezone-aware")
    return parsed


def _schedule_payload_sha256(row: sqlite3.Row) -> str:
    payload = {
        "provider_id": str(row["provider_id"]),
        "provider_game_id": (
            str(row["provider_game_id"]) if row["provider_game_id"] is not None else None
        ),
        "status": str(row["status"]),
        "scheduled_kickoff": str(row["scheduled_kickoff"]),
        "venue_id": str(row["venue_id"]) if row["venue_id"] is not None else None,
        "provider_revision": (
            str(row["provider_revision"]) if row["provider_revision"] is not None else None
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ScheduleStateAsOf:
    observation_id: str
    game_id: GameId
    provider_id: str
    provider_game_id: str | None
    status: str
    scheduled_kickoff: datetime
    venue_id: str | None
    input_ref: PITInputRef


def schedule_state_as_of(
    connection: sqlite3.Connection,
    *,
    game_id: GameId,
    cutoff: PredictionCutoff,
    policy: PITPolicy = PITPolicy(),
) -> ScheduleStateAsOf | None:
    """Return the latest defensible schedule revision known by the cutoff."""

    rows = connection.execute(
        """
        SELECT
            observation_id,
            game_id,
            evidence_id,
            provider_id,
            provider_game_id,
            status,
            scheduled_kickoff,
            venue_id,
            effective_at,
            published_at,
            observed_at,
            ingested_at,
            available_at,
            availability_method,
            availability_confidence,
            provider_revision
        FROM schedule_observations
        WHERE game_id = ?
        ORDER BY available_at, observed_at, ingested_at, observation_id
        """,
        (str(game_id),),
    ).fetchall()

    observations: list[PITObservation[sqlite3.Row]] = []
    for row in rows:
        available_at = _parse_time(row["available_at"])
        scheduled_kickoff = _parse_time(row["scheduled_kickoff"])
        if available_at is None or scheduled_kickoff is None:
            raise ValueError("schedule observation is missing required PIT timestamps")
        input_ref = PITInputRef(
            input_kind=PITInputKind.SCHEDULE,
            input_id=str(row["observation_id"]),
            available_at=available_at,
            availability_method=AvailabilityMethod(str(row["availability_method"])),
            availability_confidence=AvailabilityConfidence(
                str(row["availability_confidence"])
            ),
            source_table="schedule_observations",
            evidence_id=(str(row["evidence_id"]) if row["evidence_id"] is not None else None),
            subject_game_id=game_id,
            effective_at=_parse_time(row["effective_at"]),
            published_at=_parse_time(row["published_at"]),
            observed_at=_parse_time(row["observed_at"]),
            ingested_at=_parse_time(row["ingested_at"]),
            payload_sha256=_schedule_payload_sha256(row),
        )
        observations.append(
            PITObservation(
                logical_key=f"schedule:{game_id}",
                input_ref=input_ref,
                value=row,
            )
        )

    selected = select_latest_as_of(tuple(observations), cutoff=cutoff, policy=policy)
    if not selected:
        return None
    row = selected[0].value
    scheduled_kickoff = _parse_time(row["scheduled_kickoff"])
    if scheduled_kickoff is None:
        raise ValueError("schedule observation is missing scheduled_kickoff")
    return ScheduleStateAsOf(
        observation_id=str(row["observation_id"]),
        game_id=GameId(str(row["game_id"])),
        provider_id=str(row["provider_id"]),
        provider_game_id=(
            str(row["provider_game_id"]) if row["provider_game_id"] is not None else None
        ),
        status=str(row["status"]),
        scheduled_kickoff=scheduled_kickoff,
        venue_id=str(row["venue_id"]) if row["venue_id"] is not None else None,
        input_ref=selected[0].input_ref,
    )
