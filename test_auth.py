import unittest
from app import create_app
from extensions import db
from models import User
from middleware.rate_limiter import auth_limiter

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Clear rate limit cache before each test
        auth_limiter.clear()

        with self.app.app_context():
            user = User.query.filter_by(username="authtest").first()
            if user:
                db.session.delete(user)
                db.session.commit()

            test_user = User(username="authtest")
            test_user.set_password("secret123")
            db.session.add(test_user)
            db.session.commit()

    def test_single_active_token_flow(self):
        # 1. First Login -> POST /api/v1/auth/token -> get Token 1
        res1 = self.client.post("/api/v1/auth/token", json={"username": "authtest", "password": "secret123"})
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json["code"], 200)
        token1 = res1.json["data"]["access_token"]

        # 2. Token 1 should be valid for /api/v1/auth/me
        headers1 = {"Authorization": f"Bearer {token1}"}
        res_me1 = self.client.get("/api/v1/auth/me", headers=headers1)
        self.assertEqual(res_me1.status_code, 200)

        # 3. Second Login -> POST /api/v1/auth/token -> get Token 2 (revokes Token 1)
        res2 = self.client.post("/api/v1/auth/token", json={"username": "authtest", "password": "secret123"})
        self.assertEqual(res2.status_code, 200)
        token2 = res2.json["data"]["access_token"]
        self.assertNotEqual(token1, token2)

        # 4. Token 1 should NOW BE REVOKED (401)
        res_me1_again = self.client.get("/api/v1/auth/me", headers=headers1)
        self.assertEqual(res_me1_again.status_code, 401)
        self.assertEqual(res_me1_again.json["error"], "Token Revoked")

        # 5. Token 2 should be valid
        headers2 = {"Authorization": f"Bearer {token2}"}
        res_me2 = self.client.get("/api/v1/auth/me", headers=headers2)
        self.assertEqual(res_me2.status_code, 200)

    def test_rate_limit_exceeded(self):
        # Perform 4 attempts (max allowed per hour)
        for i in range(4):
            res = self.client.post("/api/v1/auth/token", json={"username": "authtest", "password": "wrong_password"})
            self.assertIn(res.status_code, [401, 200])

        # 5th attempt should be blocked by rate limiter (429)
        res_blocked = self.client.post("/api/v1/auth/token", json={"username": "authtest", "password": "secret123"})
        self.assertEqual(res_blocked.status_code, 429)
        self.assertEqual(res_blocked.json["code"], 429)
        self.assertEqual(res_blocked.json["error"], "Rate Limit Exceeded")
        self.assertIn("4 attempts allowed per hour", res_blocked.json["message"])

if __name__ == "__main__":
    unittest.main()
