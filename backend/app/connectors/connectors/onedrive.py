"""AutoFlow AI - OneDrive connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'OneDrive', 'version': '1.0.0', 'description': 'Microsoft OneDrive file storage integration', 'category': 'storage', 'provider': 'microsoft', 'module_name': 'onedrive', 'authentication': {'type': 'oauth2', 'provider': 'microsoft', 'supported_scopes': ['Files.ReadWrite.All', 'User.Read', 'offline_access'], 'token_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/token', 'auth_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize', 'requires_refresh': True, 'credential_fields': ['client_id', 'client_secret', 'access_token', 'refresh_token']}, 'actions': {'upload_file': {'description': 'Upload a file to OneDrive', 'kind': 'upload', 'inputs': {'path': 'string', 'content': 'string', 'conflict_behavior': 'string'}, 'outputs': {'file_id': 'string', 'download_url': 'string'}, 'required_permissions': ['Files.ReadWrite.All'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'download_file': {'description': 'Download a file from OneDrive', 'kind': 'download', 'inputs': {'path': 'string'}, 'outputs': {'content': 'string'}, 'required_permissions': ['Files.ReadWrite.All'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_files': {'description': 'List files in a folder', 'kind': 'list', 'inputs': {'path': 'string', 'top': 'integer'}, 'outputs': {'entries': 'list'}, 'required_permissions': ['Files.Read.All'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'create_folder': {'description': 'Create a folder', 'kind': 'create', 'inputs': {'path': 'string', 'name': 'string'}, 'outputs': {'folder_id': 'string'}, 'required_permissions': ['Files.ReadWrite.All'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'search_files': {'description': 'Search OneDrive for files', 'kind': 'search', 'inputs': {'query': 'string', 'top': 'integer'}, 'outputs': {'matches': 'list'}, 'required_permissions': ['Files.Read.All'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'delete_file': {'description': 'Delete a file or folder', 'kind': 'delete', 'inputs': {'path': 'string'}, 'outputs': {'deleted': 'boolean'}, 'required_permissions': ['Files.ReadWrite.All'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'file_created': {'description': 'Triggered when a file is created', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['onedrive.file_created']}, 'file_modified': {'description': 'Triggered when a file is modified', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['onedrive.file_modified']}}, 'rate_limits': {'default': '1000/hour', 'rules': {'download_file': '100/minute', 'upload_file': '100/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 2.0, 'max_delay': 120.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 60, 'write': 60, 'execute': 120}, 'polling': {'enabled': True, 'default_interval_seconds': 300}, 'webhooks': {'enabled': False, 'events': ['onedrive.file_created'], 'secret_required': False}, 'supported_events': ['onedrive.file_created', 'onedrive.file_modified'], 'supported_objects': ['file', 'folder'], 'pagination': {'enabled': True, 'default_page_size': 50, 'max_page_size': 999, 'cursor_field': 'nextLink'}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': True}, 'capabilities': {'actions': True, 'triggers': True, 'polling': True, 'webhooks': False, 'batching': False, 'streaming': True, 'pagination': True, 'file_upload': True, 'file_download': True, 'long_running': True}, 'permissions': {'read': ['Files.Read.All'], 'write': ['Files.ReadWrite.All']}, 'health_check': {'endpoint': 'https://graph.microsoft.com/v1.0/me/drive', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://learn.microsoft.com/graph/onedrive-concept-overview', 'setup_guide': 'Register an Azure app with Files.ReadWrite.All and an OAuth flow.', 'example_prompt': 'Save meeting recordings to OneDrive'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class OnedriveConnector(BaseConnector):
    """OneDrive (microsoft) connector implementation."""

    name = "OneDrive"
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
