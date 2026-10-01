from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Sequence

from pydantic import BaseModel, Field


class EvidenceRef(BaseModel):
    image_index: int = Field(ge=0)
    detail: str = ""


class CompletenessState(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    NOT_VISIBLE = "NOT_VISIBLE"


class Observation(BaseModel):
    check_key: str
    verdict: str
    confidence: float = Field(ge=0.0, le=1.0)
    detail: str = ""
    evidence: list[EvidenceRef] = Field(default_factory=list)
    completeness_state: CompletenessState | None = None


class ImageQuality(BaseModel):
    image_index: int = Field(ge=0)
    usable: bool
    issues: list[str] = Field(default_factory=list)
    detail: str = ""


class VisionAnalysis(BaseModel):
    identity: Observation
    completeness: list[Observation] = Field(default_factory=list)
    physical_state: list[Observation] = Field(default_factory=list)
    image_quality: list[ImageQuality] = Field(default_factory=list)


class VisionProviderError(RuntimeError):
    """Raised when the vision provider cannot produce usable analysis."""


class VisionProvider(ABC):
    @abstractmethod
    def analyze(
        self,
        *,
        image_refs: Sequence[str],
        ordered_sku: str,
        ordered_asin: str | None,
        expected_parts: Sequence[str],
    ) -> VisionAnalysis:
        raise NotImplementedError
