"""
SafeMeds 3D Graph Studio — Automated 4K 60fps Broadcast Demo Video Generator
=============================================================================
Records live SafeMeds UI (http://127.0.0.1:8000) with Playwright WebGL acceleration,
generates neural AI voiceover with Microsoft Edge TTS, synchronizes browser interactions
with human-like virtual cursor physics, masterfully mixes broadcast audio with ducked
ambient synth pad and loudness normalization, and renders a studio 4K UHD 60fps MP4 master.

Usage:
    python scripts/generate_demo_video.py [--8k] [--skip-audio] [--skip-browser] [--headless]
"""

import sys
import os
import re
import time
import math
import shutil
import asyncio
import argparse
import subprocess
from pathlib import Path

# Third-party dependencies
import edge_tts
import numpy as np
import wave
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
AUDIO_DIR = OUTPUT_DIR / "audio"
RAW_VIDEO_DIR = OUTPUT_DIR / "raw_video"
OUTPUT_4K = OUTPUT_DIR / "SafeMeds_Demo_4K.mp4"
OUTPUT_8K = OUTPUT_DIR / "SafeMeds_Demo_8K.mp4"
SUBTITLES_SRT = OUTPUT_DIR / "SafeMeds_Demo.srt"

# 5 Exact Narration Scripts
SCENE_SCRIPTS = [
    (
        "scene_1",
        "Every year, preventable drug, food, and enzyme collisions put millions of patients at risk—"
        "because flat medication tables hide multi-hop biological pathways. "
        "Meet SafeMeds 3D Graph Studio: a clinical decision engine powered locally by a "
        "single-file Relate by Neo4j graph database, with zero cloud latency."
    ),
    (
        "scene_2",
        "Here, a heart patient taking Clopidogrel adds Omeprazole for acid reflux. "
        "Relate instantly traverses from medicines to active ingredients and uncovers a silent "
        "CYP2C19 enzyme block that neutralizes Clopidogrel's heart protection—and surfaces a safer "
        "alternative in real time."
    ),
    (
        "scene_3",
        "With a single click on Apply Safe Swap, SafeMeds updates the regimen, re-queries the embedded "
        "Relate store, clears the enzyme collision in 3D, and verifies all pathways are safe—"
        "with full one-click undo for side-by-side clinical comparison."
    ),
    (
        "scene_4",
        "Now let's scale to complex polypharmacy: Atorvastatin, Warfarin, Grapefruit Juice, Leafy Greens, "
        "and Bleeding Risk. When we ask the local SafeMeds Graph Agent, 'Why do I have muscle pain?', "
        "it executes a deterministic Cypher traversal in under nine milliseconds—pinpointing how "
        "Grapefruit Juice inhibits CYP3A4 to amplify Statin myopathy, with full Cypher transparency."
    ),
    (
        "scene_5",
        "Beyond alerts, SafeMeds generates a five-slot daily spacing schedule, calculates cumulative "
        "organ burden, and protects clinical data with strict read-only Cypher guards. "
        "Everything runs out of a portable 176-kilobyte .rl file—bringing deterministic, "
        "explainable graph intelligence to bedside safety."
    )
]

INTRO_DURATION = 2.5
OUTRO_DURATION = 3.0
SCENE_BREATHING_ROOM = 0.6  # seconds between scenes for natural pacing


# ==============================================================================
# 1. FFMPEG UTILITIES
# ==============================================================================
def get_ffmpeg_exe() -> str:
    """Finds FFmpeg executable (imageio-ffmpeg or system PATH)."""
    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    which = shutil.which("ffmpeg")
    if which:
        return which
    default_bin = Path("C:/Users/WALTON/.gemini/antigravity/bin/ffmpeg.exe")
    if default_bin.exists():
        return str(default_bin)
    raise RuntimeError("FFmpeg executable not found.")


FFMPEG = get_ffmpeg_exe()


def run_ffmpeg(args: list, check: bool = True):
    """Executes FFmpeg with consistent logging."""
    cmd = [FFMPEG] + args
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="ignore")
    if check and res.returncode != 0:
        print(f"[FFMPEG ERROR] Command failed: {' '.join(str(c) for c in cmd[:12])}...")
        print(res.stderr[-1000:])
        raise RuntimeError(f"FFmpeg failed with exit code {res.returncode}")
    return res


def get_media_duration(file_path: Path) -> float:
    """Parses media duration using FFmpeg."""
    cmd = [FFMPEG, "-i", str(file_path)]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="ignore")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", p.stderr)
    if m:
        h, mn, s = m.groups()
        return int(h) * 3600 + int(mn) * 60 + float(s)
    return 0.0


