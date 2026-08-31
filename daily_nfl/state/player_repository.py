"""Append-only persistence and PIT reconstruction for M7-D Player State."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import cast

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    GameId,
    KnowledgeTimestamp,
    PlayerId,
    PlayerStateEvidenceObservationId,
    TeamSeasonId,
)
from daily_nfl.state.contracts import StateSnapshotEnvelope
from daily_nfl.state.injury import InjuryAvailabilityState
from daily_nfl.state.player import (
    DEFAULT_PLAYER_STATE_ESTIMATOR_CONFIG,
    PlayerEvidenceKind,
    PlayerPosition,
    PlayerStateEstimatorConfig,
    PlayerStateEvidenceObservation,
    PlayerStatePayload,
    build_player_state_snapshot,
    resolve_player_position,
)
from daily_nfl.state.repository import record_state_snapshot, require_state_snapshot_sealed
from daily_nfl.state.uncertainty import NamedMoments, NumericMoments, Probability


class PlayerStateEvidenceConflictError(RuntimeError):
    """Raised when stored player evidence conflicts with an immutable observation."""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("player evidence timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: object | None) -> datetime | None:
    if value is None:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("stored player evidence timestamp must be timezone-aware")
    return parsed


def _optional_text(value: object | None) -> str | None:
    return str(value) if value is not None else None


def _metrics_json(observation: PlayerStateEvidenceObservation) -> str:
    payload = [
        {
            "name": metric.name,
            "mean": metric.estimate.mean,
            "variance": metric.estimate.variance,
        }
        for metric in sorted(observation.metrics, key=lambda item: item.name)
    ]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _metrics_from_json(value: object) -> tuple[NamedMoments, ...]:
    decoded = json.loads(str(value))
    if not isinstance(decoded, list):
        raise ValueError("stored player evidence metrics must be a JSON list")
    metrics: list[NamedMoments] = []
    for raw_item in decoded:
        if not isinstance(raw_item, dict):
            raise ValueError("stored player evidence metric entry must be an object")
        item = cast(dict[str, object], raw_item)
        name = item.get("name")
        mean = item.get("mean")
        variance = item.get("variance")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("stored player evidence metric name is invalid")
        if not isinstance(mean, (int, float)) or isinstance(mean, bool):
            raise ValueError("stored player evidence metric mean is invalid")
        if not isinstance(variance, (int, float)) or isinstance(variance, bool):
            raise ValueError("stored player evidence metric variance is invalid")
        metrics.append(
            NamedMoments(
                name=name,
                estimate=NumericMoments(float(mean), float(variance)),
            )
        )
    return tuple(metrics)


def _row_values(observation: PlayerStateEvidenceObservation) -> tuple[object, ...]:
    return (
        str(observation.observation_id),
        str(observation.player_id),
        observation.logical_key,
        observation.revision,
        str(observation.team_season_id) if observation.team_season_id is not None else None,
        str(observation.source_game_id) if observation.source_game_id is not None else None,
        observation.position.value,
        observation.evidence_kind.value,
        _metrics_json(observation),
        observation.metrics_sha256,
        observation.payload_sha256,
        observation.sample_weight,
        observation.source_confidence.value,
        observation.evidence_contract,
        observation.evidence_version,
        observation.provider_id,
        observation.evidence_id,
        observation.evidence_observation_id,
        _iso(observation.knowledge.effective_at),
        _iso(observation.knowledge.published_at),
        _iso(observation.knowledge.observed_at),
        _iso(observation.knowledge.ingested_at),
        _iso(observation.knowledge.available_at),
        observation.knowledge.availability_method.value,
        observation.knowledge.availability_confidence.value,
        observation.provider_revision,
        observation.provider_schema_version,
        observation.parser_version,
        observation.raw_sha256,
    )


def _row_to_observation(row: sqlite3.Row) -> PlayerStateEvidenceObservation:
    available_at = _parse_time(row["available_at"])
    if available_at is None:
        raise ValueError("stored player evidence is missing available_at")
    observation = PlayerStateEvidenceObservation(
        observation_id=PlayerStateEvidenceObservationId(str(row["observation_id"])),
        player_id=PlayerId(str(row["player_id"])),
        logical_key=str(row["logical_key"]),
        revision=int(row["revision"]),
        team_season_id=(
            TeamSeasonId(str(row["team_season_id"]))
            if row["team_season_id"] is not None
            else None
        ),
        source_game_id=(
            GameId(str(row["source_game_id"])) if row["source_game_id"] is not None else None
        ),
        position=PlayerPosition(str(row["position"])),
        evidence_kind=PlayerEvidenceKind(str(row["evidence_kind"])),
        metrics=_metrics_from_json(row["metrics_json"]),
        sample_weight=float(row["sample_weight"]),
        source_confidence=Probability(float(row["source_confidence"])),
        evidence_contract=str(row["evidence_contract"]),
        evidence_version=str(row["evidence_version"]),
        provider_id=_optional_text(row["provider_id"]),
        evidence_id=_optional_text(row["evidence_id"]),
        evidence_observation_id=_optional_text(row["evidence_observation_id"]),
        provider_revision=_optional_text(row["provider_revision"]),
        provider_schema_version=_optional_text(row["provider_schema_version"]),
        parser_version=_optional_text(row["parser_version"]),
        raw_sha256=_optional_text(row["raw_sha256"]),
        knowledge=KnowledgeTimestamp(
            available_at=available_at,
            effective_at=_parse_time(row["effective_at"]),
            published_at=_parse_time(row["published_at"]),
            observed_at=_parse_time(row["observed_at"]),
            ingested_at=_parse_time(row["ingested_at"]),
            availability_method=AvailabilityMethod(str(row["availability_method"])),
            availability_confidence=AvailabilityConfidence(
                str(row["availability_confidence"])
            ),
        ),
    )
    if observation.metrics_sha256 != str(row["metrics_sha256"]):
        raise PlayerStateEvidenceConflictError(
            f"stored player evidence {observation.observation_id!s} has invalid metrics hash"
        )
    if observation.payload_sha256 != str(row["payload_sha256"]):
        raise PlayerStateEvidenceConflictError(
            f"stored player evidence {observation.observation_id!s} has invalid payload hash"
        )
    return observation


def record_player_state_evidence(
    connection: sqlite3.Connection,
    observation: PlayerStateEvidenceObservation,
) -> None:
    """Persist one immutable player-state evidence observation idempotently."""

    existing = connection.execute(
        """
        SELECT observation_id, player_id, logical_key, revision, team_season_id,
               source_game_id, position, evidence_kind, metrics_json, metrics_sha256,
               payload_sha256, sample_weight, source_confidence, evidence_contract,
               evidence_version, provider_id, evidence_id, evidence_observation_id,
               effective_at, published_at, observed_at, ingested_at, available_at,
               availability_method, availability_confidence, provider_revision,
               provider_schema_version, parser_version, raw_sha256
        FROM player_state_evidence_observations
        WHERE observation_id = ?
        """,
        (str(observation.observation_id),),
    ).fetchone()
    values = _row_values(observation)
    if existing is not None:
        if tuple(existing) != values:
            raise PlayerStateEvidenceConflictError(
                f"stored player evidence {observation.observation_id!s} conflicts with observation"
            )
        return

    connection.execute(
        """
        INSERT INTO player_state_evidence_observations(
            observation_id, player_id, logical_key, revision, team_season_id,
            source_game_id, position, evidence_kind, metrics_json, metrics_sha256,
            payload_sha256, sample_weight, source_confidence, evidence_contract,
            evidence_version, provider_id, evidence_id, evidence_observation_id,
            effective_at, published_at, observed_at, ingested_at, available_at,
            availability_method, availability_confidence, provider_revision,
            provider_schema_version, parser_version, raw_sha256
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        values,
    )


