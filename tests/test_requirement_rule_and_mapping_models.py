from uuid import uuid4

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.models.dataset_definition import DatasetDefinition
from app.models.dataset_requirement_rule import DatasetRequirementRule
from app.models.warehouse import Warehouse
from app.models.warehouse_dataset import DatasetRequirementType, WarehouseDataset
from app.models.warehouse_dataset_mapping import WarehouseDatasetMapping


def unique_constraint_columns(table: object) -> set[frozenset[str]]:
    return {
        frozenset(constraint.columns.keys())
        for constraint in table.constraints  # type: ignore[union-attr]
        if isinstance(constraint, UniqueConstraint)
    }


def test_dataset_requirement_rule_metadata_and_relationships() -> None:
    table = DatasetRequirementRule.__table__

    assert table.name == "dataset_requirement_rules"
    assert set(table.columns.keys()) == {
        "id",
        "dataset_id",
        "requirement_type",
        "condition_config",
        "description",
        "is_active",
        "created_at",
    }
    assert {foreign_key.target_fullname for foreign_key in table.c.dataset_id.foreign_keys} == {
        "dataset_definitions.id"
    }
    assert "ix_dataset_requirement_rules_dataset_id" in {
        index.name for index in table.indexes
    }
    assert set(table.c.requirement_type.type.enums) == {
        item.value for item in DatasetRequirementType
    }
    assert isinstance(table.c.condition_config.type, JSONB)
    assert table.c.is_active.default.arg is True
    assert table.c.created_at.type.timezone is True
    assert DatasetRequirementRule.dataset.property.mapper.class_ is DatasetDefinition
    assert DatasetDefinition.requirement_rules.property.mapper.class_ is DatasetRequirementRule


def test_dataset_definition_can_have_multiple_requirement_rules() -> None:
    dataset = DatasetDefinition(
        id=uuid4(),
        dataset_code="TEST_DATASET",
        name="Test Dataset",
    )
    first_rule = DatasetRequirementRule(
        id=uuid4(),
        requirement_type=DatasetRequirementType.MANDATORY,
    )
    second_rule = DatasetRequirementRule(
        id=uuid4(),
        requirement_type=DatasetRequirementType.CONDITIONAL,
        condition_config={"enabled": True},
    )

    dataset.requirement_rules.extend([first_rule, second_rule])

    assert first_rule.dataset is dataset
    assert second_rule.dataset is dataset
    assert dataset.requirement_rules == [first_rule, second_rule]


def test_warehouse_dataset_mapping_metadata_and_relationships() -> None:
    table = WarehouseDatasetMapping.__table__

    assert table.name == "warehouse_dataset_mappings"
    assert set(table.columns.keys()) == {
        "id",
        "warehouse_dataset_id",
        "customer_dataset_name",
        "confirmed_at",
        "confirmed_by",
        "created_at",
    }
    foreign_key = next(iter(table.c.warehouse_dataset_id.foreign_keys))
    assert foreign_key.target_fullname == "warehouse_datasets.id"
    assert foreign_key.ondelete == "CASCADE"
    assert frozenset({"warehouse_dataset_id"}) in unique_constraint_columns(table)
    assert WarehouseDatasetMapping.warehouse_dataset.property.mapper.class_ is WarehouseDataset
    assert WarehouseDataset.mapping.property.mapper.class_ is WarehouseDatasetMapping


def test_different_warehouses_can_map_different_names_to_one_dataset() -> None:
    dataset = DatasetDefinition(
        id=uuid4(),
        dataset_code="TEST_DATASET",
        name="Test Dataset",
    )
    first_warehouse = Warehouse(
        id=uuid4(),
        warehouse_code="WH001",
        name="First Warehouse",
    )
    second_warehouse = Warehouse(
        id=uuid4(),
        warehouse_code="WH002",
        name="Second Warehouse",
    )
    first_association = WarehouseDataset(
        id=uuid4(),
        warehouse=first_warehouse,
        dataset=dataset,
        requirement_type=DatasetRequirementType.MANDATORY,
    )
    second_association = WarehouseDataset(
        id=uuid4(),
        warehouse=second_warehouse,
        dataset=dataset,
        requirement_type=DatasetRequirementType.MANDATORY,
    )
    first_mapping = WarehouseDatasetMapping(
        id=uuid4(),
        customer_dataset_name="STOCK_DETAILS",
        warehouse_dataset=first_association,
    )
    second_mapping = WarehouseDatasetMapping(
        id=uuid4(),
        customer_dataset_name="CURRENT_STOCK",
        warehouse_dataset=second_association,
    )

    assert first_mapping.warehouse_dataset.dataset is dataset
    assert second_mapping.warehouse_dataset.dataset is dataset
    assert first_mapping.customer_dataset_name != second_mapping.customer_dataset_name
