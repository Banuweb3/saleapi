import unittest
from app import create_app
from extensions import db
from models import User, Sale
from middleware.rate_limiter import auth_limiter

class SalesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        auth_limiter.clear()

        with self.app.app_context():
            db.session.query(Sale).delete()
            db.session.query(User).delete()
            db.session.commit()

            test_user = User(username="salestest")
            test_user.set_password("pass123")
            db.session.add(test_user)
            db.session.commit()

        # Login to obtain Bearer token
        login_res = self.client.post("/api/v1/auth/token", json={"username": "salestest", "password": "pass123"})
        self.assertEqual(login_res.status_code, 200)
        self.token = login_res.json["data"]["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_create_sale_success(self):
        payload = {
            "source_id": 1,
            "invoice_number": "INV-2026-001",
            "invoice_date": "2026-09-29",
            "total_amount": 2450.75,
            "customer_name": "Ramesh Kumar",
            "customer_phone": "9876543210",
            "created_updated_timestamp": "2026-09-29 17:15:00"
        }
        res = self.client.post("/api/v1/sales", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json["code"], 201)
        self.assertEqual(res.json["data"]["source_id"], 1)
        self.assertEqual(res.json["data"]["invoice_number"], "INV-2026-001")
        self.assertEqual(res.json["data"]["customer_phone"], "9876543210")
        self.assertEqual(res.json["data"]["username"], "salestest")

    def test_duplicate_invoice_number_allowed(self):
        payload1 = {
            "source_id": 2,
            "invoice_number": "INV-DUP-001",
            "invoice_date": "2026-09-29",
            "total_amount": 1000.00,
            "customer_name": "Suresh",
            "customer_phone": "9123456789"
        }
        res1 = self.client.post("/api/v1/sales", json=payload1, headers=self.headers)
        self.assertEqual(res1.status_code, 201)

        # Second creation attempt with same invoice_number but different source_id is allowed
        payload2 = {
            "source_id": 3,
            "invoice_number": "INV-DUP-001",
            "invoice_date": "2026-09-29",
            "total_amount": 1000.00,
            "customer_name": "Suresh",
            "customer_phone": "9123456789"
        }
        res2 = self.client.post("/api/v1/sales", json=payload2, headers=self.headers)
        self.assertEqual(res2.status_code, 201)
        self.assertEqual(res2.json["code"], 201)

    def test_invalid_phone_number_accepted(self):
        payload = {
            "source_id": 4,
            "invoice_number": "INV-PHONE-01",
            "invoice_date": "2026-09-29",
            "total_amount": 500.00,
            "customer_name": "Anita",
            "customer_phone": "12345"  # Any phone string accepted
        }
        res = self.client.post("/api/v1/sales", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json["data"]["customer_phone"], "12345")

    def test_invalid_date_format_fallback(self):
        payload = {
            "source_id": 5,
            "invoice_number": "INV-DATE-01",
            "invoice_date": "29/09/2026",
            "total_amount": 500.00,
            "customer_name": "Anita",
            "customer_phone": "9876543210"
        }
        res = self.client.post("/api/v1/sales", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)

    def test_unauthorized_access(self):
        payload = {
            "source_id": 6,
            "invoice_number": "INV-NOAUTH-01",
            "invoice_date": "2026-09-29",
            "total_amount": 500.00,
            "customer_name": "Anita",
            "customer_phone": "9876543210"
        }
        res = self.client.post("/api/v1/sales", json=payload)  # No Bearer header
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json["code"], 401)
        self.assertEqual(res.json["error"], "Authorization Required")

    def test_missing_customer_phone_accepted(self):
        payload = {
            "source_id": 7,
            "invoice_number": "INV-NOPHONE-01",
            "invoice_date": "2026-09-29",
            "total_amount": 500.00,
            "customer_name": "Anita"
        }
        res = self.client.post("/api/v1/sales", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)

    def test_missing_source_id_rejected(self):
        payload = {
            "invoice_number": "INV-NOSID-01",
            "customer_name": "Anita"
        }
        res = self.client.post("/api/v1/sales", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json["message"], "source_id is required.")

    def test_bulk_create_sales_success(self):
        payload = {
            "sales": [
                {
                    "source_id": 100 + i,
                    "invoice_number": f"INV-BULK-{i}",
                    "invoice_date": "2026-09-29",
                    "total_amount": 100.0 + i,
                    "customer_name": f"Customer {i}",
                    "customer_phone": "9876543210"
                }
                for i in range(1, 10)
            ]
        }
        res = self.client.post("/api/v1/sales/bulk", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json["code"], 201)
        self.assertEqual(res.json["data"]["created_count"], 9)

    def test_bulk_create_sales_exceeds_limit(self):
        payload = {
            "sales": [
                {
                    "source_id": 1000 + i,
                    "invoice_number": f"INV-OVER-{i}",
                    "invoice_date": "2026-09-29",
                    "total_amount": 100.0,
                    "customer_name": f"Customer {i}",
                    "customer_phone": "9876543210"
                }
                for i in range(1, 502)  # 501 items (> 500)
            ]
        }
        res = self.client.post("/api/v1/sales/bulk", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Maximum 500 records allowed per request", res.json["message"])
    def test_source_id_duplicate_rejection(self):
        payload1 = {
            "source_id": 1001,
            "invoice_number": "INV-SID-01",
            "invoice_date": "2026-09-29",
            "total_amount": 500.00,
            "customer_name": "Test Customer",
            "customer_phone": "9876543210"
        }
        res1 = self.client.post("/api/v1/sales", json=payload1, headers=self.headers)
        self.assertEqual(res1.status_code, 201)
        self.assertEqual(res1.json["data"]["source_id"], 1001)

        # Duplicate source_id must be rejected
        payload2 = {
            "source_id": 1001,
            "invoice_number": "INV-SID-02",
            "invoice_date": "2026-09-30",
            "total_amount": 750.00,
            "customer_name": "Another Customer"
        }
        res2 = self.client.post("/api/v1/sales", json=payload2, headers=self.headers)
        self.assertEqual(res2.status_code, 409)
        self.assertEqual(res2.json["code"], 409)
        self.assertEqual(res2.json["error"], "Duplicate Entry")

    def test_bulk_source_id_duplicates_skipped(self):
        # 1. First insert record with source_id 2001
        payload_initial = {
            "source_id": 2001,
            "invoice_number": "INV-EXISTING-01"
        }
        res_init = self.client.post("/api/v1/sales", json=payload_initial, headers=self.headers)
        self.assertEqual(res_init.status_code, 201)

        # 2. Bulk payload contains:
        #    - source_id 2001 (already in DB -> should be skipped)
        #    - source_id 2002 (new -> should be created)
        #    - source_id 2003 (new -> should be created)
        #    - source_id 2002 (duplicate within batch -> should be skipped)
        payload_batch = {
            "sales": [
                {"source_id": 2001, "invoice_number": "INV-B-01"},
                {"source_id": 2002, "invoice_number": "INV-B-02"},
                {"source_id": 2003, "invoice_number": "INV-B-03"},
                {"source_id": 2002, "invoice_number": "INV-B-04"}
            ]
        }
        res = self.client.post("/api/v1/sales/bulk", json=payload_batch, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json["data"]["created_count"], 2)
        self.assertEqual(res.json["data"]["skipped_count"], 2)
        created_sids = [s["source_id"] for s in res.json["data"]["sales"]]
        self.assertEqual(created_sids, [2002, 2003])

if __name__ == "__main__":
    unittest.main()