def player_state_evidence_as_of(
    connection: sqlite3.Connection,
    *,
    player_id: PlayerId,
    team_season_id: TeamSeasonId,
    target_game_id: GameId,
    as_of: datetime,
) -> tuple[PlayerStateEvidenceObservation, ...]:
    """Select latest-known revisions of PIT-safe evidence for one player state."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("player evidence as_of must be timezone-aware")
    rows = connection.execute(
        """
        SELECT observation_id, player_id, logical_key, revision, team_season_id,
               source_game_id, position, evidence_kind, metrics_json, metrics_sha256,
               payload_sha256, sample_weight, source_confidence, evidence_contract,
               evidence_version, provider_id, evidence_id, evidence_observation_id,
               effective_at, published_at, observed_at, ingested_at, available_at,
               availability_method, availability_confidence, provider_revision,
               provider_schema_version, parser_version, raw_sha256
        FROM player_state_evidence_observations
        WHERE player_id = ?
          AND available_at <= ?
          AND (source_game_id IS NULL OR source_game_id <> ?)
        ORDER BY logical_key, revision, available_at, observation_id
        """,
        (str(player_id), _iso(as_of), str(target_game_id)),
    ).fetchall()

    latest_by_key: dict[str, PlayerStateEvidenceObservation] = {}
    for row in rows:
        observation = _row_to_observation(row)
        existing = latest_by_key.get(observation.logical_key)
        if existing is None or observation.revision > existing.revision:
            latest_by_key[observation.logical_key] = observation

    selected: list[PlayerStateEvidenceObservation] = []
    for observation in latest_by_key.values():
        if observation.evidence_kind is PlayerEvidenceKind.TALENT:
            selected.append(observation)
            continue
        if observation.team_season_id in (None, team_season_id):
            selected.append(observation)
    return tuple(sorted(selected, key=lambda item: str(item.observation_id)))


def build_player_state_as_of(
    connection: sqlite3.Connection,
    *,
    player_id: PlayerId,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    as_of: datetime,
    injury_snapshot: StateSnapshotEnvelope[InjuryAvailabilityState],
    position_override: PlayerPosition | None = None,
    config: PlayerStateEstimatorConfig = DEFAULT_PLAYER_STATE_ESTIMATOR_CONFIG,
    created_at: datetime,
) -> StateSnapshotEnvelope[PlayerStatePayload]:
    """Reconstruct, persist, and seal one F-7 Player State at a PIT cutoff."""

    require_state_snapshot_sealed(connection, injury_snapshot.snapshot_id)
    evidence = player_state_evidence_as_of(
        connection,
        player_id=player_id,
        team_season_id=team_season_id,
        target_game_id=game_id,
        as_of=as_of,
    )
    position = position_override or resolve_player_position(
        evidence,
        team_season_id=team_season_id,
    )
    snapshot = build_player_state_snapshot(
        player_id=player_id,
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
        position=position,
        evidence=evidence,
        injury_snapshot=injury_snapshot,
        config=config,
        created_at=created_at,
    )
    record_state_snapshot(connection, snapshot)
    return snapshot
