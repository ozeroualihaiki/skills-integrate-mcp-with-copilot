import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src import app as app_module
from src.auth import hash_password


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.users_path = Path(self.temp_dir.name) / "users.json"
        self.users_path.write_text(
            json.dumps(
                {
                    "users": [
                        {
                            "email": "student@mergington.edu",
                            "role": "student",
                            "password_hash": hash_password("student-password-123"),
                        },
                        {
                            "email": "teacher@mergington.edu",
                            "role": "organizer",
                            "password_hash": hash_password("teacher-password-123"),
                        },
                        {
                            "email": "admin@mergington.edu",
                            "role": "admin",
                            "password_hash": hash_password("admin-password-123"),
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.users_file_patch = patch.object(app_module, "users_file", self.users_path)
        self.users_file_patch.start()
        self.activity_name = "Authentication test activity"
        app_module.activities[self.activity_name] = {
            "description": "Test activity",
            "schedule": "Test schedule",
            "max_participants": 5,
            "participants": [],
        }
        self.client = TestClient(app_module.app)

    def tearDown(self):
        self.client.close()
        app_module.activities.pop(self.activity_name, None)
        self.users_file_patch.stop()
        self.temp_dir.cleanup()

    def sign_in(self, email, password):
        response = self.client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["csrf_token"]

    def test_activity_changes_require_authentication(self):
        response = self.client.post(
            f"/activities/{self.activity_name}/signup?email=student@mergington.edu"
        )
        self.assertEqual(response.status_code, 401)

    def test_student_can_only_change_their_own_registration(self):
        csrf_token = self.sign_in(
            "student@mergington.edu", "student-password-123"
        )

        denied = self.client.post(
            f"/activities/{self.activity_name}/signup?email=someone-else@mergington.edu",
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(denied.status_code, 403)

        signup = self.client.post(
            f"/activities/{self.activity_name}/signup",
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(signup.status_code, 200)
        self.assertEqual(
            app_module.activities[self.activity_name]["participants"],
            ["student@mergington.edu"],
        )

        unregister = self.client.delete(
            f"/activities/{self.activity_name}/unregister",
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(unregister.status_code, 200)
        self.assertEqual(app_module.activities[self.activity_name]["participants"], [])

    def test_organizer_can_manage_a_student_registration(self):
        csrf_token = self.sign_in(
            "teacher@mergington.edu", "teacher-password-123"
        )

        signup = self.client.post(
            f"/activities/{self.activity_name}/signup?email=student@mergington.edu",
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(signup.status_code, 200)

        unregister = self.client.delete(
            f"/activities/{self.activity_name}/unregister?email=student@mergington.edu",
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(unregister.status_code, 200)

    def test_admin_can_manage_a_student_registration(self):
        csrf_token = self.sign_in("admin@mergington.edu", "admin-password-123")

        response = self.client.post(
            f"/activities/{self.activity_name}/signup?email=student@mergington.edu",
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(response.status_code, 200)

    def test_mutations_require_csrf_token(self):
        self.sign_in("student@mergington.edu", "student-password-123")

        response = self.client.post(
            f"/activities/{self.activity_name}/signup"
        )
        self.assertEqual(response.status_code, 403)

    def test_invalid_credentials_are_rejected(self):
        response = self.client.post(
            "/auth/login",
            json={
                "email": "student@mergington.edu",
                "password": "incorrect-password",
            },
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
