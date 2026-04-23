"""
Traffic Sign Inventory Dialog
Main UI for configuring and running traffic sign + point feature queries.
UI layout loaded from .ui file; this module handles logic and signals only.
"""

import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QPushButton
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal, QObject

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'traffic_sign_inventory_dialog_base.ui'))


class FetchWorker(QThread):
    """Background worker for API calls so UI doesn't freeze."""

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, client, bbox, sign_filter, point_filter,
                 enrich, fetch_signs, fetch_points):
        super().__init__()
        self.client = client
        self.bbox = bbox
        self.sign_filter = sign_filter
        self.point_filter = point_filter
        self.enrich = enrich
        self.fetch_signs = fetch_signs
        self.fetch_points = fetch_points
        self._cancelled = False

    def cancel(self):
        """Request cancellation — checked between API calls."""
        self._cancelled = True

    def run(self):
        try:
            all_features = []

            phases = []
            if self.fetch_signs:
                phases.append('signs')
            if self.fetch_points:
                phases.append('points')
            if self.enrich:
                phases.append('enrich')

            total_phases = len(phases)
            if total_phases == 0:
                self.finished.emit([])
                return

            phase_idx = 0

            if self.fetch_signs and not self._cancelled:
                phase_start = int(phase_idx / total_phases * 100)
                phase_end = int((phase_idx + 1) / total_phases * 100)

                def sign_cb(pct, msg):
                    scaled = phase_start + int(pct * (phase_end - phase_start) / 100)
                    self.progress.emit(scaled, msg)
                    return not self._cancelled

                signs = self.client.fetch_signs_in_bbox(
                    self.bbox,
                    sign_filter=self.sign_filter or None,
                    callback=sign_cb,
                )
                all_features.extend(signs)
                phase_idx += 1

            if self.fetch_points and not self._cancelled:
                phase_start = int(phase_idx / total_phases * 100)
                phase_end = int((phase_idx + 1) / total_phases * 100)

                def point_cb(pct, msg):
                    scaled = phase_start + int(pct * (phase_end - phase_start) / 100)
                    self.progress.emit(scaled, msg)
                    return not self._cancelled

                points = self.client.fetch_points_in_bbox(
                    self.bbox,
                    point_filter=self.point_filter or None,
                    callback=point_cb,
                )
                all_features.extend(points)
                phase_idx += 1

            if self.enrich and all_features and not self._cancelled:
                phase_start = int(phase_idx / total_phases * 100)
                phase_end = int((phase_idx + 1) / total_phases * 100)

                def enrich_cb(pct, msg):
                    scaled = phase_start + int(pct * (phase_end - phase_start) / 100)
                    self.progress.emit(scaled, msg)
                    return not self._cancelled

                all_features = self.client.enrich_features(
                    all_features, callback=enrich_cb
                )

            self.finished.emit(all_features)

        except Exception as e:
            if not self._cancelled:
                msg = str(e)
                if self.client and getattr(self.client, 'token', None):
                    msg = msg.replace(self.client.token, "<redacted>")
                self.error.emit(msg)


