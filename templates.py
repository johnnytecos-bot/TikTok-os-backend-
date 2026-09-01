"""
templates.py
Defines the visual "look" of each card style. Pure data — no drawing logic
here, that lives in card_renderer.py. Add a new dict entry to add a new
style; nothing else needs to change.

Each template is self-contained (solid colors + optional grid/lines drawn
in code), so there are no external background images to source or license.
"""

TEMPLATES = {
    "dark_grid": {
        "bg_color": "#151515",
        "text_color": "#FFFFFF",
        "accent_color": "#3A3A3A",
        "border_color": None,
        "grid_lines": True,
        "font": "bold",
    },
    "notebook_paper": {
        "bg_color": "#F5F1E8",
        "text_color": "#1A1A1A",
        "accent_color": "#D8D0BC",
        "border_color": None,
        "grid_lines": False,
        "ruled_lines": True,
        "font": "regular",
    },
    "midnight_border": {
        "bg_color": "#0B0B0F",
        "text_color": "#FFFFFF",
        "accent_color": "#2A2A33",
        "border_color": "#E8264B",
        "grid_lines": False,
        "font": "bold",
    },
    "plain_dark": {
        "bg_color": "#101010",
        "text_color": "#EDEDED",
        "accent_color": "#242424",
        "border_color": None,
        "grid_lines": False,
        "font": "bold",
    },
    "cinematic": {
        "bg_gradient": ("#05070D", "#161B26"),  # top -> bottom
        "text_color": "#F5F5F0",
        "accent_color": "#2A2E3A",
        "border_color": None,
        "grid_lines": False,
        "vignette": True,
        "letterbox": True,
        "font": "regular",
    },
}

TEMPLATE_IDS = list(TEMPLATES.keys())


def pick_next_template(last_template_id: str | None) -> str:
    """
    Rotates through templates so the same style never posts twice in a row.
    Simple round-robin based on the last one used.
    """
    if last_template_id is None or last_template_id not in TEMPLATE_IDS:
        return TEMPLATE_IDS[0]

    current_index = TEMPLATE_IDS.index(last_template_id)
    next_index = (current_index + 1) % len(TEMPLATE_IDS)
    return TEMPLATE_IDS[next_index]
