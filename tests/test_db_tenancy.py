import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.database import Base
from src.db import crud
from src.db.models import CaseModel, ImageMetadataModel, CheckModel, OverrideModel
from src.models.evidence import Verdict, Status


@pytest.fixture
def db_session():
    """Provides an isolated in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_1_alpha_create_and_read_own_record(db_session):
    """1. Alpha can create/read its own record."""
    case = crud.create_case(
        db=db_session,
        organization_id="org_alpha",
        record_id="REC-ALPHA-001",
        subject="UNIT-100",
        captured_at=datetime.utcnow(),
        status="pending",
    )
    assert case is not None
    assert case.record_id == "REC-ALPHA-001"
    assert case.organization_id == "org_alpha"

    read_case = crud.get_case(db_session, organization_id="org_alpha", record_id="REC-ALPHA-001")
    assert read_case is not None
    assert read_case.subject == "UNIT-100"


def test_2_bravo_cannot_read_alpha_record(db_session):
    """2. Bravo cannot read Alpha's record even with a guessed record_id."""
    crud.create_case(
        db=db_session,
        organization_id="org_alpha",
        record_id="REC-SECRET-123",
        subject="UNIT-SECRET",
        captured_at=datetime.utcnow(),
    )

    bravo_result = crud.get_case(db_session, organization_id="org_bravo", record_id="REC-SECRET-123")
    assert bravo_result is None


def test_3_alpha_cannot_read_bravo_record(db_session):
    """3. Alpha cannot access Bravo's record."""
    crud.create_case(
        db=db_session,
        organization_id="org_bravo",
        record_id="REC-BRAVO-999",
        subject="UNIT-BRAVO",
        captured_at=datetime.utcnow(),
    )

    alpha_direct = crud.get_case(db_session, organization_id="org_alpha", record_id="REC-BRAVO-999")
    assert alpha_direct is None

    alpha_list = crud.list_cases(db_session, organization_id="org_alpha")
    assert len(alpha_list) == 0 or not any(c.record_id == "REC-BRAVO-999" for c in alpha_list)


def test_4_record_id_collision_prevention(db_session):
    """4. Both tenants can have the same record_id without collision."""
    case_alpha = crud.create_case(
        db=db_session,
        organization_id="org_alpha",
        record_id="SHARED-ID-1",
        subject="Alpha Product",
        captured_at=datetime.utcnow(),
    )

    case_bravo = crud.create_case(
        db=db_session,
        organization_id="org_bravo",
        record_id="SHARED-ID-1",
        subject="Bravo Product",
        captured_at=datetime.utcnow(),
    )

    assert case_alpha is not None
    assert case_bravo is not None

    fetched_alpha = crud.get_case(db_session, "org_alpha", "SHARED-ID-1")
    fetched_bravo = crud.get_case(db_session, "org_bravo", "SHARED-ID-1")

    assert fetched_alpha.subject == "Alpha Product"
    assert fetched_bravo.subject == "Bravo Product"


def test_5_every_crud_requires_organization_id(db_session):
    """5. Every CRUD read/write requires organization_id."""
    with pytest.raises(ValueError):
        crud.create_case(db_session, organization_id="", record_id="REC-1", subject="U-1")

    with pytest.raises(ValueError):
        crud.get_case(db_session, organization_id="", record_id="REC-1")

    with pytest.raises(ValueError):
        crud.list_cases(db_session, organization_id="")

    with pytest.raises(ValueError):
        crud.add_image_metadata(db_session, organization_id="", record_id="REC-1", image_path="p.jpg")

    with pytest.raises(ValueError):
        crud.get_images_for_case(db_session, organization_id="", record_id="REC-1")

    with pytest.raises(ValueError):
        crud.add_check(db_session, organization_id="", record_id="REC-1", check_key="k", verdict="PASS")

    with pytest.raises(ValueError):
        crud.add_override(
            db_session,
            organization_id="",
            record_id="REC-1",
            original_verdict="PASS",
            revised_verdict="FAIL",
            reason="r",
            operator_id="op1",
        )

    with pytest.raises(ValueError):
        crud.update_case_status(db_session, organization_id="", record_id="REC-1", status="review")


def test_6_image_metadata_remains_tenant_scoped(db_session):
    """6. Image metadata remains tenant-scoped."""
    crud.create_case(
        db=db_session,
        organization_id="org_alpha",
        record_id="REC-IMG-001",
        subject="UNIT-IMG",
        images=["/path/to/img1.jpg"],
        image_hashes={"/path/to/img1.jpg": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
    )

    alpha_images = crud.get_images_for_case(db_session, organization_id="org_alpha", record_id="REC-IMG-001")
    assert len(alpha_images) == 1
    assert alpha_images[0].sha256_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    bravo_images = crud.get_images_for_case(db_session, organization_id="org_bravo", record_id="REC-IMG-001")
    assert len(bravo_images) == 0


def test_7_pending_case_persisted_before_inference(db_session):
    """7. A persisted pending case can exist before inference (fail-open design)."""
    # Create return case before running any model inference
    case = crud.create_case(
        db=db_session,
        organization_id="org_alpha",
        record_id="REC-PENDING-001",
        subject="UNIT-RETRY-456",
        captured_at=datetime.utcnow(),
        status="pending",
        outcome=None,
    )

    # Add image metadata and hashes for later retry/inference
    crud.add_image_metadata(
        db=db_session,
        organization_id="org_alpha",
        record_id="REC-PENDING-001",
        image_path="/data/returns/unit_456_front.jpg",
        sha256_hash="5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5",
    )

    retrieved = crud.get_case(db_session, "org_alpha", "REC-PENDING-001")
    assert retrieved is not None
    assert retrieved.status == "pending"
    assert retrieved.outcome is None
    assert len(retrieved.checks) == 0

    images = crud.get_images_for_case(db_session, "org_alpha", "REC-PENDING-001")
    assert len(images) == 1
    assert images[0].sha256_hash == "5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5"

    # Simulate subsequent inference completion
    crud.add_check(
        db=db_session,
        organization_id="org_alpha",
        record_id="REC-PENDING-001",
        check_key="identity_match",
        verdict=Verdict.PASS,
        confidence=0.98,
        detail="Product matches serial number",
        model_version="gemini-3.6-flash",
    )
    crud.update_case_status(
        db_session,
        organization_id="org_alpha",
        record_id="REC-PENDING-001",
        status="completed",
        outcome="PASS",
    )

    updated_case = crud.get_case(db_session, "org_alpha", "REC-PENDING-001")
    assert updated_case.status == "completed"
    assert updated_case.outcome == "PASS"
    assert len(updated_case.checks) == 1
    assert updated_case.checks[0].check_key == "identity_match"
