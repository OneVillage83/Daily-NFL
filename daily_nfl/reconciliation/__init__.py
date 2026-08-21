"""Canonical identity generation and provider reconciliation for Daily NFL."""

from daily_nfl.reconciliation.authorities import (
    GSIS_AUTHORITY_DESCRIPTOR,
    GSIS_AUTHORITY_PROVIDER_ID,
)
from daily_nfl.reconciliation.canonical import (
    game_id_for_event,
    new_event_id,
    new_franchise_id,
    new_person_id,
    new_reconciliation_decision_id,
    player_id_for_person,
    team_season_id_for,
)
from daily_nfl.reconciliation.contracts import (
    FRANCHISE_ENTITY_TYPE,
    GAME_ENTITY_TYPE,
    GSIS_PLAYER_ENTITY_TYPE,
    PLAYER_ENTITY_TYPE,
    TEAM_SEASON_ENTITY_TYPE,
    CanonicalEntityType,
    CrosswalkBinding,
    ExternalIdentity,
    GameIdentityHint,
    IdentityCandidate,
    MatchMethod,
    ReconciliationDecision,
    ReconciliationReason,
    ReconciliationStatus,
)
from daily_nfl.reconciliation.reconciler import IdentityReconciler
from daily_nfl.reconciliation.repository import (
    CanonicalIdentityNotFoundError,
    CrosswalkConflictError,
    IdentityRepository,
)

__all__ = [
    "CanonicalEntityType",
    "CanonicalIdentityNotFoundError",
    "CrosswalkBinding",
    "CrosswalkConflictError",
    "ExternalIdentity",
    "FRANCHISE_ENTITY_TYPE",
    "GAME_ENTITY_TYPE",
    "GSIS_AUTHORITY_DESCRIPTOR",
    "GSIS_AUTHORITY_PROVIDER_ID",
    "GSIS_PLAYER_ENTITY_TYPE",
    "GameIdentityHint",
    "IdentityCandidate",
    "IdentityReconciler",
    "IdentityRepository",
    "MatchMethod",
    "PLAYER_ENTITY_TYPE",
    "ReconciliationDecision",
    "ReconciliationReason",
    "ReconciliationStatus",
    "TEAM_SEASON_ENTITY_TYPE",
    "game_id_for_event",
    "new_event_id",
    "new_franchise_id",
    "new_person_id",
    "new_reconciliation_decision_id",
    "player_id_for_person",
    "team_season_id_for",
]
