"""AutoFlow AI - Few-shot examples (generated from metadata).

Loads the example library from metadata/ai/examples.yaml at generation
time (embedded in the module) and exposes lookup helpers used by the
context builder and tests.
"""

from typing import Any, Dict, List, Optional

_EXAMPLES: List[Dict[str, Any]] = []


def set_examples(examples: List[Dict[str, Any]]) -> None:
    """Set the example library (called by the generator)."""
    global _EXAMPLES
    _EXAMPLES = list(examples)


def get_examples() -> List[Dict[str, Any]]:
    return list(_EXAMPLES)


def find_by_prompt_keyword(keyword: str) -> List[Dict[str, Any]]:
    """Return examples whose prompt mentions a keyword."""
    return [e for e in _EXAMPLES
            if keyword.lower() in e.get("prompt", "").lower()]


def all_prompts() -> List[str]:
    return [e.get("prompt", "") for e in _EXAMPLES]


set_examples([{'id': 'sync_notion_to_google_drive', 'prompt': 'When I add a page to my Notion database, save a copy to Google Drive', 'intent': 'automation', 'trigger': {'connector': 'notion', 'type': 'database_page_created'}, 'steps': [{'connector': 'google_drive', 'action': 'upload_file', 'inputs': {}}], 'warnings': []}, {'id': 'daily_slack_digest', 'prompt': 'Every morning at 9am, send me a summary of new GitHub issues to Slack', 'intent': 'automation', 'trigger': {'connector': 'github', 'type': 'schedule'}, 'steps': [{'connector': 'github', 'action': 'list_issues', 'inputs': {}}, {'connector': 'slack', 'action': 'send_message', 'inputs': {}}], 'warnings': ['Scheduling requires a cron trigger; asked to confirm timezone']}, {'id': 'stripe_refund_notification', 'prompt': 'When a Stripe refund is issued, notify the finance team on Discord', 'intent': 'automation', 'trigger': {'connector': 'stripe', 'type': 'refund_created'}, 'steps': [{'connector': 'discord', 'action': 'send_message', 'inputs': {}}], 'warnings': []}, {'id': 'weekly_report', 'prompt': 'Generate a weekly sales report and email it', 'intent': 'automation', 'trigger': {'connector': 'system', 'type': 'schedule'}, 'steps': [{'connector': 'shopify', 'action': 'list_orders', 'inputs': {}}, {'connector': 'gmail', 'action': 'send_email', 'inputs': {}}], 'warnings': ['Recipient address not specified; clarification required']}])
