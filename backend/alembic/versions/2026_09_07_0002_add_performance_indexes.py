"""Add performance indexes

Revision ID: 0002_indexes
Revises: 0001_initial
Create Date: 2026-09-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_indexes'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOTE: Several indexes were auto-created by migration 0001_initial via
    # index=True on column definitions. We only add COMPOSITE indexes and
    # single-column indexes on columns that did NOT have index=True.
    #
    # Already created by 0001_initial (DO NOT recreate):
    #   ix_execution_logs_execution_id  (execution_logs.execution_id, index=True)
    #   ix_workflow_nodes_workflow_id   (workflow_nodes.workflow_id, index=True)
    #   ix_workflows_organization_id   (workflows.organization_id, index=True)
    #   ix_executions_organization_id   (executions.organization_id, index=True)
    #   ix_organization_members_organization_id (organization_members.organization_id)
    #   ix_notifications_user_id        (notifications.user_id, index=True)
    #   ix_api_keys_organization_id     (api_keys.organization_id, index=True)
    #   ix_audit_logs_organization_id   (audit_logs.organization_id, index=True)

    # Audit logs - frequently queried by created_at for analytics
    op.create_index(
        'ix_audit_logs_org_created',
        'audit_logs',
        ['organization_id', 'created_at'],
    )

    # Workflows - frequently queried by organization_id and status
    op.create_index(
        'ix_workflows_org_status',
        'workflows',
        ['organization_id', 'status'],
    )

    # Executions - frequently queried by organization_id and created_at
    op.create_index(
        'ix_executions_org_created',
        'executions',
        ['organization_id', 'created_at'],
    )

    # Organization members - frequently queried by user_id
    op.create_index(
        'ix_org_members_user_id',
        'organization_members',
        ['user_id'],
    )

    # Notifications - frequently queried by user_id and is_read
    op.create_index(
        'ix_notifications_user_read',
        'notifications',
        ['user_id', 'is_read'],
    )

    # API keys - frequently queried by key_hash for authentication
    op.create_index(
        'ix_api_keys_key_hash',
        'api_keys',
        ['key_hash'],
    )

    # Marketplace items - frequently queried by type and category
    op.create_index(
        'ix_marketplace_type_category',
        'marketplace_items',
        ['type', 'category'],
    )


def downgrade() -> None:
    op.drop_index('ix_marketplace_type_category', table_name='marketplace_items')
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_index('ix_notifications_user_read', table_name='notifications')
    op.drop_index('ix_org_members_user_id', table_name='organization_members')
    op.drop_index('ix_executions_org_created', table_name='executions')
    op.drop_index('ix_workflows_org_status', table_name='workflows')
    op.drop_index('ix_audit_logs_org_created', table_name='audit_logs')
