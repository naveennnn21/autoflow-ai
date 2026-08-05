"""AutoFlow AI - Development seed script.

Populates a fresh database with realistic demo data so the frontend
(which is fully wired to the real API) has something to render:

    - demo user + organization + owner membership
    - 12 marketplace items (connectors) with rich config metadata
    - 6 workflows with node/edge graphs stored in ``config``
    - executions covering every status, plus API keys, audit logs,
      notifications and a team

The script goes through the same repositories the API uses, so it stays
consistent with the real application logic (hashing, defaults, etc.).

Usage:
    cd backend
    python -m app.seed                 # create demo data (idempotent)
    python -m app.seed --reset         # wipe seeded data first, then re-seed
    python -m app.seed --email you@x.com --password secret   # custom credentials

Requires a running PostgreSQL (see docker-compose.yml) with the schema
applied: ``alembic upgrade head`` (or the app's ``init_db()`` fallback).
"""

import argparse
import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.database import async_session_factory, init_db
from app.core.security import hash_password
from app.models.enums import (
    ExecutionStatus,
    OrganizationMemberRole,
    UserStatus,
    WorkflowStatus,
)
from app.repositories.audit_log import AuditLogRepository
from app.repositories.execution import ExecutionRepository
from app.repositories.marketplace_item import MarketplaceItemRepository
from app.repositories.notification import NotificationRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.team import TeamRepository
from app.repositories.user import UserRepository


def _config(logo, color, auth, scopes, actions, triggers, rate_limit, health, installs, verified=True, popular=False, tags=None):
    return {
        "logo": logo, "color": color, "auth": auth, "scopes": scopes,
        "actions": actions, "triggers": triggers, "rateLimit": rate_limit,
        "health": health, "installs": installs, "verified": verified,
        "popular": popular, "tags": tags or [],
    }


_SPECS_A = [
    {
        "name": "Slack", "slug": "slack", "category": "Communication",
        "description": "Send messages, post to channels, and react to workspace activity in real time.",
        "rating": 4.9, "download_count": 12480,
        "config": _config(
            "slack", "#611f69", "oauth2", ["chat:write", "channels:read", "users:read"],
            [
                {"id": "post_message", "name": "Post Message", "description": "Send a message to a channel", "inputs": ["channel", "text"], "outputs": ["ts"], "kind": "write"},
                {"id": "create_channel", "name": "Create Channel", "description": "Create a new channel", "inputs": ["name"], "outputs": ["channel_id"], "kind": "write"},
                {"id": "search_messages", "name": "Search Messages", "description": "Search workspace messages", "inputs": ["query"], "outputs": ["messages"], "kind": "search"},
            ],
            [
                {"id": "new_message", "name": "New Message", "description": "Triggers on new message", "kind": "webhook"},
                {"id": "mention", "name": "Mention", "description": "Triggers when the bot is mentioned", "kind": "webhook"},
            ],
            "100 req/min", "healthy", 12480, popular=True, tags=["communication", "team"],
        ),
    },
    {
        "name": "Gmail", "slug": "gmail", "category": "Email",
        "description": "Read, send, and organize emails with full Gmail API support.",
        "rating": 4.8, "download_count": 9864,
        "config": _config(
            "mail", "#EA4335", "oauth2", ["gmail.send", "gmail.readonly"],
            [
                {"id": "send_email", "name": "Send Email", "description": "Send a new email", "inputs": ["to", "subject", "body"], "outputs": ["message_id"], "kind": "write"},
                {"id": "search_emails", "name": "Search Emails", "description": "Search inbox", "inputs": ["query"], "outputs": ["emails"], "kind": "search"},
            ],
            [
                {"id": "new_email", "name": "New Email", "description": "Triggers on new email", "kind": "webhook"},
                {"id": "email_sent", "name": "Email Sent", "description": "Triggers when email sent", "kind": "polling"},
            ],
            "250 req/min", "healthy", 9864, popular=True, tags=["email"],
        ),
    },
    {
        "name": "GitHub", "slug": "github", "category": "Developer",
        "description": "Automate repos, issues, PRs, and CI/CD pipelines.",
        "rating": 4.9, "download_count": 8532,
        "config": _config(
            "github", "#24292F", "oauth2", ["repo", "workflow"],
            [
                {"id": "create_issue", "name": "Create Issue", "description": "Create a new issue", "inputs": ["repo", "title", "body"], "outputs": ["issue_number"], "kind": "write"},
                {"id": "create_pr", "name": "Create PR", "description": "Open a pull request", "inputs": ["repo", "title", "head"], "outputs": ["pr_number"], "kind": "write"},
            ],
            [
                {"id": "issue_opened", "name": "Issue Opened", "description": "Triggers on issue creation", "kind": "webhook"},
                {"id": "pr_merged", "name": "PR Merged", "description": "Triggers when PR merges", "kind": "webhook"},
            ],
            "5000 req/hr", "healthy", 8532, popular=True, tags=["developer"],
        ),
    },
]


