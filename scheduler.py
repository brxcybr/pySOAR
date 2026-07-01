"""Background playbook scheduler using APScheduler."""

import threading
from typing import Callable, Optional

from classes import ConfigurationManager, Log


class PlaybookScheduler:
    """Schedule recurring playbook runs in a background thread."""

    def __init__(self, config_mgr: Optional[ConfigurationManager] = None):
        self.log = Log.get_instance()
        self.config_mgr = config_mgr or ConfigurationManager()
        self.playbook_mgr = self.config_mgr.playbook_mgr
        self._scheduler = None
        self._lock = threading.Lock()

    def _ensure_scheduler(self):
        if self._scheduler is None:
            from apscheduler.schedulers.background import BackgroundScheduler

            self._scheduler = BackgroundScheduler()
        return self._scheduler

    def schedule_interval(
        self,
        playbook_name: str,
        seconds: int,
        once: bool = False,
        job_id: Optional[str] = None,
    ):
        """Run a playbook every `seconds` until stopped."""
        scheduler = self._ensure_scheduler()
        job_id = job_id or f"playbook-{playbook_name}"

        def _run():
            self.log.info(f"Scheduler triggering playbook '{playbook_name}'")
            try:
                self.playbook_mgr.launch_playbook(
                    playbook_name,
                    self.config_mgr,
                    once=once,
                    skip_validation=False,
                )
            except Exception as exc:
                self.log.error(f"Scheduled playbook '{playbook_name}' failed: {exc}")

        scheduler.add_job(
            _run,
            'interval',
            seconds=max(int(seconds), 1),
            id=job_id,
            replace_existing=True,
        )
        self.log.info(
            f"Scheduled playbook '{playbook_name}' every {seconds}s (once={once})"
        )
        return job_id

    def schedule_cron(
        self,
        playbook_name: str,
        cron_expr: str,
        once: bool = False,
        job_id: Optional[str] = None,
    ):
        """Schedule with a cron expression (minute hour day month day_of_week)."""
        scheduler = self._ensure_scheduler()
        job_id = job_id or f"playbook-{playbook_name}"
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError('Cron expression must have 5 fields')

        def _run():
            self.playbook_mgr.launch_playbook(
                playbook_name,
                self.config_mgr,
                once=once,
            )

        minute, hour, day, month, day_of_week = parts
        scheduler.add_job(
            _run,
            'cron',
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            id=job_id,
            replace_existing=True,
        )
        return job_id

    def start(self):
        scheduler = self._ensure_scheduler()
        if not scheduler.running:
            scheduler.start()
            self.log.info('Playbook scheduler started.')

    def stop(self, wait: bool = True):
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            self.log.info('Playbook scheduler stopped.')

    def list_jobs(self):
        if not self._scheduler:
            return []
        return [
            {
                'id': job.id,
                'next_run': str(job.next_run_time),
                'trigger': str(job.trigger),
            }
            for job in self._scheduler.get_jobs()
        ]

    def run_forever(self, on_signal: Optional[Callable] = None):
        """Start scheduler and block until KeyboardInterrupt."""
        import signal
        import time

        self.start()

        def _shutdown(signum, frame):
            self.log.info('Shutdown signal received.')
            self.stop()
            if on_signal:
                on_signal(signum, frame)
            raise SystemExit(0)

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
        while True:
            time.sleep(1)
