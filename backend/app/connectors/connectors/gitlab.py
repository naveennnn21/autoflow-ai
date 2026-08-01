"""AutoFlow AI - GitLab connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'GitLab', 'version': '1.0.0', 'description': 'GitLab repositories, issues, and merge requests', 'category': 'developer', 'provider': 'gitlab', 'module_name': 'gitlab', 'authentication': {'type': 'oauth2', 'provider': 'gitlab', 'supported_scopes': ['api', 'read_repository'], 'token_url': 'https://gitlab.com/oauth/token', 'auth_url': 'https://gitlab.com/oauth/authorize', 'requires_refresh': True, 'credential_fields': ['client_id', 'client_secret', 'access_token', 'refresh_token']}, 'actions': {'create_issue': {'description': 'Create an issue in a project', 'kind': 'create', 'inputs': {'project_id': 'string', 'title': 'string', 'description': 'text', 'labels': 'list'}, 'outputs': {'issue_iid': 'integer', 'issue_url': 'string'}, 'required_permissions': ['api'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_issues': {'description': 'List project issues', 'kind': 'list', 'inputs': {'project_id': 'string', 'state': 'string', 'per_page': 'integer'}, 'outputs': {'issues': 'list'}, 'required_permissions': ['api'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'create_merge_request': {'description': 'Open a merge request', 'kind': 'create', 'inputs': {'project_id': 'string', 'source_branch': 'string', 'target_branch': 'string', 'title': 'string', 'description': 'text'}, 'outputs': {'mr_iid': 'integer', 'mr_url': 'string'}, 'required_permissions': ['api'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'get_project': {'description': 'Fetch project metadata', 'kind': 'read', 'inputs': {'project_id': 'string'}, 'outputs': {'project': 'object'}, 'required_permissions': ['api'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_pipelines': {'description': 'List CI pipelines', 'kind': 'list', 'inputs': {'project_id': 'string', 'per_page': 'integer'}, 'outputs': {'pipelines': 'list'}, 'required_permissions': ['api'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'push': {'description': 'Triggered on push events', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['gitlab.push']}, 'merge_request': {'description': 'Triggered on merge request events', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['gitlab.merge_request']}, 'pipeline': {'description': 'Triggered when a pipeline status changes', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['gitlab.pipeline']}}, 'rate_limits': {'default': '600/hour', 'rules': {'list_issues': '60/minute', 'create_issue': '60/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 120}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': True, 'events': ['gitlab.push', 'gitlab.merge_request', 'gitlab.pipeline'], 'secret_required': True}, 'supported_events': ['gitlab.push', 'gitlab.merge_request', 'gitlab.pipeline'], 'supported_objects': ['project', 'issue', 'merge_request', 'pipeline'], 'pagination': {'enabled': True, 'default_page_size': 20, 'max_page_size': 100, 'cursor_field': 'page'}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': False, 'webhooks': True, 'batching': False, 'streaming': False, 'pagination': True, 'file_upload': True, 'file_download': True, 'long_running': False}, 'permissions': {'read': ['read_repository'], 'write': ['api']}, 'health_check': {'endpoint': 'https://gitlab.com/api/v4/projects', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://docs.gitlab.com/api', 'setup_guide': 'Create an OAuth application in GitLab and configure the api scope.', 'example_prompt': 'Create a GitLab issue for feature requests'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class GitlabConnector(BaseConnector):
    """GitLab (gitlab) connector implementation."""

    name = "GitLab"
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
