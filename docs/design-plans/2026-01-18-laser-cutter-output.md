# Laser Cutter Output Design

## Definition of Done

The laser cutter output feature is complete when the maptoposter tool can generate both SVG and XCS files suitable for XTool laser cutters. Success means a user can run a single command with `--format laser` to produce files that open directly in XTool Creative Space with pre-configured power/speed settings for their chosen material profile. The existing PNG output remains fully functional and unchanged, and users can customize laser settings through YAML profile files without modifying code.

## Summary

This design adds laser cutter output capabilities to maptoposter, enabling users to engrave street maps onto wood or other materials using XTool laser cutters. The implementation extracts map data (roads, water, parks, labels) into a shared data structure that feeds both the existing matplotlib PNG renderer and new laser output modules. The laser output produces two file formats: structured SVG files with color-coded layers representing different laser operations, and XCS project files that open directly in XTool Creative Space with pre-configured power and speed settings.

The approach preserves backward compatibility by refactoring data extraction into a reusable layer without modifying the existing PNG generation logic. A YAML-based configuration system allows users to define machine-specific laser profiles (power, speed, density) for different materials and road types. The design follows existing patterns in the codebase, extending the JSON theme system with optional laser-specific options and reusing the established road classification hierarchy.

## Glossary

- **SVG (Scalable Vector Graphics)**: An XML-based vector image format that laser cutters can interpret as cutting/engraving paths
- **XCS (XTool Creative Space)**: Proprietary project file format used by XTool laser cutter software
- **OSM (OpenStreetMap)**: Open-source map database providing geographic data including roads, water bodies, and parks
- **NetworkX**: Python library for working with graph structures; used here to represent road networks as nodes and edges
- **GeoDataFrame**: Pandas DataFrame variant from GeoPandas library that handles geographic data with geometry columns
- **matplotlib**: Python plotting library used for the existing PNG poster generation
- **svgwrite**: Python library for programmatically generating SVG files
- **EPSG:4326**: Standard geographic coordinate system using latitude/longitude
- **UTM (Universal Transverse Mercator)**: Projected coordinate system that converts lat/lon to meters for accurate distance calculations
- **viewBox**: SVG attribute that defines the coordinate system for vector graphics independent of display size
- **Raster engrave**: Laser operation that fills an area by scanning back and forth with the beam
- **Vector engrave**: Laser operation that follows path outlines (also called "score mode")
- **Shapely**: Python library for geometric operations on shapes like polygons and lines
- **dataclass**: Python decorator that auto-generates class methods for structured data objects
- **YAML**: Human-readable configuration file format using key-value pairs and indentation

## Architecture

### Dual Renderer Approach

The design introduces a shared data extraction layer that feeds both the existing matplotlib renderer and a new laser output module. This preserves backward compatibility while enabling new output formats.

```
                    ┌──────────────────┐
                    │  get_map_data()  │  ← NEW: Extract data once
                    │  returns MapData │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                              ▼
    ┌─────────────────┐            ┌─────────────────┐
    │ create_poster() │            │ create_laser()  │  ← NEW
    │  (matplotlib)   │            │ (svgwrite+json) │
    │  → PNG output   │            │ → SVG + XCS     │
    └─────────────────┘            └─────────────────┘
```

### Core Data Structure

**MapData** (new dataclass) holds extracted map information:
- `roads`: List of (geometry, road_type) tuples from NetworkX graph edges
- `water`: List of polygon geometries from GeoDataFrame
- `parks`: List of polygon geometries from GeoDataFrame
- `metadata`: City name, country, coordinates, bounding box
- `theme`: Loaded theme dictionary

### SVG Generation

Uses **svgwrite** library for structured SVG with color-coded layers for XCS compatibility:
- Roads: Red strokes (`#FF0000` variants) with varying darkness for 5 power levels
- Water: Yellow fill (`#FFFF00`) for raster engrave
- Parks: Light yellow fill (`#FFFFAA`) for lighter engrave
- Text: Black fill (`#000000`) for solid engrave, converted to paths

Physical sizing controlled by SVG `width`/`height` attributes in inches with corresponding viewBox.

### XCS Generation

Generates XTool Creative Space project files (JSON format) with:
- Canvas structure containing path elements with SVG path data
- Layer definitions mapped to colors
- Per-element power/speed settings under `device.data.value[].displays`
- Material preset (3mm Basswood Plywood)

Processing modes:
- `VECTOR_ENGRAVING`: Score mode for road lines
- `FILL_VECTOR_ENGRAVING`: Raster mode for water/parks fills
- Solid engrave for text elements

### Configuration System

YAML-based laser profiles stored in `laser_profiles/` directory:

