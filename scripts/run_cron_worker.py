from __future__ import annotations

import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL_PACKAGE_SRCS = (
    ROOT / "packages" / "python" / "ops-admin-system" / "src",
    ROOT / "packages" / "python" / "ops-admin-cron" / "src",
)

for path in (ROOT, *LOCAL_PACKAGE_SRCS):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from apscheduler.schedulers.background import BackgroundScheduler

from cron.infrastructure.commands.registry import build_default_dispatcher
from cron.infrastructure.scheduler.worker import CronWorker


def main() -> None:
    scheduler = BackgroundScheduler(timezone="UTC")
    worker = CronWorker(scheduler=scheduler, dispatcher=build_default_dispatcher(), worker_id="ops-admin-cron-worker")
    stop = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    worker.start()
    print("cron worker started")
    try:
        while not stop:
            time.sleep(1)
    finally:
        worker.shutdown()
        print("cron worker stopped")


if __name__ == "__main__":
    main()
