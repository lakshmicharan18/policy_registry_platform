"""add upload warehouse and dataset identity to column mappings

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""

from alembic import op
import sqlalchemy as sa


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_warehouse_uploads_id_warehouse_dataset",
        "warehouse_uploads",
        ["id", "warehouse_id", "dataset_id"],
    )
    op.add_column("upload_column_mappings", sa.Column("warehouse_id", sa.UUID(), nullable=True))
    op.add_column("upload_column_mappings", sa.Column("dataset_id", sa.UUID(), nullable=True))
    op.execute("""
        UPDATE upload_column_mappings AS mapping
        SET warehouse_id = upload.warehouse_id,
            dataset_id = upload.dataset_id
        FROM warehouse_uploads AS upload
        WHERE mapping.upload_id = upload.id
    """)
    op.alter_column("upload_column_mappings", "warehouse_id", nullable=False)
    op.alter_column("upload_column_mappings", "dataset_id", nullable=False)
    op.create_foreign_key(
        "fk_upload_column_mappings_warehouse_id",
        "upload_column_mappings",
        "warehouses",
        ["warehouse_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_upload_column_mappings_dataset_id",
        "upload_column_mappings",
        "dataset_definitions",
        ["dataset_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_upload_column_mappings_warehouse_id", "upload_column_mappings", ["warehouse_id"])
    op.create_index("ix_upload_column_mappings_dataset_id", "upload_column_mappings", ["dataset_id"])
    op.create_foreign_key(
        "fk_upload_column_mappings_upload_identity",
        "upload_column_mappings",
        "warehouse_uploads",
        ["upload_id", "warehouse_id", "dataset_id"],
        ["id", "warehouse_id", "dataset_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_upload_column_mappings_upload_identity", "upload_column_mappings", type_="foreignkey")
    op.drop_index("ix_upload_column_mappings_dataset_id", table_name="upload_column_mappings")
    op.drop_index("ix_upload_column_mappings_warehouse_id", table_name="upload_column_mappings")
    op.drop_constraint("fk_upload_column_mappings_dataset_id", "upload_column_mappings", type_="foreignkey")
    op.drop_constraint("fk_upload_column_mappings_warehouse_id", "upload_column_mappings", type_="foreignkey")
    op.drop_column("upload_column_mappings", "dataset_id")
    op.drop_column("upload_column_mappings", "warehouse_id")
    op.drop_constraint("uq_warehouse_uploads_id_warehouse_dataset", "warehouse_uploads", type_="unique")
