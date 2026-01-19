# Laser Cutter Output Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:subagent-driven-development to implement this plan task-by-task.

**Goal:** Generate XTool Creative Space project files

**Architecture:** Create xcs_generator.py that builds XCS JSON structure with canvas elements, layer definitions, and power/speed settings from laser profiles.

**Tech Stack:** Python json, uuid

**Scope:** 6 phases from original design (phases 1-6)

**Codebase verified:** 2026-01-18

---

## Phase 5: XCS Generator

**Goal:** Generate XTool Creative Space project files

**Done when:** XCS files open in XTool Creative Space with correct layers and pre-mapped power settings

---

### Task 1: Create xcs_generator.py with XCS structure builder

**Files:**
- Create: `xcs_generator.py`

**Step 1: Create the xcs_generator.py file**

```python
"""
XCS (XTool Creative Space) project file generator.

Generates .xcs files that open directly in XTool Creative Space
with pre-configured power/speed settings.
"""
import json
import uuid
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

from map_data import MapData
from laser_config import LaserProfile
from laser_theme import LaserThemeOptions, get_laser_options, get_road_color
from svg_renderer import (
    get_graph_bounds, transform_coords, geometry_to_path_d,
    extract_road_paths, extract_polygon_paths, PhysicalSize, SVGBounds
)


# XCS Processing modes
class ProcessingMode:
    VECTOR_ENGRAVING = "VECTOR_ENGRAVING"  # Score mode for lines
    FILL_VECTOR_ENGRAVING = "FILL_VECTOR_ENGRAVING"  # Raster fill mode
    BITMAP_ENGRAVING = "BITMAP_ENGRAVING"  # Solid bitmap engrave


@dataclass
class XCSElement:
    """Single element in XCS canvas."""
    element_id: str
    path_d: str
    color: str
    processing_mode: str
    power: int
    speed: int
    density: Optional[int] = None
    element_type: str = "path"  # path, text, etc.


def generate_uuid() -> str:
    """Generate a UUID for XCS elements."""
    return str(uuid.uuid4())


def create_xcs_element_dict(element: XCSElement, index: int) -> Dict[str, Any]:
    """
    Create XCS element dictionary structure.

    Args:
        element: XCSElement with path and settings
        index: Element index for z-ordering

    Returns:
        Dictionary matching XCS element format
    """
    elem_dict = {
        "id": element.element_id,
        "type": element.element_type,
        "zIndex": index,
        "visible": True,
        "locked": False,
        "data": {
            "path": element.path_d,
            "stroke": element.color,
            "strokeWidth": 1,
            "fill": "none" if element.processing_mode == ProcessingMode.VECTOR_ENGRAVING else element.color
        },
        "processing": {
            "mode": element.processing_mode,
            "power": element.power,
            "speed": element.speed,
        }
    }

    # Add density for fill operations
    if element.density is not None:
        elem_dict["processing"]["density"] = element.density

    return elem_dict


def create_xcs_layer_dict(layer_id: str, name: str, color: str,
                          visible: bool = True) -> Dict[str, Any]:
    """
    Create XCS layer dictionary structure.

    Args:
        layer_id: Unique layer ID
        name: Display name for layer
        color: Layer color for UI
        visible: Whether layer is visible

    Returns:
        Dictionary matching XCS layer format
    """
    return {
        "id": layer_id,
        "name": name,
        "color": color,
        "visible": visible,
        "locked": False,
        "elements": []
    }


def build_xcs_structure(elements: List[XCSElement], layers: List[Dict[str, Any]],
                        canvas_width: float, canvas_height: float,
                        profile: LaserProfile, map_data: MapData) -> Dict[str, Any]:
    """
    Build complete XCS project structure.

    Args:
        elements: List of XCSElement objects
        layers: List of layer dictionaries
        canvas_width: Canvas width in mm
        canvas_height: Canvas height in mm
        profile: LaserProfile with machine settings
        map_data: MapData for metadata

    Returns:
        Complete XCS project dictionary
    """
    # Convert elements to dicts
    element_dicts = [create_xcs_element_dict(elem, i)
                     for i, elem in enumerate(elements)]

    # Build project structure
    project = {
        "version": "1.0",
        "created": datetime.now().isoformat(),
        "generator": "maptoposter",
        "machine": profile.machine,
        "material": {
            "name": profile.material_name,
            "thickness": profile.material_thickness
        },
        "canvas": {
            "width": canvas_width,
            "height": canvas_height,
            "unit": "mm"
        },
        "layers": layers,
        "elements": element_dicts,
        "metadata": {
            "city": map_data.city,
            "country": map_data.country,
            "coordinates": {
                "latitude": map_data.point[0],
                "longitude": map_data.point[1]
            }
        }
    }

    return project


def create_xcs_file(map_data: MapData, output_path: str,
                    size: PhysicalSize, theme: Dict[str, Any],
                    profile: LaserProfile) -> str:
    """
    Create XCS project file for laser cutting.

    Args:
        map_data: MapData with roads, water, parks
        output_path: Path to save XCS file
        size: Physical size in inches
        theme: Theme dictionary
        profile: LaserProfile with power/speed settings

    Returns:
        Path to created XCS file
    """
    # Get laser options from theme
    laser_options = get_laser_options(theme)

    # Convert size to mm (1 inch = 25.4 mm)
    canvas_width = size.width * 25.4
    canvas_height = size.height * 25.4

    # Use same coordinate system as SVG (100 units per inch)
    units_per_inch = 100
    svg_width = size.width * units_per_inch
    svg_height = size.height * units_per_inch

    # Get bounds from road network
    bounds = get_graph_bounds(map_data.roads)

    # Create layers
    layers = []
    elements = []

    # Water layer
    if laser_options.include_water and map_data.water is not None:
        water_layer = create_xcs_layer_dict(
            generate_uuid(), "Water", laser_options.water_color
        )
        layers.append(water_layer)

        water_paths = extract_polygon_paths(map_data.water, bounds,
                                            svg_width, svg_height)
        for path_d in water_paths:
            elem = XCSElement(
                element_id=generate_uuid(),
                path_d=path_d,
                color=laser_options.water_color,
                processing_mode=ProcessingMode.FILL_VECTOR_ENGRAVING,
                power=profile.engrave_fill_water.power,
                speed=profile.engrave_fill_water.speed,
                density=profile.engrave_fill_water.density
            )
            elements.append(elem)
            water_layer["elements"].append(elem.element_id)

    # Parks layer
    if laser_options.include_parks and map_data.parks is not None:
        parks_layer = create_xcs_layer_dict(
            generate_uuid(), "Parks", laser_options.parks_color
        )
        layers.append(parks_layer)

        parks_paths = extract_polygon_paths(map_data.parks, bounds,
                                            svg_width, svg_height)
        for path_d in parks_paths:
            elem = XCSElement(
                element_id=generate_uuid(),
                path_d=path_d,
                color=laser_options.parks_color,
                processing_mode=ProcessingMode.FILL_VECTOR_ENGRAVING,
                power=profile.engrave_fill_parks.power,
                speed=profile.engrave_fill_parks.speed,
                density=profile.engrave_fill_parks.density
            )
            elements.append(elem)
            parks_layer["elements"].append(elem.element_id)

    # Roads layers (one per road type for power control)
    if laser_options.include_roads:
        road_data = extract_road_paths(map_data.roads, bounds,
                                       svg_width, svg_height, laser_options)

        # Group roads by type
        roads_by_type: Dict[str, List[Dict]] = {
            'motorway': [],
            'primary': [],
            'secondary': [],
            'tertiary': [],
            'residential': []
        }

        type_mapping = {
            'motorway': 'motorway', 'motorway_link': 'motorway',
            'trunk': 'primary', 'trunk_link': 'primary',
            'primary': 'primary', 'primary_link': 'primary',
            'secondary': 'secondary', 'secondary_link': 'secondary',
            'tertiary': 'tertiary', 'tertiary_link': 'tertiary',
        }

        for road in road_data:
            road_type = road.get('road_type', 'residential')
            normalized_type = type_mapping.get(road_type, 'residential')
            roads_by_type[normalized_type].append(road)

        # Create layer for each road type
        profile_map = {
            'motorway': profile.score_roads_motorway,
            'primary': profile.score_roads_primary,
            'secondary': profile.score_roads_secondary,
            'tertiary': profile.score_roads_tertiary,
            'residential': profile.score_roads_residential,
        }

        for road_type, roads in roads_by_type.items():
            if not roads:
                continue

            road_settings = profile_map[road_type]
            road_color = laser_options.road_colors.get(road_type, '#BB0000')

            road_layer = create_xcs_layer_dict(
                generate_uuid(), f"Roads - {road_type.title()}", road_color
            )
            layers.append(road_layer)

            for road in roads:
                elem = XCSElement(
                    element_id=generate_uuid(),
                    path_d=road['path_d'],
                    color=road['color'],
                    processing_mode=ProcessingMode.VECTOR_ENGRAVING,
                    power=road_settings.power,
                    speed=road_settings.speed
                )
                elements.append(elem)
                road_layer["elements"].append(elem.element_id)

    # Text layer
    if laser_options.include_text:
        text_layer = create_xcs_layer_dict(
            generate_uuid(), "Text", laser_options.text_color
        )
        layers.append(text_layer)

        # City name (simplified - actual text would need path conversion)
        text_y = svg_height * 0.88
        city_path = f"M {svg_width/2 - 100},{text_y} L {svg_width/2 + 100},{text_y}"

        city_elem = XCSElement(
            element_id=generate_uuid(),
            path_d=city_path,
            color=laser_options.text_color,
            processing_mode=ProcessingMode.BITMAP_ENGRAVING,
            power=profile.engrave_solid_text.power,
            speed=profile.engrave_solid_text.speed,
            element_type="text"
        )
        elements.append(city_elem)
        text_layer["elements"].append(city_elem.element_id)

    # Build and save XCS structure
    xcs_project = build_xcs_structure(
        elements, layers, canvas_width, canvas_height, profile, map_data
    )

    with open(output_path, 'w') as f:
        json.dump(xcs_project, f, indent=2)

    print(f"✓ XCS saved: {output_path}")
    print(f"  Machine: {profile.machine}")
    print(f"  Material: {profile.material_name}")
    print(f"  Layers: {len(layers)}")
    print(f"  Elements: {len(elements)}")

    return output_path
```

