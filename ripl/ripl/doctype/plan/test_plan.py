# Copyright (c) 2026, dewansh and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase

from ripl.api.plan import get_plans


class TestPlan(FrappeTestCase):
    def setUp(self):
        self.created_docs = []

    def tearDown(self):
        for doctype, name in reversed(self.created_docs):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1)

    def _create_plan(self, **kwargs):
        name = kwargs.pop("name", f"TEST-PLAN-{frappe.generate_hash(length=8)}")
        doc = frappe.get_doc(
            {
                "doctype": "Plan",
                "name": name,
                "plan_name": kwargs.pop("plan_name", f"Plan {name}"),
                "is_active": kwargs.pop("is_active", 1),
                "price": kwargs.pop("price", 1200),
                "duration": kwargs.pop("duration", 12),
                "tag": kwargs.pop("tag", "Popular"),
                "is_highlighted": kwargs.pop("is_highlighted", 0),
                "sort_order": kwargs.pop("sort_order", 1),
            }
        )
        for feature in kwargs.pop("features", []):
            doc.append("features", {"feature": feature})
        doc.update(kwargs)
        doc.insert(ignore_permissions=True)
        self.created_docs.append(("Plan", doc.name))
        return doc

    def test_before_save_sets_monthly_price_and_slug(self):
        plan = self._create_plan(plan_name="Growth Plan", price=3000, duration=6)
        self.assertEqual(float(plan.monthly_price), 500.0)
        self.assertEqual(plan.slug, "growth-plan")

    def test_get_plans_returns_active_plans_with_features(self):
        active = self._create_plan(
            plan_name="Active Plan",
            sort_order=1,
            price=999,
            duration=3,
            features=["Feature A", "Feature B"],
        )
        self._create_plan(plan_name="Inactive Plan", sort_order=2, is_active=0)

        response = get_plans()

        self.assertEqual(len(response), 1)
        self.assertEqual(response[0]["id"], active.name)
        self.assertEqual(response[0]["title"], "Active Plan")
        self.assertEqual(response[0]["monthly_price"], 333)
        self.assertEqual(response[0]["features"], ["Feature A", "Feature B"])

    def test_get_plans_raises_graceful_error_on_failure(self):
        with patch("ripl.api.plan.frappe.get_all", side_effect=Exception("db down")):
            with self.assertRaises(ValidationError):
                get_plans()
