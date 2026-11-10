from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.models.dataset_column import DatasetColumn, DatasetDataType
from app.models.dataset_definition import DatasetDefinition
from app.models.warehouse import Warehouse
from app.models.warehouse_dataset import DatasetRequirementType, WarehouseDataset


def unique_constraint_columns(table: object) -> set[frozenset[str]]:
    return {
        frozenset(constraint.columns.keys())
        for constraint in table.constraints  # type: ignore[union-attr]
        if isinstance(constraint, UniqueConstraint)
    }


def test_dataset_definition_metadata_and_relationships() -> None:
    table = DatasetDefinition.__table__

    assert table.name == "dataset_definitions"
    assert set(table.columns.keys()) == {
        "id",
        "dataset_code",
        "name",
        "description",
        "created_at",
    }
    assert table.c.id.primary_key
    assert table.c.dataset_code.unique
    assert table.c.dataset_code.type.length == 100
    assert table.c.name.type.length == 255
    assert table.c.description.nullable
    assert table.c.created_at.type.timezone is True
    assert DatasetDefinition.columns.property.mapper.class_ is DatasetColumn
    assert DatasetDefinition.warehouse_associations.property.mapper.class_ is WarehouseDataset


def test_dataset_column_metadata_constraints_and_relationships() -> None:
    table = DatasetColumn.__table__

    assert table.name == "dataset_columns"
    assert table.c.dataset_id.foreign_keys.pop().target_fullname == "dataset_definitions.id"
    assert table.c.column_name.type.length == 100
    assert set(table.c.data_type.type.enums) == {item.value for item in DatasetDataType}
    assert table.c.is_required.default.arg is True
    assert frozenset({"dataset_id", "column_name"}) in unique_constraint_columns(table)
    assert DatasetColumn.dataset.property.mapper.class_ is DatasetDefinition


def test_warehouse_dataset_metadata_constraints_and_relationships() -> None:
    table = WarehouseDataset.__table__

    assert table.name == "warehouse_datasets"
    foreign_key_targets = {
        foreign_key.target_fullname
        for column in (table.c.warehouse_id, table.c.dataset_id)
        for foreign_key in column.foreign_keys
    }
    assert foreign_key_targets == {"warehouses.id", "dataset_definitions.id"}
    assert set(table.c.requirement_type.type.enums) == {
        item.value for item in DatasetRequirementType
    }
    assert isinstance(table.c.condition_config.type, JSONB)
    assert table.c.condition_config.nullable
    assert frozenset({"warehouse_id", "dataset_id"}) in unique_constraint_columns(table)
    assert WarehouseDataset.warehouse.property.mapper.class_ is Warehouse
    assert WarehouseDataset.dataset.property.mapper.class_ is DatasetDefinition
    assert Warehouse.dataset_associations.property.mapper.class_ is WarehouseDataset