# ==============================================================================
# 2. LOCAL SERVER HEALTH VERIFICATION
# ==============================================================================
def ensure_local_server():
    """Verifies that http://127.0.0.1:8000/api/health is online."""
    import requests
    print("[1/8] Verifying local SafeMeds server status...")
    try:
        r = requests.get("http://127.0.0.1:8000/api/health", timeout=2)
        if r.status_code == 200:
            print("  ✓ Local SafeMeds server is online and healthy.")
            return None
    except Exception:
        pass

    print("  ! SafeMeds server not detected on 8000. Launching background server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    for _ in range(30):
        time.sleep(0.5)
        try:
            r = requests.get("http://127.0.0.1:8000/api/health", timeout=1)
            if r.status_code == 200:
                print("  ✓ Server successfully launched.")
                return proc
        except Exception:
            continue
    raise RuntimeError("Failed to connect to local SafeMeds server at http://127.0.0.1:8000")


# ==============================================================================
# 3. NEURAL VOICEOVER GENERATION (edge-tts)
# ==============================================================================
async def _generate_single_voiceover(scene_name: str, text: str, output_path: Path):
    """Generates a single scene neural voiceover clip with fallback."""
    voices_to_try = ["en-US-BrianNeural", "en-US-AndrewNeural", "en-US-ChristopherNeural"]
    for v in voices_to_try:
        try:
            communicate = edge_tts.Communicate(text, v, rate="-4%")
            await communicate.save(str(output_path))
            if output_path.exists() and output_path.stat().st_size > 1000:
                return v
        except Exception as e:
            print(f"    Voice {v} failed ({e}), trying next voice...")
            continue
    raise RuntimeError(f"Failed to generate neural voiceover for {scene_name}")


def generate_voiceovers(skip: bool = False) -> dict:
    """Generates all 5 scene voiceover clips and records exact durations."""
    print("[2/8] Generating studio neural voiceovers (edge-tts)...")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    durations = {}

    for name, text in SCENE_SCRIPTS:
        clip_path = AUDIO_DIR / f"{name}.mp3"
        if skip and clip_path.exists() and clip_path.stat().st_size > 1000:
            dur = get_media_duration(clip_path)
            durations[name] = dur
            print(f"  ✓ Reusing existing {name}.mp3 ({dur:.2f}s)")
            continue

        print(f"  • Generating {name}.mp3...")
        voice_used = asyncio.run(_generate_single_voiceover(name, text, clip_path))
        dur = get_media_duration(clip_path)
        durations[name] = dur
        print(f"    ✓ {name}.mp3 generated [{voice_used}] — Duration: {dur:.2f}s")

    total_speech = sum(durations.values())
    print(f"  ✓ All 5 scenes synthesized. Total narration time: {total_speech:.2f}s")
    return durations


# ==============================================================================
# 4. INTRO & OUTRO CARD RENDERING (Pillow + FFmpeg)
# ==============================================================================
def create_gradient_canvas(width: int, height: int, top_color: tuple, bottom_color: tuple) -> Image.Image:
    """Creates a smooth vertical gradient canvas."""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img


def generate_title_cards():
    """Generates 4K Intro & Outro title cards."""
    print("[3/8] Rendering broadcast 4K Intro & Outro title cards...")
    W, H = 3840, 2160
    font_bold_path = "C:/Windows/Fonts/segoeuib.ttf" if os.path.exists("C:/Windows/Fonts/segoeuib.ttf") else "C:/Windows/Fonts/arialbd.ttf"
    font_reg_path = "C:/Windows/Fonts/segoeui.ttf" if os.path.exists("C:/Windows/Fonts/segoeui.ttf") else "C:/Windows/Fonts/arial.ttf"

    font_title = ImageFont.truetype(font_bold_path, 115)
    font_sub = ImageFont.truetype(font_reg_path, 54)
    font_badge = ImageFont.truetype(font_bold_path, 40)
    font_small = ImageFont.truetype(font_reg_path, 38)

    # 1. Intro Card
    intro_img = create_gradient_canvas(W, H, (11, 37, 69), (2, 132, 199))
    draw = ImageDraw.Draw(intro_img)

    # Brand Title
    draw.text((W / 2, H / 2 - 150), "SafeMeds 3D Graph Studio", font=font_title, fill=(255, 255, 255), anchor="mm")
    draw.text((W / 2, H / 2 - 20), "Powered by Relate by Neo4j • Offline-First Clinical Intelligence", font=font_sub, fill=(186, 230, 253), anchor="mm")

    # Yellow Challenge Tag Pill
    badge_text = "RELATE HACKATHON: \"CONTEXT, CONNECTED\""
    badge_w = 1100
    badge_h = 70
    badge_x = (W - badge_w) / 2
    badge_y = H / 2 + 80
    draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=35, fill=(253, 224, 71))
    draw.text((W / 2, badge_y + badge_h / 2), badge_text, font=font_badge, fill=(11, 37, 69), anchor="mm")

    # Feature Highlights
    features = "In-Process Embedded Rust Engine  •  176 KB Single-File Store  •  Zero Cloud Latency"
    draw.text((W / 2, H / 2 + 220), features, font=font_small, fill=(224, 242, 254), anchor="mm")

    intro_png = OUTPUT_DIR / "intro_card.png"
    intro_img.save(intro_png)

    # 2. Outro Card
    outro_img = create_gradient_canvas(W, H, (11, 37, 69), (16, 185, 129))
    draw_out = ImageDraw.Draw(outro_img)

    draw_out.text((W / 2, H / 2 - 160), "SafeMeds", font=font_title, fill=(255, 255, 255), anchor="mm")
    draw_out.text((W / 2, H / 2 - 30), "Portable Graph  •  Zero Cloud Latency  •  Deterministic Bedside Safety", font=font_sub, fill=(253, 224, 71), anchor="mm")

    detail = "Built with Relate by Neo4j for the \"Context, Connected\" Hackathon"
    draw_out.text((W / 2, H / 2 + 70), detail, font=font_badge, fill=(209, 250, 229), anchor="mm")

    callout = "Clinical Knowledge Graphs  •  Cypher Traversal  •  Offline-First Architecture"
    draw_out.text((W / 2, H / 2 + 160), callout, font=font_small, fill=(240, 253, 244), anchor="mm")

    outro_png = OUTPUT_DIR / "outro_card.png"
    outro_img.save(outro_png)

    # Convert to 60fps MP4 with fade transitions
    intro_mp4 = OUTPUT_DIR / "intro.mp4"
    outro_mp4 = OUTPUT_DIR / "outro.mp4"

    # Intro MP4 (2.5s with 0.5s fade-in)
    run_ffmpeg([
        "-y", "-loop", "1", "-i", str(intro_png),
        "-t", str(INTRO_DURATION),
        "-vf", "fps=60,fade=t=in:st=0:d=0.5,format=yuv420p",
        "-c:v", "libx264", "-crf", "15", "-preset", "veryfast",
        str(intro_mp4)
    ])

    # Outro MP4 (3.0s with 0.5s fade-out)
    run_ffmpeg([
        "-y", "-loop", "1", "-i", str(outro_png),
        "-t", str(OUTRO_DURATION),
        "-vf", f"fps=60,fade=t=out:st={OUTRO_DURATION - 0.5}:d=0.5,format=yuv420p",
        "-c:v", "libx264", "-crf", "15", "-preset", "veryfast",
        str(outro_mp4)
    ])

    print("  ✓ Intro and Outro 4K 60fps video clips rendered.")
    return intro_mp4, outro_mp4


