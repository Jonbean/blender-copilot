# SPDX-License-Identifier: GPL-3.0-or-later
# Blender Gemini Assistant - AI-driven viewport control via Google Gemini

bl_info = {
    "name": "Gemini Assistant",
    "author": "Praugo",
    "description": "Control Blender with natural language using Google Gemini. Uses viewport screenshot and supports select/move object actions.",
    "blender": (4, 0, 0),
    "version": (1, 0, 0),
    "location": "View3D > Sidebar > Gemini Assistant",
    "category": "Interface",
}

import bpy
from . import viewport_capture
from . import gemini_client
from . import actions
from . import spell_codebook


def _update_response_lines(scene):
    """Sync scene['gemini_assistant_response'] text into scene.gemini_assistant_response_lines for scrollable UI."""
    lines_coll = scene.gemini_assistant_response_lines
    lines_coll.clear()
    text = scene.get("gemini_assistant_response") or ""
    for line in text.splitlines():
        item = lines_coll.add()
        item.text = line[:2000]  # per-line limit for storage


def execute_actions(action_list):
    """Run parsed actions through bpy (select_object, move_object, execute_bpy). Returns list of result strings."""
    results = []
    for item in action_list:
        name = (item or {}).get("name")
        args = (item or {}).get("args") or {}
        if name == "select_object":
            out = actions.select_object(args.get("object_name") or "")
            results.append(f"select_object({args}) -> {out}")
        elif name == "move_object":
            out = actions.move_object(
                object_name=args.get("object_name"),
                x=args.get("x"),
                y=args.get("y"),
                z=args.get("z"),
            )
            results.append(f"move_object({args}) -> {out}")
        elif name == "execute_bpy":
            args = args or {}
            operator_idname = args.get("operator") if isinstance(args, dict) else None
            kwargs = {k: v for k, v in args.items() if k != "operator"} if isinstance(args, dict) else {}
            if not operator_idname:
                out = {"ok": False, "error": "execute_bpy requires 'operator' (e.g. 'object.origin_set')"}
            else:
                out = actions.execute_bpy(operator_idname, **kwargs)
            results.append(f"execute_bpy({operator_idname}, {kwargs}) -> {out}")
        elif name == "shape_change_near_cursor":
            out = actions.shape_change_near_cursor()
            results.append(f"shape_change_near_cursor() -> {out}")
        else:
            results.append(f"Unknown action: {name}")
    return results


class GEMINI_response_line(bpy.types.PropertyGroup):
    """One line of agent response text for scrollable list."""
    text: bpy.props.StringProperty(name="Line", default="", maxlen=2000)


class GEMINI_OT_edit_prompt(bpy.types.Operator):
    bl_idname = "gemini.edit_prompt"
    bl_label = "Edit prompt"
    bl_description = "Open a window to type or edit your prompt"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Your prompt (what should the assistant do?):")
        layout.prop(scene, "gemini_assistant_prompt", text="", icon="NONE")


