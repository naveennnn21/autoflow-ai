"""AutoFlow AI - Google Drive connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Google Drive', 'version': '1.0.0', 'description': 'Google Drive file storage integration', 'category': 'storage', 'provider': 'google', 'module_name': 'google_drive', 'authentication': {'type': 'oauth2', 'provider': 'google', 'supported_scopes': ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/drive.appdata'], 'token_url': 'https://oauth2.googleapis.com/token', 'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth', 'requires_refresh': True, 'credential_fields': ['client_id', 'client_secret', 'access_token', 'refresh_token']}, 'actions': {'upload_file': {'description': 'Upload a file to Drive', 'kind': 'upload', 'inputs': {'name': 'string', 'content': 'string', 'mime_type': 'string', 'parent_folder_id': 'string'}, 'outputs': {'file_id': 'string', 'web_view_link': 'string'}, 'required_permissions': ['drive.file'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'download_file': {'description': 'Download a file from Drive', 'kind': 'download', 'inputs': {'file_id': 'string', 'mime_type': 'string'}, 'outputs': {'content': 'string', 'content_type': 'string'}, 'required_permissions': ['drive.readonly'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_files': {'description': 'List files in a folder', 'kind': 'list', 'inputs': {'folder_id': 'string', 'page_size': 'integer', 'query': 'string'}, 'outputs': {'files': 'list', 'next_page_token': 'string'}, 'required_permissions': ['drive.readonly'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'create_folder': {'description': 'Create a Drive folder', 'kind': 'create', 'inputs': {'name': 'string', 'parent_folder_id': 'string'}, 'outputs': {'folder_id': 'string'}, 'required_permissions': ['drive.file'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'search_files': {'description': 'Search Drive for files', 'kind': 'search', 'inputs': {'query': 'string', 'page_size': 'integer'}, 'outputs': {'files': 'list'}, 'required_permissions': ['drive.readonly'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'delete_file': {'description': 'Delete a file', 'kind': 'delete', 'inputs': {'file_id': 'string'}, 'outputs': {'deleted': 'boolean'}, 'required_permissions': ['drive.file'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'file_created': {'description': 'Triggered when a file is created', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['google_drive.file_created']}, 'file_modified': {'description': 'Triggered when a file is modified', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['google_drive.file_modified']}}, 'rate_limits': {'default': '300/minute', 'rules': {'download_file': '120/minute', 'upload_file': '60/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 60, 'write': 60, 'execute': 120}, 'polling': {'enabled': True, 'default_interval_seconds': 300}, 'webhooks': {'enabled': False, 'events': ['google_drive.file_created'], 'secret_required': False}, 'supported_events': ['google_drive.file_created', 'google_drive.file_modified'], 'supported_objects': ['file', 'folder'], 'pagination': {'enabled': True, 'default_page_size': 100, 'max_page_size': 1000, 'cursor_field': 'nextPageToken'}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': True}, 'capabilities': {'actions': True, 'triggers': True, 'polling': True, 'webhooks': False, 'batching': False, 'streaming': True, 'pagination': True, 'file_upload': True, 'file_download': True, 'long_running': True}, 'permissions': {'read': ['drive.readonly'], 'write': ['drive.file', 'drive.appdata']}, 'health_check': {'endpoint': 'https://www.googleapis.com/drive/v3/about', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://developers.google.com/drive/api', 'setup_guide': 'Enable the Drive API in Google Cloud and add OAuth client credentials.', 'example_prompt': 'Save the generated report to Google Drive'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class GoogleDriveConnector(BaseConnector):
    """Google Drive (google) connector implementation."""

    name = "Google Drive"
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
