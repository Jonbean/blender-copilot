# SPDX-License-Identifier: GPL-3.0-or-later
"""
Blender Gemini Assistant - Viewport screenshot capture using bpy.
Captures the current 3D viewport (or camera view) to image bytes for the AI.
"""

import bpy
import tempfile
import os
import base64
from typing import Tuple


def _find_view3d_area():
    """Return the first VIEW_3D area in the current screen, or None."""
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            return area
    return None


def capture_viewport_to_bytes(width=1024, height=768) -> Tuple[bytes, str]:
    """
    Capture the 3D viewport as PNG image bytes and base64 string.
    Uses OpenGL render when a VIEW_3D area exists; otherwise renders from active camera.
    Returns (raw_bytes, base64_string). On failure returns (b"", "").
    """
    area = _find_view3d_area()
    scene = bpy.context.scene
    original_path = scene.render.filepath
    original_res_x = scene.render.resolution_x
    original_res_y = scene.render.resolution_y
    original_format = scene.render.image_settings.file_format
    path = None

    try:
        scene.render.resolution_x = width
        scene.render.resolution_y = height
        scene.render.image_settings.file_format = 'PNG'
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        scene.render.filepath = path

        if area:
            try:
                with bpy.context.temp_override(area=area):
                    bpy.ops.render.opengl(write_still=True)
            except Exception:
                # Fallback: render from active camera
                if scene.camera:
                    bpy.ops.render.opengl(write_still=True)
                else:
                    return (b"", "")
        else:
            if scene.camera:
                bpy.ops.render.opengl(write_still=True)
            else:
                return (b"", "")

        with open(path, "rb") as f:
            raw = f.read()
        return (raw, base64.b64encode(raw).decode("utf-8"))
    except Exception:
        return (b"", "")
    finally:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except Exception:
                pass
        scene.render.filepath = original_path
        scene.render.resolution_x = original_res_x
        scene.render.resolution_y = original_res_y
        scene.render.image_settings.file_format = original_format
