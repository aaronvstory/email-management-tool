# Production Readiness Plan

**Date:** October 2, 2025
**Deadline:** URGENT - Production deployment imminent
**Status:** Phase 1B Complete → Accelerating to Production

## Critical Path (Priority Order)

### ✅ COMPLETED

- [x] Phase 0: DB hardening (indices, WAL, fetch_counts optimization)
- [x] Phase 1A: Stats service + caching
- [x] Phase 1B: Core blueprints (auth, dashboard, stats, moderation, interception)
- [x] Dependency injection support in db utilities
- [x] IMAP/SMTP credentials configured (3 real accounts + 1 test)
- [x] Interception lifecycle tests (fetch → hold → edit → release)
- [x] UI modernization (toast notifications, dark theme, edit modal)

### 🔥 CRITICAL - MUST COMPLETE FOR PRODUCTION

#### 1. Verify Core Functionality Works (TODAY)

- [ ] **Smoke test**: Start app, send test email via SMTP proxy, verify interception
- [ ] **IMAP monitoring**: Confirm watcher threads start and can fetch mail
- [ ] **Hold/Release flow**: Manually intercept → edit → release → confirm delivery
- [ ] **Account management**: Add/edit/delete accounts via UI
- [ ] **Document any blockers immediately**

#### 2. Complete Phase 1C: Blueprint Migration (1-2 hours)

**Remaining routes in simple_app.py to extract:**

**Priority 1 (Email CRUD) - CRITICAL:**

- `/emails` → `app/routes/emails.py`
- `/email/<int:email_id>` → `app/routes/emails.py`
- `/email/<int:email_id>/action` → `app/routes/emails.py`
- `/email/<int:email_id>/full` → `app/routes/emails.py`
- `/api/emails/pending` → `app/routes/emails.py`
- `/api/email/<email_id>/reply-forward` → `app/routes/emails.py`
- `/api/email/<email_id>/download` → `app/routes/emails.py`

**Priority 2 (Accounts) - HIGH:**

- `/accounts` → `app/routes/accounts.py`
- `/accounts/add` → `app/routes/accounts.py`
- `/api/accounts` → `app/routes/accounts.py`
- `/api/accounts/<account_id>` → `app/routes/accounts.py` (consolidate duplicates!)
- `/api/accounts/<account_id>/health` → `app/routes/accounts.py`
- `/api/accounts/<account_id>/test` → `app/routes/accounts.py`
- `/api/accounts/export` → `app/routes/accounts.py`
- `/api/detect-email-settings` → `app/routes/accounts.py`
- `/api/test-connection/<connection_type>` → `app/routes/accounts.py`

**Priority 3 (Compose/Send) - HIGH:**

- `/compose` → `app/routes/compose.py`
- `/inbox` → `app/routes/compose.py`
- (Reply/forward handlers already in emails.py)

**Priority 4 (Diagnostics) - MEDIUM:**

- `/diagnostics` → `app/routes/diagnostics.py`
- `/diagnostics/<account_id>` → `app/routes/diagnostics.py`
- `/api/diagnostics/<account_id>` → `app/routes/diagnostics.py`
- `/diagnostics/test` → `app/routes/diagnostics.py`
- `/api/events` → `app/routes/diagnostics.py`

**Can defer to post-production:**

- Test-only routes (`/test/*`, `/interception-test`, etc.) → Keep in simple_app or move to test blueprint

#### 3. Stabilize Test Infrastructure (2-3 hours)

- [ ] Create production-grade `tests/conftest.py`:
  - Flask app fixture
  - Test client fixture
  - Authenticated client fixture
  - Temporary database fixture with proper cleanup
  - Mock IMAP/SMTP fixtures
- [ ] Fix import errors in existing tests (62 failing tests)
- [ ] Create import compatibility layer if needed
- [ ] Run full test suite → target 80%+ pass rate

#### 4. Integration Testing with Real Accounts (1 hour)

- [ ] Create `tests/integration/test_live_email_flow.py`
- [ ] Gated by `ENABLE_LIVE_EMAIL_TESTS=1` in .env
- [ ] Test scenarios:
  - Compose → Send → Intercept → Edit → Release
  - Inbound → Auto-hold (rule-based) → Release
  - Account connection health checks
  - Multi-account forwarding
- [ ] Use Gmail (ndayijecika@gmail.com) + Hostinger (mcintyre@corrinbox.com)

