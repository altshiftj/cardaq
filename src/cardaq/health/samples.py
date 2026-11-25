"""Summarize eligible measurements within one trip."""

from collections.abc import Iterable
from math import isfinite
from statistics import median, quantiles

from ..viewer.series import nearby as nearby


def feature(
    key: str, label: str, unit: str, condition: str, values: Iterable[float], *,
    minimum: int = 5, statistic: str = "median", minimum_change: float | None = None,
) -> dict:
    """Summarize finite source samples and retain the count when coverage is too low."""
    observations = [v for v in values if isfinite(v)]
    value = None
    if statistic not in ("median", "iqr"):
        raise ValueError(f"Unsupported trip statistic {statistic!r}.")
    if len(observations) >= minimum:
        if statistic == "median":
            value = median(observations)
        else:
            lower, _, upper = quantiles(observations, n=4, method="inclusive")
            value = upper - lower
    result = dict(key=key, label=label, unit=unit, condition=condition, count=len(observations),
                  value=value, minimum=minimum, statistic=statistic)
    if minimum_change is not None:
        result["minimum_change"] = minimum_change
    return result