**Step 2: Verify the module imports correctly**

Run: `python -c "from xcs_generator import create_xcs_file, ProcessingMode, XCSElement; print('Import successful')"`

Expected: `Import successful`

**Step 3: Commit**

```bash
git add xcs_generator.py
git commit -m "feat: add XCS generator for XTool Creative Space project files

- XCSElement and layer structure builders
- Power/speed mapping from laser profiles
- Processing mode assignment (VECTOR_ENGRAVING, FILL_VECTOR_ENGRAVING)
- Grouped layers by element type and road category"
```

---

### Task 2: Test XCS generation with real map data

**Files:**
- None (verification only)

**Step 1: Create a test script to verify XCS generation**

Run:
```bash
python -c "
from map_data import get_map_data
from xcs_generator import create_xcs_file
from svg_renderer import PhysicalSize
from laser_config import load_laser_profile
from create_map_poster import load_theme

# Fetch data
print('Fetching map data for test...')
map_data = get_map_data('Venice', 'Italy', (45.4408, 12.3155), 2000)

# Load theme and profile
theme = load_theme('laser_mono')
profile = load_laser_profile('p2_basswood_3mm')
map_data.theme = theme

# Generate XCS
size = PhysicalSize(width=8, height=12)
output_path = 'posters/test_laser_output.xcs'

create_xcs_file(map_data, output_path, size, theme, profile)

print('Test complete!')
"
```

