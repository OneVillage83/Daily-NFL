"""Deterministic nflverse-to-canonical play normalization for M6."""

from __future__ import annotations

from daily_nfl.domain import (
    Period,
    Penalty,
    PlayDesignModifier,
    PlayEvent,
    PlayEventType,
    PlayExecution,
    PlayResult,
    PlayStateAfter,
    PlayType,
    Possession,
    PrePlayState,
)
from daily_nfl.normalization.contracts import (
    NflverseGameContext,
    NflversePlayRecord,
    NormalizedPlayBundle,
)
from daily_nfl.reconciliation import (
    drive_id_for,
    play_event_id_for,
    play_id_for,
    possession_id_for,
)


class PlayNormalizationError(ValueError):
    """Raised when a provider row cannot be normalized without guessing."""


def _hint(record: NflversePlayRecord) -> str:
    return (record.play_type_hint or "").strip().lower().replace("-", "_")


def classify_play_type(record: NflversePlayRecord) -> PlayType:
    """Map provider indicators to the canonical primary play taxonomy."""

    hint = _hint(record)
    if record.qb_kneel or hint in {"qb_kneel", "kneel"}:
        return PlayType.KNEEL
    if record.qb_spike or hint in {"qb_spike", "spike"}:
        return PlayType.SPIKE
    if record.punt_attempt or hint == "punt":
        return PlayType.PUNT
    if record.field_goal_attempt or hint in {"field_goal", "field_goal_attempt"}:
        return PlayType.FIELD_GOAL
    if record.kickoff_attempt or hint == "kickoff":
        return PlayType.KICKOFF
    if record.extra_point_attempt or hint in {"extra_point", "extra_point_attempt"}:
        return PlayType.EXTRA_POINT
    if record.two_point_attempt or hint in {"two_point", "two_point_attempt"}:
        return PlayType.TWO_POINT
    if record.sack or hint == "sack":
        return PlayType.SACK
    if record.qb_scramble or hint in {"qb_scramble", "scramble"}:
        return PlayType.SCRAMBLE
    if record.pass_attempt or hint == "pass":
        return PlayType.PASS
    if record.rush_attempt or hint in {"run", "rush"}:
        return PlayType.RUSH
    if record.timeout or hint == "timeout":
        return PlayType.TIMEOUT
    if record.no_play and record.penalties:
        return PlayType.PENALTY_ONLY
    if record.administrative or hint in {
        "administrative",
        "end_game",
        "end_period",
        "game_start",
        "quarter_end",
    }:
        return PlayType.ADMINISTRATIVE
    return PlayType.OTHER


def _modifiers(record: NflversePlayRecord, play_type: PlayType) -> frozenset[PlayDesignModifier]:
    if play_type not in {PlayType.PASS, PlayType.RUSH, PlayType.SCRAMBLE, PlayType.SACK}:
        return frozenset()

    modifiers: set[PlayDesignModifier] = set()
    for enabled, modifier in (
        (record.play_action, PlayDesignModifier.PLAY_ACTION),
        (record.rpo, PlayDesignModifier.RPO),
        (record.screen, PlayDesignModifier.SCREEN),
        (record.shotgun, PlayDesignModifier.SHOTGUN),
        (record.under_center, PlayDesignModifier.UNDER_CENTER),
        (record.motion, PlayDesignModifier.MOTION),
        (record.shift, PlayDesignModifier.SHIFT),
        (record.no_huddle, PlayDesignModifier.NO_HUDDLE),
        (record.designed_qb_run, PlayDesignModifier.DESIGNED_QB_RUN),
    ):
        if enabled:
            modifiers.add(modifier)
    return frozenset(modifiers)


def _score_change(record: NflversePlayRecord, next_record: NflversePlayRecord | None) -> int:
    home_after = record.home_score_after
    away_after = record.away_score_after
    if home_after is None or away_after is None:
        if next_record is None:
            return 0
        home_after = next_record.home_score_before
        away_after = next_record.away_score_before

    before = record.home_score_before + record.away_score_before
    after = home_after + away_after
    if after < before:
        raise PlayNormalizationError("post-play total score cannot be lower than pre-play score")
    return after - before


def _require_possession_codes(record: NflversePlayRecord) -> tuple[str, str]:
    offense = record.offense_team_code
    defense = record.defense_team_code
    if offense is None or defense is None:
        raise PlayNormalizationError(
            "normalization requires explicit offense and defense team codes"
        )
    if offense == defense:
        raise PlayNormalizationError("offense and defense team codes must differ")
    return offense, defense


def _build_events(
    *,
    record: NflversePlayRecord,
    play_id,
    play_type: PlayType,
    score_change: int,
) -> tuple[PlayEvent, ...]:
    event_specs: list[tuple[PlayEventType, str | None]] = []
    if play_type in {
        PlayType.PASS,
        PlayType.RUSH,
        PlayType.SCRAMBLE,
        PlayType.SACK,
        PlayType.KNEEL,
        PlayType.SPIKE,
    }:
        event_specs.append((PlayEventType.SNAP, None))
    if play_type is PlayType.PASS:
        event_specs.append((PlayEventType.THROW, None))
    if record.complete_pass:
        event_specs.append((PlayEventType.CATCH, None))
    if play_type is PlayType.SACK:
        event_specs.append((PlayEventType.SACK, None))
    if record.interception:
        event_specs.append((PlayEventType.INTERCEPTION, None))
    if record.fumble:
        event_specs.append((PlayEventType.FUMBLE, None))
    if play_type in {
        PlayType.PUNT,
        PlayType.FIELD_GOAL,
        PlayType.KICKOFF,
        PlayType.EXTRA_POINT,
    }:
        event_specs.append((PlayEventType.KICK, None))
    event_specs.extend(
        (PlayEventType.PENALTY, penalty.penalty_type) for penalty in record.penalties
    )
    if score_change > 0 or record.touchdown or record.safety:
        event_specs.append((PlayEventType.SCORE, None))

    return tuple(
        PlayEvent(
            play_event_id=play_event_id_for(play_id, sequence),
            play_id=play_id,
            sequence=sequence,
            event_type=event_type,
            detail=detail,
        )
        for sequence, (event_type, detail) in enumerate(event_specs, start=1)
    )


