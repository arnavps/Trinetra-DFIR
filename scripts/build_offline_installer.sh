#!/bin/bash
# Builds single signed offline installer bundling Python runtime, ONNX weights, FFmpeg, and Qt libraries.

set -e

echo "=== UniDVR-Forensics Offline Installer Build ==="
echo "1. Checking offline environment..."
python -c "from app.security.network_watchdog import assert_offline_environment; assert_offline_environment()"

echo "2. Compiling PyO3 Rust Core binary..."
cd rust_core && cargo build --release && cd ..

echo "3. Running PyInstaller standalone packaging..."
python build/build_installer.py

echo "=== Build Complete: Standalone offline installer executable generated ==="
