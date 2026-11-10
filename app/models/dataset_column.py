from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Enum as SQLAlchemyEnum, ForeignKey, String, UniqueConstraint, true
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DatasetDataType(str, Enum):
    """Logical types supported by the dataset catalog."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"


class DatasetColumn(Base):
    """A column defined within a dataset definition."""

    __tablename__ = "dataset_columns"
    __table_args__ = (
        UniqueConstraint("dataset_id", "column_name", name="uq_dataset_columns_dataset_id_column_name"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    dataset_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("dataset_definitions.id"),
        nullable=False,
    )
    column_name: Mapped[str] = mapped_column(String(100), nullable=False)
    data_type: Mapped[DatasetDataType] = mapped_column(
        SQLAlchemyEnum(
            DatasetDataType,
            name="dataset_data_type",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
    dataset: Mapped["DatasetDefinition"] = relationship(back_populates="columns")
