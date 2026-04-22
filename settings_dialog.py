"""
Settings dialog for Traffic Sign Inventory.

Stores the Mapillary access token in QSettings under the
"TrafficSignInventory" namespace — never in a file on disk inside
the plugin directory.
"""

from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QDialogButtonBox, QFrame
)

SETTINGS_ORG = "TrafficSignInventory"
SETTINGS_KEY_TOKEN = "mapillary/access_token"
MAPILLARY_DEVELOPER_URL = "https://www.mapillary.com/dashboard/developers"


def get_mapillary_token():
    """Read the stored Mapillary token. Returns empty string if unset."""
    settings = QSettings(SETTINGS_ORG, SETTINGS_ORG)
    return settings.value(SETTINGS_KEY_TOKEN, "", type=str)


def set_mapillary_token(token):
    """Persist the Mapillary token."""
    settings = QSettings(SETTINGS_ORG, SETTINGS_ORG)
    settings.setValue(SETTINGS_KEY_TOKEN, token)


class SettingsDialog(QDialog):
    """Simple settings dialog for the Mapillary access token."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Traffic Sign Inventory — Settings")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        intro = QLabel(
            "<b>Mapillary Access Token</b><br>"
            "This plugin needs a free Mapillary API token to fetch traffic "
            "signs and point features. Your token is stored in your QGIS "
            "user profile and is never shared."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        how_to = QLabel(
            "<b>How to get a token:</b><br>"
            "1. Sign in at "
            f"<a href='{MAPILLARY_DEVELOPER_URL}'>"
            "mapillary.com/dashboard/developers</a><br>"
            "2. Click <i>Register Application</i> (any name works).<br>"
            "3. Under the new app, click <i>Create a token</i> with the "
            "<i>read</i> scope.<br>"
            "4. Copy the token (starts with <code>MLY|</code>) and paste it "
            "below."
        )
        how_to.setWordWrap(True)
        how_to.setOpenExternalLinks(True)
        how_to.setTextInteractionFlags(Qt.TextBrowserInteraction)
        layout.addWidget(how_to)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        layout.addWidget(divider)

        token_row = QHBoxLayout()
        token_row.addWidget(QLabel("Token:"))
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setPlaceholderText("MLY|...")
        self.token_input.setText(get_mapillary_token())
        token_row.addWidget(self.token_input, stretch=1)

        self.show_btn = QPushButton("Show")
        self.show_btn.setCheckable(True)
        self.show_btn.toggled.connect(self._toggle_visibility)
        self.show_btn.setMaximumWidth(70)
        token_row.addWidget(self.show_btn)

        layout.addLayout(token_row)

        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self._test_connection)
        layout.addWidget(self.test_btn)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _toggle_visibility(self, on):
        self.token_input.setEchoMode(
            QLineEdit.Normal if on else QLineEdit.Password
        )
        self.show_btn.setText("Hide" if on else "Show")

    def _current_token(self):
        return self.token_input.text().strip()

    def _is_plausible_token(self, token):
        return bool(token) and token.startswith("MLY|") and token.count("|") >= 2

    def _test_connection(self):
        token = self._current_token()
        if not self._is_plausible_token(token):
            self.status_label.setText(
                "<span style='color:#c0392b'>Token format looks wrong — "
                "expected <code>MLY|...|...</code></span>"
            )
            return

        self.status_label.setText("Testing…")
        self.test_btn.setEnabled(False)
        try:
            from .mapillary_client import MapillaryClient
            client = MapillaryClient(token)
            ok = client.test_connection()
            if ok:
                self.status_label.setText(
                    "<span style='color:#27ae60'>✓ Connection OK — token "
                    "is valid.</span>"
                )
            else:
                self.status_label.setText(
                    "<span style='color:#c0392b'>✗ Mapillary rejected the "
                    "token. Check it's correct and has <i>read</i> scope."
                    "</span>"
                )
        except Exception as e:
            self.status_label.setText(
                f"<span style='color:#c0392b'>✗ Network error: {e}</span>"
            )
        finally:
            self.test_btn.setEnabled(True)

    def _save(self):
        token = self._current_token()
        if not token:
            reply = QMessageBox.question(
                self, "Clear token?",
                "The token field is empty. Save anyway (clears the stored "
                "token)?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        elif not self._is_plausible_token(token):
            reply = QMessageBox.question(
                self, "Unusual token format",
                "This doesn't look like a Mapillary token "
                "(expected <code>MLY|…|…</code>). Save anyway?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        set_mapillary_token(token)
        self.accept()
