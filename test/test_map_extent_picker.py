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


from qgis.gui import QgsMapToolPan


class MapToolLifecycleTest(unittest.TestCase):

    def setUp(self):
        self.picker = MapExtentPicker(IFACE)
        self.pan_tool = QgsMapToolPan(CANVAS)
        CANVAS.setMapTool(self.pan_tool)

    def tearDown(self):
        try:
            self.picker.deactivate()
        except Exception:
            pass
        self.picker = None
        self.pan_tool = None

    def test_activate_saves_previous_map_tool(self):
        self.picker.activate()
        self.assertIs(self.picker._previous_tool, self.pan_tool)

    def test_deactivate_restores_previous_map_tool(self):
        self.picker.activate()
        self.picker.deactivate()
        self.assertIs(CANVAS.mapTool(), self.pan_tool)

    def test_activate_twice_preserves_original_previous_tool(self):
        self.picker.activate()
        first_extent_tool = self.picker._map_tool
        self.picker.activate()
        # _previous_tool should still point at the pre-picker pan tool,
        # not the first QgsMapToolExtent that activate() created.
        self.assertIs(self.picker._previous_tool, self.pan_tool)
        # And the first extent tool must be disposed (not the current _map_tool).
        self.assertIsNot(self.picker._map_tool, first_extent_tool)


class ExtentPickedSignalTest(unittest.TestCase):

    def setUp(self):
        CANVAS.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        self.picker = MapExtentPicker(IFACE)
        self.received = []
        self.picker.extent_picked.connect(lambda r: self.received.append(r))

    def tearDown(self):
        try:
            self.picker.deactivate()
        except Exception:
            pass
        self.picker = None

    def test_extent_picked_signal_emitted_on_draw_complete(self):
        rect = QgsRectangle(-111.93, 33.40, -111.92, 33.41)
        self.picker._on_extent_changed(rect)
        self.assertEqual(len(self.received), 1)
        out = self.received[0]
        self.assertAlmostEqual(out.xMinimum(), -111.93, places=6)

    def test_zero_size_rect_is_ignored(self):
        rect = QgsRectangle(-111.93, 33.40, -111.93, 33.40)
        self.picker._on_extent_changed(rect)
        self.assertEqual(len(self.received), 0)


if __name__ == "__main__":
    unittest.main()
