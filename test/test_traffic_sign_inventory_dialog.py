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

    def test_redraw_clears_previous_rubber_band(self):
        # First draw sets up the picker + rubber band
        rect1 = QgsRectangle(-111.93, 33.40, -111.92, 33.41)
        self.dialog._start_draw()  # lazy-init the picker
        self.dialog.extent_picker._on_extent_changed(rect1)  # completes a draw, sets rubber band
        self.assertIsNotNone(self.dialog.extent_picker._persistent_band)

        # Re-draw should clear the band before re-activating
        self.dialog._on_redraw_clicked()
        self.assertIsNone(self.dialog.extent_picker._persistent_band)

    def test_switching_bbox_method_clears_rubber_band(self):
        rect = QgsRectangle(-111.93, 33.40, -111.92, 33.41)
        self.dialog._start_draw()
        self.dialog.extent_picker._on_extent_changed(rect)
        self.assertIsNotNone(self.dialog.extent_picker._persistent_band)

        self.dialog.bbox_method.setCurrentIndex(0)  # Use current map extent
        self.assertIsNone(self.dialog.extent_picker._persistent_band)

    def test_close_event_cancels_picker_and_clears_band(self):
        rect = QgsRectangle(-111.93, 33.40, -111.92, 33.41)
        self.dialog._start_draw()
        self.dialog.extent_picker._on_extent_changed(rect)
        self.assertIsNotNone(self.dialog.extent_picker._persistent_band)

        self.dialog.close()
        self.assertIsNone(self.dialog.extent_picker._persistent_band)

    def test_close_event_does_not_reshow_dialog(self):
        # closeEvent must NOT re-show the dialog via the draw_cancelled path.
        rect = QgsRectangle(-111.93, 33.40, -111.92, 33.41)
        self.dialog._start_draw()
        self.dialog.extent_picker._on_extent_changed(rect)
        self.dialog.close()
        self.assertFalse(self.dialog.isVisible())

    def test_draw_cancelled_resets_combo_to_manual(self):
        # ESC / draw_cancelled should leave the combo on index 1 (Manual),
        # not stuck on index 2 (Draw on map).
        self.dialog.bbox_method.setCurrentIndex(2)  # starts a draw (dialog hides)
        self.dialog._on_draw_cancelled()
        self.assertEqual(self.dialog.bbox_method.currentIndex(), 1)
        self.assertTrue(self.dialog.isVisible())


if __name__ == "__main__":
    suite = unittest.makeSuite(TrafficSignInventoryDialogTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

