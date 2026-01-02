# Production Deployment Guide

This document provides instructions for deploying the Położne PoC to production.

---

## Recommended Stack

| Component | Recommended Service | Alternative |
|-----------|-------------------|-------------|
| Backend Hosting | Railway / Render | AWS ECS, Google Cloud Run |
| Database | Railway Postgres / Render Postgres | AWS RDS, Supabase |
| Mobile Distribution | Google Play (Internal Testing) | Firebase App Distribution |
| File Storage | Cloudflare R2 | AWS S3 (for QR images if needed) |
| Monitoring | Sentry | Datadog, New Relic |
| CI/CD | GitHub Actions | GitLab CI |

**Recommended for PoC: Railway** - Simple, affordable, good developer experience.

---

## Prerequisites

1. GitHub repository with all three projects
2. PostgreSQL 15+ database
3. Domain name (optional but recommended)
4. Apple Developer Account (for iOS distribution)
5. Google Play Developer Account (for Android distribution)

---

## Backend Deployment (Railway)

### Step 1: Create Railway Project

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select the `birth-journal-backend` repository
4. Railway will auto-detect the Python project

### Step 2: Add PostgreSQL

1. In your Railway project, click "New" → "Database" → "PostgreSQL"
2. Railway will provision a managed Postgres instance
3. Copy the `DATABASE_URL` from the PostgreSQL service

### Step 3: Configure Environment Variables

In Railway dashboard → Variables, add:

```
DATABASE_URL=<auto-populated by Railway>
JWT_SECRET=<generate with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
JWT_TTL_SECONDS=86400
CORS_ORIGINS=https://your-domain.com,polozne://
```

### Step 4: Configure Start Command

Create `Procfile` in repository root:

```
web: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

Or set in Railway:
- Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`

### Step 5: Run Migrations

In Railway → Settings → Deploy, add:
- Release Command: `alembic upgrade head`

### Step 6: Custom Domain (Optional)

1. In Railway → Settings → Domains
2. Add custom domain (e.g., `api.polozne.pl`)
3. Configure DNS CNAME record to Railway

### Verification

```bash
curl https://your-railway-url.up.railway.app/api/v1/health
# Should return: {"ok": true, "db": true}
```

---

## Alternative: Render Deployment

### Step 1: Create Web Service

