# AutoFlow AI — Edge, TLS and Network Operations

**Status:** IMPLEMENTED + VERIFIED on local infrastructure (Step 4)

This document describes the production edge: TLS termination, the network
segmentation that keeps PostgreSQL and Redis off the public host, and the
trusted-proxy rules that decide which client IP the application believes.

---

## 1. Architecture

```
                        Internet
                            │
                    ┌───────▼────────┐
                    │  Caddy (edge)  │  publishes 80 / 443 only
                    │  TLS + proxy   │  automatic ACME (public domain)
                    └───┬────────┬───┘  internal CA (localhost)
                        │        │
              /api/*,   │        │  everything else
              /health,  │        │
              /readiness│        │
                        │        │
                ┌───────▼──┐  ┌──▼────────┐
                │ backend  │  │ frontend  │      edge network
                │  :8000   │  │  :3000    │   172.28.0.0/24
                └───┬──────┘  └───────────┘
                    │
        ┌───────────┼────────────┐
        │           │            │
   ┌────▼───┐  ┌────▼───┐  ┌─────▼──────┐
   │postgres│  │ redis  │  │ celery /   │    autoflow network
   │ :5432  │  │ :6379  │  │ backup     │    internal: true
   └────────┘  └────────┘  └────────────┘    (no host ports, no route off-host)
```

The `caddy` service is the **only** container in
`docker-compose.production.yml` that declares `ports:`. Every other service
is reachable on the private Docker networks only.

---

## 2. Network model

| Network | Flag | Members | Reachable from host? |
|---------|------|---------|----------------------|
| `edge` | bridge, pinned subnet | caddy, backend, celery-worker, frontend, backup | Only through Caddy's 80/443 |
| `autoflow` | `internal: true` | postgres, redis, backend, celery-worker, backup | **Never** |

Why both: the backend and workers need outbound internet (AI providers,
Sentry, S3), so they join `edge`. PostgreSQL and Redis have no route off the
host at all — `internal: true` removes the default gateway — so even a
misconfigured `ports:` entry could not expose them usefully, and no other
container on the host can reach them.

**Verify at any time:**

```bash
docker compose -f docker-compose.production.yml config --format json \
  | python -c "import json,sys; d=json.load(sys.stdin); [print(s, [p.get('published') for p in (v.get('ports') or [])]) for s,v in d['services'].items()]"
# caddy [80, 443, 443]; every other service []
```

---

## 3. TLS modes

Certificate handling is driven entirely by `SITE_ADDRESS`:

