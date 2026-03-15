# SPDX-License-Identifier: GPL-3.0-or-later
"""
Blender Gemini Assistant - Google Gemini client.
Loads API key from a local file and sends viewport image + prompt for function-call style responses.
"""

import json
import re
import os
from typing import List, Dict, Any, Optional

# Optional: google-generativeai is installed by user / in Blender's Python
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


SYSTEM_PROMPT = """You are an AI assistant controlling Blender via a 3D viewport. The user will send you a screenshot of the viewport and a text request.

You must respond with a JSON block that lists the actions to perform. Use only these actions:

1) select_object
   - Selects a single object by name (clears previous selection).
   - Args: "object_name" (string, required): exact name of the object in the scene.

2) move_object
   - Moves an object by a delta in scene units.
   - Args: "object_name" (string, optional): name of the object. If omitted, the currently active object is moved.
   - Args: "x", "y", "z" (float, optional): delta to add to location. Omitted axes are unchanged.

Output format: put a single JSON object in a code block with language "json". The object must have a key "actions" which is a list of action objects. Each action has "name" (string) and "args" (object).

Example response:
```json
{
  "actions": [
    { "name": "select_object", "args": { "object_name": "Cube" } },
    { "name": "move_object", "args": { "x": 1.0, "z": 0.5 } }
  ]
}
```

If the user request cannot be done with these two actions, respond with a short explanation and use "actions": []. Always include the JSON block with at least "actions" key."""


def get_api_key_path() -> str:
    """Path to the file containing the Gemini API key (in addon directory)."""
    this_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(this_dir, "gemini_api_key.txt")


def load_api_key(path: Optional[str] = None) -> Optional[str]:
    """Load API key from a local file. Uses first non-empty line (skips lines starting with #)."""
    p = path or get_api_key_path()
    try:
        if os.path.isfile(p):
            with open(p, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        return line
    except Exception:
        pass
    return None


def parse_actions_from_response(text: str, debug: bool = True) -> List[Dict[str, Any]]:
    """Extract actions list from model response. Looks for a JSON code block with 'actions'."""
    if not text:
        if debug:
            print("[Gemini Assistant] DEBUG: parse_actions — response text is empty")
        return []
    # Match ```json ... ``` or ``` ... ``` block
    block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if not block:
        if debug:
            print("[Gemini Assistant] DEBUG: parse_actions — no ```json ... ``` block found in response")
            print("[Gemini Assistant] DEBUG: response snippet (first 600 chars):", repr(text[:600]))
        return []
    try:
        data = json.loads(block.group(1))
        actions = data.get("actions") or []
        if debug:
            print("[Gemini Assistant] DEBUG: parse_actions — found JSON block, actions count =", len(actions), "->", actions)
        return actions
    except (json.JSONDecodeError, AttributeError) as e:
        if debug:
            print("[Gemini Assistant] DEBUG: parse_actions — JSON decode error:", e)
            print("[Gemini Assistant] DEBUG: matched block snippet:", repr(block.group(1)[:400]))
        return []


def call_gemini(
    image_bytes: bytes,
    user_message: str,
    object_list: List[str],
    api_key_path: Optional[str] = None,
) -> tuple:
    """
    Send viewport image + user message to Gemini and return (raw_text, parsed_actions).
    image_bytes: raw PNG bytes (or empty bytes to skip image).
    object_list is passed so the model knows available object names.
    """
    if not GEMINI_AVAILABLE:
        print("[Gemini Assistant] DEBUG: google-generativeai not installed")
        return "Error: google-generativeai is not installed. Install it in Blender's Python (e.g. pip install google-generativeai).", []

    key = load_api_key(api_key_path)
    if not key:
        print("[Gemini Assistant] DEBUG: API key not found at", get_api_key_path())
        return "Error: Gemini API key not found. Put your key in gemini_api_key.txt in the addon folder.", []

    print("[Gemini Assistant] DEBUG: API key loaded, building request...")
    print("[Gemini Assistant] DEBUG: user_message (prompt) =", repr(user_message[:300]) + ("..." if len(user_message) > 300 else ""))

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        user_content = (
            "Available object names in the scene: " + ", ".join(object_list) + ".\n\n"
            "User request: " + user_message
        )

        # Single content: system prompt, optional image, then user text
        content_parts = [SYSTEM_PROMPT]
        if image_bytes:
            content_parts.append({"mime_type": "image/png", "data": image_bytes})
        content_parts.append(user_content)

        print("[Gemini Assistant] DEBUG: Sending to Gemini: %d parts (system + image %s + user text)" % (
            len(content_parts), "yes" if image_bytes else "no"))
        response = model.generate_content(
            content_parts,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1024,
            ),
        )

        if not response or not response.candidates:
            print("[Gemini Assistant] DEBUG: Gemini returned no candidates. response =", response)
            return "No response from Gemini.", []

        text = (response.text or "").strip()
        print("[Gemini Assistant] DEBUG: Gemini API success. response.text length =", len(text))
        if text:
            print("[Gemini Assistant] DEBUG: Full raw response (for no-actions debugging):\n---\n", text, "\n---")
        actions = parse_actions_from_response(text)
        return text, actions
    except Exception as e:
        print("[Gemini Assistant] DEBUG: Gemini exception:", type(e).__name__, str(e))
        return f"Gemini error: {e}", []
