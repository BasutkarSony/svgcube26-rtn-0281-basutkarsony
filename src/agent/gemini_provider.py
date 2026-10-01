from __future__ import annotations

import json
from typing import Sequence

from src.agent.vision_provider import VisionAnalysis, VisionProvider, VisionProviderError


SYSTEM_PROMPT = """You are a returns-evidence vision analyst.
Analyze all supplied return images in ONE request.
Report observable evidence only. Do not choose condition or disposition.
Do not guess when evidence is insufficient or contradictory.
Every visual claim should cite one or more valid zero-based image indices.
Completeness must distinguish PRESENT, ABSENT, and NOT_VISIBLE.
Report image-quality issues such as blur, darkness, glare, occlusion, or insufficient view.
Return only the requested structured JSON."""


class GeminiVisionProvider(VisionProvider):
    """Gemini implementation kept behind the VisionProvider boundary."""

    def __init__(self, model: str = "gemini-3.6-flash", client=None):
        self.model = model
        self._client = client

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client()
        return self._client

    def analyze(
        self,
        *,
        image_refs: Sequence[str],
        ordered_sku: str,
        ordered_asin: str | None,
        expected_parts: Sequence[str],
    ) -> VisionAnalysis:
        prompt = self._build_prompt(image_refs, ordered_sku, ordered_asin, expected_parts)
        try:
            from google.genai import types
            response = self._get_client().models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=VisionAnalysis,
                ),
            )
            raw = getattr(response, "parsed", None)
            if raw is None:
                raw = json.loads(response.text)
            return VisionAnalysis.model_validate(raw)
        except Exception as exc:
            raise VisionProviderError(f"Gemini analysis failed: {exc}") from exc

    @staticmethod
    def _build_prompt(
        image_refs: Sequence[str],
        ordered_sku: str,
        ordered_asin: str | None,
        expected_parts: Sequence[str],
    ) -> str:
        parts = ", ".join(expected_parts) if expected_parts else "No parts list supplied"
        images = "\n".join(f"Image {i}: {ref}" for i, ref in enumerate(image_refs))
        return (
            f"Ordered SKU: {ordered_sku}\n"
            f"Ordered ASIN: {ordered_asin or 'not supplied'}\n"
            f"Expected parts: {parts}\n"
            f"Images:\n{images}\n\n"
            "Assess identity, completeness, observable physical state, and image quality in this single request. "
            "For each expected part use completeness_state PRESENT, ABSENT, or NOT_VISIBLE."
        )

