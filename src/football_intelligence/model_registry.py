from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoverageFlags:
    basic: bool = False
    advanced_match: bool = False
    xg: bool = False
    event_spatial: bool = False
    market: bool = False
    social: bool = False


@dataclass(frozen=True)
class ModelSelection:
    model_version: str | None
    status: str
    missing_requirements: tuple[str, ...]


MODEL_REQUIREMENTS = {
    "SIMILARITY_SPATIAL_V1": ("basic", "event_spatial"),
    "SIMILARITY_ADVANCED_V1": ("basic", "advanced_match"),
    "SIMILARITY_BASIC_V1": ("basic",),
}


def select_similarity_model(coverage: CoverageFlags) -> ModelSelection:
    for model, requirements in MODEL_REQUIREMENTS.items():
        missing = tuple(name for name in requirements if not getattr(coverage, name))
        if not missing:
            return ModelSelection(model, "AVAILABLE", ())
    return ModelSelection(None, "INSUFFICIENT_FEATURE_COVERAGE", ("basic",))
