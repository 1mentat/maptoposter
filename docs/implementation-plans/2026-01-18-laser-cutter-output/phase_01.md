# Laser Cutter Output Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:subagent-driven-development to implement this plan task-by-task.

**Goal:** Extract map data fetching into a reusable layer that feeds both PNG and future laser output

**Architecture:** Create a MapData dataclass holding roads, water, parks, and metadata. Extract data fetching from create_poster() into get_map_data(). Modify create_poster() to consume MapData.

**Tech Stack:** Python dataclasses, osmnx, geopandas, networkx

**Scope:** 6 phases from original design (phases 1-6)

**Codebase verified:** 2026-01-18

---

## Phase 1: Data Extraction Layer

**Goal:** Extract map data fetching and processing into reusable module

**Done when:** Existing PNG generation works unchanged using new data extraction layer

---

### Task 1: Create MapData dataclass

**Files:**
- Create: `map_data.py`

**Step 1: Create the map_data.py file with MapData dataclass**

```python
"""
Map data extraction module.

Provides shared data structures and extraction functions for map rendering.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import osmnx as ox
from tqdm import tqdm
import time


@dataclass
class MapData:
    """Container for extracted map data."""

    # Geographic data
    roads: Any  # NetworkX MultiDiGraph
    water: Optional[Any]  # GeoDataFrame or None
    parks: Optional[Any]  # GeoDataFrame or None

    # Metadata
    city: str
    country: str
    point: Tuple[float, float]  # (latitude, longitude)
    distance: int  # radius in meters

    # Theme (loaded separately, attached for convenience)
    theme: Optional[Dict[str, Any]] = None


def get_map_data(city: str, country: str, point: Tuple[float, float],
                 distance: int) -> MapData:
    """
    Fetch map data from OpenStreetMap.

    Args:
        city: City name
        country: Country name
        point: (latitude, longitude) tuple
        distance: Map radius in meters

    Returns:
        MapData containing roads, water, parks, and metadata
    """
    print(f"\nFetching map data for {city}, {country}...")

    with tqdm(total=3, desc="Fetching map data", unit="step",
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:

        # 1. Fetch Street Network
        pbar.set_description("Downloading street network")
        roads = ox.graph_from_point(point, dist=distance, dist_type='bbox',
                                    network_type='all')
        pbar.update(1)
        time.sleep(0.5)  # Rate limit between requests

        # 2. Fetch Water Features
        pbar.set_description("Downloading water features")
        try:
            water = ox.features_from_point(
                point,
                tags={'natural': 'water', 'waterway': 'riverbank'},
                dist=distance
            )
        except Exception:
            water = None
        pbar.update(1)
        time.sleep(0.3)

        # 3. Fetch Parks
        pbar.set_description("Downloading parks/green spaces")
        try:
            parks = ox.features_from_point(
                point,
                tags={'leisure': 'park', 'landuse': 'grass'},
                dist=distance
            )
        except Exception:
            parks = None
        pbar.update(1)

    print("✓ All data downloaded successfully!")

    return MapData(
        roads=roads,
        water=water,
        parks=parks,
        city=city,
        country=country,
        point=point,
        distance=distance,
        theme=None
    )
```

**Step 2: Verify the file was created correctly**

Run: `python -c "from map_data import MapData, get_map_data; print('Import successful')"`
Expected: `Import successful`

**Step 3: Commit**

```bash
git add map_data.py
git commit -m "feat: add MapData dataclass and get_map_data() function

Extract map data fetching into reusable module that will support
both PNG and laser output formats."
```

---

### Task 2: Refactor create_poster() to use MapData

**Files:**
- Modify: `create_map_poster.py:1-17` (add import)
- Modify: `create_map_poster.py:216-244` (refactor data fetching)

**Step 1: Add import for map_data module**

At line 12 (after `import argparse`), add:

```python
from map_data import MapData, get_map_data
```

**Step 2: Modify create_poster() function signature and body**

Replace the `create_poster` function (lines 216-323) with:

