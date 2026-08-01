"""AutoFlow AI - Notion connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Notion', 'version': '1.0.0', 'description': 'Notion pages and databases', 'category': 'productivity', 'provider': 'notion', 'module_name': 'notion', 'authentication': {'type': 'oauth2', 'provider': 'notion', 'supported_scopes': ['read', 'write'], 'token_url': 'https://api.notion.com/v1/oauth/token', 'auth_url': 'https://api.notion.com/v1/oauth/authorize', 'requires_refresh': False, 'credential_fields': ['client_id', 'client_secret', 'access_token', 'integration_token']}, 'actions': {'create_page': {'description': 'Create a page in a parent', 'kind': 'create', 'inputs': {'parent_id': 'string', 'parent_type': 'string', 'title': 'string', 'properties': 'json', 'content': 'json'}, 'outputs': {'page_id': 'string', 'page_url': 'string'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'update_page': {'description': 'Update page properties', 'kind': 'update', 'inputs': {'page_id': 'string', 'properties': 'json', 'archived': 'boolean'}, 'outputs': {'page_id': 'string'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'query_database': {'description': 'Query a Notion database', 'kind': 'search', 'inputs': {'database_id': 'string', 'filter': 'json', 'sorts': 'json', 'page_size': 'integer'}, 'outputs': {'results': 'list', 'has_more': 'boolean'}, 'required_permissions': ['read'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'get_page': {'description': 'Fetch a page', 'kind': 'read', 'inputs': {'page_id': 'string'}, 'outputs': {'page': 'object'}, 'required_permissions': ['read'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'create_database': {'description': 'Create a database', 'kind': 'create', 'inputs': {'parent_id': 'string', 'title': 'string', 'properties': 'json'}, 'outputs': {'database_id': 'string'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'search': {'description': 'Search pages and databases', 'kind': 'search', 'inputs': {'query': 'string', 'filter': 'json', 'page_size': 'integer'}, 'outputs': {'results': 'list'}, 'required_permissions': ['read'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'page_created': {'description': 'Triggered when a page is created', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['notion.page_created']}, 'database_updated': {'description': 'Triggered when a database changes', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['notion.database_updated']}}, 'rate_limits': {'default': '3/second', 'rules': {'query_database': '3/second', 'create_page': '3/second'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': True, 'default_interval_seconds': 300}, 'webhooks': {'enabled': False, 'events': ['notion.page_created'], 'secret_required': False}, 'supported_events': ['notion.page_created', 'notion.database_updated'], 'supported_objects': ['page', 'database', 'block'], 'pagination': {'enabled': True, 'default_page_size': 100, 'max_page_size': 100, 'cursor_field': 'start_cursor'}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': True, 'webhooks': False, 'batching': False, 'streaming': False, 'pagination': True, 'file_upload': True, 'file_download': False, 'long_running': False}, 'permissions': {'read': ['read'], 'write': ['write']}, 'health_check': {'endpoint': 'https://api.notion.com/v1/users/me', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://developers.notion.com', 'setup_guide': 'Create an integration in Notion, share your database with it, and copy the token.', 'example_prompt': 'Add new signups to a Notion CRM database'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class NotionConnector(BaseConnector):
    """Notion (notion) connector implementation."""

    name = "Notion"
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
