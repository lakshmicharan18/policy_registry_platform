"""add warehouse upload uniqueness rules

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""

from alembic import op
import sqlalchemy as sa


revision = "g7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = depends_on = None


def upgrade() -> None:
    # Both indexes are warehouse-scoped: other warehouses may use the same
    # filename and may map an upload to the same logical dataset.
    op.create_index(
        "uq_warehouse_uploads_warehouse_normalized_filename",
        "warehouse_uploads",
        ["warehouse_id", sa.text("lower(btrim(original_filename))")],
        unique=True,
    )
    op.create_index(
        "uq_warehouse_uploads_warehouse_dataset",
        "warehouse_uploads",
        ["warehouse_id", "dataset_id"],
        unique=True,
        postgresql_where=sa.text("dataset_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_warehouse_uploads_warehouse_dataset", table_name="warehouse_uploads")
    op.drop_index("uq_warehouse_uploads_warehouse_normalized_filename", table_name="warehouse_uploads")