Expected:
```
Fetching map data for test...
✓ All data downloaded successfully!
✓ Loaded theme: Laser Mono
✓ Loaded laser profile: P2 / 3mm Basswood Plywood
✓ XCS saved: posters/test_laser_output.xcs
  Machine: P2
  Material: 3mm Basswood Plywood
  Layers: [N]
  Elements: [M]
Test complete!
```

**Step 2: Verify XCS file structure**

Run: `python -c "import json; data = json.load(open('posters/test_laser_output.xcs')); print(f'Version: {data[\"version\"]}'); print(f'Machine: {data[\"machine\"]}'); print(f'Layers: {len(data[\"layers\"])}'); print(f'Elements: {len(data[\"elements\"])}')" `

Expected:
```
Version: 1.0
Machine: P2
Layers: [N]
Elements: [M]
```

**Step 3: Verify power/speed settings are correct**

Run:
```bash
python -c "
import json
data = json.load(open('posters/test_laser_output.xcs'))

# Find a road element
for elem in data['elements']:
    if elem.get('processing', {}).get('mode') == 'VECTOR_ENGRAVING':
        print(f'Road element found:')
        print(f'  Power: {elem[\"processing\"][\"power\"]}')
        print(f'  Speed: {elem[\"processing\"][\"speed\"]}')
        break

# Find a water element
for elem in data['elements']:
    if elem.get('processing', {}).get('mode') == 'FILL_VECTOR_ENGRAVING':
        print(f'Fill element found:')
        print(f'  Power: {elem[\"processing\"][\"power\"]}')
        print(f'  Speed: {elem[\"processing\"][\"speed\"]}')
        print(f'  Density: {elem[\"processing\"].get(\"density\")}')
        break
"
```

Expected: Power/speed values match those in p2_basswood_3mm.yaml

**Step 4: Clean up test file**

Run: `rm posters/test_laser_output.xcs`

