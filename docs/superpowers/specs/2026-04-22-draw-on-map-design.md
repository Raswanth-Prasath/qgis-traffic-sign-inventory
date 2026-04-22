# Draw-on-map bbox picker — Design

Status: Approved
Date: 2026-04-22
Author: Raswanth
Context file: `traffic_sign_inventory_dialog.py`

## 1. Summary

Replace the existing `"Draw on map (coming soon)"` placeholder in the bbox
method combo with a working interactive picker. The user selects
`"Draw on map"`, the dialog temporarily hides, the user drags a rectangle on
the QGIS map canvas, and the four W/S/E/N coordinate inputs are populated in
WGS84. A translucent overlay of the drawn rectangle remains visible on the
map so the user can visually confirm the area before fetching, and a
`"Re-draw"` button allows redefining without re-opening the combo.

## 2. Goals and non-goals

**Goals**

- Replace the placeholder third option in `bbox_method` with a functional
  click-drag rectangle picker.
- Hide the dialog during draw so the map is fully visible.
- Populate the existing W/S/E/N inputs in EPSG:4326 regardless of the
  canvas CRS.
- Persist the drawn rectangle on the map until the user re-draws, changes
  bbox method, or closes the dialog.
- Provide ESC cancellation and a `"Re-draw"` affordance.
- Downstream `bbox` pipeline stays untouched — the feature only produces
  the same `(west, south, east, north)` tuple the other two methods produce.

**Non-goals**

- Polygon or freehand selection.
- Two-way sync between the W/S/E/N inputs and the rubber band after draw.
  Manual edits to the inputs do not update the overlay.
- Snapping to features, layer-constrained drawing, or rotation.
- Fixing the pre-existing dialog test that references a non-existent
  `button_box` attribute — out of scope; noted but not addressed.

## 3. Locked design decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Rectangle only (no polygon) | Downstream API consumes a bbox tuple; polygons would either be reduced to their bbox (misleading) or force a larger refactor. |
| 2 | Click-drag interaction | Matches QGIS's own "Zoom to rectangle" and most selection tools. Single-gesture flow. |
| 3 | Dialog hides during draw; auto-restores on completion or ESC | Maximum map visibility on small screens. |
| 4 | Rubber band persists until re-draw / method change / dialog close | Visual confirmation of the selected area before fetch. |
| 5 | Use QGIS's built-in `QgsMapToolExtent` rather than a custom `QgsMapTool` | Less code, native styling, handles ESC and mouse-move for free. |

## 4. UX flow

```
1. User selects "Draw on map" from bbox_method (index 2).
   (The combo item text changes from "Draw on map (coming soon)"
   to "Draw on map".)

2. Dialog hides. iface.messageBar() shows a floating hint:
   "Drag a rectangle on the map to define the area. Press ESC to cancel."
   Cursor becomes a crosshair.

3. User click-drags on the map canvas. QgsMapToolExtent shows a live
   rubber band of the rectangle as it is drawn.

4. On mouse release:
   - Drawn rectangle is transformed to WGS84 if canvas CRS ≠ EPSG:4326.
   - W/S/E/N spinboxes are populated.
   - Dialog is restored (show + raise + activateWindow).
   - A persistent translucent rubber band is drawn on the map.
   - "Re-draw" button becomes visible next to the combo.

5. User options:
   - "Fetch Features" to run the query.
   - "Re-draw" to repeat from step 2 (old rubber band cleared first).
   - Switch combo to another bbox method — rubber band clears.
   - Manually edit W/S/E/N — no effect on the overlay (by design).

6. Dialog close: rubber band removed, previous map tool restored,
   message bar hint cleared.

ESC during draw: cancel, restore dialog, inputs unchanged,
previous map tool restored.
```

## 5. Component design

All code lives in `traffic_sign_inventory_dialog.py`. No new modules — the
feature is tightly coupled to dialog state and small enough that a separate
file would add more indirection than value.

### 5.1 `MapExtentPicker` (new class, ~50 LOC)

Owns the QGIS map-tool lifecycle, the persistent rubber band, and the CRS
transform. Pure signal-based interface; it does not know about the dialog.

