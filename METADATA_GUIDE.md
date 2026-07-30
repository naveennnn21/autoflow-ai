# AutoFlow AI Metadata System

## Overview

The metadata layer is the **single source of truth** for the AutoFlow AI platform.
All code generation across backend, frontend, infrastructure, and documentation
consumes these metadata definitions. Nothing should be hardcoded.

### Architecture Flow

```
metadata/*.yaml  ->  MetadataLoader  ->  IntermediateModel  ->  Generators  ->  Code
       |
  MetadataValidator
       |
  Validation Report
```

## Directory Structure

```
metadata/
  entities/      # Database models and schemas (18 entity files)
  services/      # Business logic services (12 service files)
  api/           # REST API endpoints (8 API files)
  permissions/   # RBAC roles and policies (3 files)
  workflows/     # Workflow templates, states, retry policies (4 files)
  connectors/    # External service integrations (9 connector files)
  ai/            # AI/ML models, agents, prompts (7 files)
  ui/            # Frontend forms, tables, navigation, themes (6 files)
  events/        # Platform event definitions (1 file)
  plugins/       # Plugin SDK metadata (1 file)
```

## Entities (18)

| Entity | Table | Tenant | Timestamps | Soft Delete |
|--------|-------|--------|------------|-------------|
| User | users | No | Yes | Yes |
| Organization | organizations | No | Yes | Yes |
| OrganizationMember | organization_members | No | No | No |
| Team | teams | Yes | Yes | Yes |
| TeamMember | team_members | No | No | No |
| Project | projects | Yes | Yes | Yes |
| Workflow | workflows | Yes | Yes | Yes |
| WorkflowNode | workflow_nodes | No | Yes | No |
| Execution | executions | Yes | Yes | Yes |
| ExecutionLog | execution_logs | Yes | Yes | No |
| Template | templates | Yes | Yes | Yes |
| MarketplaceItem | marketplace_items | No | Yes | No |
| Notification | notifications | No | Yes | No |
| AuditLog | audit_logs | Yes | Yes | No |
| APIKey | api_keys | No | Yes | Yes |
| OAuthToken | oauth_tokens | No | Yes | No |
| Subscription | subscriptions | Yes | Yes | Yes |
| Invoice | invoices | Yes | Yes | No |

## Services (12)

Auth, Organization, Team, Project, Workflow, Execution,
Monitoring, Billing, Marketplace, Notification, Analytics, Audit

## API Endpoints (8 files)

auth, users, organizations, projects, workflows, executions, monitoring, billing

## Permissions

Roles: owner (100) > admin (80) > developer (60) > viewer (40) > member (20)
Resource-level permissions: workflow.*, organization.*, project.*, etc.

## Connectors (9)

Gmail, Slack, Discord, GitHub, Notion, Stripe, Shopify, Airtable, GoogleDrive

## AI (7 files)

models.yaml, agents.yaml, prompts.yaml, memory.yaml,
planner.yaml, optimizer.yaml, workflow_generator.yaml

## UI (6 files)

forms.yaml, tables.yaml, pages.yaml, dashboard.yaml, navigation.yaml, themes.yaml

## Events (25+ platform events)

WorkflowStarted, WorkflowCompleted, WorkflowFailed, ExecutionRetried,
InvoicePaid, SubscriptionCancelled, ConnectorConnected, AIWorkflowGenerated, etc.

## Validation

Run full metadata validation:

```bash
python -c "
from scripts.generators.common.metadata_validator import MetadataValidator
v = MetadataValidator(metadata_dir='metadata')
v.validate_all()
print(v.summary())
"
```

## Best Practices

1. One entity per YAML file
2. Use enums instead of raw strings for constrained values
3. Define bidirectional relationships with back_populates
4. Mark sensitive fields (passwords, tokens) with sensitive: true
5. Set tenant: true for organization-scoped entities
6. Define validation rules in service methods blocks
7. Specify rate limits on API endpoints
8. Always provide descriptions for entities, fields, and endpoints
