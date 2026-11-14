"""
SafeMeds 3D Graph Studio — Root Entrypoint for Hugging Face Spaces & Standalone Launch
Runs the FastAPI + Three.js WebGL application on 0.0.0.0:$PORT (default 7860).
"""

import os
import sys
from pathlib import Path
import uvicorn

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Hugging Face ZeroGPU runtime hook: registers a @spaces.GPU function during startup
try:
    import spaces
except ImportError:
    spaces = None

if spaces is not None:
    @spaces.GPU
    def safemeds_zerogpu_probe():
        return "SafeMeds 3D Graph Studio Ready"

# Import the ASGI application from server.app
from server.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"[SafeMeds] Launching SafeMeds 3D Graph Studio on http://0.0.0.0:{port}...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",
        log_level="info"
    )
