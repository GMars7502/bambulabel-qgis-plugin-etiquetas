# -*- coding: utf-8 -*-
"""
Panel de Control y Gestión de Etiquetas BambuLabel Studio para QGIS
Versión 1.2:
- Polígono Lineal Directo (Estilo QGIS)
- Pincel por Flujo y Tramos con Grosor
- Auto-Relleno de Huecos Interiores (Efecto Dona / Árbol)
- Deshacer punto individual (Ctrl+Z / Backspace)
- Esquema dinámico de atributos
"""
import os
import datetime
from qgis.PyQt.QtCore import Qt, QDate
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QSlider,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QToolButton,
    QAbstractItemView,
    QDialog,
    QScrollArea,
    QFrame
)
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsCollapsibleGroupBox
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsField,
    QgsFields,
    QgsFeature,
    QgsGeometry,
    QgsFillSymbol,
    QgsSingleSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsVectorFileWriter,
    QgsWkbTypes
)
from qgis.PyQt.QtCore import QVariant

from .icons import get_icon


class BambuConfirmLabelDialog(QDialog):
    """
    Ventana emergente que muestra la geometría recién dibujada,
    calcula id y Superficie, y permite al usuario verificar o escribir
    el nombre de la Imagen (u otros atributos) antes de dar Aceptar o Cancelar.
    """
    def __init__(self, parent, layer, geom, default_attrs, raster_names, is_merge=False):
        super().__init__(parent)
        self.setWindowTitle("Confirmar Nueva Etiqueta — BambuLabel")
        self.setMinimumWidth(460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.layer = layer
        self.geom = geom
        self.default_attrs = default_attrs
        self.input_widgets = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # 1. Resumen Geométrico
        grp_summary = QGroupBox("1. Información de la Geometría Digitalizada")
        l_sum = QGridLayout(grp_summary)
        l_sum.setContentsMargins(10, 10, 10, 10)
        l_sum.setSpacing(8)

        area_m2 = round(geom.area(), 2)
        perimeter_m = round(geom.length(), 2)

        lbl_sup_title = QLabel("Superficie Calculada:")
        lbl_sup_title.setStyleSheet("font-weight: bold; color: #1b5e20;")
        lbl_sup_val = QLabel(f"<b>{area_m2:,.2f} m²</b> &nbsp;&nbsp;({area_m2 / 10000.0:.4f} ha)")
        lbl_sup_val.setStyleSheet("color: #1b5e20; font-size: 13px;")
        l_sum.addWidget(lbl_sup_title, 0, 0)
        l_sum.addWidget(lbl_sup_val, 0, 1)

        lbl_per_title = QLabel("Perímetro:")
        lbl_per_val = QLabel(f"{perimeter_m:,.2f} m")
        lbl_per_val.setStyleSheet("color: #444;")
        l_sum.addWidget(lbl_per_title, 1, 0)
        l_sum.addWidget(lbl_per_val, 1, 1)

        if is_merge:
            lbl_merge = QLabel("⚠️ <i>Aviso: Se fusionará con un polígono adyacente existente.</i>")
            lbl_merge.setStyleSheet("color: #e65100; font-weight: bold;")
            l_sum.addWidget(lbl_merge, 2, 0, 1, 2)

        layout.addWidget(grp_summary)

        # 2. Atributos a Registrar
        grp_fields = QGroupBox("2. Atributos a Registrar en la Capa")
        f_layout = QGridLayout(grp_fields)
        f_layout.setContentsMargins(10, 10, 10, 10)
        f_layout.setSpacing(8)

        first_focus_widget = None
        row = 0

        for field in layer.fields():
            fname = field.name()
            fn_l = fname.lower()
            default_val = default_attrs.get(fname, "")

            lbl_f = QLabel(f"<b>{fname}:</b>")
            f_layout.addWidget(lbl_f, row, 0)

            if fn_l in ("imagen", "image"):
                combo_img = QComboBox()
                combo_img.setEditable(True)
                for r in raster_names:
                    combo_img.addItem(r)
                if default_val:
                    idx = combo_img.findText(str(default_val))
                    if idx != -1:
                        combo_img.setCurrentIndex(idx)
                    else:
                        combo_img.setEditText(str(default_val))
                combo_img.setToolTip("Nombre de la imagen TIFF asociada (puedes seleccionarlo o escribirlo libremente)")
                f_layout.addWidget(combo_img, row, 1)
                self.input_widgets[fname] = combo_img
                first_focus_widget = combo_img

            elif fn_l == "id":
                spin_id = QSpinBox()
                spin_id.setRange(0, 99999999)
                try:
                    spin_id.setValue(int(default_val) if default_val is not None else 1)
                except:
                    spin_id.setValue(1)
                f_layout.addWidget(spin_id, row, 1)
                self.input_widgets[fname] = spin_id
                if not first_focus_widget:
                    first_focus_widget = spin_id

            elif fn_l in ("superficie", "area", "area_m2"):
                spin_area = QDoubleSpinBox()
                spin_area.setRange(0.0, 99999999.0)
                spin_area.setDecimals(2)
                spin_area.setSuffix(" m²")
                try:
                    spin_area.setValue(float(default_val) if default_val is not None else area_m2)
                except:
                    spin_area.setValue(area_m2)
                f_layout.addWidget(spin_area, row, 1)
                self.input_widgets[fname] = spin_area

            elif fn_l == "area_ha":
                spin_ha = QDoubleSpinBox()
                spin_ha.setRange(0.0, 999999.0)
                spin_ha.setDecimals(4)
                spin_ha.setSuffix(" ha")
                try:
                    spin_ha.setValue(float(default_val) if default_val is not None else round(area_m2 / 10000.0, 4))
                except:
                    spin_ha.setValue(round(area_m2 / 10000.0, 4))
                f_layout.addWidget(spin_ha, row, 1)
                self.input_widgets[fname] = spin_ha

            else:
                txt = QLineEdit(str(default_val) if default_val is not None else "")
                f_layout.addWidget(txt, row, 1)
                self.input_widgets[fname] = txt
                if not first_focus_widget:
                    first_focus_widget = txt

            row += 1

        layout.addWidget(grp_fields)

        # 3. Botones Aceptar / Cancelar
        h_btn = QHBoxLayout()
        h_btn.addStretch(1)

        btn_cancel = QPushButton("❌ Cancelar (Esc)")
        btn_cancel.setStyleSheet("padding: 6px 14px; font-weight: bold;")
        btn_cancel.clicked.connect(self.reject)
        h_btn.addWidget(btn_cancel)

        btn_ok = QPushButton("✅ Aceptar y Cargar (Enter)")
        btn_ok.setDefault(True)
        btn_ok.setStyleSheet("padding: 6px 18px; font-weight: bold; background-color: #2ecc71; color: white;")
        btn_ok.clicked.connect(self.accept)
        h_btn.addWidget(btn_ok)

        layout.addLayout(h_btn)

        if first_focus_widget:
            first_focus_widget.setFocus()

    def get_attributes(self):
        res = {}
        for fname, widget in self.input_widgets.items():
            if isinstance(widget, QComboBox):
                res[fname] = widget.currentText().strip()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                res[fname] = widget.value()
            elif isinstance(widget, QLineEdit):
                res[fname] = widget.text().strip()
        return res


class BambuLabelDockWidget(QDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__("BambuLabel Studio — Etiquetado Rápido", parent)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.linear_poly_tool = None
        self.stream_tool = None
        self.segment_tool = None
        self.eraser_tool = None

        self.custom_attr_inputs = {}

        self.init_ui()
        self.refresh_layers_list()
        self.refresh_raster_list()

        QgsProject.instance().layersAdded.connect(self.refresh_layers_list)
        QgsProject.instance().layersRemoved.connect(self.refresh_layers_list)
        QgsProject.instance().layersAdded.connect(self.refresh_raster_list)
        QgsProject.instance().layersRemoved.connect(self.refresh_raster_list)

    def set_tools(self, linear_poly_tool, stream_tool, segment_tool, eraser_tool):
        self.linear_poly_tool = linear_poly_tool
        self.stream_tool = stream_tool
        self.segment_tool = segment_tool
        self.eraser_tool = eraser_tool

        self.linear_poly_tool.feature_added.connect(self.update_features_table)
        self.linear_poly_tool.point_count_changed.connect(self.on_point_count_changed)

        self.stream_tool.feature_added.connect(self.update_features_table)

        self.segment_tool.feature_added.connect(self.update_features_table)
        self.segment_tool.point_count_changed.connect(self.on_point_count_changed)

        self.eraser_tool.features_modified.connect(self.update_features_table)

    def init_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ==========================================
        # 1. GESTIÓN DE CAPA DE ETIQUETAS
        # ==========================================
        grp_layer = QgsCollapsibleGroupBox("1. Capa de Etiquetas (Vectorial)")
        grp_layer.setCollapsed(True)
        l_lay = QVBoxLayout(grp_layer)

        h_combo = QHBoxLayout()
        self.combo_layers = QComboBox()
        self.combo_layers.currentIndexChanged.connect(self.on_layer_selection_changed)
        h_combo.addWidget(self.combo_layers, 1)

        btn_refresh = QToolButton()
        btn_refresh.setText("🔄")
        btn_refresh.setToolTip("Refrescar capas disponibles")
        btn_refresh.clicked.connect(self.refresh_layers_list)
        h_combo.addWidget(btn_refresh)
        l_lay.addLayout(h_combo)

        h_layer_btns = QHBoxLayout()
        self.btn_new_layer = QPushButton("➕ Nueva Capa (.shp)")
        self.btn_new_layer.setIcon(get_icon("new_layer"))
        self.btn_new_layer.setStyleSheet("font-weight: bold; background-color: #e8f5e9; color: #1b5e20;")
        self.btn_new_layer.clicked.connect(self.create_new_layer_dialog)
        h_layer_btns.addWidget(self.btn_new_layer)

        self.btn_load_layer = QPushButton("📂 Cargar SHP")
        self.btn_load_layer.setIcon(get_icon("import"))
        self.btn_load_layer.clicked.connect(self.load_existing_layer)
        h_layer_btns.addWidget(self.btn_load_layer)
        l_lay.addLayout(h_layer_btns)

        self.chk_editing = QCheckBox("Modo Edición activo (Conmutar lápiz)")
        self.chk_editing.stateChanged.connect(self.toggle_layer_editing)
        l_lay.addWidget(self.chk_editing)

        layout.addWidget(grp_layer)

        # ==========================================
        # 2. HERRAMIENTAS DE DIBUJO Y AUTO-RELLENO
        # ==========================================
        grp_tools = QgsCollapsibleGroupBox("2. Herramientas de Dibujo")
        grp_tools.setCollapsed(False)
        l_tools = QVBoxLayout(grp_tools)

        # Primary drawing modes
        h_modes = QHBoxLayout()

        # Polígono Lineal estilo QGIS (Bordes rectos directos sin círculos)
        self.btn_linear_poly = QPushButton(" Polígono Lineal")
        self.btn_linear_poly.setIcon(get_icon("polygon"))
        self.btn_linear_poly.setCheckable(True)
        self.btn_linear_poly.setChecked(True)
        self.btn_linear_poly.setToolTip("Dibuja bordes lineales precisos clic a clic (Estilo QGIS). Clic derecho o doble clic para terminar.")
        self.btn_linear_poly.setStyleSheet("QPushButton:checked { background-color: #c8e6c9; font-weight: bold; color: #1b5e20; }")
        self.btn_linear_poly.clicked.connect(self.activate_linear_poly)
        h_modes.addWidget(self.btn_linear_poly)

        # Pincel por Flujo
        self.btn_stream = QPushButton(" Pincel Flujo")
        self.btn_stream.setIcon(get_icon("brush"))
        self.btn_stream.setCheckable(True)
        self.btn_stream.setToolTip("Pinta libremente a mano alzada manteniendo presionado el ratón.")
        self.btn_stream.setStyleSheet("QPushButton:checked { background-color: #b2dfdb; font-weight: bold; color: #004d40; }")
        self.btn_stream.clicked.connect(self.activate_stream_brush)
        h_modes.addWidget(self.btn_stream)
        l_tools.addLayout(h_modes)

        h_submodes = QHBoxLayout()
        # Pincel por tramos gruesos
        self.btn_segment = QPushButton(" Tramos Gruesos")
        self.btn_segment.setIcon(get_icon("brush_segment"))
        self.btn_segment.setCheckable(True)
        self.btn_segment.setToolTip("Segmentos punto a punto con grosor de pincel.")
        self.btn_segment.setStyleSheet("QPushButton:checked { background-color: #d1c4e9; font-weight: bold; color: #311b92; }")
        self.btn_segment.clicked.connect(self.activate_segment_brush)
        h_submodes.addWidget(self.btn_segment)

        # Borrador
        self.btn_eraser = QPushButton(" Borrador")
        self.btn_eraser.setIcon(get_icon("eraser"))
        self.btn_eraser.setCheckable(True)
        self.btn_eraser.setStyleSheet("QPushButton:checked { background-color: #f8bbd0; font-weight: bold; color: #880e4f; }")
        self.btn_eraser.clicked.connect(self.activate_eraser)
        h_submodes.addWidget(self.btn_eraser)

        self.btn_pan = QPushButton("✋ Navegar")
        self.btn_pan.clicked.connect(self.activate_pan)
        h_submodes.addWidget(self.btn_pan)
        l_tools.addLayout(h_submodes)

        # Botón para deshacer el último clic del polígono/segmento
        self.btn_undo_point = QPushButton(" ↩️ Deshacer último clic (Ctrl+Z / Backspace)")
        self.btn_undo_point.setIcon(get_icon("undo_point"))
        self.btn_undo_point.setToolTip("Elimina únicamente el último clic colocado durante el trazado.")
        self.btn_undo_point.setEnabled(False)
        self.btn_undo_point.setStyleSheet("color: #e65100; font-weight: bold;")
        self.btn_undo_point.clicked.connect(self.undo_last_point_clicked)
        l_tools.addWidget(self.btn_undo_point)

        # AUTO-RELLENO DE HUECOS (EFECTO DONA / ÁRBOL)
        self.chk_fill_holes = QCheckBox("Rellenar centro automáticamente (Efecto dona / árbol)")
        self.chk_fill_holes.setChecked(True)
        self.chk_fill_holes.setStyleSheet("font-weight: bold; color: #1b5e20;")
        self.chk_fill_holes.setToolTip(
            "Al delinear el contorno cerrado de un árbol o figura con hueco interior,\n"
            "el centro se rellena automáticamente convirtiéndose en un polígono 100% sólido."
        )
        l_tools.addWidget(self.chk_fill_holes)

        # Suavizado de trazo (Anti-tambaleo)
        h_smooth = QHBoxLayout()
        h_smooth.addWidget(QLabel("Suavizado:"))
        self.spin_smooth = QSpinBox()
        self.spin_smooth.setRange(0, 4)
        self.spin_smooth.setValue(1) # Leve por defecto para polígono lineal
        self.spin_smooth.valueChanged.connect(self.on_spin_smooth_changed)
        h_smooth.addWidget(self.spin_smooth)

        self.lbl_smooth_desc = QLabel("Leve (Bordes limpios)")
        self.lbl_smooth_desc.setStyleSheet("color: #1b5e20;")
        h_smooth.addWidget(self.lbl_smooth_desc)
        l_tools.addLayout(h_smooth)

        # Radio de pincel (para modos Flujo y Tramos)
        h_rad = QHBoxLayout()
        h_rad.addWidget(QLabel("Grosor / Radio (m):"))
        self.spin_radius = QDoubleSpinBox()
        self.spin_radius.setRange(0.2, 50.0)
        self.spin_radius.setValue(2.5)
        self.spin_radius.setSingleStep(0.5)
        self.spin_radius.setSuffix(" m")
        self.spin_radius.valueChanged.connect(self.on_spin_radius_changed)
        h_rad.addWidget(self.spin_radius)

        for rad_val in [1.0, 2.5, 5.0]:
            btn_p = QPushButton(f"{rad_val}m")
            btn_p.setMaximumWidth(40)
            btn_p.clicked.connect(lambda ch, r=rad_val: self.set_preset_radius(r))
            h_rad.addWidget(btn_p)

        l_tools.addLayout(h_rad)

        self.chk_merge = QCheckBox("Fusionar automáticamente con polígonos que se toquen")
        self.chk_merge.setChecked(True)
        l_tools.addWidget(self.chk_merge)

        self.chk_confirm_dialog = QCheckBox("Mostrar ventana de atributos al terminar figura")
        self.chk_confirm_dialog.setChecked(True)
        self.chk_confirm_dialog.setStyleSheet("font-weight: bold; color: #0d47a1;")
        self.chk_confirm_dialog.setToolTip(
            "Al completar la figura, abre una ventana emergente para revisar y editar los datos\n"
            "(ID, Imagen, Superficie) antes de guardarla o cancelarla."
        )
        l_tools.addWidget(self.chk_confirm_dialog)

        layout.addWidget(grp_tools)

        # ==========================================
        # 3. ATRIBUTOS DINÁMICOS DE LA CAPA
        # ==========================================
        self.grp_attr = QgsCollapsibleGroupBox("3. Atributos de la Capa Activa")
        self.grp_attr.setCollapsed(True)
        self.layout_attr = QVBoxLayout(self.grp_attr)

        h_img = QHBoxLayout()
        h_img.addWidget(QLabel("Imagen activa:"))
        self.combo_raster = QComboBox()
        self.combo_raster.setEditable(True)
        self.combo_raster.setToolTip("GeoTIFF asignado automáticamente a la columna 'Imagen' (editable o seleccionable)")
        h_img.addWidget(self.combo_raster, 1)
        self.layout_attr.addLayout(h_img)

        self.widget_dynamic_fields = QWidget()
        self.grid_dynamic = QGridLayout(self.widget_dynamic_fields)
        self.grid_dynamic.setContentsMargins(0, 0, 0, 0)
        self.layout_attr.addWidget(self.widget_dynamic_fields)

        layout.addWidget(self.grp_attr)

        # ==========================================
        # 4. HISTORIAL Y GUARDADO
        # ==========================================
        grp_hist = QgsCollapsibleGroupBox("4. Historial y Guardado")
        grp_hist.setCollapsed(True)
        l_hist = QVBoxLayout(grp_hist)

        h_undo = QHBoxLayout()
        self.btn_undo = QPushButton(" Deshacer figura (Ctrl+Z)")
        self.btn_undo.setIcon(get_icon("undo"))
        self.btn_undo.clicked.connect(self.undo_action)
        h_undo.addWidget(self.btn_undo)

        self.btn_redo = QPushButton(" Rehacer (Ctrl+Y)")
        self.btn_redo.setIcon(get_icon("redo"))
        self.btn_redo.clicked.connect(self.redo_action)
        h_undo.addWidget(self.btn_redo)
        l_hist.addLayout(h_undo)

        h_save = QHBoxLayout()
        self.btn_save = QPushButton("💾 Guardar en Disco")
        self.btn_save.setStyleSheet("font-weight: bold;")
        self.btn_save.clicked.connect(self.save_edits)
        h_save.addWidget(self.btn_save)

        self.btn_full_table = QPushButton("📊 Tabla QGIS (F6)")
        self.btn_full_table.setIcon(get_icon("table"))
        self.btn_full_table.clicked.connect(self.open_full_attribute_table)
        h_save.addWidget(self.btn_full_table)
        l_hist.addLayout(h_save)

        layout.addWidget(grp_hist)

        # ==========================================
        # 5. TABLA RESUMEN DE ETIQUETAS
        # ==========================================
        grp_table = QgsCollapsibleGroupBox("5. Etiquetas Creadas (Doble clic para Zoom)")
        grp_table.setCollapsed(False)
        l_table = QVBoxLayout(grp_table)

        self.table_features = QTableWidget(0, 3)
        self.table_features.setHorizontalHeaderLabels(["ID", "Imagen", "Superficie"])
        self.table_features.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_features.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_features.cellDoubleClicked.connect(self.on_table_cell_double_clicked)
        l_table.addWidget(self.table_features)

        self.lbl_summary = QLabel("Total polígonos: 0 | Superficie: 0.00 ha")
        self.lbl_summary.setStyleSheet("font-weight: bold; color: #2e7d32;")
        l_table.addWidget(self.lbl_summary)

        h_tab_acts = QHBoxLayout()
        self.btn_zoom_selected = QPushButton("🔍 Zoom seleccionado")
        self.btn_zoom_selected.setIcon(get_icon("zoom"))
        self.btn_zoom_selected.clicked.connect(self.zoom_to_selected)
        h_tab_acts.addWidget(self.btn_zoom_selected)

        self.btn_delete_selected = QPushButton("🗑️ Eliminar")
        self.btn_delete_selected.setIcon(get_icon("delete"))
        self.btn_delete_selected.clicked.connect(self.delete_selected_feature)
        h_tab_acts.addWidget(self.btn_delete_selected)
        l_table.addLayout(h_tab_acts)

        layout.addWidget(grp_table)

        # ==========================================
        # 6. EXPORTACIÓN
        # ==========================================
        grp_export = QgsCollapsibleGroupBox("6. Exportar Etiquetas")
        grp_export.setCollapsed(True)
        l_exp = QHBoxLayout(grp_export)

        btn_exp_shp = QPushButton("Exportar SHP")
        btn_exp_shp.setIcon(get_icon("export"))
        btn_exp_shp.clicked.connect(lambda: self.export_layer("shp"))
        l_exp.addWidget(btn_exp_shp)

        btn_exp_geojson = QPushButton("Exportar GeoJSON")
        btn_exp_geojson.setIcon(get_icon("export"))
        btn_exp_geojson.clicked.connect(lambda: self.export_layer("geojson"))
        l_exp.addWidget(btn_exp_geojson)

        layout.addWidget(grp_export)

        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(container)
        self.setWidget(scroll)

    # ==========================================
    # LÓGICA DE HERRAMIENTAS
    # ==========================================
    def on_point_count_changed(self, count):
        self.btn_undo_point.setEnabled(count > 0)
        if count > 0:
            self.btn_undo_point.setText(f" ↩️ Deshacer clic (Puntos actuales: {count})")
        else:
            self.btn_undo_point.setText(" ↩️ Deshacer último clic (Ctrl+Z / Backspace)")

    def undo_last_point_clicked(self):
        curr_tool = self.canvas.mapTool()
        if hasattr(curr_tool, "undo_last_point"):
            curr_tool.undo_last_point()

    def activate_linear_poly(self):
        layer = self.get_active_layer()
        if not layer:
            QMessageBox.warning(self, "Atención", "Seleccione o cree una capa de etiquetas antes de dibujar.")
            self.btn_linear_poly.setChecked(False)
            return

        self.btn_linear_poly.setChecked(True)
        self.btn_stream.setChecked(False)
        self.btn_segment.setChecked(False)
        self.btn_eraser.setChecked(False)
        if self.linear_poly_tool:
            self.canvas.setMapTool(self.linear_poly_tool)

    def activate_stream_brush(self):
        layer = self.get_active_layer()
        if not layer:
            QMessageBox.warning(self, "Atención", "Seleccione o cree una capa de etiquetas antes de dibujar.")
            self.btn_stream.setChecked(False)
            return

        self.btn_stream.setChecked(True)
        self.btn_linear_poly.setChecked(False)
        self.btn_segment.setChecked(False)
        self.btn_eraser.setChecked(False)
        if self.stream_tool:
            self.canvas.setMapTool(self.stream_tool)

    def activate_segment_brush(self):
        layer = self.get_active_layer()
        if not layer:
            QMessageBox.warning(self, "Atención", "Seleccione o cree una capa de etiquetas antes de dibujar.")
            self.btn_segment.setChecked(False)
            return

        self.btn_segment.setChecked(True)
        self.btn_linear_poly.setChecked(False)
        self.btn_stream.setChecked(False)
        self.btn_eraser.setChecked(False)
        if self.segment_tool:
            self.canvas.setMapTool(self.segment_tool)

    def activate_eraser(self):
        layer = self.get_active_layer()
        if not layer:
            QMessageBox.warning(self, "Atención", "Seleccione una capa de etiquetas antes de usar el borrador.")
            self.btn_eraser.setChecked(False)
            return

        self.btn_eraser.setChecked(True)
        self.btn_linear_poly.setChecked(False)
        self.btn_stream.setChecked(False)
        self.btn_segment.setChecked(False)
        if self.eraser_tool:
            self.canvas.setMapTool(self.eraser_tool)

    def activate_pan(self):
        self.btn_linear_poly.setChecked(False)
        self.btn_stream.setChecked(False)
        self.btn_segment.setChecked(False)
        self.btn_eraser.setChecked(False)
        self.iface.actionPan().trigger()

    def is_fill_holes_enabled(self):
        return self.chk_fill_holes.isChecked()

    def get_brush_radius(self):
        return self.spin_radius.value()

    def on_spin_radius_changed(self, val):
        pass

    def set_preset_radius(self, r):
        self.spin_radius.setValue(r)

    def get_smooth_level(self):
        return self.spin_smooth.value()

    def on_spin_smooth_changed(self, val):
        labels = {
            0: "Sin filtro (Lineal estricto)",
            1: "Leve (Bordes limpios)",
            2: "Medio (Suave)",
            3: "Alto (Curvas orgánicas)",
            4: "Ultrasuave"
        }
        self.lbl_smooth_desc.setText(labels.get(val, "Leve"))

    def is_merge_enabled(self):
        return self.chk_merge.isChecked()

    # ==========================================
    # LÓGICA DE CAPAS Y PROYECTO
    # ==========================================
    def refresh_layers_list(self):
        current_id = self.get_active_layer().id() if self.get_active_layer() else None
        self.combo_layers.blockSignals(True)
        self.combo_layers.clear()

        polygon_layers = []
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer) and lyr.geometryType() == QgsWkbTypes.PolygonGeometry:
                polygon_layers.append(lyr)
                self.combo_layers.addItem(lyr.name(), lyr.id())

        if current_id:
            idx = self.combo_layers.findData(current_id)
            if idx != -1:
                self.combo_layers.setCurrentIndex(idx)
        elif polygon_layers:
            self.combo_layers.setCurrentIndex(0)

        self.combo_layers.blockSignals(False)
        self.on_layer_selection_changed()

    def get_available_raster_names(self):
        rasters = []
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsRasterLayer):
                rasters.append(lyr.name())
        return sorted(rasters)

    def refresh_raster_list(self):
        self.combo_raster.blockSignals(True)
        current_text = self.combo_raster.currentText()
        self.combo_raster.clear()

        rasters = self.get_available_raster_names()
        for rname in rasters:
            self.combo_raster.addItem(rname)

        if current_text:
            idx = self.combo_raster.findText(current_text)
            if idx != -1:
                self.combo_raster.setCurrentIndex(idx)
            else:
                self.combo_raster.setEditText(current_text)

        self.combo_raster.blockSignals(False)

    def set_active_image_name(self, img_name):
        if not img_name:
            return
        idx = self.combo_raster.findText(img_name)
        if idx != -1:
            self.combo_raster.setCurrentIndex(idx)
        else:
            self.combo_raster.addItem(img_name)
            self.combo_raster.setCurrentIndex(self.combo_raster.count() - 1)

    def get_active_layer(self):
        lyr_id = self.combo_layers.currentData()
        if lyr_id:
            return QgsProject.instance().mapLayer(lyr_id)
        return None

    def on_layer_selection_changed(self):
        layer = self.get_active_layer()
        if layer:
            self.chk_editing.blockSignals(True)
            self.chk_editing.setChecked(layer.isEditable())
            self.chk_editing.blockSignals(False)
            self.rebuild_dynamic_attribute_inputs(layer)
            self.update_features_table()

    def rebuild_dynamic_attribute_inputs(self, layer):
        for i in reversed(range(self.grid_dynamic.count())):
            item = self.grid_dynamic.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        self.custom_attr_inputs = {}
        fields = [f.name() for f in layer.fields()]

        row = 0
        for fname in fields:
            fname_lower = fname.lower()
            if fname_lower in ("id", "superficie", "area", "area_m2", "area_ha"):
                continue
            if fname_lower in ("imagen", "image"):
                continue

            lbl = QLabel(f"{fname}:")
            inp = QLineEdit()
            self.grid_dynamic.addWidget(lbl, row, 0)
            self.grid_dynamic.addWidget(inp, row, 1)
            self.custom_attr_inputs[fname] = inp
            row += 1

    def toggle_layer_editing(self, state):
        layer = self.get_active_layer()
        if not layer:
            return
        if state == Qt.Checked:
            if not layer.isEditable():
                layer.startEditing()
        else:
            if layer.isEditable():
                res = QMessageBox.question(
                    self,
                    "Guardar Cambios",
                    "¿Desea guardar los cambios realizados en la capa de etiquetas antes de cerrar edición?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                if res == QMessageBox.Save:
                    layer.commitChanges()
                elif res == QMessageBox.Discard:
                    layer.rollBack()
                else:
                    self.chk_editing.setChecked(True)
        self.chk_editing.setChecked(layer.isEditable())

    def create_new_layer_dialog(self):
        default_dir = r"D:\TRABAJO_BAMBU\BAMBUTECH_INFORME_1\06_ETIQUETAS"
        if not os.path.exists(default_dir):
            default_dir = QgsProject.instance().homePath() or os.path.expanduser("~")

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        suggested_path = os.path.join(default_dir, f"etiquetas_bambu_{timestamp}.shp")

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Crear Nueva Capa de Etiquetas Shapefile",
            suggested_path,
            "ESRI Shapefile (*.shp);;GeoPackage (*.gpkg)"
        )
        if not path:
            return

        crs_32718 = QgsCoordinateReferenceSystem("EPSG:32718")

        # Standard user schema: id, Imagen, Superficie
        fields = QgsFields()
        fields.append(QgsField("id", QVariant.Int))
        fields.append(QgsField("Imagen", QVariant.String, len=100))
        fields.append(QgsField("Superficie", QVariant.Double, prec=2))

        driver_name = "GPKG" if path.lower().endswith(".gpkg") else "ESRI Shapefile"
        writer = QgsVectorFileWriter(
            path,
            "UTF-8",
            fields,
            QgsWkbTypes.Polygon,
            crs_32718,
            driver_name
        )
        if writer.hasError() != QgsVectorFileWriter.NoError:
            QMessageBox.critical(self, "Error al crear capa", f"No se pudo crear el archivo:\n{writer.errorMessage()}")
            return
        del writer

        layer_name = os.path.splitext(os.path.basename(path))[0]
        vlayer = QgsVectorLayer(path, layer_name, "ogr")
        if not vlayer.isValid():
            QMessageBox.critical(self, "Error", "No se pudo cargar la capa recién creada.")
            return

        sym = QgsFillSymbol.createSimple({
            "color": "46,204,113,85",
            "outline_color": "39,174,96,255",
            "outline_width": "0.6",
            "outline_width_unit": "MM"
        })
        vlayer.setRenderer(QgsSingleSymbolRenderer(sym))

        QgsProject.instance().addMapLayer(vlayer)
        vlayer.startEditing()
        self.refresh_layers_list()

        idx = self.combo_layers.findData(vlayer.id())
        if idx != -1:
            self.combo_layers.setCurrentIndex(idx)

        QMessageBox.information(
            self,
            "Capa Creada con Éxito",
            f"Se creó la capa con campos estándar [id, Imagen, Superficie]:\n{path}"
        )

    def load_existing_layer(self):
        default_dir = r"D:\TRABAJO_BAMBU\BAMBUTECH_INFORME_1\06_ETIQUETAS"
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Cargar Capa de Etiquetas",
            default_dir,
            "Vectores (*.shp *.geojson *.gpkg *.json);;Todos los archivos (*.*)"
        )
        if not path:
            return

        layer_name = os.path.splitext(os.path.basename(path))[0]
        vlayer = QgsVectorLayer(path, layer_name, "ogr")
        if vlayer.isValid():
            QgsProject.instance().addMapLayer(vlayer)
            self.refresh_layers_list()
            idx = self.combo_layers.findData(vlayer.id())
            if idx != -1:
                self.combo_layers.setCurrentIndex(idx)
        else:
            QMessageBox.critical(self, "Error", "No se pudo abrir el archivo seleccionado.")

    def get_active_image_name(self):
        txt = self.combo_raster.currentText().strip()
        if txt:
            return txt
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsRasterLayer):
                return lyr.name()
        return "Desconocida"

    def get_new_feature_attributes(self, geom):
        layer = self.get_active_layer()
        if not layer:
            return {}

        fields = [f.name() for f in layer.fields()]
        attrs = {}

        # 1. ID
        id_field_name = None
        for fn in fields:
            if fn.lower() == "id":
                id_field_name = fn
                break

        if id_field_name:
            existing_ids = [feat[id_field_name] for feat in layer.getFeatures() if feat[id_field_name] is not None and str(feat[id_field_name]).isdigit()]
            max_id = max(existing_ids) if existing_ids else 0
            attrs[id_field_name] = max_id + 1

        # 2. Imagen
        img_val = self.get_active_image_name()
        for fn in fields:
            if fn.lower() in ("imagen", "image"):
                attrs[fn] = img_val
                break

        # 3. Superficie
        area_m2 = round(geom.area(), 2)
        for fn in fields:
            fn_l = fn.lower()
            if fn_l in ("superficie", "area", "area_m2"):
                attrs[fn] = area_m2
                break
            elif fn_l == "area_ha":
                attrs[fn] = round(area_m2 / 10000.0, 4)

        # 4. Custom fields
        for fn, inp in self.custom_attr_inputs.items():
            if fn in fields and inp.text().strip():
                attrs[fn] = inp.text().strip()

        return attrs

    def is_confirm_dialog_enabled(self):
        return self.chk_confirm_dialog.isChecked()

    def confirm_and_get_attributes(self, geom, is_merge=False):
        """
        Si la confirmación está activa, abre la ventana emergente BambuConfirmLabelDialog.
        Permite al usuario verificar o editar Imagen, ID, Superficie y dar Aceptar o Cancelar.
        Retorna: (accepted: bool, attr_dict: dict)
        """
        layer = self.get_active_layer()
        if not layer:
            return False, {}

        default_attrs = self.get_new_feature_attributes(geom)

        if not self.is_confirm_dialog_enabled():
            return True, default_attrs

        raster_names = self.get_available_raster_names()
        dlg = BambuConfirmLabelDialog(self, layer, geom, default_attrs, raster_names, is_merge=is_merge)
        if dlg.exec_() == QDialog.Accepted:
            confirmed_attrs = dlg.get_attributes()
            # Actualizar el nombre de imagen activo en el panel si el usuario lo cambió
            for fn in confirmed_attrs:
                if fn.lower() in ("imagen", "image"):
                    self.set_active_image_name(confirmed_attrs[fn])
                    break
            return True, confirmed_attrs
        else:
            return False, {}

    def update_feature_attributes_after_edit(self, layer, fid, geom):
        fields = layer.fields()
        area_m2 = round(geom.area(), 2)

        for fn in [f.name() for f in fields]:
            fn_l = fn.lower()
            idx = fields.indexOf(fn)
            if fn_l in ("superficie", "area", "area_m2"):
                layer.changeAttributeValue(fid, idx, area_m2)
            elif fn_l == "area_ha":
                layer.changeAttributeValue(fid, idx, round(area_m2 / 10000.0, 4))
            elif fn_l in ("imagen", "image"):
                img_val = self.get_active_image_name()
                layer.changeAttributeValue(fid, idx, img_val)

    # ==========================================
    # DESHACER / REHACER / GUARDAR
    # ==========================================
    def undo_action(self):
        layer = self.get_active_layer()
        if layer and layer.isEditable():
            layer.undoStack().undo()
            self.update_features_table()

    def redo_action(self):
        layer = self.get_active_layer()
        if layer and layer.isEditable():
            layer.undoStack().redo()
            self.update_features_table()

    def save_edits(self):
        layer = self.get_active_layer()
        if layer and layer.isEditable():
            if layer.commitChanges():
                layer.startEditing()
                self.chk_editing.setChecked(True)
                QMessageBox.information(self, "Guardado", "Cambios guardados exitosamente en el archivo.")
            else:
                QMessageBox.critical(self, "Error", f"No se pudieron guardar los cambios:\n{layer.commitErrors()}")

    def open_full_attribute_table(self):
        layer = self.get_active_layer()
        if layer:
            self.iface.showAttributeTable(layer)

    # ==========================================
    # TABLA RESUMEN EN EL PANEL (DINÁMICA)
    # ==========================================
    def update_features_table(self):
        layer = self.get_active_layer()
        if not layer:
            self.table_features.setRowCount(0)
            self.lbl_summary.setText("Sin capa seleccionada")
            return

        features = list(layer.getFeatures())
        field_names = [f.name() for f in layer.fields()]

        display_fields = []
        for pref in ["id", "Id", "ID", "Imagen", "imagen", "Superficie", "superficie", "area", "Area"]:
            if pref in field_names and pref not in display_fields:
                display_fields.append(pref)

        for fn in field_names:
            if fn not in display_fields and len(display_fields) < 4:
                display_fields.append(fn)

        if not display_fields:
            display_fields = ["ID", "Superficie"]

        self.table_features.setColumnCount(len(display_fields))
        self.table_features.setHorizontalHeaderLabels(display_fields)
        self.table_features.setRowCount(len(features))

        total_area_m2 = 0.0

        for row, feat in enumerate(features):
            geom = feat.geometry()
            area_m2 = geom.area() if geom else 0.0
            total_area_m2 += area_m2

            for col_idx, col_name in enumerate(display_fields):
                f_idx = layer.fields().indexOf(col_name)
                val_str = ""
                if f_idx != -1:
                    val = feat.attributes()[f_idx]
                    if isinstance(val, float):
                        val_str = f"{val:.2f}"
                    else:
                        val_str = str(val if val is not None else "")
                elif col_name in ("Área", "Superficie"):
                    val_str = f"{area_m2:.1f}"

                item = QTableWidgetItem(val_str)
                if col_idx == 0:
                    item.setData(Qt.UserRole, feat.id())
                self.table_features.setItem(row, col_idx, item)

        total_ha = total_area_m2 / 10000.0
        self.lbl_summary.setText(f"Total polígonos: {len(features)} | Superficie: {total_ha:.3f} ha ({total_area_m2:.1f} m²)")

    def on_table_cell_double_clicked(self, row, col):
        self.zoom_to_selected()

    def zoom_to_selected(self):
        layer = self.get_active_layer()
        if not layer:
            return

        row = self.table_features.currentRow()
        if row == -1:
            return

        item = self.table_features.item(row, 0)
        if not item:
            return

        fid = item.data(Qt.UserRole)
        feat = layer.getFeature(fid)
        if feat and feat.geometry():
            box = feat.geometry().boundingBox()
            box.grow(10.0)
            self.canvas.setExtent(box)
            self.canvas.refresh()
            layer.selectByIds([fid])

    def delete_selected_feature(self):
        layer = self.get_active_layer()
        if not layer or not layer.isEditable():
            QMessageBox.warning(self, "Atención", "Active el modo edición antes de eliminar.")
            return

        row = self.table_features.currentRow()
        if row == -1:
            return

        item = self.table_features.item(row, 0)
        fid = item.data(Qt.UserRole)

        layer.beginEditCommand("Eliminar etiqueta")
        layer.deleteFeature(fid)
        layer.endEditCommand()
        layer.triggerRepaint()
        self.canvas.refresh()
        self.update_features_table()

    # ==========================================
    # EXPORTACIÓN
    # ==========================================
    def export_layer(self, fmt):
        layer = self.get_active_layer()
        if not layer:
            QMessageBox.warning(self, "Atención", "No hay capa de etiquetas activa para exportar.")
            return

        default_dir = r"D:\TRABAJO_BAMBU\BAMBUTECH_INFORME_1\06_ETIQUETAS"
        if fmt == "shp":
            filter_str = "ESRI Shapefile (*.shp)"
            ext = ".shp"
            driver = "ESRI Shapefile"
        else:
            filter_str = "GeoJSON (*.geojson *.json)"
            ext = ".geojson"
            driver = "GeoJSON"

        suggested = os.path.join(default_dir, f"{layer.name()}_export{ext}")
        path, _ = QFileDialog.getSaveFileName(self, f"Exportar Capa a {driver}", suggested, filter_str)
        if not path:
            return

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = driver
        options.fileEncoding = "UTF-8"
        options.ct = None

        err, msg = QgsVectorFileWriter.writeAsVectorFormatV2(layer, path, QgsProject.instance().transformContext(), options)
        if err == QgsVectorFileWriter.NoError:
            QMessageBox.information(self, "Exportación Exitosa", f"Capa exportada correctamente a:\n{path}")
        else:
            QMessageBox.critical(self, "Error en Exportación", f"No se pudo exportar:\n{msg}")

    def show_message(self, text):
        self.iface.messageBar().pushMessage("BambuLabel", text, level=1, duration=4)
