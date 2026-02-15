"""
Feature 2 — Subscriber Notes (Long-term Memory) Tests.

Tests note CRUD, prompt formatting, agent tool execution, and dashboard APIs.
"""

import json

from django.test import TestCase

from accounts.models import Subscriber
from agent.models import SubscriberNote
from agent.notes_service import (
    save_note,
    get_active_notes,
    update_note,
    format_notes_for_prompt,
    MAX_ACTIVE_NOTES,
)


def _create_subscriber(**kwargs):
    defaults = {
        "subscription_number": "01-800001-01",
        "phone_number": "+962798000001",
        "name": "Notes Test User",
        "area": "Abdoun",
        "governorate": "Amman",
        "tariff_category": "residential",
        "household_size": 4,
        "is_verified": True,
        "language": "en",
    }
    defaults.update(kwargs)
    return Subscriber.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Subscriber Notes Service Tests
# ---------------------------------------------------------------------------

class SaveNoteTest(TestCase):
    def setUp(self):
        self.sub = _create_subscriber()

    def test_save_note_creates_note(self):
        note = save_note(self.sub, "appliance", "Has a 2kW water heater on timer")
        self.assertEqual(note.subscriber, self.sub)
        self.assertEqual(note.category, "appliance")
        self.assertTrue(note.is_active)

    def test_save_note_caps_at_max(self):
        for i in range(12):
            save_note(self.sub, "appliance", f"Fact {i}")
        active = SubscriberNote.objects.filter(subscriber=self.sub, is_active=True)
        self.assertEqual(active.count(), MAX_ACTIVE_NOTES)

    def test_save_note_deactivates_oldest(self):
        notes = []
        for i in range(12):
            notes.append(save_note(self.sub, "appliance", f"Fact {i}"))
        # Oldest notes should be deactivated
        oldest = SubscriberNote.objects.get(id=notes[0].id)
        self.assertFalse(oldest.is_active)
        newest = SubscriberNote.objects.get(id=notes[11].id)
        self.assertTrue(newest.is_active)


class GetActiveNotesTest(TestCase):
    def setUp(self):
        self.sub = _create_subscriber()

    def test_returns_active_notes(self):
        save_note(self.sub, "appliance", "Has AC")
        save_note(self.sub, "schedule", "Works from home 9-5")
        notes = get_active_notes(self.sub)
        self.assertEqual(len(notes), 2)

    def test_excludes_inactive_notes(self):
        note = save_note(self.sub, "appliance", "Had EV")
        note.is_active = False
        note.save()
        notes = get_active_notes(self.sub)
        self.assertEqual(len(notes), 0)

    def test_returns_newest_first(self):
        save_note(self.sub, "appliance", "Old fact")
        save_note(self.sub, "goal", "New fact")
        notes = get_active_notes(self.sub)
        self.assertEqual(notes[0].content, "New fact")


class UpdateNoteTest(TestCase):
    def setUp(self):
        self.sub = _create_subscriber()

    def test_update_content(self):
        note = save_note(self.sub, "appliance", "Has 1 AC")
        result = update_note(self.sub, note.id, content="Has 2 ACs")
        self.assertEqual(result["status"], "updated")
        note.refresh_from_db()
        self.assertEqual(note.content, "Has 2 ACs")

    def test_deactivate_note(self):
        note = save_note(self.sub, "appliance", "Has EV")
        result = update_note(self.sub, note.id, is_active=False)
        note.refresh_from_db()
        self.assertFalse(note.is_active)

    def test_update_nonexistent_note(self):
        result = update_note(self.sub, 99999, content="test")
        self.assertIn("error", result)


class FormatNotesForPromptTest(TestCase):
    def setUp(self):
        self.sub = _create_subscriber()

    def test_format_with_notes(self):
        save_note(self.sub, "appliance", "Has water heater")
        save_note(self.sub, "goal", "Wants to save 5 JOD/month")
        block = format_notes_for_prompt(self.sub)
        self.assertIn("What You Know About This User", block)
        self.assertIn("[appliance] Has water heater", block)
        self.assertIn("[goal] Wants to save 5 JOD/month", block)

    def test_format_no_notes_returns_empty(self):
        block = format_notes_for_prompt(self.sub)
        self.assertEqual(block, "")


# ---------------------------------------------------------------------------
# Notes Tool Execution Tests
# ---------------------------------------------------------------------------

class NotesToolExecutionTest(TestCase):
    def setUp(self):
        self.sub = _create_subscriber()

    def test_save_note_tool(self):
        from agent.tools import execute_tool
        result = json.loads(execute_tool("save_note", {
            "phone": self.sub.phone_number,
            "category": "appliance",
            "content": "Has a washing machine that runs nightly",
        }))
        self.assertEqual(result["status"], "saved")
        self.assertEqual(SubscriberNote.objects.count(), 1)

    def test_get_notes_tool(self):
        from agent.tools import execute_tool
        save_note(self.sub, "schedule", "Works night shifts")
        result = json.loads(execute_tool("get_notes", {
            "phone": self.sub.phone_number,
        }))
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["notes"][0]["category"], "schedule")

    def test_update_note_tool(self):
        from agent.tools import execute_tool
        note = save_note(self.sub, "appliance", "Has EV")
        result = json.loads(execute_tool("update_note", {
            "phone": self.sub.phone_number,
            "note_id": note.id,
            "is_active": False,
        }))
        self.assertEqual(result["status"], "updated")
        note.refresh_from_db()
        self.assertFalse(note.is_active)

    def test_save_note_tool_unknown_phone(self):
        from agent.tools import execute_tool
        result = json.loads(execute_tool("save_note", {
            "phone": "+962790000000",
            "category": "appliance",
            "content": "test",
        }))
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# Notes Dashboard API Tests
# ---------------------------------------------------------------------------

class NotesDashboardAPITest(TestCase):
    def setUp(self):
        self.sub = _create_subscriber()
        self.note = save_note(self.sub, "appliance", "Has water heater")

    def test_list_notes(self):
        resp = self.client.get(f"/api/agent/notes/{self.sub.subscription_number}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["category"], "appliance")

    def test_deactivate_note_via_api(self):
        resp = self.client.delete(
            f"/api/agent/notes/{self.sub.subscription_number}/{self.note.id}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.note.refresh_from_db()
        self.assertFalse(self.note.is_active)

    def test_deactivate_note_404(self):
        resp = self.client.delete(
            f"/api/agent/notes/{self.sub.subscription_number}/99999/"
        )
        self.assertEqual(resp.status_code, 404)

    def test_list_notes_invalid_sub(self):
        resp = self.client.get("/api/agent/notes/99-999999-99/")
        self.assertEqual(resp.status_code, 404)
