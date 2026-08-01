"""AutoFlow AI - Discord connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Discord', 'version': '1.0.0', 'description': 'Discord server messaging integration', 'category': 'chat', 'provider': 'discord', 'module_name': 'discord', 'authentication': {'type': 'bearer', 'provider': 'discord', 'supported_scopes': ['bot', 'messages.read'], 'token_url': '', 'auth_url': '', 'requires_refresh': False, 'credential_fields': ['bot_token']}, 'actions': {'send_message': {'description': 'Send a message to a channel', 'kind': 'create', 'inputs': {'channel_id': 'string', 'content': 'string', 'embeds': 'json', 'tts': 'boolean'}, 'outputs': {'message_id': 'string'}, 'required_permissions': ['send_messages'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'create_channel': {'description': 'Create a text channel', 'kind': 'create', 'inputs': {'guild_id': 'string', 'name': 'string', 'topic': 'string'}, 'outputs': {'channel_id': 'string'}, 'required_permissions': ['manage_channels'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_channels': {'description': 'List channels in a guild', 'kind': 'list', 'inputs': {'guild_id': 'string'}, 'outputs': {'channels': 'list'}, 'required_permissions': ['view_channels'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'get_guild_member': {'description': 'Fetch a guild member', 'kind': 'read', 'inputs': {'guild_id': 'string', 'user_id': 'string'}, 'outputs': {'member': 'object'}, 'required_permissions': ['view_members'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'delete_message': {'description': 'Delete a message', 'kind': 'delete', 'inputs': {'channel_id': 'string', 'message_id': 'string'}, 'outputs': {'deleted': 'boolean'}, 'required_permissions': ['manage_messages'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'message_received': {'description': 'Triggered when a message is posted', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['discord.message_created']}, 'member_joined': {'description': 'Triggered when a member joins', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['discord.member_joined']}}, 'rate_limits': {'default': '50/second', 'rules': {'send_message': '5/second', 'list_channels': '10/second'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': True, 'events': ['discord.message_created', 'discord.member_joined'], 'secret_required': False}, 'supported_events': ['discord.message_created', 'discord.member_joined'], 'supported_objects': ['channel', 'message', 'member', 'guild'], 'pagination': {'enabled': True, 'default_page_size': 100, 'max_page_size': 1000, 'cursor_field': 'before'}, 'batching': {'enabled': False, 'max_batch_size': 50}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': False, 'webhooks': True, 'batching': False, 'streaming': False, 'pagination': True, 'file_upload': True, 'file_download': False, 'long_running': False}, 'permissions': {'read': ['view_channels', 'view_members'], 'write': ['send_messages', 'manage_channels', 'manage_messages']}, 'health_check': {'endpoint': 'https://discord.com/api/v10/users/@me', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://discord.com/developers/docs', 'setup_guide': 'Create a bot application in the Discord developer portal and add it to your server.', 'example_prompt': 'Announce releases in the'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class DiscordConnector(BaseConnector):
    """Discord (discord) connector implementation."""

    name = "Discord"
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