1. Go to [render.com](https://render.com) and connect GitHub
2. New → Web Service → Select repository
3. Configure:
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`

### Step 2: Add PostgreSQL

1. New → PostgreSQL
2. Copy Internal Database URL
3. Add as `DATABASE_URL` environment variable

### Step 3: Environment Variables

Same as Railway configuration above.

---

## Docker Deployment (Self-hosted)

### Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ backend/
COPY alembic.ini .
COPY backend/migrations/ backend/migrations/

# Run migrations and start server
CMD alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+psycopg://postgres:postgres@db:5432/polozne
      JWT_SECRET: ${JWT_SECRET}
      JWT_ALGORITHM: HS256
      JWT_TTL_SECONDS: 86400
      CORS_ORIGINS: https://your-domain.com
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: polozne
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

### Deploy with Docker

```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f api

# Run migrations manually if needed
docker-compose exec api alembic upgrade head
```

---

## Mobile App Distribution

### Android (Google Play Internal Testing)

#### Step 1: Build Release APK

```powershell
cd birth-journal-patient-app

# Set production API URL
flutter build apk --release `
  --dart-define=API_BASE_URL=https://api.polozne.pl/api/v1
```

#### Step 2: Sign the APK

1. Create keystore (one-time):
```bash
keytool -genkey -v -keystore polozne-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias polozne
```

2. Create `android/key.properties`:
```properties
storePassword=<your-password>
keyPassword=<your-password>
keyAlias=polozne
storeFile=../polozne-key.jks
```

3. Update `android/app/build.gradle.kts`:
```kotlin
signingConfigs {
    create("release") {
        val keyPropertiesFile = rootProject.file("key.properties")
        val keyProperties = Properties().apply {
            load(FileInputStream(keyPropertiesFile))
        }
        storeFile = file(keyProperties["storeFile"] as String)
        storePassword = keyProperties["storePassword"] as String
        keyAlias = keyProperties["keyAlias"] as String
        keyPassword = keyProperties["keyPassword"] as String
    }
}

buildTypes {
    release {
        signingConfig = signingConfigs.getByName("release")
    }
}
```

#### Step 3: Upload to Play Console

1. Go to [Google Play Console](https://play.google.com/console)
2. Create new app → "Położne"
3. Internal testing → Create new release
4. Upload APK/AAB
5. Add testers by email

### iOS (TestFlight)

#### Step 1: Build IPA

```bash
cd birth-journal-patient-app

flutter build ipa --release \
  --dart-define=API_BASE_URL=https://api.polozne.pl/api/v1
```

#### Step 2: Upload to App Store Connect

1. Open Xcode → Product → Archive
2. Or use: `xcrun altool --upload-app -f build/ios/ipa/*.ipa -t ios -u <apple-id> -p <app-specific-password>`

#### Step 3: TestFlight Distribution

1. Go to [App Store Connect](https://appstoreconnect.apple.com)
2. My Apps → Położne → TestFlight
3. Add internal/external testers

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Run tests
        env:
          DATABASE_URL: postgresql+psycopg://test:test@localhost:5432/test
          JWT_SECRET: test-secret
        run: pytest -v

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Railway
        uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: backend

  build-android:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.24.0'
      - name: Build Patient APK
        run: |
          cd birth-journal-patient-app
          flutter pub get
          flutter build apk --release \
            --dart-define=API_BASE_URL=${{ secrets.API_BASE_URL }}
      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: patient-app-apk
          path: birth-journal-patient-app/build/app/outputs/flutter-apk/app-release.apk
```

---

## Environment Configuration

### Production Environment Variables

```bash
# Backend
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db
JWT_SECRET=<64-char-random-string>
JWT_ALGORITHM=HS256
JWT_TTL_SECONDS=86400
CORS_ORIGINS=https://app.polozne.pl,polozne://

# Optional: Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx

# Optional: Push Notifications (future)
FCM_PROJECT_ID=polozne-prod
FCM_PRIVATE_KEY=<service-account-key>
```

### Flutter App Configuration

```dart
// lib/config/environment.dart
class Environment {
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.polozne.pl/api/v1',
  );
}
```

Build with:
```bash
flutter build apk --dart-define=API_BASE_URL=https://api.polozne.pl/api/v1
```

---

## Monitoring & Logging

### Sentry Integration (Backend)

```python
# backend/app/main.py
import sentry_sdk

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    traces_sample_rate=0.1,
)
```

### Sentry Integration (Flutter)

```yaml
# pubspec.yaml
dependencies:
  sentry_flutter: ^7.0.0
```

```dart
// lib/main.dart
import 'package:sentry_flutter/sentry_flutter.dart';

void main() async {
  await SentryFlutter.init(
    (options) {
      options.dsn = 'https://xxx@sentry.io/xxx';
    },
    appRunner: () => runApp(const MyApp()),
  );
}
```

---

## Security Checklist

- [ ] JWT_SECRET is 64+ characters, randomly generated
- [ ] DATABASE_URL uses SSL (`?sslmode=require`)
- [ ] CORS_ORIGINS only includes production domains
- [ ] No debug endpoints in production
- [ ] Rate limiting enabled (Railway/Render handle this)
- [ ] Database backups configured
- [ ] HTTPS only (Railway/Render provide free SSL)
- [ ] Secrets not committed to repository

---

## Rollback Procedure

### Railway
```bash
# Railway CLI
railway rollback
```

### Docker
```bash
# Tag releases
docker tag polozne-api:latest polozne-api:v1.0.0

# Rollback
docker-compose down
docker tag polozne-api:v0.9.0 polozne-api:latest
docker-compose up -d
```

---

## Cost Estimates

| Service | Monthly Cost |
|---------|-------------|
| Railway (Hobby) | $5 + usage |
| Railway Postgres | $5 + storage |
| Google Play Console | $25 (one-time) |
| Apple Developer | $99/year |
| Custom Domain | ~$12/year |
| **Total** | ~$15-25/month |

**Note:** Railway/Render free tiers may be sufficient for PoC testing.