| `SITE_ADDRESS` | Behaviour |
|----------------|-----------|
| a public hostname (`app.example.com`) | Automatic HTTPS via ACME (Let's Encrypt / ZeroSSL), including the 80→443 redirect |
| `localhost` (default) | Caddy's internal CA — used for pre-production validation only |

There is one Caddyfile (`infra/docker/caddy/Caddyfile`) and one shared routes
file (`infra/docker/caddy/routes.caddy`) used by **both** modes, so local
validation exercises the exact production routing.

Optional: add `email ops@example.com` to the global options block in the
Caddyfile to receive certificate-expiry notices. It is omitted by default so
no address is guessed.

---

## 4. Routing

| Path | Upstream |
|------|----------|
| `/api/*` | `backend:8000` (with `flush_interval -1` so SSE is never buffered) |
| `/health`, `/health/db`, `/readiness` | `backend:8000` |
| `/docs`, `/redoc`, `/openapi.json` | `backend:8000` (the app returns 404 for these in production) |
| everything else | `frontend:3000` |

HSTS is asserted at the edge for the frontend responses and for the health
paths (which short-circuit the backend's security-headers middleware). API
responses get HSTS/CSP/nosniff/X-Frame-Options from the backend middleware.

---

## 5. Environment variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SITE_ADDRESS` | ✅ for real TLS | `localhost` | Public hostname served by the edge |
| `HTTP_PORT` | No | `80` | Published HTTP port |
| `HTTPS_PORT` | No | `443` | Published HTTPS port (TCP + UDP/HTTP3) |
| `EDGE_SUBNET` | No | `172.28.0.0/24` | Fixed subnet of the `edge` network |
| `TRUSTED_PROXY_CIDRS` | No | `172.28.0.0/24` | Peer ranges allowed to set `X-Forwarded-For` |
| `CORS_ORIGINS` | ✅ | `["https://yourdomain.com"]` | Must be the HTTPS origin |
| `NEXT_PUBLIC_API_URL` | ✅ | `https://yourdomain.com/api/v1` | Baked into the frontend at build time |

`.env.example` contains placeholders only. `EDGE_SUBNET` and
`TRUSTED_PROXY_CIDRS` must stay in sync; a test asserts they do.

---

## 6. Trusted-proxy / client IP semantics

Behind the edge, `request.client.host` is Caddy for every visitor. The client
address is resolved by `backend/app/core/client_ip.py`:

1. If no trusted ranges are configured → use the direct peer (fail-closed).
2. If the direct peer is **not** inside `TRUSTED_PROXY_CIDRS` → use the direct
   peer and **ignore `X-Forwarded-For` entirely** (a spoofing client gets
   nowhere).
3. Otherwise walk `X-Forwarded-For` right-to-left, skipping trusted proxies,
   and take the first untrusted address — the real client.

The resolved address is published on `request.state.client_ip`, used as the
rate-limit key, and recorded on audit events. `uvicorn` is also started with
`--proxy-headers --forwarded-allow-ips <same CIDRs>` so `request.client`
agrees.

**Security property:** with the default (empty or mismatched) allowlist the
system trusts nobody; with the production default it trusts exactly the
`edge` network, which contains only AutoFlow's own containers.

---

## 7. Deploying with real TLS

1. Point DNS (`A`/`AAAA`) for your hostname at the server.
2. Ensure inbound 80 and 443 are open (80 is needed for the ACME HTTP
   challenge and the HTTPS redirect).
3. In `.env`:
   ```
   SITE_ADDRESS=app.example.com
   NEXT_PUBLIC_SITE_URL=https://app.example.com
   NEXT_PUBLIC_API_URL=https://app.example.com/api/v1
   CORS_ORIGINS=["https://app.example.com"]
   ```
4. Rebuild the frontend (the public URL is a build argument) and start:
   ```bash
   docker compose -f docker-compose.production.yml up -d --build
   ```
5. Confirm: `curl -I https://app.example.com/readiness`

Certificates are stored in the `caddydata` volume and renewed automatically.

---

## 8. Local validation (no public domain required)

```bash
# Start the stack with the local-TLS harness (site = localhost, internal CA)
docker compose -f docker-compose.production.yml \
               -f docker-compose.edge-local-test.yml up -d --build

# TLS + redirect
curl -sI http://localhost/            # 308 -> https://localhost/
echo | openssl s_client -connect localhost:443 -servername localhost 2>/dev/null \
  | openssl x509 -noout -issuer -dates

# Readiness through the edge
curl -sk https://localhost/readiness   # {"status":"healthy","database":"connected"}

# Datastores must not be published
docker inspect autoflow-ai-postgres-1 --format '{{json .NetworkSettings.Ports}}'   # {"5432/tcp":null}
```

### Verified results (local, 2026-09-20)

| Check | Result |
|-------|--------|
| HTTP → HTTPS redirect | ✅ 308 |
| TLS certificate served | ✅ Caddy Local Authority (internal CA) |
| `/readiness` through the edge | ✅ `{"status":"healthy","database":"connected"}` |
| Security headers (API) | ✅ HSTS, CSP, nosniff, X-Frame-Options |
| Security headers (edge/frontend + health) | ✅ HSTS, nosniff, Referrer-Policy |
| postgres / redis / backend / frontend host bindings | ✅ `null` (not published) |
| `caddy` host bindings | ✅ 80, 443 (tcp+udp) |
| `autoflow` network internal flag | ✅ `true` |
| Forged `X-Forwarded-For` from an untrusted peer | ✅ ignored (130 rotated values → 120 allowed + 10 × 429) |
| Trusted-proxy forwarded IP honoured | ✅ two forwarded IPs → two independent buckets |
| SSE not buffered through the edge | ✅ identical frame timing direct vs. proxied (2.10s spread both) |

---

## 9. Operational notes

- **Adding a route:** edit `infra/docker/caddy/routes.caddy`, then
  `docker compose -f docker-compose.production.yml restart caddy`.
- **Backup service:** the `backup` container joins both networks so it can
  reach PostgreSQL internally and S3 externally. Nothing there changed — see
  `docs/BACKUP_OPERATIONS.md`.
- **Health checks:** the `caddy` healthcheck asserts TLS is actually being
  served (`nc -z 127.0.0.1 443`), not merely that the process exists.
- **Do not** re-add `ports:` to postgres/redis/backend/frontend, and do not
  use `docker-compose.override.yml` in production — it re-publishes those
  ports for local development.
- **Known gap (P3):** `/health`, `/health/db` and `/readiness` short-circuit
  before the backend's security-headers middleware; the edge adds HSTS for
  those paths. The remaining headers are irrelevant for non-sensitive
  readiness JSON.
