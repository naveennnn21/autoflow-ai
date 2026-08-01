"""AutoFlow AI - Confluence connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Confluence', 'version': '1.0.0', 'description': 'Confluence pages and spaces', 'category': 'productivity', 'provider': 'atlassian', 'module_name': 'confluence', 'authentication': {'type': 'oauth2', 'provider': 'atlassian', 'supported_scopes': ['read:confluence-space.summary', 'write:confluence-content', 'read:confluence-content.all', 'offline_access'], 'token_url': 'https://auth.atlassian.com/oauth/token', 'auth_url': 'https://auth.atlassian.com/authorize', 'requires_refresh': True, 'credential_fields': ['client_id', 'client_secret', 'access_token', 'refresh_token']}, 'actions': {'create_page': {'description': 'Create a Confluence page', 'kind': 'create', 'inputs': {'space_key': 'string', 'title': 'string', 'body': 'text', 'parent_page_id': 'string'}, 'outputs': {'page_id': 'string', 'page_url': 'string'}, 'required_permissions': ['write:confluence-content'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'update_page': {'description': 'Update a Confluence page', 'kind': 'update', 'inputs': {'page_id': 'string', 'title': 'string', 'body': 'text', 'version': 'integer'}, 'outputs': {'page_id': 'string'}, 'required_permissions': ['write:confluence-content'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'get_page': {'description': 'Fetch a Confluence page', 'kind': 'read', 'inputs': {'page_id': 'string'}, 'outputs': {'page': 'object'}, 'required_permissions': ['read:confluence-content.all'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'search_pages': {'description': 'Search pages with CQL', 'kind': 'search', 'inputs': {'cql': 'string', 'limit': 'integer'}, 'outputs': {'pages': 'list'}, 'required_permissions': ['read:confluence-content.all'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_spaces': {'description': 'List accessible spaces', 'kind': 'list', 'inputs': {'limit': 'integer'}, 'outputs': {'spaces': 'list'}, 'required_permissions': ['read:confluence-space.summary'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'page_created': {'description': 'Triggered when a page is created', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['confluence.page_created']}, 'page_updated': {'description': 'Triggered when a page is updated', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['confluence.page_updated']}}, 'rate_limits': {'default': '1000/minute', 'rules': {'search_pages': '60/minute', 'create_page': '60/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 2.0, 'max_delay': 120.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': True, 'default_interval_seconds': 300}, 'webhooks': {'enabled': False, 'events': ['confluence.page_updated'], 'secret_required': False}, 'supported_events': ['confluence.page_created', 'confluence.page_updated'], 'supported_objects': ['page', 'space', 'attachment'], 'pagination': {'enabled': True, 'default_page_size': 25, 'max_page_size': 200, 'cursor_field': 'next'}, 'batching': {'enabled': False, 'max_batch_size': 50}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': True, 'webhooks': False, 'batching': False, 'streaming': False, 'pagination': True, 'file_upload': True, 'file_download': True, 'long_running': False}, 'permissions': {'read': ['read:confluence-content.all'], 'write': ['write:confluence-content']}, 'health_check': {'endpoint': 'https://{site}.atlassian.net/wiki/rest/api/content', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://developer.atlassian.com/cloud/confluence', 'setup_guide': 'Create a Confluence Cloud app with OAuth 2.0 and content scopes.', 'example_prompt': 'Publish release notes to the Confluence wiki'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class ConfluenceConnector(BaseConnector):
    """Confluence (atlassian) connector implementation."""

    name = "Confluence"
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
