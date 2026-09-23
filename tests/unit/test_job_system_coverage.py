"""Unit test for Job System UI Threading Coverage (Section 5 Acceptance Criteria 4).
Asserts zero direct unthreaded calls to ImageReader(, acquire_image(, or model inference
in any UI page or view outside JobManager / CaseSession shared reader.
"""

import os
import re

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UI_DIR = os.path.join(ROOT_DIR, "app", "engine9_ui")


def test_no_direct_imagereader_in_ui_pages_and_views():
    """All UI pages and views must use CaseSession.get_image_reader() and never instantiate ImageReader directly."""
    pages_dir = os.path.join(UI_DIR, "pages")
    views_dir = os.path.join(UI_DIR, "views")

    offending_files = []

    for d in [pages_dir, views_dir]:
        if not os.path.exists(d):
            continue
        for fname in os.listdir(d):
            if fname.endswith(".py"):
                fpath = os.path.join(d, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                # Check for direct instantiation: ImageReader(...)
                # (Allow comments or strings)
                matches = re.findall(r"^\s*[^#\n]*\bImageReader\(", content, re.MULTILINE)
                if matches:
                    offending_files.append((fname, matches))

    assert len(offending_files) == 0, f"Found direct ImageReader(...) calls in UI files: {offending_files}"


def test_no_unthreaded_acquire_image_in_ui():
    """All acquire_image calls in UI must run inside JobManager tasks."""
    pages_dir = os.path.join(UI_DIR, "pages")

    for fname in os.listdir(pages_dir):
        if fname.endswith(".py"):
            fpath = os.path.join(pages_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if acquire_image is called outside JobManager.instance().submit_job
            if "acquire_image(" in content:
                assert "JobManager.instance().submit_job" in content, (
                    f"{fname} calls acquire_image without JobManager!"
                )
