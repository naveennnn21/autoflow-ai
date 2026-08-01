"""AutoFlow AI - Linear connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Linear', 'version': '1.0.0', 'description': 'Linear issue tracking and project management', 'category': 'productivity', 'provider': 'linear', 'module_name': 'linear', 'authentication': {'type': 'bearer', 'provider': 'linear', 'supported_scopes': ['read', 'write', 'issues:create'], 'token_url': 'https://api.linear.app/oauth/token', 'auth_url': 'https://linear.app/oauth/authorize', 'requires_refresh': True, 'credential_fields': ['client_id', 'client_secret', 'access_token', 'api_key']}, 'actions': {'create_issue': {'description': 'Create a Linear issue', 'kind': 'create', 'inputs': {'team_id': 'string', 'title': 'string', 'description': 'text', 'priority': 'integer', 'assignee_id': 'string', 'labels': 'list'}, 'outputs': {'issue_id': 'string', 'issue_identifier': 'string', 'issue_url': 'string'}, 'required_permissions': ['issues:create'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'update_issue': {'description': 'Update a Linear issue', 'kind': 'update', 'inputs': {'issue_id': 'string', 'title': 'string', 'description': 'text', 'state_id': 'string', 'priority': 'integer'}, 'outputs': {'issue_id': 'string'}, 'required_permissions': ['write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'search_issues': {'description': 'Search issues by filter', 'kind': 'search', 'inputs': {'query': 'string', 'team_id': 'string', 'state_id': 'string', 'first': 'integer'}, 'outputs': {'issues': 'list'}, 'required_permissions': ['read'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'get_issue': {'description': 'Fetch a single issue', 'kind': 'read', 'inputs': {'issue_id': 'string'}, 'outputs': {'issue': 'object'}, 'required_permissions': ['read'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_teams': {'description': 'List teams the user can access', 'kind': 'list', 'inputs': {'first': 'integer'}, 'outputs': {'teams': 'list'}, 'required_permissions': ['read'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'issue_created': {'description': 'Triggered when an issue is created', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['linear.issue_created']}, 'issue_updated': {'description': 'Triggered when an issue is updated', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['linear.issue_updated']}, 'comment_created': {'description': 'Triggered when a comment is created', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['linear.comment_created']}}, 'rate_limits': {'default': '400/minute', 'rules': {'search_issues': '60/minute', 'create_issue': '60/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': True, 'events': ['linear.issue_created', 'linear.issue_updated', 'linear.comment_created'], 'secret_required': True}, 'supported_events': ['linear.issue_created', 'linear.issue_updated', 'linear.comment_created'], 'supported_objects': ['issue', 'team', 'project', 'comment'], 'pagination': {'enabled': True, 'default_page_size': 50, 'max_page_size': 250, 'cursor_field': 'after'}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': False, 'webhooks': True, 'batching': False, 'streaming': False, 'pagination': True, 'file_upload': True, 'file_download': False, 'long_running': False}, 'permissions': {'read': ['read'], 'write': ['write', 'issues:create']}, 'health_check': {'endpoint': 'https://api.linear.app/graphql', 'method': 'POST', 'timeout_seconds': 10}, 'documentation': {'url': 'https://developers.linear.app', 'setup_guide': 'Create a Linear API key or OAuth app and grant read/write scopes.', 'example_prompt': 'Create a Linear issue for onboarding tasks'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class LinearConnector(BaseConnector):
    """Linear (linear) connector implementation."""

    name = "Linear"
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
