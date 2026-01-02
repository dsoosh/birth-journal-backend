# Testing Tooling Recommendations

This document outlines recommended testing tools and strategies to improve the Położne project's test coverage and reliability.

---

## Current Testing Stack

| Layer | Tool | Coverage |
|-------|------|----------|
| Backend Unit Tests | pytest | 57% |
| Midwife App Tests | flutter_test | 6% |
| Patient App Tests | flutter_test | 27% |
| Integration Tests | pytest (API tests) | Partial |
| E2E Tests | None | 0% |

---

## Recommended Additions

### 1. End-to-End Testing (High Priority)

#### Option A: Maestro (Recommended for Mobile)
**Why:** Mobile-first, simple YAML syntax, works great for Flutter.

```yaml
# Example: maestro/flows/patient_login.yaml
appId: com.poloznebirth.patient
---
- launchApp
- tapOn: "Dołącz przez kod"
- inputText:
    id: "join_code_field"
    text: "ABC123"
- tapOn: "Dołącz"
- assertVisible: "Panel główny"
```

**Installation:**
```bash
# Install Maestro CLI
curl -Ls "https://get.maestro.mobile.dev" | bash

# Run tests
maestro test maestro/flows/
```

**Effort:** 1-2 days to set up, then ~1 hour per flow

---

#### Option B: Patrol (Flutter-native E2E)
**Why:** Written in Dart, integrates with `flutter_test`, can test native features.

```dart
// integration_test/patient_app_test.dart
import 'package:patrol/patrol.dart';

void main() {
  patrolTest('Complete contraction tracking flow', ($) async {
    await $.pumpWidgetAndSettle(const MyApp());
    
    // Join case
    await $('Dołącz przez kod').tap();
    await $(#joinCodeField).enterText('ABC123');
    await $('Dołącz').tap();
    
    // Start contraction
    await $('Rozpocznij skurcz').tap();
    await $.pump(Duration(seconds: 60));
    await $('Zakończ skurcz').tap();
    
    // Verify in timeline
    expect($('Skurcz 1').visible, isTrue);
  });
}
```

**Installation:**
```yaml
# pubspec.yaml
dev_dependencies:
  patrol: ^3.8.0
```

**Effort:** 2-3 days to set up, then ~2 hours per test

---

### 2. API Contract Testing (Medium Priority)

#### Schemathesis (Recommended)
**Why:** Auto-generates API tests from OpenAPI schema, finds edge cases.

```bash
# Install
pip install schemathesis

# Generate OpenAPI schema from FastAPI
# FastAPI auto-generates at /openapi.json

# Run tests
schemathesis run http://localhost:8000/openapi.json \
  --hypothesis-max-examples=100 \
  --checks all
```

**Benefits:**
- Finds schema violations
- Tests edge cases (empty strings, huge numbers)
- Validates response formats
- No test code to write

**Effort:** 0.5 days to set up, runs automatically

---

#### Pact (Consumer-Driven Contract Testing)
**Why:** Ensures Flutter apps and backend stay in sync.

```python
# tests/test_pacts.py
from pact import Consumer, Provider

pact = Consumer('PatientApp').has_pact_with(Provider('Backend'))

def test_event_sync_contract():
    expected = {
        'accepted_event_ids': Like(['uuid-here']),
        'server_cursor': Like('123'),
        'new_events': EachLike({
            'event_id': Like('uuid'),
            'type': Like('contraction_start'),
            'ts': Like('2025-01-01T00:00:00Z'),
        }),
    }
    
    (pact
        .given('a case exists')
        .upon_receiving('an event sync request')
        .with_request('POST', '/api/v1/events/sync')
        .will_respond_with(200, body=expected))
    
    with pact:
        # Test Flutter client against pact
        pass
```

**Effort:** 2-3 days to set up, ongoing maintenance

---

### 3. Load Testing (Medium Priority)

