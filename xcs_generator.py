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
