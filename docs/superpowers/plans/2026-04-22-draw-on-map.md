# Draw-on-map bbox picker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `"Draw on map (coming soon)"` placeholder in the bbox method combo with a working interactive rectangle picker that populates the existing W/S/E/N inputs.

**Architecture:** Add a `MapExtentPicker` class inside `traffic_sign_inventory_dialog.py` that wraps QGIS's built-in `QgsMapToolExtent`, handles CRS transform to WGS84, and owns a persistent `QgsRubberBand` overlay. The dialog hides while drawing, receives a `QgsRectangle` via signal, populates inputs, and restores. A new `redraw_btn` in the `.ui` file allows redefining without re-opening the combo.

**Tech Stack:** Python 3, PyQGIS (QGIS 3.0+), PyQt5, `unittest` (matching existing test style).

**Spec:** `docs/superpowers/specs/2026-04-22-draw-on-map-design.md`

---

## Pre-flight

### Pre-flight task A: Initial commit (ONE-TIME)

This repo has no commits yet and many untracked files, including `config.py` which holds the Mapillary token. **Do NOT run `git add -A` or `git add .`** — that would commit secrets.

- [ ] **Step 1: Check `config.py` for secrets**

Run:
```bash
grep -n "TOKEN\|SECRET\|KEY" config.py
```
If a real token is present, either move it to an env var / ignored file and replace with a placeholder, or add `config.py` to `.gitignore` before committing anything.

- [ ] **Step 2: Verify `.gitignore` is sensible**

Open `.gitignore` and confirm it excludes `config.py` if that file contains a live token. If not, add a line:
```
config.py
```

- [ ] **Step 3: Stage only plugin source (not secrets)**

Run (from repo root):
```bash
git add .gitignore Makefile README.txt __init__.py mapillary_client.py mutcd_mapping.py \
        metadata.txt pb_tool.cfg plugin_upload.py pylintrc resources.py resources.qrc \
        icon.png traffic_sign_inventory.py traffic_sign_inventory_dialog.py \
        traffic_sign_inventory_dialog_base.ui \
        i18n/ help/ scripts/ test/ \
        docs/
```

Do NOT include `config.py` if it contains a real token.

- [ ] **Step 4: Create the initial commit**

```bash
git commit -m "chore: initial plugin import with draw-on-map spec and plan"
```

- [ ] **Step 5: Verify clean state**

```bash
git status
```
Expected: only `config.py` (if excluded) or truly transient files remain untracked.

---

## File structure

| Path | Action | Responsibility |
|------|--------|----------------|
| `traffic_sign_inventory_dialog_base.ui` | Modify | Rename combo item index 2 from `"Draw on map (coming soon)"` to `"Draw on map"`; add `redraw_btn` QPushButton (hidden by default). |
| `traffic_sign_inventory_dialog.py` | Modify | Add `MapExtentPicker` class (at module scope, after `FetchWorker`); add dialog methods `_start_draw`, `_on_extent_picked`, `_on_draw_cancelled`, `_on_redraw_clicked`; extend `_connect_signals`, `_on_bbox_method_changed`, `closeEvent`. |
| `test/test_map_extent_picker.py` | Create | Unit tests for the `MapExtentPicker` class in isolation (CRS, state, signals). |
| `test/test_traffic_sign_inventory_dialog.py` | Modify (additive) | Add integration tests for the dialog wiring. Do NOT fix the existing broken tests — noted as out-of-scope in the spec. |

Design rationale: `MapExtentPicker` lives inside `traffic_sign_inventory_dialog.py` per the spec — the class is small (~50 LOC) and exclusively serves this dialog. Moving it to its own file would add import indirection with no payoff.

---

## Task 1: UI updates (rename combo item + add Re-draw button)

**Files:**
- Modify: `traffic_sign_inventory_dialog_base.ui`

- [ ] **Step 1: Change combo item 2 text**

Find (around line 50–54):
```xml
<item>
 <property name="text">
  <string>Draw on map (coming soon)</string>
 </property>
</item>
```
Change the `<string>` to:
```xml
<string>Draw on map</string>
```

- [ ] **Step 2: Add Re-draw button in the same grid row as the combo**

