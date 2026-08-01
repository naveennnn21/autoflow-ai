"""AutoFlow AI - GitHub connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'GitHub', 'version': '1.0.0', 'description': 'GitHub repositories, issues, and pull requests', 'category': 'developer', 'provider': 'github', 'module_name': 'github', 'authentication': {'type': 'oauth2', 'provider': 'github', 'supported_scopes': ['repo', 'read:org', 'workflow'], 'token_url': 'https://github.com/login/oauth/access_token', 'auth_url': 'https://github.com/login/oauth/authorize', 'requires_refresh': False, 'credential_fields': ['client_id', 'client_secret', 'access_token']}, 'actions': {'create_issue': {'description': 'Create an issue in a repository', 'kind': 'create', 'inputs': {'owner': 'string', 'repo': 'string', 'title': 'string', 'body': 'text', 'labels': 'list'}, 'outputs': {'issue_number': 'integer', 'issue_url': 'string'}, 'required_permissions': ['issues:write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_issues': {'description': 'List issues for a repository', 'kind': 'list', 'inputs': {'owner': 'string', 'repo': 'string', 'state': 'string', 'per_page': 'integer'}, 'outputs': {'issues': 'list'}, 'required_permissions': ['issues:read'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'create_pull_request': {'description': 'Open a pull request', 'kind': 'create', 'inputs': {'owner': 'string', 'repo': 'string', 'title': 'string', 'head': 'string', 'base': 'string', 'body': 'text'}, 'outputs': {'pr_number': 'integer', 'pr_url': 'string'}, 'required_permissions': ['pulls:write'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'get_repository': {'description': 'Fetch repository metadata', 'kind': 'read', 'inputs': {'owner': 'string', 'repo': 'string'}, 'outputs': {'repository': 'object'}, 'required_permissions': ['repo'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_commits': {'description': 'List commits on a branch', 'kind': 'list', 'inputs': {'owner': 'string', 'repo': 'string', 'branch': 'string', 'per_page': 'integer'}, 'outputs': {'commits': 'list'}, 'required_permissions': ['repo'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'push': {'description': 'Triggered on push events', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['github.push']}, 'pull_request': {'description': 'Triggered on pull request events', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['github.pull_request']}, 'issues': {'description': 'Triggered on issue events', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['github.issues']}, 'workflow_run': {'description': 'Triggered when a workflow run completes', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['github.workflow_run']}}, 'rate_limits': {'default': '5000/hour', 'rules': {'list_issues': '60/minute', 'create_issue': '60/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 120}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': True, 'events': ['github.push', 'github.pull_request', 'github.issues', 'github.workflow_run'], 'secret_required': True}, 'supported_events': ['github.push', 'github.pull_request', 'github.issues', 'github.workflow_run'], 'supported_objects': ['repository', 'issue', 'pull_request', 'commit', 'release'], 'pagination': {'enabled': True, 'default_page_size': 30, 'max_page_size': 100, 'cursor_field': 'page'}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': False, 'webhooks': True, 'batching': False, 'streaming': False, 'pagination': True, 'file_upload': True, 'file_download': True, 'long_running': False}, 'permissions': {'read': ['repo', 'issues:read'], 'write': ['issues:write', 'pulls:write', 'workflow']}, 'health_check': {'endpoint': 'https://api.github.com/rate_limit', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://docs.github.com/rest', 'setup_guide': 'Create an OAuth App in GitHub developer settings and enable the required scopes.', 'example_prompt': 'Create a GitHub issue for bug reports'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class GithubConnector(BaseConnector):
    """GitHub (github) connector implementation."""

    name = "GitHub"
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
