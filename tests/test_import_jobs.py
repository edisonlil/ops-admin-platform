from __future__ import annotations

import unittest
from time import sleep
from threading import Event

from fastapi import HTTPException

from identity_access.application import import_jobs


class ImportJobTests(unittest.TestCase):
    def setUp(self) -> None:
        import_jobs.reset_import_jobs_for_tests()

    def tearDown(self) -> None:
        import_jobs.reset_import_jobs_for_tests()

    def test_current_import_job_is_scoped_by_kind_and_tenant(self) -> None:
        platform = import_jobs.start_import_job("platform_users", lambda _progress: {"count": 1})
        tenant_one = import_jobs.start_import_job("tenant_users", lambda _progress: {"count": 2}, scope_id=1)
        tenant_two = import_jobs.start_import_job("tenant_users", lambda _progress: {"count": 3}, scope_id=2)

        self.assertEqual(import_jobs.current_import_job("platform_users")["id"], platform["id"])
        self.assertEqual(import_jobs.current_import_job("tenant_users", scope_id=1)["id"], tenant_one["id"])
        self.assertEqual(import_jobs.current_import_job("tenant_users", scope_id=2)["id"], tenant_two["id"])
        self.assertIsNone(import_jobs.current_import_job("tenant_users", scope_id=3))

    def test_concurrent_guard_only_blocks_same_scope(self) -> None:
        release = Event()

        def wait_for_release(_progress: object) -> dict[str, int]:
            release.wait(timeout=2)
            return {"count": 1}

        try:
            import_jobs.start_import_job("tenant_users", wait_for_release, scope_id=1)
            import_jobs.start_import_job("tenant_users", lambda _progress: {"count": 1}, scope_id=2)

            with self.assertRaises(HTTPException):
                import_jobs.start_import_job("tenant_users", lambda _progress: {"count": 1}, scope_id=1)
        finally:
            release.set()

    def test_failed_job_uses_http_exception_detail_as_error(self) -> None:
        def fail_with_http_detail(_progress: object) -> dict[str, int]:
            raise HTTPException(status_code=400, detail="导入模板表头不正确")

        job = import_jobs.start_import_job("tenant_users", fail_with_http_detail, scope_id=1)

        for _ in range(100):
            current = import_jobs.current_import_job("tenant_users", scope_id=1)
            if current and not current["is_active"]:
                break
            sleep(0.01)
        else:
            self.fail("import job did not finish")

        current = import_jobs.current_import_job("tenant_users", scope_id=1)
        self.assertEqual(current["id"], job["id"])
        self.assertEqual(current["status"], "failed")
        self.assertEqual(current["error"], "导入模板表头不正确")


if __name__ == "__main__":
    unittest.main()
