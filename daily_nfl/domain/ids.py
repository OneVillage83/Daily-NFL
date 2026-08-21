"""Typed canonical identifiers for Daily NFL.

Provider identifiers are deliberately absent. External IDs belong in the
provider crosswalk/reconciliation layer and must never become canonical IDs.

Generic cross-sport identifiers such as CompetitionId/EventId/VenueId are
opaque references to concepts ultimately owned by Daily-Data-Core. Daily-NFL
never derives those identities from provider IDs.
"""

from typing import NewType

CompetitionId = NewType("CompetitionId", str)
EventId = NewType("EventId", str)
GameId = NewType("GameId", str)
FranchiseId = NewType("FranchiseId", str)
TeamSeasonId = NewType("TeamSeasonId", str)
PersonId = NewType("PersonId", str)
PlayerId = NewType("PlayerId", str)
RosterStintId = NewType("RosterStintId", str)
CoachRoleId = NewType("CoachRoleId", str)
VenueId = NewType("VenueId", str)
PossessionId = NewType("PossessionId", str)
PossessionSegmentId = NewType("PossessionSegmentId", str)
DriveId = NewType("DriveId", str)
PlayId = NewType("PlayId", str)
PlayEventId = NewType("PlayEventId", str)
ParticipationId = NewType("ParticipationId", str)
PenaltyId = NewType("PenaltyId", str)
InjuryObservationId = NewType("InjuryObservationId", str)
DepthChartSnapshotId = NewType("DepthChartSnapshotId", str)
