# Laser Cutter Output Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:subagent-driven-development to implement this plan task-by-task.

**Goal:** Generate structured SVG files for laser cutting

**Architecture:** Create svg_renderer.py with svgwrite-based SVG generation. Transform coordinates from geographic to SVG space. Organize elements into color-coded layers for XCS compatibility.

**Tech Stack:** svgwrite, shapely, networkx, fonttools

**Scope:** 6 phases from original design (phases 1-6)

**Codebase verified:** 2026-01-18

---

## Phase 4: SVG Renderer

**Goal:** Generate structured SVG files for laser cutting

**Done when:** SVG files generate with correct structure, color-coded layers, and physical sizing in inches

---

### Task 1: Add svgwrite dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add svgwrite to requirements**

Add to the end of `requirements.txt`:

```
svgwrite==1.4.3
```

**Step 2: Install the new dependency**

Run: `pip install svgwrite==1.4.3`

Expected: `Successfully installed svgwrite-1.4.3`

**Step 3: Verify installation**

Run: `python -c "import svgwrite; print(f'svgwrite version: {svgwrite.version}')"`

Expected: `svgwrite version: 1.4.3`

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add svgwrite dependency for SVG laser output"
```

---

### Task 2: Create svg_renderer.py with coordinate transformation

**Files:**
- Create: `svg_renderer.py`

**Step 1: Create the svg_renderer.py file with core structure**

```python
"""
SVG renderer for laser cutter output.

Generates structured SVG files with color-coded layers for XTool laser cutters.
"""
import svgwrite
from dataclasses import dataclass
from typing import Tuple, List, Optional, Dict, Any
import numpy as np

from map_data import MapData
from laser_theme import LaserThemeOptions, get_laser_options, get_road_color


@dataclass
class SVGBounds:
    """Bounding box for SVG coordinate transformation."""
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y


@dataclass
class PhysicalSize:
    """Physical size in inches."""
    width: float
    height: float

    @classmethod
    def from_string(cls, size_str: str) -> 'PhysicalSize':
        """
        Parse size string like '8x12' or '12x18' into PhysicalSize.

        Args:
            size_str: Size in format 'WxH' (width x height in inches)

        Returns:
            PhysicalSize instance
        """
        parts = size_str.lower().split('x')
        if len(parts) != 2:
            raise ValueError(f"Invalid size format: {size_str}. Expected 'WxH' like '8x12'")

        try:
            width = float(parts[0])
            height = float(parts[1])
        except ValueError:
            raise ValueError(f"Invalid size values: {size_str}. Must be numbers.")

        return cls(width=width, height=height)


# Supported physical sizes (inches)
SUPPORTED_SIZES = ['8x12', '12x18', '18x24']


def get_graph_bounds(graph) -> SVGBounds:
    """
    Extract bounding box from NetworkX graph nodes.

    Args:
        graph: NetworkX MultiDiGraph with node x/y attributes

    Returns:
        SVGBounds with min/max coordinates
    """
    xs = []
    ys = []

    for node, data in graph.nodes(data=True):
        if 'x' in data and 'y' in data:
            xs.append(data['x'])
            ys.append(data['y'])

    if not xs or not ys:
        raise ValueError("Graph has no nodes with coordinates")

    return SVGBounds(
        min_x=min(xs),
        max_x=max(xs),
        min_y=min(ys),
        max_y=max(ys)
    )