class GEMINI_OT_ask(bpy.types.Operator):
    bl_idname = "gemini.ask"
    bl_label = "Ask Gemini"
    bl_description = "Send viewport screenshot and prompt to Gemini; the agent will listen and run actions"
    bl_options = {"REGISTER"}

    def execute(self, context):
        scene = context.scene
        prompt = getattr(scene, "gemini_assistant_prompt", "") or ""
        prompt = prompt.strip()
        if not prompt:
            self.report({"WARNING"}, "Enter a prompt in the text field.")
            return {"CANCELLED"}

        # Spell code book: exact match translates to Gemini prompt or direct actions
        translated_prompt, direct_actions = spell_codebook.resolve(prompt)
        if direct_actions is not None:
            # Run spell actions directly (no Gemini call)
            run_results = execute_actions(direct_actions)
            scene["gemini_assistant_response"] = (
                f"Spell cast: \"{prompt}\"\n\n--- Actions executed ---\n" + "\n".join(run_results)
            )
            _update_response_lines(scene)
            self.report({"INFO"}, f"Spell: ran {len(direct_actions)} action(s).")
            return {"FINISHED"}

        # Use translated prompt if spell provided one, else original
        prompt_to_send = translated_prompt if translated_prompt is not None else prompt
        print("[Gemini Assistant] Prompt to send:", repr(prompt_to_send[:200]) + ("..." if len(prompt_to_send) > 200 else ""))

        # Capture viewport (raw PNG bytes)
        raw_bytes, _ = viewport_capture.capture_viewport_to_bytes()
        if not raw_bytes:
            self.report({"WARNING"}, "Could not capture viewport. Open a 3D view and ensure a camera exists for fallback.")
            print("[Gemini Assistant] DEBUG: No viewport capture (raw_bytes is empty)")
            return {"CANCELLED"}

        print("[Gemini Assistant] Viewport captured:", len(raw_bytes), "bytes")

        # Call Gemini
        object_list = actions.list_objects()
        print("[Gemini Assistant] Calling Gemini API with", len(object_list), "objects in scene")
        text, action_list = gemini_client.call_gemini(raw_bytes, prompt_to_send, object_list)
        print("[Gemini Assistant] Gemini returned. Response length:", len(text or ""), "| Actions parsed:", len(action_list or []))

        # Store raw response for UI and scrollable lines
        scene["gemini_assistant_response"] = text
        _update_response_lines(scene)

        if not action_list:
            self.report({"INFO"}, "No actions to run. Check response in panel.")
            return {"FINISHED"}

        run_results = execute_actions(action_list)
        scene["gemini_assistant_response"] = (text or "") + "\n\n--- Actions executed ---\n" + "\n".join(run_results)
        _update_response_lines(scene)
        self.report({"INFO"}, f"Ran {len(action_list)} action(s).")
        return {"FINISHED"}


class GEMINI_UL_response_lines(bpy.types.UIList):
    """Scrollable list of agent response lines."""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.label(text=item.text or "", icon="NONE")


class GEMINI_PT_panel(bpy.types.Panel):
    bl_label = "Gemini Assistant"
    bl_idname = "GEMINI_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gemini Assistant"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Prompt section: talk to Gemini
        box = layout.box()
        box.label(text="Talk to Gemini", icon="BLANK1")
        prompt = (getattr(scene, "gemini_assistant_prompt", None) or "").strip()
        if not prompt:
            box.label(text="Type your request below, then Send.", icon="NONE")
        row = box.row(align=True)
        row.prop(scene, "gemini_assistant_prompt", text="", icon="TEXT")
        row.operator("gemini.edit_prompt", text="", icon="BLANK1")
        box.operator("gemini.ask", text="Send to Gemini", icon="PINNED")

        # Agent response (scrollable)
        response = scene.get("gemini_assistant_response")
        if response:
            if len(scene.gemini_assistant_response_lines) == 0:
                _update_response_lines(scene)
            box = layout.box()
            box.label(text="Agent response", icon="UNPINNED")
            box.template_list(
                "GEMINI_UL_response_lines",
                "gemini_response_list",
                scene,
                "gemini_assistant_response_lines",
                scene,
                "gemini_assistant_response_lines_index",
                rows=12,
                maxrows=20,
            )


def register():
    # PropertyGroup must be registered before CollectionProperty that uses it
    bpy.utils.register_class(GEMINI_response_line)
    bpy.utils.register_class(GEMINI_UL_response_lines)
    bpy.types.Scene.gemini_assistant_prompt = bpy.props.StringProperty(
        name="Prompt",
        description="What you want the Gemini agent to do (e.g. 'Select the Cube and move it up by 2')",
        default="",
        maxlen=2000,
    )
    bpy.types.Scene.gemini_assistant_response_lines = bpy.props.CollectionProperty(type=GEMINI_response_line)
    bpy.types.Scene.gemini_assistant_response_lines_index = bpy.props.IntProperty(default=0)
    bpy.utils.register_class(GEMINI_OT_edit_prompt)
    bpy.utils.register_class(GEMINI_OT_ask)
    bpy.utils.register_class(GEMINI_PT_panel)


def unregister():
    bpy.utils.unregister_class(GEMINI_PT_panel)
    bpy.utils.unregister_class(GEMINI_OT_ask)
    bpy.utils.unregister_class(GEMINI_OT_edit_prompt)
    bpy.utils.unregister_class(GEMINI_UL_response_lines)
    bpy.utils.unregister_class(GEMINI_response_line)
    del bpy.types.Scene.gemini_assistant_response_lines_index
    del bpy.types.Scene.gemini_assistant_response_lines
    del bpy.types.Scene.gemini_assistant_prompt
