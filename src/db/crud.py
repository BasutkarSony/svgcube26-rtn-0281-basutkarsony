from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from src.db.models import CaseModel, ImageMetadataModel, CheckModel, OverrideModel
from src.models.evidence import EvidenceContract, CheckRecord, OverrideRecord, Verdict, Status


def create_case(
    db: Session,
    organization_id: str,
    record_id: str,
    subject: str,
    captured_at: Optional[datetime] = None,
    client_id: Optional[str] = None,
    operator_label: Optional[str] = None,
    schema_version: str = "1.0",
    agent: str = "returns-manager-agent",
    outcome: Optional[str] = None,
    status: str = "pending",
    content_hash: Optional[str] = None,
    images: Optional[List[str]] = None,
    image_hashes: Optional[Dict[str, str]] = None,
) -> CaseModel:
    """
    Creates a new return case bound to organization_id.
    Every operation requires explicit organization_id.
    """
    if not organization_id:
        raise ValueError("organization_id is required for all database operations")

    if captured_at is None:
        captured_at = datetime.utcnow()

    # Create case model
    case = CaseModel(
        organization_id=organization_id,
        record_id=record_id,
        schema_version=schema_version,
        client_id=client_id,
        agent=agent,
        subject=subject,
        captured_at=captured_at,
        operator_label=operator_label,
        outcome=outcome,
        status=status,
        content_hash=content_hash,
    )

    db.add(case)
    db.flush()

    # Add images if provided
    if images:
        for img_path in images:
            sha256 = image_hashes.get(img_path) if image_hashes else None
            img_meta = ImageMetadataModel(
                organization_id=organization_id,
                record_id=record_id,
                image_path=img_path,
                sha256_hash=sha256,
            )
            db.add(img_meta)

    db.commit()
    db.refresh(case)
    return case


def create_case_from_contract(
    db: Session,
    organization_id: str,
    contract: EvidenceContract,
    image_hashes: Optional[Dict[str, str]] = None,
) -> CaseModel:
    """
    Creates a return case from an EvidenceContract schema while ensuring tenant isolation.
    """
    if not organization_id:
        raise ValueError("organization_id is required for all database operations")
    if contract.organization_id != organization_id:
        raise ValueError(
            f"Tenant mismatch: provided org_id '{organization_id}' does not match contract org_id '{contract.organization_id}'"
        )

    case = CaseModel(
        organization_id=organization_id,
        record_id=contract.record_id,
        schema_version=contract.schema_version,
        client_id=contract.client_id,
        agent=contract.agent,
        subject=contract.subject,
        captured_at=contract.captured_at,
        operator_label=contract.operator_label,
        outcome=contract.outcome.value if isinstance(contract.outcome, Verdict) else contract.outcome,
        status=contract.status.value if isinstance(contract.status, Status) else contract.status,
        content_hash=contract.content_hash,
    )

    db.add(case)
    db.flush()

    if contract.images:
        for img_path in contract.images:
            sha256 = image_hashes.get(img_path) if image_hashes else None
            img_meta = ImageMetadataModel(
                organization_id=organization_id,
                record_id=contract.record_id,
                image_path=img_path,
                sha256_hash=sha256,
            )
            db.add(img_meta)

    if contract.checks:
        for check in contract.checks:
            check_model = CheckModel(
                organization_id=organization_id,
                record_id=contract.record_id,
                check_key=check.check_key,
                verdict=check.verdict.value if isinstance(check.verdict, Verdict) else check.verdict,
                confidence=check.confidence,
                detail=check.detail,
                model_version=check.model_version,
                latency_ms=check.latency_ms,
            )
            db.add(check_model)

    if contract.overrides:
        for override in contract.overrides:
            override_model = OverrideModel(
                organization_id=organization_id,
                record_id=contract.record_id,
                original_verdict=override.original_verdict.value if isinstance(override.original_verdict, Verdict) else override.original_verdict,
                revised_verdict=override.revised_verdict.value if isinstance(override.revised_verdict, Verdict) else override.revised_verdict,
                reason=override.reason,
                override_at=override.override_at,
                operator_id=override.operator_id,
            )
            db.add(override_model)

    db.commit()
    db.refresh(case)
    return case


