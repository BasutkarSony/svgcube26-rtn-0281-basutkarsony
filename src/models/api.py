from pydantic import BaseModel, Field
from typing import List, Optional
from src.models.evidence import EvidenceContract

class ReturnsAgentRequest(BaseModel):
    unit_id: str
    org_id: str
    operator_id: str
    order_id: str
    ordered_sku: str
    ordered_asin: Optional[str] = None
    parts_list: str = Field(..., description="Semicolon-separated list of expected parts")
    photo_refs: str = Field(..., description="Semicolon-separated list of photo references")

class ReturnsAgentResponse(BaseModel):
    success: bool
    evidence: Optional[EvidenceContract] = None
    error_message: Optional[str] = None
