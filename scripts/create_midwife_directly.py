"""Create a test midwife account directly in the database."""
import uuid
from backend.app.db import get_sessionmaker
from backend.app.models import Midwife
from backend.app.password import hash_password

email = "test@example.com"
password = "test123"

SessionLocal = get_sessionmaker()
with SessionLocal() as session:
    # Check if account exists
    existing = session.query(Midwife).filter_by(email=email).first()
    if existing:
        print(f"Midwife account {email} already exists")
    else:
        midwife = Midwife(
            midwife_id=uuid.uuid4(),
            email=email,
            password_hash=hash_password(password)
        )
        session.add(midwife)
        session.commit()
        print(f"Created midwife account: {email}")
        print(f"Password: {password}")