# ==============================================================================
# 5. PROCEDURAL AMBIENT SYNTH PAD GENERATION (numpy + wave)
# ==============================================================================
def generate_ambient_synth_track(total_duration: float, output_path: Path):
    """Generates an ultra-subtle, copyright-free warm ambient synth pad."""
    print(f"[4/8] Synthesizing harmonic ambient synth bed ({total_duration:.1f}s)...")
    sample_rate = 48000
    n_samples = int(sample_rate * total_duration)
    t = np.linspace(0, total_duration, n_samples, endpoint=False)

    # Warm C-Major 9th chord voicing (C4, G4, B4, D5, E5)
    frequencies = [261.63, 392.00, 493.88, 587.33, 659.25]
    signal = np.zeros_like(t)

    for f in frequencies:
        # Base tone + subtle detuned unison for stereo warmth
        signal += np.sin(2 * np.pi * f * t) * 0.20
        signal += np.sin(2 * np.pi * (f + 0.45) * t) * 0.15
        signal += np.sin(2 * np.pi * (f - 0.35) * t) * 0.10

    # Slow attack (3s) and slow release (3s) envelope
    attack = np.clip(t / 3.0, 0, 1)
    release = np.clip((total_duration - t) / 3.0, 0, 1)
    envelope = attack * release

    # Gentle low-frequency modulation (swell)
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.12 * t)
    signal = signal * envelope * lfo * 0.18

    # Convert to 16-bit stereo PCM
    audio_int16 = (signal * 32767).astype(np.int16)
    stereo_data = np.column_stack((audio_int16, audio_int16)).flatten()

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(stereo_data.tobytes())

    print("  ✓ Ambient synth bed synthesized.")


# ==============================================================================
# 6. CINEMATIC BROWSER CAPTURE WITH VIRTUAL CURSOR (Playwright)
# ==============================================================================
CURSOR_INJECTION_SCRIPT = """
(() => {
  function setupCursor() {
    if (document.getElementById('virtual-cursor-layer')) return;
    if (!document.body) {
      document.addEventListener('DOMContentLoaded', setupCursor);
      return;
    }
    const style = document.createElement('style');
    style.id = 'virtual-cursor-style';
    style.innerHTML = `
      #virtual-cursor-layer {
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 9999999;
        overflow: hidden;
      }
      #cinematic-cursor {
        position: absolute;
        top: 0;
        left: 0;
        width: 26px;
        height: 26px;
        transform: translate(-3px, -3px);
        filter: drop-shadow(0 3px 10px rgba(11, 61, 145, 0.45));
        transition: transform 0.035s linear;
        will-change: transform;
      }
      .click-ripple {
        position: absolute;
        border-radius: 50%;
        border: 2px solid #38BDF8;
        background: radial-gradient(circle, rgba(56, 189, 248, 0.4) 0%, rgba(2, 132, 199, 0.0) 70%);
        transform: translate(-50%, -50%) scale(0.15);
        animation: rippleExpand 0.55s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        pointer-events: none;
      }
      @keyframes rippleExpand {
        0% { transform: translate(-50%, -50%) scale(0.15); opacity: 0.95; }
        100% { transform: translate(-50%, -50%) scale(2.4); opacity: 0; }
      }
    `;
    (document.head || document.documentElement).appendChild(style);

    const layer = document.createElement('div');
    layer.id = 'virtual-cursor-layer';
    layer.innerHTML = `
      <div id="cinematic-cursor">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
          <path d="M4 3L11.5 21.5L14.5 14L21.5 11L4 3Z" fill="#38BDF8" stroke="#FFFFFF" stroke-width="2.2" stroke-linejoin="round"/>
        </svg>
      </div>
    `;
    document.body.appendChild(layer);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupCursor);
  } else {
    setupCursor();
  }

  window.__moveCursor = (x, y) => {
    const cursorEl = document.getElementById('cinematic-cursor');
    if (cursorEl) cursorEl.style.transform = `translate(${x}px, ${y}px)`;
  };

  window.__showRipple = (x, y) => {
    const layer = document.getElementById('virtual-cursor-layer') || document.body;
    if (!layer) return;
    const r = document.createElement('div');
    r.className = 'click-ripple';
    r.style.left = `${x}px`;
    r.style.top = `${y}px`;
    r.style.width = '36px';
    r.style.height = '36px';
    layer.appendChild(r);
    setTimeout(() => r.remove(), 600);
  };
})();
"""


