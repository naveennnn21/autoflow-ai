# AutoFlow AI — Implementation Roadmap

**Date:** September 7, 2026  
**Based on:** PROJECT_AUDIT.md findings  
**Target:** Production deployment readiness

---

## Priority Legend

| Priority | Meaning | Timeline |
|----------|---------|----------|
| **P0** | Critical / Security / Blocking | Must fix NOW |
| **P1** | Production requirement | Must fix before deploy |
| **P2** | Important product feature | Fix within 1 week |
| **P3** | Enhancement | Fix within 1 month |
| **P4** | Future / Optional | Backlog |

---

## P0 — Critical / Security / Blocking (Fix NOW)

### SEC-001: Debug Authentication Bypass
**Severity:** CRITICAL  
**File:** `backend/app/api/v1/deps.py`  
**Issue:** X-User-ID and X-Org-ID headers are accepted in debug mode, allowing any request to impersonate any user/org.  
**Fix:** Remove debug header bypass entirely, or gate it behind `settings.debug and settings.environment == "development"`.  
**Effort:** 1 hour  
**Impact:** Without this fix, any request can access any tenant's data.

### SEC-002: Hardcoded Development Secret Key
**Severity:** CRITICAL  
**File:** `backend/app/core/config.py`  
**Issue:** Default `secret_key` is a hardcoded string. If not overridden in production, all JWTs are signed with a known key.  
**Fix:** Fail startup if secret_key is the default value in production. Add validation in Settings.  
**Effort:** 30 minutes  
**Impact:** Without this fix, JWTs can be forged.

### SEC-003: No Rate Limiting on Auth Endpoints
**Severity:** HIGH  
**File:** `backend/app/api/v1/routers/auth.py`  
**Issue:** No rate limiting on `/auth/login`, `/auth/register`, `/auth/password-reset`. Enables brute force attacks.  
**Fix:** Add per-IP rate limiting (5 attempts/minute for login, 3/hour for password reset).  
**Effort:** 2 hours  
**Impact:** Account compromise risk.

---

## P1 — Production Requirement (Fix Before Deploy)

### DB-001: Alembic Migration Infrastructure
**Severity:** HIGH  
**Files:** New `alembic.ini`, `alembic/env.py`, migration scripts  
**Issue:** Using `create_all` for database setup. No migration history, no upgrade path.  
**Fix:** Initialize Alembic, generate initial migration from existing models, add to CI/CD.  
**Effort:** 4 hours  
**Impact:** Cannot deploy schema changes safely.

### SEC-004: Account Lockout
**Severity:** HIGH  
**File:** `backend/app/api/v1/routers/auth.py`  
**Issue:** No lockout after failed login attempts.  
**Fix:** Track failed attempts per email/IP. Lock account after 5 failures for 15 minutes.  
**Effort:** 3 hours  
**Impact:** Brute force vulnerability.

### SEC-005: CSRF Protection
**Severity:** HIGH  
**Files:** `backend/app/middleware/manager.py`, new CSRF middleware  
**Issue:** No CSRF tokens on state-changing endpoints.  
**Fix:** Implement CSRF middleware for browser-based requests (skip for API key auth).  
**Effort:** 4 hours  
**Impact:** Cross-site request forgery risk.

### DEP-001: Production Docker Compose
**Severity:** MEDIUM  
**File:** New `docker-compose.production.yml`  
**Issue:** No production-ready Docker Compose with proper secrets, replicas, and networking.  
**Fix:** Create production compose with: separate worker service, health checks, resource limits, secrets management.  
**Effort:** 4 hours  
**Impact:** Cannot deploy to production.

### DEP-002: Celery Worker Configuration
**Severity:** MEDIUM  
**Files:** `backend/app/tasks/__init__.py`, worker startup  
**Issue:** Celery is configured but no worker is running. Background jobs (scheduled workflows, retries) won't execute.  
**Fix:** Add Celery worker to docker-compose, implement scheduled workflow task.  
**Effort:** 4 hours  
**Impact:** Scheduled workflows, background retries won't work.

