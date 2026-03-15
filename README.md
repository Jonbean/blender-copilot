# Blender Gemini Assistant

Blender add-on that uses **Google Gemini** as the brain to control the viewport via natural language. It sends a **viewport screenshot** and your **prompt** to Gemini, which can return **select_object** and **move_object** actions executed with **bpy**.

## Features

1. **Gemini integration** – API key is read from a local file: `gemini_assistant/gemini_api_key.txt` (in the addon folder). Put your key on its own line in that file.
2. **Selection and move** – The AI is prompted to return structured “function calls” for:
   - **select_object** – Select an object by name.
   - **move_object** – Move the active or named object by x/y/z deltas.
3. **Viewport screenshot** – The current 3D viewport (or active camera view if no viewport is found) is captured and sent as part of the request.
4. **bpy** – All Blender operations use the official `bpy` API.

## Installation

1. **Get a Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey).
2. **Install the add-on:**
   - Zip the `gemini_assistant` folder (so that `gemini_assistant/__init__.py` is inside the zip) or copy `gemini_assistant` into your Blender add-ons directory.
   - In Blender: Edit → Preferences → Add-ons → Install… → select the zip (or enable the add-on if you copied the folder).
3. **Set the API key:**  
   Open `gemini_assistant/gemini_api_key.txt` (inside the add-on folder) and paste your key on a new line. Remove the `#` comment line if you put the key on that line.
4. **Install the Gemini Python package** in Blender's Python (required for the add-on to talk to the API):
   - **Recommended — from inside Blender:** Open the **Scripting** workspace, paste the code below in the editor, and run it (Alt+P or click Run Script). If you get "No module named pip", run the ensurepip snippet first, then run the install again.
     ```python
     import subprocess, sys
     try:
         subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai"])
         print("Installed google-generativeai OK")
     except subprocess.CalledProcessError as e:
         print("pip install failed:", e)
     ```
     If pip is missing, run this once:
     ```python
     import subprocess, sys
     subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
     ```
   - **From terminal** (use Blender's Python, not system Python):  
     **macOS:** `/Applications/Blender.app/Contents/Resources/4.2/python/bin/python3.11 -m pip install google-generativeai` (adjust 4.2 and python3.11 to your Blender version).  
     **Windows:** `"C:\Program Files\Blender Foundation\Blender 4.2\4.2\python\bin\python.exe" -m pip install google-generativeai`  
     If you get **SSL errors**, add: `--trusted-host pypi.org --trusted-host files.pythonhosted.org`
5. **Enable** the add-on “Gemini Assistant” in Preferences → Add-ons.

## Usage

1. Open the **3D Viewport** (so the add-on can capture it; otherwise the active camera is used).
2. In the sidebar (N key), open the **Gemini Assistant** tab.
3. Type a prompt, e.g.:
   - “Select the Cube and move it up by 2”
   - “Select Sphere and move it 1 unit on X”
4. Click **Ask Gemini**. The viewport is captured, sent to Gemini with the prompt and scene object names, and any returned **select_object** / **move_object** actions are run in Blender. The response (and executed actions) are shown in the panel.

## API key file location

By default the key is read from:

- `gemini_assistant/gemini_api_key.txt`

(path relative to the add-on directory). The file should contain only the API key (or the key on one line, with comments allowed). Do not commit this file if the repo is public.

## Design: prompts and function calls

The add-on sends Gemini a **system prompt** that describes exactly two actions and a JSON output format:

- **select_object** – `object_name` (required).
- **move_object** – `object_name` (optional), `x`, `y`, `z` (optional floats, deltas).

The model is asked to reply with a single JSON block containing an `"actions"` array of `{ "name", "args" }` objects. The add-on parses that block and runs each action via bpy (selection and location changes). This gives you a clear, extensible pattern to add more actions later (e.g. rotate, scale) by updating the system prompt and `execute_actions()` in `__init__.py`.

## License

GPL-3.0-or-later.
