"""External identity namespaces that are stronger than any carrier provider."""

from daily_nfl.providers import ProviderDescriptor

GSIS_AUTHORITY_PROVIDER_ID = "nfl-gsis"

GSIS_AUTHORITY_DESCRIPTOR = ProviderDescriptor(
    provider_id=GSIS_AUTHORITY_PROVIDER_ID,
    name="NFL GSIS identity namespace",
    provider_type="IDENTITY_AUTHORITY",
    parser_version="GSIS_IDENTITY_NAMESPACE_V1",
)