_SPECS_A += [
    {
        "name": "Notion", "slug": "notion", "category": "Productivity",
        "description": "Create pages, databases, and comments across your workspace.",
        "rating": 4.7, "download_count": 7645,
        "config": _config(
            "notion", "#111111", "oauth2", ["read_content", "write_content"],
            [
                {"id": "create_page", "name": "Create Page", "description": "Create a new page", "inputs": ["parent", "title", "content"], "outputs": ["page_id"], "kind": "write"},
                {"id": "add_db_row", "name": "Add DB Row", "description": "Add row to database", "inputs": ["database_id", "properties"], "outputs": ["page_id"], "kind": "write"},
            ],
            [{"id": "page_created", "name": "Page Created", "description": "Triggers on page creation", "kind": "polling"}],
            "3 req/s", "healthy", 7645, tags=["productivity", "docs"],
        ),
    },
    {
        "name": "Stripe", "slug": "stripe", "category": "Payments",
        "description": "Automate payments, subscriptions, invoices, and customers.",
        "rating": 4.8, "download_count": 6871,
        "config": _config(
            "stripe", "#635BFF", "api_key", ["charges", "customers", "subscriptions"],
            [
                {"id": "create_customer", "name": "Create Customer", "description": "Create a new customer", "inputs": ["email", "name"], "outputs": ["customer_id"], "kind": "write"},
                {"id": "create_charge", "name": "Create Charge", "description": "Charge a customer", "inputs": ["customer_id", "amount"], "outputs": ["charge_id"], "kind": "write"},
            ],
            [
                {"id": "invoice_paid", "name": "Invoice Paid", "description": "Triggers on invoice payment", "kind": "webhook"},
                {"id": "customer_created", "name": "Customer Created", "description": "Triggers on new customer", "kind": "webhook"},
            ],
            "100 req/s", "healthy", 6871, popular=True, tags=["payments"],
        ),
    },
    {
        "name": "Shopify", "slug": "shopify", "category": "E-commerce",
        "description": "Manage products, orders, and inventory from your store.",
        "rating": 4.6, "download_count": 4520,
        "config": _config(
            "shopping-bag", "#96BF48", "oauth2", ["read_products", "write_orders"],
            [
                {"id": "create_product", "name": "Create Product", "description": "Create a new product", "inputs": ["title", "price"], "outputs": ["product_id"], "kind": "write"},
                {"id": "update_inventory", "name": "Update Inventory", "description": "Set inventory level", "inputs": ["product_id", "quantity"], "outputs": ["ok"], "kind": "write"},
            ],
            [{"id": "order_created", "name": "Order Created", "description": "Triggers on new order", "kind": "webhook"}],
            "40 req/s", "healthy", 4520, tags=["ecommerce"],
        ),
    },
]


