"""Persistence bridge for canonical M6 normalized play observations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from daily_nfl.domain import KnowledgeTimestamp
from daily_nfl.normalization.contracts import NormalizedPlayBundle


class NormalizedPlayConflictError(RuntimeError):
    """Raised when canonical or observation identity conflicts with stored history."""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("normalization timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class NormalizationProvenance:
    observation_id: str
    knowledge: KnowledgeTimestamp
    evidence_id: str | None = None
    provider_revision: str | None = None

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("observation_id cannot be blank")
        if self.evidence_id is not None and not self.evidence_id.strip():
            raise ValueError("evidence_id cannot be blank when present")
        if self.knowledge.ingested_at is None:
            raise ValueError("normalized observations require ingested_at")


def normalized_play_observation_id(
    *,
    evidence_id: str,
    provider_id: str,
    provider_play_id: str,
    provider_revision: str | None = None,
) -> str:
    """Derive stable observation identity from immutable evidence plus provider row identity."""

    if not evidence_id.strip() or not provider_id.strip() or not provider_play_id.strip():
        raise ValueError("normalization observation identity fields cannot be blank")
    payload = "|".join(
        (evidence_id, provider_id, provider_play_id, provider_revision or "")
    ).encode()
    return f"pob_{hashlib.sha256(payload).hexdigest()}"


def _payload(bundle: NormalizedPlayBundle) -> dict[str, object]:
    pre = bundle.pre_play_state
    result = bundle.result
    after = bundle.state_after
    return {
        "contract_version": "NFL_CANONICAL_PLAY_V1",
        "game_id": str(bundle.game_id),
        "canonical_sequence": bundle.canonical_sequence,
        "drive_sequence": bundle.drive_sequence,
        "possession_sequence": bundle.possession_sequence,
        "provider_id": bundle.provider_id,
        "provider_play_id": bundle.provider_play_id,
        "provider_drive_id": bundle.provider_drive_id,
        "description": bundle.description,
        "pre_play_state": {
            "play_id": str(pre.play_id),
            "drive_id": str(pre.drive_id) if pre.drive_id is not None else None,
            "possession_id": str(pre.possession.possession_id),
            "possession_segment_id": (
                str(pre.possession_segment_id)
                if pre.possession_segment_id is not None
                else None
            ),
            "offense_team_season_id": str(pre.possession.offense_team_season_id),
            "defense_team_season_id": str(pre.possession.defense_team_season_id),
            "period": pre.period.number,
            "is_overtime": pre.period.is_overtime,
            "clock_seconds_remaining": pre.clock_seconds_remaining,
            "down": pre.down,
            "distance": pre.distance,
            "yards_to_goal": pre.yards_to_goal,
            "home_score": pre.home_score,
            "away_score": pre.away_score,
            "home_timeouts_remaining": pre.home_timeouts_remaining,
            "away_timeouts_remaining": pre.away_timeouts_remaining,
        },
        "execution": {
            "primary_play_type": bundle.execution.primary_play_type.value,
            "modifiers": sorted(modifier.value for modifier in bundle.execution.modifiers),
            "semantic_label": bundle.execution.semantic_label,
        },
        "events": [
            {
                "play_event_id": str(event.play_event_id),
                "sequence": event.sequence,
                "event_type": event.event_type.value,
                "player_id": str(event.player_id) if event.player_id is not None else None,
                "team_season_id": (
                    str(event.team_season_id) if event.team_season_id is not None else None
                ),
                "detail": event.detail,
            }
            for event in bundle.events
        ],
        "participation": [
            {
                "participation_id": str(item.participation_id),
                "player_id": str(item.player_id),
                "team_season_id": str(item.team_season_id),
                "side": item.side.value,
                "role": item.role,
                "on_field": item.on_field,
            }
            for item in bundle.participation
        ],
        "penalties": [
            {
                "penalty_id": str(penalty.penalty_id),
                "team_season_id": str(penalty.team_season_id),
                "player_id": str(penalty.player_id) if penalty.player_id is not None else None,
                "penalty_type": penalty.penalty_type,
                "disposition": penalty.disposition.value,
                "yards": penalty.yards,
                "automatic_first_down": penalty.automatic_first_down,
                "loss_of_down": penalty.loss_of_down,
                "nullifies_play": penalty.nullifies_play,
                "enforcement_spot": penalty.enforcement_spot,
            }
            for penalty in bundle.penalties
        ],
        "result": {
            "official_yards_gained": result.official_yards_gained,
            "physical_yards_gained": result.physical_yards_gained,
            "first_down": result.first_down,
            "touchdown": result.touchdown,
            "safety": result.safety,
            "completion": result.completion,
            "interception": result.interception,
            "sack": result.sack,
            "fumble": result.fumble,
            "fumble_lost": result.fumble_lost,
            "possession_changed": result.possession_changed,
            "score_change": result.score_change,
            "no_play": result.no_play,
        },
        "state_after": (
            None
            if after is None
            else {
                "next_possession_id": (
                    str(after.next_possession.possession_id)
                    if after.next_possession is not None
                    else None
                ),
                "offense_team_season_id": (
                    str(after.next_possession.offense_team_season_id)
                    if after.next_possession is not None
                    else None
                ),
                "defense_team_season_id": (
                    str(after.next_possession.defense_team_season_id)
                    if after.next_possession is not None
                    else None
                ),
                "period": after.period.number,
                "is_overtime": after.period.is_overtime,
                "clock_seconds_remaining": after.clock_seconds_remaining,
                "down": after.down,
                "distance": after.distance,
                "yards_to_goal": after.yards_to_goal,
                "home_score": after.home_score,
                "away_score": after.away_score,
                "drive_continues": after.drive_continues,
            }
        ),
    }


def serialize_normalized_play(bundle: NormalizedPlayBundle) -> tuple[str, str]:
    payload_json = json.dumps(_payload(bundle), sort_keys=True, separators=(",", ":"))
    return payload_json, hashlib.sha256(payload_json.encode()).hexdigest()


def _ensure_child_identity(
    connection: sqlite3.Connection,
    *,
    table: str,
    id_column: str,
    canonical_id: str,
    play_id: str,
    sequence: int,
) -> None:
    connection.execute(
        f"""
        INSERT INTO {table}({id_column}, play_id, canonical_sequence)
        VALUES (?, ?, ?)
        ON CONFLICT({id_column}) DO NOTHING
        """,
        (canonical_id, play_id, sequence),
    )
    row = connection.execute(
        f"SELECT play_id, canonical_sequence FROM {table} WHERE {id_column} = ?",
        (canonical_id,),
    ).fetchone()
    expected = (play_id, sequence)
    if row is None or tuple(row) != expected:
        raise NormalizedPlayConflictError(f"canonical {table} identity conflicts with stored facts")


def _ensure_canonical_rows(
    connection: sqlite3.Connection,
    bundle: NormalizedPlayBundle,
) -> None:
    pre = bundle.pre_play_state
    possession = pre.possession
    segment_id = pre.possession_segment_id
    if segment_id is None:
        raise NormalizedPlayConflictError(
            "canonical normalized play requires possession_segment_id"
        )

    # Retain the original possession relation for backward compatibility while
    # persisting the certified F-5 possession-segment identity separately.
    connection.execute(
        """
        INSERT INTO possessions(
            possession_id,
            game_id,
            offense_team_season_id,
            defense_team_season_id
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(possession_id) DO NOTHING
        """,
        (
            str(possession.possession_id),
            str(bundle.game_id),
            str(possession.offense_team_season_id),
            str(possession.defense_team_season_id),
        ),
    )
    possession_row = connection.execute(
        """
        SELECT game_id, offense_team_season_id, defense_team_season_id
        FROM possessions
        WHERE possession_id = ?
        """,
        (str(possession.possession_id),),
    ).fetchone()
    expected_possession = (
        str(bundle.game_id),
        str(possession.offense_team_season_id),
        str(possession.defense_team_season_id),
    )
    if possession_row is None or tuple(possession_row) != expected_possession:
        raise NormalizedPlayConflictError("canonical possession conflicts with stored facts")

    connection.execute(
        """
        INSERT INTO possession_segments(
            possession_segment_id,
            game_id,
            canonical_sequence,
            offense_team_season_id,
            defense_team_season_id
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(possession_segment_id) DO NOTHING
        """,
        (
            str(segment_id),
            str(bundle.game_id),
            bundle.possession_sequence,
            str(possession.offense_team_season_id),
            str(possession.defense_team_season_id),
        ),
    )
    segment_row = connection.execute(
        """
        SELECT game_id, canonical_sequence, offense_team_season_id, defense_team_season_id
        FROM possession_segments
        WHERE possession_segment_id = ?
        """,
        (str(segment_id),),
    ).fetchone()
    expected_segment = (
        str(bundle.game_id),
        bundle.possession_sequence,
        str(possession.offense_team_season_id),
        str(possession.defense_team_season_id),
    )
    if segment_row is None or tuple(segment_row) != expected_segment:
        raise NormalizedPlayConflictError(
            "canonical possession segment conflicts with stored facts"
        )

    if pre.drive_id is not None:
        connection.execute(
            """
            INSERT INTO drives(
                drive_id,
                game_id,
                possession_id,
                canonical_sequence,
                possession_segment_id
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(drive_id) DO NOTHING
            """,
            (
                str(pre.drive_id),
                str(bundle.game_id),
                str(possession.possession_id),
                bundle.drive_sequence,
                str(segment_id),
            ),
        )
        drive_row = connection.execute(
            """
            SELECT game_id, possession_id, canonical_sequence, possession_segment_id
            FROM drives
            WHERE drive_id = ?
            """,
            (str(pre.drive_id),),
        ).fetchone()
        expected_drive = (
            str(bundle.game_id),
            str(possession.possession_id),
            bundle.drive_sequence,
            str(segment_id),
        )
        if drive_row is None or tuple(drive_row) != expected_drive:
            raise NormalizedPlayConflictError("canonical drive conflicts with stored facts")

    connection.execute(
        """
        INSERT INTO plays(
            play_id,
            game_id,
            drive_id,
            possession_id,
            canonical_sequence,
            possession_segment_id
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(play_id) DO NOTHING
        """,
        (
            str(pre.play_id),
            str(bundle.game_id),
            str(pre.drive_id) if pre.drive_id is not None else None,
            str(possession.possession_id),
            bundle.canonical_sequence,
            str(segment_id),
        ),
    )
    play_row = connection.execute(
        """
        SELECT game_id, drive_id, possession_id, canonical_sequence, possession_segment_id
        FROM plays
        WHERE play_id = ?
        """,
        (str(pre.play_id),),
    ).fetchone()
    expected_play = (
        str(bundle.game_id),
        str(pre.drive_id) if pre.drive_id is not None else None,
        str(possession.possession_id),
        bundle.canonical_sequence,
        str(segment_id),
    )
    if play_row is None or tuple(play_row) != expected_play:
        raise NormalizedPlayConflictError("canonical play conflicts with stored facts")

    play_id = str(pre.play_id)
    for event in bundle.events:
        _ensure_child_identity(
            connection,
            table="play_events",
            id_column="play_event_id",
            canonical_id=str(event.play_event_id),
            play_id=play_id,
            sequence=event.sequence,
        )
    for sequence, item in enumerate(bundle.participation, start=1):
        _ensure_child_identity(
            connection,
            table="participations",
            id_column="participation_id",
            canonical_id=str(item.participation_id),
            play_id=play_id,
            sequence=sequence,
        )
    for sequence, penalty in enumerate(bundle.penalties, start=1):
        _ensure_child_identity(
            connection,
            table="penalties",
            id_column="penalty_id",
            canonical_id=str(penalty.penalty_id),
            play_id=play_id,
            sequence=sequence,
        )


def _participation_observation_id(observation_id: str, sequence: int) -> str:
    digest = hashlib.sha256(f"{observation_id}|participation|{sequence}".encode()).hexdigest()
    return f"pao_{digest}"


def _penalty_observation_id(observation_id: str, sequence: int) -> str:
    digest = hashlib.sha256(f"{observation_id}|penalty|{sequence}".encode()).hexdigest()
    return f"peo_{digest}"


def record_normalized_play(
    connection: sqlite3.Connection,
    bundle: NormalizedPlayBundle,
    provenance: NormalizationProvenance,
) -> None:
    """Persist canonical identity rows plus one immutable normalized observation."""

    _ensure_canonical_rows(connection, bundle)
    payload_json, payload_sha256 = serialize_normalized_play(bundle)
    existing = connection.execute(
        """
        SELECT play_id, evidence_id, provider_id, provider_play_id,
               provider_revision, normalized_payload_json, normalized_sha256
        FROM play_observations
        WHERE observation_id = ?
        """,
        (provenance.observation_id,),
    ).fetchone()
    expected = (
        str(bundle.pre_play_state.play_id),
        provenance.evidence_id,
        bundle.provider_id,
        bundle.provider_play_id,
        provenance.provider_revision,
        payload_json,
        payload_sha256,
    )
    if existing is not None:
        if tuple(existing) != expected:
            raise NormalizedPlayConflictError(
                "stored normalized play observation conflicts with supplied observation"
            )
        return

    knowledge = provenance.knowledge
    connection.execute(
        """
        INSERT INTO play_observations(
            observation_id,
            play_id,
            evidence_id,
            provider_id,
            provider_play_id,
            provider_revision,
            normalized_payload_json,
            normalized_sha256,
            effective_at,
            published_at,
            observed_at,
            ingested_at,
            available_at,
            availability_method,
            availability_confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            provenance.observation_id,
            str(bundle.pre_play_state.play_id),
            provenance.evidence_id,
            bundle.provider_id,
            bundle.provider_play_id,
            provenance.provider_revision,
            payload_json,
            payload_sha256,
            _iso(knowledge.effective_at),
            _iso(knowledge.published_at),
            _iso(knowledge.observed_at),
            _iso(knowledge.ingested_at),
            _iso(knowledge.available_at),
            knowledge.availability_method.value,
            knowledge.availability_confidence.value,
        ),
    )

    for sequence, item in enumerate(bundle.participation, start=1):
        connection.execute(
            """
            INSERT INTO participation_observations(
                observation_id,
                participation_id,
                play_id,
                player_id,
                team_season_id,
                evidence_id,
                provider_id,
                side,
                role,
                on_field,
                effective_at,
                published_at,
                observed_at,
                ingested_at,
                available_at,
                availability_method,
                availability_confidence,
                provider_revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _participation_observation_id(provenance.observation_id, sequence),
                str(item.participation_id),
                str(item.play_id),
                str(item.player_id),
                str(item.team_season_id),
                provenance.evidence_id,
                bundle.provider_id,
                item.side.value,
                item.role,
                int(item.on_field),
                _iso(knowledge.effective_at),
                _iso(knowledge.published_at),
                _iso(knowledge.observed_at),
                _iso(knowledge.ingested_at),
                _iso(knowledge.available_at),
                knowledge.availability_method.value,
                knowledge.availability_confidence.value,
                provenance.provider_revision,
            ),
        )

    for sequence, penalty in enumerate(bundle.penalties, start=1):
        connection.execute(
            """
            INSERT INTO penalty_observations(
                observation_id,
                penalty_id,
                play_id,
                team_season_id,
                player_id,
                evidence_id,
                provider_id,
                penalty_type,
                disposition,
                yards,
                automatic_first_down,
                loss_of_down,
                nullifies_play,
                enforcement_spot,
                effective_at,
                published_at,
                observed_at,
                ingested_at,
                available_at,
                availability_method,
                availability_confidence,
                provider_revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _penalty_observation_id(provenance.observation_id, sequence),
                str(penalty.penalty_id),
                str(penalty.play_id),
                str(penalty.team_season_id),
                str(penalty.player_id) if penalty.player_id is not None else None,
                provenance.evidence_id,
                bundle.provider_id,
                penalty.penalty_type,
                penalty.disposition.value,
                penalty.yards,
                int(penalty.automatic_first_down),
                int(penalty.loss_of_down),
                int(penalty.nullifies_play),
                penalty.enforcement_spot,
                _iso(knowledge.effective_at),
                _iso(knowledge.published_at),
                _iso(knowledge.observed_at),
                _iso(knowledge.ingested_at),
                _iso(knowledge.available_at),
                knowledge.availability_method.value,
                knowledge.availability_confidence.value,
                provenance.provider_revision,
            ),
        )
