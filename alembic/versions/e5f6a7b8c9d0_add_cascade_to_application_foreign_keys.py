"""add cascade deletes to application foreign keys

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""

from alembic import op


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = depends_on = None


# name, child table, parent table, child columns, parent columns, legacy action
FOREIGN_KEYS = (
    ("dataset_columns_dataset_id_fkey", "dataset_columns", "dataset_definitions", ["dataset_id"], ["id"], None),
    ("dataset_requirement_rules_dataset_id_fkey", "dataset_requirement_rules", "dataset_definitions", ["dataset_id"], ["id"], None),
    ("warehouse_datasets_warehouse_id_fkey", "warehouse_datasets", "warehouses", ["warehouse_id"], ["id"], None),
    ("warehouse_datasets_dataset_id_fkey", "warehouse_datasets", "dataset_definitions", ["dataset_id"], ["id"], None),
    ("warehouse_dataset_mappings_warehouse_dataset_id_fkey", "warehouse_dataset_mappings", "warehouse_datasets", ["warehouse_dataset_id"], ["id"], "CASCADE"),
    ("fk_warehouse_dataset_mappings_warehouse_id", "warehouse_dataset_mappings", "warehouses", ["warehouse_id"], ["id"], None),
    ("fk_warehouse_dataset_mappings_dataset_id", "warehouse_dataset_mappings", "dataset_definitions", ["dataset_id"], ["id"], None),
    ("fk_warehouse_dataset_mappings_association_identity", "warehouse_dataset_mappings", "warehouse_datasets", ["warehouse_dataset_id", "warehouse_id", "dataset_id"], ["id", "warehouse_id", "dataset_id"], "CASCADE"),
    ("warehouse_uploads_warehouse_id_fkey", "warehouse_uploads", "warehouses", ["warehouse_id"], ["id"], None),
    ("warehouse_uploads_dataset_id_fkey", "warehouse_uploads", "dataset_definitions", ["dataset_id"], ["id"], None),
    ("upload_column_mappings_upload_id_fkey", "upload_column_mappings", "warehouse_uploads", ["upload_id"], ["id"], "CASCADE"),
    ("upload_column_mappings_logical_column_id_fkey", "upload_column_mappings", "dataset_columns", ["logical_column_id"], ["id"], None),
    ("upload_review_comments_upload_id_fkey", "upload_review_comments", "warehouse_uploads", ["upload_id"], ["id"], "CASCADE"),
    ("upload_review_confirmations_upload_id_fkey", "upload_review_confirmations", "warehouse_uploads", ["upload_id"], ["id"], "CASCADE"),
)


def _replace_foreign_keys(*, cascade: bool) -> None:
    for name, source, _target, _local, _remote, _legacy_action in FOREIGN_KEYS:
        op.drop_constraint(name, source, type_="foreignkey")
    for name, source, target, local, remote, legacy_action in FOREIGN_KEYS:
        op.create_foreign_key(
            name,
            source,
            target,
            local,
            remote,
            ondelete="CASCADE" if cascade else legacy_action,
        )


def upgrade() -> None:
    _replace_foreign_keys(cascade=True)


def downgrade() -> None:
    _replace_foreign_keys(cascade=False)