_SPECS_B = [
    {
        "name": "Discord", "slug": "discord", "category": "Communication",
        "description": "Send messages and manage servers and channels.",
        "rating": 4.5, "download_count": 3890,
        "config": _config(
            "message-square", "#5865F2", "bearer", ["messages.read", "guilds.write"],
            [
                {"id": "send_message", "name": "Send Message", "description": "Send message to channel", "inputs": ["channel_id", "content"], "outputs": ["message_id"], "kind": "write"},
            ],
            [{"id": "message_sent", "name": "Message Sent", "description": "Triggers on new message", "kind": "webhook"}],
            "50 req/s", "healthy", 3890, tags=["communication"],
        ),
    },
    {
        "name": "Google Drive", "slug": "google-drive", "category": "Storage",
        "description": "Upload, download, and organize files in Drive.",
        "rating": 4.7, "download_count": 3210,
        "config": _config(
            "hard-drive", "#4285F4", "oauth2", ["drive.file"],
            [
                {"id": "upload_file", "name": "Upload File", "description": "Upload a file", "inputs": ["name", "content"], "outputs": ["file_id"], "kind": "upload"},
                {"id": "list_files", "name": "List Files", "description": "List files in folder", "inputs": ["folder_id"], "outputs": ["files"], "kind": "read"},
            ],
            [{"id": "file_created", "name": "File Created", "description": "Triggers on new file", "kind": "polling"}],
            "100 req/s", "healthy", 3210, tags=["storage"],
        ),
    },
    {
        "name": "Airtable", "slug": "airtable", "category": "Database",
        "description": "Sync records and bases with two-way automation.",
        "rating": 4.6, "download_count": 2984,
        "config": _config(
            "table", "#F82B60", "api_key", ["data.records"],
            [
                {"id": "create_record", "name": "Create Record", "description": "Add a record", "inputs": ["base_id", "table", "fields"], "outputs": ["record_id"], "kind": "write"},
                {"id": "update_record", "name": "Update Record", "description": "Update fields", "inputs": ["record_id", "fields"], "outputs": ["record_id"], "kind": "write"},
            ],
            [{"id": "record_created", "name": "Record Created", "description": "Triggers on new record", "kind": "polling"}],
            "5 req/s", "healthy", 2984, tags=["database"],
        ),
    },
]


_SPECS_B += [
    {
        "name": "Linear", "slug": "linear", "category": "Productivity",
        "description": "Automate issues, cycles, and project tracking.",
        "rating": 4.8, "download_count": 2104,
        "config": _config(
            "git-branch", "#5E6AD2", "oauth2", ["issues:read", "issues:write"],
            [
                {"id": "create_issue", "name": "Create Issue", "description": "Create a new issue", "inputs": ["team_id", "title"], "outputs": ["issue_id"], "kind": "write"},
            ],
            [{"id": "issue_created", "name": "Issue Created", "description": "Triggers on new issue", "kind": "webhook"}],
            "100 req/min", "degraded", 2104, tags=["productivity", "issues"],
        ),
    },
    {
        "name": "PostgreSQL", "slug": "postgres", "category": "Database",
        "description": "Query and mutate tables with parameterized SQL.",
        "rating": 4.5, "download_count": 1874,
        "config": _config(
            "database", "#336791", "basic", ["read", "write"],
            [
                {"id": "run_query", "name": "Run Query", "description": "Execute a SQL query", "inputs": ["sql", "params"], "outputs": ["rows"], "kind": "read"},
                {"id": "insert_row", "name": "Insert Row", "description": "Insert into a table", "inputs": ["table", "data"], "outputs": ["id"], "kind": "write"},
            ],
            [],
            "unlimited", "healthy", 1874, tags=["database"],
        ),
    },
    {
        "name": "HubSpot", "slug": "hubspot", "category": "CRM",
        "description": "Sync contacts, deals, and pipelines across your CRM.",
        "rating": 4.4, "download_count": 1532,
        "config": _config(
            "users", "#FF7A59", "oauth2", ["crm.objects.contacts"],
            [
                {"id": "create_contact", "name": "Create Contact", "description": "Create a contact", "inputs": ["email", "firstname"], "outputs": ["contact_id"], "kind": "write"},
            ],
            [{"id": "contact_created", "name": "Contact Created", "description": "Triggers on new contact", "kind": "webhook"}],
            "100 req/s", "healthy", 1532, tags=["crm"],
        ),
    },
]

