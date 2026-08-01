"""AutoFlow AI - Dropbox connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Dropbox', 'version': '1.0.0', 'description': 'Dropbox file storage integration', 'category': 'storage', 'provider': 'dropbox', 'module_name': 'dropbox', 'authentication': {'type': 'oauth2', 'provider': 'dropbox', 'supported_scopes': ['files.metadata.write', 'files.metadata.read', 'files.content.write', 'files.content.read', 'account_info.read'], 'token_url': 'https://api.dropboxapi.com/oauth2/token', 'auth_url': 'https://www.dropbox.com/oauth2/authorize', 'requires_refresh': True, 'credential_fields': ['client_id', 'client_secret', 'access_token', 'refresh_token']}, 'actions': {'upload_file': {'description': 'Upload a file to a Dropbox path', 'kind': 'upload', 'inputs': {'path': 'string', 'content': 'string', 'mode': 'string', 'autorename': 'boolean'}, 'outputs': {'file_id': 'string', 'revision': 'string'}, 'required_permissions': ['files.content.write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'download_file': {'description': 'Download a file from Dropbox', 'kind': 'download', 'inputs': {'path': 'string'}, 'outputs': {'content': 'string', 'content_type': 'string'}, 'required_permissions': ['files.content.read'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_files': {'description': 'List files in a folder', 'kind': 'list', 'inputs': {'path': 'string', 'recursive': 'boolean', 'limit': 'integer'}, 'outputs': {'entries': 'list'}, 'required_permissions': ['files.metadata.read'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'create_folder': {'description': 'Create a folder', 'kind': 'create', 'inputs': {'path': 'string'}, 'outputs': {'folder_id': 'string'}, 'required_permissions': ['files.metadata.write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'search_files': {'description': 'Search for files by name', 'kind': 'search', 'inputs': {'query': 'string', 'path': 'string', 'max_results': 'integer'}, 'outputs': {'matches': 'list'}, 'required_permissions': ['files.metadata.read'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'delete_file': {'description': 'Delete a file or folder', 'kind': 'delete', 'inputs': {'path': 'string'}, 'outputs': {'deleted': 'boolean'}, 'required_permissions': ['files.metadata.write'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'file_created': {'description': 'Triggered when a file is created', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 60, 'cron': '', 'supported_events': ['dropbox.file_created']}, 'file_modified': {'description': 'Triggered when a file is modified', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 60, 'cron': '', 'supported_events': ['dropbox.file_modified']}}, 'rate_limits': {'default': '240/minute', 'rules': {'download_file': '120/minute', 'upload_file': '120/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 60, 'write': 60, 'execute': 120}, 'polling': {'enabled': True, 'default_interval_seconds': 60}, 'webhooks': {'enabled': False, 'events': ['dropbox.file_created'], 'secret_required': False}, 'supported_events': ['dropbox.file_created', 'dropbox.file_modified'], 'supported_objects': ['file', 'folder'], 'pagination': {'enabled': True, 'default_page_size': 100, 'max_page_size': 2000, 'cursor_field': 'cursor'}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': True}, 'capabilities': {'actions': True, 'triggers': True, 'polling': True, 'webhooks': False, 'batching': False, 'streaming': True, 'pagination': True, 'file_upload': True, 'file_download': True, 'long_running': True}, 'permissions': {'read': ['files.metadata.read', 'files.content.read'], 'write': ['files.metadata.write', 'files.content.write']}, 'health_check': {'endpoint': 'https://api.dropboxapi.com/2/users/get_current_account', 'method': 'POST', 'timeout_seconds': 10}, 'documentation': {'url': 'https://developers.dropbox.com', 'setup_guide': 'Create a Dropbox app with the files scopes and OAuth credentials.', 'example_prompt': 'Back up the daily export to Dropbox'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class DropboxConnector(BaseConnector):
    """Dropbox (dropbox) connector implementation."""

    name = "Dropbox"
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
