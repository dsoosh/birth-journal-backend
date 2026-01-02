# Flutter App Deployment Scripts

This guide explains how to use the updated deployment scripts for both Flutter applications.

## Overview

All four deployment scripts (`deploy_to_chrome.ps1` and `deploy_to_phone.ps1` in both app directories) now automatically:

1. **Check if Railway backend is available** - Makes a health check request to the production backend
2. **Use Railway URL if available** - Falls back to local development if production isn't reachable
3. **Provide clear feedback** - Shows which backend it's connecting to before deployment

## Script Locations

**Midwife App:**
- `birth-journal-midwife-app/deploy_to_chrome.ps1` - Deploy to Chrome for web debugging
- `birth-journal-midwife-app/deploy_to_phone.ps1` - Deploy to connected Android/iOS device

**Patient App:**
- `birth-journal-patient-app/deploy_to_chrome.ps1` - Deploy to Chrome for web debugging
- `birth-journal-patient-app/deploy_to_phone.ps1` - Deploy to connected Android/iOS device

## Running the Scripts

### Chrome Web Deployment

```powershell
# From your Flutter app directory, run either:

# Midwife app
.\deploy_to_chrome.ps1

# Patient app
.\deploy_to_chrome.ps1
```

**What happens:**
1. Checks if Railway backend is available at `https://birth-journal-backend-production.up.railway.app/api/v1/health`
2. If available: Uses production URL `https://birth-journal-backend-production.up.railway.app/api/v1`
3. If unavailable: Automatically detects local WiFi IP and uses `http://{local_ip}:8000/api/v1`
4. Prompts for confirmation before deploying
5. Launches Flutter app in Chrome

### Android/iOS Phone Deployment

```powershell
# From your Flutter app directory, run:

# Midwife app
.\deploy_to_phone.ps1

# Patient app
.\deploy_to_phone.ps1
```

**What happens:**
1. Same Railway health check as Chrome deployment
2. Falls back to local WiFi IP if Railway unavailable
3. Lists connected devices (phone must be connected via USB or wireless)
4. Prompts for confirmation
5. Builds and deploys to connected device

## Scenarios

### Scenario 1: Railway Backend is Running

```
Checking Railway backend availability... Cyan
✓ Railway backend is available Green
Backend API: https://birth-journal-backend-production.up.railway.app/api/v1 Yellow
```

- App will connect to production backend
- Perfect for testing with real production data
- No local server needed

### Scenario 2: Railway Backend is Down

```
Checking Railway backend availability... Cyan
✗ Railway backend is not reachable Yellow
Using local WiFi IP: 192.168.1.100 Yellow
Backend API: http://192.168.1.100:8000/api/v1 Yellow
```

- App will use local development server
- Make sure FastAPI server is running locally on port 8000
- Works for testing locally without internet

### Scenario 3: No WiFi IP Found (Local Fallback)

```
✗ Railway backend is not reachable
Warning: Could not determine local IP address Yellow
Using fallback IP: 192.168.1.1
```

- Uses a fallback IP (you may need to update this if different)
- Check what your local IP actually is with `ipconfig` command

## Prerequisites

### For Chrome Web Deployment
- Flutter SDK installed
- Chrome browser installed
- Run command: `flutter run -d chrome`

### For Phone Deployment
- Flutter SDK installed
- Android emulator OR connected Android device (USB debugging enabled)
- Or connected iOS device with developer tools installed
- Run command: `flutter run` (auto-detects device)

### For Local Development
- FastAPI backend running on `{local_wifi_ip}:8000`
- PostgreSQL database configured with `DATABASE_URL` env var
- Run backend with: `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000`

## Troubleshooting

### Script won't run - Execution Policy Error

```powershell
# Set execution policy to allow scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then run the script again
.\deploy_to_chrome.ps1
```

### Can't determine local WiFi IP

The script attempts to find your WiFi IP. If it fails:
```powershell
# Check your actual local IP
ipconfig

# Look for "IPv4 Address" under your WiFi adapter
# Example: 192.168.1.100
```

### Railway health check always fails

Check if:
1. Railway service is deployed and running
2. PostgreSQL database is provisioned
3. Post-deploy migrations have run: `python -m alembic upgrade head`
4. Health endpoint is accessible: `curl https://birth-journal-backend-production.up.railway.app/api/v1/health`

### Can't connect to local backend

Make sure:
1. FastAPI server is running: `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000`
2. Database is running: PostgreSQL or SQLite
3. Environment variables set: `DATABASE_URL`, `JWT_SECRET`
4. Local WiFi IP matches what you see in `ipconfig`

### Phone deployment can't find device

```powershell
# List available devices
flutter devices

# If no devices shown:
# - For Android: Enable USB debugging in Developer Options
# - For iOS: Connect and trust the computer, then run: flutter devices
# - For emulator: Start Android Studio emulator first
```

## Environment Variables (for reference)

The scripts pass `API_BASE_URL` to Flutter as a define variable. Your app should read it via:

```dart
const String apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000/api/v1',
);
```

## Advanced: Modifying Scripts

To change the Railway URL or add new logic:

```powershell
# Edit the script (example for Chrome)
code ./deploy_to_chrome.ps1

# Key variables to modify:
$railwayUrl = "https://birth-journal-backend-production.up.railway.app/api/v1/health"
# ^ Change this to a different Railway URL if needed

$timeout = 5  # seconds for health check
# ^ Increase if your connection is slow
```

## Summary

These scripts provide a **seamless development experience**:
- ✅ Auto-detect production vs. local backend
- ✅ Clear feedback on which backend is being used
- ✅ Works offline if you have local development server
- ✅ No manual URL configuration needed
- ✅ Same script works for Chrome and phone deployment

Just run the script, confirm the backend URL looks correct, and go!
