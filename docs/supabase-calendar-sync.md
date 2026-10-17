# Supabase Calendar Sync — isolated recovery

The deployed SmartBiz Safety App Supabase project is **separate** from this repository's SQLite-backed calendar implementation. This worker provides a narrow integration path; it is **not deployed by adding it to GitHub**.

## Safety boundaries
- Defaults to dry run. No calendar or database writes unless `CALENDAR_SYNC_APPLY=true`.
- Only `confirmed`, future-dated bookings with concrete `start_at` and `end_at` timestamps qualify.
- Historical `requested` and `completed` bookings remain untouched.
- Uses deterministic event IDs for safe retry after partial failure and avoids invitation emails.
- Does not generate or send customer outreach. Gmail remains draft-only.
- Operate a single worker process and monitor logs before increasing schedule frequency.

## Required backend secrets
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, optionally `GOOGLE_CALENDAR_ID`.

Do not place service-role or OAuth values in a browser or Git. Store them in the production secret manager. The OAuth token needs appropriate Calendar event permissions.

## Safe validation
1. `python -m unittest tests/test_supabase_calendar_sync.py`
2. Set only the Supabase URL and service-role key in a secure runtime; run `python scripts/supabase_calendar_sync.py` (dry-run, no writes).
3. Confirm the five old queue records are reported as skipped.
4. Configure Google OAuth secrets, create one approved future booking with status `confirmed`, and run with `CALENDAR_SYNC_APPLY=true` in a controlled environment.
5. Verify the event ID in Google Calendar, `service_bookings.calendar_event_id` and `calendar_sync_queue.processed_at`. Repeat the worker and confirm no duplicate event.
6. Only after validation, schedule it in the backend worker environment. Supabase Cron currently has no jobs.

**Not yet implemented:** production secrets, worker deployment, health monitoring, and reconciliation of the five old records. Do not backfill them without customer approval.
