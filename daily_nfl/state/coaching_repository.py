"""Append-only persistence and PIT reconstruction for M7-F Coaching State."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import cast

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    CoachingAssignmentObservationId,
    CoachingSchemeEvidenceObservationId,
    CoachingStintId,
    GameId,
    KnowledgeTimestamp,
    PersonId,
    PublicSchemeLabelObservationId,
    TeamSeasonId,
)
from daily_nfl.state.coaching import (
    DEFAULT_COACHING_STATE_ESTIMATOR_CONFIG,
    CoachingAssignmentObservation,
    CoachingEvidenceScope,
    CoachingGameStateCondition,
    CoachingResponsibility,
    CoachingRoleType,
    CoachingSchemeEvidenceObservation,
    CoachingStateComponent,
    CoachingStateEstimatorConfig,
    CoachingStatePayload,
    PublicSchemeLabelObservation,
    PublicSchemeSide,
    build_coaching_state_snapshot,
    resolve_active_coaching_assignments,
)
from daily_nfl.state.contracts import StateSnapshotEnvelope
from daily_nfl.state.repository import record_state_snapshot
from daily_nfl.state.snapshot import canonical_state_json
from daily_nfl.state.uncertainty import NamedMoments, NumericMoments, Probability


class CoachingStateEvidenceConflictError(RuntimeError):
    """Raised when stored coaching evidence conflicts with immutable content."""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("coaching evidence timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: object | None) -> datetime | None:
    if value is None:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("stored coaching timestamp must be timezone-aware")
    return parsed


def _optional_text(value: object | None) -> str | None:
    return str(value) if value is not None else None


def _responsibilities_json(observation: CoachingAssignmentObservation) -> str:
    return canonical_state_json(
        [item.value for item in observation.canonical_responsibilities]
    )


def _responsibilities_from_json(value: object) -> tuple[CoachingResponsibility, ...]:
    decoded = json.loads(str(value))
    if not isinstance(decoded, list):
        raise ValueError("stored coaching responsibilities must be a JSON list")
    responsibilities: list[CoachingResponsibility] = []
    for item in decoded:
        if not isinstance(item, str):
            raise ValueError("stored coaching responsibility must be text")
        responsibilities.append(CoachingResponsibility(item))
    return tuple(responsibilities)


def _condition_json(observation: CoachingSchemeEvidenceObservation) -> str:
    return canonical_state_json(observation.condition)


def _condition_from_json(value: object) -> CoachingGameStateCondition:
    decoded = json.loads(str(value))
    if not isinstance(decoded, dict):
        raise ValueError("stored coaching condition must be a JSON object")
    item = cast(dict[str, object], decoded)

    def optional_string(name: str) -> str | None:
        raw = item.get(name)
        if raw is None:
            return None
        if not isinstance(raw, str):
            raise ValueError(f"stored coaching condition {name} must be text")
        return raw

    neutral = item.get("neutral_situation")
    if neutral is not None and not isinstance(neutral, bool):
        raise ValueError("stored coaching condition neutral_situation must be boolean")
    contract = item.get("contract")
    version = item.get("version")
    if not isinstance(contract, str) or not isinstance(version, str):
        raise ValueError("stored coaching condition contract/version is invalid")
    return CoachingGameStateCondition(
        contract=contract,
        version=version,
        neutral_situation=neutral,
        down_bucket=optional_string("down_bucket"),
        distance_bucket=optional_string("distance_bucket"),
        score_state=optional_string("score_state"),
        time_state=optional_string("time_state"),
        field_position_state=optional_string("field_position_state"),
        personnel_state=optional_string("personnel_state"),
        opponent_context=optional_string("opponent_context"),
    )


def _metrics_json(observation: CoachingSchemeEvidenceObservation) -> str:
    payload = [
        {
            "name": metric.name,
            "mean": metric.estimate.mean,
            "variance": metric.estimate.variance,
        }
        for metric in sorted(observation.metrics, key=lambda item: item.name)
    ]
    return canonical_state_json(payload)


def _metrics_from_json(value: object) -> tuple[NamedMoments, ...]:
    decoded = json.loads(str(value))
    if not isinstance(decoded, list):
        raise ValueError("stored coaching metrics must be a JSON list")
    metrics: list[NamedMoments] = []
    for raw_item in decoded:
        if not isinstance(raw_item, dict):
            raise ValueError("stored coaching metric entry must be an object")
        item = cast(dict[str, object], raw_item)
        name = item.get("name")
        mean = item.get("mean")
        variance = item.get("variance")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("stored coaching metric name is invalid")
        if not isinstance(mean, (int, float)) or isinstance(mean, bool):
            raise ValueError("stored coaching metric mean is invalid")
        if not isinstance(variance, (int, float)) or isinstance(variance, bool):
            raise ValueError("stored coaching metric variance is invalid")
        metrics.append(
            NamedMoments(
                name=name,
                estimate=NumericMoments(float(mean), float(variance)),
            )
        )
    return tuple(metrics)


def _assignment_row_values(
    observation: CoachingAssignmentObservation,
) -> tuple[object, ...]:
    return (
        str(observation.observation_id),
        str(observation.coaching_stint_id),
        str(observation.person_id),
        str(observation.team_season_id),
        observation.logical_key,
        observation.revision,
        observation.role_type.value,
        _responsibilities_json(observation),
        observation.responsibilities_sha256,
        observation.payload_sha256,
        _iso(observation.effective_from),
        _iso(observation.effective_to),
        observation.assignment_contract,
        observation.assignment_version,
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


def _ensure_coaching_stint(
    connection: sqlite3.Connection,
    observation: CoachingAssignmentObservation,
) -> None:
    row = connection.execute(
        "SELECT coaching_stint_id, person_id, team_season_id "
        "FROM coaching_stints WHERE coaching_stint_id = ?",
        (str(observation.coaching_stint_id),),
    ).fetchone()
    expected = (
        str(observation.coaching_stint_id),
        str(observation.person_id),
        str(observation.team_season_id),
    )
    if row is not None:
        if tuple(row) != expected:
            raise CoachingStateEvidenceConflictError(
                f"coaching stint {observation.coaching_stint_id!s} conflicts"
            )
        return
    connection.execute(
        "INSERT INTO coaching_stints(coaching_stint_id, person_id, team_season_id) "
        "VALUES (?, ?, ?)",
        expected,
    )


def record_coaching_assignment_observation(
    connection: sqlite3.Connection,
    observation: CoachingAssignmentObservation,
) -> None:
    """Persist one immutable coaching assignment observation idempotently."""

    _ensure_coaching_stint(connection, observation)
    existing = connection.execute(
        """
        SELECT observation_id, coaching_stint_id, person_id, team_season_id,
               logical_key, revision, role_type, responsibilities_json,
               responsibilities_sha256, payload_sha256, effective_from,
               effective_to, assignment_contract, assignment_version,
               provider_id, evidence_id, evidence_observation_id,
               knowledge_effective_at, published_at, observed_at, ingested_at,
               available_at, availability_method, availability_confidence,
               provider_revision, provider_schema_version, parser_version,
               raw_sha256
        FROM coaching_assignment_observations
        WHERE observation_id = ?
        """,
        (str(observation.observation_id),),
    ).fetchone()
    values = _assignment_row_values(observation)
    if existing is not None:
        if tuple(existing) != values:
            raise CoachingStateEvidenceConflictError(
                f"stored coaching assignment {observation.observation_id!s} conflicts"
            )
        return
    connection.execute(
        """
        INSERT INTO coaching_assignment_observations(
            observation_id, coaching_stint_id, person_id, team_season_id,
            logical_key, revision, role_type, responsibilities_json,
            responsibilities_sha256, payload_sha256, effective_from, effective_to,
            assignment_contract, assignment_version, provider_id, evidence_id,
            evidence_observation_id, knowledge_effective_at, published_at,
            observed_at, ingested_at, available_at, availability_method,
            availability_confidence, provider_revision, provider_schema_version,
            parser_version, raw_sha256
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        values,
    )


