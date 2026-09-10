"""Authentication, password hashing, session token management, and RBAC for SmartBiz Fire."""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from smartbiz.db import get_connection, db_lock

AUTH_SECRET = os.environ.get("AUTH_SECRET", "smartbiz-fire-secret-key-2026-south-africa")
ADMIN_TOKEN = os.environ.get("SMARTBIZ_ADMIN_TOKEN", "dev")

# Role definitions
ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_ADMIN = "ADMIN"
ROLE_MANAGER = "MANAGER"
ROLE_TECHNICIAN = "TECHNICIAN"
ROLE_CUSTOMER = "CUSTOMER"

ALL_ROLES = [ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_MANAGER, ROLE_TECHNICIAN, ROLE_CUSTOMER]

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if not salt:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return f"{salt}:{pw_hash}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a password against a salt:hash string."""
    try:
        salt, pw_hash = stored_hash.split(":", 1)
        expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
        return hmac.compare_digest(pw_hash, expected)
    except Exception:
        return False

def create_session_token(user_id: int, email: str, role: str, expires_in_seconds: int = 86400 * 7) -> str:
    """Generates a secure signed session token."""
    expires_at = int(time.time()) + expires_in_seconds
    payload = f"{user_id}:{email}:{role}:{expires_at}"
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"

def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Validates a signed session token and returns the user dict if valid and non-expired."""
    try:
        parts = token.split(":")
        if len(parts) != 5:
            return None
        user_id_str, email, role, expires_at_str, signature = parts
        payload = f"{user_id_str}:{email}:{role}:{expires_at_str}"
        expected_sig = hmac.new(AUTH_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        if int(expires_at_str) < int(time.time()):
            return None
        return {
            "user_id": int(user_id_str),
            "email": email,
            "role": role,
            "expires_at": int(expires_at_str),
        }
    except Exception:
        return None

def seed_default_admin() -> None:
    """Seeds default super admin user if users table is empty."""
    with db_lock, get_connection() as con:
        count = con.execute("SELECT count(*) FROM users").fetchone()[0]
        if count == 0:
            default_email = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@smartbizfire.co.za")
            default_pass = os.environ.get("DEFAULT_ADMIN_PASSWORD", "SmartBizFire2026!")
            pw_hash = hash_password(default_pass)
            now = datetime.now(timezone.utc).isoformat()
            con.execute(
                """
                INSERT INTO users (email, password_hash, full_name, role, phone, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (default_email, pw_hash, "SmartBiz Super Admin", ROLE_SUPER_ADMIN, "+27110000000", now, now)
            )
            con.commit()
