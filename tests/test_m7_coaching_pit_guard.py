"""Focused PIT regression guards for M7-F Coaching State."""

from datetime import UTC, datetime, timedelta

import pytest

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    CoachingAssignmentObservationId,
    CoachingStintId,
    GameId,
    KnowledgeTimestamp,
    PersonId,
    TeamSeasonId,
)
from daily_nfl.state import (
    CoachingAssignmentObservation,
    CoachingRoleType,
    build_coaching_state_snapshot,
)

TEAM_ID = TeamSeasonId("team-coaching-pit-guard")
GAME_ID = GameId("game-coaching-pit-guard")
COACH_ID = PersonId("coach-pit-guard")
AS_OF = datetime(2026, 9, 13, 16, 0, tzinfo=UTC)


def test_post_cutoff_assignment_fails_closed_in_pure_builder() -> None:
    late_assignment = CoachingAssignmentObservation(
        observation_id=CoachingAssignmentObservationId("coach-assignment-post-cutoff"),
        coaching_stint_id=CoachingStintId("coach-stint-post-cutoff"),
        person_id=COACH_ID,
        team_season_id=TEAM_ID,
        logical_key="head-coach",
        revision=1,
        role_type=CoachingRoleType.HEAD_COACH,
        responsibilities=(),
        assignment_contract="NFL_COACHING_ASSIGNMENT_PIT_GUARD_V1",
        assignment_version="1",
        knowledge=KnowledgeTimestamp(
            available_at=AS_OF + timedelta(minutes=1),
            effective_at=AS_OF - timedelta(days=1),
            published_at=AS_OF + timedelta(minutes=1),
            observed_at=AS_OF + timedelta(minutes=1),
            ingested_at=AS_OF + timedelta(minutes=1),
            availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
            availability_confidence=AvailabilityConfidence.HIGH,
        ),
        effective_from=AS_OF - timedelta(days=1),
    )

    with pytest.raises(
        ValueError,
        match="coaching assignment cannot be available after Coaching State as_of",
    ):
        build_coaching_state_snapshot(
            team_season_id=TEAM_ID,
            game_id=GAME_ID,
            as_of=AS_OF,
            assignment_observations=(late_assignment,),
            scheme_evidence=(),
            created_at=AS_OF + timedelta(seconds=1),
        )
