"""
Mapillary API Client.

All HTTP goes through QgsNetworkAccessManager (via QgsBlockingNetworkRequest)
so the plugin inherits the user's QGIS proxy, SSL, and authentication
configuration — no direct `requests` dependency.

Vector tiles are decoded with the in-plugin `mvt_decoder` (Point-only,
no protobuf runtime required). Tile math lives in `tile_math`.
"""

import json
import re
import time

from qgis.core import QgsBlockingNetworkRequest, QgsMessageLog, Qgis
from qgis.PyQt.QtCore import QUrl, QUrlQuery
from qgis.PyQt.QtNetwork import QNetworkRequest

from . import tile_math
from . import mvt_decoder


MAPILLARY_TEST_TIMEOUT_MS = 5000


class MapillaryClient:
    """Client for Mapillary API v4."""

    # Token is sent via Authorization header only — never in the URL, so
    # it cannot leak into proxy logs or exception strings.
    TILE_URL = (
        "https://tiles.mapillary.com/maps/vtp/"
        "{tile_layer}/2/{z}/{x}/{y}"
    )
    ENTITY_URL = "https://graph.mapillary.com/{id}"
    TEST_URL = "https://graph.mapillary.com/images"

    def __init__(self, access_token):
        self.token = access_token
        self._auth_header = ("OAuth " + access_token).encode("ascii")

    # ---- Logging ------------------------------------------------------

    def _redact(self, text):
        if not text:
            return text
        text = str(text).replace(self.token, "<redacted>")
        return re.sub(
            r"access_token=[^&\s]+", "access_token=<redacted>", text
        )

    def log(self, msg, level=Qgis.Info):
        QgsMessageLog.logMessage(self._redact(msg), "SignInventory", level)

    # ---- HTTP ---------------------------------------------------------

    def _http_get(self, url, include_auth_header=True, timeout_ms=None):
        """GET `url` via QgsNetworkAccessManager.

        Returns `(status_code, content_bytes)` where `status_code` is
        `None` on a network/SSL failure.
        """
        qurl = url if isinstance(url, QUrl) else QUrl(url)
        req = QNetworkRequest(qurl)
        if include_auth_header:
            req.setRawHeader(b"Authorization", self._auth_header)
        req.setAttribute(
            QNetworkRequest.RedirectPolicyAttribute,
            QNetworkRequest.NoLessSafeRedirectPolicy,
        )
        self._set_transfer_timeout(req, timeout_ms)

        blocking = QgsBlockingNetworkRequest()
        err = blocking.get(req)
        reply = blocking.reply()
        if reply is None or err == QgsBlockingNetworkRequest.NetworkError:
            return None, b""
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        raw = reply.content()
        content = bytes(raw) if raw is not None else b""
        return status, content

    def _set_transfer_timeout(self, req, timeout_ms):
        """Apply a network transfer timeout when the Qt version supports it."""
        if not timeout_ms:
            return

        try:
            req.setTransferTimeout(int(timeout_ms))
            return
        except AttributeError:
            pass
        except TypeError:
            pass

        try:
            req.setAttribute(
                QNetworkRequest.TransferTimeoutAttribute,
                int(timeout_ms),
            )
        except AttributeError:
            pass

    def _build_entity_url(self, entity_id, fields):
        url = QUrl(self.ENTITY_URL.format(id=entity_id))
        q = QUrlQuery()
        q.addQueryItem("fields", fields)
        url.setQuery(q)
        return url

    def _build_tile_url(self, tile_layer, z, x, y):
        url = QUrl(self.TILE_URL.format(tile_layer=tile_layer, z=z, x=x, y=y))
        q = QUrlQuery()
        q.addQueryItem("access_token", self.token)
        url.setQuery(q)
        return url

    # ---- Tile fetch ---------------------------------------------------

    def fetch_features_in_bbox(self, bbox, tile_layer, mvt_layer_name,
                               value_filter=None, callback=None):
        """Fetch map features from Mapillary vector tiles.

        Args:
            bbox: (west, south, east, north) in WGS84
            tile_layer: 'mly_map_feature_traffic_sign' or 'mly_map_feature_point'
            mvt_layer_name: 'traffic_sign' or 'point'
            value_filter: list of values to include (None = all)
            callback: function(progress_pct, message) for progress updates;
                returning False asks the client to stop after the current tile.

        Returns:
            list of feature dicts with id, value, lng, lat, first_seen_at,
            last_seen_at, source_layer
        """
        west, south, east, north = bbox
        tile_list = list(tile_math.tiles(west, south, east, north, zooms=14))
        total_tiles = len(tile_list)

        self.log(
            "Querying {} tiles for {} in bbox {}".format(
                total_tiles, mvt_layer_name, bbox
            )
        )

        all_features = []
        seen_ids = set()

        for i, tile in enumerate(tile_list):
            url = self._build_tile_url(
                tile_layer=tile_layer, z=14, x=tile.x, y=tile.y,
            )

            status, content = self._http_get(url, include_auth_header=False)

            if status == 429:
                self.log("Rate limited — waiting 60s", Qgis.Warning)
                time.sleep(60)
                status, content = self._http_get(url, include_auth_header=False)

            if status in (401, 403):
                raise RuntimeError(
                    "Mapillary rejected vector-tile access for the configured "
                    "token (HTTP {}). Open Settings and test or replace the "
                    "token.".format(status)
                )

            if status != 200 or not content:
                if status not in (None, 404):
                    self.log(
                        "Tile request for {} returned HTTP {}".format(
                            mvt_layer_name, status
                        ),
                        Qgis.Warning,
                    )
                continue

            try:
                tile_data = mvt_decoder.decode(content)
            except Exception as e:
                self.log("MVT decode error: {}".format(e), Qgis.Warning)
                continue

            if mvt_layer_name not in tile_data:
                continue

            layer = tile_data[mvt_layer_name]
            extent = layer.get('extent', 4096)

            for feat in layer.get('features', []):
                props = feat.get('properties') or {}
                feat_id = props.get('id') or feat.get('id')
                feat_value = props.get('value', 'unknown')
                if value_filter and feat_value not in value_filter:
                    continue

                geom = feat.get('geometry') or {}
                if geom.get('type') != 'Point':
                    continue
                raw_coords = geom.get('coordinates') or []
                if len(raw_coords) < 2:
                    continue
                lng, lat = self._mvt_to_lnglat(
                    raw_coords, tile.x, tile.y, 14, extent
                )
                if not self._point_in_bbox(lng, lat, bbox):
                    continue
                if feat_id in seen_ids:
                    continue
                if feat_id is not None:
                    seen_ids.add(feat_id)

                all_features.append({
                    'id': feat_id,
                    'value': feat_value,
                    'lng': lng,
                    'lat': lat,
                    'first_seen_at': props.get('first_seen_at'),
                    'last_seen_at': props.get('last_seen_at'),
                    'source_layer': mvt_layer_name,
                })

            if callback:
                pct = int((i + 1) / total_tiles * 100)
                keep_going = callback(
                    pct,
                    "Fetched {} tile {}/{}".format(
                        mvt_layer_name, i + 1, total_tiles
                    ),
                )
                if keep_going is False:
                    break

        self.log(
            "Found {} unique {} features from {} tiles".format(
                len(all_features), mvt_layer_name, total_tiles
            )
        )
        return all_features

    def fetch_signs_in_bbox(self, bbox, sign_filter=None, callback=None):
        return self.fetch_features_in_bbox(
            bbox,
            tile_layer='mly_map_feature_traffic_sign',
            mvt_layer_name='traffic_sign',
            value_filter=sign_filter,
            callback=callback,
        )

    def fetch_points_in_bbox(self, bbox, point_filter=None, callback=None):
        return self.fetch_features_in_bbox(
            bbox,
            tile_layer='mly_map_feature_point',
            mvt_layer_name='point',
            value_filter=point_filter,
            callback=callback,
        )

    # ---- Entity enrichment -------------------------------------------

    def enrich_features(self, features, callback=None):
        """Enrich features with precise geometry and image references."""
        total = len(features)
        self.log("Enriching {} features with entity metadata".format(total))

        fields = "geometry,object_value,first_seen_at,last_seen_at,images"

        for i, feat in enumerate(features):
            url = self._build_entity_url(feat['id'], fields)

            status, content = self._http_get(url)
            if status == 429:
                time.sleep(2)
                status, content = self._http_get(url)

            if status == 200 and content:
                try:
                    data = json.loads(content.decode('utf-8', errors='replace'))
                except ValueError:
                    data = {}

                geom = data.get('geometry') or {}
                coords = geom.get('coordinates') if isinstance(geom, dict) else None
                if coords and len(coords) >= 2:
                    feat['lng'] = coords[0]
                    feat['lat'] = coords[1]

                if data.get('first_seen_at'):
                    feat['first_seen_at'] = data['first_seen_at']
                if data.get('last_seen_at'):
                    feat['last_seen_at'] = data['last_seen_at']

                images = data.get('images', [])
                if isinstance(images, list):
                    feat['image_ids'] = [
                        img.get('id') for img in images
                        if isinstance(img, dict) and img.get('id')
                    ]
                    feat['num_observations'] = len(images)
                else:
                    feat['num_observations'] = 0

                feat['mapillary_link'] = (
                    "https://www.mapillary.com/app/"
                    "?focus=map_feature&pKey={}".format(feat['id'])
                )
            else:
                self.log(
                    "Enrichment failed for {} (status={})".format(
                        feat.get('id'), status
                    ),
                    Qgis.Warning,
                )

            if (i + 1) % 50 == 0:
                time.sleep(0.5)

            if callback:
                pct = int((i + 1) / total * 100)
                keep_going = callback(
                    pct, "Enriched {}/{} features".format(i + 1, total)
                )
                if keep_going is False:
                    break

        return features

    def get_image_thumbnail(self, image_id, size=1024):
        """Get thumbnail URL + metadata for an image."""
        fields = "thumb_{}_url,captured_at,computed_geometry,compass_angle".format(size)
        url = self._build_entity_url(image_id, fields)
        status, content = self._http_get(url)
        if status == 200 and content:
            try:
                return json.loads(content.decode('utf-8', errors='replace'))
            except ValueError:
                return None
        return None

    # ---- Coordinate conversion ---------------------------------------

    def _mvt_to_lnglat(self, coords, tile_x, tile_y, zoom, extent=4096):
        """Convert MVT tile-relative coordinates to longitude/latitude.

        mvt_decoder flips y to match GeoJSON convention (y=0 south,
        y=extent north), so this is a straight linear map inside the
        tile's geographic bounds.
        """
        b = tile_math.bounds(tile_x, tile_y, zoom)
        x_ratio = coords[0] / extent
        y_ratio = coords[1] / extent
        lng = b.west + (b.east - b.west) * x_ratio
        lat = b.south + (b.north - b.south) * y_ratio
        return lng, lat

    def _point_in_bbox(self, lng, lat, bbox):
        west, south, east, north = bbox
        return west <= lng <= east and south <= lat <= north

    # ---- Connectivity / token check ----------------------------------

    def test_connection(self, timeout_ms=MAPILLARY_TEST_TIMEOUT_MS,
                        progress_callback=None):
        """Verify both Graph API and vector-tile access for the token."""
        url = QUrl(self.TEST_URL)
        q = QUrlQuery()
        q.addQueryItem("fields", "id")
        q.addQueryItem("bbox", "-111.93,33.42,-111.92,33.43")
        q.addQueryItem("limit", "1")
        url.setQuery(q)
        if progress_callback:
            progress_callback("Checking Mapillary Graph API...")
        status, _ = self._http_get(url, timeout_ms=timeout_ms)
        if status != 200:
            return False

        tile = next(
            tile_math.tiles(-111.93, 33.42, -111.92, 33.43, zooms=14),
            None,
        )
        if tile is None:
            return False

        if progress_callback:
            progress_callback("Checking Mapillary vector tiles...")
        tile_url = self._build_tile_url(
            "mly_map_feature_traffic_sign", 14, tile.x, tile.y
        )
        tile_status, _ = self._http_get(
            tile_url,
            include_auth_header=False,
            timeout_ms=timeout_ms,
        )
        return tile_status not in (None, 401, 403)
