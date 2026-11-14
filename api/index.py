"""
SafeMeds 3D Graph Studio — Vercel Serverless Entrypoint
Imports the FastAPI application from `server.app`.
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so `server` package is importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server.app import app  # ASGI app exposed for Vercel
