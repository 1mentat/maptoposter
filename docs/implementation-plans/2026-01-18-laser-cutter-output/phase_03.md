# Laser Cutter Output Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:subagent-driven-development to implement this plan task-by-task.

**Goal:** Extend theme system for laser-specific options

**Architecture:** Create laser-optimized theme with XCS-compatible colors. Add optional laser section to theme schema for element inclusion flags. Update theme loader to handle laser options with defaults.

**Tech Stack:** JSON, Python

**Scope:** 6 phases from original design (phases 1-6)

**Codebase verified:** 2026-01-18

---

## Phase 3: Laser Theme Extension

**Goal:** Extend theme system for laser-specific options

**Done when:** Laser themes load with element inclusion flags, existing themes work unchanged

---

### Task 1: Create laser_mono.json theme

**Files:**
- Create: `themes/laser_mono.json`

**Step 1: Create the laser-optimized theme file**

Create file `themes/laser_mono.json`:

```json
{
  "name": "Laser Mono",
  "description": "Monochrome theme optimized for laser engraving with XCS-compatible color coding",
  "bg": "#FFFFFF",
  "text": "#000000",
  "gradient_color": "#FFFFFF",
  "water": "#FFFF00",
  "parks": "#FFFFAA",
  "road_motorway": "#FF0000",
  "road_primary": "#CC0000",
  "road_secondary": "#990000",
  "road_tertiary": "#660000",
  "road_residential": "#330000",
  "road_default": "#660000",
  "laser": {
    "include_roads": true,
    "include_water": true,
    "include_parks": true,
    "include_text": true,
    "include_border": false,
    "road_colors": {
      "motorway": "#FF0000",
      "primary": "#EE0000",
      "secondary": "#DD0000",
      "tertiary": "#CC0000",
      "residential": "#BB0000"
    },
    "water_color": "#FFFF00",
    "parks_color": "#FFFFAA",
    "text_color": "#000000"
  }
}
```

**Step 2: Verify the JSON is valid**

Run: `python -c "import json; json.load(open('themes/laser_mono.json')); print('Valid JSON')"`

Expected: `Valid JSON`

**Step 3: Verify theme loads with existing loader**

Run: `python -c "from create_map_poster import load_theme; t = load_theme('laser_mono'); print(f'Theme: {t[\"name\"]}')"`

Expected: `Theme: Laser Mono` (with loaded message)

**Step 4: Commit**

```bash
git add themes/laser_mono.json
git commit -m "feat: add laser_mono theme with XCS-compatible colors

Color scheme:
- Roads: Red gradients (#FF0000 to #BB0000) by importance
- Water: Yellow (#FFFF00) for raster engrave
- Parks: Light yellow (#FFFFAA) for lighter engrave
- Text: Black (#000000) for solid engrave

Includes laser section with element inclusion flags."
```

---

### Task 2: Create LaserThemeOptions dataclass

**Files:**
- Create: `laser_theme.py`

**Step 1: Create the laser_theme.py file**

```python
"""
Laser theme options module.

Provides structured access to laser-specific theme options.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class LaserThemeOptions:
    """Laser-specific theme options with defaults."""

    # Element inclusion flags
    include_roads: bool = True
    include_water: bool = True
    include_parks: bool = True
    include_text: bool = True
    include_border: bool = False

    # Color overrides for laser output (XCS-compatible)
    road_colors: Dict[str, str] = field(default_factory=lambda: {
        'motorway': '#FF0000',
        'primary': '#EE0000',
        'secondary': '#DD0000',
        'tertiary': '#CC0000',
        'residential': '#BB0000'
    })
    water_color: str = '#FFFF00'
    parks_color: str = '#FFFFAA'
    text_color: str = '#000000'


def get_laser_options(theme: Dict[str, Any]) -> LaserThemeOptions:
    """
    Extract laser options from theme, using defaults for missing values.

    Args:
        theme: Theme dictionary (may or may not have 'laser' section)

    Returns:
        LaserThemeOptions with values from theme or defaults
    """
    laser_section = theme.get('laser', {})

    if not laser_section:
        # No laser section - use all defaults
        return LaserThemeOptions()

    # Build options with defaults for missing keys
    defaults = LaserThemeOptions()

    road_colors = laser_section.get('road_colors', None)
    if road_colors is None:
        road_colors = defaults.road_colors
    else:
        # Merge with defaults for any missing road types
        merged_colors = defaults.road_colors.copy()
        merged_colors.update(road_colors)
        road_colors = merged_colors

    return LaserThemeOptions(
        include_roads=laser_section.get('include_roads', defaults.include_roads),
        include_water=laser_section.get('include_water', defaults.include_water),
        include_parks=laser_section.get('include_parks', defaults.include_parks),
        include_text=laser_section.get('include_text', defaults.include_text),
        include_border=laser_section.get('include_border', defaults.include_border),
        road_colors=road_colors,
        water_color=laser_section.get('water_color', defaults.water_color),
        parks_color=laser_section.get('parks_color', defaults.parks_color),
        text_color=laser_section.get('text_color', defaults.text_color),
    )


def get_road_color(laser_options: LaserThemeOptions, road_type: str) -> str:
    """
    Get the laser color for a road type.

    Args:
        laser_options: LaserThemeOptions instance
        road_type: Road type (motorway, primary, secondary, tertiary, residential)

    Returns:
        Hex color string for the road type
    """
    # Normalize road type
    type_mapping = {
        'motorway': 'motorway',
        'motorway_link': 'motorway',
        'trunk': 'primary',
        'trunk_link': 'primary',
        'primary': 'primary',
        'primary_link': 'primary',
        'secondary': 'secondary',
        'secondary_link': 'secondary',
        'tertiary': 'tertiary',
        'tertiary_link': 'tertiary',
        'residential': 'residential',
        'living_street': 'residential',
        'unclassified': 'residential',
    }

    normalized = type_mapping.get(road_type, 'residential')
    return laser_options.road_colors.get(normalized, '#BB0000')
```

