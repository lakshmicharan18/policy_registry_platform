"""add warehouse onboarding workflow

Revision ID: 9d319b4b87ef
Revises: 600c037e270e
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "9d319b4b87ef"
down_revision = "600c037e270e"
branch_labels = depends_on = None

def upgrade() -> None:
    op.create_table("warehouse_uploads", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("warehouse_id", sa.UUID(), nullable=False), sa.Column("dataset_id", sa.UUID()), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("storage_key", sa.String(255), nullable=False, unique=True), sa.Column("source_headers", postgresql.JSONB(), nullable=False), sa.Column("sample_rows", postgresql.JSONB(), nullable=False), sa.Column("row_count", sa.Integer(), nullable=False), sa.Column("status", sa.String(32), server_default="draft", nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]), sa.ForeignKeyConstraint(["dataset_id"], ["dataset_definitions.id"]))
    op.create_index("ix_warehouse_uploads_warehouse_id", "warehouse_uploads", ["warehouse_id"])
    op.create_table("upload_column_mappings", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("upload_id", sa.UUID(), nullable=False), sa.Column("source_column_name", sa.String(255), nullable=False), sa.Column("logical_column_id", sa.UUID(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["upload_id"], ["warehouse_uploads.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["logical_column_id"], ["dataset_columns.id"]), sa.UniqueConstraint("upload_id", "source_column_name", name="uq_upload_source_column"), sa.UniqueConstraint("upload_id", "logical_column_id", name="uq_upload_logical_column"))
    op.create_index("ix_upload_column_mappings_upload_id", "upload_column_mappings", ["upload_id"])
    for table in ("upload_review_comments", "upload_review_confirmations"):
        columns = [sa.Column("id", sa.UUID(), primary_key=True), sa.Column("upload_id", sa.UUID(), nullable=False), sa.Column("author", sa.String(255), nullable=False), sa.Column("role", sa.String(32), nullable=False)]
        if table == "upload_review_comments": columns.append(sa.Column("comment", sa.Text(), nullable=False)); columns.append(sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
        else: columns.append(sa.Column("confirmed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
        columns.append(sa.ForeignKeyConstraint(["upload_id"], ["warehouse_uploads.id"], ondelete="CASCADE")); op.create_table(table, *columns); op.create_index(f"ix_{table}_upload_id", table, ["upload_id"])

def downgrade() -> None:
    for table in ("upload_review_confirmations", "upload_review_comments", "upload_column_mappings", "warehouse_uploads"):
        op.drop_table(table)
