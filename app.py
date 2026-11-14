"""
SafeMeds 3D Graph Studio — Hugging Face ZeroGPU & Standalone Entrypoint
Launches via gradio.Blocks.launch() to trigger ZeroGPU @spaces.GPU detection
while serving the full SafeMeds FastAPI + Three.js WebGL application directly
at `/`, `/api/*`, and `/static/*`.
"""

import os
import sys
import inspect
from pathlib import Path

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# 1. STRICT IMPORT ORDER: spaces first, then gradio, then server.app
try:
    import spaces
except ImportError:
    spaces = None

try:
    import gradio as gr
except ImportError:
    gr = None

print(f"[SafeMeds] Runtime check -> spaces={spaces is not None}, gradio={gr is not None}", flush=True)

import uvicorn
from server.app import app as safemeds_app

# 2. REGISTER REAL @spaces.GPU HANDLER FOR ZEROGPU STARTUP DETECTION
if spaces is not None:
    @spaces.GPU
    def safemeds_gpu_heartbeat(query: str = "SafeMeds 3D") -> str:
        """Hugging Face ZeroGPU heartbeat function."""
        return f"SafeMeds 3D Graph Studio ZeroGPU Active: {query}"
else:
    def safemeds_gpu_heartbeat(query: str = "SafeMeds 3D") -> str:
        return f"SafeMeds 3D Graph Studio Local: {query}"

# 3. BUILD GRADIO BLOCKS CONTAINER WITH ACTIVE @spaces.GPU EVENT
demo = None
if gr is not None:
    with gr.Blocks(title="SafeMeds 3D Graph Studio") as demo:
        # Invisible UI components registering real @spaces.GPU function in demo.fns
        _inp = gr.Textbox(value="SafeMeds 3D", visible=False)
        _out = gr.Textbox(visible=False)
        _btn = gr.Button("ZeroGPU Heartbeat", visible=False)
        _btn.click(fn=safemeds_gpu_heartbeat, inputs=_inp, outputs=_out)

# 4. ENTRYPOINT: LAUNCH VIA demo.launch() AND PREPEND SAFEMEDS FASTAPI ROUTES
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))

    if gr is not None and demo is not None:
        print(f"[SafeMeds] Launching via Gradio Blocks.launch() for ZeroGPU on port {port}...")

        # Check if ssr_mode is accepted in Gradio 5 to prevent Node.js SSR proxying
        launch_kwargs = {}
        sig_params = inspect.signature(demo.launch).parameters
        if "ssr_mode" in sig_params:
            launch_kwargs["ssr_mode"] = False

        # Launch Gradio server without blocking immediately so we can inject routes
        gr_app, local_url, share_url = demo.launch(
            server_name="0.0.0.0",
            server_port=port,
            prevent_thread_lock=True,
            **launch_kwargs
        )

        # Filter out Gradio's default '/' route so SafeMeds HTML dashboard takes precedence
        gr_app.router.routes = [r for r in gr_app.router.routes if getattr(r, "path", None) != "/"]

        # Prepend SafeMeds routes to the front of Gradio's router
        # This routes `/`, `/api/*`, and `/static/*` directly to SafeMeds
        # while keeping Gradio's internal `/config`, `/gradio_api/*`, and ZeroGPU hooks intact
        safemeds_routes = [
            r for r in safemeds_app.router.routes
            if getattr(r, "path", "").startswith("/api")
            or getattr(r, "path", "").startswith("/static")
            or getattr(r, "path", "") == "/"
        ]
        gr_app.router.routes[:0] = safemeds_routes

        print(f"[SafeMeds] Successfully prepended {len(safemeds_routes)} SafeMeds routes to Gradio router.")
        print(f"[SafeMeds] SafeMeds 3D Graph Studio live at http://0.0.0.0:{port}")

        # Keep server thread alive
        demo.block_thread()

    else:
        # Fallback for environments where Gradio is not installed
        print(f"[SafeMeds] Gradio not found. Falling back to direct Uvicorn on port {port}...")
        uvicorn.run(
            safemeds_app,
            host="0.0.0.0",
            port=port,
            proxy_headers=True,
            forwarded_allow_ips="*",
            log_level="info"
        )
