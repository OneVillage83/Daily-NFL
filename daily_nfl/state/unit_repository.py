"""Append-only persistence and PIT reconstruction for M7-E Unit State."""

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
    TeamSeasonId,
    UnitConfigurationObservationId,
    UnitStateEvidenceObservationId,
)
from daily_nfl.state.contracts import StateSnapshotEnvelope
from daily_nfl.state.player import PlayerStatePayload
from daily_nfl.state.repository import record_state_snapshot, require_state_snapshot_sealed
from daily_nfl.state.uncertainty import NamedMoments, NumericMoments, Probability
from daily_nfl.state.unit import (
    DEFAULT_UNIT_STATE_ESTIMATOR_CONFIG,
    UnitConfigurationAlternative,
    UnitConfigurationAvailabilityBasis,
    UnitConfigurationObservation,
    UnitEvidenceKind,
    UnitMemberAssignment,
    UnitStateEstimatorConfig,
    UnitStateEvidenceObservation,
    UnitStatePayload,
    UnitType,
    build_unit_state_snapshot,
)


class UnitStateEvidenceConflictError(RuntimeError):
    """Raised when stored unit evidence conflicts with its immutable content."""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("unit evidence timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: object | None) -> datetime | None:
    if value is None:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("stored unit evidence timestamp must be timezone-aware")
    return parsed


def _optional_text(value: object | None) -> str | None:
    return str(value) if value is not None else None


def _distribution_json(observation: UnitConfigurationObservation) -> str:
    payload = [
        {
            "prior_probability": alternative.prior_probability.value,
            "members": [
                {
                    "player_id": str(member.player_id),
                    "role": member.role,
                    "expected_share": member.expected_share.value,
                }
                for member in alternative.members
            ],
        }
        for alternative in observation.alternatives
    ]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _distribution_from_json(value: object) -> tuple[UnitConfigurationAlternative, ...]:
    decoded = json.loads(str(value))
    if not isinstance(decoded, list):
        raise ValueError("stored unit configuration distribution must be a JSON list")
    alternatives: list[UnitConfigurationAlternative] = []
    for raw_alternative in decoded:
        if not isinstance(raw_alternative, dict):
            raise ValueError("stored unit configuration alternative must be an object")
        alternative = cast(dict[str, object], raw_alternative)
        raw_probability = alternative.get("prior_probability")
        raw_members = alternative.get("members")
        if not isinstance(raw_probability, (int, float)) or isinstance(raw_probability, bool):
            raise ValueError("stored unit configuration probability is invalid")
        if not isinstance(raw_members, list):
            raise ValueError("stored unit configuration members must be a list")
        members: list[UnitMemberAssignment] = []
        for raw_member in raw_members:
            if not isinstance(raw_member, dict):
                raise ValueError("stored unit configuration member must be an object")
            member = cast(dict[str, object], raw_member)
            player_id = member.get("player_id")
            role = member.get("role")
            expected_share = member.get("expected_share")
            if not isinstance(player_id, str) or not player_id.strip():
                raise ValueError("stored unit member player_id is invalid")
            if not isinstance(role, str) or not role.strip():
                raise ValueError("stored unit member role is invalid")
            if not isinstance(expected_share, (int, float)) or isinstance(
                expected_share, bool
            ):
                raise ValueError("stored unit member expected_share is invalid")
            members.append(
                UnitMemberAssignment(
                    player_id=PlayerId(player_id),
                    role=role,
                    expected_share=Probability(float(expected_share)),
                )
            )
        alternatives.append(
            UnitConfigurationAlternative(
                members=tuple(members),
                prior_probability=Probability(float(raw_probability)),
            )
        )
    return tuple(alternatives)


def _metrics_json(observation: UnitStateEvidenceObservation) -> str:
    payload = [
        {
            "name": metric.name,
            "mean": metric.estimate.mean,
            "variance": metric.estimate.variance,
        }
        for metric in observation.metrics
    ]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _metrics_from_json(value: object) -> tuple[NamedMoments, ...]:
    decoded = json.loads(str(value))
    if not isinstance(decoded, list):
        raise ValueError("stored unit evidence metrics must be a JSON list")
    metrics: list[NamedMoments] = []
    for raw_item in decoded:
        if not isinstance(raw_item, dict):
            raise ValueError("stored unit evidence metric entry must be an object")
        item = cast(dict[str, object], raw_item)
        name = item.get("name")
        mean = item.get("mean")
        variance = item.get("variance")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("stored unit evidence metric name is invalid")
        if not isinstance(mean, (int, float)) or isinstance(mean, bool):
            raise ValueError("stored unit evidence metric mean is invalid")
        if not isinstance(variance, (int, float)) or isinstance(variance, bool):
            raise ValueError("stored unit evidence metric variance is invalid")
        metrics.append(
            NamedMoments(
                name=name,
                estimate=NumericMoments(float(mean), float(variance)),
            )
        )
    return tuple(metrics)


def _configuration_row_values(
    observation: UnitConfigurationObservation,
) -> tuple[object, ...]:
    return (
        str(observation.observation_id),
        str(observation.team_season_id),
        str(observation.game_id),
        observation.unit_type.value,
        observation.logical_key,
        observation.revision,
        observation.availability_basis.value,
        _distribution_json(observation),
        observation.distribution_sha256,
        observation.payload_sha256,
        observation.configuration_contract,
        observation.configuration_version,
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


def _configuration_from_row(row: sqlite3.Row) -> UnitConfigurationObservation:
    available_at = _parse_time(row["available_at"])
    if available_at is None:
        raise ValueError("stored unit configuration is missing available_at")
    observation = UnitConfigurationObservation(
        observation_id=UnitConfigurationObservationId(str(row["observation_id"])),
        team_season_id=TeamSeasonId(str(row["team_season_id"])),
        game_id=GameId(str(row["game_id"])),
        unit_type=UnitType(str(row["unit_type"])),
        logical_key=str(row["logical_key"]),
        revision=int(row["revision"]),
        availability_basis=UnitConfigurationAvailabilityBasis(
            str(row["availability_basis"])
        ),
        alternatives=_distribution_from_json(row["distribution_json"]),
        configuration_contract=str(row["configuration_contract"]),
        configuration_version=str(row["configuration_version"]),
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
    if observation.distribution_sha256 != str(row["distribution_sha256"]):
        raise UnitStateEvidenceConflictError(
            f"stored unit configuration {observation.observation_id!s} has invalid distribution hash"
        )
    if observation.payload_sha256 != str(row["payload_sha256"]):
        raise UnitStateEvidenceConflictError(
            f"stored unit configuration {observation.observation_id!s} has invalid payload hash"
        )
    return observation


def record_unit_configuration_observation(
    connection: sqlite3.Connection,
    observation: UnitConfigurationObservation,
) -> None:
    """Persist one immutable unit-configuration prior idempotently."""

    existing = connection.execute(
        """
        SELECT observation_id, team_season_id, game_id, unit_type, logical_key,
               revision, availability_basis, distribution_json, distribution_sha256,
               payload_sha256, configuration_contract, configuration_version,
               provider_id, evidence_id, evidence_observation_id, effective_at,
               published_at, observed_at, ingested_at, available_at,
               availability_method, availability_confidence, provider_revision,
               provider_schema_version, parser_version, raw_sha256
        FROM unit_configuration_observations
        WHERE observation_id = ?
        """,
        (str(observation.observation_id),),
    ).fetchone()
    values = _configuration_row_values(observation)
    if existing is not None:
        if tuple(existing) != values:
            raise UnitStateEvidenceConflictError(
                f"stored unit configuration {observation.observation_id!s} conflicts"
            )
        return
    connection.execute(
        """
        INSERT INTO unit_configuration_observations(
            observation_id, team_season_id, game_id, unit_type, logical_key,
            revision, availability_basis, distribution_json, distribution_sha256,
            payload_sha256, configuration_contract, configuration_version,
            provider_id, evidence_id, evidence_observation_id, effective_at,
            published_at, observed_at, ingested_at, available_at,
            availability_method, availability_confidence, provider_revision,
            provider_schema_version, parser_version, raw_sha256
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?
        )
        """,
        values,
    )


def _evidence_row_values(observation: UnitStateEvidenceObservation) -> tuple[object, ...]:
    return (
        str(observation.observation_id),
        str(observation.team_season_id),
        str(observation.source_game_id) if observation.source_game_id is not None else None,
        observation.unit_type.value,
        observation.logical_key,
        observation.revision,
        observation.evidence_kind.value,
        _metrics_json(observation),
        observation.metrics_sha256,
        observation.payload_sha256,
        observation.sample_weight,
        observation.source_confidence.value,
        int(observation.residualized_against_player_state),
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


def _evidence_from_row(row: sqlite3.Row) -> UnitStateEvidenceObservation:
    available_at = _parse_time(row["available_at"])
    if available_at is None:
        raise ValueError("stored unit evidence is missing available_at")
    observation = UnitStateEvidenceObservation(
        observation_id=UnitStateEvidenceObservationId(str(row["observation_id"])),
        team_season_id=TeamSeasonId(str(row["team_season_id"])),
        source_game_id=(
            GameId(str(row["source_game_id"])) if row["source_game_id"] is not None else None
        ),
        unit_type=UnitType(str(row["unit_type"])),
        logical_key=str(row["logical_key"]),
        revision=int(row["revision"]),
        evidence_kind=UnitEvidenceKind(str(row["evidence_kind"])),
        metrics=_metrics_from_json(row["metrics_json"]),
        sample_weight=float(row["sample_weight"]),
        source_confidence=Probability(float(row["source_confidence"])),
        residualized_against_player_state=bool(
            int(row["residualized_against_player_state"])
        ),
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
        raise UnitStateEvidenceConflictError(
            f"stored unit evidence {observation.observation_id!s} has invalid metrics hash"
        )
    if observation.payload_sha256 != str(row["payload_sha256"]):
        raise UnitStateEvidenceConflictError(
            f"stored unit evidence {observation.observation_id!s} has invalid payload hash"
        )
    return observation


def record_unit_state_evidence(
    connection: sqlite3.Connection,
    observation: UnitStateEvidenceObservation,
) -> None:
    """Persist one immutable direct unit-state evidence observation idempotently."""

    existing = connection.execute(
        """
        SELECT observation_id, team_season_id, source_game_id, unit_type,
               logical_key, revision, evidence_kind, metrics_json, metrics_sha256,
               payload_sha256, sample_weight, source_confidence,
               residualized_against_player_state, evidence_contract,
               evidence_version, provider_id, evidence_id, evidence_observation_id,
               effective_at, published_at, observed_at, ingested_at, available_at,
               availability_method, availability_confidence, provider_revision,
               provider_schema_version, parser_version, raw_sha256
        FROM unit_state_evidence_observations
        WHERE observation_id = ?
        """,
        (str(observation.observation_id),),
    ).fetchone()
    values = _evidence_row_values(observation)
    if existing is not None:
        if tuple(existing) != values:
            raise UnitStateEvidenceConflictError(
                f"stored unit evidence {observation.observation_id!s} conflicts"
            )
        return
    connection.execute(
        """
        INSERT INTO unit_state_evidence_observations(
            observation_id, team_season_id, source_game_id, unit_type,
            logical_key, revision, evidence_kind, metrics_json, metrics_sha256,
            payload_sha256, sample_weight, source_confidence,
            residualized_against_player_state, evidence_contract,
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


def unit_configuration_observations_as_of(
    connection: sqlite3.Connection,
    *,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    unit_type: UnitType,
    as_of: datetime,
) -> tuple[UnitConfigurationObservation, ...]:
    """Select latest-known configuration revisions for each logical source key."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("unit configuration as_of must be timezone-aware")
    rows = connection.execute(
        """
        SELECT observation_id, team_season_id, game_id, unit_type, logical_key,
               revision, availability_basis, distribution_json, distribution_sha256,
               payload_sha256, configuration_contract, configuration_version,
               provider_id, evidence_id, evidence_observation_id, effective_at,
               published_at, observed_at, ingested_at, available_at,
               availability_method, availability_confidence, provider_revision,
               provider_schema_version, parser_version, raw_sha256
        FROM unit_configuration_observations
        WHERE team_season_id = ?
          AND game_id = ?
          AND unit_type = ?
          AND available_at <= ?
        ORDER BY logical_key, revision, available_at, observation_id
        """,
        (str(team_season_id), str(game_id), unit_type.value, _iso(as_of)),
    ).fetchall()
    latest_by_key: dict[str, UnitConfigurationObservation] = {}
    for row in rows:
        observation = _configuration_from_row(row)
        existing = latest_by_key.get(observation.logical_key)
        if existing is None or observation.revision > existing.revision:
            latest_by_key[observation.logical_key] = observation
    return tuple(
        sorted(latest_by_key.values(), key=lambda item: str(item.observation_id))
    )


def unit_state_evidence_as_of(
    connection: sqlite3.Connection,
    *,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    unit_type: UnitType,
    as_of: datetime,
) -> tuple[UnitStateEvidenceObservation, ...]:
    """Select latest-known PIT-safe direct evidence for one functional unit."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("unit evidence as_of must be timezone-aware")
    rows = connection.execute(
        """
        SELECT observation_id, team_season_id, source_game_id, unit_type,
               logical_key, revision, evidence_kind, metrics_json, metrics_sha256,
               payload_sha256, sample_weight, source_confidence,
               residualized_against_player_state, evidence_contract,
               evidence_version, provider_id, evidence_id, evidence_observation_id,
               effective_at, published_at, observed_at, ingested_at, available_at,
               availability_method, availability_confidence, provider_revision,
               provider_schema_version, parser_version, raw_sha256
        FROM unit_state_evidence_observations
        WHERE team_season_id = ?
          AND unit_type = ?
          AND available_at <= ?
          AND (source_game_id IS NULL OR source_game_id <> ?)
        ORDER BY logical_key, revision, available_at, observation_id
        """,
        (str(team_season_id), unit_type.value, _iso(as_of), str(game_id)),
    ).fetchall()
    latest_by_key: dict[str, UnitStateEvidenceObservation] = {}
    for row in rows:
        observation = _evidence_from_row(row)
        existing = latest_by_key.get(observation.logical_key)
        if existing is None or observation.revision > existing.revision:
            latest_by_key[observation.logical_key] = observation
    return tuple(
        sorted(latest_by_key.values(), key=lambda item: str(item.observation_id))
    )


def build_unit_state_as_of(
    connection: sqlite3.Connection,
    *,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    unit_type: UnitType,
    as_of: datetime,
    player_snapshots: tuple[StateSnapshotEnvelope[PlayerStatePayload], ...],
    config: UnitStateEstimatorConfig = DEFAULT_UNIT_STATE_ESTIMATOR_CONFIG,
    created_at: datetime,
) -> StateSnapshotEnvelope[UnitStatePayload]:
    """Reconstruct, persist, and seal one F-8 Unit State at a PIT cutoff."""

    for snapshot in player_snapshots:
        require_state_snapshot_sealed(connection, snapshot.snapshot_id)
    configuration_observations = unit_configuration_observations_as_of(
        connection,
        team_season_id=team_season_id,
        game_id=game_id,
        unit_type=unit_type,
        as_of=as_of,
    )
    unit_evidence = unit_state_evidence_as_of(
        connection,
        team_season_id=team_season_id,
        game_id=game_id,
        unit_type=unit_type,
        as_of=as_of,
    )
    snapshot = build_unit_state_snapshot(
        team_season_id=team_season_id,
        game_id=game_id,
        unit_type=unit_type,
        as_of=as_of,
        configuration_observations=configuration_observations,
        unit_evidence=unit_evidence,
        player_snapshots=player_snapshots,
        config=config,
        created_at=created_at,
    )
    record_state_snapshot(connection, snapshot)
    return snapshot
