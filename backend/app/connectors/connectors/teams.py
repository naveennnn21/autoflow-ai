"""AutoFlow AI - Microsoft Teams connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Microsoft Teams', 'version': '1.0.0', 'description': 'Microsoft Teams messaging integration', 'category': 'chat', 'provider': 'microsoft', 'module_name': 'teams', 'authentication': {'type': 'oauth2', 'provider': 'microsoft', 'supported_scopes': ['ChannelMessage.Send', 'Team.ReadBasic.All', 'User.Read', 'offline_access'], 'token_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/token', 'auth_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize', 'requires_refresh': True, 'credential_fields': ['client_id', 'client_secret', 'access_token', 'refresh_token']}, 'actions': {'send_message': {'description': 'Send a message to a Teams channel', 'kind': 'create', 'inputs': {'team_id': 'string', 'channel_id': 'string', 'content': 'string', 'content_type': 'string'}, 'outputs': {'message_id': 'string'}, 'required_permissions': ['ChannelMessage.Send'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'list_channels': {'description': 'List channels in a team', 'kind': 'list', 'inputs': {'team_id': 'string'}, 'outputs': {'channels': 'list'}, 'required_permissions': ['Team.ReadBasic.All'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'create_channel': {'description': 'Create a channel in a team', 'kind': 'create', 'inputs': {'team_id': 'string', 'display_name': 'string', 'description': 'string'}, 'outputs': {'channel_id': 'string'}, 'required_permissions': ['Channel.Create'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_teams': {'description': 'List teams the user belongs to', 'kind': 'list', 'inputs': {'top': 'integer'}, 'outputs': {'teams': 'list'}, 'required_permissions': ['Team.ReadBasic.All'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'get_message': {'description': 'Fetch a channel message', 'kind': 'read', 'inputs': {'team_id': 'string', 'channel_id': 'string', 'message_id': 'string'}, 'outputs': {'message': 'object'}, 'required_permissions': ['ChannelMessage.Read.All'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'message_received': {'description': 'Triggered when a channel message is posted', 'kind': 'polling', 'webhook': False, 'polling_interval_seconds': 300, 'cron': '', 'supported_events': ['teams.message_created']}}, 'rate_limits': {'default': '300/minute', 'rules': {'send_message': '100/minute', 'list_channels': '200/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 2.0, 'max_delay': 120.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': True, 'default_interval_seconds': 300}, 'webhooks': {'enabled': False, 'events': ['teams.message_created'], 'secret_required': False}, 'supported_events': ['teams.message_created'], 'supported_objects': ['team', 'channel', 'message'], 'pagination': {'enabled': True, 'default_page_size': 50, 'max_page_size': 999, 'cursor_field': 'nextLink'}, 'batching': {'enabled': False, 'max_batch_size': 50}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': True, 'webhooks': False, 'batching': False, 'streaming': False, 'pagination': True, 'file_upload': True, 'file_download': True, 'long_running': False}, 'permissions': {'read': ['Team.ReadBasic.All', 'ChannelMessage.Read.All'], 'write': ['ChannelMessage.Send', 'Channel.Create']}, 'health_check': {'endpoint': 'https://graph.microsoft.com/v1.0/me', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://learn.microsoft.com/graph/teams-concept-overview', 'setup_guide': 'Register an Azure app with Microsoft Graph Teams permissions and an OAuth flow.', 'example_prompt': 'Post sprint updates to the engineering channel'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class TeamsConnector(BaseConnector):
    """Microsoft Teams (microsoft) connector implementation."""

    name = "Microsoft Teams"
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