MARKETPLACE_SPECS = _SPECS_A + _SPECS_B


def _mins(m, base):
    return base - timedelta(minutes=m)


def _hours(h, base):
    return base - timedelta(hours=h)


def _days(d, base):
    return base - timedelta(days=d)


def _workflow_nodes(seed):
    """Return (nodes, edges) for the frontend workflow builder, keyed by seed name."""
    if seed == "lead":
        nodes = [
            {"id": "n1", "kind": "trigger", "label": "Contact Created", "connector": "hubspot", "status": "success"},
            {"id": "n2", "kind": "action", "label": "Enrich with GitHub", "connector": "github", "action": "Enrich Profile", "status": "success"},
            {"id": "n3", "kind": "condition", "label": "Is Enterprise?", "status": "success"},
            {"id": "n4", "kind": "action", "label": "Add to Airtable", "connector": "airtable", "action": "Create Record", "status": "success"},
            {"id": "n5", "kind": "action", "label": "Notify Slack", "connector": "slack", "action": "Post Message", "status": "success"},
        ]
        edges = [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n3"},
            {"id": "e3", "source": "n3", "target": "n4", "label": "yes"},
            {"id": "e4", "source": "n4", "target": "n5"},
        ]
    elif seed == "report":
        nodes = [
            {"id": "n1", "kind": "trigger", "label": "Every Monday 9am", "status": "success"},
            {"id": "n2", "kind": "action", "label": "Fetch Payments", "connector": "stripe", "action": "List Charges", "status": "success"},
            {"id": "n3", "kind": "ai", "label": "Summarize Revenue", "status": "success"},
            {"id": "n4", "kind": "action", "label": "Email Digest", "connector": "gmail", "action": "Send Email", "status": "success"},
        ]
        edges = [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n3"},
            {"id": "e3", "source": "n3", "target": "n4"},
        ]
    elif seed == "triage":
        nodes = [
            {"id": "n1", "kind": "trigger", "label": "New Email", "connector": "gmail", "status": "success"},
            {"id": "n2", "kind": "ai", "label": "Classify Intent", "status": "success"},
            {"id": "n3", "kind": "condition", "label": "Urgent?", "status": "success"},
            {"id": "n4", "kind": "action", "label": "Alert Support", "connector": "slack", "action": "Post Message", "status": "running"},
        ]
        edges = [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n3"},
            {"id": "e3", "source": "n3", "target": "n4", "label": "yes"},
        ]
    elif seed == "deploy":
        nodes = [
            {"id": "n1", "kind": "trigger", "label": "PR Merged", "connector": "github"},
            {"id": "n2", "kind": "action", "label": "Announce Deploy", "connector": "discord", "action": "Send Message"},
        ]
        edges = [{"id": "e1", "source": "n1", "target": "n2"}]
    elif seed == "inventory":
        nodes = [
            {"id": "n1", "kind": "trigger", "label": "Every night 2am", "status": "success"},
            {"id": "n2", "kind": "action", "label": "Fetch Products", "connector": "shopify", "action": "List Products", "status": "success"},
            {"id": "n3", "kind": "action", "label": "Sync to Postgres", "connector": "postgres", "action": "Run Query", "status": "success"},
        ]
        edges = [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n3"},
        ]
    else:  # onboarding
        nodes = [
            {"id": "n1", "kind": "trigger", "label": "Customer Created", "connector": "stripe", "status": "success"},
            {"id": "n2", "kind": "condition", "label": "Plan is Pro?", "status": "success"},
            {"id": "n3", "kind": "action", "label": "Send Welcome", "connector": "gmail", "action": "Send Email", "status": "success"},
            {"id": "n4", "kind": "action", "label": "Log to Notion", "connector": "notion", "action": "Add DB Row", "status": "success"},
        ]
        edges = [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n3", "label": "yes"},
            {"id": "e3", "source": "n3", "target": "n4"},
        ]
    return nodes, edges


