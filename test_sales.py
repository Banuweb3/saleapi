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
        self.assertEqual(res.json["data"]["invoice_number"], "INV-2026-001")
        self.assertEqual(res.json["data"]["customer_phone"], "9876543210")
        self.assertEqual(res.json["data"]["username"], "salestest")

    def test_duplicate_invoice_number(self):
        payload = {
            "invoice_number": "INV-DUP-001",
            "invoice_date": "2026-09-29",
            "total_amount": 1000.00,
            "customer_name": "Suresh",
            "customer_phone": "9123456789"
        }
        res1 = self.client.post("/api/v1/sales", json=payload, headers=self.headers)
        self.assertEqual(res1.status_code, 201)

        # Second creation attempt with same invoice_number
        res2 = self.client.post("/api/v1/sales", json=payload, headers=self.headers)
        self.assertEqual(res2.status_code, 409)
        self.assertEqual(res2.json["code"], 409)
        self.assertEqual(res2.json["error"], "Duplicate Entry")

    def test_invalid_phone_number(self):
        payload = {
            "invoice_number": "INV-PHONE-01",
            "invoice_date": "2026-09-29",
            "total_amount": 500.00,
            "customer_name": "Anita",
            "customer_phone": "12345"  # Invalid 5-digit phone
        }
        res = self.client.post("/api/v1/sales", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json["code"], 400)
        self.assertIn("10-digit number", res.json["message"])

    def test_invalid_date_format(self):
        payload = {
            "invoice_number": "INV-DATE-01",
            "invoice_date": "29/09/2026",  # Invalid DD/MM/YYYY format
            "total_amount": 500.00,
            "customer_name": "Anita",
            "customer_phone": "9876543210"
        }
        res = self.client.post("/api/v1/sales", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("YYYY-MM-DD format", res.json["message"])

    def test_unauthorized_access(self):
        payload = {
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

    def test_missing_customer_phone(self):
        payload = {
            "invoice_number": "INV-NOPHONE-01",
            "invoice_date": "2026-09-29",
            "total_amount": 500.00,
            "customer_name": "Anita"
        }
        res = self.client.post("/api/v1/sales", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json["message"], "customer_phone is required.")

    def test_bulk_create_sales_success(self):
        payload = {
            "sales": [
                {
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

    def test_bulk_create_sales_missing_phone(self):
        payload = {
            "sales": [
                {
                    "invoice_number": "INV-BULK-FAIL",
                    "invoice_date": "2026-09-29",
                    "total_amount": 500.0,
                    "customer_name": "No Phone User"
                }
            ]
        }
        res = self.client.post("/api/v1/sales/bulk", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json["failed_count"], 1)
        self.assertIn("customer_phone is required.", res.json["details"][0]["errors"])

if __name__ == "__main__":
    unittest.main()

