# SPDX-License-Identifier: GPL-3.0-or-later
"""
Blender Gemini Assistant - Action execution (bpy-backed).
Implements select_object, move_object, and execute_bpy (arbitrary bpy operator) for the AI agent.
"""

import bpy

# Operators that are not allowed (safety: script execution, quit, etc.)
EXECUTE_BPY_BLOCKLIST = {
    "script.python_file_run",
    "script.reload",
    "wm.quit_blender",
    "wm.read_factory_settings",
    "wm.read_homefile",
    "preferences.addon_install",
    "preferences.addon_remove",
}


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


def execute_bpy(operator_idname: str, **kwargs) -> dict:
    """
    Run an arbitrary bpy.ops operator by idname (e.g. "object.origin_set", "mesh.primitive_cube_add").
    kwargs are passed as keyword arguments to the operator.
    Returns {"ok": True} or {"ok": False, "error": "message"} if the operator is blocked or fails.
    """
    if not operator_idname or "." not in operator_idname:
        return {"ok": False, "error": "operator must be a bpy.ops idname like 'object.origin_set'"}

    op_lower = operator_idname.strip().lower()
    if op_lower in EXECUTE_BPY_BLOCKLIST:
        return {"ok": False, "error": f"Operator '{operator_idname}' is not allowed for safety"}

    if op_lower.startswith("script."):
        return {"ok": False, "error": "Script operators are not allowed for safety"}

    parts = operator_idname.split(".", 1)
    if len(parts) != 2:
        return {"ok": False, "error": "operator must be 'category.operator_name'"}
    category, op_name = parts

    try:
        ops_module = getattr(bpy.ops, category, None)
        if ops_module is None:
            return {"ok": False, "error": f"Unknown bpy.ops category: '{category}'"}
        op_call = getattr(ops_module, op_name, None)
        if op_call is None:
            return {"ok": False, "error": f"Unknown operator: '{operator_idname}'"}
    except Exception as e:
        return {"ok": False, "error": f"Could not resolve operator: {e}"}

    # Normalize kwargs: JSON numbers are int/float; enums are usually strings
    try:
        result = op_call(**kwargs)
    except TypeError as e:
        return {"ok": False, "error": f"Invalid arguments for {operator_idname}: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"Not working: {e}"}

    if result == {"CANCELLED"}:
        return {"ok": False, "error": "Operator was cancelled or not available in this context"}
    return {"ok": True, "operator": operator_idname}
