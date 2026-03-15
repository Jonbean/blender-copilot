# SPDX-License-Identifier: GPL-3.0-or-later
"""
Blender Gemini Assistant - Action execution (bpy-backed).
Implements select_object and move_object for the AI agent.
"""

import bpy


def list_objects():
    """Return list of object names in the current scene (for AI context)."""
    return [obj.name for obj in bpy.context.scene.objects]


def select_object(object_name: str) -> dict:
    """
    Select a single object by name. Clears current selection first.
    Returns {"ok": True} or {"ok": False, "error": "message"}.
    """
    if not object_name:
        return {"ok": False, "error": "object_name is required"}
    scene = bpy.context.scene
    if object_name not in scene.objects:
        return {"ok": False, "error": f"Object '{object_name}' not found in scene"}
    bpy.ops.object.select_all(action='DESELECT')
    scene.objects[object_name].select_set(True)
    bpy.context.view_layer.objects.active = scene.objects[object_name]
    return {"ok": True, "selected": object_name}


def move_object(object_name: str = None, x: float = None, y: float = None, z: float = None) -> dict:
    """
    Move an object by name. If object_name is omitted, moves the active object.
    x, y, z are deltas in scene units (floats). Omitted axes are left unchanged.
    Returns {"ok": True} or {"ok": False, "error": "message"}.
    """
    scene = bpy.context.scene
    obj = None
    if object_name:
        if object_name not in scene.objects:
            return {"ok": False, "error": f"Object '{object_name}' not found"}
        obj = scene.objects[object_name]
    else:
        obj = bpy.context.view_layer.objects.active
        if not obj:
            return {"ok": False, "error": "No active object and no object_name given"}
    if x is not None:
        obj.location.x += float(x)
    if y is not None:
        obj.location.y += float(y)
    if z is not None:
        obj.location.z += float(z)
    return {"ok": True, "moved": obj.name}
