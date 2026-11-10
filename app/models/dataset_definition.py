from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DatasetDefinition(Base):
    """A reusable definition of a dataset required by warehouses."""

    __tablename__ = "dataset_definitions"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    dataset_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    columns: Mapped[list["DatasetColumn"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DatasetColumn.column_name",
    )
    warehouse_associations: Mapped[list["WarehouseDataset"]] = relationship(
        back_populates="dataset"
    )
    requirement_rules: Mapped[list["DatasetRequirementRule"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
