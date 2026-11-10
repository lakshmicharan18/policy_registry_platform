"""create dataset catalog tables

Revision ID: 0d5a130da757
Revises: a107760c7d40
Create Date: 2026-11-09 10:51:29.815628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0d5a130da757'
down_revision: Union[str, Sequence[str], None] = 'a107760c7d40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

dataset_data_type = postgresql.ENUM(
    "string",
    "integer",
    "float",
    "boolean",
    "date",
    "datetime",
    name="dataset_data_type",
    create_type=False,
)
dataset_requirement_type = postgresql.ENUM(
    "mandatory",
    "optional",
    "conditional",
    name="dataset_requirement_type",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    dataset_data_type.create(bind, checkfirst=True)
    dataset_requirement_type.create(bind, checkfirst=True)

    op.create_table('dataset_definitions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('dataset_code', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dataset_code')
    )
    op.create_table('dataset_columns',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('dataset_id', sa.UUID(), nullable=False),
    sa.Column('column_name', sa.String(length=100), nullable=False),
    sa.Column('data_type', dataset_data_type, nullable=False),
    sa.Column('is_required', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.ForeignKeyConstraint(['dataset_id'], ['dataset_definitions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dataset_id', 'column_name', name='uq_dataset_columns_dataset_id_column_name')
    )
    op.create_table('warehouse_datasets',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('warehouse_id', sa.UUID(), nullable=False),
    sa.Column('dataset_id', sa.UUID(), nullable=False),
    sa.Column('requirement_type', dataset_requirement_type, nullable=False),
    sa.Column('condition_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['dataset_id'], ['dataset_definitions.id'], ),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('warehouse_id', 'dataset_id', name='uq_warehouse_datasets_warehouse_id_dataset_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('warehouse_datasets')
    op.drop_table('dataset_columns')
    op.drop_table('dataset_definitions')
    bind = op.get_bind()
    dataset_requirement_type.drop(bind, checkfirst=True)
    dataset_data_type.drop(bind, checkfirst=True)