#### Locust (Recommended)
**Why:** Python-based, easy to write, good for API load testing.

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class MidwifeUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login
        response = self.client.post("/api/v1/auth/login", json={
            "email": "midwife@test.com",
            "password": "password123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def list_cases(self):
        self.client.get("/api/v1/cases", headers=self.headers)
    
    @task(1)
    def sync_events(self):
        self.client.post("/api/v1/events/sync", 
            headers=self.headers,
            json={"cursor": None, "events": []})

class PatientUser(HttpUser):
    wait_time = between(5, 15)
    
    @task
    def submit_contraction(self):
        self.client.post("/api/v1/events/sync",
            headers=self.headers,
            json={
                "cursor": None,
                "events": [{
                    "event_id": str(uuid.uuid4()),
                    "case_id": self.case_id,
                    "type": "contraction_start",
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "payload_v": 1,
                    "payload": {}
                }]
            })
```

**Run:**
```bash
pip install locust
locust -f tests/load/locustfile.py --host http://localhost:8000

# Open http://localhost:8089 to start test
```

**Effort:** 1 day to set up basic scenarios

---

### 4. Visual Regression Testing (Low Priority)

#### Percy / Applitools (Cloud-based)
**Why:** Catch unintended UI changes across Flutter builds.

```dart
// integration_test/visual_test.dart
await tester.pumpWidget(MyApp());
await tester.pumpAndSettle();

// Take screenshot
await screenMatchesGolden('home_screen');
```

**Alternative: Flutter Golden Tests (Free)**
```dart
// test/golden_test.dart
testWidgets('ContractionButton matches golden', (tester) async {
  await tester.pumpWidget(MaterialApp(
    home: ContractionButton(onTap: () {}),
  ));
  
  await expectLater(
    find.byType(ContractionButton),
    matchesGoldenFile('goldens/contraction_button.png'),
  );
});
```

**Effort:** 0.5 days for golden tests, 1 day for cloud service

---

### 5. Security Testing (Medium Priority)

#### OWASP ZAP (Automated Security Scanning)
```bash
# Run ZAP against local API
docker run -t zaproxy/zap-stable zap-api-scan.py \
  -t http://host.docker.internal:8000/openapi.json \
  -f openapi
```

#### Bandit (Python Static Analysis)
```bash
pip install bandit
bandit -r backend/ -ll
```

**Add to CI:**
```yaml
# .github/workflows/security.yml
- name: Security Scan
  run: |
    pip install bandit
    bandit -r backend/ -f json -o bandit-report.json
```

**Effort:** 0.5 days to set up

---

### 6. Database Testing

#### pytest-postgresql (Isolated DB Tests)
```python
# tests/conftest.py
import pytest
from pytest_postgresql import factories

postgresql_proc = factories.postgresql_proc()
postgresql = factories.postgresql('postgresql_proc')

@pytest.fixture
def db_session(postgresql):
    # Create tables
    # Return session
    pass
```

**Benefits:**
- Each test gets fresh database
- Parallel test execution
- No state pollution

**Effort:** 0.5 days to set up

---

### 7. Mock Services

#### WireMock (API Mocking)
```yaml
# wiremock/mappings/backend.json
{
  "request": {
    "method": "POST",
    "url": "/api/v1/events/sync"
  },
  "response": {
    "status": 200,
    "jsonBody": {
      "accepted_event_ids": [],
      "server_cursor": "123",
      "new_events": []
    }
  }
}
```

**Run:**
```bash
docker run -d -p 8080:8080 wiremock/wiremock
```

**Use in Flutter tests:**
```dart
// Use http://localhost:8080 as API_BASE_URL in tests
```

**Effort:** 0.5 days to set up

---

## Recommended CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on: [push, pull_request]

jobs:
  backend-tests:
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
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest --cov=backend --cov-report=xml
      - uses: codecov/codecov-action@v4

  flutter-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
      - run: |
          cd birth-journal-patient-app
          flutter pub get
          flutter test --coverage
      - run: |
          cd birth-journal-midwife-app
          flutter pub get
          flutter test --coverage

  e2e-tests:
    runs-on: macos-latest
    needs: [backend-tests, flutter-tests]
    steps:
      - uses: actions/checkout@v4
      - uses: mobile-dev-inc/action-maestro-cloud@v1
        with:
          api-key: ${{ secrets.MAESTRO_CLOUD_API_KEY }}
          app-file: build/app/outputs/flutter-apk/app-release.apk

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install bandit
      - run: bandit -r backend/ -f sarif -o bandit.sarif
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: bandit.sarif
```

---

## Priority Implementation Order

| Week | Focus | Tools |
|------|-------|-------|
| 1 | API contract validation | Schemathesis |
| 1 | Security scanning | Bandit, ZAP |
| 2 | E2E happy path | Maestro or Patrol |
| 2 | Load testing baseline | Locust |
| 3 | Visual regression | Flutter Golden Tests |
| 3 | CI/CD pipeline | GitHub Actions |

---

## Cost Estimates

| Tool | Cost | Notes |
|------|------|-------|
| Schemathesis | Free | Open source |
| Locust | Free | Open source |
| Bandit | Free | Open source |
| ZAP | Free | Open source |
| Maestro Cloud | Free tier: 100 runs/month | Paid: $99/mo |
| Percy | Free tier: 5K snapshots/mo | Paid: $99/mo |
| GitHub Actions | Free: 2K min/mo | Paid: $0.008/min |

**Recommendation:** Start with free tools, consider paid for production scale.