```
class MapExtentPicker(QObject):
    extent_picked = pyqtSignal(object)   # QgsRectangle in EPSG:4326
    draw_cancelled = pyqtSignal()

    def __init__(self, iface):
        ...
        self._previous_tool = None
        self._map_tool = None            # QgsMapToolExtent
        self._persistent_band = None     # QgsRubberBand
        self._hint_item = None           # iface.messageBar() widget

    def activate(self):
        # save previous tool, install QgsMapToolExtent,
        # connect extentChanged, show messageBar hint
        ...

    def cancel(self):
        # ESC path or dialog-close path:
        # restore previous tool, clear hint, do NOT emit extent_picked;
        # emit draw_cancelled only when user pressed ESC
        ...

    def clear_rubber_band(self):
        # remove persistent rectangle overlay from map canvas
        ...

    def deactivate(self):
        # restore previous map tool + clean up hint and transient state
        # (rubber band is kept unless clear_rubber_band is also called)
        ...

    # internal
    def _on_extent_changed(self, rect):
        # ignore zero-size rects, transform to WGS84,
        # draw persistent rubber band, emit extent_picked,
        # then deactivate (but keep persistent band visible)
        ...
```

### 5.2 `TrafficSignInventoryDialog` additions

```
New state:
    self.extent_picker: MapExtentPicker   # lazy-initialized on first use

UI additions (in traffic_sign_inventory_dialog_base.ui):
    self.redraw_btn: QPushButton "Re-draw"
        - placed in the same grid cell row as bbox_method, right-aligned
        - setVisible(False) by default
    bbox_method item at index 2 text: "Draw on map (coming soon)"
        -> "Draw on map"

Extended methods:
    _connect_signals(): wire redraw_btn.clicked, and both
        extent_picker signals (extent_picked, draw_cancelled)
    _on_bbox_method_changed(idx):
        if idx == 2: self._start_draw()
        else: if picker exists, picker.clear_rubber_band()
    closeEvent(event):
        if picker exists: picker.cancel(); picker.clear_rubber_band()
        super().closeEvent(event)

New methods:
    _start_draw():
        lazy-init extent_picker if needed
        self.hide()
        self.extent_picker.activate()

    _on_extent_picked(rect_wgs84):
        self.west_input.setValue(rect_wgs84.xMinimum())
        self.south_input.setValue(rect_wgs84.yMinimum())
        self.east_input.setValue(rect_wgs84.xMaximum())
        self.north_input.setValue(rect_wgs84.yMaximum())
        self.redraw_btn.setVisible(True)
        self.show(); self.raise_(); self.activateWindow()

    _on_draw_cancelled():
        self.show(); self.raise_(); self.activateWindow()

    _on_redraw_clicked():
        if picker exists: picker.clear_rubber_band()
        self._start_draw()
```

**Interface contract:** the dialog never touches QGIS map-tool or rubber-band
APIs. It talks to `MapExtentPicker` via three method calls
(`activate`, `clear_rubber_band`, `cancel`) and two signals
(`extent_picked`, `draw_cancelled`). This boundary is what allows us to
unit-test draw logic in isolation from dialog state.

## 6. CRS handling

Same pattern as the existing `_grab_map_extent` method:

```python
canvas_crs = canvas.mapSettings().destinationCrs()
wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
if canvas_crs != wgs84:
    xform = QgsCoordinateTransform(canvas_crs, wgs84, QgsProject.instance())
    rect_wgs84 = xform.transformBoundingBox(rect)
else:
    rect_wgs84 = rect
```

`transformBoundingBox` handles antimeridian-crossing correctly; if the result
still violates `west < east`, the existing validator in `_run_query` surfaces
the standard error message.

## 7. Edge cases

| Case | Handling |
|------|----------|
| Click-release without dragging (zero-size rect) | Ignore event; stay in draw mode; no input change. |
| Antimeridian crossing | `transformBoundingBox` handles it; downstream validator catches truly invalid bboxes. |
| Dialog closed mid-draw | `closeEvent` calls `picker.cancel()` and `picker.clear_rubber_band()`. |
| User switches `bbox_method` while draw is active | Deactivate picker, clear rubber band, no input mutation. |
| ESC during draw | `draw_cancelled` signal; dialog restored; inputs untouched; previous tool restored. |
| Canvas CRS not set (new empty project) | Skip transform (matches existing `_grab_map_extent` behavior). |
| User activates a different QGIS map tool after draw | Not our problem — picker has already deactivated; persistent rubber band stays. |
| Alt-Tab away mid-draw | Default Qt behavior; draw resumes on focus return. |

## 8. Testing plan

