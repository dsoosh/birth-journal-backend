#!/usr/bin/env python3
"""
Helper script to run the Położne backend locally.

Handles:
- PostgreSQL via Docker (optional)
- Database migrations (Alembic)
- FastAPI server startup

Usage:
    python scripts/run_backend.py              # Full setup + start server
    python scripts/run_backend.py --no-docker  # Skip Docker, assume DB is running
    python scripts/run_backend.py --migrate    # Run migrations only
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def root_dir() -> Path:
    """Return the project root."""
    return Path(__file__).parent.parent


def dotenv_path() -> Path:
    """Return the .env file path."""
    return root_dir() / ".env"


def ensure_env_file(use_docker: bool = True) -> None:
    """Create .env file if it doesn't exist, reading from env vars when available."""
    env_file = dotenv_path()
    if env_file.exists():
        return

    print("Creating .env file...\n")
    
    # Read from environment or use defaults
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    db_name = os.getenv("DB_NAME", "birth_journal_db")
    
    # Allow interactive entry if not in env
    if "DB_USER" not in os.environ:
        print("Enter PostgreSQL connection details (or press Enter for defaults):\n")
        db_host = input(f"  DB host [{db_host}]: ").strip() or db_host
        db_port = input(f"  DB port [{db_port}]: ").strip() or db_port
        db_user = input(f"  DB user [{db_user}]: ").strip() or db_user
        db_password = input(f"  DB password [{db_password}]: ").strip() or db_password
        db_name = input(f"  DB name [{db_name}]: ").strip() or db_name
        print()
    
    # Use psycopg:// for psycopg3 (modern driver), not psycopg2
    db_url = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    jwt_secret = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    
    env_content = f"""# Development environment variables
# Set these before running the backend for production/CI environments

# Database
DATABASE_URL={db_url}
DB_HOST={db_host}
DB_PORT={db_port}
DB_USER={db_user}
DB_PASSWORD={db_password}
DB_NAME={db_name}

# JWT
JWT_SECRET={jwt_secret}
JWT_ALGORITHM=HS256
JWT_TTL_SECONDS=86400

# App
APP_ENV=dev
"""
    
    env_file.write_text(env_content)
    print(f"✓ Created {env_file}")
    print(f"  Host: {db_host}:{db_port}")
    print(f"  User: {db_user}")
    print(f"  Database: {db_name}\n")


def start_postgres_docker() -> bool:
    """Start PostgreSQL in Docker. Returns True if successful."""
    container_name = "midwife-postgres"
    
    # Check if container is already running
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--quiet"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout.strip():
            print(f"✓ PostgreSQL container '{container_name}' already running")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Try to start the container
    print(f"Starting PostgreSQL in Docker (container: {container_name})...")
    try:
        subprocess.run(
            [
                "docker", "run",
                "-d",
                "--name", container_name,
                "-e", "POSTGRES_USER=postgres",
                "-e", "POSTGRES_PASSWORD=postgres",
                "-e", "POSTGRES_DB=birth_journal_db",
                "-p", "5432:5432",
                "postgres:16-alpine",
            ],
            timeout=30,
            capture_output=True,
        )
        print(f"✓ PostgreSQL started. Waiting for readiness...")
        time.sleep(3)  # Give it a moment to be ready
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"✗ Failed to start Docker: {e}", file=sys.stderr)
        return False


def run_migrations() -> bool:
    """Run Alembic migrations."""
    os.chdir(root_dir())
    print("\nRunning database migrations...")
    
    # Get the Python executable from venv
    venv_path = root_dir() / ".venv"
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    try:
        result = subprocess.run(
            [str(python_exe), "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print("✓ Migrations completed successfully")
            return True
        else:
            print(f"✗ Migration failed: {result.stderr}", file=sys.stderr)
            return False
    except FileNotFoundError:
        print("✗ alembic not found. Install with: pip install -r requirements-dev.txt", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("✗ Migrations timed out", file=sys.stderr)
        return False


def start_server() -> None:
    """Start the FastAPI server."""
    os.chdir(root_dir())
    print("\nStarting FastAPI server on http://localhost:8000")
    print("Press Ctrl+C to stop.\n")
    
    # Get the Python executable from venv
    venv_path = root_dir() / ".venv"
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    try:
        subprocess.run(
            [str(python_exe), "-m", "uvicorn", "backend.app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
            timeout=None,  # Run until interrupted
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
    except FileNotFoundError:
        print("✗ uvicorn not found. Install with: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Run the Położne backend locally."
    )
    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Skip Docker setup (assumes PostgreSQL is already running)",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Run migrations only, then exit",
    )
    parser.add_argument(
        "--skip-migrate",
        action="store_true",
        help="Skip running migrations",
    )
    parser.add_argument(
        "--reset-env",
        action="store_true",
        help="Recreate .env file (overwrite existing)",
    )

    args = parser.parse_args()

    print("Położne Backend Local Setup\n")

    # Remove old .env if resetting
    if args.reset_env:
        env_file = dotenv_path()
        if env_file.exists():
            print(f"Removing old .env file...")
            env_file.unlink()

    # Ensure .env exists
    ensure_env_file(use_docker=not args.no_docker)

    # Start Docker PostgreSQL if requested
    if not args.no_docker:
        if not start_postgres_docker():
            print("\nℹ Continuing without Docker. Make sure PostgreSQL is running.")

    # Run migrations
    if not args.skip_migrate:
        if not run_migrations():
            print("\n✗ Setup failed. Cannot proceed without database.", file=sys.stderr)
            sys.exit(1)

    # Exit if only migrating
    if args.migrate:
        print("\n✓ Migrations completed. Exiting.")
        return

    # Start server
    start_server()


if __name__ == "__main__":
    main()