### 🚀 PRODUCTION DEPLOYMENT PREP

#### 5. Documentation (1 hour)

- [ ] Update `CLAUDE.md` with:
  - Current architecture (post-blueprint migration)
  - Dependency injection patterns
  - Live testing instructions
  - Production deployment checklist
- [ ] Create `DEPLOYMENT.md`:
  - System requirements
  - Installation steps
  - Configuration (`.env` setup)
  - Starting the service
  - Monitoring/logging
  - Troubleshooting

#### 6. Production Configuration (30 mins)

- [ ] Review `.env.example` for completeness
- [ ] Ensure `.gitignore` excludes all secrets
- [ ] Add production-specific settings:
  - `FLASK_DEBUG=false`
  - `LOG_LEVEL=INFO`
  - Proper `FLASK_SECRET_KEY`
  - SSL certificate paths if needed

#### 7. Final Validation (1 hour)

- [ ] Run app with production config
- [ ] Execute full integration test suite
- [ ] Verify all critical paths work:
  - User login/logout
  - Account CRUD
  - Email compose/send
  - Interception (SMTP + IMAP paths)
  - Hold/edit/release workflow
  - Dashboard stats real-time updates
- [ ] Load testing (optional): Basic Locust scenario

### 📊 CURRENT STATUS SUMMARY

**Database:**

- ✅ 4 email accounts configured
- ✅ WAL mode active
- ✅ Performance indices in place
- ✅ Encryption key present

**Codebase:**

- ✅ ~40% routes migrated to blueprints
- ⚠️ ~60% routes still in simple_app.py (but functional)
- ✅ DI-ready database layer
- ⚠️ Type-checking warnings (non-blocking)

**Testing:**

- ✅ 48/110 tests passing (44%)
- ⚠️ 62 tests failing (fixture/import issues)
- ✅ Core interception flow validated
- ❌ No live integration tests yet

**Known Issues:**

1. Multiple duplicate routes for same endpoint (e.g., `/api/accounts/<account_id>` appears twice)
2. Test infrastructure needs fixtures overhaul
3. No CI/CD pipeline
4. Type hints need cleanup (non-critical)

## Execution Strategy

### Phase 1: Rapid Stabilization (4-6 hours)

1. ✅ Verify app runs and core flows work (smoke test)
2. 🔄 Complete blueprint migration (Phase 1C)
3. 🔄 Fix test infrastructure
4. 🔄 Create live integration tests

### Phase 2: Production Hardening (2-3 hours)

5. 📝 Complete documentation
6. ⚙️ Production configuration review
7. ✅ Final validation + smoke tests

### Phase 3: Deployment (1 hour)

8. Deploy to production environment
9. Monitor initial operation
10. Document any post-deployment fixes

**Total estimated time: 7-10 hours of focused work**

## Success Criteria

### Minimum Viable Production (MVP):

- [x] App starts without errors
- [ ] All blueprints registered and functional
- [ ] 80%+ test pass rate
- [ ] Live integration tests pass with real accounts
- [ ] Documentation complete
- [ ] Core workflows validated end-to-end

### Full Production Ready:

- [ ] 95%+ test coverage
- [ ] CI/CD pipeline active
- [ ] Performance testing complete
- [ ] Security audit passed
- [ ] Monitoring/alerting configured

## Risk Mitigation

**High Risk:**

- Blueprint migration breaks existing functionality → **Mitigation**: Test after each migration
- Live account credentials expire → **Mitigation**: Document credential refresh process
- Test failures block deployment → **Mitigation**: Prioritize fixing critical path tests only

**Medium Risk:**

- Type checking errors cause runtime issues → **Mitigation**: Add runtime validation
- Performance degradation under load → **Mitigation**: Basic load test before deployment

**Low Risk:**

- Documentation incomplete → **Mitigation**: Can be updated post-deployment
- Some test failures → **Mitigation**: Acceptable if core functionality works

## Next Actions (Immediate)

1. **RUN SMOKE TEST** - Verify app works now
2. **START PHASE 1C** - Migrate email routes first (highest priority)
3. **FIX CONFTEST** - Unblock test suite
4. **INTEGRATION TEST** - Validate with real accounts

---

**Last Updated:** October 2, 2025 22:30
**Owner:** Development Team
**Status:** IN PROGRESS - URGENT