### DEP-003: SSL/TLS Configuration
**Severity:** MEDIUM  
**Issue:** No HTTPS termination configured.  
**Fix:** Add nginx/caddy reverse proxy with Let's Encrypt, or document cloud load balancer setup.  
**Effort:** 2 hours  
**Impact:** Production requires HTTPS.

### SEC-006: Security Headers in Production
**Severity:** MEDIUM  
**Files:** `backend/app/middleware/manager.py`  
**Issue:** HSTS, CSP headers only in production mode but not fully configured.  
**Fix:** Configure full security headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options.  
**Effort:** 1 hour  
**Impact:** Browser security.

### DEP-004: Database Indexes
**Severity:** MEDIUM  
**Files:** New migration, model files  
**Issue:** Missing indexes on frequently queried columns.  
**Fix:** Add indexes on: `audit_log.created_at`, `execution_log.execution_id`, `workflow_node.workflow_id`.  
**Effort:** 1 hour  
**Impact:** Query performance.

---

## P2 — Important Product Feature (Fix Within 1 Week)

### FEAT-001: Loop Runtime Support
**Severity:** MEDIUM  
**Files:** `backend/app/runtime/executor.py`  
**Issue:** Loop nodes are defined in the compiler but not executed at runtime.  
**Fix:** Implement loop node handler in the executor.  
**Effort:** 6 hours  
**Impact:** Loop workflows won't execute.

### FEAT-002: Advanced Expression Evaluation
**Severity:** MEDIUM  
**Files:** `backend/app/runtime/executor.py`  
**Issue:** Condition expressions only support `==` and `!=`.  
**Fix:** Extend to support `<`, `>`, `<=`, `>=`, `contains`, `in`, `AND`, `OR`.  
**Effort:** 4 hours  
**Impact:** Complex conditions won't work.

### FEAT-003: Workflow Pause/Resume at Node Level
**Severity:** LOW  
**Files:** `backend/app/runtime/executor.py`  
**Issue:** Pause/resume works at execution level but not node level (e.g., pause before a specific step).  
**Fix:** Implement node-level pause checkpoints.  
**Effort:** 6 hours  
**Impact:** Granular control.

### FEAT-004: Webhook Endpoints for Triggers
**Severity:** MEDIUM  
**Files:** `backend/app/api/v1/routers/ai_workflow.py`  
**Issue:** No public webhook endpoint to receive external triggers.  
**Fix:** Add `/webhooks/{workflow_id}/{token}` endpoint that validates HMAC and triggers execution.  
**Effort:** 4 hours  
**Impact:** External trigger workflows.

### FEAT-005: Workflow Templates
**Severity:** MEDIUM  
**Files:** Template model, API  
**Issue:** Templates are stored but no UI to browse/use them.  
**Fix:** Add template marketplace UI, one-click workflow creation from template.  
**Effort:** 6 hours  
**Impact:** User onboarding.

### FEAT-006: Email Notifications
**Severity:** LOW  
**Files:** `backend/app/services/notification.py`  
**Issue:** Notification service exists but no email transport.  
**Fix:** Integrate Resend/SendGrid for email delivery.  
**Effort:** 4 hours  
**Impact:** User notifications.

### FEAT-007: Workflow Scheduling (Cron)
**Severity:** MEDIUM  
**Files:** `backend/app/tasks/`  
**Issue:** No scheduled workflow execution.  
**Fix:** Implement Celery beat schedule for cron-based workflow triggers.  
**Effort:** 6 hours  
**Impact:** Time-based automations.

---

## P3 — Enhancement (Fix Within 1 Month)

### ENH-001: API Versioning Strategy
**Effort:** 4 hours  
Plan for v2 API without breaking existing clients.

### ENH-002: OpenAPI Documentation Polish
**Effort:** 2 hours  
Add examples, response schemas, and better descriptions.

### ENH-003: Frontend Mobile Responsiveness
**Effort:** 8 hours  
Improve mobile layout for all pages.

### ENH-004: Accessibility Audit
**Effort:** 6 hours  
WCAG 2.1 AA compliance.

