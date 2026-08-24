"""Provider-neutral serialization of the canonical M6 play contract."""

from __future__ import annotations

import hashlib
import json

from daily_nfl.normalization.contracts import NormalizedPlayBundle


def _payload(bundle: NormalizedPlayBundle) -> dict[str, object]:
    pre = bundle.pre_play_state
    result = bundle.result
    physical = result.physical_outcome
    after = bundle.state_after
    return {
        "contract_version": "NFL_CANONICAL_PLAY_V1",
        "game_id": str(bundle.game_id),
        "canonical_sequence": bundle.canonical_sequence,
        "drive_sequence": bundle.drive_sequence,
        "possession_sequence": bundle.possession_sequence,
        "pre_play_state": {
            "play_id": str(pre.play_id),
            "previous_play_id": (
                str(pre.previous_play_id) if pre.previous_play_id is not None else None
            ),
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
            "play_clock_seconds_remaining": pre.play_clock_seconds_remaining,
            "down": pre.down,
            "distance": pre.distance,
            "yards_to_goal": pre.yards_to_goal,
            "home_score": pre.home_score,
            "away_score": pre.away_score,
            "home_timeouts_remaining": pre.home_timeouts_remaining,
            "away_timeouts_remaining": pre.away_timeouts_remaining,
            "kickoff_state": pre.kickoff_state,
            "try_state": pre.try_state,
            "two_minute_state": pre.two_minute_state,
            "overtime_state": pre.overtime_state,
            "offensive_personnel": pre.offensive_personnel,
            "defensive_personnel": pre.defensive_personnel,
            "offensive_formation": pre.offensive_formation,
            "defensive_front": pre.defensive_front,
            "coverage_shell": pre.coverage_shell,
            "motion": pre.motion,
            "shift": pre.shift,
            "shotgun": pre.shotgun,
            "no_huddle": pre.no_huddle,
            "weather_snapshot_id": pre.weather_snapshot_id,
            "surface_state_id": pre.surface_state_id,
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
                "player_id": (
                    str(penalty.player_id) if penalty.player_id is not None else None
                ),
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
            "kick_result": result.kick_result,
            "physical_outcome": (
                None
                if physical is None
                else {
                    "yards_gained": physical.yards_gained,
                    "first_down": physical.first_down,
                    "touchdown": physical.touchdown,
                    "safety": physical.safety,
                    "completion": physical.completion,
                    "interception": physical.interception,
                    "sack": physical.sack,
                    "fumble": physical.fumble,
                    "fumble_lost": physical.fumble_lost,
                    "possession_changed": physical.possession_changed,
                    "score_change": physical.score_change,
                }
            ),
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
    """Serialize only provider-neutral canonical state/results for downstream use."""

    payload_json = json.dumps(_payload(bundle), sort_keys=True, separators=(",", ":"))
    return payload_json, hashlib.sha256(payload_json.encode()).hexdigest()


__all__ = ["serialize_normalized_play"]
