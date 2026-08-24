"""Internal canonical-row helpers shared by the certified M6 persistence boundary."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from daily_nfl.normalization.contracts import NormalizedPlayBundle


class NormalizedPlayConflictError(RuntimeError):
    """Raised when canonical or observation identity conflicts with stored history."""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("normalization timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


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
        raise NormalizedPlayConflictError(
            f"canonical {table} identity conflicts with stored facts"
        )


def _ensure_canonical_rows(
    connection: sqlite3.Connection,
    bundle: NormalizedPlayBundle,
) -> None:
    pre = bundle.pre_play_state
    possession = pre.possession
    segment_id = pre.possession_segment_id
    if segment_id is None or bundle.possession_sequence is None:
        raise NormalizedPlayConflictError(
            "canonical normalized play requires possession-segment identity and sequence"
        )

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
        raise NormalizedPlayConflictError(
            "canonical possession conflicts with stored facts"
        )

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
        SELECT game_id, canonical_sequence, offense_team_season_id,
               defense_team_season_id
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
        if bundle.drive_sequence is None:
            raise NormalizedPlayConflictError(
                "canonical drive identity requires drive_sequence"
            )
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
            raise NormalizedPlayConflictError(
                "canonical drive conflicts with stored facts"
            )

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
        SELECT game_id, drive_id, possession_id, canonical_sequence,
               possession_segment_id
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


__all__ = ["NormalizedPlayConflictError", "_ensure_canonical_rows", "_iso"]