class MapExtentPicker(QObject):
    """Wraps QgsMapToolExtent with a persistent rubber band and CRS transform.

    Emits extent_picked(QgsRectangle) in EPSG:4326 when the user completes a
    draw, or draw_cancelled() when the user presses ESC.
    """

    extent_picked = pyqtSignal(object)
    draw_cancelled = pyqtSignal()

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self._canvas = iface.mapCanvas()
        self._previous_tool = None
        self._map_tool = None
        self._persistent_band = None

    def activate(self):
        from qgis.gui import QgsMapToolExtent
        if self._map_tool is not None:
            # Already active — tear down the old tool, but DO NOT overwrite
            # _previous_tool, since that's the true pre-activation tool.
            try:
                self._map_tool.extentChanged.disconnect(self._on_extent_changed)
            except TypeError:
                pass
            self._map_tool = None
        else:
            # First activation: save the pre-picker tool for restoration.
            self._previous_tool = self._canvas.mapTool()
        self._map_tool = QgsMapToolExtent(self._canvas)
        self._map_tool.extentChanged.connect(self._on_extent_changed)
        self._canvas.setMapTool(self._map_tool)
        try:
            self.iface.messageBar().pushMessage(
                "Draw on map",
                "Drag a rectangle to define the area. Press ESC to cancel.",
                level=0,
                duration=0,
            )
        except Exception:
            # messageBar may not be available in the test harness; non-fatal.
            pass

    def cancel(self):
        raise NotImplementedError

    def deactivate(self):
        if self._map_tool is not None:
            try:
                self._map_tool.extentChanged.disconnect(self._on_extent_changed)
            except TypeError:
                pass
            if self._previous_tool is not None:
                self._canvas.setMapTool(self._previous_tool)
                self._previous_tool = None
            self._map_tool = None
        try:
            self.iface.messageBar().clearWidgets()
        except Exception:
            pass

    def clear_rubber_band(self):
        if self._persistent_band is not None:
            self._canvas.scene().removeItem(self._persistent_band)
            self._persistent_band = None

    def _on_extent_changed(self, rect):
        if rect.width() == 0 or rect.height() == 0:
            return
        try:
            rect_wgs84 = self._transform_to_wgs84(rect)
            self._draw_persistent_band(rect)
            self.extent_picked.emit(rect_wgs84)
        finally:
            self.deactivate()

    def _draw_persistent_band(self, rect):
        from qgis.gui import QgsRubberBand
        from qgis.core import QgsWkbTypes
        from qgis.PyQt.QtGui import QColor
        if self._persistent_band is not None:
            self._canvas.scene().removeItem(self._persistent_band)
            self._persistent_band = None
        band = QgsRubberBand(self._canvas, QgsWkbTypes.PolygonGeometry)
        band.setToGeometry(self._rect_to_polygon_geom(rect), None)
        band.setColor(QColor(255, 0, 0, 80))
        band.setStrokeColor(QColor(200, 0, 0, 200))
        band.setWidth(2)
        self._persistent_band = band

    def _rect_to_polygon_geom(self, rect):
        from qgis.core import QgsGeometry, QgsPointXY
        pts = [
            QgsPointXY(rect.xMinimum(), rect.yMinimum()),
            QgsPointXY(rect.xMaximum(), rect.yMinimum()),
            QgsPointXY(rect.xMaximum(), rect.yMaximum()),
            QgsPointXY(rect.xMinimum(), rect.yMaximum()),
        ]
        return QgsGeometry.fromPolygonXY([pts])

    def _transform_to_wgs84(self, rect):
        from qgis.core import (
            QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject,
        )
        canvas_crs = self._canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        if not canvas_crs.isValid() or canvas_crs == wgs84:
            return rect
        xform = QgsCoordinateTransform(canvas_crs, wgs84, QgsProject.instance())
        return xform.transformBoundingBox(rect)


