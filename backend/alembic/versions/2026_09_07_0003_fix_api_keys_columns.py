"""Fix api_keys missing columns

Revision ID: 0003_fix_api_keys
Revises: 0002_indexes
Create Date: 2026-09-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003_fix_api_keys'
down_revision: Union[str, None] = '0002_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('api_keys', sa.Column('updated_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()))
    op.add_column('api_keys', sa.Column('deleted_at', sa.DateTime(timezone=True),
                  nullable=True))


def downgrade() -> None:
    op.drop_column('api_keys', 'deleted_at')
    op.drop_column('api_keys', 'updated_at')