def _workflows(org_id, now):
    def cfg(name, description, status, trigger, connector_ids, runs, success_rate, avg_duration, last_run, favorite, tags, seed, error_count, version):
        nodes, edges = _workflow_nodes(seed)
        config = {
            "trigger": trigger, "connectorIds": connector_ids,
            "runs": runs, "successRate": success_rate, "avgDurationMs": avg_duration,
            "favorite": favorite, "tags": tags, "nodes": nodes, "edges": edges,
        }
        if last_run is not None:
            config["lastRunAt"] = last_run.isoformat()
        return {
            "organization_id": org_id, "name": name, "description": description,
            "status": status, "version": version, "config": config,
            "error_count": error_count, "last_run_at": last_run,
        }

    return [
        cfg(
            "Lead Intelligence Pipeline",
            "Enrich new HubSpot contacts with GitHub activity and file them in Airtable.",
            WorkflowStatus.ACTIVE, "contact_created", ["hubspot", "github", "airtable"],
            1284, 98.2, 4200, _mins(4, now), True, ["sales", "crm"], "lead", 12, 14,
        ),
        cfg(
            "Weekly Revenue Digest",
            "Aggregate Stripe payments and email a revenue summary every Monday.",
            WorkflowStatus.ACTIVE, "cron", ["stripe", "gmail"],
            42, 100.0, 5800, _days(2, now), True, ["finance", "reporting"], "report", 0, 6,
        ),
        cfg(
            "Support Ticket Triage",
            "Classify incoming support emails and route to the right Slack channel.",
            WorkflowStatus.ACTIVE, "new_email", ["gmail", "slack"],
            3561, 96.4, 2600, _mins(1, now), False, ["support"], "triage", 28, 9,
        ),
        cfg(
            "Deploy Notifications",
            "Watch GitHub PR merges and announce deployments in Discord.",
            WorkflowStatus.DRAFT, "pr_merged", ["github", "discord"],
            0, 0.0, 0, None, False, ["devops"], "deploy", 0, 1,
        ),
        cfg(
            "Inventory Sync",
            "Keep Shopify inventory in sync with the Postgres warehouse nightly.",
            WorkflowStatus.PAUSED, "cron", ["shopify", "postgres"],
            96, 99.1, 12400, _days(4, now), False, ["ecommerce"], "inventory", 3, 4,
        ),
        cfg(
            "Customer Onboarding",
            "Send a welcome sequence when a new customer is created in Stripe.",
            WorkflowStatus.ACTIVE, "customer_created", ["stripe", "gmail", "notion"],
            512, 99.8, 1900, _mins(22, now), True, ["growth"], "onboarding", 1, 11,
        ),
    ]


