"""Background playbook scheduler using APScheduler."""

import threading
from typing import Callable, Optional

from classes import ConfigurationManager, Log


class PlaybookScheduler:
    """Schedule recurring playbook runs in a background thread."""

    def __init__(self, config_mgr: Optional[ConfigurationManager] = None, max_concurrent: int = 4):
        self.log = Log.get_instance()
        self.config_mgr = config_mgr or ConfigurationManager()
        self.playbook_mgr = self.config_mgr.playbook_mgr
        self._scheduler = None
        self._lock = threading.Lock()
        self._run_slots = threading.BoundedSemaphore(max(int(max_concurrent), 1))

    def _guarded_launch(self, playbook_name: str, once: bool, initial_shared_data=None):
        """Run a playbook respecting the concurrency cap and per-playbook mutex."""
        if not self._run_slots.acquire(blocking=False):
            self.log.warning(
                f"Skipping scheduled run of '{playbook_name}': concurrency limit reached."
            )
            return
        try:
            if self.playbook_mgr.playbooks_data.get(playbook_name, {}).get('is_running'):
                self.log.info(
                    f"Skipping scheduled run of '{playbook_name}': already running."
                )
                return
            self.playbook_mgr.launch_playbook(
                playbook_name,
                self.config_mgr,
                once=once,
                skip_validation=False,
                initial_shared_data=initial_shared_data,
            )
        except Exception as exc:
            self.log.error(f"Scheduled playbook '{playbook_name}' failed: {exc}")
        finally:
            self._run_slots.release()

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
            self._guarded_launch(playbook_name, once)

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
            self._guarded_launch(playbook_name, once)

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

    def schedule_condition(
        self,
        playbook_name: str,
        sensor_id: str,
        when: str,
        poll_seconds: int = 300,
        once: bool = True,
        job_id: Optional[str] = None,
    ):
        """Continuously poll a sensor; launch the playbook when `when` is true.

        This is the 24/7 watch pattern: the job runs forever at low cost and
        only fires the playbook when the environmental condition is met, e.g.
        schedule_condition('contain_beacon', 'beacon_detector',
                           'beacon_score >= 0.8 and duration_hours >= 2').
        """
        from sensors.conditions import evaluate_metric_expression
        from sensors.registry import SensorRegistry

        scheduler = self._ensure_scheduler()
        job_id = job_id or f"condition-{sensor_id}-{playbook_name}"

        def _check():
            sensor = SensorRegistry.get_instance().get(sensor_id)
            if sensor is None:
                self.log.error(f"Sensor '{sensor_id}' not registered; skipping check.")
                return
            reading = sensor.poll()
            if not evaluate_metric_expression(when, reading.metrics):
                return
            self.log.info(
                f"Sensor '{sensor_id}' condition met ({when}); launching '{playbook_name}'."
            )
            seed = {'sensor_metrics': {sensor_id: reading.metrics}}
            if reading.observables:
                from core.observables import wrap_shared_data

                ctx = wrap_shared_data(seed)
                for item in reading.observables:
                    ctx.add_observable(
                        item.get('type', 'generic'),
                        str(item.get('value', '')),
                        source=f'sensor:{sensor_id}',
                    )
            self._guarded_launch(playbook_name, once, initial_shared_data=seed)

        scheduler.add_job(
            _check,
            'interval',
            seconds=max(int(poll_seconds), 1),
            id=job_id,
            replace_existing=True,
        )
        self.log.info(
            f"Watching sensor '{sensor_id}' every {poll_seconds}s to launch '{playbook_name}' when: {when}"
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
