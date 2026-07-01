"""Compatibility facade for shared pipeline domain values."""

from __future__ import annotations

from pipeline_contracts.domain import (
    IGNORE_BRAND,
    OTHER_BRAND,
    TARGET_BRANDS,
    VALID_OVERRIDE_BRANDS,
    BrandStatus,
    ClassificationInputStatus,
    CropQualityStatus,
    FinalStatus,
    normalize_brand_name,
)

__all__ = [
    "IGNORE_BRAND",
    "OTHER_BRAND",
    "TARGET_BRANDS",
    "VALID_OVERRIDE_BRANDS",
    "BrandStatus",
    "ClassificationInputStatus",
    "CropQualityStatus",
    "FinalStatus",
    "normalize_brand_name",
]
