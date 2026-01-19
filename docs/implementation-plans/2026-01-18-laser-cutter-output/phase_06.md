# Laser Cutter Output Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:subagent-driven-development to implement this plan task-by-task.

**Goal:** Command-line interface for laser output

**Architecture:** Add new CLI arguments for format selection, physical size, laser profile, and laser theme. Maintain backward compatibility with existing PNG workflow.

**Tech Stack:** Python argparse

**Scope:** 6 phases from original design (phases 1-6)

**Codebase verified:** 2026-01-18

---

## Phase 6: CLI Integration

**Goal:** Command-line interface for laser output

**Done when:** CLI generates correct outputs for all format combinations, existing usage works unchanged

---

### Task 1: Add laser output imports to create_map_poster.py

**Files:**
- Modify: `create_map_poster.py:1-15` (add imports)

**Step 1: Add imports for laser modules**

After the existing imports (around line 12-13), add:

```python
from map_data import MapData, get_map_data
from svg_renderer import create_laser_svg, PhysicalSize, SUPPORTED_SIZES
from xcs_generator import create_xcs_file
from laser_config import load_laser_profile, get_available_profiles, LaserProfileError
from laser_theme import get_laser_options
```

**Step 2: Verify imports work**

Run: `python -c "import create_map_poster; print('Imports successful')"`

Expected: `Imports successful`

**Step 3: Commit**

```bash
git add create_map_poster.py
git commit -m "chore: add laser module imports to create_map_poster"
```

---

### Task 2: Add new CLI arguments

**Files:**
- Modify: `create_map_poster.py:406-425` (argparse setup)

**Step 1: Add new arguments to the argument parser**

After the existing `--list-themes` argument (around line 423), add:

```python
    parser.add_argument('--format', '-f', type=str, default='png',
                        choices=['png', 'laser', 'svg', 'xcs', 'all'],
                        help='Output format: png (default), laser (svg+xcs), svg, xcs, or all')
    parser.add_argument('--size', '-s', type=str, default='12x18',
                        help=f'Physical size for laser output (default: 12x18). Supported: {", ".join(SUPPORTED_SIZES)}')
    parser.add_argument('--laser-profile', '-lp', type=str, default='p2_basswood_3mm',
                        help='Laser profile for power/speed settings (default: p2_basswood_3mm)')
    parser.add_argument('--list-profiles', action='store_true',
                        help='List all available laser profiles')
```

**Step 2: Verify argument parsing**

Run: `python create_map_poster.py --help`

Expected: Help output shows new `--format`, `--size`, `--laser-profile`, and `--list-profiles` arguments

**Step 3: Commit**

```bash
git add create_map_poster.py
git commit -m "feat: add CLI arguments for laser output

- --format: png, laser, svg, xcs, or all
- --size: physical dimensions for laser output
- --laser-profile: power/speed profile selection
- --list-profiles: show available laser profiles"
```

---

### Task 3: Add list_profiles function

**Files:**
- Modify: `create_map_poster.py` (add function after list_themes)

**Step 1: Add list_profiles function**

After the `list_themes()` function (around line 404), add:

```python
def list_profiles():
    """List all available laser profiles with descriptions."""
    available_profiles = get_available_profiles()
    if not available_profiles:
        print("No laser profiles found in 'laser_profiles/' directory.")
        return

    print("\nAvailable Laser Profiles:")
    print("-" * 60)
    for profile_name in available_profiles:
        try:
            profile = load_laser_profile(profile_name)
            print(f"  {profile_name}")
            print(f"    Machine: {profile.machine}")
            print(f"    Material: {profile.material_name} ({profile.material_thickness}mm)")
            print()
        except LaserProfileError as e:
            print(f"  {profile_name}")
            print(f"    Error loading: {e}")
            print()
```

**Step 2: Verify function works**

Run: `python -c "from create_map_poster import list_profiles; list_profiles()"`

Expected: Lists available profiles with machine/material info

**Step 3: Commit**

```bash
git add create_map_poster.py
git commit -m "feat: add list_profiles function for laser profile discovery"
```

---

### Task 4: Add generate_laser_filename function

