from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WarehouseDatasetMapping(Base):
    """A warehouse's confirmed source name for a canonical dataset requirement."""

    __tablename__ = "warehouse_dataset_mappings"
    __table_args__ = (
        UniqueConstraint(
            "warehouse_dataset_id",
            name="uq_warehouse_dataset_mappings_warehouse_dataset_id",
        ),
        ForeignKeyConstraint(
            ["warehouse_dataset_id", "warehouse_id", "dataset_id"],
            [
                "warehouse_datasets.id",
                "warehouse_datasets.warehouse_id",
                "warehouse_datasets.dataset_id",
            ],
            name="fk_warehouse_dataset_mappings_association_identity",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    warehouse_dataset_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("warehouse_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("dataset_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_code: Mapped[str] = mapped_column(String(50), nullable=False)
    warehouse_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_dataset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    warehouse_dataset: Mapped["WarehouseDataset"] = relationship(
        back_populates="mapping",
        foreign_keys=[warehouse_dataset_id],
    )
    warehouse: Mapped["Warehouse"] = relationship()
    dataset: Mapped["DatasetDefinition"] = relationship()