### ENH-005: SEO Optimization
**Effort:** 4 hours  
Meta tags, structured data, sitemap.

### ENH-006: APM Integration
**Effort:** 4 hours  
Add Sentry performance monitoring, custom metrics.

### ENH-007: API Key Authentication for External Access
**Effort:** 4 hours  
Allow API keys for programmatic access.

### ENH-008: Workflow Import/Export
**Effort:** 6 hours  
JSON/YAML import/export of workflow definitions.

### ENH-009: Team Management UI
**Effort:** 8 hours  
Invite members, manage roles, team settings.

### ENH-010: OAuth Provider Integration
**Effort:** 8 hours  
Google, GitHub, Microsoft sign-in.

---

## P4 — Future / Optional (Backlog)

| Item | Effort | Notes |
|------|--------|-------|
| Multi-language support (i18n) | 16h | Localize UI |
| Custom connector builder | 24h | User-defined connectors |
| Workflow marketplace | 16h | Community workflows |
| Advanced analytics | 12h | Custom dashboards, exports |
| API rate limiting per user | 4h | Quota management |
| Webhook debugging UI | 8h | Request/response inspector |
| Workflow diff visualization | 8h | Visual version comparison |
| AI-assisted debugging | 12h | Error explanation + fix suggestions |
| Mobile app | 40h | React Native |
| SSO/SAML | 16h | Enterprise auth |

---

## Implementation Order

### Phase 1: P0 Security (Day 1)
1. Fix debug auth bypass (SEC-001)
2. Fix hardcoded secret key (SEC-002)
3. Add auth rate limiting (SEC-003)

### Phase 2: P1 Infrastructure (Days 2-3)
4. Initialize Alembic migrations (DB-001)
5. Add account lockout (SEC-004)
6. Add CSRF protection (SEC-005)
7. Create production Docker Compose (DEP-001)
8. Configure Celery worker (DEP-002)
9. Add database indexes (DEP-004)
10. Configure security headers (SEC-006)

### Phase 3: P1 Deployment (Day 4)
11. Add SSL/TLS configuration (DEP-003)
12. Test production deployment end-to-end

### Phase 4: P2 Features (Week 2)
13. Implement loop runtime (FEAT-001)
14. Extend expression evaluation (FEAT-002)
15. Add webhook endpoints (FEAT-004)
16. Implement workflow scheduling (FEAT-007)
17. Add email notifications (FEAT-006)

### Phase 5: P3 Enhancements (Month 1)
18. Mobile responsiveness (ENH-003)
19. Accessibility audit (ENH-004)
20. SEO optimization (ENH-005)
21. API documentation (ENH-002)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Secret key compromise | HIGH if deployed | CRITICAL | P0 fix required |
| Tenant data leak via debug headers | HIGH if debug=true | CRITICAL | P0 fix required |
| Brute force attack | MEDIUM | HIGH | P0 rate limiting |
| Schema migration failure | HIGH | HIGH | P1 Alembic setup |
| Background job failure | MEDIUM | MEDIUM | P1 Celery config |
| SSL/TLS misconfiguration | MEDIUM | HIGH | P1 deployment testing |

---

## Success Criteria

After completing P0/P1 fixes, the platform must:

1. ✅ Reject requests with debug headers in production
2. ✅ Fail startup if using default secret key
3. ✅ Rate limit auth endpoints
4. ✅ Lock accounts after failed attempts
5. ✅ Support database migrations
6. ✅ Deploy via Docker Compose
7. ✅ Run Celery workers for background jobs
8. ✅ Serve over HTTPS
9. ✅ Pass security scan
10. ✅ All existing tests pass

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| P0 Security | 1 day | None |
| P1 Infrastructure | 3 days | P0 |
| P1 Deployment | 1 day | P1 Infrastructure |
| P2 Features | 1 week | P1 |
| P3 Enhancements | 1 month | P2 |

**Total to Production:** 5 days (P0+P1)  
**Total to Feature Complete:** 6 weeks (P0-P3)
