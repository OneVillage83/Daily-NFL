from datetime import UTC, datetime, timedelta

import pytest

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod
from daily_nfl.providers import (
    NFLVERSE_DESCRIPTOR,
    AcquisitionRequest,
    DatasetKind,
    HistoricalAvailability,
    NflverseAdapter,
    NormalizedAcquisition,
    NormalizedRecordProvenance,
    PointInTimeFidelity,
    ProviderCapability,
    ProviderDescriptor,
    ProviderPayload,
    ProviderRegistrationError,
    ProviderRegistry,
    ReliabilityTier,
    UnsupportedDatasetError,
)


def _payload() -> ProviderPayload:
    observed = datetime(2026, 8, 20, 20, 0, tzinfo=UTC)
    return ProviderPayload(
        content=b'{"fixture":true}',
        content_type="application/json",
        source_uri="fixture://schedule",
        observed_at=observed,
        available_at=observed,
        availability_method=AvailabilityMethod.OUR_OBSERVATION_TIME,
        availability_confidence=AvailabilityConfidence.HIGH,
        provider_schema_version="fixture-v1",
    )


def test_provider_payload_requires_timezone_aware_clocks() -> None:
    observed = datetime(2026, 8, 20, 20, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        ProviderPayload(
            content=b"fixture",
            content_type="text/plain",
            source_uri=None,
            observed_at=observed,
            available_at=observed,
            availability_method=AvailabilityMethod.OUR_OBSERVATION_TIME,
            availability_confidence=AvailabilityConfidence.HIGH,
        )


def test_available_at_cannot_be_after_observation() -> None:
    observed = datetime(2026, 8, 20, 20, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="cannot be later"):
        ProviderPayload(
            content=b"fixture",
            content_type="text/plain",
            source_uri=None,
            observed_at=observed,
            available_at=observed + timedelta(seconds=1),
            availability_method=AvailabilityMethod.OUR_OBSERVATION_TIME,
            availability_confidence=AvailabilityConfidence.HIGH,
        )


def test_capability_requires_attribution_text_when_attribution_is_required() -> None:
    with pytest.raises(ValueError, match="attribution_text"):
        ProviderCapability(
            dataset=DatasetKind.SCHEDULE,
            point_in_time_fidelity=PointInTimeFidelity.PARTIAL,
            cadence="DAILY",
            license_class="CC",
            attribution_required=True,
        )


def test_descriptor_rejects_duplicate_dataset_capabilities() -> None:
    capability = ProviderCapability(
        dataset=DatasetKind.SCHEDULE,
        point_in_time_fidelity=PointInTimeFidelity.UNKNOWN,
        cadence="TEST",
        license_class="TEST",
    )

    with pytest.raises(ValueError, match="cannot repeat"):
        ProviderDescriptor(
            provider_id="duplicate",
            name="Duplicate",
            provider_type="TEST",
            parser_version="v1",
            capabilities=(capability, capability),
        )


def test_nflverse_capabilities_are_truthful_machine_readable_and_licensed() -> None:
    assert {item.dataset for item in NFLVERSE_DESCRIPTOR.capabilities} == {
        DatasetKind.SCHEDULE,
        DatasetKind.PLAY_BY_PLAY,
    }

    for capability in NFLVERSE_DESCRIPTOR.capabilities:
        assert capability.entity_coverage
        assert capability.field_coverage
        assert capability.earliest_season == 1999
        assert capability.expected_latency is not None
        assert capability.historical_availability is HistoricalAvailability.ARCHIVAL
        assert capability.reliability_tier is ReliabilityTier.TIER_1
        assert capability.license_id == "CC-BY-4.0"
        assert capability.license_url is not None
        assert capability.attribution_required is True
        assert capability.attribution_text == "nflverse"


def test_registry_is_idempotent_but_rejects_conflicting_provider_id() -> None:
    registry = ProviderRegistry()
    registry.register(NFLVERSE_DESCRIPTOR)
    registry.register(NFLVERSE_DESCRIPTOR)

    assert registry.get("nflverse") == NFLVERSE_DESCRIPTOR
    assert NFLVERSE_DESCRIPTOR in registry.providers_for(DatasetKind.PLAY_BY_PLAY)

    conflicting = ProviderDescriptor(
        provider_id="nflverse",
        name="Different Provider",
        provider_type="TEST",
        parser_version="v9",
    )
    with pytest.raises(ProviderRegistrationError, match="already registered differently"):
        registry.register(conflicting)


def test_nflverse_adapter_rejects_undeclared_dataset_before_loader_call() -> None:
    calls: list[AcquisitionRequest] = []

    def loader(request: AcquisitionRequest) -> tuple[ProviderPayload, ...]:
        calls.append(request)
        return (_payload(),)

    adapter = NflverseAdapter(loader=loader)

    with pytest.raises(UnsupportedDatasetError, match="does not declare support"):
        adapter.acquire(AcquisitionRequest(dataset=DatasetKind.INJURY))

    assert calls == []


def test_nflverse_adapter_uses_injected_loader_for_declared_dataset() -> None:
    request = AcquisitionRequest(dataset=DatasetKind.SCHEDULE, seasons=(2025, 2026))
    payload = _payload()

    adapter = NflverseAdapter(loader=lambda _: (payload,))

    assert adapter.acquire(request) == (payload,)


def test_nflverse_adapter_rejects_empty_raw_batch() -> None:
    adapter = NflverseAdapter(loader=lambda _: ())

    with pytest.raises(ValueError, match="no raw payloads"):
        adapter.acquire(AcquisitionRequest(dataset=DatasetKind.SCHEDULE))


def test_normalized_acquisition_requires_record_level_evidence_lineage() -> None:
    provenance = (
        NormalizedRecordProvenance(
            source_record_id="play-1",
            evidence_id="evidence-2025",
            evidence_observation_id="observation-2025",
        ),
        NormalizedRecordProvenance(
            source_record_id="play-2",
            evidence_id="evidence-2026",
            evidence_observation_id="observation-2026",
        ),
    )
    normalized = NormalizedAcquisition[str](
        provider_id="nflverse",
        dataset=DatasetKind.PLAY_BY_PLAY,
        parser_version="NFLVERSE_ADAPTER_V1",
        provider_schema_version="fixture-v1",
        evidence_ids=("evidence-2025", "evidence-2026"),
        records=("record-1", "record-2"),
        record_provenance=provenance,
    )

    assert normalized.record_provenance == provenance

    with pytest.raises(ValueError, match="every normalized record"):
        NormalizedAcquisition[str](
            provider_id="nflverse",
            dataset=DatasetKind.PLAY_BY_PLAY,
            parser_version="NFLVERSE_ADAPTER_V1",
            provider_schema_version="fixture-v1",
            evidence_ids=("evidence-2025",),
            records=("record-1",),
        )
