from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, column, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WarehouseUpload(Base):
    __tablename__ = "warehouse_uploads"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "warehouse_id",
            "dataset_id",
            name="uq_warehouse_uploads_id_warehouse_dataset",
        ),
        Index(
            "uq_warehouse_uploads_warehouse_normalized_filename",
            "warehouse_id",
            func.lower(func.btrim(column("original_filename"))),
            unique=True,
        ),
        Index(
            "uq_warehouse_uploads_warehouse_dataset",
            "warehouse_id",
            "dataset_id",
            unique=True,
            postgresql_where=text("dataset_id IS NOT NULL"),
        ),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    warehouse_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("dataset_definitions.id", ondelete="CASCADE"), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    source_headers: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    sample_rows: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    column_mappings: Mapped[list["UploadColumnMapping"]] = relationship(back_populates="upload", cascade="all, delete-orphan", foreign_keys="UploadColumnMapping.upload_id")
    comments: Mapped[list["UploadReviewComment"]] = relationship(back_populates="upload", cascade="all, delete-orphan")
    confirmations: Mapped[list["UploadReviewConfirmation"]] = relationship(back_populates="upload", cascade="all, delete-orphan")


class UploadColumnMapping(Base):
    __tablename__ = "upload_column_mappings"
    __table_args__ = (
        UniqueConstraint("upload_id", "source_column_name", name="uq_upload_source_column"),
        UniqueConstraint("upload_id", "logical_column_id", name="uq_upload_logical_column"),
        ForeignKeyConstraint(
            ["upload_id", "warehouse_id", "dataset_id"],
            [
                "warehouse_uploads.id",
                "warehouse_uploads.warehouse_id",
                "warehouse_uploads.dataset_id",
            ],
            name="fk_upload_column_mappings_upload_identity",
            ondelete="CASCADE",
        ),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    upload_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("warehouse_uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("dataset_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    source_column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    logical_column_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("dataset_columns.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    upload: Mapped[WarehouseUpload] = relationship(back_populates="column_mappings", foreign_keys=[upload_id])


class UploadReviewComment(Base):
    __tablename__ = "upload_review_comments"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    upload_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("warehouse_uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    upload: Mapped[WarehouseUpload] = relationship(back_populates="comments")


class UploadReviewConfirmation(Base):
    __tablename__ = "upload_review_confirmations"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    upload_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("warehouse_uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    upload: Mapped[WarehouseUpload] = relationship(back_populates="confirmations")
