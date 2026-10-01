from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"


class Status(str, Enum):
    PENDING = "pending"
    REVIEW = "review"
    COMPLETED = "completed"
    ERROR = "error"


class CheckRecord(BaseModel):
    model_config = {'protected_namespaces': ()}
    check_key: str = Field(..., description="Identifier for the specific check, e.g., 'identity_match'")
    verdict: Verdict
    confidence: Optional[float] = Field(None, description="Confidence score from 0.0 to 1.0")
    detail: Optional[str] = Field(None, description="Reasoning or detailed observation for the verdict")
    model_version: Optional[str] = Field(None, description="Version of the model that produced the check")
    latency_ms: Optional[int] = Field(None, description="Latency of the model call in milliseconds")


class OverrideRecord(BaseModel):
    original_verdict: Verdict
    revised_verdict: Verdict
    reason: str
    override_at: datetime = Field(default_factory=datetime.utcnow)
    operator_id: str


class EvidenceContract(BaseModel):
    record_id: str
    schema_version: str = "1.0"
    organization_id: str
    client_id: Optional[str] = None
    agent: str = "returns-manager-agent"
    subject: str = Field(..., description="The unit_id being evaluated")
    captured_at: datetime
    operator_label: Optional[str] = None
    images: List[str] = Field(default_factory=list, description="List of image paths/references")
    checks: List[CheckRecord] = Field(default_factory=list)
    outcome: Verdict
    overrides: List[OverrideRecord] = Field(default_factory=list)
    status: Status
    content_hash: Optional[str] = None
