import psutil
import threading
import time
import logging
from src.i18n_manager import _

logger = logging.getLogger("gk-healter.health")


class HealthEngine:
    def __init__(self):
        self._cpu_usage = 0.0
        self._ram_usage = 0.0
        self._disk_usage = 0.0
        self._health_score = 100
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        # Detailed resource info
        self._ram_total: int = 0
        self._ram_used: int = 0
        self._disk_total: int = 0
        self._disk_used: int = 0
        self._cpu_count: int = psutil.cpu_count(logical=True) or 1
        self._cpu_freq_max: float = 0.0
        try:
            freq = psutil.cpu_freq()
            if freq:
                self._cpu_freq_max = freq.max or freq.current or 0.0
        except Exception:
            pass

    def start_monitoring(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop_monitoring(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _monitor_loop(self):
        while self._running:
            try:
                # psutil.cpu_percent(interval=1) blocks for 1 second, so we don't need explicit sleep
                # But to make ui responsive and not block stop_monitoring check for 1s, we can use smaller interval or just accept it.
                # using 0.5s interval
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                dsk = psutil.disk_usage('/')

                with self._lock:
                    self._cpu_usage = cpu
                    self._ram_usage = mem.percent
                    self._ram_total = mem.total
                    self._ram_used = mem.used
                    self._disk_usage = dsk.percent
                    self._disk_total = dsk.total
                    self._disk_used = dsk.used
                    self._calculate_score()

            except Exception as e:
                logger.error("Error in health monitoring: %s", e)
                time.sleep(1)

    def _calculate_score(self):
        # Simple weighted score:
        # High resource usage reduces the score.
        # Base 100

        penalty = 0

        # CPU Penalties
        if self._cpu_usage > 90:
            penalty += 20
        elif self._cpu_usage > 70:
            penalty += 10

        # RAM Penalties
        if self._ram_usage > 90:
            penalty += 20
        elif self._ram_usage > 80:
            penalty += 10

        # Disk Penalties
        if self._disk_usage > 90:
            penalty += 20
        elif self._disk_usage > 80:
            penalty += 10

        self._health_score = max(0, 100 - penalty)

    def get_metrics(self):
        with self._lock:
            return {
                'cpu': self._cpu_usage,
                'ram': self._ram_usage,
                'disk': self._disk_usage,
                'score': self._health_score,
                'ram_total': self._ram_total,
                'ram_used': self._ram_used,
                'disk_total': self._disk_total,
                'disk_used': self._disk_used,
                'cpu_count': self._cpu_count,
                'cpu_freq_max': self._cpu_freq_max,
            }

    def get_detailed_status(self):
        with self._lock:
            # Return a status string based on the score
            if self._health_score >= 90:
                return _("health_status_excellent")
            elif self._health_score >= 70:
                return _("health_status_good")
            elif self._health_score >= 50:
                return _("health_status_fair")
            else:
                return _("health_status_critical")