class VirtualCursorController:
    """Simulates smooth, organic human mouse movements with cubic Bézier easing."""
    def __init__(self, page):
        self.page = page
        self.x = 960.0
        self.y = 540.0

    def move_to(self, target_x: float, target_y: float, duration_ms: float = 650):
        start_x, start_y = self.x, self.y
        steps = max(18, int(duration_ms / 16))
        dx = target_x - start_x
        dy = target_y - start_y

        p1_x = start_x + dx * 0.35
        p1_y = start_y + dy * 0.15 + (12 if dx > 0 else -12)
        p2_x = start_x + dx * 0.75
        p2_y = start_y + dy * 0.85

        for i in range(1, steps + 1):
            t = i / steps
            cx = (1 - t)**3 * start_x + 3 * (1 - t)**2 * t * p1_x + 3 * (1 - t) * t**2 * p2_x + t**3 * target_x
            cy = (1 - t)**3 * start_y + 3 * (1 - t)**2 * t * p1_y + 3 * (1 - t) * t**2 * p2_y + t**3 * target_y
            
            try:
                self.page.evaluate("([x, y]) => { if (window.__moveCursor) window.__moveCursor(x, y); }", [cx, cy])
            except Exception:
                pass
            self.page.mouse.move(cx, cy)
            self.page.wait_for_timeout(duration_ms / steps)

        self.x = target_x
        self.y = target_y

    def click(self, target_x: float = None, target_y: float = None, move_first: bool = True):
        if target_x is not None and target_y is not None:
            if move_first:
                self.move_to(target_x, target_y)
            else:
                self.x = target_x
                self.y = target_y
                try:
                    self.page.evaluate("([x, y]) => { if (window.__moveCursor) window.__moveCursor(x, y); }", [self.x, self.y])
                except Exception:
                    pass

        try:
            self.page.evaluate("([x, y]) => { if (window.__showRipple) window.__showRipple(x, y); }", [self.x, self.y])
        except Exception:
            pass
        self.page.mouse.click(self.x, self.y)
        self.page.wait_for_timeout(80)

    def drag_orbit(self, start_x: float, start_y: float, end_x: float, end_y: float, duration_ms: float = 2000):
        self.move_to(start_x, start_y, 450)
        self.page.mouse.down()
        steps = int(duration_ms / 20)
        for i in range(1, steps + 1):
            t = i / steps
            smooth_t = t * t * (3 - 2 * t)
            cur_x = start_x + (end_x - start_x) * smooth_t
            cur_y = start_y + (end_y - start_y) * smooth_t
            try:
                self.page.evaluate("([x, y]) => { if (window.__moveCursor) window.__moveCursor(x, y); }", [cur_x, cur_y])
            except Exception:
                pass
            self.page.mouse.move(cur_x, cur_y)
            self.page.wait_for_timeout(20)
        self.page.mouse.up()
        self.x = end_x
        self.y = end_y
        self.page.wait_for_timeout(100)


