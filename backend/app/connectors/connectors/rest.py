"""AutoFlow AI - REST connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'REST', 'version': '1.0.0', 'description': 'Generic REST API connector for any HTTP endpoint', 'category': 'generic', 'provider': 'http', 'module_name': 'rest', 'authentication': {'type': 'none', 'provider': 'http', 'supported_scopes': ['read', 'write'], 'token_url': '', 'auth_url': '', 'requires_refresh': False, 'credential_fields': ['base_url', 'headers', 'api_key', 'bearer_token']}, 'actions': {'get': {'description': 'Perform an HTTP GET request', 'kind': 'read', 'inputs': {'path': 'string', 'query': 'json', 'headers': 'json'}, 'outputs': {'status_code': 'integer', 'body': 'json', 'headers': 'json'}, 'required_permissions': ['read'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'post': {'description': 'Perform an HTTP POST request', 'kind': 'create', 'inputs': {'path': 'string', 'body': 'json', 'headers': 'json'}, 'outputs': {'status_code': 'integer', 'body': 'json'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'put': {'description': 'Perform an HTTP PUT request', 'kind': 'update', 'inputs': {'path': 'string', 'body': 'json', 'headers': 'json'}, 'outputs': {'status_code': 'integer', 'body': 'json'}, 'required_permissions': ['write'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'patch': {'description': 'Perform an HTTP PATCH request', 'kind': 'update', 'inputs': {'path': 'string', 'body': 'json', 'headers': 'json'}, 'outputs': {'status_code': 'integer', 'body': 'json'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'delete': {'description': 'Perform an HTTP DELETE request', 'kind': 'delete', 'inputs': {'path': 'string', 'headers': 'json'}, 'outputs': {'status_code': 'integer', 'body': 'json'}, 'required_permissions': ['write'], 'idempotent': True, 'long_running': False, 'streaming': False}}, 'triggers': {'webhook_received': {'description': 'Triggered when the endpoint receives a webhook', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['rest.webhook_received']}, 'manual': {'description': 'Manual trigger', 'kind': 'manual', 'webhook': False, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': []}}, 'rate_limits': {'default': '60/minute', 'rules': {'get': '120/minute', 'post': '60/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': True, 'events': ['rest.webhook_received'], 'secret_required': False}, 'supported_events': ['rest.webhook_received'], 'supported_objects': ['resource'], 'pagination': {'enabled': True, 'default_page_size': 50, 'max_page_size': 1000, 'cursor_field': 'page'}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': True}, 'capabilities': {'actions': True, 'triggers': True, 'polling': False, 'webhooks': True, 'batching': False, 'streaming': True, 'pagination': True, 'file_upload': True, 'file_download': True, 'long_running': True}, 'permissions': {'read': ['read'], 'write': ['write']}, 'health_check': {'endpoint': '', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': '', 'setup_guide': 'Configure the base URL and authentication to call any REST API.', 'example_prompt': 'Call an internal REST API to fetch data'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class RestConnector(BaseConnector):
    """REST (http) connector implementation."""

    name = "REST"
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
