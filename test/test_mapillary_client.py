# coding=utf-8
"""Unit tests for MapillaryClient auth behavior."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.getcwd()))

from traffic_sign_inventory import mapillary_client as mapillary_client_module
from traffic_sign_inventory import tile_math
from traffic_sign_inventory.mapillary_client import MapillaryClient


class MapillaryClientAuthTest(unittest.TestCase):

    def setUp(self):
        self.client = MapillaryClient("MLY|test|token")

    def test_build_tile_url_puts_token_in_query_string(self):
        url = self.client._build_tile_url(
            "mly_map_feature_traffic_sign", 14, 3098, 6574
        )
        url_text = url.toString()
        self.assertIn("tiles.mapillary.com/maps/vtp/", url_text)
        self.assertIn("mly_map_feature_traffic_sign/2/14/3098/6574", url_text)
        self.assertIn("access_token=MLY%7Ctest%7Ctoken", url_text)

    def test_fetch_features_raises_on_tile_auth_failure(self):
        calls = []

        def fake_http_get(url, include_auth_header=True, timeout_ms=None):
            calls.append((url.toString(), include_auth_header))
            return 403, b""

        self.client._http_get = fake_http_get

        with self.assertRaises(RuntimeError):
            self.client.fetch_signs_in_bbox((-111.93, 33.42, -111.92, 33.43))

        self.assertEqual(len(calls), 1)
        self.assertFalse(calls[0][1])
        self.assertIn("access_token=", calls[0][0])

    def test_test_connection_checks_tile_access(self):
        calls = []
        responses = [
            (200, b'{"data": [{"id": "1"}]}'),
            (403, b""),
        ]

        def fake_http_get(url, include_auth_header=True, timeout_ms=None):
            calls.append((url.toString(), include_auth_header, timeout_ms))
            return responses.pop(0)

        self.client._http_get = fake_http_get

        progress = []
        self.assertFalse(
            self.client.test_connection(
                timeout_ms=1234,
                progress_callback=progress.append,
            )
        )
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[0][1])
        self.assertIn("graph.mapillary.com/images", calls[0][0])
        self.assertEqual(calls[0][2], 1234)
        self.assertFalse(calls[1][1])
        self.assertIn("tiles.mapillary.com/maps/vtp/", calls[1][0])
        self.assertIn("access_token=", calls[1][0])
        self.assertEqual(calls[1][2], 1234)
        self.assertEqual(
            progress,
            [
                "Checking Mapillary Graph API...",
                "Checking Mapillary vector tiles...",
            ],
        )

    def test_fetch_features_clips_results_to_bbox(self):
        bbox = (-111.93, 33.42, -111.92, 33.43)
        tile = next(tile_math.tiles(*bbox, zooms=14))
        bounds = tile_math.bounds(tile.x, tile.y, tile.z)

        def raw_point(lng, lat, extent=4096):
            x = int((lng - bounds.west) / (bounds.east - bounds.west) * extent)
            y = int((lat - bounds.south) / (bounds.north - bounds.south) * extent)
            return [x, y]

        inside = raw_point((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
        outside = raw_point(bounds.west + 0.0005, bounds.south + 0.0005)
        original_decode = mapillary_client_module.mvt_decoder.decode

        def fake_http_get(url, include_auth_header=True, timeout_ms=None):
            return 200, b"fake"

        def fake_decode(content):
            return {
                'traffic_sign': {
                    'extent': 4096,
                    'features': [
                        {
                            'id': 1,
                            'properties': {'id': 1, 'value': 'regulatory--stop--g1'},
                            'geometry': {'type': 'Point', 'coordinates': inside},
                        },
                        {
                            'id': 2,
                            'properties': {'id': 2, 'value': 'regulatory--yield--g1'},
                            'geometry': {'type': 'Point', 'coordinates': outside},
                        },
                    ],
                }
            }

        self.client._http_get = fake_http_get
        mapillary_client_module.mvt_decoder.decode = fake_decode
        try:
            features = self.client.fetch_signs_in_bbox(bbox)
        finally:
            mapillary_client_module.mvt_decoder.decode = original_decode

        self.assertEqual(len(features), 1)
        self.assertEqual(features[0]['id'], 1)


if __name__ == "__main__":
    unittest.main()
