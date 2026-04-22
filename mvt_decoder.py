"""
Minimal Mapbox Vector Tile (MVT) decoder — Point geometries only.

This plugin only ever queries Mapillary's point-feature layers, so we
skip the complexity of LINESTRING / POLYGON decoding and avoid needing
the `protobuf` runtime (which ships compiled binaries). Output shape is
compatible with `mapbox_vector_tile.decode()` for the fields this plugin
uses: {layer_name: {'extent': int, 'features': [{'id', 'properties',
'geometry': {'type': 'Point'|'MultiPoint', 'coordinates': [...]}}]}}.

MVT spec: https://github.com/mapbox/vector-tile-spec/tree/master/2.1
"""

import struct

# ---- Protobuf wire types ----

_WIRE_VARINT = 0
_WIRE_FIXED64 = 1
_WIRE_LENGTH_DELIMITED = 2
_WIRE_FIXED32 = 5

# ---- MVT field numbers (from the .proto spec) ----

# Tile
_TILE_LAYERS = 3

# Layer
_LAYER_NAME = 1
_LAYER_FEATURES = 2
_LAYER_KEYS = 3
_LAYER_VALUES = 4
_LAYER_EXTENT = 5

# Feature
_FEATURE_ID = 1
_FEATURE_TAGS = 2
_FEATURE_TYPE = 3
_FEATURE_GEOMETRY = 4

# Value (one-of)
_VALUE_STRING = 1
_VALUE_FLOAT = 2
_VALUE_DOUBLE = 3
_VALUE_INT = 4
_VALUE_UINT = 5
_VALUE_SINT = 6
_VALUE_BOOL = 7

# Geometry feature types
_TYPE_POINT = 1

# Geometry commands
_CMD_MOVETO = 1


# ---- Primitive readers ----

def _read_varint(data, pos):
    result = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise ValueError("Truncated varint")
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7
        if shift > 70:
            raise ValueError("Varint too long")


def _read_tag(data, pos):
    tag, pos = _read_varint(data, pos)
    return tag >> 3, tag & 0x07, pos


def _skip(data, pos, wire_type):
    if wire_type == _WIRE_VARINT:
        _, pos = _read_varint(data, pos)
    elif wire_type == _WIRE_FIXED64:
        pos += 8
    elif wire_type == _WIRE_LENGTH_DELIMITED:
        length, pos = _read_varint(data, pos)
        pos += length
    elif wire_type == _WIRE_FIXED32:
        pos += 4
    else:
        raise ValueError("Unknown wire type: %d" % wire_type)
    return pos


def _zigzag(n):
    return (n >> 1) ^ -(n & 1)


# ---- Message decoders ----

def _decode_value(data):
    """Decode a Value message to a Python primitive."""
    pos = 0
    n = len(data)
    value = None
    while pos < n:
        field, wire, pos = _read_tag(data, pos)
        if field == _VALUE_STRING and wire == _WIRE_LENGTH_DELIMITED:
            length, pos = _read_varint(data, pos)
            value = data[pos:pos + length].decode('utf-8', errors='replace')
            pos += length
        elif field == _VALUE_FLOAT and wire == _WIRE_FIXED32:
            value = struct.unpack_from('<f', data, pos)[0]
            pos += 4
        elif field == _VALUE_DOUBLE and wire == _WIRE_FIXED64:
            value = struct.unpack_from('<d', data, pos)[0]
            pos += 8
        elif field == _VALUE_INT and wire == _WIRE_VARINT:
            v, pos = _read_varint(data, pos)
            if v & (1 << 63):
                v -= (1 << 64)
            value = v
        elif field == _VALUE_UINT and wire == _WIRE_VARINT:
            value, pos = _read_varint(data, pos)
        elif field == _VALUE_SINT and wire == _WIRE_VARINT:
            v, pos = _read_varint(data, pos)
            value = _zigzag(v)
        elif field == _VALUE_BOOL and wire == _WIRE_VARINT:
            v, pos = _read_varint(data, pos)
            value = bool(v)
        else:
            pos = _skip(data, pos, wire)
    return value


def _decode_point_geometry(cmds, extent):
    """Decode a Point / MultiPoint geometry command stream.

    Returns a dict matching the GeoJSON-style output of mapbox_vector_tile:
    y is flipped so y=0 is south and y=extent is north.
    """
    x = 0
    y = 0
    i = 0
    n = len(cmds)
    points = []
    while i < n:
        header = cmds[i]
        i += 1
        cmd = header & 0x07
        count = header >> 3
        if cmd != _CMD_MOVETO:
            break
        for _ in range(count):
            if i + 1 >= n:
                break
            x += _zigzag(cmds[i])
            y += _zigzag(cmds[i + 1])
            i += 2
            points.append((x, extent - y))
    if not points:
        return None
    if len(points) == 1:
        return {'type': 'Point', 'coordinates': [points[0][0], points[0][1]]}
    return {
        'type': 'MultiPoint',
        'coordinates': [[px, py] for (px, py) in points],
    }