def normalize_nflverse_play(
    record: NflversePlayRecord,
    *,
    context: NflverseGameContext,
    canonical_sequence: int,
    drive_sequence: int | None,
    possession_sequence: int,
    next_record: NflversePlayRecord | None = None,
    next_drive_sequence: int | None = None,
    next_possession_sequence: int | None = None,
) -> NormalizedPlayBundle:
    """Normalize one parsed nflverse row without exposing provider-shaped state downstream."""

    if canonical_sequence < 1 or possession_sequence < 1:
        raise ValueError("canonical play and possession sequences must be positive")
    if drive_sequence is not None and drive_sequence < 1:
        raise ValueError("drive_sequence must be positive when present")
    if next_record is not None and next_record.provider_game_id != record.provider_game_id:
        raise PlayNormalizationError("next_record must belong to the same provider game")

    offense_code, defense_code = _require_possession_codes(record)
    offense_id = context.team_id_for_code(offense_code)
    defense_id = context.team_id_for_code(defense_code)
    play_id = play_id_for(context.game_id, canonical_sequence)
    drive_id = (
        drive_id_for(context.game_id, drive_sequence) if drive_sequence is not None else None
    )
    possession = Possession(
        possession_id=possession_id_for(context.game_id, possession_sequence),
        offense_team_season_id=offense_id,
        defense_team_season_id=defense_id,
    )
    period = Period(number=record.period, is_overtime=record.period > 4)
    pre_state = PrePlayState(
        play_id=play_id,
        drive_id=drive_id,
        possession=possession,
        period=period,
        clock_seconds_remaining=record.quarter_seconds_remaining,
        down=record.down,
        distance=record.distance,
        yards_to_goal=record.yards_to_goal,
        home_score=record.home_score_before,
        away_score=record.away_score_before,
        home_timeouts_remaining=record.home_timeouts_remaining,
        away_timeouts_remaining=record.away_timeouts_remaining,
    )

    play_type = classify_play_type(record)
    execution = PlayExecution(
        primary_play_type=play_type,
        modifiers=_modifiers(record, play_type),
    )
    score_change = _score_change(record, next_record)

    state_after: PlayStateAfter | None = None
    possession_changed = record.interception or record.fumble_lost
    if next_record is not None:
        next_offense_code, next_defense_code = _require_possession_codes(next_record)
        possession_changed = next_offense_code != offense_code
        if next_possession_sequence is None:
            raise PlayNormalizationError(
                "next_possession_sequence is required when next_record is provided"
            )
        next_possession = Possession(
            possession_id=possession_id_for(context.game_id, next_possession_sequence),
            offense_team_season_id=context.team_id_for_code(next_offense_code),
            defense_team_season_id=context.team_id_for_code(next_defense_code),
        )
        next_period = Period(
            number=next_record.period,
            is_overtime=next_record.period > 4,
        )
        state_after = PlayStateAfter(
            play_id=play_id,
            next_possession=next_possession,
            period=next_period,
            clock_seconds_remaining=next_record.quarter_seconds_remaining,
            down=next_record.down,
            distance=next_record.distance,
            yards_to_goal=next_record.yards_to_goal,
            home_score=next_record.home_score_before,
            away_score=next_record.away_score_before,
            drive_continues=(
                drive_sequence is not None
                and next_drive_sequence == drive_sequence
                and not possession_changed
            ),
        )

    official_yards = None if record.no_play else record.official_yards_gained
    result = PlayResult(
        play_id=play_id,
        official_yards_gained=official_yards,
        physical_yards_gained=record.physical_yards_gained,
        first_down=record.first_down and not record.no_play,
        touchdown=record.touchdown and not record.no_play,
        safety=record.safety and not record.no_play,
        completion=(record.complete_pass if play_type is PlayType.PASS else None),
        interception=record.interception and not record.no_play,
        sack=play_type is PlayType.SACK and not record.no_play,
        fumble=record.fumble,
        fumble_lost=record.fumble_lost,
        possession_changed=possession_changed,
        score_change=score_change,
        no_play=record.no_play,
    )
    penalties = tuple(
        Penalty(
            play_id=play_id,
            team_season_id=context.team_id_for_code(penalty.team_code),
            penalty_type=penalty.penalty_type,
            disposition=penalty.disposition,
            yards=penalty.yards,
            automatic_first_down=penalty.automatic_first_down,
            loss_of_down=penalty.loss_of_down,
            nullifies_play=penalty.nullifies_play,
            enforcement_spot=penalty.enforcement_spot,
        )
        for penalty in record.penalties
    )
    events = _build_events(
        record=record,
        play_id=play_id,
        play_type=play_type,
        score_change=score_change,
    )

    return NormalizedPlayBundle(
        game_id=context.game_id,
        canonical_sequence=canonical_sequence,
        drive_sequence=drive_sequence,
        possession_sequence=possession_sequence,
        provider_id="nflverse",
        provider_play_id=record.provider_play_id,
        provider_drive_id=record.provider_drive_id,
        pre_play_state=pre_state,
        execution=execution,
        events=events,
        participation=(),
        penalties=penalties,
        result=result,
        state_after=state_after,
        description=record.description,
    )
