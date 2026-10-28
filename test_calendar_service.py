import os
import tempfile
import unittest

from calendar_service import ApiError, CalendarService, SESSION_SECONDS

SLOT = "2026-11-02T10"
OTHER_SLOT = "2026-11-02T11"


class FakeClock:
    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now


class CalendarServiceTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.service = CalendarService(clock=self.clock)
        self.nishita = self.service.login("Nishita")["token"]
        self.ritika = self.service.login("Ritika")["token"]

    def assertApiError(self, status, func, *args):
        with self.assertRaises(ApiError) as ctx:
            func(*args)
        self.assertEqual(ctx.exception.status, status)

    def test_login_rejects_unknown_name(self):
        self.assertApiError(400, self.service.login, "Mallory")

    def test_visitor_gets_fifteen_minutes_owner_gets_none(self):
        visitor = self.service.login("Yuvraj")
        self.assertEqual(visitor["expiresAt"] - visitor["now"], SESSION_SECONDS * 1000)
        self.assertEqual(visitor["role"], "visitor")
        owner = self.service.login("Nishita")
        self.assertIsNone(owner["expiresAt"])
        self.assertEqual(owner["role"], "owner")

    def test_only_owner_can_block(self):
        self.assertApiError(403, self.service.block, self.ritika, [{"slot": SLOT, "title": "x"}])

    def test_blocked_slot_cannot_be_booked(self):
        self.service.block(self.nishita, [{"slot": SLOT, "title": "Excel"}])
        self.assertApiError(409, self.service.book, self.ritika, SLOT, "Chai", "")

    def test_booking_stored_and_visible(self):
        self.service.book(self.ritika, SLOT, "Chai", "hi")
        booking = self.service.calendar(self.nishita)["bookings"][SLOT]
        self.assertEqual(booking, {"by": "Ritika", "kind": "Chai", "note": "hi"})

    def test_double_booking_rejected(self):
        self.service.book(self.ritika, SLOT, "Chai", "")
        other = self.service.login("Prateek")["token"]
        self.assertApiError(409, self.service.book, other, SLOT, "Coffee", "")

    def test_cannot_block_booked_slot(self):
        self.service.book(self.ritika, SLOT, "Chai", "")
        self.assertApiError(409, self.service.block, self.nishita, [{"slot": SLOT, "title": "x"}])

    def test_booking_after_expiry_rejected(self):
        self.clock.now += SESSION_SECONDS + 1
        self.assertApiError(403, self.service.book, self.ritika, SLOT, "Chai", "")

    def test_owner_cannot_book(self):
        self.assertApiError(403, self.service.book, self.nishita, SLOT, "Chai", "")

    def test_unblock_frees_slot(self):
        self.service.block(self.nishita, [{"slot": SLOT, "title": "x"}])
        self.service.unblock(self.nishita, SLOT)
        self.service.book(self.ritika, SLOT, "Chai", "")

    def test_cancel_rules(self):
        self.service.book(self.ritika, SLOT, "Chai", "")
        other = self.service.login("Prateek")["token"]
        self.assertApiError(403, self.service.cancel, other, SLOT)
        self.service.cancel(self.nishita, SLOT)
        self.assertNotIn(SLOT, self.service.calendar(self.nishita)["bookings"])
        self.service.book(self.ritika, OTHER_SLOT, "Chai", "")
        self.service.cancel(self.ritika, OTHER_SLOT)
        self.assertEqual(self.service.calendar(self.nishita)["bookings"], {})

    def test_invalid_slots_rejected(self):
        for bad in ("nope", "2026-02-31T10", "2026-11-02T03", "2026-11-02T24", None, 5):
            self.assertApiError(400, self.service.unblock, self.nishita, bad)

    def test_batch_is_validated_and_atomic(self):
        items = [{"slot": SLOT, "title": "ok"}, {"slot": "bad", "title": "ok"}]
        self.assertApiError(400, self.service.block, self.nishita, items)
        self.assertEqual(self.service.calendar(self.nishita)["blocks"], {})
        self.assertApiError(400, self.service.block, self.nishita, [])
        self.assertApiError(400, self.service.block, self.nishita, [{"slot": SLOT, "title": "  "}])

    def test_unknown_token_rejected(self):
        self.assertApiError(401, self.service.calendar, "nope")

    def test_text_is_trimmed_to_limits(self):
        self.service.book(self.ritika, SLOT, "k" * 500, "n" * 500)
        booking = self.service.calendar(self.ritika)["bookings"][SLOT]
        self.assertEqual((len(booking["kind"]), len(booking["note"])), (60, 140))

    def test_data_persists_to_disk(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "data.json")
            first = CalendarService(path, clock=self.clock)
            token = first.login("Nishita")["token"]
            first.block(token, [{"slot": SLOT, "title": "Excel"}])
            second = CalendarService(path, clock=self.clock)
            token = second.login("Nishita")["token"]
            self.assertEqual(second.calendar(token)["blocks"], {SLOT: {"title": "Excel"}})


if __name__ == "__main__":
    unittest.main()