**Files:**
- Modify: `create_map_poster.py` (add function after generate_output_filename)

**Step 1: Add generate_laser_filename function**

After the `generate_output_filename()` function (around line 49), add:

```python
def generate_laser_filename(city, theme_name, size_str, extension):
    """
    Generate output filename for laser files.

    Args:
        city: City name
        theme_name: Theme name
        size_str: Size string like '12x18'
        extension: File extension ('svg' or 'xcs')

    Returns:
        Full path to output file
    """
    if not os.path.exists(POSTERS_DIR):
        os.makedirs(POSTERS_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city.lower().replace(' ', '_')
    size_slug = size_str.replace('x', '_')
    filename = f"{city_slug}_{theme_name}_{size_slug}_{timestamp}.{extension}"
    return os.path.join(POSTERS_DIR, filename)
```

**Step 2: Verify function works**

Run: `python -c "from create_map_poster import generate_laser_filename; print(generate_laser_filename('Paris', 'laser_mono', '12x18', 'svg'))"`

Expected: Path like `posters/paris_laser_mono_12_18_YYYYMMDD_HHMMSS.svg`

**Step 3: Commit**

```bash
git add create_map_poster.py
git commit -m "feat: add generate_laser_filename for laser output file naming"
```

---

### Task 5: Add create_laser_output function

**Files:**
- Modify: `create_map_poster.py` (add function after create_poster)

**Step 1: Add create_laser_output function**

After the `create_poster()` function (around line 323), add:

```python
def create_laser_output(city, country, point, dist, theme_name, size_str,
                        profile_name, formats):
    """
    Generate laser cutter output files.

    Args:
        city: City name
        country: Country name
        point: (latitude, longitude) tuple
        dist: Map radius in meters
        theme_name: Theme name to use
        size_str: Physical size like '12x18'
        profile_name: Laser profile name
        formats: List of formats to generate ('svg', 'xcs')

    Returns:
        List of generated file paths
    """
    # Load theme
    theme = load_theme(theme_name)

    # Load laser profile
    try:
        profile = load_laser_profile(profile_name)
    except LaserProfileError as e:
        print(f"Error: {e}")
        return []

    # Parse size
    try:
        size = PhysicalSize.from_string(size_str)
    except ValueError as e:
        print(f"Error: {e}")
        print(f"Supported sizes: {', '.join(SUPPORTED_SIZES)}")
        return []

    # Fetch map data
    map_data = get_map_data(city, country, point, dist)
    map_data.theme = theme

    generated_files = []

    # Generate SVG
    if 'svg' in formats:
        svg_path = generate_laser_filename(city, theme_name, size_str, 'svg')
        create_laser_svg(map_data, svg_path, size, theme)
        generated_files.append(svg_path)

    # Generate XCS
    if 'xcs' in formats:
        xcs_path = generate_laser_filename(city, theme_name, size_str, 'xcs')
        create_xcs_file(map_data, xcs_path, size, theme, profile)
        generated_files.append(xcs_path)

    return generated_files
```

**Step 2: Verify function compiles**

Run: `python -c "from create_map_poster import create_laser_output; print('Function defined')"`

Expected: `Function defined`

**Step 3: Commit**

```bash
git add create_map_poster.py
git commit -m "feat: add create_laser_output function for laser file generation"
```

---

### Task 6: Update main block to handle new arguments

**Files:**
- Modify: `create_map_poster.py:432-471` (main block)

**Step 1: Update main block to handle list-profiles**

After the `if args.list_themes:` block (around line 435), add:

```python
    # List profiles if requested
    if args.list_profiles:
        list_profiles()
        os.sys.exit(0)
```

**Step 2: Update main block to validate and process format argument**

Replace the existing try/except block at the end (around lines 458-471) with:

```python
    # Get coordinates
    try:
        coords = get_coordinates(args.city, args.country)
    except Exception as e:
        print(f"\n✗ Error getting coordinates: {e}")
        os.sys.exit(1)

    # Determine which formats to generate
    if args.format == 'png':
        formats = ['png']
    elif args.format == 'laser':
        formats = ['svg', 'xcs']
    elif args.format == 'all':
        formats = ['png', 'svg', 'xcs']
    else:
        formats = [args.format]

    try:
        generated_files = []

        # Generate PNG if requested
        if 'png' in formats:
            output_file = generate_output_filename(args.city, args.theme)
            create_poster(args.city, args.country, coords, args.distance, output_file)
            generated_files.append(output_file)

        # Generate laser formats if requested
        laser_formats = [f for f in formats if f in ['svg', 'xcs']]
        if laser_formats:
            laser_files = create_laser_output(
                args.city, args.country, coords, args.distance,
                args.theme, args.size, args.laser_profile, laser_formats
            )
            generated_files.extend(laser_files)

        print("\n" + "=" * 50)
        print("✓ Generation complete!")
        print("=" * 50)
        for f in generated_files:
            print(f"  {f}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        os.sys.exit(1)
```

**Step 3: Commit**

```bash
git add create_map_poster.py
git commit -m "feat: integrate laser output into CLI main block

- Handle --list-profiles flag
- Route format argument to appropriate generators
- Support png, laser, svg, xcs, and all formats"
```

---

### Task 7: Test backward compatibility (PNG only)

**Files:**
- None (verification only)

**Step 1: Test default PNG generation (no new arguments)**

Run: `python create_map_poster.py --city "Berlin" --country "Germany" --theme noir --distance 4000`

Expected:
- Generates PNG only (default behavior)
- No laser-related output
- File saved to `posters/berlin_noir_*.png`

**Step 2: Test explicit PNG format**

Run: `python create_map_poster.py --city "Madrid" --country "Spain" --theme warm_beige --distance 3000 --format png`

Expected:
- Same as default behavior
- Only PNG generated

---

### Task 8: Test laser format combinations

**Files:**
- None (verification only)

**Step 1: Test --format laser (generates both SVG and XCS)**

Run: `python create_map_poster.py --city "Amsterdam" --country "Netherlands" --theme laser_mono --distance 3000 --format laser --size 8x12`

Expected:
```
...
✓ Generation complete!
==================================================
  posters/amsterdam_laser_mono_8_12_*.svg
  posters/amsterdam_laser_mono_8_12_*.xcs
```

**Step 2: Test --format svg (SVG only)**

Run: `python create_map_poster.py --city "Vienna" --country "Austria" --theme laser_mono --distance 3000 --format svg --size 12x18`

Expected:
- Only SVG generated
- File: `posters/vienna_laser_mono_12_18_*.svg`

**Step 3: Test --format xcs (XCS only)**

Run: `python create_map_poster.py --city "Prague" --country "Czech Republic" --theme laser_mono --distance 3000 --format xcs --size 18x24`

Expected:
- Only XCS generated
- File: `posters/prague_laser_mono_18_24_*.xcs`

**Step 4: Test --format all (PNG + SVG + XCS)**

Run: `python create_map_poster.py --city "Budapest" --country "Hungary" --theme laser_mono --distance 3000 --format all --size 12x18`

Expected:
```
...
✓ Generation complete!
==================================================
  posters/budapest_laser_mono_*.png
  posters/budapest_laser_mono_12_18_*.svg
  posters/budapest_laser_mono_12_18_*.xcs
```

---

### Task 9: Test profile and size validation

**Files:**
- None (verification only)

**Step 1: Test invalid profile error**

Run: `python create_map_poster.py --city "Rome" --country "Italy" --theme laser_mono --distance 3000 --format laser --laser-profile nonexistent`

Expected: Error message listing available profiles

**Step 2: Test invalid size error**

Run: `python create_map_poster.py --city "Rome" --country "Italy" --theme laser_mono --distance 3000 --format laser --size invalid`

Expected: Error about invalid size format

**Step 3: Test --list-profiles**

Run: `python create_map_poster.py --list-profiles`

Expected: Lists all available profiles with machine/material info

---

### Task 10: Update print_examples with laser examples

**Files:**
- Modify: `create_map_poster.py:325-379` (print_examples function)

**Step 1: Add laser examples to print_examples function**

Update the print_examples() function to include laser examples in the usage text:

