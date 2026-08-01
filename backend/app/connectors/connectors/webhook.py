"""AutoFlow AI - Webhook connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Webhook', 'version': '1.0.0', 'description': 'Generic webhook receiver connector', 'category': 'generic', 'provider': 'http', 'module_name': 'webhook', 'authentication': {'type': 'webhook_secret', 'provider': 'http', 'supported_scopes': ['receive'], 'token_url': '', 'auth_url': '', 'requires_refresh': False, 'credential_fields': ['secret', 'signing_header']}, 'actions': {'verify_signature': {'description': 'Verify the webhook request signature', 'kind': 'run', 'inputs': {'payload': 'json', 'signature': 'string', 'timestamp': 'string'}, 'outputs': {'verified': 'boolean'}, 'required_permissions': ['receive'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'transform_payload': {'description': 'Transform an incoming webhook payload', 'kind': 'run', 'inputs': {'payload': 'json', 'mapping': 'json'}, 'outputs': {'transformed': 'json'}, 'required_permissions': ['receive'], 'idempotent': True, 'long_running': False, 'streaming': False}}, 'triggers': {'webhook_received': {'description': 'Triggered when the webhook fires', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['webhook.received']}}, 'rate_limits': {'default': '120/minute', 'rules': {'verify_signature': '120/minute'}}, 'retry_policy': {'max_attempts': 1, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': True, 'events': ['webhook.received'], 'secret_required': True}, 'supported_events': ['webhook.received'], 'supported_objects': ['payload'], 'pagination': {'enabled': False, 'default_page_size': 50, 'max_page_size': 1000, 'cursor_field': ''}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': False, 'webhooks': True, 'batching': False, 'streaming': False, 'pagination': False, 'file_upload': False, 'file_download': False, 'long_running': False}, 'permissions': {'read': ['receive'], 'write': ['receive']}, 'health_check': {'endpoint': '', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': '', 'setup_guide': 'Register a webhook URL and configure the signing secret.', 'example_prompt': 'Receive and route webhook events'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': []}


class WebhookConnector(BaseConnector):
    """Webhook (http) connector implementation."""

    name = "Webhook"
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