Inside `<layout class="QGridLayout" name="bbox_layout">`, add after the combo item (the combo spans columns 1–3 in row 0, so put the button in row 0 column 4, OR add a new cell after the combo; easiest: change the combo's `colspan` from 3 to 2 and put the button at column 3):

Replace:
```xml
<item row="0" column="1" colspan="3">
 <widget class="QComboBox" name="bbox_method">
```
With:
```xml
<item row="0" column="1" colspan="2">
 <widget class="QComboBox" name="bbox_method">
```

Then add after the closing `</item>` of the combo:
```xml
<item row="0" column="3">
 <widget class="QPushButton" name="redraw_btn">
  <property name="text">
   <string>Re-draw</string>
  </property>
  <property name="visible">
   <bool>false</bool>
  </property>
  <property name="toolTip">
   <string>Draw a new rectangle on the map</string>
  </property>
 </widget>
</item>
```

- [ ] **Step 3: Smoke-test the UI loads**

Run (from plugin root, with QGIS python):
```bash
python -c "from qgis.PyQt import uic; uic.loadUiType('traffic_sign_inventory_dialog_base.ui')"
```
Expected: no output, no exception.

- [ ] **Step 4: Commit**

```bash
git add traffic_sign_inventory_dialog_base.ui
git commit -m "ui: rename draw-on-map combo item and add hidden Re-draw button"
```

---

## Task 2: Scaffold `MapExtentPicker` class

**Files:**
- Modify: `traffic_sign_inventory_dialog.py`

- [ ] **Step 1: Add imports**

At the top of `traffic_sign_inventory_dialog.py`, extend the imports:
```python
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal, QObject
```
(Adds `QObject`.) At the point of use inside the class, import:
```python
from qgis.core import QgsRectangle, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
from qgis.gui import QgsMapToolExtent, QgsRubberBand
from qgis.core import QgsWkbTypes
from qgis.PyQt.QtGui import QColor
```
(Put those inside the methods where used, matching the existing pattern in `_grab_map_extent`.)

- [ ] **Step 2: Add the `MapExtentPicker` class skeleton**

Insert after the `FetchWorker` class, before the `TrafficSignInventoryDialog` class:

```python
class MapExtentPicker(QObject):
    """Wraps QgsMapToolExtent with a persistent rubber band and CRS transform.

    Emits extent_picked(QgsRectangle) in EPSG:4326 when the user completes a draw,
    or draw_cancelled() when the user presses ESC.
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
        raise NotImplementedError

    def cancel(self):
        raise NotImplementedError

    def deactivate(self):
        raise NotImplementedError

    def clear_rubber_band(self):
        raise NotImplementedError

    def _on_extent_changed(self, rect):
        raise NotImplementedError

    def _transform_to_wgs84(self, rect):
        raise NotImplementedError
```

- [ ] **Step 3: Verify module still imports**

Run:
```bash
python -c "import traffic_sign_inventory_dialog"
```
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add traffic_sign_inventory_dialog.py
git commit -m "feat: scaffold MapExtentPicker class with signals"
```

---

## Task 3: CRS transform (TDD)

**Files:**
- Create: `test/test_map_extent_picker.py`
- Modify: `traffic_sign_inventory_dialog.py`

- [ ] **Step 1: Write failing tests for CRS transform**

Create `test/test_map_extent_picker.py`:

```python
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
        #   lon -111.93, lat 33.40  ->  x=-12460000.28, y=3951534.54  (approx)
        rect_m = QgsRectangle(-12460000.0, 3951000.0, -12459000.0, 3952000.0)
        out = self.picker._transform_to_wgs84(rect_m)
        # Expect longitudes near -111.93 and latitudes near 33.40
        self.assertAlmostEqual(out.xMinimum(), -111.929617, places=3)
        self.assertAlmostEqual(out.yMinimum(), 33.396142, places=3)
        self.assertTrue(out.xMaximum() > out.xMinimum())
        self.assertTrue(out.yMaximum() > out.yMinimum())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to confirm failure**

Run (from plugin root):
```bash
python -m unittest test.test_map_extent_picker -v
```
Expected: both tests FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement `_transform_to_wgs84`**

Replace the `_transform_to_wgs84` stub with:

```python
def _transform_to_wgs84(self, rect):
    from qgis.core import (
        QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
    )
    canvas_crs = self._canvas.mapSettings().destinationCrs()
    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    if not canvas_crs.isValid() or canvas_crs == wgs84:
        return rect
    xform = QgsCoordinateTransform(canvas_crs, wgs84, QgsProject.instance())
    return xform.transformBoundingBox(rect)
```

- [ ] **Step 4: Run to confirm pass**

```bash
python -m unittest test.test_map_extent_picker -v
```
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add test/test_map_extent_picker.py traffic_sign_inventory_dialog.py
git commit -m "feat(picker): implement CRS transform to WGS84"
```

---

## Task 4: `activate()` / `deactivate()` save and restore previous map tool

**Files:**
- Modify: `test/test_map_extent_picker.py`, `traffic_sign_inventory_dialog.py`

- [ ] **Step 1: Add failing tests**

Append to `test/test_map_extent_picker.py`:

```python
from qgis.gui import QgsMapToolPan


class MapToolLifecycleTest(unittest.TestCase):

    def setUp(self):
        self.picker = MapExtentPicker(IFACE)
        self.pan_tool = QgsMapToolPan(CANVAS)
        CANVAS.setMapTool(self.pan_tool)

    def test_activate_saves_previous_map_tool(self):
        self.picker.activate()
        self.assertIs(self.picker._previous_tool, self.pan_tool)

    def test_deactivate_restores_previous_map_tool(self):
        self.picker.activate()
        self.picker.deactivate()
        self.assertIs(CANVAS.mapTool(), self.pan_tool)
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m unittest test.test_map_extent_picker -v
```
Expected: two new tests FAIL.

- [ ] **Step 3: Implement `activate` and `deactivate`**

Replace the stubs:

```python
def activate(self):
    from qgis.gui import QgsMapToolExtent
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
        # messageBar may not be available in test harness; non-fatal
        pass

def deactivate(self):
    if self._map_tool is not None:
        try:
            self._map_tool.extentChanged.disconnect(self._on_extent_changed)
        except TypeError:
            pass
        if self._previous_tool is not None:
            self._canvas.setMapTool(self._previous_tool)
        self._map_tool = None
    try:
        self.iface.messageBar().clearWidgets()
    except Exception:
        pass
```

- [ ] **Step 4: Run to confirm pass**

```bash
python -m unittest test.test_map_extent_picker -v
```
Expected: all tests so far PASS.

- [ ] **Step 5: Commit**

```bash
git add test/test_map_extent_picker.py traffic_sign_inventory_dialog.py
git commit -m "feat(picker): implement activate/deactivate map tool lifecycle"
```

---

## Task 5: `extent_picked` signal + zero-size guard

**Files:**
- Modify: `test/test_map_extent_picker.py`, `traffic_sign_inventory_dialog.py`

- [ ] **Step 1: Add failing tests**

Append:

```python
class ExtentPickedSignalTest(unittest.TestCase):

    def setUp(self):
        CANVAS.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        self.picker = MapExtentPicker(IFACE)
        self.received = []
        self.picker.extent_picked.connect(lambda r: self.received.append(r))

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
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m unittest test.test_map_extent_picker -v
```
Expected: two new tests FAIL.

- [ ] **Step 3: Implement `_on_extent_changed` and add persistent rubber band**

Replace the `_on_extent_changed` stub:

```python
def _on_extent_changed(self, rect):
    if rect.width() == 0 or rect.height() == 0:
        return
    rect_wgs84 = self._transform_to_wgs84(rect)
    self._draw_persistent_band(rect)  # draw in native canvas CRS
    self.extent_picked.emit(rect_wgs84)
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
```

- [ ] **Step 4: Run to confirm pass**

```bash
python -m unittest test.test_map_extent_picker -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add test/test_map_extent_picker.py traffic_sign_inventory_dialog.py
git commit -m "feat(picker): emit extent_picked with WGS84 rect and draw persistent overlay"
```

---

## Task 6: `clear_rubber_band()`

**Files:**
- Modify: `test/test_map_extent_picker.py`, `traffic_sign_inventory_dialog.py`

- [ ] **Step 1: Add failing test**

Append:

```python
class ClearRubberBandTest(unittest.TestCase):

    def setUp(self):
        CANVAS.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        self.picker = MapExtentPicker(IFACE)

    def test_clear_rubber_band_removes_from_canvas(self):
        rect = QgsRectangle(-111.93, 33.40, -111.92, 33.41)
        self.picker._on_extent_changed(rect)
        self.assertIsNotNone(self.picker._persistent_band)
        self.picker.clear_rubber_band()
        self.assertIsNone(self.picker._persistent_band)
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m unittest test.test_map_extent_picker -v
```
Expected: new test FAILS.

- [ ] **Step 3: Implement `clear_rubber_band`**

Replace stub:

```python
def clear_rubber_band(self):
    if self._persistent_band is not None:
        self._canvas.scene().removeItem(self._persistent_band)
        self._persistent_band = None
```

- [ ] **Step 4: Run to confirm pass**

```bash
python -m unittest test.test_map_extent_picker -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add test/test_map_extent_picker.py traffic_sign_inventory_dialog.py
git commit -m "feat(picker): implement clear_rubber_band"
```

---

## Task 7: `cancel()` emits `draw_cancelled` only

**Files:**
- Modify: `test/test_map_extent_picker.py`, `traffic_sign_inventory_dialog.py`

- [ ] **Step 1: Add failing test**

Append:

```python
from qgis.gui import QgsMapToolPan as _PanToolForCancel


class CancelTest(unittest.TestCase):

    def setUp(self):
        CANVAS.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        self.picker = MapExtentPicker(IFACE)
        self.picked = []
        self.cancelled = []
        self.picker.extent_picked.connect(lambda r: self.picked.append(r))
        self.picker.draw_cancelled.connect(lambda: self.cancelled.append(True))
        self.pan_tool = _PanToolForCancel(CANVAS)
        CANVAS.setMapTool(self.pan_tool)

    def test_cancel_does_not_emit_extent_picked(self):
        self.picker.activate()
        self.picker.cancel()
        self.assertEqual(self.picked, [])
        self.assertEqual(len(self.cancelled), 1)
        self.assertIs(CANVAS.mapTool(), self.pan_tool)
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m unittest test.test_map_extent_picker -v
```
Expected: new test FAILS.

- [ ] **Step 3: Implement `cancel`**

Replace stub:

```python
def cancel(self):
    self.deactivate()
    self.draw_cancelled.emit()
```

- [ ] **Step 4: Run to confirm pass**

```bash
python -m unittest test.test_map_extent_picker -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add test/test_map_extent_picker.py traffic_sign_inventory_dialog.py
git commit -m "feat(picker): implement cancel with draw_cancelled signal"
```

---

## Task 8: Dialog wiring — `_start_draw` + combo handling

**Files:**
- Modify: `test/test_traffic_sign_inventory_dialog.py`, `traffic_sign_inventory_dialog.py`

Note: the existing `test_traffic_sign_inventory_dialog.py` has a reference to a non-existent `button_box`. Do NOT fix that — out-of-scope per spec. Add new tests in a new `TestCase` class below the existing one.

- [ ] **Step 1: Add failing integration tests**

Append to `test/test_traffic_sign_inventory_dialog.py`:

```python
from qgis.core import QgsRectangle
from traffic_sign_inventory_dialog import TrafficSignInventoryDialog


class DrawOnMapIntegrationTest(unittest.TestCase):

    def setUp(self):
        from utilities import get_qgis_app
        self.qgis_app, self.canvas, self.iface, self.parent = get_qgis_app()
        self.dialog = TrafficSignInventoryDialog(self.iface)

    def tearDown(self):
        self.dialog.close()
        self.dialog = None

    def test_selecting_draw_on_map_hides_dialog(self):
        self.dialog.show()
        self.dialog.bbox_method.setCurrentIndex(2)
        self.assertFalse(self.dialog.isVisible())

    def test_redraw_button_hidden_by_default(self):
        self.assertFalse(self.dialog.redraw_btn.isVisible())
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m unittest test.test_traffic_sign_inventory_dialog.DrawOnMapIntegrationTest -v
```
Expected: FAIL — `_start_draw` is not wired, combo change does nothing.

- [ ] **Step 3: Wire dialog: extent_picker init, _start_draw, combo handler**

In `TrafficSignInventoryDialog.__init__`, add (after `self._connect_signals()`):
```python
self.extent_picker = None  # lazy init on first draw
```

In `_connect_signals`, keep existing lines. Add redraw handler (method implemented in Task 10):
```python
self.redraw_btn.clicked.connect(self._on_redraw_clicked)
```

Add new method:
```python
def _start_draw(self):
    if self.extent_picker is None:
        self.extent_picker = MapExtentPicker(self.iface, self)
        self.extent_picker.extent_picked.connect(self._on_extent_picked)
        self.extent_picker.draw_cancelled.connect(self._on_draw_cancelled)
    self.hide()
    self.extent_picker.activate()
```

Extend `_on_bbox_method_changed`:
```python
def _on_bbox_method_changed(self, idx):
    if idx == 0:
        self._grab_map_extent()
    elif idx == 2:
        self._start_draw()
    else:
        if self.extent_picker is not None:
            self.extent_picker.clear_rubber_band()
```

Add placeholder slots (implemented in Task 9 + 10):
```python
def _on_extent_picked(self, rect):
    pass

def _on_draw_cancelled(self):
    self.show()
    self.raise_()
    self.activateWindow()

def _on_redraw_clicked(self):
    pass
```

- [ ] **Step 4: Run to confirm pass**

```bash
python -m unittest test.test_traffic_sign_inventory_dialog.DrawOnMapIntegrationTest -v
```
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add test/test_traffic_sign_inventory_dialog.py traffic_sign_inventory_dialog.py
git commit -m "feat(dialog): wire draw-on-map combo option to MapExtentPicker"
```

---

## Task 9: Dialog wiring — `_on_extent_picked` populates inputs and restores

**Files:**
- Modify: `test/test_traffic_sign_inventory_dialog.py`, `traffic_sign_inventory_dialog.py`

- [ ] **Step 1: Add failing tests**

Append to `DrawOnMapIntegrationTest`:

```python
def test_extent_picked_populates_inputs(self):
    rect = QgsRectangle(-111.93, 33.40, -111.92, 33.41)
    # Trigger as if picker had emitted
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m unittest test.test_traffic_sign_inventory_dialog.DrawOnMapIntegrationTest -v
```
Expected: three new tests FAIL.

- [ ] **Step 3: Implement `_on_extent_picked`**

Replace:
```python
def _on_extent_picked(self, rect):
    self.west_input.setValue(rect.xMinimum())
    self.south_input.setValue(rect.yMinimum())
    self.east_input.setValue(rect.xMaximum())
    self.north_input.setValue(rect.yMaximum())
    self.redraw_btn.setVisible(True)
    self.show()
    self.raise_()
    self.activateWindow()
```

- [ ] **Step 4: Run to confirm pass**

```bash
python -m unittest test.test_traffic_sign_inventory_dialog.DrawOnMapIntegrationTest -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add test/test_traffic_sign_inventory_dialog.py traffic_sign_inventory_dialog.py
git commit -m "feat(dialog): populate inputs and restore dialog on extent picked"
```

---

## Task 10: Dialog wiring — Re-draw button

**Files:**
- Modify: `test/test_traffic_sign_inventory_dialog.py`, `traffic_sign_inventory_dialog.py`

- [ ] **Step 1: Add failing test**

Append:

```python
def test_redraw_clears_previous_rubber_band(self):
    # First draw sets up the picker + rubber band
    rect1 = QgsRectangle(-111.93, 33.40, -111.92, 33.41)
    self.dialog._start_draw()   # lazy-init picker
    self.dialog.extent_picker._on_extent_changed(rect1)  # draws band
    self.assertIsNotNone(self.dialog.extent_picker._persistent_band)

    # Re-draw should clear the band before re-activating
    self.dialog._on_redraw_clicked()
    self.assertIsNone(self.dialog.extent_picker._persistent_band)
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m unittest test.test_traffic_sign_inventory_dialog.DrawOnMapIntegrationTest.test_redraw_clears_previous_rubber_band -v
```
Expected: FAIL.

- [ ] **Step 3: Implement `_on_redraw_clicked`**

Replace:
```python
def _on_redraw_clicked(self):
    if self.extent_picker is not None:
        self.extent_picker.clear_rubber_band()
    self._start_draw()
```

- [ ] **Step 4: Run to confirm pass**

```bash
python -m unittest test.test_traffic_sign_inventory_dialog.DrawOnMapIntegrationTest -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add test/test_traffic_sign_inventory_dialog.py traffic_sign_inventory_dialog.py
git commit -m "feat(dialog): implement Re-draw button"
```

---

## Task 11: Dialog wiring — `closeEvent` cleanup + combo-change clears rubber band

**Files:**
- Modify: `test/test_traffic_sign_inventory_dialog.py`, `traffic_sign_inventory_dialog.py`

- [ ] **Step 1: Add failing tests**

Append:

```python
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
    self.dialog.close()
    self.assertIsNone(self.dialog.extent_picker._persistent_band)
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m unittest test.test_traffic_sign_inventory_dialog.DrawOnMapIntegrationTest -v
```
Expected: the first test may already pass (already implemented in Task 8); second test FAILS.

- [ ] **Step 3: Extend `closeEvent`**

Replace:
```python
def closeEvent(self, event):
    """Cancel any running worker when the dialog is closed."""
    self._cancel_worker()
    if self.extent_picker is not None:
        self.extent_picker.cancel()
        self.extent_picker.clear_rubber_band()
    super().closeEvent(event)
```

- [ ] **Step 4: Run to confirm pass**

```bash
python -m unittest test.test_traffic_sign_inventory_dialog.DrawOnMapIntegrationTest -v
```
Expected: all tests PASS.

- [ ] **Step 5: Run ALL tests one more time to catch regressions**

```bash
python -m unittest discover test -v
```
Expected: the new `MapExtentPicker` and `DrawOnMapIntegrationTest` tests all PASS. The pre-existing `button_box` tests are expected to fail (known; out of scope).

- [ ] **Step 6: Commit**

```bash
git add test/test_traffic_sign_inventory_dialog.py traffic_sign_inventory_dialog.py
git commit -m "feat(dialog): clean up picker and rubber band on dialog close"
```

---

## Task 12: Manual QA checklist

**Files:** none modified.

Run through every step in QGIS with the plugin enabled and Mapillary token configured.

- [ ] **Fresh project, WGS84 canvas:** select Draw → drag a small box → W/S/E/N populate correctly, translucent red rectangle persists on map.
- [ ] **Web Mercator canvas (EPSG:3857):** same flow → W/S/E/N values are in degrees (between -180/180 and -90/90), not meters.
- [ ] **ESC mid-draw:** dialog returns, inputs unchanged, pan tool restored.
- [ ] **Re-draw button:** click it → previous rectangle clears, new draw works.
- [ ] **Close dialog after draw:** rubber band is removed from map, pan tool is restored.
- [ ] **Switch combo 2 → 0:** rubber band clears, inputs refresh to canvas extent.
- [ ] **Click-release without dragging:** no inputs change, draw mode still active (can try again).
- [ ] **Small area → Fetch Features:** real Mapillary API call returns features inside the drawn box.
- [ ] **Canvas with no layers loaded:** draw still works.
- [ ] **Alt-Tab away and back mid-draw:** draw resumes correctly when focus returns.

If any check fails, file a bug, do NOT bump the plugin version.

- [ ] **Final commit (if any docs updated)**

If you updated anything (e.g., README), commit:
```bash
git add README.txt
git commit -m "docs: note draw-on-map feature in README"
```

---

## Known out-of-scope items (do not address here)

- Two-way binding between W/S/E/N inputs and the rubber band.
- Save/restore the last-drawn rectangle across plugin sessions.
- Fixing pre-existing `button_box` reference in `test/test_traffic_sign_inventory_dialog.py`.
- Real mouse-event simulation on `QgsMapCanvas` in the test suite.
