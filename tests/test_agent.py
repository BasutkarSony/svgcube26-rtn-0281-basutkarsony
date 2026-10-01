from src.agent.returns_agent import ReturnsAgent
from src.agent.vision_provider import (
    CompletenessState,
    EvidenceRef,
    ImageQuality,
    Observation,
    VisionAnalysis,
    VisionProvider,
    VisionProviderError,
)
from src.models.api import ReturnsAgentRequest
from src.models.evidence import Verdict, Status


class FakeProvider(VisionProvider):
    def __init__(self, analysis=None, error=None):
        self.analysis = analysis
        self.error = error
        self.calls = 0

    def analyze(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self.analysis


def request():
    return ReturnsAgentRequest(
        unit_id="unit-1",
        org_id="org_demo_alpha",
        operator_id="op-1",
        order_id="order-1",
        ordered_sku="SKU-123",
        ordered_asin="ASIN-123",
        parts_list="charger;manual",
        photo_refs="img0.jpg;img1.jpg",
    )


def observation(key="identity_match", verdict="PASS", confidence=0.95, refs=(0,), detail="matches"):
    return Observation(
        check_key=key,
        verdict=verdict,
        confidence=confidence,
        detail=detail,
        evidence=[EvidenceRef(image_index=i, detail="support") for i in refs],
    )


def analysis_with(identity=None, completeness=None, physical=None, quality=None):
    return VisionAnalysis(
        identity=identity or observation(),
        completeness=completeness or [],
        physical_state=physical or [],
        image_quality=quality or [],
    )


def test_provider_abstraction_is_used_once():
    provider = FakeProvider(analysis_with())
    result = ReturnsAgent(provider).analyze(request())
    assert provider.calls == 1
    assert result.organization_id == "org_demo_alpha"


def test_structured_success_and_identity_pass():
    provider = FakeProvider(analysis_with(identity=observation()))
    result = ReturnsAgent(provider).analyze(request())
    check = next(c for c in result.checks if c.check_key == "identity_match")
    assert check.verdict == Verdict.PASS


def test_identity_fail_and_uncertain():
    fail = FakeProvider(analysis_with(identity=observation(verdict="FAIL")))
    assert next(c for c in ReturnsAgent(fail).analyze(request()).checks if c.check_key == "identity_match").verdict == Verdict.FAIL

    uncertain = FakeProvider(analysis_with(identity=observation(verdict="PASS", confidence=0.2)))
    assert next(c for c in ReturnsAgent(uncertain).analyze(request()).checks if c.check_key == "identity_match").verdict == Verdict.UNCERTAIN


def test_completeness_present_absent_not_visible_are_preserved():
    observations = [
        Observation(check_key="part_charger", verdict="PASS", confidence=0.95, completeness_state=CompletenessState.PRESENT, evidence=[EvidenceRef(image_index=0)]),
        Observation(check_key="part_manual", verdict="FAIL", confidence=0.95, completeness_state=CompletenessState.ABSENT, evidence=[EvidenceRef(image_index=1)]),
        Observation(check_key="part_cable", verdict="UNCERTAIN", confidence=0.95, completeness_state=CompletenessState.NOT_VISIBLE, evidence=[EvidenceRef(image_index=1)]),
    ]
    result = ReturnsAgent(FakeProvider(analysis_with(completeness=observations))).analyze(request())
    details = {c.check_key: c.detail for c in result.checks}
    assert "PRESENT" in details["part_charger"]
    assert "ABSENT" in details["part_manual"]
    assert "NOT_VISIBLE" in details["part_cable"]
    assert next(c for c in result.checks if c.check_key == "part_cable").verdict == Verdict.UNCERTAIN


def test_invalid_evidence_reference_becomes_uncertain():
    bad = observation(refs=(99,))
    result = ReturnsAgent(FakeProvider(analysis_with(identity=bad))).analyze(request())
    check = next(c for c in result.checks if c.check_key == "identity_match")
    assert check.verdict == Verdict.UNCERTAIN


def test_contradictory_evidence_becomes_uncertain():
    a = observation(verdict="PASS", refs=(0,))
    b = observation(key="physical_damage", verdict="FAIL", refs=(1,))
    result = ReturnsAgent(FakeProvider(analysis_with(identity=a, physical=[b]))).analyze(request())
    # Different check keys are intentionally not considered contradictory.
    assert next(c for c in result.checks if c.check_key == "identity_match").verdict == Verdict.PASS

    contradictory = VisionAnalysis(identity=a, physical_state=[Observation(check_key="identity_match", verdict="FAIL", confidence=0.95, evidence=[EvidenceRef(image_index=1)])])
    result = ReturnsAgent(FakeProvider(contradictory)).analyze(request())
    assert next(c for c in result.checks if c.check_key == "identity_match").verdict == Verdict.UNCERTAIN


def test_poor_image_quality_becomes_uncertain():
    quality = [ImageQuality(image_index=0, usable=False, issues=["blur", "darkness"], detail="image unusable")]
    result = ReturnsAgent(FakeProvider(analysis_with(quality=quality))).analyze(request())
    check = next(c for c in result.checks if c.check_key == "image_quality_0")
    assert check.verdict == Verdict.UNCERTAIN


def test_provider_error_fails_open():
    result = ReturnsAgent(FakeProvider(error=VisionProviderError("timeout"))).analyze(request())
    assert result.outcome == Verdict.UNCERTAIN
    assert result.status == Status.REVIEW
    assert result.images == ["img0.jpg", "img1.jpg"]


def test_malformed_provider_output_fails_open():
    class MalformedProvider(VisionProvider):
        def analyze(self, **kwargs):
            raise ValueError("malformed structured response")

    result = ReturnsAgent(MalformedProvider()).analyze(request())
    assert result.outcome == Verdict.UNCERTAIN
    assert result.status == Status.REVIEW