def _executions(org_id, user_id, workflows, now):
    by_name = {w.name: w for w in workflows}

    def wf(name):
        return str(by_name[name].id)

    return [
        {"workflow_id": wf("Support Ticket Triage"), "triggered_by": user_id, "status": ExecutionStatus.RUNNING,
         "trigger_type": "webhook", "input_data": {}, "output_data": {}, "error_message": "",
         "started_at": _mins(0.4, now), "completed_at": None, "duration_ms": None,
         "retry_attempt": 0, "cost": 0.02, "organization_id": org_id},
        {"workflow_id": wf("Lead Intelligence Pipeline"), "triggered_by": user_id, "status": ExecutionStatus.COMPLETED,
         "trigger_type": "webhook", "input_data": {}, "output_data": {}, "error_message": "",
         "started_at": _mins(4, now), "completed_at": _mins(3.9, now), "duration_ms": 4120,
         "retry_attempt": 0, "cost": 0.14, "organization_id": org_id},
        {"workflow_id": wf("Customer Onboarding"), "triggered_by": user_id, "status": ExecutionStatus.COMPLETED,
         "trigger_type": "webhook", "input_data": {}, "output_data": {}, "error_message": "",
         "started_at": _mins(22, now), "completed_at": _mins(21.9, now), "duration_ms": 1930,
         "retry_attempt": 0, "cost": 0.04, "organization_id": org_id},
        {"workflow_id": wf("Support Ticket Triage"), "triggered_by": user_id, "status": ExecutionStatus.RETRYING,
         "trigger_type": "webhook", "input_data": {}, "output_data": {}, "error_message": "Rate limit exceeded on slack:post_message (429)",
         "started_at": _hours(1.1, now), "completed_at": None, "duration_ms": None,
         "retry_attempt": 2, "cost": 0.05, "organization_id": org_id},
        {"workflow_id": wf("Lead Intelligence Pipeline"), "triggered_by": user_id, "status": ExecutionStatus.FAILED,
         "trigger_type": "webhook", "input_data": {}, "output_data": {}, "error_message": "Rate limit exceeded on github:enrich_profile (429)",
         "started_at": _hours(2.3, now), "completed_at": _hours(2.2, now), "duration_ms": 8900,
         "retry_attempt": 3, "cost": 0.22, "organization_id": org_id},
        {"workflow_id": wf("Weekly Revenue Digest"), "triggered_by": user_id, "status": ExecutionStatus.COMPLETED,
         "trigger_type": "cron", "input_data": {}, "output_data": {}, "error_message": "",
         "started_at": _days(2, now), "completed_at": _days(2, now), "duration_ms": 5810,
         "retry_attempt": 0, "cost": 0.09, "organization_id": org_id},
        {"workflow_id": wf("Inventory Sync"), "triggered_by": user_id, "status": ExecutionStatus.FAILED,
         "trigger_type": "cron", "input_data": {}, "output_data": {}, "error_message": "Constraint violation on postgres:insert_row",
         "started_at": _days(4, now), "completed_at": _days(4, now), "duration_ms": 15400,
         "retry_attempt": 2, "cost": 0.31, "organization_id": org_id},
        {"workflow_id": wf("Customer Onboarding"), "triggered_by": user_id, "status": ExecutionStatus.COMPLETED,
         "trigger_type": "webhook", "input_data": {}, "output_data": {}, "error_message": "",
         "started_at": _hours(6, now), "completed_at": _hours(6, now), "duration_ms": 1810,
         "retry_attempt": 0, "cost": 0.04, "organization_id": org_id},
        {"workflow_id": wf("Lead Intelligence Pipeline"), "triggered_by": user_id, "status": ExecutionStatus.COMPLETED,
         "trigger_type": "webhook", "input_data": {}, "output_data": {}, "error_message": "",
         "started_at": _hours(9, now), "completed_at": _hours(9, now), "duration_ms": 3980,
         "retry_attempt": 0, "cost": 0.13, "organization_id": org_id},
        {"workflow_id": wf("Support Ticket Triage"), "triggered_by": user_id, "status": ExecutionStatus.PENDING,
         "trigger_type": "webhook", "input_data": {}, "output_data": {}, "error_message": "",
         "started_at": _hours(12, now), "completed_at": None, "duration_ms": None,
         "retry_attempt": 0, "cost": 0.0, "organization_id": org_id},
        {"workflow_id": wf("Weekly Revenue Digest"), "triggered_by": user_id, "status": ExecutionStatus.COMPLETED,
         "trigger_type": "cron", "input_data": {}, "output_data": {}, "error_message": "",
         "started_at": _days(9, now), "completed_at": _days(9, now), "duration_ms": 5740,
         "retry_attempt": 0, "cost": 0.09, "organization_id": org_id},
        {"workflow_id": wf("Inventory Sync"), "triggered_by": user_id, "status": ExecutionStatus.TIMEOUT,
         "trigger_type": "cron", "input_data": {}, "output_data": {}, "error_message": "Execution timed out after 60s",
         "started_at": _days(6, now), "completed_at": _days(6, now), "duration_ms": 60000,
         "retry_attempt": 1, "cost": 0.5, "organization_id": org_id},
        {"workflow_id": wf("Lead Intelligence Pipeline"), "triggered_by": user_id, "status": ExecutionStatus.PAUSED,
         "trigger_type": "manual", "input_data": {}, "output_data": {}, "error_message": "",
         "started_at": _days(11, now), "completed_at": None, "duration_ms": None,
         "retry_attempt": 0, "cost": 0.03, "organization_id": org_id},
        {"workflow_id": wf("Customer Onboarding"), "triggered_by": user_id, "status": ExecutionStatus.COMPLETED,
         "trigger_type": "webhook", "input_data": {}, "output_data": {}, "error_message": "",
         "started_at": _days(3, now), "completed_at": _days(3, now), "duration_ms": 1760,
         "retry_attempt": 0, "cost": 0.03, "organization_id": org_id},
        {"workflow_id": wf("Support Ticket Triage"), "triggered_by": user_id, "status": ExecutionStatus.CANCELLED,
         "trigger_type": "webhook", "input_data": {}, "output_data": {}, "error_message": "Cancelled by operator",
         "started_at": _days(5, now), "completed_at": _days(5, now), "duration_ms": 2400,
         "retry_attempt": 0, "cost": 0.04, "organization_id": org_id},
    ]

