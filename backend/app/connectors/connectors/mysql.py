"""AutoFlow AI - MySQL connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'MySQL', 'version': '1.0.0', 'description': 'MySQL relational database connector', 'category': 'database', 'provider': 'mysql', 'module_name': 'mysql', 'authentication': {'type': 'basic', 'provider': 'mysql', 'supported_scopes': ['read', 'write'], 'token_url': '', 'auth_url': '', 'requires_refresh': False, 'credential_fields': ['host', 'port', 'database', 'username', 'password']}, 'actions': {'execute_query': {'description': 'Run a read-only SQL query', 'kind': 'run', 'inputs': {'sql': 'text', 'parameters': 'json', 'limit': 'integer'}, 'outputs': {'rows': 'list', 'row_count': 'integer'}, 'required_permissions': ['read'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'execute_statement': {'description': 'Run an arbitrary SQL statement', 'kind': 'run', 'inputs': {'sql': 'text', 'parameters': 'json'}, 'outputs': {'affected_rows': 'integer'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_tables': {'description': 'List tables in the database', 'kind': 'list', 'inputs': {'schema': 'string'}, 'outputs': {'tables': 'list'}, 'required_permissions': ['read'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'get_schema': {'description': 'Fetch table schema', 'kind': 'read', 'inputs': {'table': 'string', 'schema': 'string'}, 'outputs': {'columns': 'list'}, 'required_permissions': ['read'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'row_inserted': {'description': 'Triggered when a row is inserted', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['mysql.row_inserted']}, 'row_updated': {'description': 'Triggered when a row is updated', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['mysql.row_updated']}}, 'rate_limits': {'default': '600/minute', 'rules': {'execute_query': '120/minute', 'execute_statement': '120/minute'}}, 'retry_policy': {'max_attempts': 2, 'base_delay': 1.0, 'max_delay': 30.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': True, 'default_interval_seconds': 300}, 'webhooks': {'enabled': False, 'events': [], 'secret_required': False}, 'supported_events': ['mysql.row_inserted', 'mysql.row_updated'], 'supported_objects': ['table', 'row', 'schema'], 'pagination': {'enabled': True, 'default_page_size': 100, 'max_page_size': 1000, 'cursor_field': 'offset'}, 'batching': {'enabled': True, 'max_batch_size': 1000}, 'streaming': {'enabled': True}, 'capabilities': {'actions': True, 'triggers': True, 'polling': True, 'webhooks': False, 'batching': True, 'streaming': True, 'pagination': True, 'file_upload': False, 'file_download': False, 'long_running': True}, 'permissions': {'read': ['read'], 'write': ['write']}, 'health_check': {'endpoint': '', 'method': 'CONNECT', 'timeout_seconds': 10}, 'documentation': {'url': 'https://dev.mysql.com/doc', 'setup_guide': 'Provide host, port, database, username, and password. Firewall must allow outbound access.', 'example_prompt': 'Look up a customer record in MySQL'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['pymysql']}


class MysqlConnector(BaseConnector):
    """MySQL (mysql) connector implementation."""

    name = "MySQL"
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
