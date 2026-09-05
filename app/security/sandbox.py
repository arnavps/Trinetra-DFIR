"""
Subprocess isolation wrapper for parser/carver/decoder engines (Blueprint §6).
Wraps BOTH filesystem parser/carver invocations AND decoder.py video decoding
in an isolated, restricted-privilege subprocess to protect against malformed data.
"""

import sys
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional, Tuple


class SandboxError(Exception):
    """Base sandbox execution error."""
    pass


class MalformedDataError(SandboxError):
    """Raised when malformed header or video stream is safely intercepted by sandbox."""
    pass


class SandboxRunner:
    """Subprocess isolation wrapper for untrusted byte parsing and decoding."""

    def __init__(self, timeout_sec: int = 10):
        self.timeout_sec = timeout_sec

    def run_parser_in_sandbox(self, parser_class_name: str, image_path: str) -> Dict[str, Any]:
        """
        Invokes filesystem parser inside an isolated subprocess.
        Safely catches malformed filesystem headers without crashing the main app.
        """
        cmd = [
            sys.executable,
            "-c",
            f"""
import sys, json
try:
    if '{parser_class_name}' == 'HikfatParser':
        from app.engine3_parsers.hikfat_parser import HikfatParser
        p = HikfatParser()
    elif '{parser_class_name}' == 'DhfsParser':
        from app.engine3_parsers.dhfs_parser import DhfsParser
        p = DhfsParser()
    else:
        from app.engine3_parsers.generic_parser import GenericParser
        p = GenericParser()

    res = p.parse(r'{image_path}')
    print(json.dumps({{'status': 'ok', 'files_count': len(res.files)}}))

except Exception as e:
    print(json.dumps({{'status': 'error', 'error': str(e)}}))
            """
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_sec)
            if res.returncode != 0:
                raise MalformedDataError(f"Subprocess terminated with code {res.returncode}: {res.stderr}")
            import json
            output = json.loads(res.stdout.strip())
            if output.get("status") == "error":
                raise MalformedDataError(output.get("error"))
            return output
        except subprocess.TimeoutExpired:
            raise SandboxError("Parser subprocess timed out.")

    def run_decoder_in_sandbox(self, stream_bytes: bytes) -> Dict[str, Any]:
        """
        Invokes decoder inside an isolated subprocess.
        Safely catches malformed video streams without crashing the main app.
        """
        with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as tmp:
            tmp.write(stream_bytes)
            tmp_path = tmp.name

        try:
            cmd = [
                sys.executable,
                "-c",
                f"""
import sys, json
try:
    with open(r'{tmp_path}', 'rb') as f:
        data = f.read()
    from app.engine5_playback.decoder import StreamDecoder
    dec = StreamDecoder(data)
    fc = dec.get_frame_count()
    print(json.dumps({{'status': 'ok', 'frame_count': fc}}))
except Exception as e:
    print(json.dumps({{'status': 'error', 'error': str(e)}}))
                """
            ]

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_sec)
            if res.returncode != 0:
                raise MalformedDataError(f"Decoder subprocess terminated with code {res.returncode}: {res.stderr}")
            import json
            output = json.loads(res.stdout.strip())
            if output.get("status") == "error":
                raise MalformedDataError(output.get("error"))
            return output
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
