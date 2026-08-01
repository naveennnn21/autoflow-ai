"""AutoFlow AI - gRPC connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'gRPC', 'version': '1.0.0', 'description': 'Generic gRPC service connector', 'category': 'generic', 'provider': 'grpc', 'module_name': 'grpc_connector', 'authentication': {'type': 'none', 'provider': 'grpc', 'supported_scopes': ['read', 'write'], 'token_url': '', 'auth_url': '', 'requires_refresh': False, 'credential_fields': ['endpoint', 'proto_path', 'service_name', 'api_key', 'tls']}, 'actions': {'unary_call': {'description': 'Invoke a unary gRPC method', 'kind': 'run', 'inputs': {'method': 'string', 'request': 'json', 'metadata': 'json'}, 'outputs': {'response': 'json'}, 'required_permissions': ['read'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'server_stream': {'description': 'Invoke a server-streaming gRPC method', 'kind': 'stream', 'inputs': {'method': 'string', 'request': 'json', 'metadata': 'json'}, 'outputs': {'responses': 'stream'}, 'required_permissions': ['read'], 'idempotent': False, 'long_running': False, 'streaming': True}, 'client_stream': {'description': 'Invoke a client-streaming gRPC method', 'kind': 'stream', 'inputs': {'method': 'string', 'requests': 'json', 'metadata': 'json'}, 'outputs': {'response': 'json'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': True}, 'health_check': {'description': 'Call the gRPC health service', 'kind': 'read', 'inputs': {'service': 'string'}, 'outputs': {'status': 'string'}, 'required_permissions': ['read'], 'idempotent': True, 'long_running': False, 'streaming': False}}, 'triggers': {'manual': {'description': 'Manual trigger', 'kind': 'manual', 'webhook': False, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': []}}, 'rate_limits': {'default': '120/minute', 'rules': {'unary_call': '60/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 120}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': False, 'events': [], 'secret_required': False}, 'supported_events': [], 'supported_objects': ['service', 'method'], 'pagination': {'enabled': False, 'default_page_size': 50, 'max_page_size': 1000, 'cursor_field': ''}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': True}, 'capabilities': {'actions': True, 'triggers': False, 'polling': False, 'webhooks': False, 'batching': False, 'streaming': True, 'pagination': False, 'file_upload': False, 'file_download': False, 'long_running': True}, 'permissions': {'read': ['read'], 'write': ['write']}, 'health_check': {'endpoint': '', 'method': 'GRPC', 'timeout_seconds': 10}, 'documentation': {'url': 'https://grpc.io/docs', 'setup_guide': 'Provide the gRPC endpoint and compiled proto descriptor to call methods.', 'example_prompt': 'Call a gRPC service method'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['grpcio']}


class GrpcConnectorConnector(BaseConnector):
    """gRPC (grpc) connector implementation."""

    name = "gRPC"
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