def _decode_feature(data, keys, values, extent):
    pos = 0
    n = len(data)
    feat_id = None
    tag_indices = []
    ftype = 0
    geometry_cmds = []

    while pos < n:
        field, wire, pos = _read_tag(data, pos)
        if field == _FEATURE_ID and wire == _WIRE_VARINT:
            feat_id, pos = _read_varint(data, pos)
        elif field == _FEATURE_TAGS and wire == _WIRE_LENGTH_DELIMITED:
            length, pos = _read_varint(data, pos)
            end = pos + length
            while pos < end:
                v, pos = _read_varint(data, pos)
                tag_indices.append(v)
        elif field == _FEATURE_TAGS and wire == _WIRE_VARINT:
            v, pos = _read_varint(data, pos)
            tag_indices.append(v)
        elif field == _FEATURE_TYPE and wire == _WIRE_VARINT:
            ftype, pos = _read_varint(data, pos)
        elif field == _FEATURE_GEOMETRY and wire == _WIRE_LENGTH_DELIMITED:
            length, pos = _read_varint(data, pos)
            end = pos + length
            while pos < end:
                v, pos = _read_varint(data, pos)
                geometry_cmds.append(v)
        else:
            pos = _skip(data, pos, wire)

    properties = {}
    for idx in range(0, len(tag_indices) - 1, 2):
        k = tag_indices[idx]
        v = tag_indices[idx + 1]
        if 0 <= k < len(keys) and 0 <= v < len(values):
            properties[keys[k]] = values[v]

    # Mapillary encodes the feature ID inside the tag list under key "id"
    # too; keep a consistent spelling.
    if feat_id is not None and 'id' not in properties:
        properties['id'] = feat_id

    geometry = None
    if ftype == _TYPE_POINT:
        geometry = _decode_point_geometry(geometry_cmds, extent)

    return {
        'id': feat_id,
        'properties': properties,
        'geometry': geometry,
    }


def _decode_layer(data):
    pos = 0
    n = len(data)
    name = None
    extent = 4096
    features_blobs = []
    keys = []
    values = []

    while pos < n:
        field, wire, pos = _read_tag(data, pos)
        if field == _LAYER_NAME and wire == _WIRE_LENGTH_DELIMITED:
            length, pos = _read_varint(data, pos)
            name = data[pos:pos + length].decode('utf-8', errors='replace')
            pos += length
        elif field == _LAYER_FEATURES and wire == _WIRE_LENGTH_DELIMITED:
            length, pos = _read_varint(data, pos)
            features_blobs.append(bytes(data[pos:pos + length]))
            pos += length
        elif field == _LAYER_KEYS and wire == _WIRE_LENGTH_DELIMITED:
            length, pos = _read_varint(data, pos)
            keys.append(data[pos:pos + length].decode('utf-8', errors='replace'))
            pos += length
        elif field == _LAYER_VALUES and wire == _WIRE_LENGTH_DELIMITED:
            length, pos = _read_varint(data, pos)
            values.append(_decode_value(bytes(data[pos:pos + length])))
            pos += length
        elif field == _LAYER_EXTENT and wire == _WIRE_VARINT:
            extent, pos = _read_varint(data, pos)
        else:
            pos = _skip(data, pos, wire)

    features = [
        _decode_feature(fb, keys, values, extent) for fb in features_blobs
    ]
    return name, {'extent': extent, 'features': features}


def decode(data):
    """Decode an MVT tile into `{layer_name: {'extent': int, 'features': [...]}}`.

    Accepts `bytes`, `bytearray`, or `memoryview`. Only POINT geometries
    are decoded; LINESTRING / POLYGON features yield `geometry=None`.
    """
    if isinstance(data, memoryview):
        data = bytes(data)
    elif isinstance(data, bytearray):
        data = bytes(data)
    if not data:
        return {}

    pos = 0
    n = len(data)
    result = {}
    while pos < n:
        field, wire, pos = _read_tag(data, pos)
        if field == _TILE_LAYERS and wire == _WIRE_LENGTH_DELIMITED:
            length, pos = _read_varint(data, pos)
            name, layer = _decode_layer(data[pos:pos + length])
            if name:
                result[name] = layer
            pos += length
        else:
            pos = _skip(data, pos, wire)
    return result
