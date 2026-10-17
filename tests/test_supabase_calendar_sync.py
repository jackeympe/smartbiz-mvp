import unittest
from datetime import datetime, timedelta, timezone
from scripts.supabase_calendar_sync import eligible, google_event_id

NOW = datetime(2026, 10, 17, tzinfo=timezone.utc)

class CalendarWorkerTests(unittest.TestCase):
    def booking(self, **overrides):
        row = {
            "status": "confirmed", "calendar_sync_status": "pending",
            "calendar_event_id": None,
            "start_at": (NOW + timedelta(days=1)).isoformat(),
            "end_at": (NOW + timedelta(days=1, hours=1)).isoformat(),
        }
        row.update(overrides)
        return row

    def test_confirmed_future_booking(self):
        self.assertTrue(eligible(self.booking(), NOW))

    def test_requested_and_completed_skipped(self):
        for status in ("requested", "completed", "cancelled"):
            self.assertFalse(eligible(self.booking(status=status), NOW))

    def test_old_booking_skipped(self):
        self.assertFalse(eligible(self.booking(start_at=(NOW - timedelta(days=1)).isoformat()), NOW))

    def test_missing_times_skipped(self):
        self.assertFalse(eligible(self.booking(start_at=None), NOW))

    def test_existing_event_skipped(self):
        self.assertFalse(eligible(self.booking(calendar_event_id="previous"), NOW))

    def test_deterministic_google_event_id(self):
        self.assertEqual(google_event_id("c3f5e2d7-3d16-485c-9407-fd134d2273e8"),
                         "sbc3f5e2d73d16485c9407fd134d2273e8")
        with self.assertRaises(ValueError):
            google_event_id("bad-id")

if __name__ == "__main__":
    unittest.main()
