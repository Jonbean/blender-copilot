# SPDX-License-Identifier: GPL-3.0-or-later
"""
Spell code book: exact-match phrases that translate to Gemini prompts or direct actions.
When the user's command matches a spell exactly, it is either translated and sent to the
Gemini agent, or executed as direct actions (no API call).
"""

from typing import List, Dict, Any, Optional, Tuple

# Normalize for matching: strip and optionally lower. Spells are stored normalized.
def _normalize(s: str) -> str:
    return s.strip().lower()


# ---------------------------------------------------------------------------
# Spell code book: list of { "phrase": str, "translated_prompt": str | None, "direct_actions": list | None }
# - phrase: exact match (after normalize). User must type this exactly (ignoring case/outer whitespace).
# - translated_prompt: if set, this string is sent to Gemini instead of the user's input.
# - direct_actions: if set, these actions are run locally and Gemini is not called.
#   Each item is {"name": "move_object"|"select_object"|"execute_bpy"|"shape_change_near_cursor", "args": {...}}.
# Only one of translated_prompt or direct_actions should be set per spell.
# ---------------------------------------------------------------------------

SPELL_BOOK: List[Dict[str, Any]] = [
    {
        "phrase": "wingardium leviosa",
        "translated_prompt": None,
        "direct_actions": [
            {"name": "move_object", "args": {"z": 3.0}}
        ],
    },
    {
        "phrase": "abracadabra",
        "translated_prompt": None,
        "direct_actions": [
            {"name": "shape_change_near_cursor", "args": {}}
        ],
    },
]


def resolve(user_prompt: str) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
    """
    If user_prompt matches a spell exactly (after normalizing), return either:
    - (translated_prompt, None): send translated_prompt to Gemini.
    - (None, direct_actions): run direct_actions locally; do not call Gemini.
    If no spell matches, return (user_prompt, None) so the original prompt is sent to Gemini.
    """
    if not user_prompt or not user_prompt.strip():
        return (user_prompt, None)
    normalized = _normalize(user_prompt)
    for entry in SPELL_BOOK:
        spell_phrase = (entry.get("phrase") or "").strip().lower()
        if not spell_phrase:
            continue
        if normalized == spell_phrase:
            direct = entry.get("direct_actions")
            if direct is not None and isinstance(direct, list) and len(direct) > 0:
                return (None, direct)
            translated = entry.get("translated_prompt")
            if translated is not None:
                return (translated, None)
            # Spell has no translation and no direct actions; fall through (use original)
            break
    return (user_prompt, None)


def list_spells() -> List[str]:
    """Return the list of registered spell phrases (normalized) for UI or docs."""
    out = []
    for entry in SPELL_BOOK:
        p = (entry.get("phrase") or "").strip().lower()
        if p:
            out.append(p)
    return out
