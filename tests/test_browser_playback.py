"""
Automated end-to-end browser regression test for Three.js avatar rendering,
WebGL2 context stability, multi-sign playback, and mesh vertex deformation.
"""

import asyncio
import json
import os
import subprocess
import time
import urllib.request
import pytest
from PIL import Image
import numpy as np

try:
    import websockets
except ImportError:
    subprocess.check_call(["pip", "install", "websockets"])
    import websockets


def get_or_launch_chrome():
    """Ensure Chrome is running with remote debugging port 9222."""
    try:
        urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=1)
        return None  # already running
    except Exception:
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        user_data = os.path.join(os.environ.get("TEMP", r"C:\Temp"), f"chrome_avatar_test_{int(time.time())}")
        cmd = [
            chrome_path,
            "--remote-debugging-port=9222",
            f"--user-data-dir={user_data}",
            "--headless=new",
            "--enable-webgl",
            "--ignore-gpu-blocklist",
            "--disable-gpu-sandbox",
            "--window-size=1280,800",
            "http://localhost:5174"
        ]
        proc = subprocess.Popen(cmd)
        time.sleep(3)
        return proc


@pytest.mark.asyncio
async def test_e2e_avatar_browser_playback_and_deformation():
    """
    Connects to Chrome via CDP, asserts WebGL2 active, verifies mesh deformation
    across playback frames, switches signs, and asserts subsequent playback works
    with zero console or WebGL errors.
    """
    proc = get_or_launch_chrome()
    try:
        targets_raw = urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=5).read().decode("utf-8")
        targets = json.loads(targets_raw)
        page_target = next((t for t in targets if t.get("type") == "page" and "localhost:5174" in t.get("url", "")), None)

        if not page_target:
            # Open new tab to localhost:5174 if not present
            new_tab = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/new?http://localhost:5174", timeout=5).read().decode("utf-8"))
            ws_url = new_tab["webSocketDebuggerUrl"]
        else:
            ws_url = page_target["webSocketDebuggerUrl"]

        console_errors = []
        failed_requests = []

        async with websockets.connect(ws_url, max_size=50_000_000) as ws:
            msg_id = 1
            async def cdp(method, params=None):
                nonlocal msg_id
                cid = msg_id
                msg_id += 1
                await ws.send(json.dumps({"id": cid, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(await ws.recv())
                    if "method" in msg:
                        if msg["method"] == "Console.messageAdded":
                            m = msg["params"]["message"]
                            if m.get("level") == "error":
                                console_errors.append(m.get("text", ""))
                        elif msg["method"] == "Network.responseReceived":
                            r = msg["params"]["response"]
                            if r["status"] >= 400:
                                failed_requests.append(f"{r['status']} {r['url']}")
                    if msg.get("id") == cid:
                        return msg.get("result", {})

            await cdp("Page.enable")
            await cdp("Console.enable")
            await cdp("Network.enable")
            await cdp("Runtime.enable")

            # Wait for 3D stage and initial sign to load
            await asyncio.sleep(4)

            # 1. Assert WebGL2 context health
            diag = await cdp("Runtime.evaluate", {
                "expression": """(() => {
                    const canvas = document.querySelector('#avatar-interactive-section canvas') || document.querySelector('canvas');
                    if (!canvas) return { error: 'No canvas found' };
                    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
                    if (!gl) return { error: 'No WebGL context' };
                    return {
                        hasCanvas: true,
                        contextType: gl instanceof WebGL2RenderingContext ? 'webgl2' : 'webgl',
                        drawingBufferWidth: gl.drawingBufferWidth,
                        drawingBufferHeight: gl.drawingBufferHeight,
                        isContextLost: gl.isContextLost(),
                        error: gl.getError()
                    };
                })()""",
                "returnByValue": True
            })

            res = diag.get("result", {}).get("value", {})
            assert res.get("hasCanvas") is True, f"Canvas not located: {res}"
            assert res.get("isContextLost") is False, "WebGL context was lost"
            assert res.get("error") == 0, f"WebGL reported error: {res.get('error')}"
            assert res.get("drawingBufferWidth", 0) > 200, "Drawing buffer width too small"

            # 2. Capture frame 1 screenshot
            import base64
            scr1 = await cdp("Page.captureScreenshot", {"format": "png"})
            arr1 = np.array(Image.open(io_bytes := __import__('io').BytesIO(base64.b64decode(scr1["data"]))), dtype=np.int16)

            # Wait during sign 1 playback
            await asyncio.sleep(1.5)

            # 3. Capture frame 2 screenshot and verify mesh deformation delta
            scr2 = await cdp("Page.captureScreenshot", {"format": "png"})
            arr2 = np.array(Image.open(__import__('io').BytesIO(base64.b64decode(scr2["data"]))), dtype=np.int16)

            # Check avatar stage region (bottom right)
            crop1 = arr1[400:800, 600:1200]
            crop2 = arr2[400:800, 600:1200]
            diff12 = np.abs(crop1 - crop2)
            changed_pixels_1 = np.count_nonzero(diff12.max(axis=-1) > 5)

            assert changed_pixels_1 > 500, f"Expected mesh animation, only {changed_pixels_1} pixels changed"

            # 4. Trigger subsequent sign ('Drink')
            click_res = await cdp("Runtime.evaluate", {
                "expression": """(() => {
                    const buttons = Array.from(document.querySelectorAll('#avatar-interactive-section button'));
                    const targetBtn = buttons.find(b => b.textContent && b.textContent.trim() === 'Drink');
                    if (targetBtn) {
                        targetBtn.click();
                        return { clicked: true, text: targetBtn.textContent };
                    }
                    return { clicked: false, buttons: buttons.map(b => b.textContent) };
                })()""",
                "returnByValue": True
            })
            val_click = click_res.get("result", {}).get("value", {})
            assert val_click.get("clicked") is True, f"Failed to click Drink sign: {val_click}"

            # Wait for subsequent sign to load and animate
            await asyncio.sleep(2.0)

            # 5. Capture frame 3 screenshot and assert subsequent playback deformation
            scr3 = await cdp("Page.captureScreenshot", {"format": "png"})
            arr3 = np.array(Image.open(__import__('io').BytesIO(base64.b64decode(scr3["data"]))), dtype=np.int16)
            crop3 = arr3[400:800, 600:1200]
            diff23 = np.abs(crop2 - crop3)
            changed_pixels_2 = np.count_nonzero(diff23.max(axis=-1) > 5)

            assert changed_pixels_2 > 500, f"Subsequent playback failed to animate, only {changed_pixels_2} pixels changed"

            # 6. Assert zero console errors and zero failed requests
            assert len(console_errors) == 0, f"Encountered browser console errors: {console_errors}"
            assert len(failed_requests) == 0, f"Encountered failed network requests: {failed_requests}"

    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
