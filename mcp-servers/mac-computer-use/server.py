#!/usr/bin/env python3
"""
macOS Computer Use MCP Server (v3 - AppleScript-first)
- AppleScript for screenshots, keyboard, clipboard, window management, UI interaction
- CGEvent in isolated subprocesses for mouse operations only
- Full-quality screenshots with ImageContent return
- Chinese text input via clipboard paste
"""

import asyncio
import base64
import io
import json
import os
import subprocess
import sys
import time
import tempfile
from typing import Any

from mcp.server import Server, ServerRequestContext, NotificationOptions, InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types

# Quartz only for safe read-only operations (no CGEvent in main process)
from Quartz import (
    CGMainDisplayID,
    CGDisplayPixelsWide,
    CGDisplayPixelsHigh,
    CGGetActiveDisplayList,
    CGDisplayBounds,
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionAll,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID,
    kCGWindowNumber,
    kCGWindowOwnerName,
    kCGWindowName,
    kCGWindowBounds,
    kCGWindowLayer,
    # Screenshot via Quartz API (replaces screencapture -D subprocess)
    CGDisplayCreateImage,
    CGDisplayCreateImageForRect,
    CGImageGetWidth,
    CGImageGetHeight,
    CGImageGetBitsPerPixel,
    CGImageGetDataProvider,
    CGDataProviderCopyData,
    CGRectMake,
)
from PIL import Image


# ============================================================
# Helper: Run AppleScript
# ============================================================

def _run_applescript(script: str, timeout: int = 10) -> tuple[bool, str]:
    """Run an AppleScript and return (success, output_or_error)."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def _run_applescript_file(script: str, timeout: int = 15) -> tuple[bool, str]:
    """Run a multi-line AppleScript via temp file (avoids -e escaping issues)."""
    with tempfile.NamedTemporaryFile(suffix=".scpt", mode="w", delete=False) as f:
        f.write(script)
        f.flush()
        script_path = f.name
    try:
        result = subprocess.run(
            ["osascript", script_path],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)
    finally:
        try:
            os.unlink(script_path)
        except:
            pass


def _escape_as_string(text: str) -> str:
    """Escape text for use as an AppleScript string literal."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


# ============================================================
# Screenshot (full resolution, high quality, no cropping)
# ============================================================

def _get_display_info() -> dict:
    """Get multi-display configuration info."""
    try:
        count, displays, _ = CGGetActiveDisplayList(10, None, None)
        main_id = CGMainDisplayID()
        display_list = []
        for i, d in enumerate(displays):
            r = CGDisplayBounds(d)
            display_list.append({
                "index": i,
                "display_id": d,
                "is_main": d == main_id,
                "origin": {"x": r.origin.x, "y": r.origin.y},
                "size": {"width": r.size.width, "height": r.size.height},
            })
        return {"displays": display_list, "main_display_id": main_id}
    except Exception:
        return {"displays": [], "main_display_id": 0}


def _find_display_for_point(x: float, y: float) -> dict:
    """Find which display contains the given point."""
    info = _get_display_info()
    for d in info["displays"]:
        ox = d["origin"]["x"]
        oy = d["origin"]["y"]
        ow = d["size"]["width"]
        oh = d["size"]["height"]
        if ox <= x < ox + ow and oy <= y < oy + oh:
            return d
    # Default to main display
    for d in info["displays"]:
        if d["is_main"]:
            return d
    return info["displays"][0] if info["displays"] else None


def _cgimage_to_jpeg(cg_image) -> tuple[bytes, int, int]:
    """Convert a CGImageRef to JPEG bytes.

    Returns (jpeg_bytes, width, height).
    CoreGraphics bitmap data is bottom-up; PIL expects top-down.
    """
    width = CGImageGetWidth(cg_image)
    height = CGImageGetHeight(cg_image)

    provider = CGImageGetDataProvider(cg_image)
    data = CGDataProviderCopyData(provider)
    raw_bytes = bytes(data)

    bpp = CGImageGetBitsPerPixel(cg_image)
    mode = 'RGBA' if bpp == 32 else 'RGB'
    img = Image.frombytes(mode, (width, height), raw_bytes)
    # CoreGraphics bitmap data is bottom-up; PIL expects top-down
    img = img.transpose(Image.FLIP_TOP_BOTTOM)

    img_rgb = img.convert("RGB")
    buf = io.BytesIO()
    img_rgb.save(buf, format="JPEG", quality=85)
    img_data = buf.getvalue()

    # Reduce quality if too large
    if len(img_data) > 1_500_000:
        buf = io.BytesIO()
        img_rgb.save(buf, format="JPEG", quality=65)
        img_data = buf.getvalue()

    return img_data, width, height


def _validate_coordinates(x: float, y: float, operation: str = "mouse") -> tuple[bool, str, dict]:
    """Validate that (x, y) falls within at least one display's bounds.

    Returns (is_valid, error_message, display_info).
    Does NOT fall back to main display — out-of-bounds is an error.
    """
    info = _get_display_info()
    if not info["displays"]:
        return False, "No active displays found", None

    # Check each display's bounds directly (no fallback to main display)
    for d in info["displays"]:
        ox = d["origin"]["x"]
        oy = d["origin"]["y"]
        ow = d["size"]["width"]
        oh = d["size"]["height"]
        if ox <= x < ox + ow and oy <= y < oy + oh:
            return True, "", d

    # Point is outside all displays
    bounds_str = []
    for d in info["displays"]:
        ox, oy = d["origin"]["x"], d["origin"]["y"]
        ow, oh = d["size"]["width"], d["size"]["height"]
        label = "main" if d["is_main"] else f"display_id={d['display_id']}"
        bounds_str.append(
            f"{label}: x=[{ox}, {ox+ow}), y=[{oy}, {oy+oh})"
        )
    return False, (
        f"Coordinates ({x}, {y}) are outside all displays. "
        f"Valid ranges: {'; '.join(bounds_str)}"
    ), None


