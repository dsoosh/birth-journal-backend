# Recent Deployment & Configuration Updates

## Summary of Changes

This document summarizes all recent updates to the Położne project infrastructure, including Flutter deployment scripts and Railway configuration improvements.

---

## 1. Flutter Deployment Scripts Updated

### What Changed

All four Flutter deployment scripts now intelligently detect and connect to the appropriate backend:

**Modified Files:**
- `birth-journal-midwife-app/deploy_to_chrome.ps1`
- `birth-journal-midwife-app/deploy_to_phone.ps1`
- `birth-journal-patient-app/deploy_to_chrome.ps1`
- `birth-journal-patient-app/deploy_to_phone.ps1`

### How It Works

Each script now:

1. **Checks Railway Backend First**
   ```powershell
   # Makes a health request to production
   https://birth-journal-backend-production.up.railway.app/api/v1/health
   ```

2. **Falls Back to Local WiFi**
   - If Railway is unreachable, automatically detects local WiFi IP
   - Uses format: `http://{local_wifi_ip}:8000/api/v1`

3. **Provides Clear Feedback**
   ```
   ✓ Railway backend is available
   Using local WiFi IP: 192.168.1.100
   ```

4. **Prompts for Confirmation**
   - Shows which API URL will be used
   - Asks for confirmation before building/deploying

### Usage Examples

**Chrome Web Deployment:**
```powershell
cd birth-journal-midwife-app
.\deploy_to_chrome.ps1
# Checks Railway → Uses local WiFi → Deploys to Chrome
```

**Android Phone Deployment:**
```powershell
cd birth-journal-patient-app
.\deploy_to_phone.ps1
# Checks Railway → Uses local WiFi → Deploys to connected device
```

---

## 2. Railway Post-Deploy Migrations (Enhanced Documentation)

### What Changed

Updated `docs/deployment.md` with clearer instructions for configuring automatic database migrations:

### Key Improvement

**Option A: Dashboard (Easiest)**
1. Railway dashboard → Your backend service → Settings
2. Find "Post Deployment Hook" section
3. Enter: `python -m alembic upgrade head`
4. Save

Migrations will automatically run after every deployment!

**Option B: Railway CLI**
```bash
railway run python -m alembic upgrade head
```

### Why This Matters

- **Before:** Migrations were manual, easy to forget
- **After:** Automatic, guaranteed database schema is always up-to-date
- **Safety:** Deployment fails if migrations fail

---

## 3. Python Dependencies (Verified)

### Current State

**requirements.txt:**
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.5.3           ← Fixed version for wheel availability
pydantic-settings==2.2.1  ← Compatible with pydantic 2.5.3
pydantic[email]==2.5.3    ← Consistent version
SQLAlchemy==2.0.36
alembic==1.14.0           ← Moved to production (for migrations)
psycopg[binary]==3.2.3    ← For PostgreSQL connection
psycopg2-binary==2.9.9    ← Fallback compatibility
PyJWT==2.10.1
qrcode[pil]==8.1
bcrypt==4.1.2
python-dotenv==1.0.1
```

**requirements-dev.txt:**
```
-r requirements.txt        ← Imports all production deps
pytest==8.3.4
httpx==0.28.1
pytest-cov==6.0.0
ruff==0.8.4
requests==2.32.5
```

### Key Fix

✅ Removed conflicting `pydantic[email]==2.7.0` from requirements-dev.txt
- Prevents pip resolver conflicts in CI/CD
- Ensures single pydantic version (2.5.3) across all environments

---

## 4. Deployment Documentation

### New Files Created

**`docs/DEPLOY_SCRIPTS.md`** - Complete guide for Flutter deployment scripts
- Usage instructions for Chrome and phone deployment
- Troubleshooting common issues
- Prerequisites checklist
- Scenarios (production vs. local development)

### Updated Files

**`docs/deployment.md`** - Enhanced Railway configuration
- Clearer Step 3: Environment Variables (with reference badge note)
- New Step 4: Post-Deploy Migrations with both dashboard and CLI methods
- Better verification steps

---

## 5. Backend Infrastructure Status

### Current Deployment

**Production URL:** `https://birth-journal-backend-production.up.railway.app`

**Health Check:**
```bash
curl https://birth-journal-backend-production.up.railway.app/api/v1/health
# Returns: {"ok": true, "db": true}
```

### Next Steps for Complete Setup

1. **Configure Post-Deploy Hook in Railway Dashboard** (5 min)
   - Go to backend service → Settings → Post Deployment Hook
   - Add: `python -m alembic upgrade head`
   - This runs migrations automatically after each deployment

2. **Run Initial Migrations** (if not done)
   - Via Railway dashboard: Service → More Options → Run Command
   - Or via CLI: `railway run python -m alembic upgrade head`
   - Verify with: `curl {backend_url}/api/v1/health`

3. **Test with Flutter Apps**
   - Run deploy scripts (they'll auto-detect Railway)
   - Login as midwife or join as patient
   - Check that API calls succeed

---

## Technical Details

### Why These Changes?

1. **Smart Deploy Scripts**
   - Developers no longer need to manually switch URLs
   - Works offline (with local dev server)
   - Same script for development and production

2. **Automatic Migrations**
   - Reduces human error
   - Database schema always matches code
   - Deployment fails safely if migration fails

3. **Dependency Consistency**
   - Single pydantic version prevents conflicts
   - Pre-built wheels for Python 3.12 (faster CI/CD)
   - Matches production runtime (python-3.12.7)

---

## Verification Checklist

- [x] Flutter deploy scripts check Railway health
- [x] Flutter deploy scripts detect local WiFi IP
- [x] requirements.txt has consistent pydantic 2.5.3
- [x] requirements-dev.txt imports from requirements.txt
- [x] Deployment documentation updated
- [x] Deploy scripts guide created
- [x] Backend running on Railway
- [x] Health endpoint accessible
- [ ] Post-deploy migrations configured in Railway dashboard (user action)
- [ ] Initial database migrations run (user action)

---

## Quick Commands

**Test local deployment (Chrome):**
```powershell
cd birth-journal-patient-app
.\deploy_to_chrome.ps1
# Should detect Railway or use local WiFi automatically
```

**Check backend health:**
```bash
curl https://birth-journal-backend-production.up.railway.app/api/v1/health
```

**Run migrations manually (if needed):**
```bash
railway run python -m alembic upgrade head
```

**View recent deployments:**
Railway dashboard → Deployments → Select deployment → View Logs

---

## Questions?

Refer to:
- Flutter deployment: `docs/DEPLOY_SCRIPTS.md`
- Railway setup: `docs/deployment.md`
- Architecture: `docs/architecture.md`
- API contracts: `docs/api.md`
