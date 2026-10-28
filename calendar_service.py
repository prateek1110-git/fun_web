"""Business logic for Nishita's (very scarce) calendar. No HTTP in here."""

import json
import os
import re
import secrets
import threading
import time
from datetime import date

OWNER = "Nishita"
VISITORS = ("Prateek", "Ritika", "Yuvraj")
USERS = VISITORS + (OWNER,)
SESSION_SECONDS = 15 * 60
FIRST_HOUR = 8
LAST_HOUR = 23
MAX_TITLE = 60
MAX_NOTE = 140
MAX_BATCH = 20

_SLOT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2})$")


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def validate_slot(slot):
    match = _SLOT_RE.match(slot) if isinstance(slot, str) else None
    if not match:
        raise ApiError(400, "That time slot looks fishy.")
    try:
        date.fromisoformat(match.group(1))
    except ValueError:
        raise ApiError(400, "That date does not exist, unlike Nishita's free time.")
    if not FIRST_HOUR <= int(match.group(2)) <= LAST_HOUR:
        raise ApiError(400, "That hour is outside the calendar.")
    return slot


def clean_text(value, limit, fallback=None):
    text = value.strip()[:limit] if isinstance(value, str) else ""
    if not text:
        if fallback is None:
            raise ApiError(400, "Please fill in all the fields.")
        return fallback
    return text


class CalendarService:
    def __init__(self, data_file=None, clock=time.time):
        self._data_file = data_file
        self._clock = clock
        self._lock = threading.Lock()
        self._sessions = {}
        self._blocks = {}
        self._bookings = {}
        self._load()

    def _load(self):
        if not self._data_file or not os.path.exists(self._data_file):
            return
        with open(self._data_file, encoding="utf-8") as handle:
            data = json.load(handle)
        self._blocks = data.get("blocks", {})
        self._bookings = data.get("bookings", {})

    def _save(self):
        if not self._data_file:
            return
        tmp_path = self._data_file + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump({"blocks": self._blocks, "bookings": self._bookings}, handle, indent=2)
        os.replace(tmp_path, self._data_file)

    def _now_ms(self):
        return int(self._clock() * 1000)

    def _session(self, token):
        session = self._sessions.get(token)
        if not session:
            raise ApiError(401, "Your session vanished. Please log in again.")
        return session

    def _owner_session(self, token):
        session = self._session(token)
        if session["name"] != OWNER:
            raise ApiError(403, "Nice try. Only Nishita can block her own calendar.")
        return session

    def _visitor_session(self, token):
        session = self._session(token)
        if session["name"] == OWNER:
            raise ApiError(403, "Nishita, you cannot book yourself. Go to sleep.")
        if self._now_ms() >= session["expires_at"]:
            raise ApiError(403, "Time's up! Your 15 minutes are gone. Nishita's calendar moved on.")
        return session

    def login(self, name):
        if name not in USERS:
            raise ApiError(400, "Unknown guest. Pick a name from the list.")
        now = self._now_ms()
        expires_at = None if name == OWNER else now + SESSION_SECONDS * 1000
        token = secrets.token_urlsafe(24)
        with self._lock:
            self._sessions[token] = {"name": name, "expires_at": expires_at or float("inf")}
        return {
            "token": token,
            "name": name,
            "role": "owner" if name == OWNER else "visitor",
            "expiresAt": expires_at,
            "now": now,
        }

    def calendar(self, token):
        with self._lock:
            session = self._session(token)
            expires_at = session["expires_at"]
            return {
                "name": session["name"],
                "blocks": dict(self._blocks),
                "bookings": dict(self._bookings),
                "expiresAt": None if expires_at == float("inf") else expires_at,
                "now": self._now_ms(),
            }

    def block(self, token, items):
        if not isinstance(items, list) or not 0 < len(items) <= MAX_BATCH:
            raise ApiError(400, "Nothing to block.")
        cleaned = []
        for item in items:
            item = item if isinstance(item, dict) else {}
            cleaned.append((validate_slot(item.get("slot")), clean_text(item.get("title"), MAX_TITLE)))
        with self._lock:
            self._owner_session(token)
            for slot, _ in cleaned:
                if slot in self._bookings:
                    raise ApiError(409, "Someone already booked that slot. Decline them first.")
            for slot, title in cleaned:
                self._blocks[slot] = {"title": title}
            self._save()

    def unblock(self, token, slot):
        with self._lock:
            self._owner_session(token)
            self._blocks.pop(validate_slot(slot), None)
            self._save()

    def book(self, token, slot, kind, note):
        slot = validate_slot(slot)
        kind = clean_text(kind, MAX_TITLE)
        note = clean_text(note, MAX_NOTE, fallback="")
        with self._lock:
            session = self._visitor_session(token)
            if slot in self._blocks:
                raise ApiError(409, "Nishita is 'busy' then. Pick another slot.")
            if slot in self._bookings:
                raise ApiError(409, "Too slow! Someone else grabbed that slot.")
            self._bookings[slot] = {"by": session["name"], "kind": kind, "note": note}
            self._save()

    def cancel(self, token, slot):
        slot = validate_slot(slot)
        with self._lock:
            session = self._session(token)
            booking = self._bookings.get(slot)
            if booking and session["name"] not in (OWNER, booking["by"]):
                raise ApiError(403, "You can only cancel your own appointments.")
            self._bookings.pop(slot, None)
            self._save()
