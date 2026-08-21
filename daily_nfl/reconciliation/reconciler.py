"""Policy layer for provider-to-canonical identity reconciliation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from daily_nfl.domain import FranchiseId, PersonId, PlayerId, TeamSeasonId
from daily_nfl.reconciliation.canonical import (
    new_person_id,
    new_reconciliation_decision_id,
    player_id_for_person,
    team_season_id_for,
)
from daily_nfl.reconciliation.contracts import (
    CanonicalEntityType,
    ExternalIdentity,
    FRANCHISE_ENTITY_TYPE,
    GAME_ENTITY_TYPE,
    GSIS_PLAYER_ENTITY_TYPE,
    GameIdentityHint,
    IdentityCandidate,
    MatchMethod,
    ReconciliationDecision,
    ReconciliationReason,
    ReconciliationStatus,
    TEAM_SEASON_ENTITY_TYPE,
)
from daily_nfl.reconciliation.repository import IdentityRepository

DecisionIdFactory = Callable[[], str]
PersonIdFactory = Callable[[], PersonId]


def _parse_utc(value: object) -> datetime:
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("stored kickoff must be timezone-aware")
    return parsed.astimezone(UTC)


@dataclass(slots=True)
class IdentityReconciler:
    repository: IdentityRepository
    decision_id_factory: DecisionIdFactory = new_reconciliation_decision_id
    person_id_factory: PersonIdFactory = new_person_id

    def resolve(
        self,
        external: ExternalIdentity,
        expected_entity_type: CanonicalEntityType,
    ) -> ReconciliationDecision:
        decision = self._evaluate_existing_crosswalk(external, expected_entity_type)
        self.repository.record_decision(decision)
        return decision

    def bind_verified(
        self,
        *,
        external: ExternalIdentity,
        canonical_entity_type: CanonicalEntityType,
        canonical_entity_id: str,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        supersedes_crosswalk_id: int | None = None,
    ) -> ReconciliationDecision:
        candidate = IdentityCandidate(
            canonical_entity_type=canonical_entity_type,
            canonical_entity_id=canonical_entity_id,
            match_method=MatchMethod.MANUAL_VERIFIED,
            match_confidence=1.0,
            explanation="explicit verified canonical binding",
        )
        decision = ReconciliationDecision(
            decision_id=self.decision_id_factory(),
            external_identity=external,
            expected_entity_type=canonical_entity_type,
            status=ReconciliationStatus.RESOLVED,
            reason=ReconciliationReason.VERIFIED_BINDING_CREATED,
            candidates=(candidate,),
            selected_canonical_entity_id=canonical_entity_id,
            match_method=MatchMethod.MANUAL_VERIFIED,
            match_confidence=1.0,
        )
        self.repository.bind(
            canonical_entity_type=canonical_entity_type,
            canonical_entity_id=canonical_entity_id,
            external=external,
            match_method=MatchMethod.MANUAL_VERIFIED,
            match_confidence=1.0,
            verified=True,
            decision_id=decision.decision_id,
            valid_from=valid_from,
            valid_to=valid_to,
            supersedes_crosswalk_id=supersedes_crosswalk_id,
        )
        self.repository.record_decision(decision)
        return decision

    def resolve_or_create_gsis_player(
        self,
        *,
        provider_id: str,
        gsis_id: str,
        canonical_name: str | None = None,
        valid_at: datetime | None = None,
    ) -> ReconciliationDecision:
        external = ExternalIdentity(
            provider_id=provider_id,
            provider_entity_type=GSIS_PLAYER_ENTITY_TYPE,
            external_id=gsis_id,
            valid_at=valid_at,
        )
        existing = self._evaluate_existing_crosswalk(external, CanonicalEntityType.PLAYER)
        if existing.status is not ReconciliationStatus.UNRESOLVED:
            self.repository.record_decision(existing)
            return existing

        person_id = self.person_id_factory()
        player_id = player_id_for_person(person_id)
        self.repository.ensure_person_player(person_id, player_id, canonical_name)

        candidate = IdentityCandidate(
            canonical_entity_type=CanonicalEntityType.PLAYER,
            canonical_entity_id=str(player_id),
            match_method=MatchMethod.TRUSTED_EXTERNAL_ID,
            match_confidence=1.0,
            explanation="new opaque canonical player bootstrapped from trusted GSIS identity",
        )
        decision = ReconciliationDecision(
            decision_id=self.decision_id_factory(),
            external_identity=external,
            expected_entity_type=CanonicalEntityType.PLAYER,
            status=ReconciliationStatus.RESOLVED,
            reason=ReconciliationReason.TRUSTED_EXTERNAL_ID_CREATED,
            candidates=(candidate,),
            selected_canonical_entity_id=str(player_id),
            match_method=MatchMethod.TRUSTED_EXTERNAL_ID,
            match_confidence=1.0,
        )
        self.repository.bind(
            canonical_entity_type=CanonicalEntityType.PLAYER,
            canonical_entity_id=str(player_id),
            external=external,
            match_method=MatchMethod.TRUSTED_EXTERNAL_ID,
            match_confidence=1.0,
            verified=True,
            decision_id=decision.decision_id,
        )
        self.repository.record_decision(decision)
        return decision

    def resolve_team_season(
        self,
        *,
        provider_id: str,
        external_team_id: str,
        season: int,
        valid_at: datetime | None = None,
        display_name: str | None = None,
    ) -> ReconciliationDecision:
        team_external = ExternalIdentity(
            provider_id=provider_id,
            provider_entity_type=TEAM_SEASON_ENTITY_TYPE,
            external_id=external_team_id,
            valid_at=valid_at,
        )
        existing = self._evaluate_existing_crosswalk(
            team_external,
            CanonicalEntityType.TEAM_SEASON,
        )
        if existing.status is not ReconciliationStatus.UNRESOLVED:
            self.repository.record_decision(existing)
            return existing

        franchise_external = ExternalIdentity(
            provider_id=provider_id,
            provider_entity_type=FRANCHISE_ENTITY_TYPE,
            external_id=external_team_id,
            valid_at=valid_at,
        )
        franchise = self._evaluate_existing_crosswalk(
            franchise_external,
            CanonicalEntityType.FRANCHISE,
        )
        self.repository.record_decision(franchise)
        if not franchise.resolved or franchise.selected_canonical_entity_id is None:
            reason = (
                ReconciliationReason.MULTIPLE_CANONICAL_CANDIDATES
                if franchise.status is ReconciliationStatus.AMBIGUOUS
                else ReconciliationReason.NO_CANONICAL_CANDIDATE
            )
            decision = ReconciliationDecision(
                decision_id=self.decision_id_factory(),
                external_identity=team_external,
                expected_entity_type=CanonicalEntityType.TEAM_SEASON,
                status=(
                    ReconciliationStatus.AMBIGUOUS
                    if franchise.status is ReconciliationStatus.AMBIGUOUS
                    else ReconciliationStatus.UNRESOLVED
                ),
                reason=reason,
            )
            self.repository.record_decision(decision)
            return decision

        franchise_id = FranchiseId(franchise.selected_canonical_entity_id)
        team_season_id = team_season_id_for(franchise_id, season)
        self.repository.ensure_team_season(
            team_season_id,
            franchise_id,
            season,
            display_name,
        )
        confidence = min(franchise.match_confidence or 0.0, 0.99)
        candidate = IdentityCandidate(
            canonical_entity_type=CanonicalEntityType.TEAM_SEASON,
            canonical_entity_id=str(team_season_id),
            match_method=MatchMethod.CANONICAL_COMPOSITE,
            match_confidence=confidence,
            explanation="derived from resolved canonical franchise plus season",
        )
        decision = ReconciliationDecision(
            decision_id=self.decision_id_factory(),
            external_identity=team_external,
            expected_entity_type=CanonicalEntityType.TEAM_SEASON,
            status=ReconciliationStatus.RESOLVED,
            reason=ReconciliationReason.FRANCHISE_SEASON_DERIVATION,
            candidates=(candidate,),
            selected_canonical_entity_id=str(team_season_id),
            match_method=MatchMethod.CANONICAL_COMPOSITE,
            match_confidence=confidence,
        )
        self.repository.bind(
            canonical_entity_type=CanonicalEntityType.TEAM_SEASON,
            canonical_entity_id=str(team_season_id),
            external=team_external,
            match_method=MatchMethod.CANONICAL_COMPOSITE,
            match_confidence=confidence,
            verified=False,
            decision_id=decision.decision_id,
        )
        self.repository.record_decision(decision)
        return decision

    def reconcile_game(
        self,
        *,
        provider_id: str,
        external_game_id: str,
        hint: GameIdentityHint,
        max_kickoff_delta: timedelta = timedelta(days=7),
    ) -> ReconciliationDecision:
        if max_kickoff_delta < timedelta(0):
            raise ValueError("max_kickoff_delta cannot be negative")
        external = ExternalIdentity(
            provider_id=provider_id,
            provider_entity_type=GAME_ENTITY_TYPE,
            external_id=external_game_id,
            valid_at=hint.scheduled_kickoff,
        )
        existing = self._evaluate_existing_crosswalk(external, CanonicalEntityType.GAME)
        if existing.status is not ReconciliationStatus.UNRESOLVED:
            self.repository.record_decision(existing)
            return existing

        rows = self.repository.game_candidates(
            season=hint.season,
            season_phase=hint.season_phase,
            home_team_season_id=hint.home_team_season_id,
            away_team_season_id=hint.away_team_season_id,
            week=hint.week,
        )
        if hint.week is None:
            rows = tuple(
                row
                for row in rows
                if abs(_parse_utc(row["scheduled_kickoff"]) - hint.scheduled_kickoff.astimezone(UTC))
                <= max_kickoff_delta
            )

        confidence = 0.995 if hint.week is not None else 0.98
        candidates = tuple(
            IdentityCandidate(
                canonical_entity_type=CanonicalEntityType.GAME,
                canonical_entity_id=str(row["game_id"]),
                match_method=MatchMethod.CANONICAL_COMPOSITE,
                match_confidence=confidence,
                explanation=(
                    "same canonical teams, season/phase"
                    + ("/week" if hint.week is not None else ", kickoff within tolerance")
                ),
            )
            for row in rows
        )
        if not candidates:
            decision = ReconciliationDecision(
                decision_id=self.decision_id_factory(),
                external_identity=external,
                expected_entity_type=CanonicalEntityType.GAME,
                status=ReconciliationStatus.UNRESOLVED,
                reason=ReconciliationReason.NO_CANONICAL_CANDIDATE,
            )
            self.repository.record_decision(decision)
            return decision
        if len(candidates) > 1:
            decision = ReconciliationDecision(
                decision_id=self.decision_id_factory(),
                external_identity=external,
                expected_entity_type=CanonicalEntityType.GAME,
                status=ReconciliationStatus.AMBIGUOUS,
                reason=ReconciliationReason.MULTIPLE_CANONICAL_CANDIDATES,
                candidates=candidates,
            )
            self.repository.record_decision(decision)
            return decision

        selected = candidates[0]
        decision = ReconciliationDecision(
            decision_id=self.decision_id_factory(),
            external_identity=external,
            expected_entity_type=CanonicalEntityType.GAME,
            status=ReconciliationStatus.RESOLVED,
            reason=ReconciliationReason.SINGLE_CANONICAL_GAME_MATCH,
            candidates=candidates,
            selected_canonical_entity_id=selected.canonical_entity_id,
            match_method=MatchMethod.CANONICAL_COMPOSITE,
            match_confidence=confidence,
        )
        self.repository.bind(
            canonical_entity_type=CanonicalEntityType.GAME,
            canonical_entity_id=selected.canonical_entity_id,
            external=external,
            match_method=MatchMethod.CANONICAL_COMPOSITE,
            match_confidence=confidence,
            verified=False,
            decision_id=decision.decision_id,
        )
        self.repository.record_decision(decision)
        return decision

    def record_fuzzy_candidates_for_review(
        self,
        *,
        external: ExternalIdentity,
        expected_entity_type: CanonicalEntityType,
        candidates: tuple[IdentityCandidate, ...],
    ) -> ReconciliationDecision:
        if any(candidate.match_method is not MatchMethod.FUZZY_CANDIDATE_ONLY for candidate in candidates):
            raise ValueError("review-only fuzzy candidates must use FUZZY_CANDIDATE_ONLY")
        decision = ReconciliationDecision(
            decision_id=self.decision_id_factory(),
            external_identity=external,
            expected_entity_type=expected_entity_type,
            status=(
                ReconciliationStatus.AMBIGUOUS
                if candidates
                else ReconciliationStatus.UNRESOLVED
            ),
            reason=ReconciliationReason.FUZZY_REQUIRES_REVIEW,
            candidates=candidates,
        )
        self.repository.record_decision(decision)
        return decision

    def _evaluate_existing_crosswalk(
        self,
        external: ExternalIdentity,
        expected_entity_type: CanonicalEntityType,
    ) -> ReconciliationDecision:
        bindings = self.repository.active_crosswalks(external)
        if not bindings:
            return ReconciliationDecision(
                decision_id=self.decision_id_factory(),
                external_identity=external,
                expected_entity_type=expected_entity_type,
                status=ReconciliationStatus.UNRESOLVED,
                reason=ReconciliationReason.NO_EXISTING_MAPPING,
            )

        candidates = tuple(
            IdentityCandidate(
                canonical_entity_type=binding.canonical_entity_type,
                canonical_entity_id=binding.canonical_entity_id,
                match_method=MatchMethod.EXISTING_CROSSWALK,
                match_confidence=binding.match_confidence,
                explanation=f"active crosswalk {binding.crosswalk_id}",
            )
            for binding in bindings
        )
        matching = tuple(
            binding
            for binding in bindings
            if binding.canonical_entity_type is expected_entity_type
        )
        if len(matching) == 1 and len(bindings) == 1:
            selected = matching[0]
            return ReconciliationDecision(
                decision_id=self.decision_id_factory(),
                external_identity=external,
                expected_entity_type=expected_entity_type,
                status=ReconciliationStatus.RESOLVED,
                reason=ReconciliationReason.EXISTING_MAPPING,
                candidates=candidates,
                selected_canonical_entity_id=selected.canonical_entity_id,
                match_method=MatchMethod.EXISTING_CROSSWALK,
                match_confidence=selected.match_confidence,
            )
        if not matching:
            return ReconciliationDecision(
                decision_id=self.decision_id_factory(),
                external_identity=external,
                expected_entity_type=expected_entity_type,
                status=ReconciliationStatus.CONFLICT,
                reason=ReconciliationReason.TARGET_ENTITY_TYPE_MISMATCH,
                candidates=candidates,
            )
        return ReconciliationDecision(
            decision_id=self.decision_id_factory(),
            external_identity=external,
            expected_entity_type=expected_entity_type,
            status=ReconciliationStatus.AMBIGUOUS,
            reason=ReconciliationReason.MULTIPLE_ACTIVE_MAPPINGS,
            candidates=candidates,
        )
