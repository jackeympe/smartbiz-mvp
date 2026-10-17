"""Supabase -> Google Calendar booking sync. Runs only on explicit invocation.

Requires backend-only credentials. Defaults to dry-run and never replays old bookings.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

def request(url, *, method="GET", headers=None, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        # Never log response bodies: may contain customer details or secrets.
        raise ApiError(exc.code) from exc

class ApiError(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__(f"Remote API returned HTTP {status}")

def google_event_id(booking_id):
    # Google IDs permit lowercase hex digits; deterministic IDs prevent duplicates.
    compact = booking_id.lower().replace("-", "")
    if len(compact) != 32 or any(c not in "0123456789abcdef" for c in compact):
        raise ValueError("Invalid booking UUID")
    return "sb" + compact

def eligible(row, now):
    if row.get("status") != "confirmed":
        return False
    if row.get("calendar_sync_status") not in ("pending", "retry"):
        return False
    if row.get("calendar_event_id"):
        return False
    try:
        start = datetime.fromisoformat(row["start_at"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(row["end_at"].replace("Z", "+00:00"))
        return start.tzinfo is not None and end.tzinfo is not None and now < start < end
    except (ValueError, TypeError, KeyError, AttributeError):
        return False

def run():
    endpoint = os.environ["SUPABASE_URL"].rstrip("/")
    secret = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    refresh = os.environ.get("GOOGLE_REFRESH_TOKEN", "")
    calendar = urllib.parse.quote(os.environ.get("GOOGLE_CALENDAR_ID", "primary"), safe="")
    dry_run = os.environ.get("CALENDAR_SYNC_APPLY", "false").lower() != "true"
    db_headers = {"apikey": secret, "Authorization": "Bearer " + secret, "Content-Type": "application/json"}
    base = endpoint + "/rest/v1/"
    if not dry_run and not (client_id and client_secret and refresh):
        raise RuntimeError("Google OAuth is not configured")
    queue = request(base + "calendar_sync_queue?select=id,booking_id,action,processed_at&processed_at=is.null&action=eq.create&order=created_at.asc&limit=1000", headers=db_headers)
    if not queue:
        print("No pending queue items")
        return
    token = None
    now = datetime.now(timezone.utc)
    eligible_count = 0
    for item in queue:
        booking_id = item["booking_id"]
        rows = request(base + "service_bookings?select=id,status,calendar_sync_status,calendar_event_id,start_at,end_at,service_type,address,city,booking_ref&id=eq." + urllib.parse.quote(booking_id, safe="") + "&limit=1", headers=db_headers)
        if not rows or not eligible(rows[0], now):
            print(f"Skipped ineligible booking queue item {item['id']}")
            continue
        row = rows[0]
        eligible_count += 1
        if dry_run:
            print(f"Eligible booking: {booking_id} (dry-run, no writes)")
            continue
        if token is None:
            form = urllib.parse.urlencode({"client_id":client_id,"client_secret":client_secret,"refresh_token":refresh,"grant_type":"refresh_token"}).encode()
            response = urllib.request.Request("https://oauth2.googleapis.com/token", data=form, headers={"Content-Type":"application/x-www-form-urlencoded"}, method="POST")
            with urllib.request.urlopen(response, timeout=20) as res:
                token = json.loads(res.read())["access_token"]
        eid = google_event_id(booking_id)
        google_url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar}/events"
        google_headers = {"Authorization":"Bearer " + token, "Content-Type":"application/json"}
        event_url = google_url + "/" + eid
        try:
            event = request(event_url, headers=google_headers)
        except ApiError as exc:
            if exc.status != 404:
                raise
            payload = {
                "id":eid,
                "summary":"SmartBiz Fire service appointment",
                "description":"Booking reference: " + str(row.get("booking_ref") or booking_id),
                "location":", ".join(x for x in (row.get("address"),row.get("city")) if x),
                "start":{"dateTime":row["start_at"]},
                "end":{"dateTime":row["end_at"]},
            }
            try:
                event = request(google_url + "?sendUpdates=none", method="POST", headers=google_headers, payload=payload)
            except ApiError as create_error:
                if create_error.status != 409:
                    raise
                event = request(event_url, headers=google_headers)
        if event.get("id") != eid:
            raise RuntimeError("Calendar event verification failed")
        # Retrying after partial DB failure is safe: the same deterministic event ID is reused.
        patch_headers = {**db_headers, "Prefer":"return=representation"}
        updated = request(base + "service_bookings?id=eq." + urllib.parse.quote(booking_id, safe="") + "&calendar_event_id=is.null", method="PATCH", headers=patch_headers, payload={
            "calendar_event_id":eid, "calendar_html_link":event.get("htmlLink"),
            "calendar_sync_status":"synced", "calendar_synced_at":datetime.now(timezone.utc).isoformat()
        })
        if not updated:
            raise RuntimeError("Booking update failed or concurrent update detected")
        request(base + "calendar_sync_queue?id=eq." + urllib.parse.quote(item["id"], safe="") + "&processed_at=is.null", method="PATCH", headers=db_headers, payload={"processed_at":datetime.now(timezone.utc).isoformat()})
        print(f"Synced queue item {item['id']}")
    print(f"Eligible future confirmed bookings: {eligible_count}; apply={not dry_run}")

if __name__ == "__main__":
    try:
        run()
    except (ApiError, RuntimeError, ValueError, KeyError, urllib.error.URLError) as exc:
        print(f"Calendar sync stopped: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
