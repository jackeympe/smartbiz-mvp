"""Optional SMTP integration test.

Run only when SMTP env vars are configured:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMARBIZ_EMAIL_TO

Usage:
  cd C:/Users/jacke/Downloads/smartbiz-mvp
  PYTHONPATH='' .venv/Scripts/python.exe tests/test_smtp_integration.py
"""
import os
import sys

def main() -> int:
    host = os.environ.get("SMTP_HOST")
    port = os.environ.get("SMTP_PORT")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    to_addr = os.environ.get("SMARBIZ_EMAIL_TO") or user
    if not all([host, port, user, password, to_addr]):
        print("SMTP not configured; skipping integration test")
        return 0
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from smartbiz.main import _send_email, _booking_confirmed_email, _technician_completed_email, _refund_confirmed_email
    try:
        _send_email("SmartBiz SMTP test", "This is a test message from SmartBiz.", to_addr)
        print("SMTP integration test passed: message sent")
        return 0
    except Exception as e:
        print(f"SMTP integration test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
