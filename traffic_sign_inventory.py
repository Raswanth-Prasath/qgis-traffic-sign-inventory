"""
Traffic Sign Inventory — QGIS Plugin
Fetches traffic signs and point features from Mapillary with MUTCD mapping.
"""

import os

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

# Initialize Qt resources from file resources.py
from .resources import *


class TrafficSignInventory:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dialog = None
        self.actions = []
        self.menu = self.tr(u'&Traffic Sign Inventory')

        # Locale / translation support
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir, 'i18n',
            'TrafficSignInventory_{}.qm'.format(locale)
        )
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

    def tr(self, message):
        return QCoreApplication.translate('TrafficSignInventory', message)

    def initGui(self):
        """Create menu entry and toolbar icon."""
        icon_path = ':/plugins/traffic_sign_inventory/icon.png'
        icon = QIcon(icon_path)

        self.action = QAction(
            icon,
            self.tr(u'Traffic Sign Inventory'),
            self.iface.mainWindow(),
        )
        self.action.setStatusTip(
            "Fetch traffic signs and point features from Mapillary"
        )
        self.action.triggered.connect(self.run)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.menu, self.action)
        self.actions.append(self.action)

        self.settings_action = QAction(
            self.tr(u'Settings…'),
            self.iface.mainWindow(),
        )
        self.settings_action.setStatusTip(
            "Configure Mapillary access token"
        )
        self.settings_action.triggered.connect(self.open_settings)
        self.iface.addPluginToMenu(self.menu, self.settings_action)
        self.actions.append(self.settings_action)

    def unload(self):
        """Remove plugin menu item and icon."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)

    def open_settings(self):
        """Open the settings dialog from the plugin menu."""
        from .settings_dialog import SettingsDialog

        dlg = SettingsDialog(self.iface.mainWindow())
        dlg.exec_()

    def run(self):
        """Open the dialog (non-modal, reused across invocations)."""
        from .traffic_sign_inventory_dialog import TrafficSignInventoryDialog

        if self.dialog is None:
            self.dialog = TrafficSignInventoryDialog(
                self.iface, self.iface.mainWindow()
            )

        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
