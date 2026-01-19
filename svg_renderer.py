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