def get_case(db: Session, organization_id: str, record_id: str) -> Optional[CaseModel]:
    """
    Fetches a case strictly filtering by tenant (organization_id) and record_id.
    Never queries by record_id alone. Cross-tenant lookups return None.
    """
    if not organization_id:
        raise ValueError("organization_id is required for all database operations")

    return (
        db.query(CaseModel)
        .filter(
            CaseModel.organization_id == organization_id,
            CaseModel.record_id == record_id,
        )
        .first()
    )


def list_cases(
    db: Session, organization_id: str, skip: int = 0, limit: int = 100
) -> List[CaseModel]:
    """
    Lists all cases belonging exclusively to organization_id.
    """
    if not organization_id:
        raise ValueError("organization_id is required for all database operations")

    return (
        db.query(CaseModel)
        .filter(CaseModel.organization_id == organization_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def add_image_metadata(
    db: Session,
    organization_id: str,
    record_id: str,
    image_path: str,
    sha256_hash: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    mime_type: Optional[str] = None,
) -> Optional[ImageMetadataModel]:
    """
    Adds image metadata to a tenant-scoped case.
    """
    if not organization_id:
        raise ValueError("organization_id is required for all database operations")

    case = get_case(db, organization_id, record_id)
    if not case:
        return None

    img_meta = ImageMetadataModel(
        organization_id=organization_id,
        record_id=record_id,
        image_path=image_path,
        sha256_hash=sha256_hash,
        file_size_bytes=file_size_bytes,
        mime_type=mime_type,
    )
    db.add(img_meta)
    db.commit()
    db.refresh(img_meta)
    return img_meta


def get_images_for_case(
    db: Session, organization_id: str, record_id: str
) -> List[ImageMetadataModel]:
    """
    Returns image metadata strictly scoped to organization_id and record_id.
    """
    if not organization_id:
        raise ValueError("organization_id is required for all database operations")

    return (
        db.query(ImageMetadataModel)
        .filter(
            ImageMetadataModel.organization_id == organization_id,
            ImageMetadataModel.record_id == record_id,
        )
        .all()
    )


def add_check(
    db: Session,
    organization_id: str,
    record_id: str,
    check_key: str,
    verdict: Union[str, Verdict],
    confidence: Optional[float] = None,
    detail: Optional[str] = None,
    model_version: Optional[str] = None,
    latency_ms: Optional[int] = None,
) -> Optional[CheckModel]:
    """
    Adds a check result to a tenant-scoped case.
    """
    if not organization_id:
        raise ValueError("organization_id is required for all database operations")

    case = get_case(db, organization_id, record_id)
    if not case:
        return None

    verdict_str = verdict.value if isinstance(verdict, Verdict) else verdict

    check = CheckModel(
        organization_id=organization_id,
        record_id=record_id,
        check_key=check_key,
        verdict=verdict_str,
        confidence=confidence,
        detail=detail,
        model_version=model_version,
        latency_ms=latency_ms,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


def add_override(
    db: Session,
    organization_id: str,
    record_id: str,
    original_verdict: Union[str, Verdict],
    revised_verdict: Union[str, Verdict],
    reason: str,
    operator_id: str,
    override_at: Optional[datetime] = None,
) -> Optional[OverrideModel]:
    """
    Records an override for a case without overwriting original decision history.
    Updates current case outcome and status to 'review' / 'completed'.
    """
    if not organization_id:
        raise ValueError("organization_id is required for all database operations")

    case = get_case(db, organization_id, record_id)
    if not case:
        return None

    orig_str = original_verdict.value if isinstance(original_verdict, Verdict) else original_verdict
    rev_str = revised_verdict.value if isinstance(revised_verdict, Verdict) else revised_verdict

    override = OverrideModel(
        organization_id=organization_id,
        record_id=record_id,
        original_verdict=orig_str,
        revised_verdict=rev_str,
        reason=reason,
        override_at=override_at or datetime.utcnow(),
        operator_id=operator_id,
    )
    db.add(override)

    # Update current outcome and status
    case.outcome = rev_str
    case.status = "completed"
    case.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(override)
    db.refresh(case)
    return override


def update_case_status(
    db: Session,
    organization_id: str,
    record_id: str,
    status: str,
    outcome: Optional[str] = None,
) -> Optional[CaseModel]:
    """
    Updates status and/or outcome for a tenant-scoped case.
    """
    if not organization_id:
        raise ValueError("organization_id is required for all database operations")

    case = get_case(db, organization_id, record_id)
    if not case:
        return None

    case.status = status
    if outcome is not None:
        case.outcome = outcome
    case.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(case)
    return case
