"""AutoFlow AI - Outlook connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Outlook', 'version': '1.0.0', 'description': 'Microsoft Outlook email and calendar integration', 'category': 'email', 'provider': 'microsoft', 'module_name': 'outlook', 'authentication': {'type': 'oauth2', 'provider': 'microsoft', 'supported_scopes': ['Mail.ReadWrite', 'Mail.Send', 'Calendars.ReadWrite', 'offline_access'], 'token_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/token', 'auth_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize', 'requires_refresh': True, 'credential_fields': ['client_id', 'client_secret', 'access_token', 'refresh_token']}, 'actions': {'send_email': {'description': 'Send an email via Microsoft Graph', 'kind': 'create', 'inputs': {'to': 'string', 'cc': 'string', 'bcc': 'string', 'subject': 'string', 'body': 'text', 'importance': 'string'}, 'outputs': {'message_id': 'string'}, 'required_permissions': ['Mail.Send'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'search_emails': {'description': 'Search mailbox messages', 'kind': 'search', 'inputs': {'query': 'string', 'top': 'integer'}, 'outputs': {'messages': 'list'}, 'required_permissions': ['Mail.Read'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'create_event': {'description': 'Create a calendar event', 'kind': 'create', 'inputs': {'subject': 'string', 'start_time': 'datetime', 'end_time': 'datetime', 'attendees': 'list', 'body': 'text'}, 'outputs': {'event_id': 'string'}, 'required_permissions': ['Calendars.ReadWrite'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_events': {'description': 'List calendar events', 'kind': 'list', 'inputs': {'start_time': 'datetime', 'end_time': 'datetime', 'top': 'integer'}, 'outputs': {'events': 'list'}, 'required_permissions': ['Calendars.Read'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'get_message': {'description': 'Fetch a message by id', 'kind': 'read', 'inputs': {'message_id': 'string'}, 'outputs': {'message': 'object'}, 'required_permissions': ['Mail.Read'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'new_email': {'description': 'Triggered when a new email arrives', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 120, 'cron': '', 'supported_events': ['outlook.email_received']}, 'event_created': {'description': 'Triggered when a calendar event is created', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['outlook.event_created']}}, 'rate_limits': {'default': '1000/hour', 'rules': {'send_email': '100/hour', 'search_emails': '250/hour'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 2.0, 'max_delay': 120.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': True, 'default_interval_seconds': 120}, 'webhooks': {'enabled': False, 'events': ['outlook.email_received'], 'secret_required': False}, 'supported_events': ['outlook.email_received', 'outlook.event_created'], 'supported_objects': ['message', 'event', 'contact'], 'pagination': {'enabled': True, 'default_page_size': 50, 'max_page_size': 1000, 'cursor_field': 'nextLink'}, 'batching': {'enabled': False, 'max_batch_size': 50}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': True, 'webhooks': False, 'batching': False, 'streaming': False, 'pagination': True, 'file_upload': True, 'file_download': True, 'long_running': False}, 'permissions': {'read': ['Mail.Read', 'Calendars.Read'], 'write': ['Mail.Send', 'Mail.ReadWrite', 'Calendars.ReadWrite']}, 'health_check': {'endpoint': 'https://graph.microsoft.com/v1.0/me', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://learn.microsoft.com/graph', 'setup_guide': 'Register an Azure app, grant Microsoft Graph delegated permissions, and configure OAuth redirect URIs.', 'example_prompt': 'Send a calendar invite for the next team sync'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class OutlookConnector(BaseConnector):
    """Outlook (microsoft) connector implementation."""

    name = "Outlook"
    version = "1.0.0"
    metadata = CONNECTOR_METADATA

    def execute_action(self, action: str, inputs: Dict[str, Any],
                       context: Optional[dict] = None) -> ActionResponse:
        """Execute an action against the provider API."""
        action_def = self._check_action(action)
        kind = action_def.get("kind", "run")
        try:
            method, path = self._endpoint_for(action, inputs or {})
            response = self._transport_request(
                method, path, json_body=dict(inputs or {}))
            data = response if isinstance(response, dict) else {"result": response}
            return ActionResponse(ok=True, data=data,
                                  connector=self.name, action=action)
        except Exception as exc:  # noqa: BLE001 - converted to response
            return ActionResponse(ok=False, error=str(exc),
                                  status_code=500,
                                  connector=self.name, action=action)

    def poll(self, trigger: str,
             context: Optional[dict] = None) -> List[TriggerEvent]:
        """Collect new polling events (provider-specific fetch)."""
        return super().poll(trigger, context=context)
