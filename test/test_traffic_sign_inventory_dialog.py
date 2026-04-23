# coding=utf-8
"""Dialog test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = 'raswanth@asu.edu'
__date__ = '2026-02-13'
__copyright__ = 'Copyright 2026, Raswanth'

import unittest

from qgis.PyQt.QtGui import QDialogButtonBox, QDialog

from traffic_sign_inventory_dialog import TrafficSignInventoryDialog

from utilities import get_qgis_app
QGIS_APP = get_qgis_app()


class TrafficSignInventoryDialogTest(unittest.TestCase):
    """Test dialog works."""

    def setUp(self):
        """Runs before each test."""
        self.dialog = TrafficSignInventoryDialog(None)

    def tearDown(self):
        """Runs after each test."""
        self.dialog = None

    def test_dialog_ok(self):
        """Test we can click OK."""

        button = self.dialog.button_box.button(QDialogButtonBox.Ok)
        button.click()
        result = self.dialog.result()
        self.assertEqual(result, QDialog.Accepted)

    def test_dialog_cancel(self):
        """Test we can click cancel."""
        button = self.dialog.button_box.button(QDialogButtonBox.Cancel)
        button.click()
        result = self.dialog.result()
        self.assertEqual(result, QDialog.Rejected)

from qgis.core import QgsRectangle


class DrawOnMapIntegrationTest(unittest.TestCase):

    def setUp(self):
        self.qgis_app, self.canvas, self.iface, self.parent = get_qgis_app()
        self.dialog = TrafficSignInventoryDialog(self.iface)

    def tearDown(self):
        try:
            self.dialog.close()
        except Exception:
            pass
        self.dialog = None

    def test_selecting_draw_on_map_hides_dialog(self):
        self.dialog.show()
        self.dialog.bbox_method.setCurrentIndex(2)
        self.assertFalse(self.dialog.isVisible())

    def test_redraw_button_hidden_by_default(self):
        self.assertFalse(self.dialog.redraw_btn.isVisible())

    def test_extent_picked_populates_inputs(self):
        rect = QgsRectangle(-111.93, 33.40, -111.92, 33.41)
        self.dialog._on_extent_picked(rect)
        self.assertAlmostEqual(self.dialog.west_input.value(), -111.93, places=4)
        self.assertAlmostEqual(self.dialog.south_input.value(), 33.40, places=4)
        self.assertAlmostEqual(self.dialog.east_input.value(), -111.92, places=4)
        self.assertAlmostEqual(self.dialog.north_input.value(), 33.41, places=4)

    def test_extent_picked_restores_dialog(self):
        self.dialog.hide()
        rect = QgsRectangle(-111.93, 33.40, -111.92, 33.41)
        self.dialog._on_extent_picked(rect)
        self.assertTrue(self.dialog.isVisible())

    def test_redraw_button_visible_after_first_draw(self):
        rect = QgsRectangle(-111.93, 33.40, -111.92, 33.41)
        self.dialog.show()
        self.dialog._on_extent_picked(rect)
        self.assertTrue(self.dialog.redraw_btn.isVisible())


if __name__ == "__main__":
    suite = unittest.makeSuite(TrafficSignInventoryDialogTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