def _assignment_from_row(row: sqlite3.Row) -> CoachingAssignmentObservation:
    available_at = _parse_time(row["available_at"])
    if available_at is None:
        raise ValueError("stored coaching assignment is missing available_at")
    observation = CoachingAssignmentObservation(
        observation_id=CoachingAssignmentObservationId(str(row["observation_id"])),
        coaching_stint_id=CoachingStintId(str(row["coaching_stint_id"])),
        person_id=PersonId(str(row["person_id"])),
        team_season_id=TeamSeasonId(str(row["team_season_id"])),
        logical_key=str(row["logical_key"]),
        revision=int(row["revision"]),
        role_type=CoachingRoleType(str(row["role_type"])),
        responsibilities=_responsibilities_from_json(row["responsibilities_json"]),
        effective_from=_parse_time(row["effective_from"]),
        effective_to=_parse_time(row["effective_to"]),
        assignment_contract=str(row["assignment_contract"]),
        assignment_version=str(row["assignment_version"]),
        provider_id=_optional_text(row["provider_id"]),
        evidence_id=_optional_text(row["evidence_id"]),
        evidence_observation_id=_optional_text(row["evidence_observation_id"]),
        provider_revision=_optional_text(row["provider_revision"]),
        provider_schema_version=_optional_text(row["provider_schema_version"]),
        parser_version=_optional_text(row["parser_version"]),
        raw_sha256=_optional_text(row["raw_sha256"]),
        knowledge=KnowledgeTimestamp(
            available_at=available_at,
            effective_at=_parse_time(row["knowledge_effective_at"]),
            published_at=_parse_time(row["published_at"]),
            observed_at=_parse_time(row["observed_at"]),
            ingested_at=_parse_time(row["ingested_at"]),
            availability_method=AvailabilityMethod(str(row["availability_method"])),
            availability_confidence=AvailabilityConfidence(
                str(row["availability_confidence"])
            ),
        ),
    )
    if observation.responsibilities_sha256 != str(row["responsibilities_sha256"]):
        raise CoachingStateEvidenceConflictError(
            "stored coaching assignment "
            f"{observation.observation_id!s} has invalid responsibilities hash"
        )
    if observation.payload_sha256 != str(row["payload_sha256"]):
        raise CoachingStateEvidenceConflictError(
            f"stored coaching assignment {observation.observation_id!s} has invalid payload hash"
        )
    return observation


