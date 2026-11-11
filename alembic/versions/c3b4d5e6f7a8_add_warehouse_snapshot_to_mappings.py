"""add warehouse snapshot to mappings

Revision ID: c3b4d5e6f7a8
Revises: 9d319b4b87ef
"""
from alembic import op
import sqlalchemy as sa

revision = "c3b4d5e6f7a8"
down_revision = "9d319b4b87ef"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("warehouse_dataset_mappings", sa.Column("warehouse_id", sa.UUID(), nullable=True))
    op.add_column("warehouse_dataset_mappings", sa.Column("warehouse_code", sa.String(length=50), nullable=True))
    op.add_column("warehouse_dataset_mappings", sa.Column("warehouse_name", sa.String(length=255), nullable=True))
    op.execute("""
        UPDATE warehouse_dataset_mappings AS mapping
        SET warehouse_id = association.warehouse_id,
            warehouse_code = warehouse.warehouse_code,
            warehouse_name = warehouse.name
        FROM warehouse_datasets AS association
        JOIN warehouses AS warehouse ON warehouse.id = association.warehouse_id
        WHERE mapping.warehouse_dataset_id = association.id
    """)
    op.alter_column("warehouse_dataset_mappings", "warehouse_id", nullable=False)
    op.alter_column("warehouse_dataset_mappings", "warehouse_code", nullable=False)
    op.alter_column("warehouse_dataset_mappings", "warehouse_name", nullable=False)
    op.create_foreign_key("fk_warehouse_dataset_mappings_warehouse_id", "warehouse_dataset_mappings", "warehouses", ["warehouse_id"], ["id"])
    op.create_index("ix_warehouse_dataset_mappings_warehouse_id", "warehouse_dataset_mappings", ["warehouse_id"])


def downgrade() -> None:
    op.drop_index("ix_warehouse_dataset_mappings_warehouse_id", table_name="warehouse_dataset_mappings")
    op.drop_constraint("fk_warehouse_dataset_mappings_warehouse_id", "warehouse_dataset_mappings", type_="foreignkey")
    op.drop_column("warehouse_dataset_mappings", "warehouse_name")
    op.drop_column("warehouse_dataset_mappings", "warehouse_code")
    op.drop_column("warehouse_dataset_mappings", "warehouse_id")