def transform_coords(x: float, y: float, bounds: SVGBounds,
                     svg_width: float, svg_height: float) -> Tuple[float, float]:
    """
    Transform geographic coordinates to SVG coordinates.

    Handles:
    - Scaling to fit SVG dimensions
    - Y-axis flip (SVG origin is top-left)
    - Centering within the viewBox

    Args:
        x: Geographic x coordinate (longitude)
        y: Geographic y coordinate (latitude)
        bounds: Geographic bounding box
        svg_width: SVG viewBox width
        svg_height: SVG viewBox height

    Returns:
        (svg_x, svg_y) tuple
    """
    # Calculate scale to fit within SVG while maintaining aspect ratio
    scale_x = svg_width / bounds.width if bounds.width > 0 else 1
    scale_y = svg_height / bounds.height if bounds.height > 0 else 1
    scale = min(scale_x, scale_y) * 0.95  # 5% margin

    # Center offset
    offset_x = (svg_width - bounds.width * scale) / 2
    offset_y = (svg_height - bounds.height * scale) / 2

    # Transform
    svg_x = (x - bounds.min_x) * scale + offset_x
    # Flip Y axis (SVG origin is top-left)
    svg_y = svg_height - ((y - bounds.min_y) * scale + offset_y)

    return svg_x, svg_y


def geometry_to_path_d(geom, bounds: SVGBounds,
                       svg_width: float, svg_height: float) -> str:
    """
    Convert Shapely geometry to SVG path d attribute string.

    Args:
        geom: Shapely geometry (LineString, Polygon, MultiPolygon, etc.)
        bounds: Geographic bounding box
        svg_width: SVG viewBox width
        svg_height: SVG viewBox height

    Returns:
        SVG path d string
    """
    geom_type = geom.geom_type

    if geom_type == 'LineString':
        coords = list(geom.coords)
        if not coords:
            return ""

        first = transform_coords(coords[0][0], coords[0][1],
                                 bounds, svg_width, svg_height)
        d = f"M {first[0]:.2f},{first[1]:.2f}"

        for coord in coords[1:]:
            pt = transform_coords(coord[0], coord[1], bounds, svg_width, svg_height)
            d += f" L {pt[0]:.2f},{pt[1]:.2f}"

        return d

    elif geom_type == 'Polygon':
        exterior = list(geom.exterior.coords)
        if not exterior:
            return ""

        first = transform_coords(exterior[0][0], exterior[0][1],
                                 bounds, svg_width, svg_height)
        d = f"M {first[0]:.2f},{first[1]:.2f}"

        for coord in exterior[1:]:
            pt = transform_coords(coord[0], coord[1], bounds, svg_width, svg_height)
            d += f" L {pt[0]:.2f},{pt[1]:.2f}"

        d += " Z"
        return d

    elif geom_type == 'MultiPolygon':
        parts = []
        for polygon in geom.geoms:
            part_d = geometry_to_path_d(polygon, bounds, svg_width, svg_height)
            if part_d:
                parts.append(part_d)
        return " ".join(parts)

    elif geom_type == 'MultiLineString':
        parts = []
        for line in geom.geoms:
            part_d = geometry_to_path_d(line, bounds, svg_width, svg_height)
            if part_d:
                parts.append(part_d)
        return " ".join(parts)

    elif geom_type == 'GeometryCollection':
        parts = []
        for sub_geom in geom.geoms:
            part_d = geometry_to_path_d(sub_geom, bounds, svg_width, svg_height)
            if part_d:
                parts.append(part_d)
        return " ".join(parts)

    else:
        # Unsupported geometry type
        return ""


def extract_road_paths(graph, bounds: SVGBounds,
                       svg_width: float, svg_height: float,
                       laser_options: LaserThemeOptions) -> List[Dict[str, Any]]:
    """
    Extract road paths from NetworkX graph with color assignment.

    Args:
        graph: NetworkX MultiDiGraph
        bounds: Geographic bounding box
        svg_width: SVG viewBox width
        svg_height: SVG viewBox height
        laser_options: LaserThemeOptions for color assignment

    Returns:
        List of dicts with 'path_d' and 'color' keys
    """
    roads = []

    for u, v, data in graph.edges(data=True):
        # Get geometry if available, otherwise construct from nodes
        if 'geometry' in data:
            geom = data['geometry']
            path_d = geometry_to_path_d(geom, bounds, svg_width, svg_height)
        else:
            # Construct line from node coordinates
            u_data = graph.nodes[u]
            v_data = graph.nodes[v]

            if 'x' in u_data and 'y' in u_data and 'x' in v_data and 'y' in v_data:
                start = transform_coords(u_data['x'], u_data['y'],
                                         bounds, svg_width, svg_height)
                end = transform_coords(v_data['x'], v_data['y'],
                                       bounds, svg_width, svg_height)
                path_d = f"M {start[0]:.2f},{start[1]:.2f} L {end[0]:.2f},{end[1]:.2f}"
            else:
                continue

        if not path_d:
            continue

        # Get road type and color
        highway = data.get('highway', 'unclassified')
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'

        color = get_road_color(laser_options, highway)

        roads.append({
            'path_d': path_d,
            'color': color,
            'road_type': highway
        })

    return roads