class TrafficSignInventoryDialog(QDialog, FORM_CLASS):
    """Main plugin dialog. Widgets are defined in the .ui file."""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.iface = iface
        self.worker = None
        self._last_features = []
        self._temp_geojson_path = None

        # Inline "Settings…" button above the Fetch button so users can
        # configure the Mapillary token without leaving the dialog.
        self.settings_btn = QPushButton("Mapillary Token / Settings…")
        main_layout = self.layout()
        run_btn_index = main_layout.indexOf(self.run_btn)
        main_layout.insertWidget(run_btn_index, self.settings_btn)
        self.settings_btn.clicked.connect(self._open_settings)

        self._connect_signals()
        # Grab extent on startup if method is "Use current map extent"
        if self.bbox_method.currentIndex() == 0:
            self._grab_map_extent()

    def showEvent(self, event):
        """Refresh map extent each time the dialog is shown."""
        super().showEvent(event)
        if self.bbox_method.currentIndex() == 0:
            self._grab_map_extent()

    def closeEvent(self, event):
        """Cancel any running worker when the dialog is closed."""
        self._cancel_worker()
        self._cleanup_temp_geojson()
        super().closeEvent(event)

    def _cleanup_temp_geojson(self):
        """Remove the temp GeoJSON file backing the in-memory layer, if any."""
        path = self._temp_geojson_path
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        self._temp_geojson_path = None

    def _open_settings(self):
        from .settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        dlg.exec_()

    def _cancel_worker(self):
        """Stop the background thread if it's running."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(5000)  # wait up to 5s for it to finish
            self.worker = None
            self.run_btn.setEnabled(True)
            self.run_btn.setText("Fetch Features")
            self.progress_bar.setVisible(False)
            self.status_label.setText("Cancelled")

    def _connect_signals(self):
        """Wire up all button/checkbox signals to slots."""
        self.grab_extent_btn.clicked.connect(self._grab_map_extent)
        self.bbox_method.currentIndexChanged.connect(self._on_bbox_method_changed)
        self.fetch_signs_check.stateChanged.connect(self._on_layer_toggle)
        self.fetch_points_check.stateChanged.connect(self._on_layer_toggle)
        self.run_btn.clicked.connect(self._run_query)
        self.export_geojson_btn.clicked.connect(lambda: self._export("geojson"))
        self.export_shp_btn.clicked.connect(lambda: self._export("shp"))
        self.export_csv_btn.clicked.connect(lambda: self._export("csv"))

    # ---- UI callbacks ----

    def _on_layer_toggle(self):
        signs_on = self.fetch_signs_check.isChecked()
        self.sign_filter_label.setVisible(signs_on)
        self.filter_category.setVisible(signs_on)

        points_on = self.fetch_points_check.isChecked()
        self.point_filter_label.setVisible(points_on)
        self.point_filter_category.setVisible(points_on)

    def _on_bbox_method_changed(self, idx):
        if idx == 0:
            self._grab_map_extent()

    def _grab_map_extent(self):
        from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject

        canvas = self.iface.mapCanvas()
        extent = canvas.extent()

        # Transform to WGS84 (EPSG:4326) if the canvas uses a different CRS
        canvas_crs = canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        if canvas_crs != wgs84:
            xform = QgsCoordinateTransform(canvas_crs, wgs84, QgsProject.instance())
            extent = xform.transformBoundingBox(extent)

        self.west_input.setValue(extent.xMinimum())
        self.south_input.setValue(extent.yMinimum())
        self.east_input.setValue(extent.xMaximum())
        self.north_input.setValue(extent.yMaximum())

    def _get_sign_filter(self):
        from .mutcd_mapping import get_category_values, get_all_sign_values

        idx = self.filter_category.currentIndex()
        if idx == 0:
            return None
        elif idx == 1:
            return get_category_values('regulatory')
        elif idx == 2:
            return get_category_values('warning')
        elif idx == 3:
            return get_category_values('information')
        elif idx == 4:
            return [
                'regulatory--stop--g1',
                'regulatory--yield--g1',
                'regulatory--all-way--g1',
            ]
        elif idx == 5:
            return [v for v in get_all_sign_values() if 'speed-limit' in v]
        return None

    def _get_point_filter(self):
        from .mutcd_mapping import get_point_category_values

        idx = self.point_filter_category.currentIndex()
        if idx == 0:
            return None
        category_map = {
            1: 'signal',
            2: 'marking',
            3: 'infrastructure',
            4: 'furniture',
            5: 'traffic_control',
        }
        category = category_map.get(idx)
        if category:
            return get_point_category_values(category)
        return None

    # ---- Query execution ----

    def _run_query(self):
        from .mapillary_client import MapillaryClient
        from .settings_dialog import get_mapillary_token, SettingsDialog

        token = get_mapillary_token()
        if not token:
            reply = QMessageBox.question(
                self, "Mapillary token required",
                "No Mapillary access token is configured.\n\n"
                "Open Settings now to add one?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                dlg = SettingsDialog(self)
                if dlg.exec_() == QDialog.Accepted:
                    token = get_mapillary_token()
            if not token:
                return

        fetch_signs = self.fetch_signs_check.isChecked()
        fetch_points = self.fetch_points_check.isChecked()

        if not fetch_signs and not fetch_points:
            QMessageBox.warning(
                self, "Error",
                "Please select at least one layer to fetch "
                "(traffic signs or point features)."
            )
            return

        bbox = (
            self.west_input.value(),
            self.south_input.value(),
            self.east_input.value(),
            self.north_input.value(),
        )

        if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
            QMessageBox.warning(
                self, "Error",
                "Invalid bounding box. West must be less than East, "
                "South less than North."
            )
            return

        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        if area > 0.1:
            reply = QMessageBox.question(
                self, "Large Area",
                f"This is a large area ({area:.4f} sq degrees). "
                "This may take a while and use many API calls. Continue?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        sign_filter = self._get_sign_filter() if fetch_signs else None
        point_filter = self._get_point_filter() if fetch_points else None
        enrich = self.enrich_check.isChecked()

        self.run_btn.setEnabled(False)
        self.run_btn.setText("Fetching...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.results_text.clear()

        client = MapillaryClient(token)
        self.worker = FetchWorker(
            client, bbox, sign_filter, point_filter,
            enrich, fetch_signs, fetch_points,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, pct, msg):
        self.progress_bar.setValue(pct)
        self.status_label.setText(msg)

    def _on_finished(self, features):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Fetch Features")
        self.progress_bar.setVisible(False)

        self._last_features = features

        if not features:
            self.status_label.setText("No features found in this area.")
            self.results_text.setPlainText(
                "No features detected.\n\n"
                "Possible reasons:\n"
                "- No Mapillary coverage in this area\n"
                "- Bounding box is too small\n"
                "- Filter too restrictive\n\n"
                "Check coverage: https://www.mapillary.com/app/"
            )
            return

        from collections import Counter
        from .mutcd_mapping import get_mutcd, get_point_info

        signs = [f for f in features if f.get('source_layer') == 'traffic_sign']
        points = [f for f in features if f.get('source_layer') == 'point']

        summary = f"Found {len(features)} total features\n"
        summary += f"  Traffic signs: {len(signs)}\n"
        summary += f"  Point features: {len(points)}\n"

        if signs:
            categories = Counter()
            mutcd_codes = Counter()
            for s in signs:
                code, desc, cat = get_mutcd(s['value'])
                categories[cat] += 1
                mutcd_codes[f"{code or 'UNMAPPED'} ({desc})"] += 1

            summary += "\n--- Traffic Signs ---\n"
            summary += "By category:\n"
            for cat, count in categories.most_common():
                summary += f"  {cat:20s}  {count}\n"
            summary += "Top sign types:\n"
            for code, count in mutcd_codes.most_common(10):
                summary += f"  {code:35s}  {count}\n"

        if points:
            pt_categories = Counter()
            for p in points:
                pt_cat, pt_desc = get_point_info(p['value'])
                pt_categories[pt_cat] += 1

            summary += "\n--- Point Features ---\n"
            summary += "By category:\n"
            for cat, count in pt_categories.most_common():
                summary += f"  {cat:20s}  {count}\n"

        self.results_text.setPlainText(summary)
        self.status_label.setText(f"{len(features)} features loaded")

        self.export_geojson_btn.setEnabled(True)
        self.export_shp_btn.setEnabled(True)
        self.export_csv_btn.setEnabled(True)

        self._add_to_map(features)

    def _on_error(self, error_msg):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Fetch Features")
        self.progress_bar.setVisible(False)
        self.status_label.setText("Error occurred")
        QMessageBox.critical(self, "Error", f"Query failed:\n{error_msg}")

    # ---- Map layer ----

    def _build_feature_properties(self, feat):
        from .mutcd_mapping import get_mutcd, get_point_info

        source_layer = feat.get('source_layer', 'traffic_sign')

        if source_layer == 'traffic_sign':
            code, desc, cat = get_mutcd(feat['value'])
            return {
                'mapillary_id': feat.get('id'),
                'mapillary_value': feat.get('value', ''),
                'feature_type': 'traffic_sign',
                'category': cat,
                'mutcd_code': code or 'UNMAPPED',
                'mutcd_description': desc,
                'description': desc,
                'first_seen': feat.get('first_seen_at', ''),
                'last_seen': feat.get('last_seen_at', ''),
                'num_observations': feat.get('num_observations', 0),
                'mapillary_link': feat.get('mapillary_link', ''),
            }
        else:
            pt_cat, pt_desc = get_point_info(feat['value'])
            return {
                'mapillary_id': feat.get('id'),
                'mapillary_value': feat.get('value', ''),
                'feature_type': 'point_feature',
                'category': pt_cat,
                'mutcd_code': '',
                'mutcd_description': '',
                'description': pt_desc,
                'first_seen': feat.get('first_seen_at', ''),
                'last_seen': feat.get('last_seen_at', ''),
                'num_observations': feat.get('num_observations', 0),
                'mapillary_link': feat.get('mapillary_link', ''),
            }

    def _add_to_map(self, features):
        import json
        import tempfile
        from qgis.core import (
            QgsVectorLayer, QgsProject,
            QgsCategorizedSymbolRenderer, QgsRendererCategory,
            QgsMarkerSymbol
        )

        geojson_features = []
        for feat in features:
            props = self._build_feature_properties(feat)
            geojson_features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [feat['lng'], feat['lat']]
                },
                'properties': props,
            })

        geojson = {
            'type': 'FeatureCollection',
            'features': geojson_features,
        }

        # Drop any previous temp file before writing a new one
        self._cleanup_temp_geojson()
        tmp = tempfile.NamedTemporaryFile(
            suffix='.geojson', delete=False, mode='w'
        )
        json.dump(geojson, tmp, indent=2)
        tmp.close()
        self._temp_geojson_path = tmp.name

        layer = QgsVectorLayer(tmp.name, "Feature Inventory", "ogr")
        if not layer.isValid():
            QMessageBox.warning(self, "Error", "Failed to create map layer.")
            return

        categories_style = {
            'regulatory':       ('#E74C3C', 'circle'),
            'warning':          ('#F39C12', 'diamond'),
            'information':      ('#3498DB', 'square'),
            'complementary':    ('#2ECC71', 'triangle'),
            'signal':           ('#8E44AD', 'star'),
            'marking':          ('#F1C40F', 'cross2'),
            'infrastructure':   ('#8B4513', 'pentagon'),
            'furniture':        ('#008080', 'hexagon'),
            'traffic_control':  ('#E74C3C', 'triangle'),
            'unknown':          ('#95A5A6', 'cross'),
        }

        cat_list = []
        for cat_name, (color, shape) in categories_style.items():
            symbol = QgsMarkerSymbol.createSimple({
                'name': shape,
                'color': color,
                'size': '3.5',
                'outline_color': '#000000',
                'outline_width': '0.4',
            })
            cat_list.append(QgsRendererCategory(cat_name, symbol, cat_name.title()))

        renderer = QgsCategorizedSymbolRenderer('category', cat_list)
        layer.setRenderer(renderer)

        QgsProject.instance().addMapLayer(layer)
        self.iface.mapCanvas().refresh()

    # ---- Export ----

    def _export(self, fmt):
        import json
        import csv

        if not self._last_features:
            return

        if fmt == "geojson":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save GeoJSON", "feature_inventory.geojson",
                "GeoJSON (*.geojson)"
            )
            if not path:
                return

            geojson_features = []
            for feat in self._last_features:
                props = self._build_feature_properties(feat)
                props['latitude'] = feat['lat']
                props['longitude'] = feat['lng']
                geojson_features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [feat['lng'], feat['lat']]
                    },
                    'properties': props,
                })
            geojson = {'type': 'FeatureCollection', 'features': geojson_features}
            with open(path, 'w') as f:
                json.dump(geojson, f, indent=2)
            QMessageBox.information(
                self, "Exported",
                f"Saved {len(geojson_features)} features to:\n{path}"
            )

        elif fmt == "csv":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save CSV", "feature_inventory.csv",
                "CSV (*.csv)"
            )
            if not path:
                return

            headers = [
                'latitude', 'longitude', 'feature_type', 'category',
                'mutcd_code', 'mutcd_description', 'description',
                'mapillary_value', 'mapillary_id',
                'first_seen', 'last_seen', 'num_observations',
                'mapillary_link',
            ]
            with open(path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for feat in self._last_features:
                    props = self._build_feature_properties(feat)
                    writer.writerow({
                        'latitude': feat['lat'],
                        'longitude': feat['lng'],
                        'feature_type': props['feature_type'],
                        'category': props['category'],
                        'mutcd_code': props['mutcd_code'],
                        'mutcd_description': props['mutcd_description'],
                        'description': props['description'],
                        'mapillary_value': props['mapillary_value'],
                        'mapillary_id': props['mapillary_id'],
                        'first_seen': props['first_seen'],
                        'last_seen': props['last_seen'],
                        'num_observations': props['num_observations'],
                        'mapillary_link': props['mapillary_link'],
                    })
            QMessageBox.information(
                self, "Exported",
                f"Saved {len(self._last_features)} features to:\n{path}"
            )

        elif fmt == "shp":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Shapefile", "feature_inventory.shp",
                "Shapefile (*.shp)"
            )
            if not path:
                return

            from qgis.core import QgsVectorLayer, QgsVectorFileWriter

            if self._temp_geojson_path:
                layer = QgsVectorLayer(self._temp_geojson_path, "temp", "ogr")
                if layer.isValid():
                    error = QgsVectorFileWriter.writeAsVectorFormat(
                        layer, path, "UTF-8",
                        layer.crs(), "ESRI Shapefile"
                    )
                    if error[0] == QgsVectorFileWriter.NoError:
                        QMessageBox.information(
                            self, "Exported",
                            f"Saved {layer.featureCount()} features to:\n{path}"
                        )
                    else:
                        QMessageBox.warning(
                            self, "Error",
                            f"Shapefile export failed: {error[1]}"
                        )