---

### Task 3: Verify XCS works with different profiles

**Files:**
- Create: `laser_profiles/p2_birch_3mm.yaml` (for testing)

**Step 1: Create an alternate profile for testing**

Create file `laser_profiles/p2_birch_3mm.yaml`:

```yaml
# XTool P2 Laser Profile for 3mm Birch Plywood
# Birch is harder than basswood - needs higher power

machine: P2
material:
  name: "3mm Birch Plywood"
  thickness: 3

operations:
  score:
    roads_motorway:
      power: 30
      speed: 90
    roads_primary:
      power: 27
      speed: 110
    roads_secondary:
      power: 23
      speed: 130
    roads_tertiary:
      power: 20
      speed: 150
    roads_residential:
      power: 17
      speed: 170

  engrave_fill:
    water:
      power: 50
      speed: 180
      density: 100
    parks:
      power: 40
      speed: 180
      density: 80

  engrave_solid:
    text:
      power: 60
      speed: 140
```

**Step 2: Verify both profiles are available**

Run: `python -c "from laser_config import get_available_profiles; print(get_available_profiles())"`

Expected: `['p2_basswood_3mm', 'p2_birch_3mm']`

**Step 3: Test XCS generation with alternate profile**

Run:
```bash
python -c "
from map_data import get_map_data
from xcs_generator import create_xcs_file
from svg_renderer import PhysicalSize
from laser_config import load_laser_profile
from create_map_poster import load_theme

# Fetch data
map_data = get_map_data('Paris', 'France', (48.8566, 2.3522), 2000)
theme = load_theme('laser_mono')
profile = load_laser_profile('p2_birch_3mm')

size = PhysicalSize(width=12, height=18)
output_path = 'posters/test_birch.xcs'

create_xcs_file(map_data, output_path, size, theme, profile)

# Verify different power settings
import json
data = json.load(open(output_path))
print(f'Material in file: {data[\"material\"][\"name\"]}')

# Cleanup
import os
os.remove(output_path)
print('Test passed!')
"
```

Expected:
```
...
Material in file: 3mm Birch Plywood
Test passed!
```

**Step 4: Commit the new profile**

```bash
git add laser_profiles/p2_birch_3mm.yaml
git commit -m "feat: add P2 birch plywood laser profile

Higher power settings for harder birch wood."
```

---

### Task 4: Manual XCS verification in XTool Creative Space

**Files:**
- None (manual verification)

**Note:** This task requires XTool Creative Space software to be installed. If not available, skip this task and verify during first actual laser cutting session.

**Step 1: Generate a test XCS file**

Run:
```bash
python -c "
from map_data import get_map_data
from xcs_generator import create_xcs_file
from svg_renderer import PhysicalSize
from laser_config import load_laser_profile
from create_map_poster import load_theme

map_data = get_map_data('Paris', 'France', (48.8566, 2.3522), 3000)
theme = load_theme('laser_mono')
profile = load_laser_profile('p2_basswood_3mm')

size = PhysicalSize(width=12, height=18)
create_xcs_file(map_data, 'posters/verify_xcs.xcs', size, theme, profile)
"
```

**Step 2: Open in XTool Creative Space**

1. Launch XTool Creative Space
2. File > Open > Select `posters/verify_xcs.xcs`
3. Verify:
   - File opens without errors
   - Layers are visible in the layers panel
   - Power/speed settings are applied to elements
   - Canvas size matches 12" x 18"

**Step 3: Document any format issues**

If the file doesn't open correctly:
- Note the error message
- Compare generated JSON structure with a known-good XCS file
- Adjust `xcs_generator.py` structure accordingly

**Step 4: Clean up**

Run: `rm posters/verify_xcs.xcs`

---

### Task 5: Verify existing functionality unchanged

**Files:**
- None (verification only)

**Step 1: Verify PNG generation still works**

Run: `python create_map_poster.py --city "Rome" --country "Italy" --theme noir --distance 4000`

Expected:
- Map generates successfully
- PNG saved to posters/

**Step 2: Verify list-themes still works**

Run: `python create_map_poster.py --list-themes`

Expected: Lists all themes including laser_mono

---

## Phase 5 Complete

After completing all tasks:
- `xcs_generator.py` provides `create_xcs_file()` function
- XCS files contain proper structure with layers and elements
- Power/speed settings mapped correctly from laser profiles
- Processing modes assigned correctly (VECTOR_ENGRAVING, FILL_VECTOR_ENGRAVING)
- Multiple laser profiles supported
- Existing PNG generation unchanged
- Ready for Phase 6: CLI Integration
