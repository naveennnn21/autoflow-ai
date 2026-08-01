"""AutoFlow AI - Stripe connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Stripe', 'version': '1.0.0', 'description': 'Stripe payment processing integration', 'category': 'payments', 'provider': 'stripe', 'module_name': 'stripe', 'authentication': {'type': 'api_key', 'provider': 'stripe', 'supported_scopes': ['payment_intent', 'subscription', 'invoice', 'customer', 'refund'], 'token_url': '', 'auth_url': '', 'requires_refresh': False, 'credential_fields': ['secret_key', 'publishable_key', 'webhook_secret']}, 'actions': {'create_payment': {'description': 'Create a payment intent', 'kind': 'create', 'inputs': {'amount': 'integer', 'currency': 'string', 'description': 'string', 'customer_id': 'string', 'payment_method_id': 'string', 'metadata': 'json'}, 'outputs': {'payment_intent_id': 'string', 'client_secret': 'string', 'status': 'string'}, 'required_permissions': ['payment_intent'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'create_subscription': {'description': 'Create a subscription', 'kind': 'create', 'inputs': {'customer_id': 'string', 'price_id': 'string', 'trial_period_days': 'integer', 'metadata': 'json'}, 'outputs': {'subscription_id': 'string', 'status': 'string'}, 'required_permissions': ['subscription'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'create_invoice': {'description': 'Create an invoice', 'kind': 'create', 'inputs': {'customer_id': 'string', 'description': 'string', 'metadata': 'json'}, 'outputs': {'invoice_id': 'string', 'status': 'string'}, 'required_permissions': ['invoice'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'refund_payment': {'description': 'Refund a payment', 'kind': 'create', 'inputs': {'payment_intent_id': 'string', 'amount': 'integer', 'reason': 'string'}, 'outputs': {'refund_id': 'string', 'status': 'string'}, 'required_permissions': ['refund'], 'idempotent': True, 'long_running': False, 'streaming': False}, 'list_customers': {'description': 'List customers', 'kind': 'list', 'inputs': {'limit': 'integer', 'email': 'string'}, 'outputs': {'customers': 'list'}, 'required_permissions': ['customer'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'get_customer': {'description': 'Fetch a customer', 'kind': 'read', 'inputs': {'customer_id': 'string'}, 'outputs': {'customer': 'object'}, 'required_permissions': ['customer'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'payment_succeeded': {'description': 'Payment completed successfully', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['stripe.payment_intent.succeeded']}, 'payment_failed': {'description': 'Payment failed', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['stripe.payment_intent.payment_failed']}, 'subscription_updated': {'description': 'Subscription status changed', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['stripe.customer.subscription.updated']}, 'invoice_paid': {'description': 'Invoice paid', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['stripe.invoice.paid']}}, 'rate_limits': {'default': '100/second', 'rules': {'create_payment': '25/second', 'list_customers': '25/second'}}, 'retry_policy': {'max_attempts': 4, 'base_delay': 0.5, 'max_delay': 30.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': True, 'events': ['stripe.payment_intent.succeeded', 'stripe.payment_intent.payment_failed', 'stripe.customer.subscription.updated', 'stripe.invoice.paid'], 'secret_required': True}, 'supported_events': ['stripe.payment_intent.succeeded', 'stripe.payment_intent.payment_failed', 'stripe.customer.subscription.updated', 'stripe.invoice.paid'], 'supported_objects': ['payment_intent', 'subscription', 'invoice', 'customer', 'refund'], 'pagination': {'enabled': True, 'default_page_size': 10, 'max_page_size': 100, 'cursor_field': 'starting_after'}, 'batching': {'enabled': False, 'max_batch_size': 100}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': False, 'webhooks': True, 'batching': False, 'streaming': False, 'pagination': True, 'file_upload': False, 'file_download': False, 'long_running': False}, 'permissions': {'read': ['customer'], 'write': ['payment_intent', 'subscription', 'invoice', 'refund']}, 'health_check': {'endpoint': 'https://api.stripe.com/v1/balance', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://docs.stripe.com/api', 'setup_guide': 'Get your Stripe secret key and configure the webhook signing secret.', 'example_prompt': 'Charge a customer for a subscription renewal'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['stripe']}


class StripeConnector(BaseConnector):
    """Stripe (stripe) connector implementation."""

    name = "Stripe"
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
