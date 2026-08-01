"""AutoFlow AI - MongoDB connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'MongoDB', 'version': '1.0.0', 'description': 'MongoDB document database connector', 'category': 'database', 'provider': 'mongodb', 'module_name': 'mongodb', 'authentication': {'type': 'basic', 'provider': 'mongodb', 'supported_scopes': ['read', 'write'], 'token_url': '', 'auth_url': '', 'requires_refresh': False, 'credential_fields': ['uri', 'database', 'username', 'password']}, 'actions': {'find_documents': {'description': 'Query documents in a collection', 'kind': 'read', 'inputs': {'collection': 'string', 'filter': 'json', 'limit': 'integer', 'sort': 'json'}, 'outputs': {'documents': 'list', 'count': 'integer'}, 'required_permissions': ['read'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'insert_documents': {'description': 'Insert documents into a collection', 'kind': 'create', 'inputs': {'collection': 'string', 'documents': 'json'}, 'outputs': {'inserted_ids': 'list'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'update_documents': {'description': 'Update documents matching a filter', 'kind': 'update', 'inputs': {'collection': 'string', 'filter': 'json', 'update': 'json', 'upsert': 'boolean', 'multi': 'boolean'}, 'outputs': {'modified_count': 'integer'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'delete_documents': {'description': 'Delete documents matching a filter', 'kind': 'delete', 'inputs': {'collection': 'string', 'filter': 'json'}, 'outputs': {'deleted_count': 'integer'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'aggregate': {'description': 'Run an aggregation pipeline', 'kind': 'run', 'inputs': {'collection': 'string', 'pipeline': 'json'}, 'outputs': {'results': 'list'}, 'required_permissions': ['read'], 'idempotent': True, 'long_running': False, 'streaming': False}}, 'triggers': {'document_inserted': {'description': 'Triggered when a document is inserted', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['mongodb.document_inserted']}}, 'rate_limits': {'default': '600/minute', 'rules': {'find_documents': '120/minute', 'insert_documents': '120/minute'}}, 'retry_policy': {'max_attempts': 2, 'base_delay': 1.0, 'max_delay': 30.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': True, 'default_interval_seconds': 300}, 'webhooks': {'enabled': False, 'events': [], 'secret_required': False}, 'supported_events': ['mongodb.document_inserted'], 'supported_objects': ['collection', 'document'], 'pagination': {'enabled': True, 'default_page_size': 100, 'max_page_size': 1000, 'cursor_field': 'skip'}, 'batching': {'enabled': True, 'max_batch_size': 1000}, 'streaming': {'enabled': True}, 'capabilities': {'actions': True, 'triggers': True, 'polling': True, 'webhooks': False, 'batching': True, 'streaming': True, 'pagination': True, 'file_upload': False, 'file_download': False, 'long_running': True}, 'permissions': {'read': ['read'], 'write': ['write']}, 'health_check': {'endpoint': '', 'method': 'CONNECT', 'timeout_seconds': 10}, 'documentation': {'url': 'https://www.mongodb.com/docs', 'setup_guide': 'Provide a MongoDB connection URI, database name, and optional credentials.', 'example_prompt': 'Find all users created in the last week'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['pymongo']}


class MongodbConnector(BaseConnector):
    """MongoDB (mongodb) connector implementation."""

    name = "MongoDB"
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