def extract_polygon_paths(gdf, bounds: SVGBounds,
                          svg_width: float, svg_height: float) -> List[str]:
    """
    Extract polygon paths from GeoDataFrame.

    Args:
        gdf: GeoDataFrame with geometry column
        bounds: Geographic bounding box
        svg_width: SVG viewBox width
        svg_height: SVG viewBox height

    Returns:
        List of SVG path d strings
    """
    paths = []

    if gdf is None or gdf.empty:
        return paths

    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None:
            continue

        path_d = geometry_to_path_d(geom, bounds, svg_width, svg_height)
        if path_d:
            paths.append(path_d)

    return paths


def create_laser_svg(map_data: MapData, output_path: str,
                     size: PhysicalSize, theme: Dict[str, Any]) -> str:
    """
    Create SVG file for laser cutting.

    Args:
        map_data: MapData with roads, water, parks
        output_path: Path to save SVG file
        size: Physical size in inches
        theme: Theme dictionary

    Returns:
        Path to created SVG file
    """
    # Get laser options from theme
    laser_options = get_laser_options(theme)

    # Calculate viewBox dimensions (use 100 units per inch for precision)
    units_per_inch = 100
    svg_width = size.width * units_per_inch
    svg_height = size.height * units_per_inch

    # Get bounds from road network
    bounds = get_graph_bounds(map_data.roads)

    # Create SVG document with physical size
    dwg = svgwrite.Drawing(
        output_path,
        size=(f'{size.width}in', f'{size.height}in'),
        debug=False
    )
    dwg.viewbox(minx=0, miny=0, width=svg_width, height=svg_height)

    # Create layer groups (order matters for z-index)
    water_layer = dwg.g(id='water')
    parks_layer = dwg.g(id='parks')
    roads_layer = dwg.g(id='roads')
    text_layer = dwg.g(id='text')

    # Add water polygons
    if laser_options.include_water and map_data.water is not None:
        water_paths = extract_polygon_paths(map_data.water, bounds,
                                            svg_width, svg_height)
        for path_d in water_paths:
            water_layer.add(dwg.path(
                d=path_d,
                fill=laser_options.water_color,
                stroke='none'
            ))

    # Add parks polygons
    if laser_options.include_parks and map_data.parks is not None:
        parks_paths = extract_polygon_paths(map_data.parks, bounds,
                                            svg_width, svg_height)
        for path_d in parks_paths:
            parks_layer.add(dwg.path(
                d=path_d,
                fill=laser_options.parks_color,
                stroke='none'
            ))

    # Add roads
    if laser_options.include_roads:
        road_data = extract_road_paths(map_data.roads, bounds,
                                       svg_width, svg_height, laser_options)

        # Group roads by color for efficient rendering
        roads_by_color: Dict[str, List[str]] = {}
        for road in road_data:
            color = road['color']
            if color not in roads_by_color:
                roads_by_color[color] = []
            roads_by_color[color].append(road['path_d'])

        # Add roads grouped by color
        for color, paths in roads_by_color.items():
            color_group = dwg.g(stroke=color, fill='none', stroke_width=1)
            for path_d in paths:
                color_group.add(dwg.path(d=path_d))
            roads_layer.add(color_group)

    # Add text labels
    if laser_options.include_text:
        # City name at bottom center
        city_text = map_data.city.upper()
        text_y = svg_height * 0.88  # 12% from bottom

        city_elem = dwg.text(
            city_text,
            insert=(svg_width / 2, text_y),
            text_anchor='middle',
            font_size=svg_height * 0.05,
            font_family='sans-serif',
            font_weight='bold',
            fill=laser_options.text_color
        )
        text_layer.add(city_elem)

        # Country name below city
        country_text = map_data.country.upper()
        country_y = svg_height * 0.92

        country_elem = dwg.text(
            country_text,
            insert=(svg_width / 2, country_y),
            text_anchor='middle',
            font_size=svg_height * 0.025,
            font_family='sans-serif',
            fill=laser_options.text_color
        )
        text_layer.add(country_elem)

        # Coordinates
        lat, lon = map_data.point
        coords_str = f"{abs(lat):.4f}° {'N' if lat >= 0 else 'S'} / "
        coords_str += f"{abs(lon):.4f}° {'E' if lon >= 0 else 'W'}"
        coords_y = svg_height * 0.95

        coords_elem = dwg.text(
            coords_str,
            insert=(svg_width / 2, coords_y),
            text_anchor='middle',
            font_size=svg_height * 0.015,
            font_family='sans-serif',
            fill=laser_options.text_color,
            opacity=0.7
        )
        text_layer.add(coords_elem)

    # Add layers to document (order determines z-index)
    dwg.add(water_layer)
    dwg.add(parks_layer)
    dwg.add(roads_layer)
    dwg.add(text_layer)

    # Save SVG
    dwg.save()

    print(f"✓ SVG saved: {output_path}")
    print(f"  Size: {size.width}\" x {size.height}\"")
    print(f"  Layers: water, parks, roads, text")

    return output_path
