from backend.app.db import get_engine
from sqlalchemy import text

engine = get_engine()
with engine.connect() as conn:
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
    tables = [row[0] for row in result]
    if tables:
        print("Tables in database:")
        for table in tables:
            print(f"  - {table}")
    else:
        print("No tables found in database")
