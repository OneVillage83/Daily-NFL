from __future__ import annotations

import math

import pytest

from daily_nfl.state import (
    BoundedInterval,
    CategoricalDistribution,
    CategoryProbability,
    MissingnessReason,
    NamedProbability,
    NumericMoments,
    Probability,
    StateUncertainty,
    UnknownQuantity,
)


def test_probability_accepts_closed_unit_interval() -> None:
    assert Probability(0.0).value == 0.0
    assert Probability(1.0).value == 1.0
    assert Probability(0.42).value == 0.42


@pytest.mark.parametrize("value", [-0.01, 1.01, math.inf, -math.inf, math.nan])
def test_probability_rejects_invalid_values(value: float) -> None:
    with pytest.raises(ValueError):
        Probability(value)


def test_numeric_moments_validate_variance_and_expose_stddev() -> None:
    moments = NumericMoments(mean=4.0, variance=9.0)
    assert moments.standard_deviation == 3.0


@pytest.mark.parametrize(
    ("mean", "variance"),
    [
        (math.nan, 1.0),
        (1.0, math.inf),
        (1.0, -0.1),
    ],
)
def test_numeric_moments_reject_invalid_values(mean: float, variance: float) -> None:
    with pytest.raises(ValueError):
        NumericMoments(mean=mean, variance=variance)


def test_bounded_interval_requires_finite_ordered_bounds() -> None:
    interval = BoundedInterval(lower=0.2, upper=0.8, mass=Probability(0.9))
    assert interval.mass == Probability(0.9)

    with pytest.raises(ValueError, match="upper bound"):
        BoundedInterval(lower=2.0, upper=1.0)
    with pytest.raises(ValueError, match="finite"):
        BoundedInterval(lower=0.0, upper=math.inf)


def test_categorical_distribution_requires_unique_normalized_mass() -> None:
    distribution = CategoricalDistribution(
        entries=(
            CategoryProbability("starter", Probability(0.6)),
            CategoryProbability("backup", Probability(0.4)),
        )
    )
    assert math.fsum(entry.probability.value for entry in distribution.entries) == 1.0

    with pytest.raises(ValueError, match="sum to 1"):
        CategoricalDistribution(
            entries=(
                CategoryProbability("starter", Probability(0.7)),
                CategoryProbability("backup", Probability(0.2)),
            )
        )

    with pytest.raises(ValueError, match="unique"):
        CategoricalDistribution(
            entries=(
                CategoryProbability("starter", Probability(0.5)),
                CategoryProbability("starter", Probability(0.5)),
            )
        )


def test_categorical_distribution_cannot_be_empty() -> None:
    with pytest.raises(ValueError, match="at least one"):
        CategoricalDistribution(entries=())


def test_unknown_quantity_preserves_structured_missingness() -> None:
    unknown = UnknownQuantity(
        name="coverage_shell",
        reason=MissingnessReason.UNSUPPORTED_ERA,
        detail="provider charting unavailable",
    )
    assert unknown.reason is MissingnessReason.UNSUPPORTED_ERA

    with pytest.raises(ValueError, match="detail"):
        UnknownQuantity(
            name="coverage_shell",
            reason=MissingnessReason.UNKNOWN,
            detail="   ",
        )


def test_state_uncertainty_rejects_duplicate_names_within_a_family() -> None:
    with pytest.raises(ValueError, match="probability names must be unique"):
        StateUncertainty(
            probabilities=(
                NamedProbability("active", Probability(0.7)),
                NamedProbability("active", Probability(0.3)),
            )
        )


def test_state_uncertainty_empty_flag_is_deterministic() -> None:
    assert StateUncertainty().is_empty is True
    assert (
        StateUncertainty(
            probabilities=(NamedProbability("active", Probability(0.8)),)
        ).is_empty
        is False
    )
