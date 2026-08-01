# Connector Framework

Metadata-driven, multi-tenant connector framework generated from `metadata/connectors/*.yaml` (26 connectors).

## Architecture

| Layer | Modules |
|-------|---------|
| SDK | `base.py` - `BaseConnector` lifecycle contract |
| Registry | `registry.py`, `factory.py`, `manager.py`, `loader.py`, `discovery.py` |
| Auth | `authentication/oauth.py`, `api_key.py`, `bearer.py`, `basic.py`, `jwt.py` |
| Execution | `execution/executor.py`, `retry.py`, `rate_limit.py`, `cache.py`, `scheduler.py`, `polling.py`, `webhooks.py` |
| Transport | `transport/http.py`, `graphql.py`, `grpc.py`, `websocket.py` |
| Serialization | `serialization/serializer.py`, `validation.py` |
| Observability | `observability/metrics.py`, `logging.py`, `tracing.py` |
| Security | `security/credentials.py`, `secrets.py`, `permissions.py` |

## Connector SDK

Every connector inherits from `BaseConnector` and implements:

```python
connect()  disconnect()  authenticate()  refresh_token()
health()   discover()    validate()      execute_action()
execute_trigger()  poll()  webhook()  rollback()  cleanup()
```

## Generated connectors

| Module | Name | Auth | Actions | Triggers |
|--------|------|------|---------|----------|
| `airtable` | Airtable | api_key | 5 | 2 |
| `confluence` | Confluence | oauth2 | 5 | 2 |
| `discord` | Discord | bearer | 5 | 2 |
| `dropbox` | Dropbox | oauth2 | 6 | 2 |
| `github` | GitHub | oauth2 | 5 | 4 |
| `gitlab` | GitLab | oauth2 | 5 | 3 |
| `gmail` | Gmail | oauth2 | 5 | 2 |
| `google_drive` | Google Drive | oauth2 | 6 | 2 |
| `graphql_connector` | GraphQL | bearer | 4 | 2 |
| `grpc_connector` | gRPC | none | 4 | 1 |
| `jira` | Jira | oauth2 | 5 | 2 |
| `linear` | Linear | bearer | 5 | 3 |
| `mongodb` | MongoDB | basic | 5 | 1 |
| `mysql` | MySQL | basic | 4 | 2 |
| `notion` | Notion | oauth2 | 6 | 2 |
| `onedrive` | OneDrive | oauth2 | 6 | 2 |
| `outlook` | Outlook | oauth2 | 5 | 2 |
| `paypal` | PayPal | oauth2 | 5 | 3 |
| `postgres` | PostgreSQL | basic | 4 | 2 |
| `redis` | Redis | basic | 6 | 2 |
| `rest` | REST | none | 5 | 2 |
| `shopify` | Shopify | oauth2 | 6 | 4 |
| `slack` | Slack | oauth2 | 5 | 2 |
| `stripe` | Stripe | api_key | 6 | 4 |
| `teams` | Microsoft Teams | oauth2 | 5 | 1 |
| `webhook` | Webhook | webhook_secret | 2 | 1 |

## Authentication guide

- **OAuth2 / PKCE**: `OAuth2Strategy` with automatic refresh.
- **API key**: `APIKeyStrategy` (header, query, or bearer placement).
- **Bearer**: `BearerStrategy`.
- **Basic**: `BasicAuthStrategy`.
- **JWT**: `JWTStrategy` (PyJWT when available, stdlib HS256 fallback).
- **Webhook secret**: verified via `WebhookManager.verify()` (HMAC-SHA256).

## Adding a new connector

1. Add `metadata/connectors/<name>.yaml` with the full schema (name,
   version, authentication, actions, triggers, rate_limits,
   retry_policy, timeouts, polling, webhooks, supported_events,
   supported_objects, pagination, batching, streaming, capabilities,
   permissions, health_check, documentation, deprecation_policy).
2. Run `python scripts/generate.py backend.connectors --force`.
3. Run `python scripts/validate_connectors.py`.

## Resilience

Retry with backoff, circuit breaker, rate limiting, timeouts,
idempotency keys, response caching, duplicate event protection,
and fallback behavior are layered in `ActionExecutor`.

> Design notes:
> - `ConnectorManager.execute` invokes the connector directly; the
>   resilience layers in `ActionExecutor` (retry, circuit breaker,
>   rate limiting, cache, idempotency) are applied when callers
>   wrap actions with `ActionExecutor` explicitly. The manager path
>   is intentionally kept synchronous and thin.
> - Empty `organization_id` on a caller is treated as unscoped (no
>   tenant context) and skips the isolation check; callers that
>   need strict tenant isolation must pass a non-empty org id.

## Security

Credentials are encrypted at rest (`SecretManager`, Fernet when
available), tenant-scoped (`CredentialStore`), rotation-aware,
and gated by `PermissionValidator` with tenant-isolation checks.

## Validation

The 11-step pipeline `scripts/validate_connectors.py` runs:

1. AST validation
2. Import validation
3. Registry validation
4. Factory validation
5. Authentication validation
6. Trigger validation
7. Action validation
8. Integration tests
9. Documentation validation
10. Cleanliness scan
11. Coverage report
