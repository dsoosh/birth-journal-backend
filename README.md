# Birth Journal Backend

Backend API for the Położne (Birth Journal) application - a PoC for labor and postpartum monitoring with midwife oversight.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

## Quick Start

### Development

```powershell
# Setup database
CREATE USER midwife_test WITH PASSWORD 'midwife_test_pw';
CREATE DATABASE midwife_support_test OWNER midwife_test;

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set environment variables
$env:DATABASE_URL="postgresql+psycopg://midwife_test:midwife_test_pw@localhost:5432/midwife_support_test"
$env:JWT_SECRET="dev-secret-key"

# Run migrations
alembic upgrade head

# Start development server
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Deployment (Railway)

1. Click the "Deploy on Railway" button above
2. Add PostgreSQL database service
3. Set `JWT_SECRET` environment variable
4. Deploy automatically handles migrations and startup

See [docs/deployment.md](docs/deployment.md) for detailed deployment instructions.

## Documentation

- [API Reference](docs/api.md) - REST endpoints and event schemas
- [Architecture](docs/architecture.md) - Event-based model and sync strategy
- [Deployment](docs/deployment.md) - Production deployment guide
- [Privacy & Security](docs/privacy-security.md) - GDPR compliance and data handling

## Key Features

- **Event-based architecture**: Append-only event store with deterministic state derivation
- **Offline-first sync**: Cursor-based pagination with idempotent event handling
- **Server-authoritative**: Backend enforces track assignment and business rules
- **GDPR-compliant**: Data separation, audit trails, no PII in logs

## Testing

```powershell
# Run tests
$env:DATABASE_URL="postgresql+psycopg://midwife_test:midwife_test_pw@localhost:5432/midwife_support_test"
python -m pytest -v

# With coverage
python -m pytest --cov=backend --cov-report=html --cov-report=term
```

## Project Structure

```
backend/
├── app/
│   ├── main.py          # FastAPI application
│   ├── api/
│   │   ├── router.py    # REST endpoints
│   │   └── schemas.py   # Pydantic models
│   ├── models.py        # SQLAlchemy ORM
│   ├── auth.py          # JWT authentication
│   ├── track.py         # Event track derivation
│   └── join_code.py     # Case join code generation
├── migrations/          # Alembic migrations
docs/                    # Documentation
tests/                   # Integration tests
```

## License

Private PoC project.