def record_browser_session(scene_durations: dict, headless: bool = False, skip: bool = False) -> Path:
    """Executes high-fidelity GPU browser recording synchronized to speech durations."""
    print("[5/8] Capturing GPU-accelerated 4K browser performance...")
    RAW_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    
    existing_videos = list(RAW_VIDEO_DIR.glob("*.webm"))
    if skip and existing_videos:
        raw_path = existing_videos[0]
        print(f"  ✓ Reusing existing browser recording: {raw_path.name}")
        return raw_path

    for old in RAW_VIDEO_DIR.glob("*.webm"):
        try:
            old.unlink()
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--use-gl=angle",
                "--enable-webgl",
                "--ignore-gpu-blocklist",
                "--enable-features=Vulkan,DefaultANGLEVulkan",
                "--disable-infobars",
                "--start-maximized"
            ]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            record_video_dir=str(RAW_VIDEO_DIR),
            record_video_size={"width": 1920, "height": 1080}
        )

        page = context.new_page()
        page.add_init_script(CURSOR_INJECTION_SCRIPT)

        cursor = VirtualCursorController(page)

        print("  • Loading SafeMeds 3D Studio (http://127.0.0.1:8000)...")
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        page.wait_for_timeout(1000)
        try:
            page.evaluate(CURSOR_INJECTION_SCRIPT)
        except Exception:
            pass
        page.wait_for_timeout(500)

        # ----------------------------------------------------------------------
        # SCENE 1: The Hook & Overview (Heart + Gastric Block auto-loaded)
        # ----------------------------------------------------------------------
        s1_dur = scene_durations["scene_1"] + SCENE_BREATHING_ROOM
        print(f"  • Recording Scene 1 (The Hook) — Target duration: {s1_dur:.2f}s...")
        t_scene_start = time.perf_counter()

        # Smooth 3D orbit drag across center stage
        cursor.drag_orbit(960, 520, 1140, 470, duration_ms=2200)

        # Glide smoothly to hover over ./data/safemeds.rl store badge
        badge = page.locator(".relate-store-badge")
        if badge.count() > 0:
            box = badge.bounding_box()
            cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=900)
            page.wait_for_timeout(700)

        # Glide to key action banner
        banner = page.locator("#keyActionBanner")
        if banner.count() > 0 and banner.is_visible():
            box = banner.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=800)

        elapsed = time.perf_counter() - t_scene_start
        if s1_dur > elapsed:
            page.wait_for_timeout((s1_dur - elapsed) * 1000)

        # ----------------------------------------------------------------------
        # SCENE 2: Graph Advantage & Silent CYP2C19 Block
        # ----------------------------------------------------------------------
        s2_dur = scene_durations["scene_2"] + SCENE_BREATHING_ROOM
        print(f"  • Recording Scene 2 (Graph Advantage) — Target duration: {s2_dur:.2f}s...")
        t_scene_start = time.perf_counter()

        # Sweep across the 4 graph lanes at the top
        lanes = page.locator(".stage-lanes-header .lane-col-label").all()
        for lane in lanes:
            box = lane.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=550)
                page.wait_for_timeout(350)

        # Glide to right panel red conflict alert card
        conflict_card = page.locator(".alert-card-item").first
        if conflict_card.count() > 0:
            box = conflict_card.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=750)
                page.wait_for_timeout(700)

        # Hover safe alternative recommendation card
        safe_card = page.locator(".safe-card-item").first
        if safe_card.count() > 0:
            box = safe_card.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=700)

        elapsed = time.perf_counter() - t_scene_start
        if s2_dur > elapsed:
            page.wait_for_timeout((s2_dur - elapsed) * 1000)

        # ----------------------------------------------------------------------
        # SCENE 3: Live Safe Swap & 3D Pathway Resolution
        # ----------------------------------------------------------------------
        s3_dur = scene_durations["scene_3"] + SCENE_BREATHING_ROOM
        print(f"  • Recording Scene 3 (Live Safe Swap) — Target duration: {s3_dur:.2f}s...")
        t_scene_start = time.perf_counter()

        # Glide to green "Apply Safe Swap" button
        swap_btn = page.locator(".btn-apply-swap").first
        if swap_btn.count() > 0:
            box = swap_btn.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=750)
                page.wait_for_timeout(400)
                cursor.click()
                try:
                    swap_btn.click(force=True)
                except Exception:
                    pass

        # Hold 3.5s for 3D animation and emerald "All Pathways Clear" pill to shine
        page.wait_for_timeout(3500)

        # Glide cursor up to showcase the top emerald "All Pathways Clear" pill
        all_clear = page.locator("#stageAllClearNotice")
        if all_clear.count() > 0:
            box = all_clear.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=850)
                page.wait_for_timeout(1000)

        # Glide to "Undo Swap" button on right panel
        undo_btn = page.locator("#btnUndoSwap")
        if undo_btn.count() > 0 and undo_btn.is_visible():
            box = undo_btn.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=750)
                page.wait_for_timeout(600)

        elapsed = time.perf_counter() - t_scene_start
        if s3_dur > elapsed:
            page.wait_for_timeout((s3_dur - elapsed) * 1000)

        # ----------------------------------------------------------------------
        # SCENE 4: Polypharmacy & AI Graph Agent Traversal
        # ----------------------------------------------------------------------
        s4_dur = scene_durations["scene_4"] + SCENE_BREATHING_ROOM
        print(f"  • Recording Scene 4 (Polypharmacy & AI Agent) — Target duration: {s4_dur:.2f}s...")
        t_scene_start = time.perf_counter()

        # Click Preset 4: Statin + Diet Clash
        p4 = page.locator("#btnPreset4")
        if p4.count() > 0:
            box = p4.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=800)
                cursor.click()
                try:
                    p4.click(force=True)
                except Exception:
                    pass
                page.wait_for_timeout(1600)

        # Glide down to prompt chip: "🩺 Why do I have muscle pain?"
        chip = page.locator(".agent-prompt-chip").filter(has_text="muscle pain").first
        if chip.count() > 0:
            box = chip.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=850)
                page.wait_for_timeout(400)
                cursor.click()
                try:
                    chip.click(force=True)
                except Exception:
                    pass

        # Wait 2.8s for 3D graph scan wave & multi-node bounding box focus
        page.wait_for_timeout(2800)

        # Glide to and click "Inspect Executed Cypher Query"
        details_summary = page.locator(".agent-cypher-details summary").first
        if details_summary.count() > 0:
            box = details_summary.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=750)
                cursor.click()
                try:
                    details_summary.click(force=True)
                except Exception:
                    pass
                page.wait_for_timeout(2000)

        elapsed = time.perf_counter() - t_scene_start
        if s4_dur > elapsed:
            page.wait_for_timeout((s4_dur - elapsed) * 1000)

        # ----------------------------------------------------------------------
        # SCENE 5: Clinical Utility, Routine, Organ Burden & Closing
        # ----------------------------------------------------------------------
        s5_dur = scene_durations["scene_5"] + SCENE_BREATHING_ROOM
        print(f"  • Recording Scene 5 (Clinical Suite & Closing) — Target duration: {s5_dur:.2f}s...")
        t_scene_start = time.perf_counter()

        # Click "Daily Routine" tab
        tab_sched = page.locator("#tabBtnSchedule")
        if tab_sched.count() > 0:
            box = tab_sched.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=700)
                cursor.click()
                try:
                    tab_sched.click(force=True)
                except Exception:
                    pass
                page.wait_for_timeout(3400)

        # Click "Organ Load" tab
        tab_organ = page.locator("#tabBtnOrgan")
        if tab_organ.count() > 0:
            box = tab_organ.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=650)
                cursor.click()
                try:
                    tab_organ.click(force=True)
                except Exception:
                    pass
                page.wait_for_timeout(3400)

        # Click "Cypher" tab
        tab_cypher = page.locator("#tabBtnCypher")
        if tab_cypher.count() > 0:
            box = tab_cypher.bounding_box()
            if box:
                cursor.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, duration_ms=650)
                cursor.click()
                try:
                    tab_cypher.click(force=True)
                except Exception:
                    pass
                page.wait_for_timeout(3800)

        elapsed = time.perf_counter() - t_scene_start
        if s5_dur > elapsed:
            page.wait_for_timeout((s5_dur - elapsed) * 1000)

        # Retrieve video path
        video_path_str = page.video.path()
        page.close()
        context.close()
        browser.close()

        raw_video_path = Path(video_path_str)

    print(f"  ✓ Browser recording complete: {raw_video_path.name}")
    return raw_video_path


