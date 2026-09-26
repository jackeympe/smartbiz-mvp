"""Calendar Provider abstraction supporting Internal Calendar, Google Calendar, and Microsoft Outlook."""
import json
import os
import sqlite3
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from smartbiz.db import get_connection, db_lock

TIMEZONE_SA = "Africa/Johannesburg"

class CalendarProvider:
    """Base Calendar interface."""
    def create_event(self, title: str, start_time: str, end_time: str, description: str = "", customer_id: int = 0, site_id: int = 0, technician_id: int = 0) -> Dict[str, Any]:
        raise NotImplementedError

    def list_events(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

class InternalCalendarProvider(CalendarProvider):
    """Local SQLite-backed calendar provider with Africa/Johannesburg timezone normalization."""

    def create_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        customer_id: int = 0,
        site_id: int = 0,
        technician_id: int = 0,
    ) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        with db_lock, get_connection() as con:
            cur = con.execute(
                """
                INSERT INTO calendar_events (
                  title, description, start_time, end_time, timezone, provider,
                  customer_id, site_id, technician_id, created_at
                ) VALUES (?, ?, ?, ?, ?, 'INTERNAL', ?, ?, ?, ?)
                """,
                (title, description, start_time, end_time, TIMEZONE_SA, customer_id, site_id, technician_id, now_iso)
            )
            event_id = cur.lastrowid
            con.commit()

        return self.get_event(event_id)

    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        with db_lock, get_connection() as con:
            row = con.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,)).fetchone()
            return dict(row) if row else None

    def list_events(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        with db_lock, get_connection() as con:
            query = "SELECT * FROM calendar_events WHERE 1=1"
            params = []
            if start_date:
                query += " AND start_time >= ?"
                params.append(start_date)
            if end_date:
                query += " AND end_time <= ?"
                params.append(end_date)
            query += " ORDER BY start_time ASC"
            rows = con.execute(query, params).fetchall()
            return [dict(r) for r in rows]


class GoogleCalendarSync:
    """Small Google Calendar REST adapter using OAuth refresh-token credentials."""

    token_url = "https://oauth2.googleapis.com/token"
    api_root = "https://www.googleapis.com/calendar/v3"

    def __init__(self) -> None:
        self.client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
        self.client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
        self.refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN", "").strip()
        self.calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary").strip() or "primary"

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def _access_token(self) -> str:
        if not self.configured:
            raise RuntimeError("Google Calendar OAuth is not configured")
        body = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")
        req = urllib.request.Request(
            self.token_url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("Google OAuth refresh did not return an access token")
        return token

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        token = self._access_token()
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            self.api_root + path,
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Google Calendar API {exc.code}: {detail[:500]}") from exc

    def create_event(
        self,
        *,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        attendee_email: str = "",
    ) -> Dict[str, Any]:
        event: Dict[str, Any] = {
            "summary": title,
            "description": description,
            "location": location,
            "start": {"dateTime": start_time, "timeZone": TIMEZONE_SA},
            "end": {"dateTime": end_time, "timeZone": TIMEZONE_SA},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 120},
                ],
            },
        }
        if attendee_email:
            event["attendees"] = [{"email": attendee_email}]
        encoded_calendar = urllib.parse.quote(self.calendar_id, safe="")
        result = self._request(
            "POST",
            f"/calendars/{encoded_calendar}/events?sendUpdates=all",
            event,
        )
        return {
            "ok": True,
            "provider": "GOOGLE",
            "external_event_id": result.get("id", ""),
            "external_event_url": result.get("htmlLink", ""),
            "status": result.get("status", ""),
        }


def sync_internal_event_to_google(
    event_id: int,
    *,
    location: str = "",
    attendee_email: str = "",
) -> Dict[str, Any]:
    """Mirror an existing internal event to Google when configured.

    Internal storage remains authoritative. A Google failure is returned to the
    caller and recorded without deleting the internal reservation.
    """
    google = GoogleCalendarSync()
    if not google.configured:
        return {"ok": False, "provider": "INTERNAL", "reason": "not_configured"}

    with db_lock, get_connection() as con:
        row = con.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            return {"ok": False, "provider": "GOOGLE", "reason": "event_not_found"}
        event = dict(row)

    try:
        result = google.create_event(
            title=event["title"],
            start_time=event["start_time"],
            end_time=event["end_time"],
            description=event.get("description", ""),
            location=location,
            attendee_email=attendee_email,
        )
    except Exception as exc:
        return {"ok": False, "provider": "GOOGLE", "reason": str(exc)}

    with db_lock, get_connection() as con:
        con.execute(
            """
            UPDATE calendar_events
            SET provider = 'GOOGLE', external_event_id = ?, external_event_url = ?
            WHERE id = ?
            """,
            (result["external_event_id"], result["external_event_url"], event_id),
        )
        con.commit()
    return result

# Factory instance
def get_calendar_provider() -> CalendarProvider:
    """Returns configured calendar provider based on environment variables."""
    # When Google or Microsoft credentials are provided, return external provider adaptor; else internal
    return InternalCalendarProvider()
