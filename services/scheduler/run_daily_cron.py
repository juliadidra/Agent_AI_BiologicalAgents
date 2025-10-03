"""Simple scheduler that runs send_daily_reminders.py every day at SCHEDULE_TIME (HH:MM).

This runner is intentionally dependency-free beyond the Python stdlib and the project's
requirements, so it can run inside a minimal scheduler container and call the existing
send_daily_reminders module.

Environment variables:
 - SCHEDULE_TIME: time of day in HH:MM (24h) to run the job. Default: 09:00
 - TZ: timezone name (optional). If provided, the container should have correct timezone.
"""
import os
import sys
import time
import logging
from datetime import datetime, date, timedelta
import signal

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def parse_schedule_time(s: str):
    try:
        parts = s.split(":")
        if len(parts) != 2:
            raise ValueError()
        h = int(parts[0])
        m = int(parts[1])
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError()
        return h, m
    except Exception:
        raise ValueError("SCHEDULE_TIME must be in HH:MM 24-hour format")


running = True


def handle_sigterm(signum, frame):
    global running
    logger.info("Received termination signal, shutting down scheduler")
    running = False


def seconds_until_next_run(hour: int, minute: int) -> int:
    now = datetime.now()
    today_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if today_run > now:
        delta = today_run - now
    else:
        delta = (today_run + timedelta(days=1)) - now
    return int(delta.total_seconds())


def run_job_once():
    # import and run the existing script as a module
    logger.info("Running send_daily_reminders job")
    try:
        # Ensure the services package is on path and run the module as script
        script_path = os.path.join(os.path.dirname(__file__), "send_daily_reminders.py")
        # Fallback: call as module via runpy if available
        import runpy

        target = os.path.join(os.getcwd(), "services", "scheduler", "send_daily_reminders.py")
        if os.path.exists(target):
            runpy.run_path(target, run_name="__main__")
        else:
            # Try the top-level path
            runpy.run_path(script_path, run_name="__main__")
        logger.info("Job finished")
    except Exception:
        logger.exception("send_daily_reminders failed")


def main():
    # If SCHEDULE_INTERVAL_MINUTES is provided and valid, use interval mode (run immediately then every N minutes)
    interval_env = os.environ.get("SCHEDULE_INTERVAL_MINUTES")
    schedule_time = os.environ.get("SCHEDULE_TIME", "09:00")

    interval_minutes = None
    if interval_env:
        try:
            interval_minutes = int(interval_env)
            if interval_minutes <= 0:
                raise ValueError()
        except Exception:
            logger.error("SCHEDULE_INTERVAL_MINUTES must be a positive integer; ignoring")
            interval_minutes = None

    if interval_minutes is None:
        try:
            hour, minute = parse_schedule_time(schedule_time)
        except ValueError as e:
            logger.error(str(e) + "; using default 09:00")
            hour, minute = 9, 0

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    if interval_minutes:
        logger.info("Scheduler started in INTERVAL mode, running immediately and then every %d minutes", interval_minutes)
        # Run immediately, then sleep interval in a loop
        while running:
            try:
                run_job_once()
            except Exception:
                logger.exception("Unhandled exception while running job")

            slept = 0
            secs = interval_minutes * 60
            while running and slept < secs:
                to_sleep = min(60, secs - slept)
                time.sleep(to_sleep)
                slept += to_sleep

    else:
        logger.info("Scheduler started, will run daily at %02d:%02d", hour, minute)

        while running:
            secs = seconds_until_next_run(hour, minute)
            # If secs is large, sleep in smaller increments to respond to signals
            logger.info("Sleeping %d seconds until next run", secs)
            slept = 0
            while running and slept < secs:
                to_sleep = min(60, secs - slept)
                time.sleep(to_sleep)
                slept += to_sleep

            if not running:
                break

            # Run the job
            try:
                run_job_once()
            except Exception:
                logger.exception("Unhandled exception while running job")

            # short pause before scheduling next run
            time.sleep(1)


if __name__ == "__main__":
    main()