**Step 2: Verify the module imports correctly**

Run: `python -c "from laser_theme import LaserThemeOptions, get_laser_options, get_road_color; print('Import successful')"`

Expected: `Import successful`

**Step 3: Commit**

```bash
git add laser_theme.py
git commit -m "feat: add LaserThemeOptions for laser-specific theme settings

- LaserThemeOptions dataclass with defaults
- get_laser_options() extracts from theme with fallbacks
- get_road_color() maps road types to laser colors"
```

---

### Task 3: Test laser theme options extraction

**Files:**
- None (verification only)

**Step 1: Test extraction from laser_mono theme**

Run:
```bash
python -c "
from create_map_poster import load_theme
from laser_theme import get_laser_options

theme = load_theme('laser_mono')
opts = get_laser_options(theme)

print(f'Include roads: {opts.include_roads}')
print(f'Include water: {opts.include_water}')
print(f'Include border: {opts.include_border}')
print(f'Motorway color: {opts.road_colors[\"motorway\"]}')
print(f'Water color: {opts.water_color}')
"
```

Expected:
```
✓ Loaded theme: Laser Mono
  Monochrome theme optimized for laser engraving with XCS-compatible color coding
Include roads: True
Include water: True
Include border: False
Motorway color: #FF0000
Water color: #FFFF00
```

**Step 2: Test extraction from theme without laser section**

Run:
```bash
python -c "
from create_map_poster import load_theme
from laser_theme import get_laser_options

theme = load_theme('noir')
opts = get_laser_options(theme)

print(f'Include roads: {opts.include_roads}')
print(f'Motorway color: {opts.road_colors[\"motorway\"]}')
print('Defaults applied successfully')
"
```

Expected:
```
✓ Loaded theme: Noir
  ...
Include roads: True
Motorway color: #FF0000
Defaults applied successfully
```

**Step 3: Test get_road_color mapping**

Run:
```bash
python -c "
from laser_theme import LaserThemeOptions, get_road_color

opts = LaserThemeOptions()
print(f'motorway: {get_road_color(opts, \"motorway\")}')
print(f'motorway_link: {get_road_color(opts, \"motorway_link\")}')
print(f'trunk: {get_road_color(opts, \"trunk\")}')
print(f'residential: {get_road_color(opts, \"residential\")}')
print(f'unknown_type: {get_road_color(opts, \"unknown_type\")}')
"
```

Expected:
```
motorway: #FF0000
motorway_link: #FF0000
trunk: #EE0000
residential: #BB0000
unknown_type: #BB0000
```

---

### Task 4: Verify existing themes work unchanged

**Files:**
- None (verification only)

**Step 1: Test all existing themes still load**

Run:
```bash
python -c "
from create_map_poster import get_available_themes, load_theme
from laser_theme import get_laser_options

themes = get_available_themes()
print(f'Testing {len(themes)} themes...')
for name in themes:
    theme = load_theme(name)
    opts = get_laser_options(theme)
    # Just verify no errors
print(f'All {len(themes)} themes load successfully with laser options')
"
```

Expected:
```
Testing 18 themes...
✓ Loaded theme: ...
[repeated for each theme]
All 18 themes load successfully with laser options
```

**Step 2: Verify PNG generation still works with laser theme**

Run: `python create_map_poster.py --city "Venice" --country "Italy" --theme laser_mono --distance 3000`

Expected:
- Map generates successfully
- PNG saved to `posters/venice_laser_mono_*.png`
- Colors appear as red/yellow/black per the laser theme

---

## Phase 3 Complete

After completing all tasks:
- `themes/laser_mono.json` exists with XCS-compatible colors and laser section
- `laser_theme.py` provides `LaserThemeOptions` and extraction functions
- Existing themes work unchanged (defaults applied when no laser section)
- PNG generation works with laser_mono theme
- Ready for Phase 4: SVG Renderer
