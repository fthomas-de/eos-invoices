from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone

from eos_invoices.models import PaymentLog

from .base import Due, DueTestCase, make_ceo, make_source


class TestUndoMarking(DueTestCase):
    def setUp(self):
        self.admin = make_ceo(perms=("manage_sources",))
        self.client.force_login(self.admin)

    def mark(self, source, row):
        self.client.post(reverse("eos_invoices:mark_paid", args=[source.pk]), {"row": row.pk})
        return PaymentLog.objects.latest("pk")

    def undo(self, entry):
        return self.client.post(reverse("eos_invoices:undo_marking", args=[entry.pk]))

    def notes(self, response):
        return [str(m) for m in get_messages(response.wsgi_request)]

    def test_should_set_a_boolean_back(self):
        source = make_source()
        row = Due.objects.create(corp_id=2001, amount=10)

        entry = self.mark(source, row)
        self.undo(entry)

        row.refresh_from_db()
        entry.refresh_from_db()
        self.assertFalse(row.paid)
        self.assertEqual(entry.reverted_by, self.admin)
        self.assertEqual(entry.reverted_by_name, "ceo main")

    def test_should_empty_a_stamped_datetime_again(self):
        # the stamp travels through JSON as text; the field has to read it back
        source = make_source(paid_field="paid_at", paid_mode="not_empty")
        row = Due.objects.create(corp_id=2001, amount=10)

        entry = self.mark(source, row)
        row.refresh_from_db()
        self.assertIsNotNone(row.paid_at)

        self.undo(entry)

        row.refresh_from_db()
        self.assertIsNone(row.paid_at)

    def test_should_restore_the_exact_previous_value(self):
        source = make_source(paid_field="state", paid_mode="equals", paid_value="done")
        row = Due.objects.create(corp_id=2001, amount=10, state="pending")

        self.undo(self.mark(source, row))

        row.refresh_from_db()
        self.assertEqual(row.state, "pending")

    def test_should_leave_a_row_the_owning_app_changed_since(self):
        # e.g. an automatic payment check stamped it again in between
        source = make_source(paid_field="paid_at", paid_mode="not_empty")
        row = Due.objects.create(corp_id=2001, amount=10)
        entry = self.mark(source, row)
        later = timezone.now() + timezone.timedelta(minutes=5)
        Due.objects.filter(pk=row.pk).update(paid_at=later)

        self.undo(entry)

        row.refresh_from_db()
        entry.refresh_from_db()
        self.assertEqual(row.paid_at, later)
        self.assertIsNone(entry.reverted_at)

    def test_should_undo_only_once(self):
        source = make_source()
        row = Due.objects.create(corp_id=2001, amount=10)
        entry = self.mark(source, row)
        self.undo(entry)
        # marked again by somebody, then the old entry is clicked a second time
        Due.objects.filter(pk=row.pk).update(paid=True)

        self.undo(entry)

        row.refresh_from_db()
        self.assertTrue(row.paid)

    def test_should_refuse_entries_without_stored_values(self):
        # written before undo existed: nothing to put back
        source = make_source()
        row = Due.objects.create(corp_id=2001, amount=10, paid=True)
        entry = PaymentLog.objects.create(
            user_name="x", source=source, source_name="Due", row_pk=str(row.pk),
            corporation_id=2001, amount=10,
        )

        response = self.undo(entry)

        row.refresh_from_db()
        self.assertTrue(row.paid)
        # refused by can_undo itself, not by a later check that happens to fail
        self.assertIn("This entry cannot be undone.", self.notes(response))
        self.assertNotContains(
            self.client.get(reverse("eos_invoices:log")),
            reverse("eos_invoices:undo_marking", args=[entry.pk]),
        )

    def test_should_refuse_once_the_source_reads_another_model(self):
        # the same pk there is another payment, whose flag may well be True
        source = make_source()
        row = Due.objects.create(corp_id=2001, amount=10)
        entry = self.mark(source, row)
        PaymentLog.objects.filter(pk=entry.pk).update(model_label="otherapp.Tax")

        response = self.undo(entry)

        row.refresh_from_db()
        entry.refresh_from_db()
        self.assertTrue(row.paid)
        self.assertIsNone(entry.reverted_at)
        self.assertIn(
            "This source reads another model since this was marked; nothing was changed.",
            self.notes(response),
        )

    def test_should_still_undo_an_entry_older_than_the_stored_model(self):
        # entries from before migration 0007 have no model to compare
        source = make_source()
        row = Due.objects.create(corp_id=2001, amount=10)
        entry = self.mark(source, row)
        PaymentLog.objects.filter(pk=entry.pk).update(model_label="")

        self.undo(entry)

        row.refresh_from_db()
        self.assertFalse(row.paid)

    def test_should_offer_the_button_and_show_who_undid(self):
        source = make_source()
        row = Due.objects.create(corp_id=2001, amount=10)
        entry = self.mark(source, row)
        log = reverse("eos_invoices:log")

        self.assertContains(self.client.get(log), reverse("eos_invoices:undo_marking", args=[entry.pk]))
        self.undo(entry)
        response = self.client.get(log)
        self.assertContains(response, "Undone by ceo main")
        self.assertNotContains(response, reverse("eos_invoices:undo_marking", args=[entry.pk]))

    def test_should_keep_ceos_out(self):
        source = make_source()
        row = Due.objects.create(corp_id=2001, amount=10)
        entry = self.mark(source, row)

        self.client.force_login(make_ceo("other"))
        self.undo(entry)

        row.refresh_from_db()
        self.assertTrue(row.paid)
