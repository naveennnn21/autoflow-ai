# AutoFlow AI — Production Environment Variables

**NEVER commit actual secret values.** This document describes each variable's purpose.

## Backend Environment Variables

| Variable | Required | Purpose | Default |
|----------|----------|---------|---------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string (asyncpg) | — |
| `REDIS_URL` | ✅ | Redis connection string for caching | — |
| `CELERY_BROKER_URL` | ✅ | Redis URL for Celery message broker | — |
| `CELERY_RESULT_BACKEND` | ✅ | Redis URL for Celery task results | — |
| `SECRET_KEY` | ✅ | JWT signing key (64+ chars random) | — |
| `ENVIRONMENT` | ✅ | `production` or `development` | `development` |
| `DEBUG` | No | Enable debug mode (auto-false in production) | `true` |
| `LOG_LEVEL` | No | Logging level | `INFO` |
| `CORS_ORIGINS` | No | JSON array of allowed origins | `["http://localhost:3000"]` |
| `SENTRY_DSN` | No | Sentry error tracking DSN | — |
| `OPENAI_API_KEY` | No | OpenAI API key for AI planner | — |
| `ANTHROPIC_API_KEY` | No | Anthropic API key for AI planner | — |
| `GEMINI_API_KEY` | No | Google Gemini API key | — |
| `OPENROUTER_API_KEY` | No | OpenRouter API key | — |
| `AI_DEFAULT_MODEL` | No | Default LLM model | `gpt-4o` |
| `AI_MAX_TOKENS` | No | Max tokens per AI request | `4096` |
| `AI_TEMPERATURE` | No | AI temperature | `0.2` |
| `STRIPE_SECRET_KEY` | No | Stripe payment processing key | — |
| `STRIPE_WEBHOOK_SECRET` | No | Stripe webhook verification secret | — |

## PostgreSQL Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `POSTGRES_USER` | ✅ | Database username |
| `POSTGRES_PASSWORD` | ✅ | Database password |
| `POSTGRES_DB` | No | Database name (default: `autoflow`) |

## Redis Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `REDIS_PASSWORD` | ✅ | Redis authentication password |

## Frontend Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `NEXT_PUBLIC_API_URL` | ✅ | Backend API base URL |
| `NEXT_PUBLIC_SITE_URL` | No | Public site URL |

## Security Behavior

- `SECRET_KEY` validation: Production requires non-default secret key
- `DEBUG`: Auto-disabled when `ENVIRONMENT=production`
- `CORS_ORIGINS`: Must be explicitly set for production domain
- CSRF: Enabled in production, disabled in development
- HSTS: Enabled in production (`max-age=31536000`)
- Swagger: Disabled in production (404 on `/docs`, `/redoc`, `/openapi.json`)
