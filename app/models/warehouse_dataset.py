from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Enum as SQLAlchemyEnum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DatasetRequirementType(str, Enum):
    """How a dataset applies to a warehouse."""

    MANDATORY = "mandatory"
    OPTIONAL = "optional"
    CONDITIONAL = "conditional"


class WarehouseDataset(Base):
    """Associates a warehouse with a dataset definition."""

    __tablename__ = "warehouse_datasets"
    __table_args__ = (
        UniqueConstraint(
            "warehouse_id",
            "dataset_id",
            name="uq_warehouse_datasets_warehouse_id_dataset_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("warehouses.id"),
        nullable=False,
    )
    dataset_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("dataset_definitions.id"),
        nullable=False,
    )
    requirement_type: Mapped[DatasetRequirementType] = mapped_column(
        SQLAlchemyEnum(
            DatasetRequirementType,
            name="dataset_requirement_type",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
    )
    condition_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    warehouse: Mapped["Warehouse"] = relationship(back_populates="dataset_associations")
    dataset: Mapped["DatasetDefinition"] = relationship(
        back_populates="warehouse_associations"
    )
    mapping: Mapped["WarehouseDatasetMapping | None"] = relationship(
        back_populates="warehouse_dataset",
        cascade="all, delete-orphan",
        uselist=False,
    )
