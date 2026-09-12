"""Unit tests for engine8_ai/model_registry.py verification & fail-closed session loading."""

import os
import pytest
from app.engine8_ai import model_registry


def test_verify_all_models_returns_report():
    report = model_registry.verify_all_models()
    assert isinstance(report, dict)
    assert len(report) >= 8
    for model_name, info in report.items():
        assert "status" in info
        assert "description" in info


def test_load_onnx_session_fails_closed_on_missing_file():
    with pytest.raises((FileNotFoundError, RuntimeError)):
        model_registry.load_onnx_session("non_existent_model.onnx")


def test_load_onnx_session_fails_closed_on_placeholder_status(tmp_path):
    fake_model = tmp_path / "yolov8n.onnx"
    fake_model.write_bytes(b"corrupted or fake weight data")

    # manifest specifies sha256_status: PLACEHOLDER_NOT_YET_SOURCED
    with pytest.raises(RuntimeError) as exc_info:
        model_registry.load_onnx_session("yolov8n.onnx", custom_path=str(fake_model))

    assert "Checksum verification failed" in str(exc_info.value)
