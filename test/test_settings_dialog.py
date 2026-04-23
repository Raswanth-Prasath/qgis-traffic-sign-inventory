# coding=utf-8
"""Unit tests for the Mapillary settings dialog."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.getcwd()))

from qgis.PyQt.QtCore import QObject, pyqtSignal

from traffic_sign_inventory import settings_dialog as settings_dialog_module
from traffic_sign_inventory.settings_dialog import SettingsDialog

from test.utilities import get_qgis_app

QGIS_APP = get_qgis_app()


class FakeTokenTestWorker(QObject):
    """Signal-compatible test double for TokenTestWorker."""

    progress = pyqtSignal(str)
    result = pyqtSignal(bool)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    instances = []

    def __init__(self, token, parent=None):
        super().__init__(parent)
        self.token = token
        self.started = False
        self.instances.append(self)

    def start(self):
        self.started = True


class SettingsDialogTest(unittest.TestCase):
    """Test Mapillary token connection checks."""

    def setUp(self):
        self.qgis_app, self.canvas, self.iface, self.parent = get_qgis_app()
        self.original_worker = settings_dialog_module.TokenTestWorker
        FakeTokenTestWorker.instances = []
        settings_dialog_module.TokenTestWorker = FakeTokenTestWorker
        self.dialog = SettingsDialog(self.parent)

    def tearDown(self):
        settings_dialog_module.TokenTestWorker = self.original_worker
        self.dialog.close()
        self.dialog = None

    def test_connection_check_runs_in_worker(self):
        self.dialog.token_input.setText("MLY|test|token")

        self.dialog._test_connection()

        self.assertEqual(len(FakeTokenTestWorker.instances), 1)
        worker = FakeTokenTestWorker.instances[0]
        self.assertTrue(worker.started)
        self.assertEqual(worker.token, "MLY|test|token")
        self.assertFalse(self.dialog.test_btn.isEnabled())
        self.assertFalse(self.dialog.button_box.isEnabled())
        self.assertEqual(
            self.dialog.status_label.text(),
            "Checking Mapillary Graph API...",
        )
        worker.finished.emit()

    def test_connection_check_reports_worker_result(self):
        self.dialog.token_input.setText("MLY|test|token")
        self.dialog._test_connection()
        worker = FakeTokenTestWorker.instances[0]

        worker.progress.emit("Checking Mapillary vector tiles...")
        self.assertEqual(
            self.dialog.status_label.text(),
            "Checking Mapillary vector tiles...",
        )

        worker.result.emit(True)
        self.assertIn("Connection OK", self.dialog.status_label.text())

        worker.finished.emit()
        self.assertTrue(self.dialog.test_btn.isEnabled())
        self.assertTrue(self.dialog.button_box.isEnabled())
        self.assertIsNone(self.dialog._test_worker)

    def test_invalid_token_does_not_start_worker(self):
        self.dialog.token_input.setText("not-a-mapillary-token")

        self.dialog._test_connection()

        self.assertEqual(FakeTokenTestWorker.instances, [])
        self.assertTrue(self.dialog.test_btn.isEnabled())


if __name__ == "__main__":
    unittest.main()