# ---------------------------------------------------------------------------
# Seeding logic
# ---------------------------------------------------------------------------


async def _delete_seeded(session, demo_email, org_slug):
    """Hard-delete previously seeded data (idempotent reset)."""
    users = UserRepository(session)
    orgs = OrganizationRepository(session)
    items_repo = MarketplaceItemRepository(session)

    user = await users.get_by_field("email", demo_email)
    if user is not None:
        await users.delete(user.id, hard=True)

    org = await orgs.get_by_field("slug", org_slug)
    if org is not None:
        existing = await items_repo.list(page=1, page_size=100)
        for item in existing.items:
            await items_repo.delete(item.id, hard=True)
        await orgs.delete(org.id, hard=True)

    await session.commit()


async def _run(args):
    await init_db()
    async with async_session_factory() as session:
        users = UserRepository(session)
        orgs = OrganizationRepository(session)
        items_repo = MarketplaceItemRepository(session)

        demo_email = args.email
        org_slug = "acme-corp"

        if args.reset:
            print(f"  reset: removing seeded data for {demo_email} / {org_slug}")
            await _delete_seeded(session, demo_email, org_slug)

        existing = await users.get_by_field("email", demo_email)
        if existing is not None:
            print("  seed: demo user already exists, skipping (use --reset to re-seed)")
            return

        now = datetime.now(timezone.utc)

        # --- user -----------------------------------------------------------
        user = await users.create({
            "email": demo_email,
            "password_hash": hash_password(args.password),
            "full_name": args.name,
            "avatar_url": "",
            "status": UserStatus.ACTIVE,
            "is_superuser": True,
            "is_verified": True,
        })
        print(f"  + user      {user.email}  (password: {args.password})")

        # --- organization + owner membership --------------------------------
        org = await orgs.create({
            "name": "Acme Corp", "slug": org_slug,
            "description": "Demo workspace seeded for AutoFlow AI",
            "is_active": True, "tier": "pro",
            "settings": {"notifications": {"failures": True, "digest": True}},
        })
        from app.models.organization_member import OrganizationMember
        from app.repositories.base import BaseRepository as _MemberBase

        class _MemberRepo(_MemberBase):
            def _get_model_class(self):
                return OrganizationMember

        await _MemberRepo(session).create({
            "organization_id": org.id,
            "user_id": user.id,
            "role": OrganizationMemberRole.OWNER,
            "joined_at": now,
        })
        print(f"  + org       {org.name} ({org.slug})")

        # --- marketplace items ----------------------------------------------
        for item in MARKETPLACE_SPECS:
            await items_repo.create({
                "author_id": user.id,
                "name": item["name"], "slug": item["slug"],
                "description": item["description"], "category": item["category"],
                "type": "connector", "config": item["config"],
                "version": "1.0.0", "is_verified": True,
                "is_paid": False, "price": 0.0,
                "rating": item["rating"], "download_count": item["download_count"],
            })
        print(f"  + market   {len(MARKETPLACE_SPECS)} connector items")

        # --- workflows -------------------------------------------------------
        from app.repositories.workflow import WorkflowRepository

        workflows_repo = WorkflowRepository(session)
        workflow_rows = []
        for data in _workflows(org.id, now):
            wf = await workflows_repo.create(data)
            workflow_rows.append(wf)
        print(f"  + workflow {len(workflow_rows)} workflows")

        # --- executions ------------------------------------------------------
        exec_repo = ExecutionRepository(session)
        rows = _executions(org.id, user.id, workflow_rows, now)
        for data in rows:
            await exec_repo.create(data)
        print(f"  + exec     {len(rows)} executions")

        # --- api keys --------------------------------------------------------
        from app.models.api_key import APIKey
        from app.repositories.base import BaseRepository as _KeyBase

        class _KeyRepo(_KeyBase):
            def _get_model_class(self):
                return APIKey

        prefix = f"af_{secrets.token_hex(8)}"
        await _KeyRepo(session).create({
            "user_id": user.id, "organization_id": org.id,
            "name": "Production", "key_prefix": prefix,
            "key_hash": hashlib.sha256(f"{prefix}.{secrets.token_hex(16)}".encode()).hexdigest(),
            "scopes": {"workflows": ["read", "write"], "executions": ["read"]},
            "is_active": True, "last_used_at": _mins(5, now),
        })
        print(f"  + api_key  1 key (prefix {prefix}...)")

        # --- audit logs ------------------------------------------------------
        audit_repo = AuditLogRepository(session)
        for action, resource in [
            ("workflow.deployed", "Workflow"),
            ("connector.connected", "MarketplaceItem"),
            ("execution.completed", "Execution"),
            ("user.invited", "User"),
            ("workflow.paused", "Workflow"),
        ]:
            await audit_repo.create({
                "user_id": user.id, "organization_id": org.id,
                "action": action, "resource_type": resource,
                "resource_id": str(uuid4()), "detail": {"seed": True},
                "ip_address": "127.0.0.1", "user_agent": "autoflow-seed",
            })
        print("  + audit     5 audit log entries")

        # --- notifications + team --------------------------------------------
        notif_repo = NotificationRepository(session)
        for title, message, kind in [
            ("Support Ticket Triage failed", "2 retries exhausted · slack:post_message rate limited", "alert"),
            ("Weekly Revenue Digest sent", "$12,480 MRR summarized and emailed", "info"),
            ("New connector available", "HubSpot is now in the marketplace", "info"),
        ]:
            await notif_repo.create({
                "user_id": user.id, "title": title, "message": message,
                "type": kind, "channel": "in_app", "is_read": False, "payload": {},
            })
        print("  + notif     3 notifications")

        team_repo = TeamRepository(session)
        team = await team_repo.create({
            "organization_id": org.id,
            "name": "Platform", "description": "Core automation platform team",
        })
        from app.models.team_member import TeamMember
        from app.repositories.base import BaseRepository as _TMemberBase

        class _TMemberRepo(_TMemberBase):
            def _get_model_class(self):
                return TeamMember

        await _TMemberRepo(session).create({
            "team_id": team.id, "user_id": user.id, "role": "owner",
        })
        print("  + team      1 team (Platform)")

        await session.commit()

    print()
    print("Seed complete.")
    print(f"  Demo login  : {args.email} / {args.password}")
    print("  API base    : http://localhost:8000/api/v1")


def main():
    parser = argparse.ArgumentParser(description="Seed AutoFlow AI with demo data")
    parser.add_argument("--reset", action="store_true", help="Remove seeded data before re-seeding")
    parser.add_argument("--email", default="demo@autoflow.ai", help="Demo user email")
    parser.add_argument("--password", default="Autoflow123!", help="Demo user password")
    parser.add_argument("--name", default="Ava Torres", help="Demo user full name")
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
