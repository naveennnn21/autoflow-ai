"""AutoFlow AI - GraphQL connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'GraphQL', 'version': '1.0.0', 'description': 'Generic GraphQL API connector', 'category': 'generic', 'provider': 'graphql', 'module_name': 'graphql_connector', 'authentication': {'type': 'bearer', 'provider': 'graphql', 'supported_scopes': ['read', 'write'], 'token_url': '', 'auth_url': '', 'requires_refresh': False, 'credential_fields': ['endpoint', 'api_key', 'bearer_token', 'headers']}, 'actions': {'query': {'description': 'Execute a GraphQL query', 'kind': 'read', 'inputs': {'query': 'text', 'variables': 'json', 'operation_name': 'string'}, 'outputs': {'data': 'json', 'errors': 'list'}, 'required_permissions': ['read'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'mutation': {'description': 'Execute a GraphQL mutation', 'kind': 'create', 'inputs': {'query': 'text', 'variables': 'json', 'operation_name': 'string'}, 'outputs': {'data': 'json', 'errors': 'list'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'introspection': {'description': 'Fetch the GraphQL schema via introspection', 'kind': 'read', 'inputs': {'include_deprecated': 'boolean'}, 'outputs': {'schema': 'json'}, 'required_permissions': ['read'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'subscription': {'description': 'Open a GraphQL subscription stream', 'kind': 'stream', 'inputs': {'query': 'text', 'variables': 'json'}, 'outputs': {'events': 'stream'}, 'required_permissions': ['read'], 'idempotent': False, 'long_running': False, 'streaming': True}}, 'triggers': {'subscription_event': {'description': 'Triggered on GraphQL subscription events', 'kind': 'system', 'webhook': False, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['graphql.subscription_event']}, 'manual': {'description': 'Manual trigger', 'kind': 'manual', 'webhook': False, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': []}}, 'rate_limits': {'default': '120/minute', 'rules': {'query': '60/minute', 'mutation': '60/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': False, 'events': [], 'secret_required': False}, 'supported_events': ['graphql.subscription_event'], 'supported_objects': ['query', 'mutation', 'subscription'], 'pagination': {'enabled': True, 'default_page_size': 50, 'max_page_size': 1000, 'cursor_field': 'after'}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': True}, 'capabilities': {'actions': True, 'triggers': True, 'polling': False, 'webhooks': False, 'batching': False, 'streaming': True, 'pagination': True, 'file_upload': False, 'file_download': False, 'long_running': True}, 'permissions': {'read': ['read'], 'write': ['write']}, 'health_check': {'endpoint': '', 'method': 'POST', 'timeout_seconds': 10}, 'documentation': {'url': 'https://graphql.org', 'setup_guide': 'Configure the GraphQL endpoint and any authentication headers.', 'example_prompt': 'Query user data from a GraphQL API'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class GraphqlConnectorConnector(BaseConnector):
    """GraphQL (graphql) connector implementation."""

    name = "GraphQL"
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
