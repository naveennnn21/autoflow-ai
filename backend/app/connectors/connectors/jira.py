"""AutoFlow AI - Jira connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Jira', 'version': '1.0.0', 'description': 'Jira issue tracking and project management', 'category': 'productivity', 'provider': 'atlassian', 'module_name': 'jira', 'authentication': {'type': 'oauth2', 'provider': 'atlassian', 'supported_scopes': ['read:jira-user', 'read:jira-work', 'write:jira-work', 'offline_access'], 'token_url': 'https://auth.atlassian.com/oauth/token', 'auth_url': 'https://auth.atlassian.com/authorize', 'requires_refresh': True, 'credential_fields': ['client_id', 'client_secret', 'access_token', 'refresh_token']}, 'actions': {'create_issue': {'description': 'Create a Jira issue', 'kind': 'create', 'inputs': {'project_key': 'string', 'summary': 'string', 'description': 'text', 'issue_type': 'string', 'assignee': 'string', 'priority': 'string'}, 'outputs': {'issue_key': 'string', 'issue_id': 'string', 'issue_url': 'string'}, 'required_permissions': ['write:jira-work'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'update_issue': {'description': 'Update a Jira issue', 'kind': 'update', 'inputs': {'issue_key': 'string', 'summary': 'string', 'description': 'text', 'status': 'string', 'assignee': 'string'}, 'outputs': {'issue_key': 'string'}, 'required_permissions': ['write:jira-work'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'search_issues': {'description': 'Search issues with JQL', 'kind': 'search', 'inputs': {'jql': 'string', 'max_results': 'integer', 'fields': 'list'}, 'outputs': {'issues': 'list'}, 'required_permissions': ['read:jira-work'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'get_issue': {'description': 'Fetch a single issue', 'kind': 'read', 'inputs': {'issue_key': 'string'}, 'outputs': {'issue': 'object'}, 'required_permissions': ['read:jira-work'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'transition_issue': {'description': 'Move an issue to a workflow status', 'kind': 'update', 'inputs': {'issue_key': 'string', 'transition_name': 'string'}, 'outputs': {'status': 'string'}, 'required_permissions': ['write:jira-work'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'issue_created': {'description': 'Triggered when an issue is created', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['jira.issue_created']}, 'issue_updated': {'description': 'Triggered when an issue changes', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['jira.issue_updated']}}, 'rate_limits': {'default': '500/minute', 'rules': {'search_issues': '60/minute', 'create_issue': '60/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': True, 'events': ['jira.issue_created', 'jira.issue_updated'], 'secret_required': True}, 'supported_events': ['jira.issue_created', 'jira.issue_updated'], 'supported_objects': ['issue', 'project', 'sprint', 'comment'], 'pagination': {'enabled': True, 'default_page_size': 50, 'max_page_size': 200, 'cursor_field': 'startAt'}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': False, 'webhooks': True, 'batching': False, 'streaming': False, 'pagination': True, 'file_upload': True, 'file_download': False, 'long_running': False}, 'permissions': {'read': ['read:jira-work'], 'write': ['write:jira-work']}, 'health_check': {'endpoint': 'https://{site}.atlassian.net/rest/api/3/myself', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://developer.atlassian.com/cloud/jira', 'setup_guide': 'Create a Jira Cloud app with OAuth 2.0 and add the Jira API scopes.', 'example_prompt': 'Create a Jira ticket for support requests'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class JiraConnector(BaseConnector):
    """Jira (atlassian) connector implementation."""

    name = "Jira"
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
