"""
Automated PyInstaller build script bundling Python runtime, ONNX weights, FFmpeg, and PySide6 UI.
"""

import os
import subprocess
import sys


def build_installer():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    spec_file = os.path.join(root_dir, "build", "pyinstaller.spec")
    
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        spec_file
    ]

    print(f"Building standalone offline executable using PyInstaller: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=root_dir)
    return res.returncode


if __name__ == "__main__":
    sys.exit(build_installer())
