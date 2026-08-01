"""AutoFlow AI - Shopify connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {'name': 'Shopify', 'version': '1.0.0', 'description': 'Shopify e-commerce integration', 'category': 'ecommerce', 'provider': 'shopify', 'module_name': 'shopify', 'authentication': {'type': 'oauth2', 'provider': 'shopify', 'supported_scopes': ['read_products', 'write_products', 'read_orders', 'write_orders', 'read_customers'], 'token_url': 'https://{shop}.myshopify.com/admin/oauth/access_token', 'auth_url': 'https://{shop}.myshopify.com/admin/oauth/authorize', 'requires_refresh': False, 'credential_fields': ['shop', 'client_id', 'client_secret', 'access_token']}, 'actions': {'create_product': {'description': 'Create a product', 'kind': 'create', 'inputs': {'title': 'string', 'body_html': 'text', 'vendor': 'string', 'product_type': 'string', 'tags': 'list', 'price': 'string'}, 'outputs': {'product_id': 'integer', 'handle': 'string'}, 'required_permissions': ['write_products'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'update_product': {'description': 'Update a product', 'kind': 'update', 'inputs': {'product_id': 'integer', 'title': 'string', 'body_html': 'text', 'price': 'string', 'status': 'string'}, 'outputs': {'product_id': 'integer'}, 'required_permissions': ['write_products'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_orders': {'description': 'List orders', 'kind': 'list', 'inputs': {'status': 'string', 'limit': 'integer', 'since_id': 'integer'}, 'outputs': {'orders': 'list'}, 'required_permissions': ['read_orders'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'get_order': {'description': 'Fetch an order', 'kind': 'read', 'inputs': {'order_id': 'integer'}, 'outputs': {'order': 'object'}, 'required_permissions': ['read_orders'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'create_order': {'description': 'Create a draft order', 'kind': 'create', 'inputs': {'line_items': 'json', 'customer': 'json', 'email': 'string'}, 'outputs': {'order_id': 'integer'}, 'required_permissions': ['write_orders'], 'idempotent': False, 'long_running': False, 'streaming': False}, 'list_products': {'description': 'List products', 'kind': 'list', 'inputs': {'limit': 'integer', 'since_id': 'integer'}, 'outputs': {'products': 'list'}, 'required_permissions': ['read_products'], 'idempotent': False, 'long_running': False, 'streaming': False}}, 'triggers': {'order_created': {'description': 'Triggered when an order is created', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['shopify.orders_create']}, 'order_paid': {'description': 'Triggered when an order is paid', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['shopify.orders_paid']}, 'product_updated': {'description': 'Triggered when a product changes', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['shopify.products_update']}, 'customer_created': {'description': 'Triggered when a customer is created', 'kind': 'webhook', 'webhook': True, 'polling_interval_seconds': 0, 'cron': '', 'supported_events': ['shopify.customers_create']}}, 'rate_limits': {'default': '40/second', 'rules': {'list_orders': '2/second', 'create_product': '4/second'}}, 'retry_policy': {'max_attempts': 3, 'base_delay': 1.0, 'max_delay': 60.0, 'backoff_factor': 2.0}, 'timeouts': {'connect': 10, 'read': 30, 'write': 30, 'execute': 60}, 'polling': {'enabled': False, 'default_interval_seconds': 60}, 'webhooks': {'enabled': True, 'events': ['shopify.orders_create', 'shopify.orders_paid', 'shopify.products_update', 'shopify.customers_create'], 'secret_required': True}, 'supported_events': ['shopify.orders_create', 'shopify.orders_paid', 'shopify.products_update', 'shopify.customers_create'], 'supported_objects': ['product', 'order', 'customer', 'inventory'], 'pagination': {'enabled': True, 'default_page_size': 50, 'max_page_size': 250, 'cursor_field': 'since_id'}, 'batching': {'enabled': True, 'max_batch_size': 250}, 'streaming': {'enabled': False}, 'capabilities': {'actions': True, 'triggers': True, 'polling': False, 'webhooks': True, 'batching': True, 'streaming': False, 'pagination': True, 'file_upload': True, 'file_download': False, 'long_running': False}, 'permissions': {'read': ['read_products', 'read_orders', 'read_customers'], 'write': ['write_products', 'write_orders']}, 'health_check': {'endpoint': 'https://{shop}.myshopify.com/admin/api/2024-01/shop.json', 'method': 'GET', 'timeout_seconds': 10}, 'documentation': {'url': 'https://shopify.dev/docs/api/admin', 'setup_guide': 'Create a Shopify app, install it on the store, and capture the access token.', 'example_prompt': 'Send a thank-you email when an order is paid'}, 'deprecation_policy': {'deprecated': False, 'sunset_date': None, 'recommended_version': '1.0.0'}, 'dependencies': ['requests']}


class ShopifyConnector(BaseConnector):
    """Shopify (shopify) connector implementation."""

    name = "Shopify"
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