```python
def create_poster(city, country, point, dist, output_file, map_data=None):
    """
    Generate a map poster.

    Args:
        city: City name
        country: Country name
        point: (latitude, longitude) tuple
        dist: Map radius in meters
        output_file: Path to save PNG output
        map_data: Optional pre-fetched MapData. If None, data will be fetched.
    """
    # Fetch data if not provided
    if map_data is None:
        map_data = get_map_data(city, country, point, dist)
        map_data.theme = THEME

    G = map_data.roads
    water = map_data.water
    parks = map_data.parks

    print(f"Generating map for {city}, {country}...")

    # 2. Setup Plot
    print("Rendering map...")
    fig, ax = plt.subplots(figsize=(12, 16), facecolor=THEME['bg'])
    ax.set_facecolor(THEME['bg'])
    ax.set_position([0, 0, 1, 1])

    # 3. Plot Layers
    # Layer 1: Polygons
    if water is not None and not water.empty:
        water.plot(ax=ax, facecolor=THEME['water'], edgecolor='none', zorder=1)
    if parks is not None and not parks.empty:
        parks.plot(ax=ax, facecolor=THEME['parks'], edgecolor='none', zorder=2)

    # Layer 2: Roads with hierarchy coloring
    print("Applying road hierarchy colors...")
    edge_colors = get_edge_colors_by_type(G)
    edge_widths = get_edge_widths_by_type(G)

    ox.plot_graph(
        G, ax=ax, bgcolor=THEME['bg'],
        node_size=0,
        edge_color=edge_colors,
        edge_linewidth=edge_widths,
        show=False, close=False
    )

    # Layer 3: Gradients (Top and Bottom)
    create_gradient_fade(ax, THEME['gradient_color'], location='bottom', zorder=10)
    create_gradient_fade(ax, THEME['gradient_color'], location='top', zorder=10)

    # 4. Typography using Roboto font
    if FONTS:
        font_main = FontProperties(fname=FONTS['bold'], size=60)
        font_top = FontProperties(fname=FONTS['bold'], size=40)
        font_sub = FontProperties(fname=FONTS['light'], size=22)
        font_coords = FontProperties(fname=FONTS['regular'], size=14)
    else:
        # Fallback to system fonts
        font_main = FontProperties(family='monospace', weight='bold', size=60)
        font_top = FontProperties(family='monospace', weight='bold', size=40)
        font_sub = FontProperties(family='monospace', weight='normal', size=22)
        font_coords = FontProperties(family='monospace', size=14)

    spaced_city = "  ".join(list(city.upper()))

    # --- BOTTOM TEXT ---
    ax.text(0.5, 0.14, spaced_city, transform=ax.transAxes,
            color=THEME['text'], ha='center', fontproperties=font_main, zorder=11)

    ax.text(0.5, 0.10, country.upper(), transform=ax.transAxes,
            color=THEME['text'], ha='center', fontproperties=font_sub, zorder=11)

    lat, lon = point
    coords = f"{lat:.4f}° N / {lon:.4f}° E" if lat >= 0 else f"{abs(lat):.4f}° S / {lon:.4f}° E"
    if lon < 0:
        coords = coords.replace("E", "W")

    ax.text(0.5, 0.07, coords, transform=ax.transAxes,
            color=THEME['text'], alpha=0.7, ha='center', fontproperties=font_coords, zorder=11)

    ax.plot([0.4, 0.6], [0.125, 0.125], transform=ax.transAxes,
            color=THEME['text'], linewidth=1, zorder=11)

    # --- ATTRIBUTION (bottom right) ---
    if FONTS:
        font_attr = FontProperties(fname=FONTS['light'], size=8)
    else:
        font_attr = FontProperties(family='monospace', size=8)

    ax.text(0.98, 0.02, "© OpenStreetMap contributors", transform=ax.transAxes,
            color=THEME['text'], alpha=0.5, ha='right', va='bottom',
            fontproperties=font_attr, zorder=11)

    # 5. Save
    print(f"Saving to {output_file}...")
    plt.savefig(output_file, dpi=300, facecolor=THEME['bg'])
    plt.close()
    print(f"✓ Done! Poster saved as {output_file}")
```

**Step 3: Verify PNG generation still works**

Run: `python create_map_poster.py --city "Paris" --country "France" --theme noir --distance 5000`

Expected:
- Map data downloads successfully
- PNG file is created in `posters/` directory
- No errors

**Step 4: Commit**

```bash
git add create_map_poster.py
git commit -m "refactor: update create_poster() to use MapData

- Add optional map_data parameter
- Extract data fetching to get_map_data()
- Maintains backward compatibility - fetches data if not provided"
```

---

### Task 3: Verify backward compatibility

**Files:**
- None (verification only)

**Step 1: Run the tool with default behavior**

Run: `python create_map_poster.py --city "London" --country "UK" --theme feature_based --distance 4000`

Expected:
- Coordinates lookup succeeds
- Map data downloads (3 steps)
- PNG renders and saves to `posters/`
- Output shows `✓ Done! Poster saved as posters/london_feature_based_YYYYMMDD_HHMMSS.png`

**Step 2: Verify the output file exists and is valid**

Run: `ls -la posters/london_feature_based_*.png | tail -1`

Expected: File exists with size > 500KB

**Step 3: Run list-themes to verify other CLI paths work**

Run: `python create_map_poster.py --list-themes`

Expected: Lists all 17 themes without errors

---

## Phase 1 Complete

After completing all tasks:
- `map_data.py` exists with `MapData` dataclass and `get_map_data()` function
- `create_map_poster.py` imports and uses the new module
- Existing PNG generation works unchanged
- Ready for Phase 2: Laser Profile System
