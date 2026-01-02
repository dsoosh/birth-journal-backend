from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.router import router as api_router


def run_migrations():
    """Run database migrations on startup."""
    try:
        from alembic.config import Config
        from alembic.command import upgrade
        
        alembic_cfg = Config("alembic.ini")
        upgrade(alembic_cfg, "head")
        print("✓ Database migrations completed successfully")
    except Exception as e:
        print(f"⚠ Warning: Could not run migrations: {e}")


def create_app() -> FastAPI:
    app = FastAPI(title="Położne API", version="0.1.0")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(api_router)

    # Serve static files (UI)
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    @app.on_event("startup")
    def startup_event():
        """Run migrations on application startup."""
        run_migrations()

    return app


app = create_app()