# ==============================================================================
# 7. AUDIO MIXING & BROADCAST MASTERING (FFmpeg)
# ==============================================================================
def format_srt_time(seconds: float) -> str:
    """Formats seconds into standard SRT timestamp (00:00:00,000)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int(round((seconds - int(seconds)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"


def assemble_broadcast_audio(scene_durations: dict, total_timeline_sec: float) -> Path:
    """Builds synchronized voiceover track, mixed with ducked ambient synth pad and loudnorm."""
    print("[6/8] Mastering broadcast audio stream (48kHz stereo, loudnorm)...")
    
    ambient_wav = OUTPUT_DIR / "ambient_synth_pad.wav"
    generate_ambient_synth_track(total_timeline_sec + 2.0, ambient_wav)

    scene_offsets = []
    current_offset = INTRO_DURATION

    for name, _ in SCENE_SCRIPTS:
        scene_offsets.append(current_offset)
        dur = scene_durations[name]
        current_offset += dur + SCENE_BREATHING_ROOM

    # Build Subtitles (.srt)
    with open(SUBTITLES_SRT, "w", encoding="utf-8") as f:
        for idx, ((name, text), offset) in enumerate(zip(SCENE_SCRIPTS, scene_offsets), start=1):
            dur = scene_durations[name]
            start_str = format_srt_time(offset)
            end_str = format_srt_time(offset + dur)
            f.write(f"{idx}\n{start_str} --> {end_str}\n{text}\n\n")
    print(f"  ✓ Subtitles exported: {SUBTITLES_SRT.name}")

    # Assemble FFmpeg audio filter
    inputs_cmd = ["-i", str(ambient_wav)]
    for name, _ in SCENE_SCRIPTS:
        inputs_cmd.extend(["-i", str(AUDIO_DIR / f"{name}.mp3")])

    filter_parts = []
    for i, offset in enumerate(scene_offsets, start=1):
        delay_ms = int(offset * 1000)
        filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[delayed_{i}]")

    delayed_labels = "".join([f"[delayed_{i}]" for i in range(1, 6)])
    filter_parts.append(f"{delayed_labels}amix=inputs=5:duration=longest:dropout_transition=0[voiceover]")

    filter_parts.append("[0:a]volume=0.040[pad_ducked]")  # ~-28 dB
    filter_parts.append("[voiceover][pad_ducked]amix=inputs=2:duration=longest:dropout_transition=0[mixed]")

    filter_parts.append("[mixed]loudnorm=I=-14:TP=-1.5:LRA=11,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[final_audio]")

    filter_complex = ";".join(filter_parts)
    mastered_audio_path = OUTPUT_DIR / "master_audio.aac"

    run_ffmpeg([
        "-y",
        *inputs_cmd,
        "-filter_complex", filter_complex,
        "-map", "[final_audio]",
        "-t", f"{total_timeline_sec:.2f}",
        "-c:a", "aac", "-b:a", "320k",
        str(mastered_audio_path)
    ])

    print(f"  ✓ Broadcast mastered audio created: {mastered_audio_path.name}")
    return mastered_audio_path


# ==============================================================================
# 8. FINAL 4K 60FPS MASTER ASSEMBLY & OPTIONAL 8K UPSCALE
# ==============================================================================
def assemble_master_video(raw_video: Path, intro_mp4: Path, outro_mp4: Path, master_audio: Path, upscale_8k: bool = False):
    """Assembles final 4K 60fps MP4 master with intro, outro, and synced audio."""
    print("[7/8] Rendering final 4K UHD 60fps Master Video...")
    
    browser_60fps = OUTPUT_DIR / "browser_capture_60fps.mp4"
    print("  • Transcoding browser capture to 60fps 3840x2160...")
    run_ffmpeg([
        "-y", "-i", str(raw_video),
        "-vf", "fps=60,scale=3840:2160:flags=lanczos,unsharp=3:3:0.35,format=yuv420p",
        "-c:v", "libx264", "-crf", "14", "-preset", "fast",
        str(browser_60fps)
    ])

    concat_list_file = OUTPUT_DIR / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        f.write(f"file '{intro_mp4.name}'\n")
        f.write(f"file '{browser_60fps.name}'\n")
        f.write(f"file '{outro_mp4.name}'\n")

    video_only_mp4 = OUTPUT_DIR / "video_assembly_noaudio.mp4"
    run_ffmpeg([
        "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list_file),
        "-c", "copy",
        str(video_only_mp4)
    ])

    print("  • Muxing synchronized broadcast audio with 4K 60fps master...")
    run_ffmpeg([
        "-y",
        "-i", str(video_only_mp4),
        "-i", str(master_audio),
        "-c:v", "copy",
        "-c:a", "copy",
        "-shortest",
        "-movflags", "+faststart",
        str(OUTPUT_4K)
    ])
    print(f"  ✓ 4K UHD MASTER READY: {OUTPUT_4K}")

    if upscale_8k:
        print("  • Generating optional 8K (7680x4320) Lanczos upscale master...")
        run_ffmpeg([
            "-y", "-i", str(OUTPUT_4K),
            "-vf", "scale=7680:4320:flags=lanczos",
            "-c:v", "libx264", "-crf", "14", "-preset", "medium",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(OUTPUT_8K)
        ])
        print(f"  ✓ 8K MASTER READY: {OUTPUT_8K}")


# ==============================================================================
# 9. VERIFICATION & THUMBNAILS EXTRACTION
# ==============================================================================
def verify_and_extract_thumbnails(scene_durations: dict):
    """Extracts 3 inspection thumbnails and validates stream metadata."""
    print("[8/8] Performing post-production verification & thumbnail extraction...")
    
    if not OUTPUT_4K.exists() or OUTPUT_4K.stat().st_size < 1000000:
        raise RuntimeError("Master 4K video is missing or abnormally small.")

    file_size_mb = OUTPUT_4K.stat().st_size / (1024 * 1024)
    total_dur = get_media_duration(OUTPUT_4K)
    print(f"  ✓ Video Verified: {total_dur:.2f} seconds | {file_size_mb:.1f} MB | Resolution: 3840x2160")

    # --------------------------------------------------------------------------
    # Mandatory Automated Edge-to-Edge Verification
    # --------------------------------------------------------------------------
    verify_png = OUTPUT_DIR / "verify_fullframe.png"
    print("  • Extracting verification frame at t=15.0s for edge-to-edge inspection...")
    run_ffmpeg(["-y", "-ss", "15.0", "-i", str(OUTPUT_4K), "-vframes", "1", str(verify_png)])
    
    if not verify_png.exists():
        raise RuntimeError("Verification frame output/verify_fullframe.png was not generated.")

    verify_img = Image.open(verify_png)
    if verify_img.size != (3840, 2160):
        raise RuntimeError(f"Expected 3840x2160 frame size, got {verify_img.size}")

    # Inspect bottom-right corner pixels (x=3600..3800, y=1950..2100)
    # Confirm pixels belong to the bright light-blue/white right-hand SafeMeds panel, NOT solid gray (#808080)
    gray_matches = 0
    total_samples = 0
    sample_colors = []
    for x in range(3600, 3800, 8):
        for y in range(1950, 2100, 8):
            r, g, b = verify_img.getpixel((x, y))[:3]
            sample_colors.append((r, g, b))
            total_samples += 1
            # Check if pixel is neutral/solid gray (#808080 +/- 15)
            if abs(r - 128) < 15 and abs(g - 128) < 15 and abs(b - 128) < 15:
                gray_matches += 1

    gray_ratio = gray_matches / total_samples
    avg_r = sum(c[0] for c in sample_colors) / len(sample_colors)
    avg_g = sum(c[1] for c in sample_colors) / len(sample_colors)
    avg_b = sum(c[2] for c in sample_colors) / len(sample_colors)
    print(f"  • Edge-to-edge pixel check: Average corner color RGB({avg_r:.1f}, {avg_g:.1f}, {avg_b:.1f}), Gray padding ratio: {gray_ratio:.1%}")

    if gray_ratio > 0.15:
        raise RuntimeError(f"Edge-to-edge check FAILED: {gray_ratio:.1%} of corner pixels are gray padding (#808080).")

    print("  ✓ Full-Frame Edge-to-Edge Verified: Corner pixels contain active UI content (zero gray margins).")

    # Confirm video & audio streams via FFmpeg inspection
    probe_res = subprocess.run([FFMPEG, "-i", str(OUTPUT_4K)], capture_output=True, text=True)
    probe_output = probe_res.stderr
    if "3840x2160" not in probe_output:
        raise RuntimeError("Video stream resolution is not 3840x2160 in container metadata.")
    if "Audio: aac" not in probe_output and "Stream #0:1" not in probe_output:
        raise RuntimeError("Audio stream missing in final MP4 master.")
    print("  ✓ Stream Metadata Verified: 3840x2160 video stream + AAC audio stream verified.")

    t_s1 = 8.0
    t_s3 = INTRO_DURATION + scene_durations["scene_1"] + SCENE_BREATHING_ROOM + scene_durations["scene_2"] + SCENE_BREATHING_ROOM + 5.5
    t_s4 = t_s3 + (scene_durations["scene_3"] - 5.5) + SCENE_BREATHING_ROOM + 8.5

    thumb_1 = OUTPUT_DIR / "check_scene1.png"
    thumb_3 = OUTPUT_DIR / "check_scene3_swap.png"
    thumb_4 = OUTPUT_DIR / "check_scene4_agent.png"

    run_ffmpeg(["-y", "-ss", f"{t_s1:.2f}", "-i", str(OUTPUT_4K), "-vframes", "1", str(thumb_1)])
    run_ffmpeg(["-y", "-ss", f"{t_s3:.2f}", "-i", str(OUTPUT_4K), "-vframes", "1", str(thumb_3)])
    run_ffmpeg(["-y", "-ss", f"{t_s4:.2f}", "-i", str(OUTPUT_4K), "-vframes", "1", str(thumb_4)])

    print("  ✓ Verification thumbnails saved:")
    print(f"    - Scene 1 (3D Graph & Badge):   {thumb_1}")
    print(f"    - Scene 3 (Resolved Safe Swap): {thumb_3}")
    print(f"    - Scene 4 (Agent & Cypher):     {thumb_4}")


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="SafeMeds 3D Studio Demo Video Pipeline")
    parser.add_argument("--8k", dest="upscale_8k", action="store_true", help="Also render 8K (7680x4320) Lanczos upscale")
    parser.add_argument("--skip-audio", action="store_true", help="Reuse existing voiceover audio files")
    parser.add_argument("--skip-browser", action="store_true", help="Reuse existing raw browser video recording")
    parser.add_argument("--headless", action="store_true", help="Run browser recording in headless mode")
    args = parser.parse_args()

    t_start = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 76)
    print("  SAFEMEDS 3D GRAPH STUDIO — 4K BROADCAST DEMO VIDEO PIPELINE")
    print("  Relate by Neo4j Hackathon: \"Context, Connected\"")
    print("=" * 76)

    server_proc = ensure_local_server()

    try:
        scene_durations = generate_voiceovers(skip=args.skip_audio)

        browser_timeline_sec = sum(scene_durations.values()) + len(scene_durations) * SCENE_BREATHING_ROOM
        total_timeline_sec = INTRO_DURATION + browser_timeline_sec + OUTRO_DURATION
        print(f"  • Planned Total Video Duration: {total_timeline_sec:.2f}s (~{int(total_timeline_sec)}s)")

        intro_mp4, outro_mp4 = generate_title_cards()

        raw_video_path = record_browser_session(scene_durations, headless=args.headless, skip=args.skip_browser)

        master_audio = assemble_broadcast_audio(scene_durations, total_timeline_sec)

        assemble_master_video(raw_video_path, intro_mp4, outro_mp4, master_audio, upscale_8k=args.upscale_8k)

        verify_and_extract_thumbnails(scene_durations)

        elapsed = time.perf_counter() - t_start
        print("=" * 76)
        print(f"  PRODUCTION PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.1f}s")
        print(f"  Output Master: {OUTPUT_4K}")
        if args.upscale_8k:
            print(f"  Output 8K Master: {OUTPUT_8K}")
        print(f"  Subtitles (.srt): {SUBTITLES_SRT}")
        print("=" * 76)

    finally:
        if server_proc:
            print("Cleaning up background server subprocess...")
            server_proc.terminate()


if __name__ == "__main__":
    main()
