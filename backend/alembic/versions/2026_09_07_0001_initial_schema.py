"""Initial schema from existing models

Revision ID: 0001_initial
Revises: 
Create Date: 2026-09-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum types - created explicitly to avoid double-creation by sa.Enum columns
_userstatus = postgresql.ENUM('active', 'inactive', 'suspended', 'pending',
                               name='userstatus', create_type=False)
_workflowstatus = postgresql.ENUM('draft', 'active', 'paused', 'archived', 'failed',
                                   name='workflowstatus', create_type=False)
_executionstatus = postgresql.ENUM('pending', 'running', 'paused', 'completed',
                                    'failed', 'cancelled', 'timeout', 'retrying',
                                    name='executionstatus', create_type=False)
_orgmemberrole = postgresql.ENUM('owner', 'admin', 'developer', 'viewer',
                                  name='organizationmemberrole', create_type=False)


def upgrade() -> None:
    # Create enum types once with checkfirst
    _userstatus.create(op.get_bind(), checkfirst=True)
    _workflowstatus.create(op.get_bind(), checkfirst=True)
    _executionstatus.create(op.get_bind(), checkfirst=True)
    _orgmemberrole.create(op.get_bind(), checkfirst=True)

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255)),
        sa.Column('full_name', sa.String(255)),
        sa.Column('avatar_url', sa.String(255)),
        sa.Column('status', _userstatus),
        sa.Column('is_superuser', sa.Boolean),
        sa.Column('is_verified', sa.Boolean),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )

    # Organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('logo_url', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('is_active', sa.Boolean),
        sa.Column('tier', sa.String(255)),
        sa.Column('settings', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )

    # Organization Members table
    op.create_table(
        'organization_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', _orgmemberrole, nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_active', sa.Boolean),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )

    # Workflows table
    op.create_table(
        'workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', _workflowstatus),
        sa.Column('version', sa.Integer),
        sa.Column('config', postgresql.JSON),
        sa.Column('error_count', sa.Integer),
        sa.Column('last_run_at', sa.DateTime(timezone=True)),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )

    # Workflow Nodes table
    op.create_table(
        'workflow_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('node_type', sa.String(255), nullable=False),
        sa.Column('config', postgresql.JSON),
        sa.Column('position_x', sa.Float),
        sa.Column('position_y', sa.Float),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Executions table
    op.create_table(
        'executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('triggered_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('status', _executionstatus),
        sa.Column('trigger_type', sa.String(255)),
        sa.Column('input_data', postgresql.JSON),
        sa.Column('output_data', postgresql.JSON),
        sa.Column('error_message', sa.Text),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('duration_ms', sa.Integer),
        sa.Column('retry_attempt', sa.Integer),
        sa.Column('cost', sa.Float),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_executions_workflow_status', 'executions', ['workflow_id', 'status'])

    # Execution Logs table
    op.create_table(
        'execution_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('executions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('node_id', sa.String(255)),
        sa.Column('status', sa.String(255)),
        sa.Column('message', sa.Text),
        sa.Column('data', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Templates table
    op.create_table(
        'templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('config', postgresql.JSON),
        sa.Column('is_public', sa.Boolean),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )

    # Teams table
    op.create_table(
        'teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Team Members table
    op.create_table(
        'team_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('key_prefix', sa.String(10)),
        sa.Column('scopes', postgresql.JSON),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Audit Log table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('resource_type', sa.String(255)),
        sa.Column('resource_id', sa.String(255)),
        sa.Column('details', postgresql.JSON),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # Notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text),
        sa.Column('type', sa.String(255)),
        sa.Column('is_read', sa.Boolean),
        sa.Column('data', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # OAuth Tokens table
    op.create_table(
        'oauth_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('provider', sa.String(255), nullable=False),
        sa.Column('access_token', sa.Text),
        sa.Column('refresh_token', sa.Text),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('scopes', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('plan', sa.String(255), nullable=False),
        sa.Column('status', sa.String(255)),
        sa.Column('stripe_subscription_id', sa.String(255)),
        sa.Column('current_period_start', sa.DateTime(timezone=True)),
        sa.Column('current_period_end', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Invoices table
    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('currency', sa.String(3)),
        sa.Column('status', sa.String(255)),
        sa.Column('stripe_invoice_id', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('due_date', sa.DateTime(timezone=True)),
        sa.Column('paid_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Marketplace Items table
    op.create_table(
        'marketplace_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('type', sa.String(255)),
        sa.Column('category', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('version', sa.String(50)),
        sa.Column('config', postgresql.JSON),
        sa.Column('rating', sa.Float),
        sa.Column('download_count', sa.Integer),
        sa.Column('is_verified', sa.Boolean),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('marketplace_items')
    op.drop_table('invoices')
    op.drop_table('subscriptions')
    op.drop_table('oauth_tokens')
    op.drop_table('notifications')
    op.drop_table('audit_logs')
    op.drop_table('api_keys')
    op.drop_table('team_members')
    op.drop_table('teams')
    op.drop_table('templates')
    op.drop_table('execution_logs')
    op.drop_index('ix_executions_workflow_status', table_name='executions')
    op.drop_table('executions')
    op.drop_table('workflow_nodes')
    op.drop_table('workflows')
    op.drop_table('projects')
    op.drop_table('organization_members')
    op.drop_table('organizations')
    op.drop_table('users')

    _executionstatus.drop(op.get_bind(), checkfirst=True)
    _workflowstatus.drop(op.get_bind(), checkfirst=True)
    _orgmemberrole.drop(op.get_bind(), checkfirst=True)
    _userstatus.drop(op.get_bind(), checkfirst=True)
