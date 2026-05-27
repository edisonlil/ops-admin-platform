from __future__ import annotations

import unittest

from pydantic import ValidationError

from authorization.interfaces.http.dtos import DataAccessPolicyRequest


class DataAccessPolicyRequestTests(unittest.TestCase):
    def test_user_subject_allows_all_users_id(self) -> None:
        payload = DataAccessPolicyRequest(
            subject_type="user",
            subject_id=0,
            resource_key="basic-data.dictionary",
            action="read",
            scope="self",
        )

        self.assertEqual(payload.subject_id, 0)

    def test_department_subject_requires_concrete_department(self) -> None:
        with self.assertRaises(ValidationError):
            DataAccessPolicyRequest(
                subject_type="department",
                subject_id=0,
                resource_key="basic-data.dictionary",
                action="read",
                scope="self",
            )


if __name__ == "__main__":
    unittest.main()
