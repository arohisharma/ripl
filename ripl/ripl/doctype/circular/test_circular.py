# Copyright (c) 2026, dewansh and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.exceptions import DoesNotExistError, ValidationError
from frappe.tests.utils import FrappeTestCase

from ripl.api.circular import (
    get_circular_detail,
    get_circulars,
    get_filtered_circulars,
    get_latest_circulars,
)


class TestCircular(FrappeTestCase):
    def setUp(self):
        self.created_docs = []

    def tearDown(self):
        for doctype, name in reversed(self.created_docs):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1)

    def _create_circular(self, **kwargs):
        name = kwargs.pop("name", f"TEST-CIRC-{frappe.generate_hash(length=8)}")
        doc = frappe.get_doc(
            {
                "doctype": "Circular",
                "name": name,
                "title": kwargs.pop("title", f"Circular {name}"),
                "circular_number": kwargs.pop("circular_number", "RBI/2026/001"),
                "circular_date": kwargs.pop("circular_date", "2026-01-01"),
                "regulator": kwargs.pop("regulator", "RBI"),
                "category": kwargs.pop("category", "Compliance"),
                "circular_url": kwargs.pop("circular_url", "https://example.com/circular"),
                "ai_summary": kwargs.pop("ai_summary", "AI summary"),
                "key_points": kwargs.pop("key_points", "Key points"),
                "show_impacted_entities": kwargs.pop("show_impacted_entities", 0),
                "impacted_entities": kwargs.pop("impacted_entities", "All banks"),
                "show_required_actions": kwargs.pop("show_required_actions", 0),
                "required_actions": kwargs.pop("required_actions", "No action"),
                "status": kwargs.pop("status", "Draft"),
            }
        )
        doc.update(kwargs)
        doc.insert(ignore_permissions=True)
        self.created_docs.append(("Circular", doc.name))
        return doc

    def test_before_save_sets_published_fields(self):
        doc = self._create_circular(status="Published", published_by=None, published_date=None)
        self.assertTrue(doc.published_by)
        self.assertTrue(doc.published_date)

    def test_get_circulars_returns_only_published(self):
        published = self._create_circular(title="Published Circular", status="Published")
        self._create_circular(title="Draft Circular", status="Draft")

        response = get_circulars()

        self.assertEqual(response["status"], "success")
        self.assertEqual(len(response["data"]), 1)
        self.assertEqual(response["data"][0]["name"], published.name)

    def test_get_circular_detail_hides_optional_sections(self):
        circular = self._create_circular(
            status="Published",
            show_impacted_entities=0,
            impacted_entities="Impacted data",
            show_required_actions=0,
            required_actions="Action data",
        )

        response = get_circular_detail(circular.name)

        self.assertEqual(response["status"], "success")
        self.assertIsNone(response["data"]["impacted_entities"])
        self.assertIsNone(response["data"]["required_actions"])

    def test_get_circular_detail_requires_name(self):
        with self.assertRaises(ValidationError):
            get_circular_detail(None)

    def test_get_circular_detail_raises_when_not_found(self):
        with self.assertRaises(DoesNotExistError):
            get_circular_detail("MISSING-CIRCULAR")

    def test_get_filtered_circulars_applies_filters_and_search(self):
        self._create_circular(
            title="RBI KYC Master Direction",
            status="Published",
            regulator="RBI",
            category="KYC",
        )
        self._create_circular(
            title="SEBI Market Circular",
            status="Published",
            regulator="SEBI",
            category="Market",
        )

        response = get_filtered_circulars(category="KYC", regulator="RBI", search="master")

        self.assertEqual(response["status"], "success")
        self.assertEqual(len(response["data"]), 1)
        self.assertEqual(response["data"][0]["title"], "RBI KYC Master Direction")

    def test_get_latest_circulars_validates_limit(self):
        with self.assertRaises(ValidationError):
            get_latest_circulars(limit=0)
        with self.assertRaises(ValidationError):
            get_latest_circulars(limit="abc")

    def test_get_latest_circulars_respects_limit(self):
        self._create_circular(name="C-1", title="One", status="Published", circular_date="2026-01-01")
        self._create_circular(name="C-2", title="Two", status="Published", circular_date="2026-01-02")
        self._create_circular(name="C-3", title="Three", status="Published", circular_date="2026-01-03")

        response = get_latest_circulars(limit=2)

        self.assertEqual(response["status"], "success")
        self.assertEqual(len(response["data"]), 2)

    def test_get_circulars_raises_graceful_error_on_failure(self):
        with patch("ripl.api.circular.frappe.get_all", side_effect=Exception("db down")):
            with self.assertRaises(ValidationError):
                get_circulars()
