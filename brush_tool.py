# -*- coding: utf-8 -*-
"""
Herramientas avanzadas de Etiquetado para QGIS:
1. Polígono Lineal Directo (Estilo QGIS sin buffer circular)
2. Pincel por Flujo (Arrastre continuo)
3. Pincel por Segmentos con Grosor
4. Borrador inteligente
5. Algoritmo de Auto-Relleno de Huecos Interiores (Efecto Dona / Árbol)
6. Deshacer punto individual (Ctrl+Z / Backspace)
"""
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import (
    QgsWkbTypes,
    QgsPointXY,
    QgsGeometry,
    QgsFeature,
    QgsField,
    QgsProject,
    QgsVectorLayer
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QDate
from qgis.PyQt.QtGui import QColor, QCursor

def fill_polygon_holes(geom):
    """
    Rellena automáticamente los huecos interiores (islas o donas) de un polígono,
    haciendo que el interior sea 100% sólido.
    """
    if not geom or geom.isEmpty():
        return geom

    if geom.isMultipart():
        multi = geom.asMultiPolygon()
        filled_multi = []
        for poly in multi:
            if poly and len(poly) > 0:
                # poly[0] es el anillo exterior. Descartamos poly[1:] (huecos interiores)
                filled_multi.append([poly[0]])
        if filled_multi:
            return QgsGeometry.fromMultiPolygonXY(filled_multi)
    else:
        poly = geom.asPolygon()
        if poly and len(poly) > 0:
            return QgsGeometry.fromPolygonXY([poly[0]])

    return geom

def apply_smoothing(points, iterations=2, weight=0.25):
    """Filtro de media móvil para suavizar líneas y amortiguar el temblor."""
    if len(points) < 3 or iterations <= 0:
        return points

    smoothed = list(points)
    for _ in range(iterations):
        new_pts = [smoothed[0]]
        for i in range(1, len(smoothed) - 1):
            px = (1.0 - 2.0 * weight) * smoothed[i].x() + weight * smoothed[i - 1].x() + weight * smoothed[i + 1].x()
            py = (1.0 - 2.0 * weight) * smoothed[i].y() + weight * smoothed[i - 1].y() + weight * smoothed[i + 1].y()
            new_pts.append(QgsPointXY(px, py))
        new_pts.append(smoothed[-1])
        smoothed = new_pts

    return smoothed


# =====================================================================
# 1. POLÍGONO LINEAL DIRECTO (Estilo QGIS - Sin círculos)
# =====================================================================
class BambuLinearPolygonTool(QgsMapTool):
    feature_added = pyqtSignal()
    point_count_changed = pyqtSignal(int)

    def __init__(self, canvas, dock):
        super().__init__(canvas)
        self.canvas = canvas
        self.dock = dock
        self.points = []
        self.is_active = False

        # Rubberband for the closed polygon preview
        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setColor(QColor(46, 204, 113, 100))
        self.rubber_band.setStrokeColor(QColor(39, 174, 96, 255))
        self.rubber_band.setWidth(2)

        self.setCursor(Qt.CrossCursor)

    def activate(self):
        super().activate()
        self.points = []
        self.is_active = False
        self.point_count_changed.emit(0)

    def deactivate(self):
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self.points = []
        self.is_active = False
        self.point_count_changed.emit(0)
        super().deactivate()

    def canvasMoveEvent(self, e):
        map_pt = self.toMapCoordinates(e.pos())

        if self.is_active and self.points:
            # Preview closed polygon with current mouse position
            preview_pts = self.points + [map_pt]
            geom = QgsGeometry.fromPolygonXY([preview_pts])
            if geom and not geom.isEmpty():
                self.rubber_band.setToGeometry(geom, None)

    def canvasPressEvent(self, e):
        layer = self.dock.get_active_layer()
        if not layer or not layer.isValid():
            self.dock.show_message("Seleccione o cree una capa de polígonos primero.")
            return

        if not layer.isEditable():
            layer.startEditing()

        if e.button() == Qt.LeftButton:
            map_pt = self.toMapCoordinates(e.pos())
            self.points.append(map_pt)
            self.is_active = True
            self.point_count_changed.emit(len(self.points))

            # Update preview
            preview_pts = self.points + [map_pt]
            geom = QgsGeometry.fromPolygonXY([preview_pts])
            if geom and not geom.isEmpty():
                self.rubber_band.setToGeometry(geom, None)

        elif e.button() == Qt.RightButton:
            # Right click completes and closes the polygon!
            if len(self.points) >= 3:
                self.commit_polygon()

    def canvasDoubleClickEvent(self, e):
        # Double click completes the polygon
        if len(self.points) >= 3:
            self.commit_polygon()

    def undo_last_point(self):
        """Retrocede el último clic colocado."""
        if self.points:
            self.points.pop()
            self.point_count_changed.emit(len(self.points))
            if len(self.points) >= 1:
                # Update preview with current cursor
                map_pt = self.canvas.mouseLastXY()
                if map_pt:
                    mpt = self.toMapCoordinates(map_pt)
                    preview_pts = self.points + [mpt]
                    geom = QgsGeometry.fromPolygonXY([preview_pts])
                    self.rubber_band.setToGeometry(geom, None)
            else:
                self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
                self.is_active = False

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            if len(self.points) >= 3:
                self.commit_polygon()
        elif e.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            self.undo_last_point()
        elif e.key() == Qt.Key_Z and (e.modifiers() & Qt.ControlModifier):
            self.undo_last_point()
        elif e.key() == Qt.Key_Escape:
            self.points = []
            self.is_active = False
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            self.point_count_changed.emit(0)

    def commit_polygon(self):
        layer = self.dock.get_active_layer()
        if not layer or not layer.isEditable() or len(self.points) < 3:
            self.points = []
            self.is_active = False
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            self.point_count_changed.emit(0)
            return

        poly_pts = list(self.points)
        # Ensure closure
        if poly_pts[0] != poly_pts[-1]:
            poly_pts.append(poly_pts[0])

        smooth_iter = self.dock.get_smooth_level()
        if smooth_iter > 0 and len(poly_pts) > 4:
            smoothed = apply_smoothing(poly_pts[:-1], smooth_iter, 0.25)
            smoothed.append(smoothed[0])
            poly_geom = QgsGeometry.fromPolygonXY([smoothed])
            poly_geom = poly_geom.smooth(smooth_iter, 0.25)
        else:
            poly_geom = QgsGeometry.fromPolygonXY([poly_pts])

        # Auto-fill interior holes (donut effect)
        if self.dock.is_fill_holes_enabled():
            poly_geom = fill_polygon_holes(poly_geom)

        self.points = []
        self.is_active = False
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self.point_count_changed.emit(0)

        if not poly_geom or poly_geom.isEmpty():
            return

        should_merge = self.dock.is_merge_enabled()
        candidate_merge = None
        if should_merge:
            bb = poly_geom.boundingBox()
            candidates = [f for f in layer.getFeatures(bb) if f.geometry().intersects(poly_geom)]
            if candidates:
                candidate_merge = candidates[0]

        accepted, attr_dict = self.dock.confirm_and_get_attributes(poly_geom, is_merge=(candidate_merge is not None))
        if not accepted:
            return

        layer.beginEditCommand("Dibujar Polígono Lineal")
        if candidate_merge is not None:
            new_geom = candidate_merge.geometry().combine(poly_geom)
            if self.dock.is_fill_holes_enabled():
                new_geom = fill_polygon_holes(new_geom)
            if new_geom and not new_geom.isEmpty():
                layer.changeGeometry(candidate_merge.id(), new_geom)
                self.dock.update_feature_attributes_after_edit(layer, candidate_merge.id(), new_geom)
        else:
            feat = QgsFeature(layer.fields())
            feat.setGeometry(poly_geom)
            for fname, val in attr_dict.items():
                idx = layer.fields().indexOf(fname)
                if idx != -1:
                    feat.setAttribute(idx, val)
            layer.addFeature(feat)

        layer.endEditCommand()
        layer.triggerRepaint()
        self.canvas.refresh()
        self.feature_added.emit()


# =====================================================================
# 2. PINCEL POR FLUJO (Freehand Streaming Brush)
# =====================================================================
class BambuStreamingBrushTool(QgsMapTool):
    feature_added = pyqtSignal()

    def __init__(self, canvas, dock):
        super().__init__(canvas)
        self.canvas = canvas
        self.dock = dock
        self.is_drawing = False
        self.raw_points = []

        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setColor(QColor(46, 204, 113, 110))
        self.rubber_band.setStrokeColor(QColor(39, 174, 96, 200))
        self.rubber_band.setWidth(2)

        self.cursor_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.cursor_band.setColor(QColor(46, 204, 113, 30))
        self.cursor_band.setStrokeColor(QColor(46, 204, 113, 180))
        self.cursor_band.setWidth(1)

        self.setCursor(Qt.CrossCursor)

    @property
    def radius_map_units(self):
        return self.dock.get_brush_radius()

    @property
    def smooth_iterations(self):
        return self.dock.get_smooth_level()

    def activate(self):
        super().activate()
        self.cursor_band.reset(QgsWkbTypes.PolygonGeometry)
        self.cursor_band.show()

    def deactivate(self):
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self.cursor_band.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()

    def canvasMoveEvent(self, e):
        map_pt = self.toMapCoordinates(e.pos())
        r = self.radius_map_units

        geom_circ = QgsGeometry.fromPointXY(map_pt).buffer(r, 16)
        self.cursor_band.setToGeometry(geom_circ, None)

        if self.is_drawing:
            min_dist = max(r * 0.2, 0.15)
            if not self.raw_points or self.raw_points[-1].distance(map_pt) >= min_dist:
                self.raw_points.append(map_pt)
                self._update_stroke_preview()

    def canvasPressEvent(self, e):
        if e.button() == Qt.LeftButton:
            layer = self.dock.get_active_layer()
            if not layer or not layer.isValid():
                self.dock.show_message("Seleccione o cree una capa de polígonos primero.")
                return

            if not layer.isEditable():
                layer.startEditing()

            self.is_drawing = True
            map_pt = self.toMapCoordinates(e.pos())
            self.raw_points = [map_pt]
            self._update_stroke_preview()

    def canvasReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            map_pt = self.toMapCoordinates(e.pos())
            self.raw_points.append(map_pt)

            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            self._commit_stroke()
            self.raw_points = []

    def _get_smoothed_geometry(self):
        r = self.radius_map_units
        if len(self.raw_points) == 1:
            geom = QgsGeometry.fromPointXY(self.raw_points[0]).buffer(r, 16)
        elif len(self.raw_points) > 1:
            smoothed_pts = apply_smoothing(self.raw_points, self.smooth_iterations, 0.25)
            line = QgsGeometry.fromPolylineXY(smoothed_pts)
            if self.smooth_iterations > 0 and len(smoothed_pts) > 2:
                line = line.smooth(self.smooth_iterations, 0.25)
            geom = line.buffer(r, 16)
        else:
            return None

        # Auto-fill donut holes if enabled
        if geom and self.dock.is_fill_holes_enabled():
            geom = fill_polygon_holes(geom)

        return geom

    def _update_stroke_preview(self):
        geom = self._get_smoothed_geometry()
        if geom and not geom.isEmpty():
            self.rubber_band.setToGeometry(geom, None)

    def _commit_stroke(self):
        layer = self.dock.get_active_layer()
        if not layer or not layer.isEditable():
            return

        stroke_geom = self._get_smoothed_geometry()
        if not stroke_geom or stroke_geom.isEmpty():
            return

        should_merge = self.dock.is_merge_enabled()
        candidate_merge = None
        if should_merge:
            bb = stroke_geom.boundingBox()
            candidates = [f for f in layer.getFeatures(bb) if f.geometry().intersects(stroke_geom)]
            if candidates:
                candidate_merge = candidates[0]

        accepted, attr_dict = self.dock.confirm_and_get_attributes(stroke_geom, is_merge=(candidate_merge is not None))
        if not accepted:
            return

        layer.beginEditCommand("Pintar etiqueta (Flujo)")
        if candidate_merge is not None:
            new_geom = candidate_merge.geometry().combine(stroke_geom)
            if self.dock.is_fill_holes_enabled():
                new_geom = fill_polygon_holes(new_geom)
            if new_geom and not new_geom.isEmpty():
                layer.changeGeometry(candidate_merge.id(), new_geom)
                self.dock.update_feature_attributes_after_edit(layer, candidate_merge.id(), new_geom)
        else:
            feat = QgsFeature(layer.fields())
            feat.setGeometry(stroke_geom)
            for fname, val in attr_dict.items():
                idx = layer.fields().indexOf(fname)
                if idx != -1:
                    feat.setAttribute(idx, val)
            layer.addFeature(feat)

        layer.endEditCommand()
        layer.triggerRepaint()
        self.canvas.refresh()
        self.feature_added.emit()


# =====================================================================
# 3. PINCEL POR SEGMENTOS CON GROSOR
# =====================================================================
class BambuSegmentBrushTool(QgsMapTool):
    feature_added = pyqtSignal()
    point_count_changed = pyqtSignal(int)

    def __init__(self, canvas, dock):
        super().__init__(canvas)
        self.canvas = canvas
        self.dock = dock
        self.is_active_path = False
        self.points = []

        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setColor(QColor(46, 204, 113, 110))
        self.rubber_band.setStrokeColor(QColor(39, 174, 96, 220))
        self.rubber_band.setWidth(2)

        self.cursor_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.cursor_band.setColor(QColor(46, 204, 113, 30))
        self.cursor_band.setStrokeColor(QColor(46, 204, 113, 180))
        self.cursor_band.setWidth(1)

        self.setCursor(Qt.CrossCursor)

    @property
    def radius_map_units(self):
        return self.dock.get_brush_radius()

    @property
    def smooth_iterations(self):
        return self.dock.get_smooth_level()

    def activate(self):
        super().activate()
        self.points = []
        self.is_active_path = False
        self.cursor_band.reset(QgsWkbTypes.PolygonGeometry)
        self.cursor_band.show()
        self.point_count_changed.emit(0)

    def deactivate(self):
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self.cursor_band.reset(QgsWkbTypes.PolygonGeometry)
        self.points = []
        self.is_active_path = False
        self.point_count_changed.emit(0)
        super().deactivate()

    def canvasMoveEvent(self, e):
        map_pt = self.toMapCoordinates(e.pos())
        r = self.radius_map_units

        geom_circ = QgsGeometry.fromPointXY(map_pt).buffer(r, 16)
        self.cursor_band.setToGeometry(geom_circ, None)

        if self.is_active_path and self.points:
            preview_pts = self.points + [map_pt]
            self._update_preview(preview_pts)

    def canvasPressEvent(self, e):
        layer = self.dock.get_active_layer()
        if not layer or not layer.isValid():
            self.dock.show_message("Seleccione o cree una capa de polígonos primero.")
            return

        if not layer.isEditable():
            layer.startEditing()

        if e.button() == Qt.LeftButton:
            map_pt = self.toMapCoordinates(e.pos())
            self.points.append(map_pt)
            self.is_active_path = True
            self.point_count_changed.emit(len(self.points))
            self._update_preview(self.points)

        elif e.button() == Qt.RightButton:
            if len(self.points) >= 1:
                self.commit_segments()

    def canvasDoubleClickEvent(self, e):
        if len(self.points) >= 1:
            self.commit_segments()

    def undo_last_point(self):
        """Retrocede el último punto del trazado."""
        if self.points:
            self.points.pop()
            self.point_count_changed.emit(len(self.points))
            if self.points:
                map_pt = self.canvas.mouseLastXY()
                if map_pt:
                    mpt = self.toMapCoordinates(map_pt)
                    self._update_preview(self.points + [mpt])
                else:
                    self._update_preview(self.points)
            else:
                self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
                self.is_active_path = False

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            if len(self.points) >= 1:
                self.commit_segments()
        elif e.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            self.undo_last_point()
        elif e.key() == Qt.Key_Z and (e.modifiers() & Qt.ControlModifier):
            self.undo_last_point()
        elif e.key() == Qt.Key_Escape:
            self.points = []
            self.is_active_path = False
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            self.point_count_changed.emit(0)

    def _update_preview(self, pts):
        r = self.radius_map_units
        if len(pts) == 1:
            geom = QgsGeometry.fromPointXY(pts[0]).buffer(r, 16)
        else:
            if self.smooth_iterations > 0 and len(pts) > 2:
                smoothed_pts = apply_smoothing(pts, self.smooth_iterations, 0.25)
                line = QgsGeometry.fromPolylineXY(smoothed_pts)
                line = line.smooth(self.smooth_iterations, 0.25)
            else:
                line = QgsGeometry.fromPolylineXY(pts)
            geom = line.buffer(r, 16)

        if geom and not geom.isEmpty():
            if self.dock.is_fill_holes_enabled():
                geom = fill_polygon_holes(geom)
            self.rubber_band.setToGeometry(geom, None)

    def commit_segments(self):
        layer = self.dock.get_active_layer()
        if not layer or not layer.isEditable() or not self.points:
            self.points = []
            self.is_active_path = False
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            self.point_count_changed.emit(0)
            return

        r = self.radius_map_units
        if len(self.points) == 1:
            stroke_geom = QgsGeometry.fromPointXY(self.points[0]).buffer(r, 16)
        else:
            if self.smooth_iterations > 0 and len(self.points) > 2:
                smoothed_pts = apply_smoothing(self.points, self.smooth_iterations, 0.25)
                line = QgsGeometry.fromPolylineXY(smoothed_pts)
                line = line.smooth(self.smooth_iterations, 0.25)
            else:
                line = QgsGeometry.fromPolylineXY(self.points)
            stroke_geom = line.buffer(r, 16)

        # Auto-fill donut holes if enabled
        if stroke_geom and self.dock.is_fill_holes_enabled():
            stroke_geom = fill_polygon_holes(stroke_geom)

        self.points = []
        self.is_active_path = False
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self.point_count_changed.emit(0)

        if not stroke_geom or stroke_geom.isEmpty():
            return

        should_merge = self.dock.is_merge_enabled()
        candidate_merge = None
        if should_merge:
            bb = stroke_geom.boundingBox()
            candidates = [f for f in layer.getFeatures(bb) if f.geometry().intersects(stroke_geom)]
            if candidates:
                candidate_merge = candidates[0]

        accepted, attr_dict = self.dock.confirm_and_get_attributes(stroke_geom, is_merge=(candidate_merge is not None))
        if not accepted:
            return

        layer.beginEditCommand("Pintar etiqueta (Segmentos)")
        if candidate_merge is not None:
            new_geom = candidate_merge.geometry().combine(stroke_geom)
            if self.dock.is_fill_holes_enabled():
                new_geom = fill_polygon_holes(new_geom)
            if new_geom and not new_geom.isEmpty():
                layer.changeGeometry(candidate_merge.id(), new_geom)
                self.dock.update_feature_attributes_after_edit(layer, candidate_merge.id(), new_geom)
        else:
            feat = QgsFeature(layer.fields())
            feat.setGeometry(stroke_geom)
            for fname, val in attr_dict.items():
                idx = layer.fields().indexOf(fname)
                if idx != -1:
                    feat.setAttribute(idx, val)
            layer.addFeature(feat)

        layer.endEditCommand()
        layer.triggerRepaint()
        self.canvas.refresh()
        self.feature_added.emit()


# =====================================================================
# 4. BORRADOR (Eraser Tool)
# =====================================================================
class BambuEraserTool(QgsMapTool):
    features_modified = pyqtSignal()

    def __init__(self, canvas, dock):
        super().__init__(canvas)
        self.canvas = canvas
        self.dock = dock
        self.is_drawing = False
        self.raw_points = []

        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setColor(QColor(240, 98, 146, 120))
        self.rubber_band.setStrokeColor(QColor(233, 30, 99, 220))
        self.rubber_band.setWidth(2)

        self.cursor_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.cursor_band.setColor(QColor(240, 98, 146, 30))
        self.cursor_band.setStrokeColor(QColor(233, 30, 99, 180))
        self.cursor_band.setWidth(1)

        self.setCursor(Qt.CrossCursor)

    @property
    def radius_map_units(self):
        return self.dock.get_brush_radius()

    @property
    def smooth_iterations(self):
        return self.dock.get_smooth_level()

    def activate(self):
        super().activate()
        self.cursor_band.reset(QgsWkbTypes.PolygonGeometry)
        self.cursor_band.show()

    def deactivate(self):
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self.cursor_band.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()

    def canvasMoveEvent(self, e):
        map_pt = self.toMapCoordinates(e.pos())
        r = self.radius_map_units

        geom_circ = QgsGeometry.fromPointXY(map_pt).buffer(r, 16)
        self.cursor_band.setToGeometry(geom_circ, None)

        if self.is_drawing:
            min_dist = max(r * 0.2, 0.15)
            if not self.raw_points or self.raw_points[-1].distance(map_pt) >= min_dist:
                self.raw_points.append(map_pt)
                self._update_preview()

    def canvasPressEvent(self, e):
        if e.button() == Qt.LeftButton:
            layer = self.dock.get_active_layer()
            if not layer or not layer.isValid():
                self.dock.show_message("Seleccione una capa de etiquetas válida.")
                return

            if not layer.isEditable():
                layer.startEditing()

            self.is_drawing = True
            map_pt = self.toMapCoordinates(e.pos())
            self.raw_points = [map_pt]
            self._update_preview()

    def canvasReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            map_pt = self.toMapCoordinates(e.pos())
            self.raw_points.append(map_pt)

            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            self._commit_eraser()
            self.raw_points = []

    def _get_eraser_geometry(self):
        r = self.radius_map_units
        if len(self.raw_points) == 1:
            return QgsGeometry.fromPointXY(self.raw_points[0]).buffer(r, 16)
        elif len(self.raw_points) > 1:
            smoothed_pts = apply_smoothing(self.raw_points, self.smooth_iterations, 0.25)
            line = QgsGeometry.fromPolylineXY(smoothed_pts)
            if self.smooth_iterations > 0 and len(smoothed_pts) > 2:
                line = line.smooth(self.smooth_iterations, 0.25)
            return line.buffer(r, 16)
        return None

    def _update_preview(self):
        geom = self._get_eraser_geometry()
        if geom and not geom.isEmpty():
            self.rubber_band.setToGeometry(geom, None)

    def _commit_eraser(self):
        layer = self.dock.get_active_layer()
        if not layer or not layer.isEditable():
            return

        eraser_geom = self._get_eraser_geometry()
        if not eraser_geom or eraser_geom.isEmpty():
            return

        layer.beginEditCommand("Borrar trazo de etiqueta")
        bb = eraser_geom.boundingBox()
        features = list(layer.getFeatures(bb))
        modified = False

        for feat in features:
            fgeom = feat.geometry()
            if fgeom.intersects(eraser_geom):
                diff = fgeom.difference(eraser_geom)
                if diff.isEmpty() or diff.area() < 0.05:
                    layer.deleteFeature(feat.id())
                else:
                    layer.changeGeometry(feat.id(), diff)
                    self.dock.update_feature_attributes_after_edit(layer, feat.id(), diff)
                modified = True

        layer.endEditCommand()
        layer.triggerRepaint()
        self.canvas.refresh()

        if modified:
            self.features_modified.emit()
