#!/usr/bin/env bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "==============================================================================="
echo "  TRI-NETRA DFIR -- PORTABLE COURT EVIDENCE VIEWER (STANDALONE)"
echo "  Original Stream Playback -- In-Memory Bitstream Decoding -- Zero Re-Encoding"
echo "==============================================================================="
echo ""

if command -v python3 &> /dev/null; then
    python3 trinetra_viewer.py "$@"
elif command -v python &> /dev/null; then
    python trinetra_viewer.py "$@"
else
    echo "[ERROR] Python 3 not found. Please install Python 3 and dependencies in requirements.txt"
    exit 1
fi
