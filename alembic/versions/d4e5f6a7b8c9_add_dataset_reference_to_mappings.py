"""add direct dataset reference and consistency constraint to mappings

Revision ID: d4e5f6a7b8c9
Revises: c3b4d5e6f7a8
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c3b4d5e6f7a8"
branch_labels = depends_on = None


def upgrade() -> None:
    # A candidate key is required for the composite foreign key below.
    op.create_unique_constraint(
        "uq_warehouse_datasets_id_warehouse_dataset",
        "warehouse_datasets",
        ["id", "warehouse_id", "dataset_id"],
    )
    op.add_column(
        "warehouse_dataset_mappings", sa.Column("dataset_id", sa.UUID(), nullable=True)
    )
    # Preserve every existing mapping and derive both direct references from
    # its already-required warehouse_dataset association.
    op.execute("""
        UPDATE warehouse_dataset_mappings AS mapping
        SET warehouse_id = association.warehouse_id,
            dataset_id = association.dataset_id
        FROM warehouse_datasets AS association
        WHERE mapping.warehouse_dataset_id = association.id
    """)
    op.alter_column("warehouse_dataset_mappings", "dataset_id", nullable=False)
    op.create_foreign_key(
        "fk_warehouse_dataset_mappings_dataset_id",
        "warehouse_dataset_mappings",
        "dataset_definitions",
        ["dataset_id"],
        ["id"],
    )
    op.create_index(
        "ix_warehouse_dataset_mappings_dataset_id",
        "warehouse_dataset_mappings",
        ["dataset_id"],
    )
    op.create_foreign_key(
        "fk_warehouse_dataset_mappings_association_identity",
        "warehouse_dataset_mappings",
        "warehouse_datasets",
        ["warehouse_dataset_id", "warehouse_id", "dataset_id"],
        ["id", "warehouse_id", "dataset_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_warehouse_dataset_mappings_association_identity",
        "warehouse_dataset_mappings",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_warehouse_dataset_mappings_dataset_id",
        table_name="warehouse_dataset_mappings",
    )
    op.drop_constraint(
        "fk_warehouse_dataset_mappings_dataset_id",
        "warehouse_dataset_mappings",
        type_="foreignkey",
    )
    op.drop_column("warehouse_dataset_mappings", "dataset_id")
    op.drop_constraint(
        "uq_warehouse_datasets_id_warehouse_dataset",
        "warehouse_datasets",
        type_="unique",
    )
