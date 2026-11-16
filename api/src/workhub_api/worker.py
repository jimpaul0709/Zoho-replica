"""The job worker (WH-07). Run it next to the API:  uv run python -m workhub_api.worker

It runs due jobs one after another, and sleeps a few seconds when there is nothing to do.
Stop it with Ctrl-C; it finishes the job it is on first.
"""

import logging
import signal
import threading
from types import FrameType

from sqlalchemy.orm import Session

from workhub_api.db import engine
from workhub_api.jobs import run_one
from workhub_api.routing import ensure_housekeeping  # importing routing registers its handlers

POLL_SECONDS = 5
log = logging.getLogger("workhub.worker")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    stop = threading.Event()

    def on_signal(signum: int, frame: FrameType | None) -> None:
        stop.set()

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    log.info("worker started, polling every %s s", POLL_SECONDS)
    while not stop.is_set():
        try:
            with Session(engine) as session:
                ran = run_one(session)
                if not ran:
                    ensure_housekeeping(session)  # keeps the repeating job alive
                    session.commit()
        except Exception:  # e.g. the database is briefly unreachable: log it and carry on
            log.exception("worker loop error")
            ran = False
        if not ran:
            stop.wait(POLL_SECONDS)
    log.info("worker stopped")


if __name__ == "__main__":
    main()
