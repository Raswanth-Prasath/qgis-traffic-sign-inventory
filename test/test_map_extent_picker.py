# coding=utf-8
"""Unit tests for MapExtentPicker."""

import unittest

from qgis.core import QgsRectangle, QgsCoordinateReferenceSystem

from utilities import get_qgis_app
from traffic_sign_inventory_dialog import MapExtentPicker

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class CrsTransformTest(unittest.TestCase):

    def setUp(self):
        self.picker = MapExtentPicker(IFACE)

    def test_crs_transform_wgs84_passthrough(self):
        CANVAS.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        rect = QgsRectangle(-111.93, 33.40, -111.92, 33.41)
        out = self.picker._transform_to_wgs84(rect)
        self.assertAlmostEqual(out.xMinimum(), rect.xMinimum(), places=9)
        self.assertAlmostEqual(out.yMinimum(), rect.yMinimum(), places=9)
        self.assertAlmostEqual(out.xMaximum(), rect.xMaximum(), places=9)
        self.assertAlmostEqual(out.yMaximum(), rect.yMaximum(), places=9)

    def test_crs_transform_web_mercator_to_wgs84(self):
        CANVAS.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        # A rectangle in Web Mercator meters around Tempe, AZ:
        rect_m = QgsRectangle(-12460000.0, 3951000.0, -12459000.0, 3952000.0)
        out = self.picker._transform_to_wgs84(rect_m)
        # y=3951000 m Web Mercator ≈ 33.4186° lat; x=-12460000 m ≈ -111.9301° lon
        self.assertAlmostEqual(out.xMinimum(), -111.9301, places=3)
        self.assertAlmostEqual(out.yMinimum(), 33.4186, places=3)
        self.assertTrue(out.xMaximum() > out.xMinimum())
        self.assertTrue(out.yMaximum() > out.yMinimum())


if __name__ == "__main__":
    unittest.main()
