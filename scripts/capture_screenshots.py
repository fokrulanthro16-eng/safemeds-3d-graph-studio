#!/usr/bin/env python3
"""
SafeMeds 3D Graph Studio — Automated 4K UHD Screenshot Capture Pipeline
Captures 6 submission-ready 4K (3840x2160) PNG screenshots for hackathon evaluation.
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
from PIL import Image, ImageStat
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "docs" / "screenshots"

SCREENSHOTS = [
    {
        "filename": "01_hero_heart_gastric_block.png",
        "title": "Hero: Heart + Gastric Block (Clopidogrel + Omeprazole CYP2C19 Block)",
        "action": "hero"
    },
    {
        "filename": "02_live_safe_swap_resolved.png",
        "title": "Live Safe Swap: Famotidine Activated, 3D Pathways Clear",
        "action": "safe_swap"
    },
    {
        "filename": "03_polypharmacy_statin_diet.png",
        "title": "Polypharmacy: Statin + Grapefruit + Warfarin + Spinach 5-Item Graph",
        "action": "statin_diet"
    },
    {
        "filename": "04_ai_agent_cypher_trace.png",
        "title": "AI Agent: Symptom Reverse Trace & Executed Relate Cypher Query",
        "action": "ai_agent"
    },
    {
        "filename": "05_antibiotic_dairy_daily_routine.png",
        "title": "Clinical Suite: 3h Chelation Gap & 5-Slot Daily Schedule",
        "action": "antibiotic_schedule"
    },
    {
        "filename": "06_nsaid_organ_load_dashboard.png",
        "title": "Organ Load: BP + Double NSAID Cumulative Stress Meters",
        "action": "organ_load"
    }
]


def ensure_local_server():
    """Verifies that the SafeMeds local API server is responding on port 8000."""
    import urllib.request
    print("[1/3] Checking SafeMeds local API server on http://127.0.0.1:8000...")
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1.5) as res:
            if res.status == 200:
                print("  ✓ Local SafeMeds API server is online and healthy.")
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
            with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1) as res:
                if res.status == 200:
                    print("  ✓ Server successfully launched.")
                    return proc
        except Exception:
            continue
    raise RuntimeError("Failed to connect to local SafeMeds server at http://127.0.0.1:8000")


def capture_screenshots(headless: bool = False):
    """Executes the Playwright capture suite generating 3840x2160 screenshots."""
    print("[2/3] Capturing 6 studio-grade 4K UHD screenshots...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--use-gl=angle",
                "--enable-webgl",
                "--ignore-gpu-blocklist",
                "--disable-infobars",
                "--start-maximized"
            ]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2  # Produces native 3840x2160 screenshots
        )

        page = context.new_page()

        print("  • Navigating to http://127.0.0.1:8000...")
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")

        # Hide any browser scrollbars across the viewport
        page.add_style_tag(content="""
            ::-webkit-scrollbar { display: none !important; width: 0 !important; height: 0 !important; }
            * { scrollbar-width: none !important; -ms-overflow-style: none !important; }
            html, body { overflow: hidden !important; }
        """)

        # ----------------------------------------------------------------------
        # SCREENSHOT 1: Hero Heart + Gastric Block
        # ----------------------------------------------------------------------
        print(f"  [1/6] Capturing: {SCREENSHOTS[0]['title']}...")
        page.locator("#btnPreset1").click(force=True)
        page.locator("#tabBtnClinical").click(force=True)
        page.wait_for_timeout(2600)  # Let 3D camera & WebGL shaders settle
        target_path_1 = OUTPUT_DIR / SCREENSHOTS[0]["filename"]
        page.screenshot(path=str(target_path_1))
        print(f"        ✓ Saved {target_path_1.name}")

        # ----------------------------------------------------------------------
        # SCREENSHOT 2: Live Safe Swap Resolved
        # ----------------------------------------------------------------------
        print(f"  [2/6] Capturing: {SCREENSHOTS[1]['title']}...")
        swap_btn = page.locator(".btn-apply-swap").first
        if swap_btn.count() > 0:
            swap_btn.click(force=True)
        page.wait_for_timeout(3500)  # Wait for 3D transition and emerald notice
        target_path_2 = OUTPUT_DIR / SCREENSHOTS[1]["filename"]
        page.screenshot(path=str(target_path_2))
        print(f"        ✓ Saved {target_path_2.name}")

        # ----------------------------------------------------------------------
        # SCREENSHOT 3: Polypharmacy Statin + Diet Clash
        # ----------------------------------------------------------------------
        print(f"  [3/6] Capturing: {SCREENSHOTS[2]['title']}...")
        page.locator("#btnPreset4").click(force=True)
        page.locator("#tabBtnClinical").click(force=True)
        page.wait_for_timeout(2800)  # Wait for 5-item auto-framing
        target_path_3 = OUTPUT_DIR / SCREENSHOTS[2]["filename"]
        page.screenshot(path=str(target_path_3))
        print(f"        ✓ Saved {target_path_3.name}")

        # ----------------------------------------------------------------------
        # SCREENSHOT 4: AI Agent Cypher Trace
        # ----------------------------------------------------------------------
        print(f"  [4/6] Capturing: {SCREENSHOTS[3]['title']}...")
        chip = page.locator(".agent-prompt-chip").filter(has_text="muscle pain").first
        if chip.count() > 0:
            chip.click(force=True)
        page.wait_for_timeout(2500)  # Wait for agent query execution & 3D focus
        
        # Open Executed Cypher details
        details_summary = page.locator(".agent-cypher-details summary").first
        if details_summary.count() > 0:
            details_summary.click(force=True)
        page.wait_for_timeout(1500)  # Wait for code block reveal
        target_path_4 = OUTPUT_DIR / SCREENSHOTS[3]["filename"]
        page.screenshot(path=str(target_path_4))
        print(f"        ✓ Saved {target_path_4.name}")

        # Close agent popup for subsequent screenshots
        page.evaluate("const p = document.getElementById('agentResponsePopup'); if (p) p.style.display = 'none';")

        # ----------------------------------------------------------------------
        # SCREENSHOT 5: Antibiotic + Dairy Daily Routine Schedule
        # ----------------------------------------------------------------------
        print(f"  [5/6] Capturing: {SCREENSHOTS[4]['title']}...")
        page.locator("#btnPreset2").click(force=True)
        page.wait_for_timeout(2000)
        page.locator("#tabBtnSchedule").click(force=True)
        page.wait_for_timeout(2000)  # Let timetable layout settle
        target_path_5 = OUTPUT_DIR / SCREENSHOTS[4]["filename"]
        page.screenshot(path=str(target_path_5))
        print(f"        ✓ Saved {target_path_5.name}")

        # ----------------------------------------------------------------------
        # SCREENSHOT 6: BP + Double NSAID Organ Load Dashboard
        # ----------------------------------------------------------------------
        print(f"  [6/6] Capturing: {SCREENSHOTS[5]['title']}...")
        page.locator("#btnPreset3").click(force=True)
        page.wait_for_timeout(2000)
        page.locator("#tabBtnOrgan").click(force=True)
        page.wait_for_timeout(2000)  # Let organ load meters render
        target_path_6 = OUTPUT_DIR / SCREENSHOTS[5]["filename"]
        page.screenshot(path=str(target_path_6))
        print(f"        ✓ Saved {target_path_6.name}")

        page.close()
        context.close()
        browser.close()


def verify_and_optimize_screenshots():
    """Validates 3840x2160 resolution, non-blank content, and web-ready file sizes."""
    print("[3/3] Verifying and optimizing screenshots...")
    
    for item in SCREENSHOTS:
        filepath = OUTPUT_DIR / item["filename"]
        if not filepath.exists():
            raise FileNotFoundError(f"Missing screenshot: {filepath}")

        with Image.open(filepath) as img:
            w, h = img.size
            if (w, h) != (3840, 2160):
                raise ValueError(f"{item['filename']} resolution mismatch: expected (3840, 2160), got ({w}, {h})")

            # Check that image is not blank/solid
            stat = ImageStat.Stat(img)
            avg_stddev = sum(stat.stddev[:3]) / 3
            if avg_stddev < 8.0:
                raise ValueError(f"{item['filename']} appears blank/solid (stddev={avg_stddev:.1f})")

            initial_size_mb = filepath.stat().st_size / (1024 * 1024)

            # If over 4.8MB, optimize PNG compression for fast loading
            if initial_size_mb > 4.8:
                print(f"  • Optimizing compression for {item['filename']} ({initial_size_mb:.2f} MB)...")
                img.save(filepath, format="PNG", optimize=True)
                final_size_mb = filepath.stat().st_size / (1024 * 1024)
                print(f"    ✓ Reduced to {final_size_mb:.2f} MB")
            else:
                final_size_mb = initial_size_mb

        print(f"  ✓ {item['filename']}: 3840x2160 | {final_size_mb:.2f} MB | Non-blank (stddev: {avg_stddev:.1f}) | {item['title']}")


def main():
    parser = argparse.ArgumentParser(description="Capture 4K Screenshots of SafeMeds 3D Studio")
    parser.add_argument("--headless", action="store_true", default=False, help="Run browser in headless mode")
    args = parser.parse_args()

    t_start = time.perf_counter()
    print("=" * 76)
    print("  SAFEMEDS 3D GRAPH STUDIO — 4K SUBMISSION SCREENSHOT SUITE")
    print("  Relate by Neo4j Hackathon: \"Context, Connected\"")
    print("=" * 76)

    server_proc = ensure_local_server()

    try:
        capture_screenshots(headless=args.headless)
        verify_and_optimize_screenshots()
        elapsed = time.perf_counter() - t_start
        print("=" * 76)
        print(f"  ALL 6 SCREENSHOTS CAPTURED & VERIFIED IN {elapsed:.1f}s")
        print(f"  Target Directory: {OUTPUT_DIR}")
        print("=" * 76)
    finally:
        if server_proc:
            print("Cleaning up local server subprocess...")
            server_proc.terminate()


if __name__ == "__main__":
    main()
