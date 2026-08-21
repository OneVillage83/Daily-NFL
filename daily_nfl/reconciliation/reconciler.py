"""Policy layer for provider-to-canonical identity reconciliation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from daily_nfl.domain import FranchiseId, PersonId
from daily_nfl.reconciliation.authorities import GSIS_AUTHORITY_PROVIDER_ID
from daily_nfl.reconciliation.canonical import (
    new_person_id,
    new_reconciliation_decision_id,
    player_id_for_person,
    team_season_id_for,
)
from daily_nfl.reconciliation.contracts import (
    DRIVE_ENTITY_TYPE,
    FRANCHISE_ENTITY_TYPE,
    GAME_ENTITY_TYPE,
    GSIS_PLAYER_ENTITY_TYPE,
    PLAY_ENTITY_TYPE,
    TEAM_SEASON_ENTITY_TYPE,
    CanonicalEntityType,
    DriveIdentityHint,
    ExternalIdentity,
    GameIdentityHint,
    IdentityCandidate,
    MatchMethod,
    PlayIdentityHint,
    ReconciliationDecision,
    ReconciliationEvidence,
    ReconciliationReason,
    ReconciliationStatus,
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


def _season_identity_window(season: int) -> tuple[datetime, datetime]:
    """Return the non-overlapping NFL season identity window.

    Team-season identity follows the league-year boundary rather than the
    calendar year so January/February postseason games remain part of the
    season that began the previous fall.
    """

    if season < 1920:
        raise ValueError("season is outside the supported NFL era")
    start = datetime(season, 3, 1, tzinfo=UTC)
    next_start = datetime(season + 1, 3, 1, tzinfo=UTC)
    return start, next_start - timedelta(microseconds=1)


@dataclass(slots=True)
class IdentityReconciler:
    repository: IdentityRepository
    decision_id_factory: DecisionIdFactory = new_reconciliation_decision_id
    person_id_factory: PersonIdFactory = new_person_id

    def resolve(
        self,
        external: ExternalIdentity,
        expected_entity_type: CanonicalEntityType,
        *,
        evidence: tuple[ReconciliationEvidence, ...] = (),
    ) -> ReconciliationDecision:
        decision = self._evaluate_existing_crosswalk(
            external,
            expected_entity_type,
            evidence=evidence,
        )
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
        evidence: tuple[ReconciliationEvidence, ...] = (),
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
            evidence=evidence,
            selected_canonical_entity_id=canonical_entity_id,
            match_method=MatchMethod.MANUAL_VERIFIED,
            match_confidence=1.0,
        )
        self.repository.record_resolution_binding(
            decision,
            canonical_entity_type=canonical_entity_type,
            canonical_entity_id=canonical_entity_id,
            external=external,
            match_method=MatchMethod.MANUAL_VERIFIED,
            match_confidence=1.0,
            verified=True,
            valid_from=valid_from,
            valid_to=valid_to,
            supersedes_crosswalk_id=supersedes_crosswalk_id,
        )
        return decision

    def resolve_or_create_gsis_player(
        self,
        *,
        gsis_id: str,
        canonical_name: str | None = None,
        valid_at: datetime | None = None,
        evidence: tuple[ReconciliationEvidence, ...] = (),
    ) -> ReconciliationDecision:
        external = ExternalIdentity(
            provider_id=GSIS_AUTHORITY_PROVIDER_ID,
            provider_entity_type=GSIS_PLAYER_ENTITY_TYPE,
            external_id=gsis_id,
            valid_at=valid_at,
        )
        existing = self._evaluate_existing_crosswalk(
            external,
            CanonicalEntityType.PLAYER,
            evidence=evidence,
        )
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
            evidence=evidence,
            selected_canonical_entity_id=str(player_id),
            match_method=MatchMethod.TRUSTED_EXTERNAL_ID,
            match_confidence=1.0,
        )
        self.repository.record_resolution_binding(
            decision,
            canonical_entity_type=CanonicalEntityType.PLAYER,
            canonical_entity_id=str(player_id),
            external=external,
            match_method=MatchMethod.TRUSTED_EXTERNAL_ID,
            match_confidence=1.0,
            verified=True,
        )
        return decision

    def resolve_team_season(
        self,
        *,
        provider_id: str,
        external_team_id: str,
        season: int,
        valid_at: datetime | None = None,
        display_name: str | None = None,
        evidence: tuple[ReconciliationEvidence, ...] = (),
    ) -> ReconciliationDecision:
        valid_from, valid_to = _season_identity_window(season)
        lookup_at = valid_at or valid_from
        if not valid_from <= lookup_at.astimezone(UTC) <= valid_to:
            raise ValueError("valid_at is outside the requested NFL team-season window")

        team_external = ExternalIdentity(
            provider_id=provider_id,
            provider_entity_type=TEAM_SEASON_ENTITY_TYPE,
            external_id=external_team_id,
            valid_at=lookup_at,
        )
        existing = self._evaluate_existing_crosswalk(
            team_external,
            CanonicalEntityType.TEAM_SEASON,
            evidence=evidence,
        )
        if existing.status is not ReconciliationStatus.UNRESOLVED:
            if (
                existing.resolved
                and existing.selected_canonical_entity_id is not None
                and not self.repository.team_season_matches(
                    existing.selected_canonical_entity_id,
                    season,
                )
            ):
                conflict = ReconciliationDecision(
                    decision_id=self.decision_id_factory(),
                    external_identity=team_external,
                    expected_entity_type=CanonicalEntityType.TEAM_SEASON,
                    status=ReconciliationStatus.CONFLICT,
                    reason=ReconciliationReason.EXISTING_MAPPING_CONTEXT_MISMATCH,
                    candidates=existing.candidates,
                    evidence=evidence,
                )
                self.repository.record_decision(conflict)
                return conflict
            self.repository.record_decision(existing)
            return existing

        franchise_external = ExternalIdentity(
            provider_id=provider_id,
            provider_entity_type=FRANCHISE_ENTITY_TYPE,
            external_id=external_team_id,
            valid_at=lookup_at,
        )
        franchise = self._evaluate_existing_crosswalk(
            franchise_external,
            CanonicalEntityType.FRANCHISE,
            evidence=evidence,
        )
        self.repository.record_decision(franchise)
        if not franchise.resolved or franchise.selected_canonical_entity_id is None:
            if franchise.status is ReconciliationStatus.AMBIGUOUS:
                status = ReconciliationStatus.AMBIGUOUS
                reason = ReconciliationReason.MULTIPLE_CANONICAL_CANDIDATES
            elif franchise.status is ReconciliationStatus.CONFLICT:
                status = ReconciliationStatus.CONFLICT
                reason = ReconciliationReason.CROSSWALK_CONFLICT
            else:
                status = ReconciliationStatus.UNRESOLVED
                reason = ReconciliationReason.NO_CANONICAL_CANDIDATE
            decision = ReconciliationDecision(
                decision_id=self.decision_id_factory(),
                external_identity=team_external,
                expected_entity_type=CanonicalEntityType.TEAM_SEASON,
                status=status,
                reason=reason,
                evidence=evidence,
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
            evidence=evidence,
            selected_canonical_entity_id=str(team_season_id),
            match_method=MatchMethod.CANONICAL_COMPOSITE,
            match_confidence=confidence,
        )
        self.repository.record_resolution_binding(
            decision,
            canonical_entity_type=CanonicalEntityType.TEAM_SEASON,
            canonical_entity_id=str(team_season_id),
            external=team_external,
            match_method=MatchMethod.CANONICAL_COMPOSITE,
            match_confidence=confidence,
            verified=False,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        return decision

    def _game_candidate_rows(
        self,
        hint: GameIdentityHint,
        kickoff_delta: timedelta,
    ) -> tuple[object, ...]:
        rows = self.repository.game_candidates(
            season=hint.season,
            season_phase=hint.season_phase,
            home_team_season_id=hint.home_team_season_id,
            away_team_season_id=hint.away_team_season_id,
            week=hint.week,
        )
        if hint.week is None:
            kickoff = hint.scheduled_kickoff.astimezone(UTC)
            rows = tuple(
                row
                for row in rows
                if abs(_parse_utc(row["scheduled_kickoff"]) - kickoff) <= kickoff_delta
            )
        return rows

    def reconcile_game(
        self,
        *,
        provider_id: str,
        external_game_id: str,
        hint: GameIdentityHint,
        max_kickoff_delta: timedelta | None = None,
        evidence: tuple[ReconciliationEvidence, ...] = (),
    ) -> ReconciliationDecision:
        kickoff_delta = timedelta(days=7) if max_kickoff_delta is None else max_kickoff_delta
        if kickoff_delta < timedelta(0):
            raise ValueError("max_kickoff_delta cannot be negative")
        external = ExternalIdentity(
            provider_id=provider_id,
            provider_entity_type=GAME_ENTITY_TYPE,
            external_id=external_game_id,
            valid_at=hint.scheduled_kickoff,
        )
        rows = self._game_candidate_rows(hint, kickoff_delta)
        candidate_ids = {str(row["game_id"]) for row in rows}
        existing = self._evaluate_existing_crosswalk(
            external,
            CanonicalEntityType.GAME,
            evidence=evidence,
        )
        if existing.status is not ReconciliationStatus.UNRESOLVED:
            if (
                existing.resolved
                and existing.selected_canonical_entity_id is not None
                and existing.selected_canonical_entity_id not in candidate_ids
            ):
                conflict = ReconciliationDecision(
                    decision_id=self.decision_id_factory(),
                    external_identity=external,
                    expected_entity_type=CanonicalEntityType.GAME,
                    status=ReconciliationStatus.CONFLICT,
                    reason=ReconciliationReason.EXISTING_MAPPING_CONTEXT_MISMATCH,
                    candidates=existing.candidates,
                    evidence=evidence,
                )
                self.repository.record_decision(conflict)
                return conflict
            self.repository.record_decision(existing)
            return existing

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
                evidence=evidence,
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
                evidence=evidence,
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
            evidence=evidence,
            selected_canonical_entity_id=selected.canonical_entity_id,
            match_method=MatchMethod.CANONICAL_COMPOSITE,
            match_confidence=confidence,
        )
        self.repository.record_resolution_binding(
            decision,
            canonical_entity_type=CanonicalEntityType.GAME,
            canonical_entity_id=selected.canonical_entity_id,
            external=external,
            match_method=MatchMethod.CANONICAL_COMPOSITE,
            match_confidence=confidence,
            verified=False,
        )
        return decision

    def reconcile_drive(
        self,
        *,
        provider_id: str,
        external_drive_id: str,
        hint: DriveIdentityHint,
        evidence: tuple[ReconciliationEvidence, ...] = (),
    ) -> ReconciliationDecision:
        external = ExternalIdentity(provider_id, DRIVE_ENTITY_TYPE, external_drive_id)
        existing = self._evaluate_existing_crosswalk(
            external,
            CanonicalEntityType.DRIVE,
            evidence=evidence,
        )
        segment_id = (
            str(hint.possession_segment_id)
            if hint.possession_segment_id is not None
            else None
        )
        if existing.status is not ReconciliationStatus.UNRESOLVED:
            if (
                existing.resolved
                and existing.selected_canonical_entity_id is not None
                and not self.repository.drive_matches_hint(
                    existing.selected_canonical_entity_id,
                    game_id=str(hint.game_id),
                    canonical_sequence=hint.canonical_sequence,
                    possession_segment_id=segment_id,
                )
            ):
                conflict = ReconciliationDecision(
                    decision_id=self.decision_id_factory(),
                    external_identity=external,
                    expected_entity_type=CanonicalEntityType.DRIVE,
                    status=ReconciliationStatus.CONFLICT,
                    reason=ReconciliationReason.EXISTING_MAPPING_CONTEXT_MISMATCH,
                    candidates=existing.candidates,
                    evidence=evidence,
                )
                self.repository.record_decision(conflict)
                return conflict
            self.repository.record_decision(existing)
            return existing

        rows = self.repository.drive_candidates(
            game_id=str(hint.game_id),
            canonical_sequence=hint.canonical_sequence,
            possession_segment_id=segment_id,
        )
        candidates = tuple(
            IdentityCandidate(
                canonical_entity_type=CanonicalEntityType.DRIVE,
                canonical_entity_id=str(row["drive_id"]),
                match_method=MatchMethod.CANONICAL_COMPOSITE,
                match_confidence=0.995,
                explanation="same canonical game and drive sequence/context",
            )
            for row in rows
        )
        return self._resolve_sequence_candidates(
            external=external,
            expected_entity_type=CanonicalEntityType.DRIVE,
            candidates=candidates,
            resolved_reason=ReconciliationReason.SINGLE_CANONICAL_DRIVE_MATCH,
            evidence=evidence,
        )

    def reconcile_play(
        self,
        *,
        provider_id: str,
        external_play_id: str,
        hint: PlayIdentityHint,
        evidence: tuple[ReconciliationEvidence, ...] = (),
    ) -> ReconciliationDecision:
        external = ExternalIdentity(provider_id, PLAY_ENTITY_TYPE, external_play_id)
        existing = self._evaluate_existing_crosswalk(
            external,
            CanonicalEntityType.PLAY,
            evidence=evidence,
        )
        drive_id = str(hint.drive_id) if hint.drive_id is not None else None
        if existing.status is not ReconciliationStatus.UNRESOLVED:
            if (
                existing.resolved
                and existing.selected_canonical_entity_id is not None
                and not self.repository.play_matches_hint(
                    existing.selected_canonical_entity_id,
                    game_id=str(hint.game_id),
                    canonical_sequence=hint.canonical_sequence,
                    drive_id=drive_id,
                )
            ):
                conflict = ReconciliationDecision(
                    decision_id=self.decision_id_factory(),
                    external_identity=external,
                    expected_entity_type=CanonicalEntityType.PLAY,
                    status=ReconciliationStatus.CONFLICT,
                    reason=ReconciliationReason.EXISTING_MAPPING_CONTEXT_MISMATCH,
                    candidates=existing.candidates,
                    evidence=evidence,
                )
                self.repository.record_decision(conflict)
                return conflict
            self.repository.record_decision(existing)
            return existing

        rows = self.repository.play_candidates(
            game_id=str(hint.game_id),
            canonical_sequence=hint.canonical_sequence,
            drive_id=drive_id,
        )
        candidates = tuple(
            IdentityCandidate(
                canonical_entity_type=CanonicalEntityType.PLAY,
                canonical_entity_id=str(row["play_id"]),
                match_method=MatchMethod.CANONICAL_COMPOSITE,
                match_confidence=0.995,
                explanation="same canonical game and play sequence/context",
            )
            for row in rows
        )
        return self._resolve_sequence_candidates(
            external=external,
            expected_entity_type=CanonicalEntityType.PLAY,
            candidates=candidates,
            resolved_reason=ReconciliationReason.SINGLE_CANONICAL_PLAY_MATCH,
            evidence=evidence,
        )

    def _resolve_sequence_candidates(
        self,
        *,
        external: ExternalIdentity,
        expected_entity_type: CanonicalEntityType,
        candidates: tuple[IdentityCandidate, ...],
        resolved_reason: ReconciliationReason,
        evidence: tuple[ReconciliationEvidence, ...],
    ) -> ReconciliationDecision:
        if not candidates:
            decision = ReconciliationDecision(
                decision_id=self.decision_id_factory(),
                external_identity=external,
                expected_entity_type=expected_entity_type,
                status=ReconciliationStatus.UNRESOLVED,
                reason=ReconciliationReason.NO_CANONICAL_CANDIDATE,
                evidence=evidence,
            )
            self.repository.record_decision(decision)
            return decision
        if len(candidates) > 1:
            decision = ReconciliationDecision(
                decision_id=self.decision_id_factory(),
                external_identity=external,
                expected_entity_type=expected_entity_type,
                status=ReconciliationStatus.AMBIGUOUS,
                reason=ReconciliationReason.MULTIPLE_CANONICAL_CANDIDATES,
                candidates=candidates,
                evidence=evidence,
            )
            self.repository.record_decision(decision)
            return decision

        selected = candidates[0]
        decision = ReconciliationDecision(
            decision_id=self.decision_id_factory(),
            external_identity=external,
            expected_entity_type=expected_entity_type,
            status=ReconciliationStatus.RESOLVED,
            reason=resolved_reason,
            candidates=candidates,
            evidence=evidence,
            selected_canonical_entity_id=selected.canonical_entity_id,
            match_method=MatchMethod.CANONICAL_COMPOSITE,
            match_confidence=selected.match_confidence,
        )
        self.repository.record_resolution_binding(
            decision,
            canonical_entity_type=expected_entity_type,
            canonical_entity_id=selected.canonical_entity_id,
            external=external,
            match_method=MatchMethod.CANONICAL_COMPOSITE,
            match_confidence=selected.match_confidence,
            verified=False,
        )
        return decision

    def record_fuzzy_candidates_for_review(
        self,
        *,
        external: ExternalIdentity,
        expected_entity_type: CanonicalEntityType,
        candidates: tuple[IdentityCandidate, ...],
        evidence: tuple[ReconciliationEvidence, ...] = (),
    ) -> ReconciliationDecision:
        invalid = any(
            candidate.match_method is not MatchMethod.FUZZY_CANDIDATE_ONLY
            for candidate in candidates
        )
        if invalid:
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
            evidence=evidence,
        )
        self.repository.record_decision(decision)
        return decision

    def _evaluate_existing_crosswalk(
        self,
        external: ExternalIdentity,
        expected_entity_type: CanonicalEntityType,
        *,
        evidence: tuple[ReconciliationEvidence, ...] = (),
    ) -> ReconciliationDecision:
        bindings = self.repository.active_crosswalks(external)
        if not bindings:
            return ReconciliationDecision(
                decision_id=self.decision_id_factory(),
                external_identity=external,
                expected_entity_type=expected_entity_type,
                status=ReconciliationStatus.UNRESOLVED,
                reason=ReconciliationReason.NO_EXISTING_MAPPING,
                evidence=evidence,
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
                evidence=evidence,
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
                evidence=evidence,
            )
        return ReconciliationDecision(
            decision_id=self.decision_id_factory(),
            external_identity=external,
            expected_entity_type=expected_entity_type,
            status=ReconciliationStatus.AMBIGUOUS,
            reason=ReconciliationReason.MULTIPLE_ACTIVE_MAPPINGS,
            candidates=candidates,
            evidence=evidence,
        )
