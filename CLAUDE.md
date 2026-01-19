# Map to Poster

Last verified: 2026-01-18

## Tech Stack
- Language: Python 3.x
- Map Data: OSMnx, GeoPandas, Shapely
- Rendering: Matplotlib (PNG), svgwrite (SVG)
- Geocoding: Nominatim via geopy

## Commands
- `python create_map_poster.py --city <city> --country <country>` - Generate poster
- `python create_map_poster.py --list-themes` - List available themes
- `python create_map_poster.py --list-profiles` - List laser profiles
- `python create_map_poster.py --format laser` - Generate SVG + XCS for laser cutter

## Project Structure
- `create_map_poster.py` - Main CLI and PNG rendering
- `map_data.py` - Shared MapData dataclass and OSM fetching
- `svg_renderer.py` - SVG generation for laser cutters
- `xcs_generator.py` - XTool Creative Space project files
- `laser_config.py` - YAML laser profile loading
- `laser_theme.py` - Laser-specific theme options
- `themes/` - JSON theme files (colors, styling)
- `laser_profiles/` - YAML laser power/speed profiles
- `posters/` - Generated output files

## Module Contracts

### map_data.py
- **Exposes**: `MapData` dataclass, `get_map_data(city, country, point, distance)`
- **Guarantees**: Returns roads (always), water/parks (or None)
- **Used by**: create_map_poster.py, svg_renderer.py, xcs_generator.py

### laser_config.py
- **Exposes**: `LaserProfile`, `load_laser_profile(name)`, `get_available_profiles()`
- **Guarantees**: Validates all power/speed/density values against ranges
- **Raises**: `LaserProfileError` on invalid YAML or missing fields

### svg_renderer.py
- **Exposes**: `create_laser_svg()`, `PhysicalSize`, `SUPPORTED_SIZES`
- **Guarantees**: SVG with layers: water, parks, roads, text
- **Uses**: map_data.MapData, laser_theme.LaserThemeOptions

### xcs_generator.py
- **Exposes**: `create_xcs_file()`
- **Guarantees**: XCS JSON with power/speed per road type from profile
- **Uses**: map_data.MapData, laser_config.LaserProfile, svg_renderer functions

## Output Formats
| Format | Files Generated | Use Case |
|--------|-----------------|----------|
| png | `.png` | Wall art prints |
| svg | `.svg` | Laser cutter (color-coded) |
| xcs | `.xcs` | XTool Creative Space direct import |
| laser | `.svg` + `.xcs` | Both laser formats |
| all | `.png` + `.svg` + `.xcs` | Everything |

## Key Decisions
- Separate MapData from rendering: Fetch once, render to multiple formats
- Color-coded SVG layers: XCS imports colors as separate processing groups
- YAML for laser profiles: Human-editable power/speed settings per material

## Boundaries
- Safe to edit: All Python files, themes/, laser_profiles/
- Never edit: venv/, fonts/ (binary assets)
