"""Add author_id to marketplace_items

Revision ID: 0004_marketplace_author
Revises: 0003_fix_api_keys
Create Date: 2026-09-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0004_marketplace_author'
down_revision: Union[str, None] = '0003_fix_api_keys'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('marketplace_items', sa.Column(
        'author_id',
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        index=True,
    ))
    op.add_column('marketplace_items', sa.Column(
        'is_paid', sa.Boolean(), nullable=True,
    ))
    op.add_column('marketplace_items', sa.Column(
        'price', sa.Float(), nullable=True,
    ))
    op.add_column('marketplace_items', sa.Column(
        'deleted_at', sa.DateTime(timezone=True), nullable=True,
    ))


def downgrade() -> None:
    op.drop_column('marketplace_items', 'deleted_at')
    op.drop_column('marketplace_items', 'price')
    op.drop_column('marketplace_items', 'is_paid')
    op.drop_column('marketplace_items', 'author_id')
