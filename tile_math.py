"""
Web Mercator tile math.

Standalone replacement for the small subset of the `mercantile` library
used by this plugin (tiles-covering-bbox + tile-to-bbox). Pure stdlib,
no external dependencies.
"""

import math
from collections import namedtuple

Tile = namedtuple('Tile', ['x', 'y', 'z'])
Bounds = namedtuple('Bounds', ['west', 'south', 'east', 'north'])

# Web Mercator is undefined at the poles; this is the clamp used by every
# tile server.
_MAX_LAT = 85.0511287798


def _clamp_lat(lat):
    return max(min(lat, _MAX_LAT), -_MAX_LAT)


def _lnglat_to_tile(lng, lat, zoom):
    n = 1 << zoom
    x = int((lng + 180.0) / 360.0 * n)
    lat_rad = math.radians(_clamp_lat(lat))
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tiles(west, south, east, north, zooms):
    """Yield every tile covering the bbox at the given zoom level(s)."""
    if isinstance(zooms, int):
        zooms = [zooms]
    for z in zooms:
        x_min, y_max = _lnglat_to_tile(west, south, z)
        x_max, y_min = _lnglat_to_tile(east, north, z)
        max_idx = (1 << z) - 1
        x_min = max(0, min(x_min, max_idx))
        x_max = max(0, min(x_max, max_idx))
        y_min = max(0, min(y_min, max_idx))
        y_max = max(0, min(y_max, max_idx))
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                yield Tile(x=x, y=y, z=z)


def bounds(x, y, z):
    """Return the geographic bounds of a single tile."""
    n = 1 << z
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return Bounds(west=west, south=south, east=east, north=north)
