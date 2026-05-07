"""
Create or update the initial owner user (phase 1 schema: username + role).

Usage:
    ADMIN_USERNAME=admin ADMIN_PASSWORD=changeme python scripts/create_admin.py

Optional:
    ADMIN_NAME="Shop Owner"
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_NAME = os.environ.get("ADMIN_NAME", "Administrator")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

if not ADMIN_PASSWORD:
    print("ERROR: ADMIN_PASSWORD env var is required.", file=sys.stderr)
    sys.exit(1)

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    if user:
        user.password_hash = hash_password(ADMIN_PASSWORD)
        user.name = ADMIN_NAME
        user.role = "owner"
        user.is_active = True
        db.commit()
        print(f"Updated owner user: {ADMIN_USERNAME}")
    else:
        user = User(
            name=ADMIN_NAME,
            username=ADMIN_USERNAME,
            password_hash=hash_password(ADMIN_PASSWORD),
            role="owner",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created owner user (id={user.id}): {ADMIN_USERNAME}")
finally:
    db.close()