### 8.1 Layer 1 — Automated unit tests

File: `test/test_map_extent_picker.py` (new)

| Test | Verifies |
|------|----------|
| `test_crs_transform_wgs84_passthrough` | EPSG:4326 canvas → rect returned unchanged. |
| `test_crs_transform_web_mercator_to_wgs84` | EPSG:3857 canvas → correct lat/lng output within tolerance 1e-6. |
| `test_activate_saves_previous_map_tool` | Previous tool stored and retrievable after `activate()`. |
| `test_deactivate_restores_previous_map_tool` | `canvas.mapTool()` equals stored tool after `deactivate()`. |
| `test_clear_rubber_band_removes_from_canvas` | Rubber band removed after `clear_rubber_band()`. |
| `test_extent_picked_signal_emitted_on_draw_complete` | Invoking `_on_extent_changed(rect)` emits `extent_picked` once with WGS84 rect. |
| `test_zero_size_rect_is_ignored` | `_on_extent_changed` with degenerate rect → no signal. |
| `test_cancel_does_not_emit_extent_picked` | `cancel()` emits only `draw_cancelled`; previous tool restored. |

### 8.2 Layer 2 — Dialog integration tests

Extend `test/test_traffic_sign_inventory_dialog.py` (note: the existing file
has unrelated bugs — out of scope).

| Test | Verifies |
|------|----------|
| `test_selecting_draw_on_map_hides_dialog` | Setting `bbox_method` to index 2 → `isVisible()` becomes False. |
| `test_extent_picked_populates_inputs` | Emitting fake `extent_picked` with a known rect → W/S/E/N spinboxes match. |
| `test_extent_picked_restores_dialog` | After signal, `isVisible()` becomes True. |
| `test_redraw_button_hidden_by_default` | On dialog init, `redraw_btn.isVisible()` is False. |
| `test_redraw_button_visible_after_first_draw` | After `extent_picked` fires once, button is visible. |
| `test_switching_bbox_method_clears_rubber_band` | Changing combo from 2 → 0 invokes `clear_rubber_band` once. |
| `test_close_event_deactivates_picker` | `dialog.close()` → `picker.cancel()` called. |

### 8.3 Layer 3 — Manual QA checklist

Run before shipping. Mouse-event simulation on `QgsMapCanvas` is brittle and
not worth automating for a single map tool — the authoritative verification
is interactive.

1. Fresh project, WGS84 canvas: select Draw → drag over a small area →
   inputs populate correctly and rubber band persists.
2. Same flow with canvas in Web Mercator (EPSG:3857) → inputs are in
   degrees, not meters.
3. ESC mid-draw → dialog returns, inputs unchanged.
4. Draw, then Re-draw → old rectangle clears, new draw works.
5. Draw, then close dialog → rubber band is removed, pan tool restored.
6. Draw, then switch combo to "Use current map extent" → rubber band
   clears, inputs refresh to canvas extent.
7. Click-release without dragging → no input change, draw mode persists.
8. Draw a small area → click Fetch → real API call returns features inside
   the drawn area.
9. Draw on a canvas with no layers loaded → still works.
10. Alt-Tab away and back mid-draw → draw resumes correctly.

### 8.4 Explicitly not tested

- Real mouse-event simulation through `QTest.mouseClick` on the canvas —
  known-flaky in QGIS plugin testing, platform-dependent.
- Multi-monitor geometry.
- Pre-existing bugs in `test_traffic_sign_inventory_dialog.py`.

## 9. Risks

| Risk | Mitigation |
|------|------------|
| `QgsMapToolExtent` behavior varies across QGIS 3.x minor versions | Pinned behavior assumption: `extentChanged` signal with `QgsRectangle`. If a target QGIS version lacks it, fall back to Approach 2 (custom `QgsMapTool` + `QgsRubberBand`). |
| Dialog hide/restore glitches on some window managers | Use `show() + raise_() + activateWindow()` triple on restore — standard Qt pattern. |
| Persistent rubber band lingers if plugin crashes during draw | `closeEvent` cleans up on dialog close; QGIS cleans up layers on plugin unload. Acceptable residual risk. |

## 10. Out-of-scope follow-ups (recorded, not implemented)

- Two-way binding between input fields and rubber band.
- Save/restore last-drawn rectangle across sessions.
- Fix the stale `button_box` reference in `test_traffic_sign_inventory_dialog.py`.
