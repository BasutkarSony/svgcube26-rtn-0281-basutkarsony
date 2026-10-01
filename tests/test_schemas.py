import pytest
from datetime import datetime
from pydantic import ValidationError
from src.models.evidence import EvidenceContract, CheckRecord, Verdict, Status

def test_valid_evidence_contract():
    check = CheckRecord(
        check_key="identity",
        verdict=Verdict.PASS,
        confidence=0.95,
        detail="Matched SKU visually",
        model_version="gemini-3.6",
        latency_ms=1200
    )
    
    evidence = EvidenceContract(
        record_id="RTN-001",
        organization_id="org_alpha",
        subject="UNIT-001",
        captured_at=datetime.utcnow(),
        images=["img1.jpg"],
        checks=[check],
        outcome=Verdict.PASS,
        status=Status.COMPLETED
    )
    
    assert evidence.record_id == "RTN-001"
    assert evidence.schema_version == "1.0"
    assert evidence.outcome == Verdict.PASS
    assert evidence.status == Status.COMPLETED
    assert len(evidence.checks) == 1
    assert evidence.checks[0].verdict == Verdict.PASS

def test_invalid_verdict():
    with pytest.raises(ValidationError):
        CheckRecord(
            check_key="identity",
            verdict="NOT_A_VERDICT" # type: ignore
        )

def test_uncertain_verdict():
    check = CheckRecord(
        check_key="condition",
        verdict=Verdict.UNCERTAIN,
        detail="Image too blurry"
    )
    assert check.verdict == Verdict.UNCERTAIN

def test_missing_required_fields():
    with pytest.raises(ValidationError):
        # Missing captured_at, subject, outcome, status
        EvidenceContract(
            record_id="RTN-002",
            organization_id="org_alpha"
        )