def _screenshot(path: str = "/tmp/computer_use_screenshot.png", region=None, display_id: int = 0) -> dict:
    """Capture screenshot using Quartz CGDisplayCreateImage.

    Coordinates are in LOGICAL points (global display coordinate space).
    Mouse clicks use the same coordinate system.

    Args:
        path: Save path (kept for backward compat, image is returned inline)
        region: Optional {x, y, width, height} in global logical points
        display_id: Which display to capture (0=auto-detect)
    """
    try:
        info = _get_display_info()
        if not info["displays"]:
            return {"success": False, "error": "No display found"}

        main_display = None
        target_display = None
        for d in info["displays"]:
            if d["is_main"]:
                main_display = d
            if d["display_id"] == display_id:
                target_display = d

        if target_display is None:
            # Auto-detect strategy (Improvement 10):
            # 1. If region specified, find display containing region center
            # 2. Else, find display containing cursor position
            # 3. Else, use main display
            if region:
                cx = region["x"] + region["width"] / 2
                cy = region["y"] + region["height"] / 2
                target_display = _find_display_for_point(cx, cy)
            else:
                # Try cursor position first
                cursor = _get_cursor_position()
                if cursor.get("success"):
                    target_display = _find_display_for_point(cursor["x"], cursor["y"])
                # Fallback to main display
                if target_display is None:
                    target_display = main_display or info["displays"][0]

        if target_display is None:
            return {"success": False, "error": "No display found"}

        disp_id = target_display["display_id"]
        disp_origin = target_display["origin"]
        disp_size = target_display["size"]

        # Capture using Quartz API (no screencapture -D index needed)
        if region:
            # Convert global logical coords to display-local logical coords
            local_x = region["x"] - disp_origin["x"]
            local_y = region["y"] - disp_origin["y"]
            # Clamp to display bounds
            local_x = max(0, min(local_x, disp_size["width"]))
            local_y = max(0, min(local_y, disp_size["height"]))
            rect = CGRectMake(local_x, local_y, region["width"], region["height"])
            cg_image = CGDisplayCreateImageForRect(disp_id, rect)
        else:
            cg_image = CGDisplayCreateImage(disp_id)

        if cg_image is None:
            return {"success": False, "error": "CGDisplayCreateImage returned None"}

        img_data, orig_w, orig_h = _cgimage_to_jpeg(cg_image)

        b64 = base64.b64encode(img_data).decode("ascii")

        return {
            "success": True,
            "path": path,
            "width": orig_w,
            "height": orig_h,
            "image_base64": b64,
            "image_mimetype": "image/jpeg",
            "image_size_bytes": len(img_data),
            "coordinate_system": "logical_points",
            "display": {
                "id": disp_id,
                "is_main": target_display["is_main"],
                "origin": disp_origin,
                "logical_size": disp_size,
            },
            "note": "Mouse coordinates use global logical points. Display origin offset applies for non-main displays.",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# Mouse operations (CGEvent in subprocess — isolated from main process)
# ============================================================

_PYTHON_PATH = "/Users/houtao/Library/Application Support/TRAE SOLO CN/ModularData/ai-agent/vm/tools/opt/python@3.10/3.10.20_3/libexec/lib/python3.10/site-packages"


def _mouse_click(x, y, button="left", clicks=1) -> dict:
    """Click mouse at (x, y) using CGEvent in an isolated subprocess."""
    try:
        valid, err, display = _validate_coordinates(x, y, "click")
        if not valid:
            return {"success": False, "error": err, "x": x, "y": y}

        btn_str = button
        script = f'''
import sys
sys.path.insert(0, "{_PYTHON_PATH}")
from Quartz import CGEventCreateMouseEvent, CGEventPost, kCGHIDEventTap
from Quartz import kCGEventLeftMouseDown, kCGEventLeftMouseUp, kCGEventMouseMoved
from Quartz import kCGEventRightMouseDown, kCGEventRightMouseUp
from Quartz import kCGEventOtherMouseDown, kCGEventOtherMouseUp
from Quartz import kCGMouseButtonLeft, kCGMouseButtonRight, kCGMouseButtonCenter
import time

x, y = {x}, {y}
button = "{btn_str}"
clicks = {clicks}

if button == "left":
    btn = kCGMouseButtonLeft
    down_t = kCGEventLeftMouseDown
    up_t = kCGEventLeftMouseUp
elif button == "right":
    btn = kCGMouseButtonRight
    down_t = kCGEventRightMouseDown
    up_t = kCGEventRightMouseUp
else:
    btn = kCGMouseButtonCenter
    down_t = kCGEventOtherMouseDown
    up_t = kCGEventOtherMouseUp

e = CGEventCreateMouseEvent(None, kCGEventMouseMoved, (x, y), btn)
CGEventPost(kCGHIDEventTap, e)
time.sleep(0.03)

for _ in range(clicks):
    d = CGEventCreateMouseEvent(None, down_t, (x, y), btn)
    CGEventPost(kCGHIDEventTap, d)
    time.sleep(0.02)
    u = CGEventCreateMouseEvent(None, up_t, (x, y), btn)
    CGEventPost(kCGHIDEventTap, u)
    time.sleep(0.05)

print("click done")
'''
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return {"success": True, "x": x, "y": y, "button": button, "clicks": clicks,
                    "display": {"id": display["display_id"], "is_main": display["is_main"]}}
        else:
            return {"success": False, "error": f"subprocess exit {result.returncode}: {result.stderr[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _mouse_drag(start_x, start_y, end_x, end_y, duration=0.5, button="left") -> dict:
    """Drag mouse using CGEvent in subprocess. Supports left/right/middle button."""
    try:
        valid_s, err_s, disp_s = _validate_coordinates(start_x, start_y, "drag_start")
        if not valid_s:
            return {"success": False, "error": f"Start point invalid: {err_s}"}
        valid_e, err_e, disp_e = _validate_coordinates(end_x, end_y, "drag_end")
        if not valid_e:
            return {"success": False, "error": f"End point invalid: {err_e}"}

        btn_str = button
        script = f'''
import sys
sys.path.insert(0, "{_PYTHON_PATH}")
from Quartz import CGEventCreateMouseEvent, CGEventPost, kCGHIDEventTap
from Quartz import kCGEventLeftMouseDown, kCGEventLeftMouseUp, kCGEventLeftMouseDragged
from Quartz import kCGEventRightMouseDown, kCGEventRightMouseUp, kCGEventRightMouseDragged
from Quartz import kCGEventOtherMouseDown, kCGEventOtherMouseUp, kCGEventOtherMouseDragged
from Quartz import kCGMouseButtonLeft, kCGMouseButtonRight, kCGMouseButtonCenter
import time

sx, sy, ex, ey = {start_x}, {start_y}, {end_x}, {end_y}
duration = {duration}
button = "{btn_str}"

if button == "left":
    btn = kCGMouseButtonLeft
    down_t = kCGEventLeftMouseDown
    up_t = kCGEventLeftMouseUp
    drag_t = kCGEventLeftMouseDragged
elif button == "right":
    btn = kCGMouseButtonRight
    down_t = kCGEventRightMouseDown
    up_t = kCGEventRightMouseUp
    drag_t = kCGEventRightMouseDragged
else:
    btn = kCGMouseButtonCenter
    down_t = kCGEventOtherMouseDown
    up_t = kCGEventOtherMouseUp
    drag_t = kCGEventOtherMouseDragged

down = CGEventCreateMouseEvent(None, down_t, (sx, sy), btn)
CGEventPost(kCGHIDEventTap, down)
time.sleep(0.05)

steps = max(int(duration / 0.016), 1)
for i in range(1, steps + 1):
    t = i / steps
    cx = sx + (ex - sx) * t
    cy = sy + (ey - sy) * t
    drag = CGEventCreateMouseEvent(None, drag_t, (cx, cy), btn)
    CGEventPost(kCGHIDEventTap, drag)
    time.sleep(duration / steps)

up = CGEventCreateMouseEvent(None, up_t, (ex, ey), btn)
CGEventPost(kCGHIDEventTap, up)
print("drag done")
'''
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return {"success": True, "from": [start_x, start_y], "to": [end_x, end_y],
                    "button": button,
                    "start_display": {"id": disp_s["display_id"], "is_main": disp_s["is_main"]},
                    "end_display": {"id": disp_e["display_id"], "is_main": disp_e["is_main"]}}
        else:
            return {"success": False, "error": f"subprocess exit {result.returncode}: {result.stderr[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _mouse_scroll(x, y, scroll_x=0, scroll_y=3) -> dict:
    """Scroll using CGEvent in subprocess. Supports both vertical and horizontal scrolling.

    Args:
        x, y: Mouse position (global logical points)
        scroll_x: Horizontal scroll amount (positive=right, negative=left)
        scroll_y: Vertical scroll amount (positive=up, negative=down)
    """
    try:
        valid, err, display = _validate_coordinates(x, y, "scroll")
        if not valid:
            return {"success": False, "error": err, "x": x, "y": y}

        has_horizontal = scroll_x != 0
        has_vertical = scroll_y != 0

        v_amount = abs(scroll_y) if has_vertical else 0
        v_direction = 1 if scroll_y > 0 else -1
        h_amount = abs(scroll_x) if has_horizontal else 0
        h_direction = 1 if scroll_x > 0 else -1

        script = f'''
import sys
sys.path.insert(0, "{_PYTHON_PATH}")
from Quartz import (
    CGEventCreateMouseEvent, CGEventPost, kCGHIDEventTap,
    CGEventCreateScrollWheelEvent2, kCGScrollEventUnitLine,
    kCGMouseButtonLeft, kCGEventMouseMoved
)
import time

x, y = {x}, {y}
v_amount = {v_amount}
v_direction = {v_direction}
h_amount = {h_amount}
h_direction = {h_direction}
has_vertical = {str(has_vertical)}
has_horizontal = {str(has_horizontal)}

# Move cursor to position first
e = CGEventCreateMouseEvent(None, kCGEventMouseMoved, (x, y), kCGMouseButtonLeft)
CGEventPost(kCGHIDEventTap, e)
time.sleep(0.02)

max_iter = max(v_amount, h_amount, 1)
for i in range(max_iter):
    v_val = 0
    h_val = 0
    if has_vertical and i < v_amount:
        v_val = v_direction
    if has_horizontal and i < h_amount:
        h_val = h_direction

    if has_horizontal:
        s = CGEventCreateScrollWheelEvent2(None, kCGScrollEventUnitLine, 2, v_val, h_val, 0)
    else:
        s = CGEventCreateScrollWheelEvent2(None, kCGScrollEventUnitLine, 1, v_val, 0, 0)
    CGEventPost(kCGHIDEventTap, s)
    time.sleep(0.02)

print("scroll done")
'''
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return {"success": True, "x": x, "y": y, "scroll_x": scroll_x, "scroll_y": scroll_y,
                    "display": {"id": display["display_id"], "is_main": display["is_main"]}}
        else:
            return {"success": False, "error": f"subprocess exit {result.returncode}: {result.stderr[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _mouse_move(x, y) -> dict:
    """Move mouse using CGEvent in subprocess."""
    try:
        valid, err, display = _validate_coordinates(x, y, "move")
        if not valid:
            return {"success": False, "error": err, "x": x, "y": y}

        script = f'''
import sys
sys.path.insert(0, "{_PYTHON_PATH}")
from Quartz import CGEventCreateMouseEvent, CGEventPost, kCGHIDEventTap, kCGEventMouseMoved, kCGMouseButtonLeft
e = CGEventCreateMouseEvent(None, kCGEventMouseMoved, ({x}, {y}), kCGMouseButtonLeft)
CGEventPost(kCGHIDEventTap, e)
print("move done")
'''
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return {"success": True, "x": x, "y": y,
                    "display": {"id": display["display_id"], "is_main": display["is_main"]}}
        else:
            return {"success": False, "error": f"subprocess exit {result.returncode}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get_cursor_position() -> dict:
    """Get cursor position using CGEvent in subprocess."""
    try:
        script = f'''
import sys
sys.path.insert(0, "{_PYTHON_PATH}")
from Quartz import CGEventCreate, CGEventGetLocation
e = CGEventCreate(None)
loc = CGEventGetLocation(e)
print(f"{{loc.x}},{{loc.y}}")
'''
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            x = float(parts[0])
            y = float(parts[1])
            # Determine which display the cursor is on
            display = _find_display_for_point(x, y)
            return {
                "success": True,
                "x": x,
                "y": y,
                "display": {
                    "id": display["display_id"],
                    "is_main": display["is_main"],
                    "origin": display["origin"],
                    "size": display["size"],
                } if display else None,
            }
        else:
            return {"success": False, "error": f"subprocess exit {result.returncode}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# Keyboard operations (AppleScript-based)
# ============================================================

def _key_code_for_char(char: str) -> int:
    key_map = {
        'a': 0, 'b': 11, 'c': 8, 'd': 2, 'e': 14, 'f': 3, 'g': 5, 'h': 4,
        'i': 34, 'j': 38, 'k': 40, 'l': 37, 'm': 46, 'n': 45, 'o': 31,
        'p': 35, 'q': 12, 'r': 15, 's': 1, 't': 17, 'u': 32, 'v': 9,
        'w': 13, 'x': 7, 'y': 16, 'z': 6,
        '0': 29, '1': 18, '2': 19, '3': 20, '4': 21, '5': 23, '6': 22,
        '7': 26, '8': 25, '9': 28,
        ' ': 49, '\n': 36, '\t': 48, '\r': 36,
        '-': 27, '=': 24, '[': 33, ']': 30, '\\': 42,
        ';': 41, "'": 39, '`': 50, ',': 43, '.': 47, '/': 44,
    }
    char_lower = char.lower()
    if char_lower in key_map:
        return key_map[char_lower]
    return -1


def _keyboard_type(text: str) -> dict:
    """Type text using AppleScript.
    For non-ASCII text (Chinese, etc.), uses clipboard + Command+V paste."""
    try:
        has_non_ascii = any(ord(c) > 127 for c in text)

        if has_non_ascii:
            # Set clipboard using AppleScript, then paste
            escaped = _escape_as_string(text)
            set_clip_script = f'set the clipboard to "{escaped}"'
            ok, err = _run_applescript(set_clip_script, timeout=5)
            if not ok:
                return {"success": False, "error": f"Failed to set clipboard: {err}"}

            time.sleep(0.1)

            # Paste using Command+V
            paste_script = 'tell application "System Events" to keystroke "v" using command down'
            ok, err = _run_applescript(paste_script, timeout=5)
            if not ok:
                return {"success": False, "error": f"Failed to paste: {err}"}

            return {"success": True, "text": text, "method": "clipboard_paste"}
        else:
            escaped = _escape_as_string(text)
            script = f'tell application "System Events" to keystroke "{escaped}"'
            ok, err = _run_applescript(script, timeout=15)
            if not ok:
                return {"success": False, "error": err[:200]}
            return {"success": True, "text": text, "method": "keystroke"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _keyboard_key(key: str, down=True) -> dict:
    """Press a key using AppleScript."""
    try:
        applescript_keycodes = {
            "return": 36, "enter": 36, "tab": 48, "escape": 53, "esc": 53,
            "delete": 51, "backspace": 51, "space": 49,
            "up": 126, "down": 125, "left": 123, "right": 124,
            "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
            "forward_delete": 117,
            "f1": 122, "f2": 120, "f3": 99, "f4": 118,
            "f5": 96, "f6": 97, "f7": 98, "f8": 100,
            "f9": 101, "f10": 109, "f11": 103, "f12": 111,
            "command": 55, "cmd": 55, "shift": 56,
            "control": 59, "option": 58, "caps_lock": 57,
            "+": 24, "=": 24, "-": 27, "/": 44, "*": 28,
            ".": 47, ",": 43, "[": 33, "]": 30,
        }
        key_lower = key.lower().strip()

        if key_lower in applescript_keycodes:
            keycode = applescript_keycodes[key_lower]
            script = f'tell application "System Events" to key code {keycode}'
        else:
            escaped = _escape_as_string(key)
            script = f'tell application "System Events" to keystroke "{escaped}"'

        ok, err = _run_applescript(script, timeout=10)
        if not ok:
            return {"success": False, "error": err[:200]}
        return {"success": True, "key": key, "action": "down" if down else "up"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _keyboard_hotkey(keys: list[str], hold_time=0.1) -> dict:
    """Press key combination using AppleScript."""
    try:
        applescript_keycodes = {
            "return": 36, "enter": 36, "tab": 48, "escape": 53, "esc": 53,
            "delete": 51, "space": 49,
            "up": 126, "down": 125, "left": 123, "right": 124,
            "command": 55, "cmd": 55, "shift": 56,
            "control": 59, "option": 58,
            "+": 24, "=": 24, "-": 27, "/": 44, "*": 28,
        }
        key_codes = []
        modifiers = []
        for key in keys:
            key_lower = key.lower().strip()
            if key_lower in {"command", "cmd", "shift", "control", "option"}:
                mod_map = {"command": "command down", "cmd": "command down",
                           "shift": "shift down", "control": "control down",
                           "option": "option down"}
                modifiers.append(mod_map[key_lower])
            elif key_lower in applescript_keycodes:
                key_codes.append(applescript_keycodes[key_lower])
            else:
                kc = _key_code_for_char(key)
                if kc >= 0:
                    key_codes.append(kc)
                else:
                    return {"success": False, "error": f"Unknown key: {key}"}

        if not key_codes:
            return {"success": False, "error": "No non-modifier key specified"}

        mod_str = ", ".join(modifiers)
        script = f'tell application "System Events" to key code {key_codes[0]}'
        if mod_str:
            script += f' using {{{mod_str}}}'

        ok, err = _run_applescript(script, timeout=10)
        if not ok:
            return {"success": False, "error": err[:200]}
        return {"success": True, "keys": keys}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# AppleScript-based UI operations (NEW in v3)
# ============================================================

def _run_arbitrary_applescript(script: str) -> dict:
    """Run arbitrary AppleScript. Returns output or error."""
    try:
        ok, out = _run_applescript_file(script, timeout=30)
        if ok:
            return {"success": True, "output": out}
        else:
            return {"success": False, "error": out[:500]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _click_ui_element(app_name: str, element_role: str, element_name: str,
                      window_index: int = 1, parent_path: str = "") -> dict:
    """Click a UI element by role and name using AppleScript System Events."""
    try:
        escaped_app = _escape_as_string(app_name)
        escaped_name = _escape_as_string(element_name)
        escaped_role = element_role.strip().lower()

        if parent_path:
            target_str = f'{escaped_role} "{escaped_name}" of {parent_path} of window {window_index}'
        else:
            target_str = f'{escaped_role} "{escaped_name}" of window {window_index}'

        script = f'''
tell application "System Events"
    set procList to every process whose name contains "{escaped_app}" or displayed name contains "{escaped_app}"
    if (count of procList) is 0 then
        return "error: process not found"
    end if
    set targetProc to item 1 of procList
    tell targetProc
        if (count of windows) is 0 then
            return "error: no windows"
        end if
        try
            set targetElement to {target_str}
            click targetElement
            return "clicked"
        on error errMsg
            return "error: " & errMsg
        end try
    end tell
end tell
'''
        ok, out = _run_applescript_file(script, timeout=10)
        if ok:
            if "clicked" in out:
                return {"success": True, "app": app_name, "element": element_name, "role": element_role}
            elif out.startswith("error:"):
                return {"success": False, "error": out}
            else:
                return {"success": True, "output": out}
        else:
            return {"success": False, "error": out[:500]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get_ui_elements(app_name: str = "", window_index: int = 1, depth: int = 2) -> dict:
    """Get UI element tree of an application's window using AppleScript.
    Uses a simple non-recursive approach to avoid AppleScript handler issues."""
    try:
        if app_name:
            escaped_app = _escape_as_string(app_name)
            proc_clause = f'set procList to every process whose name contains "{escaped_app}" or displayed name contains "{escaped_app}"'
        else:
            proc_clause = "set procList to every process whose frontmost is true"

        # Use a simple inline approach without separate handler
        max_depth = min(depth, 3)
        script = f"""tell application "System Events"
    {proc_clause}
    if (count of procList) is 0 then
        return "error: process not found"
    end if
    set targetProc to item 1 of procList
    set procName to name of targetProc
    tell targetProc
        if (count of windows) is 0 then
            return "error: no windows for " & procName
        end if
        set targetWindow to window {window_index}
        set winTitle to ""
        try
            set winTitle to title of targetWindow
        end try
        set output to "Process: " & procName & " | Window: " & winTitle & return
        set elemList to UI elements of targetWindow
        repeat with elem in elemList
            set elemClass to class of elem as text
            set elemName to ""
            set elemDesc to ""
            set elemRole to ""
            set elemValue to ""
            try
                set elemName to name of elem
            end try
            try
                set elemDesc to description of elem
            end try
            try
                set elemRole to role of elem
            end try
            try
                set elemValue to value of elem
            end try
            set output to output & elemClass & " | name=" & elemName & " | desc=" & elemDesc & " | role=" & elemRole & " | value=" & elemValue & return
        end repeat
        return output
    end tell
end tell"""
        ok, out = _run_applescript_file(script, timeout=15)
        if ok:
            return {"success": True, "elements": out}
        else:
            return {"success": False, "error": out[:500]}
    except Exception as e:
        return {"success": False, "error": str(e)}



def _select_menu_item(app_name: str, menu_name: str, menu_item_name: str) -> dict:
    """Select a menu item from the menu bar using AppleScript."""
    try:
        escaped_app = _escape_as_string(app_name)
        escaped_menu = _escape_as_string(menu_name)
        escaped_item = _escape_as_string(menu_item_name)

        script = f'''
tell application "System Events"
    set procList to every process whose name contains "{escaped_app}" or displayed name contains "{escaped_app}"
    if (count of procList) is 0 then
        return "error: process not found"
    end if
    tell item 1 of procList
        click menu bar item "{escaped_menu}" of menu bar 1
        delay 0.3
        click menu item "{escaped_item}" of menu "{escaped_menu}" of menu bar item "{escaped_menu}" of menu bar 1
        return "clicked"
    end tell
end tell
'''
        ok, out = _run_applescript_file(script, timeout=10)
        if ok and "clicked" in out:
            return {"success": True, "app": app_name, "menu": menu_name, "item": menu_item_name}
        else:
            return {"success": False, "error": out[:500]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# Window/App operations (AppleScript-first)
# ============================================================

def _list_windows() -> dict:
    """List visible windows using Quartz (read-only, safe). Includes display info."""
    try:
        display_info = _get_display_info()
        window_list = CGWindowListCopyWindowInfo(
            kCGWindowListOptionOnScreenOnly | kCGWindowListOptionAll, kCGNullWindowID
        )
        windows = []
        for i in range(len(window_list)):
            w = window_list[i]
            layer = w.get(kCGWindowLayer, -1)
            if layer != 0:
                continue
            owner = w.get(kCGWindowOwnerName, "")
            name = w.get(kCGWindowName, "")
            win_id = w.get(kCGWindowNumber, 0)
            bounds = w.get(kCGWindowBounds, {})
            bounds_dict = {
                "x": bounds.get("X", 0), "y": bounds.get("Y", 0),
                "width": bounds.get("Width", 0), "height": bounds.get("Height", 0),
            } if bounds else None

            # Determine which display the window is on (by center point)
            display_id = None
            on_main_display = None
            if bounds_dict and bounds_dict["width"] > 0 and bounds_dict["height"] > 0:
                center_x = bounds_dict["x"] + bounds_dict["width"] / 2
                center_y = bounds_dict["y"] + bounds_dict["height"] / 2
                win_display = _find_display_for_point(center_x, center_y)
                if win_display:
                    display_id = win_display["display_id"]
                    on_main_display = win_display["is_main"]

            windows.append({
                "id": win_id, "app": owner,
                "title": name if name else "(untitled)",
                "bounds": bounds_dict,
                "display_id": display_id,
                "on_main_display": on_main_display,
            })
        return {"success": True, "windows": windows, "displays": display_info.get("displays", [])}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _activate_app(app_name: str) -> dict:
    """Activate application using AppleScript System Events."""
    try:
        escaped = _escape_as_string(app_name)
        script = f'''
tell application "System Events"
    set procList to every process whose name contains "{escaped}" or displayed name contains "{escaped}"
    if (count of procList) > 0 then
        set targetProc to item 1 of procList
        set frontmost of targetProc to true
        set procName to name of targetProc
        return procName
    else
        return "NOT_FOUND"
    end if
end tell
'''
        ok, out = _run_applescript(script, timeout=5)
        if ok and out != "NOT_FOUND":
            time.sleep(0.3)
            return {"success": True, "app": out}
        elif ok and out == "NOT_FOUND":
            result = subprocess.run(["open", "-a", app_name], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                time.sleep(1)
                return {"success": True, "app": app_name, "opened": True}
            return {"success": False, "error": f"Application not found: {app_name}"}
        else:
            from AppKit import NSWorkspace, NSApplicationActivateIgnoringOtherApps
            workspace = NSWorkspace.sharedWorkspace()
            apps = workspace.runningApplications()
            target = None
            for a in apps:
                if app_name.lower() in a.localizedName().lower():
                    target = a
                    break
            if not target:
                return {"success": False, "error": f"Application not found: {app_name}"}
            target.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
            time.sleep(0.3)
            return {"success": True, "app": target.localizedName(), "pid": target.processIdentifier()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get_screen_size() -> dict:
    """Get screen size info for all displays."""
    try:
        info = _get_display_info()
        if not info["displays"]:
            return {"success": False, "error": "No displays found"}

        main_display = next((d for d in info["displays"] if d["is_main"]), info["displays"][0])

        # Calculate total virtual desktop bounds
        min_x = min(d["origin"]["x"] for d in info["displays"])
        min_y = min(d["origin"]["y"] for d in info["displays"])
        max_x = max(d["origin"]["x"] + d["size"]["width"] for d in info["displays"])
        max_y = max(d["origin"]["y"] + d["size"]["height"] for d in info["displays"])

        return {
            "success": True,
            # Backward compat: main display width/height at top level
            "width": main_display["size"]["width"],
            "height": main_display["size"]["height"],
            # Complete display info
            "main_display": {
                "id": main_display["display_id"],
                "width": main_display["size"]["width"],
                "height": main_display["size"]["height"],
                "origin": main_display["origin"],
            },
            "displays": [
                {
                    "id": d["display_id"],
                    "is_main": d["is_main"],
                    "width": d["size"]["width"],
                    "height": d["size"]["height"],
                    "origin": d["origin"],
                }
                for d in info["displays"]
            ],
            "virtual_desktop": {
                "min_x": min_x,
                "min_y": min_y,
                "max_x": max_x,
                "max_y": max_y,
                "total_width": max_x - min_x,
                "total_height": max_y - min_y,
            },
            "display_count": len(info["displays"]),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get_displays() -> dict:
    """Get detailed information about all displays."""
    try:
        info = _get_display_info()
        if not info["displays"]:
            return {"success": False, "error": "No displays found"}

        displays = []
        for d in info["displays"]:
            displays.append({
                "id": d["display_id"],
                "is_main": d["is_main"],
                "origin": d["origin"],
                "size": d["size"],
                "bounds": {
                    "x_min": d["origin"]["x"],
                    "y_min": d["origin"]["y"],
                    "x_max": d["origin"]["x"] + d["size"]["width"],
                    "y_max": d["origin"]["y"] + d["size"]["height"],
                },
            })

        min_x = min(d["origin"]["x"] for d in info["displays"])
        min_y = min(d["origin"]["y"] for d in info["displays"])
        max_x = max(d["origin"]["x"] + d["size"]["width"] for d in info["displays"])
        max_y = max(d["origin"]["y"] + d["size"]["height"] for d in info["displays"])

        return {
            "success": True,
            "displays": displays,
            "main_display_id": info["main_display_id"],
            "display_count": len(displays),
            "virtual_desktop": {
                "min_x": min_x,
                "min_y": min_y,
                "max_x": max_x,
                "max_y": max_y,
                "total_width": max_x - min_x,
                "total_height": max_y - min_y,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _open_app(name_or_path: str) -> dict:
    try:
        if name_or_path.startswith("/"):
            cmd = ["open", name_or_path]
        else:
            cmd = ["open", "-a", name_or_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip()}
        return {"success": True, "app": name_or_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# Clipboard operations (AppleScript-based)
# ============================================================

def _clipboard_get() -> dict:
    try:
        script = 'try\nreturn the clipboard as text\non error\nreturn ""\nend try'
        ok, out = _run_applescript(script, timeout=5)
        if ok:
            return {"success": True, "text": out}
        else:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
            return {"success": True, "text": result.stdout}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _clipboard_set(text: str) -> dict:
    try:
        escaped = _escape_as_string(text)
        script = f'set the clipboard to "{escaped}"'
        ok, err = _run_applescript(script, timeout=5)
        if ok:
            return {"success": True, "text": text}
        else:
            result = subprocess.run(["pbcopy"], input=text, text=True, timeout=5)
            if result.returncode == 0:
                return {"success": True, "text": text}
            return {"success": False, "error": err[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# Tool definitions
# ============================================================

TOOL_DEFS = [
    types.Tool(
        name="screenshot",
        description="截取屏幕截图。display_id=0时自动检测目标显示器：有region时按region中心点定位，否则按光标位置定位。返回高质量JPEG图片和显示器坐标信息。坐标系统为全局逻辑点（与鼠标点击坐标一致）。支持多显示器。",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "截图保存路径（可选）。默认 /tmp/computer_use_screenshot.png"},
                "region": {
                    "type": "object",
                    "description": "截取指定屏幕区域（可选）。坐标为逻辑点，与鼠标坐标一致。",
                    "properties": {
                        "x": {"type": "number"}, "y": {"type": "number"},
                        "width": {"type": "number"}, "height": {"type": "number"},
                    },
                    "required": ["x", "y", "width", "height"],
                },
                "display_id": {"type": "integer", "description": "指定截图的显示器ID（可选）。0=自动检测。"},
            },
        },
    ),
    types.Tool(
        name="mouse_click",
        description="在指定屏幕坐标点击鼠标。坐标使用全局逻辑点坐标系：原点(0,0)为主显示器左上角，副显示器可能有负坐标偏移。使用get_displays或get_cursor_position查看显示器布局。支持左键、右键、中键，支持单击和双击。",
        inputSchema={
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "X 坐标（全局逻辑点，主显示器左上角为0）"},
                "y": {"type": "number", "description": "Y 坐标（全局逻辑点，主显示器左上角为0）"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "默认 left"},
                "clicks": {"type": "integer", "description": "点击次数，默认 1"},
            },
            "required": ["x", "y"],
        },
    ),
    types.Tool(
        name="mouse_drag",
        description="从起始坐标拖拽鼠标到目标坐标。坐标使用全局逻辑点坐标系（与mouse_click相同）。用于选择文本、移动窗口等操作。支持左键、右键、中键拖拽。",
        inputSchema={
            "type": "object",
            "properties": {
                "start_x": {"type": "number", "description": "起始X坐标（全局逻辑点）"},
                "start_y": {"type": "number", "description": "起始Y坐标（全局逻辑点）"},
                "end_x": {"type": "number", "description": "目标X坐标（全局逻辑点）"},
                "end_y": {"type": "number", "description": "目标Y坐标（全局逻辑点）"},
                "duration": {"type": "number", "description": "拖拽持续时间（秒），默认 0.5"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "默认 left"},
            },
            "required": ["start_x", "start_y", "end_x", "end_y"],
        },
    ),
    types.Tool(
        name="mouse_scroll",
        description="在指定位置滚动鼠标滚轮。支持垂直和水平滚动。坐标使用全局逻辑点坐标系。正值scroll_y向上滚动，正值scroll_x向右滚动。",
        inputSchema={
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "X坐标（全局逻辑点）"},
                "y": {"type": "number", "description": "Y坐标（全局逻辑点）"},
                "scroll_y": {"type": "number", "description": "垂直滚动量（正=上，负=下），默认 3"},
                "scroll_x": {"type": "number", "description": "水平滚动量（正=右，负=左），默认 0"},
            },
            "required": ["x", "y"],
        },
    ),
    types.Tool(
        name="mouse_move",
        description="移动鼠标光标到指定坐标（不点击）。坐标使用全局逻辑点坐标系。",
        inputSchema={
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "X坐标（全局逻辑点）"},
                "y": {"type": "number", "description": "Y坐标（全局逻辑点）"},
            },
            "required": ["x", "y"],
        },
    ),
    types.Tool(
        name="get_cursor_position",
        description="获取当前鼠标光标位置，包含所在显示器信息（display_id, origin, size, is_main）。",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="keyboard_type",
        description="输入文本。ASCII文本用keystroke，中文等非ASCII文本自动用剪贴板粘贴（Command+V）。",
        inputSchema={
            "type": "object",
            "properties": {"text": {"type": "string", "description": "要输入的文本"}},
            "required": ["text"],
        },
    ),
    types.Tool(
        name="keyboard_key",
        description="按下指定按键。支持：return, tab, escape, delete, space, up, down, left, right, f1-f12, command, shift, control, option。",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "按键名称"},
                "action": {"type": "string", "enum": ["down", "up"], "description": "默认 down"},
            },
            "required": ["key"],
        },
    ),
    types.Tool(
        name="keyboard_hotkey",
        description="同时按下多个按键组合（快捷键）。例如 [\"command\", \"c\"]。",
        inputSchema={
            "type": "object",
            "properties": {
                "keys": {"type": "array", "items": {"type": "string"}, "description": "按键列表"},
            },
            "required": ["keys"],
        },
    ),
    types.Tool(
        name="run_applescript",
        description="运行任意AppleScript脚本。可控制任何应用、点击UI元素、读取界面信息等。充分发挥AppleScript的能力。",
        inputSchema={
            "type": "object",
            "properties": {
                "script": {"type": "string", "description": "AppleScript脚本内容"},
            },
            "required": ["script"],
        },
    ),
    types.Tool(
        name="click_ui_element",
        description="通过AppleScript点击指定应用窗口中的UI元素。比坐标点击更精确。element_role: button, text field, checkbox, pop up button, radio button等。",
        inputSchema={
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "应用名称"},
                "element_role": {"type": "string", "description": "元素类型，如 button, text field, checkbox"},
                "element_name": {"type": "string", "description": "元素名称"},
                "window_index": {"type": "integer", "description": "窗口序号，默认 1"},
                "parent_path": {"type": "string", "description": "父元素路径（可选），如 group 1 of group 2"},
            },
            "required": ["app_name", "element_role", "element_name"],
        },
    ),
    types.Tool(
        name="get_ui_elements",
        description="通过AppleScript获取应用窗口的UI元素树。用于了解界面结构，找到可点击的元素。",
        inputSchema={
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "应用名称（可选，默认为当前最前应用）"},
                "window_index": {"type": "integer", "description": "窗口序号，默认 1"},
                "depth": {"type": "integer", "description": "遍历深度，默认 2"},
            },
        },
    ),
    types.Tool(
        name="select_menu_item",
        description="通过AppleScript选择菜单栏项。例如 select_menu_item('Safari', 'File', 'New Window')。",
        inputSchema={
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "应用名称"},
                "menu_name": {"type": "string", "description": "菜单名称，如 File, Edit, View"},
                "menu_item_name": {"type": "string", "description": "菜单项名称"},
            },
            "required": ["app_name", "menu_name", "menu_item_name"],
        },
    ),
    types.Tool(
        name="list_windows",
        description="列出屏幕上所有可见窗口，包括应用名称、窗口标题、位置(bounds)和所在显示器(display_id)。可用此工具确定窗口在哪个显示器上。",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="activate_app",
        description="激活并前置显示指定应用程序。如果应用未运行则尝试打开。",
        inputSchema={
            "type": "object",
            "properties": {"app_name": {"type": "string", "description": "应用名称（模糊匹配）"}},
            "required": ["app_name"],
        },
    ),
    types.Tool(
        name="open_app",
        description="启动一个应用程序。支持应用名称或路径。",
        inputSchema={
            "type": "object",
            "properties": {"name_or_path": {"type": "string", "description": "应用名称或完整路径"}},
            "required": ["name_or_path"],
        },
    ),
    types.Tool(
        name="get_screen_size",
        description="获取所有显示器信息。返回主显示器分辨率（向后兼容）、各显示器详情（含origin偏移）和虚拟桌面总范围。多显示器下副显示器可能有负坐标origin。",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="get_displays",
        description="获取所有显示器的详细信息。返回每个显示器的display_id、origin（在全局坐标系中的偏移）、size（逻辑分辨率）、is_main标志和bounds。多显示器操作前应先调用此工具了解布局。",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="clipboard_get",
        description="读取系统剪贴板中的文本内容。",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="clipboard_set",
        description="设置系统剪贴板的文本内容。",
        inputSchema={
            "type": "object",
            "properties": {"text": {"type": "string", "description": "要复制到剪贴板的文本"}},
            "required": ["text"],
        },
    ),
]


def _execute_tool(name: str, arguments: dict) -> dict:
    """Execute a tool and return the result dict."""
    dispatch = {
        "screenshot": lambda: _screenshot(
            path=arguments.get("path", "/tmp/computer_use_screenshot.png"),
            region=arguments.get("region"),
            display_id=arguments.get("display_id", 0),
        ),
        "mouse_click": lambda: _mouse_click(
            arguments["x"], arguments["y"],
            arguments.get("button", "left"), arguments.get("clicks", 1),
        ),
        "mouse_drag": lambda: _mouse_drag(
            arguments["start_x"], arguments["start_y"],
            arguments["end_x"], arguments["end_y"],
            arguments.get("duration", 0.5), arguments.get("button", "left"),
        ),
        "mouse_scroll": lambda: _mouse_scroll(
            arguments["x"], arguments["y"],
            arguments.get("scroll_x", 0), arguments.get("scroll_y", 3),
        ),
        "mouse_move": lambda: _mouse_move(arguments["x"], arguments["y"]),
        "get_cursor_position": lambda: _get_cursor_position(),
        "keyboard_type": lambda: _keyboard_type(arguments["text"]),
        "keyboard_key": lambda: _keyboard_key(
            arguments["key"], arguments.get("action", "down") == "down",
        ),
        "keyboard_hotkey": lambda: _keyboard_hotkey(arguments["keys"]),
        "run_applescript": lambda: _run_arbitrary_applescript(arguments["script"]),
        "click_ui_element": lambda: _click_ui_element(
            arguments["app_name"], arguments["element_role"], arguments["element_name"],
            arguments.get("window_index", 1), arguments.get("parent_path", ""),
        ),
        "get_ui_elements": lambda: _get_ui_elements(
            arguments.get("app_name", ""), arguments.get("window_index", 1),
            arguments.get("depth", 2),
        ),
        "select_menu_item": lambda: _select_menu_item(
            arguments["app_name"], arguments["menu_name"], arguments["menu_item_name"],
        ),
        "list_windows": lambda: _list_windows(),
        "activate_app": lambda: _activate_app(arguments["app_name"]),
        "open_app": lambda: _open_app(arguments["name_or_path"]),
        "get_screen_size": lambda: _get_screen_size(),
        "get_displays": lambda: _get_displays(),
        "clipboard_get": lambda: _clipboard_get(),
        "clipboard_set": lambda: _clipboard_set(arguments["text"]),
    }

    if name not in dispatch:
        return {"success": False, "error": f"未知工具: {name}"}

    return dispatch[name]()


# ============================================================
# MCP Server handlers
# ============================================================

async def _on_list_tools(
    ctx: ServerRequestContext, params: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOL_DEFS)


async def _on_call_tool(
    ctx: ServerRequestContext, params: types.CallToolRequestParams
) -> types.CallToolResult:
    name = params.name
    arguments = params.arguments or {}

    try:
        result = _execute_tool(name, arguments)
        is_error = not result.get("success", False)

        content = []

        # For screenshots: return text info + ImageContent
        if name == "screenshot" and result.get("success") and result.get("image_base64"):
            text_info = {
                "success": True,
                "path": result.get("path"),
                "width": result.get("width"),
                "height": result.get("height"),
                "image_size_bytes": result.get("image_size_bytes"),
            }
            content.append(types.TextContent(
                type="text",
                text=json.dumps(text_info, ensure_ascii=False, indent=2)
            ))
            content.append(types.ImageContent(
                type="image",
                data=result["image_base64"],
                mimeType=result.get("image_mimetype", "image/jpeg")
            ))
        else:
            content.append(types.TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2)
            ))

        return types.CallToolResult(
            content=content,
            is_error=is_error,
        )
    except Exception as e:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(
                {"success": False, "error": str(e)}, ensure_ascii=False
            ))],
            is_error=True,
        )


# Create server
app = Server(
    "mac-computer-use",
    version="3.0.0",
    description="macOS Computer Use v3 - AppleScript优先，全分辨率截图，UI元素操作",
    on_list_tools=_on_list_tools,
    on_call_tool=_on_call_tool,
)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    import signal

    def _handle_sigterm(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_sigterm)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        with open("/tmp/mcp_computer_use_error.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} FATAL: {e}\n")
        sys.exit(1)
