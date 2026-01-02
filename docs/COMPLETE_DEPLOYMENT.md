# Complete Deployment Workflow

A step-by-step guide for getting Położne PoC fully deployed with all three applications.

---

## Prerequisites Checklist

- [ ] GitHub account with fork/access to all three repos
- [ ] Python 3.12+ installed locally
- [ ] Flutter SDK 3.24.0+ installed
- [ ] PostgreSQL 15+ installed locally (for development)
- [ ] Android SDK or iOS SDK (for mobile testing)
- [ ] Railway account (sign up at https://railway.app)
- [ ] Domain name (optional, Railway provides free *.up.railway.app domain)

---

## Phase 1: Backend Deployment to Production (Railway)

### 1A: Connect Repository to Railway

1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub (or create account)
3. Click **New Project** → **Deploy from GitHub repo**
4. Select `birth-journal-backend` repository
5. Railway auto-detects Python project

**Result:** Railway creates a project, queues for deployment

### 1B: Add PostgreSQL Database

1. In Railway project dashboard
2. Click **New** → **Database** → **PostgreSQL**
3. Wait for database to provision (2-5 minutes)
4. Railway automatically injects `DATABASE_URL` environment variable

**Result:** PostgreSQL is running, `DATABASE_URL` environment variable is available

### 1C: Configure Environment Variables

1. Click your backend service in Railway
2. Go to **Variables** tab
3. Click **Add Reference** (important: not manual entry)
4. Select PostgreSQL service → `DATABASE_URL`
   - This creates a reference variable (shows purple badge)

4. Add `JWT_SECRET`:
   - Click **New Variable**
   - Key: `JWT_SECRET`
   - Value: Generate with:
     ```powershell
     -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
     ```

5. Optional: Add `CORS_ORIGINS`:
   ```
   https://your-domain.com,https://*.railway.app
   ```

**Result:** All environment variables configured correctly

### 1D: Configure Post-Deploy Migrations

1. In Railway backend service
2. Click **Settings** tab
3. Scroll to **Post Deployment Hook**
4. In "Run" field, enter:
   ```
   python -m alembic upgrade head
   ```
5. Click **Save**

**Result:** Migrations run automatically after every deployment

### 1E: Initial Deployment & Migration

1. Railway automatically starts deployment (triggered by your configuration)
2. Watch **Deployments** tab for progress
3. Deployment completes in ~2-3 minutes
4. Post-deployment hook runs migrations automatically
5. Verify health endpoint:
   ```bash
   curl https://birth-journal-backend-production.up.railway.app/api/v1/health
   # Should return: {"ok": true, "db": true}
   ```

**Result:** Backend running, database initialized, migrations applied

### 1F: Verify Backend Works

```bash
# Test health check
curl https://birth-journal-backend-production.up.railway.app/api/v1/health

# Test authentication endpoint (should fail gracefully)
curl -X POST https://birth-journal-backend-production.up.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
```

**Result:** Backend API is responsive

---

## Phase 2: Local Development Setup

### 2A: Set Up Local Environment

```powershell
# Clone repositories (if not already cloned)
git clone https://github.com/your-org/birth-journal-backend.git
git clone https://github.com/your-org/birth-journal-midwife-app.git
git clone https://github.com/your-org/birth-journal-patient-app.git

cd birth-journal-backend
```

### 2B: Configure Local Database (Development)

```powershell
# Create local PostgreSQL user (Windows)
# Use PostgreSQL tools or pgAdmin

# Or use SQLite for quick local testing
$env:DATABASE_URL="sqlite:///./test.db"
$env:JWT_SECRET="dev-secret-key"
```

### 2C: Run Local Backend Server

```powershell
# Install dependencies
pip install -r requirements.txt

# Run migrations
python -m alembic upgrade head

# Start FastAPI server
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**Result:** Backend running locally at `http://localhost:8000/api/v1`

---

## Phase 3: Flutter Midwife App Deployment

### 3A: Set Up Midwife App

```powershell
cd birth-journal-midwife-app

# Get dependencies
flutter pub get

# Run analyzer and formatter checks
flutter analyze
flutter format .
```

### 3B: Deploy to Chrome (Web Testing)

```powershell
# Run the deploy script
.\deploy_to_chrome.ps1

# Script will:
# 1. Check if Railway backend is available
# 2. Use Railway URL or fall back to local WiFi
# 3. Show which URL will be used
# 4. Ask for confirmation
# 5. Deploy to Chrome

# App opens in Chrome browser at http://localhost:port
```

### 3C: Deploy to Android Phone

```powershell
# Ensure Android device is connected (USB debugging enabled)
flutter devices  # Should show your device

# Run the deploy script
.\deploy_to_phone.ps1

# Same URL detection and deployment process
```

**Result:** Midwife app running on web or phone

---

## Phase 4: Flutter Patient App Deployment

### 4A: Set Up Patient App

```powershell
cd birth-journal-patient-app

# Get dependencies
flutter pub get

# Check code quality
flutter analyze
flutter format .
```

### 4B: Deploy to Chrome (Web Testing)

```powershell
.\deploy_to_chrome.ps1

# Same workflow as midwife app
```

### 4C: Deploy to Phone

```powershell
.\deploy_to_phone.ps1

# Same workflow as midwife app
```

**Result:** Patient app running on web or phone

---

## Phase 5: Integration Testing

### 5A: Create Test Case (Midwife App)

1. Open midwife app (web or phone)
2. Login as test user (or create account)
3. Click **Create Case** or **Join Code**
4. Create a new case for testing
5. Copy the join code

### 5B: Join Case (Patient App)

1. Open patient app (web or phone)
2. Click **Join Case**
3. Enter the join code from midwife app
4. Confirm and proceed

### 5C: Test Event Sync

**In Patient App:**
1. Create an event (contraction, note, check-in)
2. Watch it sync to backend
3. Go offline (disable WiFi/internet)
4. Create another event
5. Event is queued locally

**In Midwife App:**
1. Refresh or wait for sync
2. Should see new events from patient
3. Create a note or alert
4. Patient app syncs when back online

### 5D: Verify Backend Data

```bash
# Check events in database
railway run python -c "
from backend.app.db import get_db
from backend.app.models import Event
db = next(get_db())
events = db.query(Event).count()
print(f'Total events: {events}')
"
```

**Result:** Data flows bidirectionally, offline sync works

---

## Phase 6: Production Readiness

### 6A: Security Checklist

- [ ] Change default JWT_SECRET to strong random value
- [ ] Configure CORS_ORIGINS to your actual domain
- [ ] Enable HTTPS/TLS (Railway does this automatically)
- [ ] Set up API rate limiting (if needed)
- [ ] Review privacy-security.md for GDPR compliance

### 6B: Monitoring Setup

- [ ] Check Railway Metrics tab (CPU, Memory, Network)
- [ ] Review logs regularly
- [ ] Set up error notifications (optional: Sentry, DataDog)
- [ ] Monitor database query performance

### 6C: Domain Configuration (Optional)

1. Buy domain (e.g., `polozne.pl`)
2. In Railway dashboard → Settings → Domains
3. Add custom domain
4. Configure DNS CNAME to Railway-provided target
5. Verify with: `curl https://your-domain.com/api/v1/health`

### 6D: Mobile App Store Deployment

**Android:**
```bash
cd birth-journal-midwife-app
flutter build apk --release
# Upload to Google Play Console

cd ../birth-journal-patient-app
flutter build apk --release
# Upload to Google Play Console
```

**iOS:**
```bash
cd birth-journal-midwife-app
flutter build ios --release
# Open in Xcode and configure signing
# Upload to App Store

cd ../birth-journal-patient-app
flutter build ios --release
# Same process
```

---

## Phase 7: Post-Launch Monitoring

### Checklist

- [ ] Monitor Railway logs daily for first week
- [ ] Check database storage usage
- [ ] Verify nightly backups (if configured)
- [ ] Monitor app crash rates
- [ ] Track user adoption metrics
- [ ] Review API response times
- [ ] Check for any permission/access control issues

### Ongoing Maintenance

**Weekly:**
- Review logs for errors
- Check database size
- Verify all endpoints responding

**Monthly:**
- Rotate JWT_SECRET (if desired)
- Update dependencies
- Review security advisories
- Backup database (if not automatic)

---

## Troubleshooting Quick Reference

### Backend issues

| Problem | Solution |
|---------|----------|
| Database connection fails | Check DATABASE_URL env var in Railway dashboard |
| Migrations won't run | Verify PostgreSQL is running, DATABASE_URL is correct |
| 502 Bad Gateway | Check Rails logs, restart service |
| Health endpoint returns `"db": false` | Migrations haven't run, run manually: `railway run python -m alembic upgrade head` |

### Flutter deploy script issues

| Problem | Solution |
|---------|----------|
| Script won't run | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Railway check always fails | Verify backend is running, DATABASE_URL is set, health endpoint works |
| Can't find local WiFi IP | Run `ipconfig` and verify IPv4 address under WiFi adapter |
| App can't connect to backend | Check API_BASE_URL is correct in app logs |

### App issues

| Problem | Solution |
|---------|----------|
| Login fails | Verify JWT_SECRET is set on Railway, user exists in database |
| Events don't sync | Check network connection, verify backend health endpoint works |
| Offline queue doesn't sync | Ensure app has internet, restart app to force sync |

---

## Files Reference

**Documentation:**
- `docs/api.md` - API contract and event schemas
- `docs/architecture.md` - System design, event model
- `docs/deployment.md` - Detailed Railway setup
- `docs/DEPLOY_SCRIPTS.md` - Flutter script usage guide
- `docs/RECENT_UPDATES.md` - What changed in this iteration
- `docs/privacy-security.md` - GDPR compliance, security guidelines

**Configuration:**
- `backend/requirements.txt` - Backend dependencies
- `birth-journal-midwife-app/pubspec.yaml` - Midwife app dependencies
- `birth-journal-patient-app/pubspec.yaml` - Patient app dependencies

**Deployment:**
- `backend/Procfile` - Railway start command
- `backend/railway.json` - Railway configuration
- `.github/workflows/` - CI/CD pipelines (all three projects)

---

## Success Criteria

✅ Deployment complete when:
1. Backend health endpoint returns `{"ok": true, "db": true}`
2. Flutter apps can login and authenticate
3. Events sync between midwife and patient apps
4. Offline events queue and sync when reconnected
5. All tests pass in GitHub Actions CI/CD

---

## Support

For specific questions, refer to:
- Architecture: See `docs/architecture.md`
- API details: See `docs/api.md`
- Privacy/Security: See `docs/privacy-security.md`
- Deployment issues: See `docs/deployment.md` and `docs/DEPLOY_SCRIPTS.md`
