"""add dataset requirement rules and warehouse mappings

Revision ID: 600c037e270e
Revises: 0d5a130da757
Create Date: 2026-11-10 11:02:11.043709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '600c037e270e'
down_revision: Union[str, Sequence[str], None] = '0d5a130da757'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

dataset_requirement_type = postgresql.ENUM(
    "mandatory",
    "optional",
    "conditional",
    name="dataset_requirement_type",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('dataset_requirement_rules',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('dataset_id', sa.UUID(), nullable=False),
    sa.Column('requirement_type', dataset_requirement_type, nullable=False),
    sa.Column('condition_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['dataset_id'], ['dataset_definitions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dataset_requirement_rules_dataset_id'), 'dataset_requirement_rules', ['dataset_id'], unique=False)
    op.create_table('warehouse_dataset_mappings',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('warehouse_dataset_id', sa.UUID(), nullable=False),
    sa.Column('customer_dataset_name', sa.String(length=255), nullable=False),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('confirmed_by', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['warehouse_dataset_id'], ['warehouse_datasets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('warehouse_dataset_id', name='uq_warehouse_dataset_mappings_warehouse_dataset_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('warehouse_dataset_mappings')
    op.drop_index(op.f('ix_dataset_requirement_rules_dataset_id'), table_name='dataset_requirement_rules')
    op.drop_table('dataset_requirement_rules')
