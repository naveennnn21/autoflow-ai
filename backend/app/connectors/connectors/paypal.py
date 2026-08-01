"""AutoFlow AI - PayPal connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'PayPal', 'version': '1.0.0', 'description': 'PayPal payments integration', 'category': 'payments', 'provider': 'paypal', 'module_name': 'paypal', 'authentication': {'type': 'oauth2', 'provider': 'paypal', 'supported_scopes': ['https://uri.paypal.com/services/payments/payment', 'https://uri.paypal.com/services/payments/refund', 'https://uri.paypal.com/services/subscriptions'], 'token_url': 'https://api-m.paypal.com/v1/oauth2/token', 'auth_url': '', 'requires_refresh': True, 'credential_fields': ['client_id', 'client_secret', 'access_token', 'refresh_token']}, 'actions': {'create_payment': {'description': 'Create a payment (order)', 'kind': 'create', 'inputs': {'amount': 'string', 'currency': 'string', 'intent': 'string', 'return_url': 'string', 'cancel_url': 'string'}, 'outputs': {'payment_id': 'string', 'approval_url': 'string', 'status': 'string'}, 'required_permissions': ['payments'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'capture_payment': {'description': 'Capture an authorized payment', 'kind': 'update', 'inputs': {'order_id': 'string'}, 'outputs': {'capture_id': 'string', 'status': 'string'}, 'required_permissions': ['payments'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'refund_payment': {'description': 'Refund a captured payment', 'kind': 'create', 'inputs': {'capture_id': 'string', 'amount': 'string', 'currency': 'string'}, 'outputs': {'refund_id': 'string', 'status': 'string'}, 'required_permissions': ['refunds'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'get_payment': {'description': 'Fetch payment details', 'kind': 'read', 'inputs': {'order_id': 'string'}, 'outputs': {'order': 'object'}, 'required_permissions': ['payments'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'create_subscription': {'description': 'Create a subscription plan', 'kind': 'create', 'inputs': {'plan_id': 'string', 'subscriber_email': 'string', 'return_url': 'string'}, 'outputs': {'subscription_id': 'string', 'status': 'string'}, 'required_permissions': ['subscriptions'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'payment_completed': {'description': 'Triggered when a payment is completed', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['paypal.payment_completed']}, 'payment_failed': {'description': 'Triggered when a payment fails', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['paypal.payment_failed']}, 'subscription_cancelled': {'description': 'Triggered when a subscription is cancelled', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['paypal.subscription_cancelled']}}, 'rate_limits': {'default': '500/minute', 'rules': {'create_payment': '60/minute', 'refund_payment': '60/minute'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': True, 'events': ['paypal.payment_completed', 'paypal.payment_failed', 'paypal.subscription_cancelled'], 'secret_required': True}, 'supported_events': ['paypal.payment_completed', 'paypal.payment_failed', 'paypal.subscription_cancelled'], 'supported_objects': ['payment', 'order', 'refund', 'subscription'], 'pagination': {'enabled': True, 'default_page_size': 20, 'max_page_size': 100, 'cursor_field': 'page'}, 'batching': {'enabled': False, 'max_batch_size': 50}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': False, 'webhooks': True, 'batching': False, 'streaming': False, 'pagination': True, 'file_upload': False, 'file_download': False, 'long_running': False}, 'permissions': {'read': ['payments'], 'write': ['payments', 'refunds', 'subscriptions']}, 'health_check': {'endpoint': 'https://api-m.paypal.com/v1/identity/oauth2/userinfo', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://developer.paypal.com', 'setup_guide': 'Create a PayPal REST app to get client ID and secret, and configure webhooks.', 'example_prompt': 'Charge a customer for a subscription renewal'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class PaypalConnector(BaseConnector):
    """PayPal (paypal) connector implementation."""

    name = "PayPal"
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
