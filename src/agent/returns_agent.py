from __future__ import annotations

from datetime import datetime
from collections import defaultdict

from src.agent.vision_provider import VisionAnalysis, VisionProvider, VisionProviderError
from src.models.api import ReturnsAgentRequest
from src.models.evidence import CheckRecord, EvidenceContract, Status, Verdict

CONFIDENCE_THRESHOLD = 0.60


def _verdict(value: str) -> Verdict:
    try:
        return Verdict(value.upper())
    except ValueError:
        return Verdict.UNCERTAIN


class ReturnsAgent:
    def __init__(self, provider: VisionProvider):
        self.provider = provider

    def analyze(self, request: ReturnsAgentRequest) -> EvidenceContract:
        image_refs = [x.strip() for x in request.photo_refs.split(";") if x.strip()]
        expected_parts = [x.strip() for x in request.parts_list.split(";") if x.strip()]
        try:
            analysis = self.provider.analyze(
                image_refs=image_refs,
                ordered_sku=request.ordered_sku,
                ordered_asin=request.ordered_asin,
                expected_parts=expected_parts,
            )
            checks = self._checks(analysis, len(image_refs))
            outcome = self._overall_outcome(checks)
            return EvidenceContract(
                record_id=request.unit_id,
                organization_id=request.org_id,
                subject=request.unit_id,
                captured_at=datetime.utcnow(),
                operator_label=request.operator_id,
                images=image_refs,
                checks=checks,
                outcome=outcome,
                status=Status.REVIEW if outcome == Verdict.UNCERTAIN else Status.PENDING,
            )
        except (VisionProviderError, ValueError, TypeError) as exc:
            return self._fail_open(request, image_refs, str(exc))
        except Exception as exc:
            return self._fail_open(request, image_refs, f"Unexpected analysis failure: {exc}")

    @staticmethod
    def _fail_open(request: ReturnsAgentRequest, image_refs: list[str], detail: str) -> EvidenceContract:
        return EvidenceContract(
            record_id=request.unit_id,
            organization_id=request.org_id,
            subject=request.unit_id,
            captured_at=datetime.utcnow(),
            operator_label=request.operator_id,
            images=image_refs,
            checks=[CheckRecord(check_key="vision_analysis", verdict=Verdict.UNCERTAIN, detail=detail)],
            outcome=Verdict.UNCERTAIN,
            status=Status.REVIEW,
        )

    @staticmethod
    def _checks(analysis: VisionAnalysis, image_count: int) -> list[CheckRecord]:
        observations = [analysis.identity, *analysis.completeness, *analysis.physical_state]
        grouped: dict[str, list] = defaultdict(list)
        for obs in observations:
            grouped[obs.check_key].append(obs)

        checks: list[CheckRecord] = []
        for check_key, items in grouped.items():
            valid_items = []
            for item in items:
                refs = [r for r in item.evidence if 0 <= r.image_index < image_count]
                if refs:
                    valid_items.append((item, refs))

            confidence = max((item.confidence for item, _ in valid_items), default=0.0)
            evidence = [ref for item, _ in valid_items for ref in item.evidence if 0 <= ref.image_index < image_count]
            verdicts = {_verdict(item.verdict) for item, _ in valid_items if item.confidence >= CONFIDENCE_THRESHOLD}
            detail_parts = [item.detail for item in items if item.detail]
            state_parts = [f"completeness_state={item.completeness_state.value}" for item in items if item.completeness_state]
            detail = "; ".join(detail_parts + state_parts)

            if not evidence or confidence < CONFIDENCE_THRESHOLD or len(verdicts) != 1:
                verdict = Verdict.UNCERTAIN
            else:
                verdict = next(iter(verdicts))

            checks.append(CheckRecord(
                check_key=check_key,
                verdict=verdict,
                confidence=confidence,
                detail=detail or None,
            ))

        for quality in analysis.image_quality:
            valid = 0 <= quality.image_index < image_count
            verdict = Verdict.PASS if valid and quality.usable and not quality.issues else Verdict.UNCERTAIN
            checks.append(CheckRecord(
                check_key=f"image_quality_{quality.image_index}",
                verdict=verdict,
                detail=quality.detail or ", ".join(quality.issues) or None,
            ))
        return checks

    @staticmethod
    def _overall_outcome(checks: list[CheckRecord]) -> Verdict:
        if not checks or any(c.verdict == Verdict.UNCERTAIN for c in checks):
            return Verdict.UNCERTAIN
        if any(c.verdict == Verdict.FAIL for c in checks):
            return Verdict.FAIL
        return Verdict.PASS
