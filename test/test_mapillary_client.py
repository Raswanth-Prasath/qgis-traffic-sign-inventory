# coding=utf-8
"""Unit tests for MapillaryClient auth behavior."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.getcwd()))

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

        def fake_http_get(url, include_auth_header=True):
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

        def fake_http_get(url, include_auth_header=True):
            calls.append((url.toString(), include_auth_header))
            return responses.pop(0)

        self.client._http_get = fake_http_get

        self.assertFalse(self.client.test_connection())
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[0][1])
        self.assertIn("graph.mapillary.com/images", calls[0][0])
        self.assertFalse(calls[1][1])
        self.assertIn("tiles.mapillary.com/maps/vtp/", calls[1][0])
        self.assertIn("access_token=", calls[1][0])


if __name__ == "__main__":
    unittest.main()