```python
def print_examples():
    """Print usage examples."""
    print("""
City Map Poster Generator
=========================

Usage:
  python create_map_poster.py --city <city> --country <country> [options]

Examples:
  # Standard PNG poster
  python create_map_poster.py -c "New York" -C "USA" -t noir -d 12000

  # Laser cutter output (SVG + XCS files)
  python create_map_poster.py -c "Paris" -C "France" -t laser_mono -d 8000 --format laser --size 12x18

  # Just SVG for laser
  python create_map_poster.py -c "Tokyo" -C "Japan" -t laser_mono -d 10000 --format svg --size 18x24

  # All formats (PNG + SVG + XCS)
  python create_map_poster.py -c "London" -C "UK" -t laser_mono -d 8000 --format all --size 12x18

  # Custom laser profile
  python create_map_poster.py -c "Berlin" -C "Germany" -t laser_mono -d 6000 --format laser --laser-profile p2_birch_3mm

  # List themes and profiles
  python create_map_poster.py --list-themes
  python create_map_poster.py --list-profiles

Options:
  --city, -c           City name (required)
  --country, -C        Country name (required)
  --theme, -t          Theme name (default: feature_based)
  --distance, -d       Map radius in meters (default: 29000)
  --format, -f         Output format: png, laser, svg, xcs, all (default: png)
  --size, -s           Physical size for laser: 8x12, 12x18, 18x24 (default: 12x18)
  --laser-profile, -lp Laser profile for power/speed (default: p2_basswood_3mm)
  --list-themes        List all available themes
  --list-profiles      List all available laser profiles

Distance guide:
  4000-6000m   Small/dense cities (Venice, Amsterdam old center)
  8000-12000m  Medium cities, focused downtown (Paris, Barcelona)
  15000-20000m Large metros, full city view (Tokyo, Mumbai)

Laser size guide:
  8x12"   Small plaques, gifts
  12x18"  Medium wall art (most common)
  18x24"  Large statement pieces

Available themes can be found in the 'themes/' directory.
Laser profiles can be found in the 'laser_profiles/' directory.
Generated files are saved to 'posters/' directory.
""")
```

**Step 2: Verify examples display correctly**

Run: `python create_map_poster.py`

Expected: Shows updated help with laser examples

**Step 3: Commit**

```bash
git add create_map_poster.py
git commit -m "docs: update CLI help text with laser output examples

Add examples for:
- Laser format (SVG + XCS)
- Individual SVG/XCS formats
- All formats combined
- Custom laser profiles
- Size options"
```

---

### Task 11: Final integration verification

**Files:**
- None (verification only)

**Step 1: Full end-to-end test with all features**

Run:
```bash
python create_map_poster.py \
  --city "Florence" \
  --country "Italy" \
  --theme laser_mono \
  --distance 5000 \
  --format all \
  --size 12x18 \
  --laser-profile p2_basswood_3mm
```

Expected:
- All three files generated (PNG, SVG, XCS)
- No errors
- Files listed at end

**Step 2: Verify generated files exist**

Run: `ls -la posters/florence_laser_mono_*`

Expected: Three files (one .png, one .svg, one .xcs)

**Step 3: Final commit for CLI integration**

```bash
git add -A
git commit -m "feat: complete CLI integration for laser cutter output

Phase 6 complete. Full laser output support with:
- Format selection (png, laser, svg, xcs, all)
- Physical size configuration
- Laser profile selection
- Backward compatible (default PNG behavior unchanged)"
```

---

## Phase 6 Complete

After completing all tasks:
- All laser-related imports added
- New CLI arguments: --format, --size, --laser-profile, --list-profiles
- list_profiles() function shows available profiles
- generate_laser_filename() creates appropriate file names
- create_laser_output() orchestrates laser file generation
- Main block routes format argument to correct generators
- print_examples() includes laser usage examples
- Backward compatibility verified (default PNG behavior unchanged)
- All format combinations tested

**Feature Complete!**

The maptoposter tool now supports:
- PNG poster output (original functionality)
- SVG files for laser cutters
- XCS project files for XTool Creative Space
- Configurable physical sizes (8x12, 12x18, 18x24 inches)
- YAML-based laser profiles for power/speed customization
