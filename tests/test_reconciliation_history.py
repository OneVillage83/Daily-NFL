from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from daily_nfl.persistence import apply_migrations, open_database
from daily_nfl.providers import NFLVERSE_DESCRIPTOR, record_provider
from daily_nfl.reconciliation import (
    CanonicalEntityType,
    CrosswalkConflictError,
    ExternalIdentity,
    FRANCHISE_ENTITY_TYPE,
    IdentityCandidate,
    IdentityReconciler,
    IdentityRepository,
    MatchMethod,
    ReconciliationStatus,
    new_franchise_id,
)


def _open_identity_database(path: Path):
    connection = open_database(path)
    apply_migrations(connection)
    record_provider(connection, NFLVERSE_DESCRIPTOR)
    return connection


def test_overlapping_crosswalk_to_different_entity_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    first = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    second = new_franchise_id(UUID("22222222-2222-2222-2222-222222222222"))

    with _open_identity_database(database) as connection:
        repository = IdentityRepository(connection)
        reconciler = IdentityReconciler(repository)
        repository.ensure_franchise(first)
        repository.ensure_franchise(second)
        external = ExternalIdentity("nflverse", FRANCHISE_ENTITY_TYPE, "DUP")
        reconciler.bind_verified(
            external=external,
            canonical_entity_type=CanonicalEntityType.FRANCHISE,
            canonical_entity_id=str(first),
        )

        with pytest.raises(CrosswalkConflictError, match="overlapping active"):
            reconciler.bind_verified(
                external=external,
                canonical_entity_type=CanonicalEntityType.FRANCHISE,
                canonical_entity_id=str(second),
            )


def test_superseding_crosswalk_preserves_historical_resolution(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    old_id = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    new_id = new_franchise_id(UUID("22222222-2222-2222-2222-222222222222"))
    old_start = datetime(2020, 1, 1, tzinfo=UTC)
    new_start = datetime(2025, 1, 1, tzinfo=UTC)

    with _open_identity_database(database) as connection:
        repository = IdentityRepository(connection)
        reconciler = IdentityReconciler(repository)
        repository.ensure_franchise(old_id)
        repository.ensure_franchise(new_id)
        external = ExternalIdentity("nflverse", FRANCHISE_ENTITY_TYPE, "CORRECTED")
        reconciler.bind_verified(
            external=external,
            canonical_entity_type=CanonicalEntityType.FRANCHISE,
            canonical_entity_id=str(old_id),
            valid_from=old_start,
        )
        old_binding = repository.active_crosswalks(external)[0]
        reconciler.bind_verified(
            external=external,
            canonical_entity_type=CanonicalEntityType.FRANCHISE,
            canonical_entity_id=str(new_id),
            valid_from=new_start,
            supersedes_crosswalk_id=old_binding.crosswalk_id,
        )

        historical = reconciler.resolve(
            ExternalIdentity(
                "nflverse",
                FRANCHISE_ENTITY_TYPE,
                "CORRECTED",
                datetime(2024, 6, 1, tzinfo=UTC),
            ),
            CanonicalEntityType.FRANCHISE,
        )
        current = reconciler.resolve(
            ExternalIdentity(
                "nflverse",
                FRANCHISE_ENTITY_TYPE,
                "CORRECTED",
                datetime(2026, 6, 1, tzinfo=UTC),
            ),
            CanonicalEntityType.FRANCHISE,
        )

        assert historical.selected_canonical_entity_id == str(old_id)
        assert current.selected_canonical_entity_id == str(new_id)
        assert connection.execute("SELECT COUNT(*) FROM entity_crosswalk").fetchone()[0] == 2


def test_fuzzy_candidates_are_review_only_and_never_selected(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"

    with _open_identity_database(database) as connection:
        repository = IdentityRepository(connection)
        reconciler = IdentityReconciler(repository)
        candidate = IdentityCandidate(
            canonical_entity_type=CanonicalEntityType.PLAYER,
            canonical_entity_id="ply_candidate",
            match_method=MatchMethod.FUZZY_CANDIDATE_ONLY,
            match_confidence=0.91,
            explanation="name similarity only",
        )
        decision = reconciler.record_fuzzy_candidates_for_review(
            external=ExternalIdentity("nflverse", "PLAYER", "provider-player-1"),
            expected_entity_type=CanonicalEntityType.PLAYER,
            candidates=(candidate,),
        )

        assert decision.status is ReconciliationStatus.AMBIGUOUS
        assert decision.selected_canonical_entity_id is None
        assert connection.execute("SELECT COUNT(*) FROM entity_crosswalk").fetchone()[0] == 0


def test_unresolved_identity_is_persisted_as_a_decision(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"

    with _open_identity_database(database) as connection:
        reconciler = IdentityReconciler(IdentityRepository(connection))
        decision = reconciler.resolve(
            ExternalIdentity("nflverse", "PLAYER", "missing-player"),
            CanonicalEntityType.PLAYER,
        )
        row = connection.execute(
            """
            SELECT status, selected_canonical_entity_id
            FROM identity_reconciliation_decisions
            WHERE decision_id = ?
            """,
            (decision.decision_id,),
        ).fetchone()

        assert decision.status is ReconciliationStatus.UNRESOLVED
        assert row is not None
        assert row[0] == "UNRESOLVED"
        assert row[1] is None
