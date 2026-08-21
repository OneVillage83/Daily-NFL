"""Provider capability registry for Daily NFL."""

from __future__ import annotations

from dataclasses import dataclass

from daily_nfl.providers.contracts import DatasetKind, ProviderDescriptor


class ProviderRegistrationError(ValueError):
    """Raised when a provider cannot be registered safely."""


@dataclass(slots=True)
class ProviderRegistry:
    """In-memory registry used to resolve providers by declared capability."""

    _providers: dict[str, ProviderDescriptor]

    def __init__(self) -> None:
        self._providers = {}

    def register(self, descriptor: ProviderDescriptor) -> None:
        existing = self._providers.get(descriptor.provider_id)
        if existing is not None and existing != descriptor:
            raise ProviderRegistrationError(
                f"provider_id {descriptor.provider_id!r} is already registered differently"
            )
        self._providers[descriptor.provider_id] = descriptor

    def get(self, provider_id: str) -> ProviderDescriptor:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise KeyError(f"unknown provider_id: {provider_id}") from exc

    def providers_for(self, dataset: DatasetKind) -> tuple[ProviderDescriptor, ...]:
        providers = [
            descriptor
            for descriptor in self._providers.values()
            if descriptor.capability_for(dataset) is not None
        ]
        return tuple(sorted(providers, key=lambda descriptor: descriptor.provider_id))

    def all(self) -> tuple[ProviderDescriptor, ...]:
        return tuple(
            sorted(self._providers.values(), key=lambda descriptor: descriptor.provider_id)
        )
