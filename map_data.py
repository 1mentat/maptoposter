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
