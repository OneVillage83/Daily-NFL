import json

from daily_nfl.domain import GameId, TeamSeasonId
from daily_nfl.normalization import (
    NflverseGameContext,
    NflversePlayRecord,
    normalize_nflverse_play,
    serialize_normalized_play,
)


def test_serialized_canonical_play_excludes_provider_row_identity() -> None:
    context = NflverseGameContext(
        game_id=GameId("nflg_m6_serialization"),
        home_team_code="HOM",
        away_team_code="AWY",
        home_team_season_id=TeamSeasonId("tms_home"),
        away_team_season_id=TeamSeasonId("tms_away"),
    )
    bundle = normalize_nflverse_play(
        NflversePlayRecord(
            provider_game_id="2025_02_AWY_HOM",
            provider_play_id="100",
            provider_drive_id="1",
            offense_team_code="HOM",
            defense_team_code="AWY",
            period=1,
            quarter_seconds_remaining=840,
            down=1,
            distance=10,
            yards_to_goal=75,
            home_score_before=0,
            away_score_before=0,
            source_row_index=10,
            pass_attempt=True,
            shotgun=True,
            official_yards_gained=8,
            description="provider free text",
        ),
        context=context,
        canonical_sequence=2,
        drive_sequence=1,
        possession_sequence=1,
    )

    payload_json, _ = serialize_normalized_play(bundle)
    payload = json.loads(payload_json)

    assert payload["contract_version"] == "NFL_CANONICAL_PLAY_V1"
    assert payload["pre_play_state"]["shotgun"] is True
    assert payload["pre_play_state"]["previous_play_id"] is not None
    assert payload["execution"]["primary_play_type"] == "PASS"
    assert "provider_id" not in payload
    assert "provider_play_id" not in payload
    assert "provider_drive_id" not in payload
    assert "description" not in payload
    assert "pass_attempt" not in payload
