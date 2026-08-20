"""Typed canonical identifiers for Daily NFL.

Provider identifiers are deliberately absent. External IDs belong in the
provider crosswalk/reconciliation layer and must never become canonical IDs.
"""

from typing import NewType

EventId = NewType("EventId", str)
GameId = NewType("GameId", str)
FranchiseId = NewType("FranchiseId", str)
TeamSeasonId = NewType("TeamSeasonId", str)
PersonId = NewType("PersonId", str)
PlayerId = NewType("PlayerId", str)
VenueId = NewType("VenueId", str)
PossessionId = NewType("PossessionId", str)
DriveId = NewType("DriveId", str)
PlayId = NewType("PlayId", str)
PlayEventId = NewType("PlayEventId", str)
