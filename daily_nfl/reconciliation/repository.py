"""SQLite repository for canonical identity mappings and reconciliation decisions."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from daily_nfl.domain import FranchiseId, PersonId, PlayerId, TeamSeasonId
from daily_nfl.reconciliation.contracts import (
    CanonicalEntityType,
    CrosswalkBinding,
    ExternalIdentity,
    MatchMethod,
    ReconciliationDecision,
)


class CrosswalkConflictError(RuntimeError):
    """Raised when a proposed external-ID mapping conflicts with active history."""


class CanonicalIdentityNotFoundError(LookupError):
    """Raised when a crosswalk target is not present in canonical storage."""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("identity timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("stored identity timestamp is not timezone-aware")
    return parsed


def _intervals_overlap(
    left_start: datetime | None,
    left_end: datetime | None,
    right_start: datetime | None,
    right_end: datetime | None,
) -> bool:
    if left_end is not None and right_start is not None and left_end < right_start:
        return False
    if right_end is not None and left_start is not None and right_end < left_start:
        return False
    return True


def _binding_from_row(row: sqlite3.Row) -> CrosswalkBinding:
    return CrosswalkBinding(
        crosswalk_id=int(row["crosswalk_id"]),
        canonical_entity_type=CanonicalEntityType(str(row["canonical_entity_type"])),
        canonical_entity_id=str(row["canonical_entity_id"]),
        external_identity=ExternalIdentity(
            provider_id=str(row["provider_id"]),
            provider_entity_type=str(row["provider_entity_type"]),
            external_id=str(row["external_id"]),
        ),
        valid_from=_parse(row["valid_from"]),
        valid_to=_parse(row["valid_to"]),
        match_method=MatchMethod(str(row["match_method"])),
        match_confidence=float(row["match_confidence"]),
        verified=bool(row["verified"]),
        decision_id=str(row["decision_id"]) if row["decision_id"] is not None else None,
        supersedes_crosswalk_id=(
            int(row["supersedes_crosswalk_id"])
            if row["supersedes_crosswalk_id"] is not None
            else None
        ),
    )


@dataclass(slots=True)
class IdentityRepository:
    connection: sqlite3.Connection

    def active_crosswalks(self, external: ExternalIdentity) -> tuple[CrosswalkBinding, ...]:
        params: list[object] = [
            external.provider_id,
            external.provider_entity_type,
            external.external_id,
        ]
        temporal_sql = ""
        if external.valid_at is not None:
            valid_at = _iso(external.valid_at)
            temporal_sql = (
                "AND (cw.valid_from IS NULL OR cw.valid_from <= ?) "
                "AND (cw.valid_to IS NULL OR cw.valid_to >= ?) "
            )
            params.extend([valid_at, valid_at])

        rows = self.connection.execute(
            f"""
            SELECT cw.*
            FROM entity_crosswalk cw
            WHERE cw.provider_id = ?
              AND cw.provider_entity_type = ?
              AND cw.external_id = ?
              {temporal_sql}
              AND NOT EXISTS (
                  SELECT 1
                  FROM entity_crosswalk successor
                  WHERE successor.supersedes_crosswalk_id = cw.crosswalk_id
              )
            ORDER BY cw.crosswalk_id
            """,
            tuple(params),
        ).fetchall()
        return tuple(_binding_from_row(row) for row in rows)

    def crosswalk_by_id(self, crosswalk_id: int) -> CrosswalkBinding | None:
        row = self.connection.execute(
            "SELECT * FROM entity_crosswalk WHERE crosswalk_id = ?",
            (crosswalk_id,),
        ).fetchone()
        return _binding_from_row(row) if row is not None else None

    def record_decision(self, decision: ReconciliationDecision) -> None:
        details = {
            "candidates": [
                {
                    "canonical_entity_type": candidate.canonical_entity_type.value,
                    "canonical_entity_id": candidate.canonical_entity_id,
                    "match_method": candidate.match_method.value,
                    "match_confidence": candidate.match_confidence,
                    "explanation": candidate.explanation,
                }
                for candidate in decision.candidates
            ]
        }
        self.connection.execute(
            """
            INSERT INTO identity_reconciliation_decisions(
                decision_id,
                provider_id,
                provider_entity_type,
                external_id,
                expected_canonical_entity_type,
                status,
                selected_canonical_entity_id,
                match_method,
                match_confidence,
                candidate_count,
                valid_at,
                reason_code,
                details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision.decision_id,
                decision.external_identity.provider_id,
                decision.external_identity.provider_entity_type,
                decision.external_identity.external_id,
                decision.expected_entity_type.value,
                decision.status.value,
                decision.selected_canonical_entity_id,
                decision.match_method.value if decision.match_method is not None else None,
                decision.match_confidence,
                len(decision.candidates),
                _iso(decision.external_identity.valid_at),
                decision.reason.value,
                json.dumps(details, sort_keys=True, separators=(",", ":")),
            ),
        )

    def bind(
        self,
        *,
        canonical_entity_type: CanonicalEntityType,
        canonical_entity_id: str,
        external: ExternalIdentity,
        match_method: MatchMethod,
        match_confidence: float,
        verified: bool,
        decision_id: str | None,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        supersedes_crosswalk_id: int | None = None,
    ) -> CrosswalkBinding:
        if match_method is MatchMethod.FUZZY_CANDIDATE_ONLY:
            raise ValueError("fuzzy candidates cannot be persisted as resolved crosswalks")
        if not 0.0 <= match_confidence <= 1.0:
            raise ValueError("match_confidence must be between 0 and 1")
        if valid_from is not None and valid_to is not None and valid_to < valid_from:
            raise ValueError("valid_to cannot precede valid_from")
        self._require_canonical_identity(canonical_entity_type, canonical_entity_id)

        superseded: CrosswalkBinding | None = None
        if supersedes_crosswalk_id is not None:
            superseded = self.crosswalk_by_id(supersedes_crosswalk_id)
            if superseded is None:
                raise CrosswalkConflictError("superseded crosswalk does not exist")
            if (
                superseded.external_identity.provider_id != external.provider_id
                or superseded.external_identity.provider_entity_type
                != external.provider_entity_type
                or superseded.external_identity.external_id != external.external_id
            ):
                raise CrosswalkConflictError(
                    "superseding mapping must refer to the same provider external identity"
                )

        lookup_external = ExternalIdentity(
            provider_id=external.provider_id,
            provider_entity_type=external.provider_entity_type,
            external_id=external.external_id,
        )
        for existing in self.active_crosswalks(lookup_external):
            if existing.crosswalk_id == supersedes_crosswalk_id:
                continue
            if not _intervals_overlap(
                existing.valid_from,
                existing.valid_to,
                valid_from,
                valid_to,
            ):
                continue
            if (
                existing.canonical_entity_type is canonical_entity_type
                and existing.canonical_entity_id == canonical_entity_id
                and existing.valid_from == valid_from
                and existing.valid_to == valid_to
            ):
                return existing
            raise CrosswalkConflictError(
                "external identity already has an overlapping active canonical mapping"
            )

        cursor = self.connection.execute(
            """
            INSERT INTO entity_crosswalk(
                canonical_entity_type,
                canonical_entity_id,
                provider_id,
                provider_entity_type,
                external_id,
                valid_from,
                valid_to,
                match_method,
                match_confidence,
                verified,
                decision_id,
                supersedes_crosswalk_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                canonical_entity_type.value,
                canonical_entity_id,
                external.provider_id,
                external.provider_entity_type,
                external.external_id,
                _iso(valid_from),
                _iso(valid_to),
                match_method.value,
                match_confidence,
                int(verified),
                decision_id,
                supersedes_crosswalk_id,
            ),
        )
        crosswalk_id = int(cursor.lastrowid)
        binding = self.crosswalk_by_id(crosswalk_id)
        if binding is None:
            raise RuntimeError("inserted crosswalk could not be reloaded")
        return binding

    def ensure_franchise(self, franchise_id: FranchiseId, canonical_name: str | None = None) -> None:
        self.connection.execute(
            """
            INSERT INTO franchises(franchise_id, canonical_name)
            VALUES (?, ?)
            ON CONFLICT(franchise_id) DO NOTHING
            """,
            (str(franchise_id), canonical_name),
        )

    def ensure_team_season(
        self,
        team_season_id: TeamSeasonId,
        franchise_id: FranchiseId,
        season: int,
        display_name: str | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO team_seasons(team_season_id, franchise_id, season, display_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(team_season_id) DO NOTHING
            """,
            (str(team_season_id), str(franchise_id), season, display_name),
        )
        row = self.connection.execute(
            "SELECT franchise_id, season FROM team_seasons WHERE team_season_id = ?",
            (str(team_season_id),),
        ).fetchone()
        if row is None or str(row[0]) != str(franchise_id) or int(row[1]) != season:
            raise CrosswalkConflictError("team-season canonical identity conflicts with stored facts")

    def ensure_person_player(
        self,
        person_id: PersonId,
        player_id: PlayerId,
        canonical_name: str | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO persons(person_id, canonical_name)
            VALUES (?, ?)
            ON CONFLICT(person_id) DO NOTHING
            """,
            (str(person_id), canonical_name),
        )
        self.connection.execute(
            """
            INSERT INTO players(player_id, person_id)
            VALUES (?, ?)
            ON CONFLICT(player_id) DO NOTHING
            """,
            (str(player_id), str(person_id)),
        )
        row = self.connection.execute(
            "SELECT person_id FROM players WHERE player_id = ?",
            (str(player_id),),
        ).fetchone()
        if row is None or str(row[0]) != str(person_id):
            raise CrosswalkConflictError("player canonical identity conflicts with stored person")

    def game_candidates(
        self,
        *,
        season: int,
        season_phase: str,
        home_team_season_id: TeamSeasonId,
        away_team_season_id: TeamSeasonId,
        week: int | None,
    ) -> tuple[sqlite3.Row, ...]:
        sql = """
            SELECT game_id, event_id, week, scheduled_kickoff
            FROM games
            WHERE season = ?
              AND season_phase = ?
              AND home_team_season_id = ?
              AND away_team_season_id = ?
        """
        params: list[object] = [
            season,
            season_phase,
            str(home_team_season_id),
            str(away_team_season_id),
        ]
        if week is not None:
            sql += " AND week = ?"
            params.append(week)
        sql += " ORDER BY scheduled_kickoff, game_id"
        return tuple(self.connection.execute(sql, tuple(params)).fetchall())

    def _require_canonical_identity(
        self,
        entity_type: CanonicalEntityType,
        canonical_entity_id: str,
    ) -> None:
        table_and_column = {
            CanonicalEntityType.FRANCHISE: ("franchises", "franchise_id"),
            CanonicalEntityType.TEAM_SEASON: ("team_seasons", "team_season_id"),
            CanonicalEntityType.PERSON: ("persons", "person_id"),
            CanonicalEntityType.PLAYER: ("players", "player_id"),
            CanonicalEntityType.GAME: ("games", "game_id"),
            CanonicalEntityType.EVENT: ("games", "event_id"),
        }[entity_type]
        table, column = table_and_column
        row = self.connection.execute(
            f"SELECT 1 FROM {table} WHERE {column} = ? LIMIT 1",
            (canonical_entity_id,),
        ).fetchone()
        if row is None:
            raise CanonicalIdentityNotFoundError(
                f"canonical {entity_type.value} identity {canonical_entity_id!r} does not exist"
            )
