"""Unit tests for JobManager and ForensicJob background worker system."""

import time
import pytest
from PySide6.QtWidgets import QApplication

from app.engine9_ui.job_manager import JobManager, ForensicJob, JobStatus


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_job_manager_singleton(qapp):
    jm1 = JobManager.instance()
    jm2 = JobManager.instance()
    assert jm1 is jm2


def test_job_manager_success_execution(qapp):
    jm = JobManager.instance()
    results = []

    def sample_task(progress_callback=None):
        if progress_callback:
            progress_callback(50, "Halfway done")
        return {"result": 42}

    def on_success(res):
        results.append(res)

    job = jm.submit_job(
        job_type="TEST_SUCCESS",
        description="Test execution success",
        task_fn=sample_task,
        on_success=on_success,
    )

    assert job.status in [JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.COMPLETED]
    assert job in jm.jobs

    # Wait for background thread and queued signal to complete
    timeout = 5.0
    start = time.time()
    while (job.status != JobStatus.COMPLETED or len(results) == 0) and time.time() - start < timeout:
        qapp.processEvents()
        time.sleep(0.05)
    for _ in range(5):
        qapp.processEvents()

    assert job.status == JobStatus.COMPLETED
    assert job.progress == 100
    assert len(results) == 1
    assert results[0] == {"result": 42}


def test_job_manager_error_handling(qapp):
    jm = JobManager.instance()
    errors = []

    def failing_task():
        raise ValueError("Simulated catastrophic task failure")

    def on_error(err):
        errors.append(err)

    job = jm.submit_job(
        job_type="TEST_FAIL",
        description="Test execution failure",
        task_fn=failing_task,
        on_error=on_error,
    )

    timeout = 5.0
    start = time.time()
    while (job.status != JobStatus.FAILED or len(errors) == 0) and time.time() - start < timeout:
        qapp.processEvents()
        time.sleep(0.05)
    for _ in range(5):
        qapp.processEvents()

    assert job.status == JobStatus.FAILED
    assert "Simulated catastrophic task failure" in job.error_message
    assert len(errors) == 1
    assert "Simulated catastrophic task failure" in errors[0]


def test_job_manager_cancellation(qapp):
    jm = JobManager.instance()

    def long_task(is_cancelled=None):
        while is_cancelled is None or not is_cancelled():
            time.sleep(0.02)
        return "cancelled"

    job = jm.submit_job(
        job_type="TEST_CANCEL",
        description="Test cancellation",
        task_fn=long_task,
    )

    time.sleep(0.05)
    job.cancel()
    assert job.is_cancelled() is True
    assert job.status == JobStatus.CANCELLED
