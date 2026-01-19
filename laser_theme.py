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