def _scheme_row_values(
    observation: CoachingSchemeEvidenceObservation,
) -> tuple[object, ...]:
    return (
        str(observation.observation_id),
        str(observation.team_season_id),
        str(observation.source_game_id) if observation.source_game_id is not None else None,
        (
            str(observation.applies_to_game_id)
            if observation.applies_to_game_id is not None
            else None
        ),
        observation.logical_key,
        observation.revision,
        observation.component.value,
        observation.evidence_scope.value,
        int(observation.game_state_conditioned),
        _condition_json(observation),
        observation.conditioning_sha256,
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


def record_coaching_scheme_evidence(
    connection: sqlite3.Connection,
    observation: CoachingSchemeEvidenceObservation,
) -> None:
    """Persist one immutable empirical coaching/scheme evidence observation."""

    existing = connection.execute(
        """
        SELECT observation_id, team_season_id, source_game_id, applies_to_game_id,
               logical_key, revision, component, evidence_scope,
               game_state_conditioned, conditioning_json, conditioning_sha256,
               metrics_json, metrics_sha256, payload_sha256, sample_weight,
               source_confidence, evidence_contract, evidence_version, provider_id,
               evidence_id, evidence_observation_id, effective_at, published_at,
               observed_at, ingested_at, available_at, availability_method,
               availability_confidence, provider_revision, provider_schema_version,
               parser_version, raw_sha256
        FROM coaching_scheme_evidence_observations
        WHERE observation_id = ?
        """,
        (str(observation.observation_id),),
    ).fetchone()
    values = _scheme_row_values(observation)
    if existing is not None:
        if tuple(existing) != values:
            raise CoachingStateEvidenceConflictError(
                f"stored coaching scheme evidence {observation.observation_id!s} conflicts"
            )
        return
    connection.execute(
        """
        INSERT INTO coaching_scheme_evidence_observations(
            observation_id, team_season_id, source_game_id, applies_to_game_id,
            logical_key, revision, component, evidence_scope,
            game_state_conditioned, conditioning_json, conditioning_sha256,
            metrics_json, metrics_sha256, payload_sha256, sample_weight,
            source_confidence, evidence_contract, evidence_version, provider_id,
            evidence_id, evidence_observation_id, effective_at, published_at,
            observed_at, ingested_at, available_at, availability_method,
            availability_confidence, provider_revision, provider_schema_version,
            parser_version, raw_sha256
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        values,
    )


def _scheme_from_row(row: sqlite3.Row) -> CoachingSchemeEvidenceObservation:
    available_at = _parse_time(row["available_at"])
    if available_at is None:
        raise ValueError("stored coaching scheme evidence is missing available_at")
    observation = CoachingSchemeEvidenceObservation(
        observation_id=CoachingSchemeEvidenceObservationId(str(row["observation_id"])),
        team_season_id=TeamSeasonId(str(row["team_season_id"])),
        source_game_id=(
            GameId(str(row["source_game_id"]))
            if row["source_game_id"] is not None
            else None
        ),
        applies_to_game_id=(
            GameId(str(row["applies_to_game_id"]))
            if row["applies_to_game_id"] is not None
            else None
        ),
        logical_key=str(row["logical_key"]),
        revision=int(row["revision"]),
        component=CoachingStateComponent(str(row["component"])),
        evidence_scope=CoachingEvidenceScope(str(row["evidence_scope"])),
        condition=_condition_from_json(row["conditioning_json"]),
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
    if int(observation.game_state_conditioned) != int(row["game_state_conditioned"]):
        raise CoachingStateEvidenceConflictError(
            "stored coaching scheme evidence "
            f"{observation.observation_id!s} has invalid conditioning flag"
        )
    if observation.conditioning_sha256 != str(row["conditioning_sha256"]):
        raise CoachingStateEvidenceConflictError(
            "stored coaching scheme evidence "
            f"{observation.observation_id!s} has invalid conditioning hash"
        )
    if observation.metrics_sha256 != str(row["metrics_sha256"]):
        raise CoachingStateEvidenceConflictError(
            "stored coaching scheme evidence "
            f"{observation.observation_id!s} has invalid metrics hash"
        )
    if observation.payload_sha256 != str(row["payload_sha256"]):
        raise CoachingStateEvidenceConflictError(
            "stored coaching scheme evidence "
            f"{observation.observation_id!s} has invalid payload hash"
        )
    return observation


def _label_row_values(observation: PublicSchemeLabelObservation) -> tuple[object, ...]:
    return (
        str(observation.observation_id),
        str(observation.team_season_id),
        observation.side.value,
        observation.logical_key,
        observation.revision,
        observation.label,
        observation.payload_sha256,
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


def record_public_scheme_label_observation(
    connection: sqlite3.Connection,
    observation: PublicSchemeLabelObservation,
) -> None:
    """Persist a descriptive public label without promoting it to analytics."""

    existing = connection.execute(
        """
        SELECT observation_id, team_season_id, side, logical_key, revision,
               label, payload_sha256, provider_id, evidence_id,
               evidence_observation_id, effective_at, published_at, observed_at,
               ingested_at, available_at, availability_method,
               availability_confidence, provider_revision,
               provider_schema_version, parser_version, raw_sha256
        FROM public_scheme_label_observations
        WHERE observation_id = ?
        """,
        (str(observation.observation_id),),
    ).fetchone()
    values = _label_row_values(observation)
    if existing is not None:
        if tuple(existing) != values:
            raise CoachingStateEvidenceConflictError(
                f"stored public scheme label {observation.observation_id!s} conflicts"
            )
        return
    connection.execute(
        """
        INSERT INTO public_scheme_label_observations(
            observation_id, team_season_id, side, logical_key, revision, label,
            payload_sha256, provider_id, evidence_id, evidence_observation_id,
            effective_at, published_at, observed_at, ingested_at, available_at,
            availability_method, availability_confidence, provider_revision,
            provider_schema_version, parser_version, raw_sha256
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        values,
    )


def _label_from_row(row: sqlite3.Row) -> PublicSchemeLabelObservation:
    available_at = _parse_time(row["available_at"])
    if available_at is None:
        raise ValueError("stored public scheme label is missing available_at")
    observation = PublicSchemeLabelObservation(
        observation_id=PublicSchemeLabelObservationId(str(row["observation_id"])),
        team_season_id=TeamSeasonId(str(row["team_season_id"])),
        side=PublicSchemeSide(str(row["side"])),
        logical_key=str(row["logical_key"]),
        revision=int(row["revision"]),
        label=str(row["label"]),
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
    if observation.payload_sha256 != str(row["payload_sha256"]):
        raise CoachingStateEvidenceConflictError(
            f"stored public scheme label {observation.observation_id!s} has invalid payload hash"
        )
    return observation


def coaching_assignments_as_of(
    connection: sqlite3.Connection,
    *,
    team_season_id: TeamSeasonId,
    as_of: datetime,
) -> tuple[CoachingAssignmentObservation, ...]:
    """Return resolved active coaching assignments at one PIT cutoff."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("coaching assignment as_of must be timezone-aware")
    rows = connection.execute(
        """
        SELECT observation_id, coaching_stint_id, person_id, team_season_id,
               logical_key, revision, role_type, responsibilities_json,
               responsibilities_sha256, payload_sha256, effective_from,
               effective_to, assignment_contract, assignment_version,
               provider_id, evidence_id, evidence_observation_id,
               knowledge_effective_at, published_at, observed_at, ingested_at,
               available_at, availability_method, availability_confidence,
               provider_revision, provider_schema_version, parser_version,
               raw_sha256
        FROM coaching_assignment_observations
        WHERE team_season_id = ? AND available_at <= ?
        ORDER BY logical_key, revision, available_at, observation_id
        """,
        (str(team_season_id), _iso(as_of)),
    ).fetchall()
    observations = tuple(_assignment_from_row(row) for row in rows)
    try:
        return resolve_active_coaching_assignments(
            observations,
            team_season_id=team_season_id,
            as_of=as_of,
        )
    except ValueError as exc:
        raise CoachingStateEvidenceConflictError(str(exc)) from exc


def coaching_scheme_evidence_as_of(
    connection: sqlite3.Connection,
    *,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    as_of: datetime,
) -> tuple[CoachingSchemeEvidenceObservation, ...]:
    """Return latest-known PIT-safe empirical coaching evidence for one game."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("coaching scheme as_of must be timezone-aware")
    rows = connection.execute(
        """
        SELECT observation_id, team_season_id, source_game_id, applies_to_game_id,
               logical_key, revision, component, evidence_scope,
               game_state_conditioned, conditioning_json, conditioning_sha256,
               metrics_json, metrics_sha256, payload_sha256, sample_weight,
               source_confidence, evidence_contract, evidence_version, provider_id,
               evidence_id, evidence_observation_id, effective_at, published_at,
               observed_at, ingested_at, available_at, availability_method,
               availability_confidence, provider_revision, provider_schema_version,
               parser_version, raw_sha256
        FROM coaching_scheme_evidence_observations
        WHERE team_season_id = ?
          AND available_at <= ?
          AND (source_game_id IS NULL OR source_game_id <> ?)
          AND (evidence_scope = 'BASE' OR applies_to_game_id = ?)
        ORDER BY logical_key, revision, available_at, observation_id
        """,
        (str(team_season_id), _iso(as_of), str(game_id), str(game_id)),
    ).fetchall()
    latest_by_key: dict[str, CoachingSchemeEvidenceObservation] = {}
    for row in rows:
        observation = _scheme_from_row(row)
        existing = latest_by_key.get(observation.logical_key)
        if existing is None or observation.revision > existing.revision:
            latest_by_key[observation.logical_key] = observation
        elif observation.revision == existing.revision:
            if observation.payload_sha256 != existing.payload_sha256:
                raise CoachingStateEvidenceConflictError(
                    f"conflicting coaching scheme revision for {observation.logical_key!r}"
                )
            if str(observation.observation_id) < str(existing.observation_id):
                latest_by_key[observation.logical_key] = observation
    return tuple(
        sorted(latest_by_key.values(), key=lambda item: str(item.observation_id))
    )


def public_scheme_labels_as_of(
    connection: sqlite3.Connection,
    *,
    team_season_id: TeamSeasonId,
    as_of: datetime,
) -> tuple[PublicSchemeLabelObservation, ...]:
    """Return latest-known descriptive public scheme labels at one cutoff."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("public scheme label as_of must be timezone-aware")
    rows = connection.execute(
        """
        SELECT observation_id, team_season_id, side, logical_key, revision,
               label, payload_sha256, provider_id, evidence_id,
               evidence_observation_id, effective_at, published_at, observed_at,
               ingested_at, available_at, availability_method,
               availability_confidence, provider_revision,
               provider_schema_version, parser_version, raw_sha256
        FROM public_scheme_label_observations
        WHERE team_season_id = ? AND available_at <= ?
        ORDER BY logical_key, revision, available_at, observation_id
        """,
        (str(team_season_id), _iso(as_of)),
    ).fetchall()
    latest_by_key: dict[str, PublicSchemeLabelObservation] = {}
    for row in rows:
        observation = _label_from_row(row)
        existing = latest_by_key.get(observation.logical_key)
        if existing is None or observation.revision > existing.revision:
            latest_by_key[observation.logical_key] = observation
        elif observation.revision == existing.revision:
            if observation.payload_sha256 != existing.payload_sha256:
                raise CoachingStateEvidenceConflictError(
                    f"conflicting public scheme label revision for {observation.logical_key!r}"
                )
            if str(observation.observation_id) < str(existing.observation_id):
                latest_by_key[observation.logical_key] = observation
    return tuple(
        sorted(
            latest_by_key.values(),
            key=lambda item: (item.side.value, item.label, item.logical_key),
        )
    )


def build_coaching_state_as_of(
    connection: sqlite3.Connection,
    *,
    team_season_id: TeamSeasonId,
    game_id: GameId,
    as_of: datetime,
    config: CoachingStateEstimatorConfig = DEFAULT_COACHING_STATE_ESTIMATOR_CONFIG,
    created_at: datetime,
) -> StateSnapshotEnvelope[CoachingStatePayload]:
    """Reconstruct, persist, and seal one F-9 Coaching State at a PIT cutoff."""

    assignments = coaching_assignments_as_of(
        connection,
        team_season_id=team_season_id,
        as_of=as_of,
    )
    scheme_evidence = coaching_scheme_evidence_as_of(
        connection,
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
    )
    labels = public_scheme_labels_as_of(
        connection,
        team_season_id=team_season_id,
        as_of=as_of,
    )
    coaching_snapshot = build_coaching_state_snapshot(
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
        assignment_observations=assignments,
        scheme_evidence=scheme_evidence,
        public_scheme_labels=labels,
        config=config,
        created_at=created_at,
    )
    record_state_snapshot(connection, coaching_snapshot)
    return coaching_snapshot
