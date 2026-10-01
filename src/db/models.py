from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Integer, Text, ForeignKeyConstraint, Index
from sqlalchemy.orm import relationship
from src.db.database import Base


class CaseModel(Base):
    __tablename__ = "cases"

    organization_id = Column(String, primary_key=True, nullable=False)
    record_id = Column(String, primary_key=True, nullable=False)
    schema_version = Column(String, default="1.0", nullable=False)
    client_id = Column(String, nullable=True)
    agent = Column(String, default="returns-manager-agent", nullable=False)
    subject = Column(String, nullable=False)
    captured_at = Column(DateTime, nullable=False)
    operator_label = Column(String, nullable=True)
    outcome = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)
    content_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    images = relationship("ImageMetadataModel", back_populates="case", cascade="all, delete-orphan")
    checks = relationship("CheckModel", back_populates="case", cascade="all, delete-orphan")
    overrides = relationship("OverrideModel", back_populates="case", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_cases_tenant_record", "organization_id", "record_id"),
    )


class ImageMetadataModel(Base):
    __tablename__ = "image_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(String, nullable=False)
    record_id = Column(String, nullable=False)
    image_path = Column(String, nullable=False)
    sha256_hash = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "record_id"],
            ["cases.organization_id", "cases.record_id"],
            ondelete="CASCADE",
        ),
        Index("idx_images_tenant_record", "organization_id", "record_id"),
    )

    case = relationship("CaseModel", back_populates="images")


class CheckModel(Base):
    __tablename__ = "checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(String, nullable=False)
    record_id = Column(String, nullable=False)
    check_key = Column(String, nullable=False)
    verdict = Column(String, nullable=False)
    confidence = Column(Float, nullable=True)
    detail = Column(Text, nullable=True)
    model_version = Column(String, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "record_id"],
            ["cases.organization_id", "cases.record_id"],
            ondelete="CASCADE",
        ),
        Index("idx_checks_tenant_record", "organization_id", "record_id"),
    )

    case = relationship("CaseModel", back_populates="checks")


class OverrideModel(Base):
    __tablename__ = "overrides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(String, nullable=False)
    record_id = Column(String, nullable=False)
    original_verdict = Column(String, nullable=False)
    revised_verdict = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    override_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    operator_id = Column(String, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "record_id"],
            ["cases.organization_id", "cases.record_id"],
            ondelete="CASCADE",
        ),
        Index("idx_overrides_tenant_record", "organization_id", "record_id"),
    )

    case = relationship("CaseModel", back_populates="overrides")