```

**Step 2: Verify the module imports correctly**

Run: `python -c "from svg_renderer import create_laser_svg, PhysicalSize, SUPPORTED_SIZES; print('Import successful')"`

Expected: `Import successful`

**Step 3: Commit**

```bash
git add svg_renderer.py
git commit -m "feat: add SVG renderer for laser cutter output

- Coordinate transformation from geographic to SVG space
- Road geometry extraction with color-coded layers
- Polygon rendering for water/parks
- Text labels for city, country, coordinates
- Physical sizing in inches with viewBox"
```

---

### Task 3: Test SVG generation with real map data

**Files:**
- None (verification only)

**Step 1: Create a test script to verify SVG generation**

Run:
```bash
python -c "
from map_data import get_map_data
from svg_renderer import create_laser_svg, PhysicalSize
from create_map_poster import load_theme

# Use a small area for quick testing
print('Fetching map data for test...')
map_data = get_map_data('Venice', 'Italy', (45.4408, 12.3155), 2000)

# Load laser theme
theme = load_theme('laser_mono')
map_data.theme = theme

# Generate SVG
size = PhysicalSize(width=8, height=12)
output_path = 'posters/test_laser_output.svg'

create_laser_svg(map_data, output_path, size, theme)

print('Test complete!')
"
```

Expected:
```
Fetching map data for test...
✓ All data downloaded successfully!
✓ Loaded theme: Laser Mono
✓ SVG saved: posters/test_laser_output.svg
  Size: 8" x 12"
  Layers: water, parks, roads, text
Test complete!
```

**Step 2: Verify SVG file structure**

Run: `head -20 posters/test_laser_output.svg`

Expected: XML header with SVG element containing width/height in inches and viewBox

**Step 3: Verify file size is reasonable**

Run: `ls -lh posters/test_laser_output.svg`

Expected: File exists with size > 50KB (depends on map complexity)

**Step 4: Clean up test file**

Run: `rm posters/test_laser_output.svg`

---

### Task 4: Test PhysicalSize parsing

**Files:**
- None (verification only)

**Step 1: Test valid size parsing**

Run:
```bash
python -c "
from svg_renderer import PhysicalSize, SUPPORTED_SIZES

