#!/usr/bin/env python3
"""
Standalone test for Gemini API connection using the addon's client.
Run from project root: python test_gemini_connection.py
Requires: pip install google-generativeai
"""
import sys
import os

# Run from repo root so gemini_assistant can be imported and find gemini_api_key.txt
repo_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, repo_root)

# Minimal valid 1x1 PNG (red pixel)
MINI_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def main():
    # Import client only (avoid pulling in bpy from gemini_assistant/__init__.py)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gemini_client",
        os.path.join(repo_root, "gemini_assistant", "gemini_client.py"),
    )
    gemini_client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gemini_client)

    if not gemini_client.GEMINI_AVAILABLE:
        print("FAIL: google-generativeai not installed. pip install google-generativeai")
        return 1

    key_path = gemini_client.get_api_key_path()
    if not os.path.isfile(key_path):
        print("FAIL: API key file not found:", key_path)
        return 1

    print("Using API key from:", key_path)
    print("Sending test request to Gemini (minimal image + short prompt)...")

    prompt = "The scene has objects: Cube, Camera. Reply with a JSON block only: {\"actions\": []}."
    object_list = ["Cube", "Camera"]

    text, actions = gemini_client.call_gemini(MINI_PNG, prompt, object_list)

    if text.startswith("Error:") or (text and "Gemini error:" in text):
        if "API_KEY_INVALID" in text or "API key not valid" in text or "not valid" in text.lower():
            print("Connection to Gemini OK, but API key was rejected (invalid or expired).")
            print("Put a valid key in gemini_assistant/gemini_api_key.txt and run again.")
        else:
            print("FAIL:", text[:400])
        return 1

    print("OK: Gemini responded (communication and key both work).")
    print("Response length:", len(text))
    print("Actions parsed:", len(actions), actions)
    print("Response preview:", (text or "")[:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
