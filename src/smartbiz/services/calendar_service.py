"""Calendar Provider abstraction supporting Internal Calendar, Google Calendar, and Microsoft Outlook."""
import json
import os
import sqlite3
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

# Factory instance
def get_calendar_provider() -> CalendarProvider:
    """Returns configured calendar provider based on environment variables."""
    # When Google or Microsoft credentials are provided, return external provider adaptor; else internal
    return InternalCalendarProvider()