for size_str in SUPPORTED_SIZES:
    size = PhysicalSize.from_string(size_str)
    print(f'{size_str}: {size.width}\" x {size.height}\"')

# Test custom size
custom = PhysicalSize.from_string('10x15')
print(f'Custom: {custom.width}\" x {custom.height}\"')
"
```

Expected:
```
8x12: 8.0" x 12.0"
12x18: 12.0" x 18.0"
18x24: 18.0" x 24.0"
Custom: 10.0" x 15.0"
```

**Step 2: Test invalid size parsing**

Run:
```bash
python -c "
from svg_renderer import PhysicalSize

try:
    PhysicalSize.from_string('invalid')
except ValueError as e:
    print(f'Error (expected): {e}')
"
```

Expected: `Error (expected): Invalid size format: invalid. Expected 'WxH' like '8x12'`

---

### Task 5: Verify SVG works with all supported sizes

**Files:**
- None (verification only)

**Step 1: Generate SVG for each supported size**

Run:
```bash
python -c "
from map_data import get_map_data
from svg_renderer import create_laser_svg, PhysicalSize, SUPPORTED_SIZES
from create_map_poster import load_theme
import os

# Fetch data once
print('Fetching map data...')
map_data = get_map_data('Paris', 'France', (48.8566, 2.3522), 3000)
theme = load_theme('laser_mono')
map_data.theme = theme

print()
for size_str in SUPPORTED_SIZES:
    size = PhysicalSize.from_string(size_str)
    output_path = f'posters/test_{size_str.replace(\"x\", \"_\")}.svg'
    create_laser_svg(map_data, output_path, size, theme)

print()
print('Cleaning up test files...')
for size_str in SUPPORTED_SIZES:
    path = f'posters/test_{size_str.replace(\"x\", \"_\")}.svg'
    if os.path.exists(path):
        os.remove(path)
        print(f'  Removed: {path}')

print('All sizes verified!')
"
```

Expected:
```
Fetching map data...
✓ All data downloaded successfully!
✓ Loaded theme: Laser Mono

✓ SVG saved: posters/test_8_12.svg
  Size: 8" x 12"
  Layers: water, parks, roads, text
✓ SVG saved: posters/test_12_18.svg
  Size: 12" x 18"
  Layers: water, parks, roads, text
✓ SVG saved: posters/test_18_24.svg
  Size: 18" x 24"
  Layers: water, parks, roads, text

Cleaning up test files...
  Removed: posters/test_8_12.svg
  Removed: posters/test_12_18.svg
  Removed: posters/test_18_24.svg
All sizes verified!
```

---

## Phase 4 Complete

After completing all tasks:
- `svgwrite` dependency added to requirements.txt
- `svg_renderer.py` provides `create_laser_svg()` function
- Coordinate transformation works correctly (geographic to SVG space)
- Roads, water, parks, and text render with correct colors
- Physical sizing in inches with proper viewBox
- All supported sizes (8x12, 12x18, 18x24) work correctly
- Ready for Phase 5: XCS Generator

---

## Known Limitations

### Text Handling

The current implementation uses SVG text elements rather than converting text to paths. This matches the design's fallback behavior: "Fallback to warning if text conversion fails."

**Implications:**
- Most laser cutter software (including XTool Creative Space) can handle SVG text elements
- Font rendering depends on fonts available in the laser software
- For guaranteed font fidelity, a future enhancement could add text-to-path conversion using fonttools

**Workaround:** If text doesn't render correctly in laser software, users can:
1. Open the SVG in a vector editor (Inkscape, Illustrator)
2. Convert text to paths (Object > Path > Object to Path in Inkscape)
3. Save and re-import to laser software

### Coordinate Projection

The implementation uses the same coordinate handling as the existing PNG renderer (raw geographic coordinates with aspect-ratio-preserving transformation). This maintains consistency with the current codebase behavior. For maps at high latitudes, slight distortion may occur. A future enhancement could add UTM projection for improved accuracy.
