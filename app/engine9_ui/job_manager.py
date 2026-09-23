"""Unified Forensic Job Manager and Background Worker Pool for Tri-Netra.

MANDATORY THREADING INVARIANT:
No file I/O or CPU-bound work over ~100ms may run on the Qt main thread.
All long-running tasks (disk acquisition, OEM detection, VFS parsing, carving,
AI model inference, clip extraction, and reports) MUST execute through JobManager.
"""

import uuid
from datetime import datetime, timezone
from typing import Callable, Optional, List, Dict, Any

from PySide6.QtCore import QObject, QThread, Signal, Qt


class JobStatus:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ForensicJob(QObject):
    """Represents a discrete, observable unit of forensic background work."""

    status_changed = Signal(str)
    progress_changed = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        job_id: str,
        job_type: str,
        description: str,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.job_id = job_id
        self.job_type = job_type
        self.description = description
        self.status = JobStatus.QUEUED
        self.progress = 0
        self.status_message = "Queued"
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None
        self.error_message: Optional[str] = None
        self.result: Any = None
        self._is_cancelled = False

    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def cancel(self):
        self._is_cancelled = True
        self.status = JobStatus.CANCELLED
        self.status_message = "Cancelled by investigator"
        self.end_time = datetime.now(timezone.utc).isoformat()
        self.status_changed.emit(self.status)


class JobWorker(QThread):
    """Executes a forensic task function on a dedicated QThread."""

    def __init__(
        self,
        job: ForensicJob,
        task_fn: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.job = job
        self.task_fn = task_fn
        self.args = args
        self.kwargs = kwargs or {}

    def run(self):
        self.job.status = JobStatus.RUNNING
        self.job.start_time = datetime.now(timezone.utc).isoformat()
        self.job.status_message = "Running..."
        self.job.status_changed.emit(self.job.status)

        def progress_callback(percent: int, message: str = ""):
            if not self.job.is_cancelled():
                self.job.progress = max(0, min(100, int(percent)))
                if message:
                    self.job.status_message = message
                self.job.progress_changed.emit(self.job.progress, self.job.status_message)

        # Inject progress_callback and is_cancelled into kwargs if task accepts them
        task_kwargs = dict(self.kwargs)
        import inspect
        sig = inspect.signature(self.task_fn)
        if "progress_callback" in sig.parameters:
            task_kwargs["progress_callback"] = progress_callback
        if "is_cancelled" in sig.parameters:
            task_kwargs["is_cancelled"] = self.job.is_cancelled

        try:
            res = self.task_fn(*self.args, **task_kwargs)
            if not self.job.is_cancelled():
                self.job.result = res
                self.job.status = JobStatus.COMPLETED
                self.job.progress = 100
                self.job.status_message = "Completed"
                self.job.end_time = datetime.now(timezone.utc).isoformat()
                self.job.status_changed.emit(self.job.status)
                self.job.finished.emit(res)
        except Exception as e:
            if not self.job.is_cancelled():
                self.job.status = JobStatus.FAILED
                self.job.error_message = str(e)
                self.job.status_message = f"Failed: {e}"
                self.job.end_time = datetime.now(timezone.utc).isoformat()
                self.job.status_changed.emit(self.job.status)
                self.job.failed.emit(str(e))


class JobManager(QObject):
    """
    Central queue and worker orchestrator for all background forensic operations.
    Maintains complete provenance of running and historical jobs.
    """

    job_added = Signal(object)    # ForensicJob
    job_updated = Signal(object)  # ForensicJob

    _instance: Optional["JobManager"] = None

    @classmethod
    def instance(cls) -> "JobManager":
        if cls._instance is None:
            cls._instance = JobManager()
        return cls._instance

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.jobs: List[ForensicJob] = []
        self._workers: Dict[str, JobWorker] = {}

    def submit_job(
        self,
        job_type: str,
        description: str,
        task_fn: Callable,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_progress: Optional[Callable[[int, str], None]] = None,
        *args,
        **kwargs,
    ) -> ForensicJob:
        """
        Submits and starts a background forensic task.
        Returns the observable ForensicJob instance.
        """
        job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
        job = ForensicJob(job_id, job_type, description, parent=self)
        self.jobs.append(job)

        if on_success:
            job.finished.connect(on_success)
        if on_error:
            job.failed.connect(on_error)
        if on_progress:
            job.progress_changed.connect(on_progress)

        job.status_changed.connect(lambda _: self.job_updated.emit(job))
        job.progress_changed.connect(lambda _p, _m: self.job_updated.emit(job))

        worker = JobWorker(job, task_fn, args=args, kwargs=kwargs, parent=self)
        self._workers[job_id] = worker

        def _cleanup():
            if job_id in self._workers:
                worker.deleteLater()
                del self._workers[job_id]

        worker.finished.connect(_cleanup)
        self.job_added.emit(job)
        worker.start()

        return job

    def get_all_jobs(self) -> List[ForensicJob]:
        return list(self.jobs)

    def get_active_jobs(self) -> List[ForensicJob]:
        return [j for j in self.jobs if j.status in (JobStatus.QUEUED, JobStatus.RUNNING)]

    def cancel_job(self, job_id: str):
        for j in self.jobs:
            if j.job_id == job_id:
                j.cancel()
                break


def get_job_manager() -> JobManager:
    return JobManager.instance()
