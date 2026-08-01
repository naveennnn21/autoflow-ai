"""AutoFlow AI - Redis connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Redis', 'version': '1.0.0', 'description': 'Redis in-memory data store connector', 'category': 'database', 'provider': 'redis', 'module_name': 'redis', 'authentication': {'type': 'basic', 'provider': 'redis', 'supported_scopes': ['read', 'write'], 'token_url': '', 'auth_url': '', 'requires_refresh': False, 'credential_fields': ['host', 'port', 'password', 'db']}, 'actions': {'get': {'description': 'Fetch a value by key', 'kind': 'read', 'inputs': {'key': 'string'}, 'outputs': {'value': 'string'}, 'required_permissions': ['read'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'set': {'description': 'Set a key to a value', 'kind': 'create', 'inputs': {'key': 'string', 'value': 'string', 'ttl_seconds': 'integer'}, 'outputs': {'ok': 'boolean'}, 'required_permissions': ['write'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'delete': {'description': 'Delete one or more keys', 'kind': 'delete', 'inputs': {'keys': 'list'}, 'outputs': {'deleted': 'integer'}, 'required_permissions': ['write'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'publish': {'description': 'Publish a message to a channel', 'kind': 'run', 'inputs': {'channel': 'string', 'message': 'string'}, 'outputs': {'subscribers': 'integer'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'hset': {'description': 'Set a field in a hash', 'kind': 'update', 'inputs': {'key': 'string', 'field': 'string', 'value': 'string'}, 'outputs': {'ok': 'boolean'}, 'required_permissions': ['write'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'hget': {'description': 'Fetch a field from a hash', 'kind': 'read', 'inputs': {'key': 'string', 'field': 'string'}, 'outputs': {'value': 'string'}, 'required_permissions': ['read'], 'idempotent': True, 'long_running': False, 'streaming': False}}, 'triggers': {'channel_message': {'description': 'Triggered when a message is published to a channel', 'kind': 'system', 'webhook': False, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['redis.channel_message']}, 'key_expired': {'description': 'Triggered when a key expires', 'kind': 'system', 'webhook': False, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['redis.key_expired']}}, 'rate_limits': {'default': '10000/minute', 'rules': {'get': '1000/minute', 'set': '1000/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 0.5, 'max_delay': 30.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 10, 'write': 10, 'execute': 30}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': False, 'events': [], 'secret_required': False}, 'supported_events': ['redis.channel_message', 'redis.key_expired'], 'supported_objects': ['key', 'hash', 'list', 'channel'], 'pagination': {'enabled': False, 'default_page_size': 100, 'max_page_size': 1000, 'cursor_field': 'cursor'}, 'batching': {'enabled': True, 'max_batch_size': 1000}, 'streaming': {'enabled': True}, 'capabilities': {'actions': True, 'triggers': True, 'polling': False, 'webhooks': False, 'batching': True, 'streaming': True, 'pagination': False, 'file_upload': False, 'file_download': False, 'long_running': False}, 'permissions': {'read': ['read'], 'write': ['write']}, 'health_check': {'endpoint': '', 'method': 'PING', 'timeout_seconds': 5}, 'documentation': {'url': 'https://redis.io/docs', 'setup_guide': 'Provide host, port, optional password, and database index.', 'example_prompt': 'Cache the latest product prices in Redis'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['redis']}


class RedisConnector(BaseConnector):
    """Redis (redis) connector implementation."""

    name = "Redis"
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
