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
from daily_nfl.pit.contracts import (
    DEFAULT_PIT_POLICY,
    PITInputKind,
    PITInputRef,
    PITPolicy,
    PredictionCutoff,
)
from daily_nfl.pit.selector import (
    PITObservation,
    PITSelectionConflictError,
    select_latest_as_of,
)


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


def _optional_text(value: object | None) -> str | None:
    return str(value) if value is not None else None


def _optional_bool(value: object | None) -> bool | None:
    return bool(int(value)) if value is not None else None


def _first_text(*values: object | None) -> str | None:
    for value in values:
        if value is not None:
            return str(value)
    return None


def _schedule_payload_sha256(row: sqlite3.Row) -> str:
    payload = {
        "provider_id": str(row["provider_id"]),
        "provider_game_id": _optional_text(row["provider_game_id"]),
        "status": str(row["status"]),
        "scheduled_kickoff": str(row["scheduled_kickoff"]),
        "actual_kickoff": _optional_text(row["actual_kickoff"]),
        "venue_id": _optional_text(row["venue_id"]),
        "neutral_site": _optional_bool(row["neutral_site"]),
        "schedule_version": _optional_text(row["schedule_version"]),
        "provider_revision": _optional_text(row["provider_revision"]),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _schedule_state_signature(row: sqlite3.Row) -> tuple[object, ...]:
    scheduled_kickoff = _parse_time(row["scheduled_kickoff"])
    if scheduled_kickoff is None:
        raise ValueError("schedule observation is missing scheduled_kickoff")
    return (
        str(row["status"]),
        scheduled_kickoff,
        _parse_time(row["actual_kickoff"]),
        _optional_text(row["venue_id"]),
        _optional_bool(row["neutral_site"]),
        _optional_text(row["schedule_version"]),
    )


@dataclass(frozen=True, slots=True)
class ScheduleStateAsOf:
    observation_id: str
    game_id: GameId
    provider_id: str
    provider_game_id: str | None
    status: str
    scheduled_kickoff: datetime
    actual_kickoff: datetime | None
    venue_id: str | None
    neutral_site: bool | None
    schedule_version: str | None
    provider_revision: str | None
    input_ref: PITInputRef
    supporting_inputs: tuple[PITInputRef, ...]


def schedule_state_as_of(
    connection: sqlite3.Connection,
    *,
    game_id: GameId,
    cutoff: PredictionCutoff,
    policy: PITPolicy = DEFAULT_PIT_POLICY,
) -> ScheduleStateAsOf | None:
    """Return the latest defensible schedule state known by the cutoff.

    Revisions are selected independently inside each provider namespace. If two
    providers disagree on canonical schedule state at the same prediction time,
    M5 fails closed rather than silently allowing the newest provider row to
    overwrite the other source.
    """

    if game_id != cutoff.game_id:
        raise ValueError("schedule query game_id must match the prediction cutoff game_id")

    rows = connection.execute(
        """
        SELECT
            schedule.observation_id,
            schedule.game_id,
            schedule.evidence_id,
            schedule.evidence_observation_id,
            schedule.provider_id,
            schedule.provider_game_id,
            schedule.status,
            schedule.scheduled_kickoff,
            schedule.actual_kickoff,
            schedule.venue_id,
            schedule.neutral_site,
            schedule.schedule_version,
            schedule.effective_at,
            schedule.published_at,
            schedule.observed_at,
            schedule.ingested_at,
            schedule.available_at,
            schedule.availability_method,
            schedule.availability_confidence,
            schedule.provider_revision,
            raw.sha256 AS raw_sha256,
            raw.provider_schema_version AS raw_provider_schema_version,
            raw.parser_version AS raw_parser_version,
            acquisition.evidence_id AS acquisition_evidence_id,
            acquisition.provider_id AS acquisition_provider_id,
            acquisition.provider_schema_version AS acquisition_provider_schema_version,
            acquisition.parser_version AS acquisition_parser_version
        FROM schedule_observations AS schedule
        LEFT JOIN raw_evidence AS raw
          ON raw.evidence_id = schedule.evidence_id
        LEFT JOIN raw_evidence_observations AS acquisition
          ON acquisition.evidence_observation_id = schedule.evidence_observation_id
        WHERE schedule.game_id = ?
        ORDER BY schedule.provider_id, schedule.available_at, schedule.observation_id
        """,
        (str(game_id),),
    ).fetchall()

    observations: list[PITObservation[sqlite3.Row]] = []
    for row in rows:
        available_at = _parse_time(row["available_at"])
        scheduled_kickoff = _parse_time(row["scheduled_kickoff"])
        if available_at is None or scheduled_kickoff is None:
            raise ValueError("schedule observation is missing required PIT timestamps")
        evidence_id = _optional_text(row["evidence_id"])
        evidence_observation_id = _optional_text(row["evidence_observation_id"])
        if evidence_observation_id is not None:
            if (
                _optional_text(row["acquisition_evidence_id"]) != evidence_id
                or _optional_text(row["acquisition_provider_id"]) != str(row["provider_id"])
            ):
                raise PITSelectionConflictError(
                    "schedule observation acquisition provenance disagrees with raw/provider identity"
                )
        input_ref = PITInputRef(
            input_kind=PITInputKind.SCHEDULE,
            input_id=str(row["observation_id"]),
            available_at=available_at,
            availability_method=AvailabilityMethod(str(row["availability_method"])),
            availability_confidence=AvailabilityConfidence(
                str(row["availability_confidence"])
            ),
            source_table="schedule_observations",
            evidence_id=evidence_id,
            evidence_observation_id=evidence_observation_id,
            provider_id=str(row["provider_id"]),
            provider_revision=_optional_text(row["provider_revision"]),
            provider_schema_version=_first_text(
                row["acquisition_provider_schema_version"],
                row["raw_provider_schema_version"],
            ),
            parser_version=_first_text(
                row["acquisition_parser_version"],
                row["raw_parser_version"],
            ),
            subject_game_id=game_id,
            effective_at=_parse_time(row["effective_at"]),
            published_at=_parse_time(row["published_at"]),
            observed_at=_parse_time(row["observed_at"]),
            ingested_at=_parse_time(row["ingested_at"]),
            payload_sha256=_schedule_payload_sha256(row),
            raw_sha256=_optional_text(row["raw_sha256"]),
        )
        observations.append(
            PITObservation(
                logical_key=f"schedule:{game_id}:{row['provider_id']}",
                input_ref=input_ref,
                value=row,
            )
        )

    selected = select_latest_as_of(tuple(observations), cutoff=cutoff, policy=policy)
    if not selected:
        return None

    signatures = {_schedule_state_signature(observation.value) for observation in selected}
    if len(signatures) > 1:
        providers = sorted(observation.input_ref.provider_id or "UNKNOWN" for observation in selected)
        raise PITSelectionConflictError(
            "conflicting provider schedule states at PIT cutoff for "
            f"game {game_id!s}: {providers}"
        )

    representative = min(
        selected,
        key=lambda observation: (
            observation.input_ref.provider_id or "",
            observation.input_ref.input_id,
        ),
    )
    row = representative.value
    scheduled_kickoff = _parse_time(row["scheduled_kickoff"])
    if scheduled_kickoff is None:
        raise ValueError("schedule observation is missing scheduled_kickoff")
    return ScheduleStateAsOf(
        observation_id=str(row["observation_id"]),
        game_id=GameId(str(row["game_id"])),
        provider_id=str(row["provider_id"]),
        provider_game_id=_optional_text(row["provider_game_id"]),
        status=str(row["status"]),
        scheduled_kickoff=scheduled_kickoff,
        actual_kickoff=_parse_time(row["actual_kickoff"]),
        venue_id=_optional_text(row["venue_id"]),
        neutral_site=_optional_bool(row["neutral_site"]),
        schedule_version=_optional_text(row["schedule_version"]),
        provider_revision=_optional_text(row["provider_revision"]),
        input_ref=representative.input_ref,
        supporting_inputs=tuple(observation.input_ref for observation in selected),
    )