```yaml
machine: P2
material:
  name: "3mm Basswood Plywood"
  thickness: 3

operations:
  score:
    roads_motorway:    { power: 25, speed: 100 }
    roads_primary:     { power: 22, speed: 120 }
    roads_secondary:   { power: 18, speed: 140 }
    roads_tertiary:    { power: 15, speed: 160 }
    roads_residential: { power: 12, speed: 180 }

  engrave_fill:
    water:  { power: 40, speed: 200, density: 100 }
    parks:  { power: 30, speed: 200, density: 80 }

  engrave_solid:
    text:   { power: 50, speed: 150 }
```

This allows power/speed tuning without code changes.

### Coordinate Transformation

Pipeline from OSM data to SVG coordinates:
1. OSM lat/lon (EPSG:4326) → Project to local meters (UTM)
2. Clip to bounding box based on `--distance` parameter
3. Scale to physical size based on `--size` parameter
4. Flip Y-axis (SVG origin is top-left)

## Existing Patterns

### Theme System
Investigation found extensible JSON theme system in `themes/` directory. Design extends this pattern:
- Existing themes define colors for roads, water, parks, text
- New laser themes add optional `laser` section for element inclusion flags
- Theme loading already has fallback pattern for missing optional keys

### Road Classification
Investigation found road type classification in `get_edge_colors_by_type()` and `get_edge_widths_by_type()` functions (lines 134-194). Design follows same 5-tier hierarchy:
- motorway/motorway_link
- primary/trunk and links
- secondary and links
- tertiary and links
- residential/living_street/unclassified

### Output Generation
Investigation found tightly coupled matplotlib rendering in `create_poster()` (lines 216-323). Design diverges by extracting data to shared MapData structure, enabling multiple output backends without modifying existing renderer.

## Implementation Phases

### Phase 1: Data Extraction Layer
**Goal:** Extract map data fetching and processing into reusable module

**Components:**
- `MapData` dataclass in `map_data.py` — holds roads, water, parks, metadata
- `get_map_data()` function — extracts data fetching from `create_poster()`
- Refactor `create_poster()` to consume MapData

**Dependencies:** None (first phase)

**Done when:** Existing PNG generation works unchanged using new data extraction layer

### Phase 2: Laser Profile System
**Goal:** YAML-based configuration for machine/material power settings

**Components:**
- `laser_profiles/` directory with YAML schema
- `laser_profiles/p2_basswood_3mm.yaml` — default profile
- `load_laser_profile()` function in `laser_config.py`
- Profile validation and error handling

**Dependencies:** Phase 1

**Done when:** Profiles load correctly, validation rejects malformed files, missing profiles produce clear errors

### Phase 3: Laser Theme Extension
**Goal:** Extend theme system for laser-specific options

**Components:**
- `themes/laser_mono.json` — laser-optimized theme
- Extended theme schema with optional `laser` section
- Theme loader updates to handle laser options

**Dependencies:** Phase 1

**Done when:** Laser themes load with element inclusion flags, existing themes work unchanged

### Phase 4: SVG Renderer
**Goal:** Generate structured SVG files for laser cutting

**Components:**
- `svg_renderer.py` — svgwrite-based SVG generation
- Coordinate transformation (lat/lon → SVG viewBox)
- Road geometry extraction from NetworkX edges
- Polygon conversion from Shapely to SVG paths
- Text-to-path conversion for city/country labels

**Dependencies:** Phases 1, 3

**Done when:** SVG files generate with correct structure, color-coded layers, and physical sizing in inches

### Phase 5: XCS Generator
**Goal:** Generate XTool Creative Space project files

**Components:**
- `xcs_generator.py` — JSON-based XCS file generation
- XCS structure builder matching reverse-engineered format
- Power/speed mapping from laser profiles
- Element-to-processing-mode assignment

**Dependencies:** Phases 1, 2, 4

**Done when:** XCS files open in XTool Creative Space with correct layers and pre-mapped power settings

### Phase 6: CLI Integration
**Goal:** Command-line interface for laser output

**Components:**
- New arguments: `--format`, `--size`, `--laser-profile`, `--laser-theme`
- Argument validation (valid sizes, existing profiles)
- Output file naming for SVG/XCS files
- Backward compatibility (default behavior unchanged)

**Dependencies:** Phases 4, 5

**Done when:** CLI generates correct outputs for all format combinations, existing usage works unchanged

## Additional Considerations

**Error handling:**
- Missing OSM data (water/parks): Skip those layers gracefully, roads always present
- Invalid laser profile: Clear error listing available profiles
- XCS generation failures: Validate structure before writing, log warnings for unconvertible elements

**Physical sizes supported:**
- 8x12, 12x18, 18x24 inches (standard plywood sizes)
- Size validation in CLI rejects unsupported dimensions

**Text handling:**
- Text converted to paths using font library (fonttools or similar)
- Fallback to warning if text conversion fails
