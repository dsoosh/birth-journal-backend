web: sh -c 'for i in 1 2 3 4 5; do python -m alembic upgrade head && break || sleep 5; done' && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
