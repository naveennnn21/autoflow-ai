"""AutoFlow AI - Idempotent connector marketplace seed.

Seeds the connector catalog (marketplace_items) with legitimate connector
metadata.  Safe to run multiple times — duplicate slugs are skipped.

Usage:
    python -m app.seed_connectors          # seed connectors
    python -m app.seed_connectors --dry-run # preview without writing
"""

import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_factory, init_db
from app.models.marketplace_item import MarketplaceItem
from app.repositories.marketplace_item import MarketplaceItemRepository

# ---------------------------------------------------------------------------
# Connector catalog — metadata only, no credentials or connection status.
# ---------------------------------------------------------------------------

CONNECTORS = [
    {
        "name": "Slack",
        "slug": "slack",
        "category": "Communication",
        "description": "Send messages, create channels, and manage workspace notifications via Slack API.",
        "config": {
            "logo": "message-square",
            "color": "#4A154B",
            "auth": "oauth2",
            "scopes": ["chat:write", "channels:read"],
            "actions": [
                {"id": "post_message", "name": "Post Message", "description": "Send a message to a channel", "kind": "write",
                 "inputs": [{"name": "channel", "type": "string", "required": True}, {"name": "text", "type": "string", "required": True}],
                 "outputs": [{"name": "ts", "type": "string"}]},
                {"id": "create_channel", "name": "Create Channel", "description": "Create a new channel", "kind": "write",
                 "inputs": [{"name": "name", "type": "string", "required": True}],
                 "outputs": [{"name": "channel_id", "type": "string"}]},
            ],
            "triggers": [
                {"id": "new_message", "name": "New Message", "description": "Triggered when a message is posted", "kind": "webhook"},
            ],
            "health": "healthy",
            "rateLimit": "1 msg/sec",
            "popular": True,
            "tags": ["messaging", "notifications"],
        },
        "version": "1.0.0",
        "rating": 4.8,
        "download_count": 15420,
        "is_verified": True,
    },
    {
        "name": "GitHub",
        "slug": "github",
        "category": "Development",
        "description": "Manage repositories, pull requests, issues, and CI/CD workflows on GitHub.",
        "config": {
            "logo": "git-branch",
            "color": "#333333",
            "auth": "oauth2",
            "scopes": ["repo", "read:org"],
            "actions": [
                {"id": "create_issue", "name": "Create Issue", "description": "Create a new issue", "kind": "write",
                 "inputs": [{"name": "repo", "type": "string", "required": True}, {"name": "title", "type": "string", "required": True}],
                 "outputs": [{"name": "issue_number", "type": "integer"}]},
                {"id": "list_repos", "name": "List Repositories", "description": "List repositories for an organization", "kind": "read",
                 "inputs": [{"name": "org", "type": "string", "required": False}],
                 "outputs": [{"name": "repos", "type": "array"}]},
            ],
            "triggers": [
                {"id": "push", "name": "Push", "description": "Triggered on git push", "kind": "webhook"},
                {"id": "pr_opened", "name": "PR Opened", "description": "Triggered when a pull request is opened", "kind": "webhook"},
            ],
            "health": "healthy",
            "rateLimit": "5000 req/hr",
            "popular": True,
            "tags": ["development", "git", "code"],
        },
        "version": "1.0.0",
        "rating": 4.9,
        "download_count": 22100,
        "is_verified": True,
    },
    {
        "name": "Stripe",
        "slug": "stripe",
        "category": "Payments",
        "description": "Process payments, manage subscriptions, and handle invoicing with Stripe.",
        "config": {
            "logo": "credit-card",
            "color": "#635BFF",
            "auth": "api_key",
            "scopes": ["charges", "subscriptions"],
            "actions": [
                {"id": "create_charge", "name": "Create Charge", "description": "Create a payment charge", "kind": "write",
                 "inputs": [{"name": "amount", "type": "integer", "required": True}, {"name": "currency", "type": "string", "required": True}],
                 "outputs": [{"name": "charge_id", "type": "string"}]},
                {"id": "list_customers", "name": "List Customers", "description": "List all customers", "kind": "read",
                 "inputs": [], "outputs": [{"name": "customers", "type": "array"}]},
            ],
            "triggers": [
                {"id": "payment_intent", "name": "Payment Intent", "description": "Triggered on payment intent events", "kind": "webhook"},
                {"id": "invoice_paid", "name": "Invoice Paid", "description": "Triggered when an invoice is paid", "kind": "webhook"},
            ],
            "health": "healthy",
            "rateLimit": "100 req/sec",
            "popular": True,
            "tags": ["payments", "billing", "subscriptions"],
        },
        "version": "1.0.0",
        "rating": 4.7,
        "download_count": 18300,
        "is_verified": True,
    },
    {
        "name": "Gmail",
        "slug": "gmail",
        "category": "Communication",
        "description": "Send, read, and manage emails through the Gmail API.",
        "config": {
            "logo": "mail",
            "color": "#EA4335",
            "auth": "oauth2",
            "scopes": ["gmail.send", "gmail.readonly"],
            "actions": [
                {"id": "send_email", "name": "Send Email", "description": "Send an email message", "kind": "write",
                 "inputs": [{"name": "to", "type": "string", "required": True}, {"name": "subject", "type": "string", "required": True}, {"name": "body", "type": "string", "required": True}],
                 "outputs": [{"name": "message_id", "type": "string"}]},
            ],
            "triggers": [
                {"id": "new_email", "name": "New Email", "description": "Triggered when a new email arrives", "kind": "webhook"},
            ],
            "health": "healthy",
            "rateLimit": "250 req/day",
            "popular": True,
            "tags": ["email", "communication"],
        },
        "version": "1.0.0",
        "rating": 4.5,
        "download_count": 12800,
        "is_verified": True,
    },
    {
        "name": "Airtable",
        "slug": "airtable",
        "category": "Data",
        "description": "Read and write records in Airtable bases and tables.",
        "config": {
            "logo": "database",
            "color": "#18BFFF",
            "auth": "api_key",
            "scopes": ["data.records:read", "data.records:write"],
            "actions": [
                {"id": "create_record", "name": "Create Record", "description": "Add a record to a table", "kind": "write",
                 "inputs": [{"name": "base_id", "type": "string", "required": True}, {"name": "table_id", "type": "string", "required": True}, {"name": "fields", "type": "object", "required": True}],
                 "outputs": [{"name": "record_id", "type": "string"}]},
                {"id": "list_records", "name": "List Records", "description": "List records from a table", "kind": "read",
                 "inputs": [{"name": "base_id", "type": "string", "required": True}, {"name": "table_id", "type": "string", "required": True}],
                 "outputs": [{"name": "records", "type": "array"}]},
            ],
            "triggers": [
                {"id": "record_created", "name": "Record Created", "description": "Triggered when a record is created", "kind": "webhook"},
            ],
            "health": "healthy",
            "rateLimit": "5 req/sec",
            "popular": False,
            "tags": ["database", "spreadsheet"],
        },
        "version": "1.0.0",
        "rating": 4.3,
        "download_count": 8900,
        "is_verified": True,
    },
    {
        "name": "Discord",
        "slug": "discord",
        "category": "Communication",
        "description": "Send messages, manage channels, and interact with Discord servers.",
        "config": {
            "logo": "message-circle",
            "color": "#5865F2",
            "auth": "bot_token",
            "scopes": ["send_messages"],
            "actions": [
                {"id": "send_message", "name": "Send Message", "description": "Send a message to a channel", "kind": "write",
                 "inputs": [{"name": "channel_id", "type": "string", "required": True}, {"name": "content", "type": "string", "required": True}],
                 "outputs": [{"name": "message_id", "type": "string"}]},
            ],
            "triggers": [
                {"id": "new_message", "name": "New Message", "description": "Triggered when a message is sent", "kind": "webhook"},
            ],
            "health": "healthy",
            "rateLimit": "50 msg/sec",
            "popular": False,
            "tags": ["messaging", "gaming"],
        },
        "version": "1.0.0",
        "rating": 4.6,
        "download_count": 7200,
        "is_verified": True,
    },
    {
        "name": "Webhook",
        "slug": "webhook",
        "category": "Integration",
        "description": "Receive incoming HTTP webhooks and trigger workflows.",
        "config": {
            "logo": "webhook",
            "color": "#6366f1",
            "auth": "none",
            "scopes": [],
            "actions": [],
            "triggers": [
                {"id": "receive", "name": "Receive Webhook", "description": "Triggered when an HTTP POST is received", "kind": "webhook"},
            ],
            "health": "healthy",
            "rateLimit": "—",
            "popular": True,
            "tags": ["webhook", "http", "integration"],
        },
        "version": "1.0.0",
        "rating": 4.4,
        "download_count": 25000,
        "is_verified": True,
    },
    {
        "name": "HTTP Request",
        "slug": "http",
        "category": "Integration",
        "description": "Make arbitrary HTTP requests to any REST API endpoint.",
        "config": {
            "logo": "globe",
            "color": "#10b981",
            "auth": "none",
            "scopes": [],
            "actions": [
                {"id": "request", "name": "Make Request", "description": "Send an HTTP request", "kind": "write",
                 "inputs": [{"name": "url", "type": "string", "required": True}, {"name": "method", "type": "string", "required": True}, {"name": "body", "type": "object", "required": False}],
                 "outputs": [{"name": "status", "type": "integer"}, {"name": "body", "type": "object"}]},
            ],
            "triggers": [],
            "health": "healthy",
            "rateLimit": "—",
            "popular": False,
            "tags": ["http", "rest", "api"],
        },
        "version": "1.0.0",
        "rating": 4.2,
        "download_count": 9500,
        "is_verified": True,
    },
]


async def seed(dry_run: bool = False) -> int:
    """Seed connector marketplace items. Returns count of new items added."""
    await init_db()
    async with async_session_factory() as session:
        repo = MarketplaceItemRepository(session)
        added = 0
        for spec in CONNECTORS:
            existing = await repo.get_by_field("slug", spec["slug"])
            if existing is not None:
                continue
            if dry_run:
                print(f"  [dry-run] Would add: {spec['name']} ({spec['slug']})")
                continue
            await repo.create({
                "name": spec["name"],
                "slug": spec["slug"],
                "description": spec["description"],
                "category": spec["category"],
                "type": "connector",
                "config": spec["config"],
                "version": spec["version"],
                "is_verified": spec["is_verified"],
                "rating": spec["rating"],
                "download_count": spec["download_count"],
            })
            added += 1
            print(f"  + {spec['name']} ({spec['slug']})")
        if not dry_run:
            await session.commit()
        return added


def main():
    parser = argparse.ArgumentParser(description="Seed connector marketplace data")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    added = asyncio.run(seed(dry_run=args.dry_run))
    if args.dry_run:
        print("Dry run complete.")
    else:
        print(f"Seeded {added} new connector(s).")


if __name__ == "__main__":
    main()
