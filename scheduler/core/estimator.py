"""
estimator.py — STORM v2
Multi-source weighted temperature estimation.
"""

import logging

from scheduler.models import City, CitySource, EstimateResult
from scheduler.sources.registry import SOURCE_REGISTRY

logger = logging.getLogger(__name__)


def estimate_max_temp(city: City, sources_config: list[CitySource]) -> EstimateResult | None:
    """
    Run source pipeline per DB config.
    - Sorted by priority
    - Single source → use directly
    - Multiple sources → weighted mean
    """
    enabled = sorted(
        [s for s in sources_config if s.enabled],
        key=lambda s: s.priority,
    )

    if not enabled:
        logger.warning(f"[estimator] no enabled sources for {city.name}")
        return None

    results: list[tuple[float, float, str]] = []

    for cfg in enabled:
        source = SOURCE_REGISTRY.get(cfg.source_type)
        if not source:
            logger.warning(f"[estimator] unknown source_type: {cfg.source_type}")
            continue

        val = source.fetch(city)
        if val is not None:
            results.append((val, cfg.weight, cfg.source_type))
            logger.info(f"[estimator] {cfg.source_type} → {val}°C (weight={cfg.weight})")

    if not results:
        logger.error(f"[estimator] all sources failed for {city.name}")
        return None

    if len(results) == 1:
        temp, _, source_type = results[0]
        return EstimateResult(
            temp=temp,
            sources_used=[source_type],
            is_single_source=True,
        )

    total_weight = sum(w for _, w, _ in results)
    weighted_temp = sum(t * w for t, w, _ in results) / total_weight

    return EstimateResult(
        temp=round(weighted_temp, 2),
        sources_used=[s for _, _, s in results],
        is_single_source=False,
    )
