# -*- coding: utf-8 -*-
"""
Clase Principal del Plugin BambuLabel Studio para QGIS
Versión 1.2: Soporte para Polígono Lineal Directo, Pincel por Flujo, Pincel por Tramos,
Borrador inteligente, Auto-relleno de Huecos Interiores y Deshacer Clic a Clic.
"""
import os
from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject

from .icons import get_icon
from .brush_tool import (
    BambuLinearPolygonTool,
    BambuStreamingBrushTool,
    BambuSegmentBrushTool,
    BambuEraserTool
)
from .bambu_label_dock import BambuLabelDockWidget

class BambuLabelPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.dock = None
        self.toolbar = None
        self.actions = []
        self.linear_poly_tool = None
        self.stream_tool = None
        self.segment_tool = None
        self.eraser_tool = None

    def initGui(self):
        # 1. Crear el Panel Dock
        self.dock = BambuLabelDockWidget(self.iface)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)

        # 2. Crear las herramientas interactivas
        self.linear_poly_tool = BambuLinearPolygonTool(self.canvas, self.dock)
        self.stream_tool = BambuStreamingBrushTool(self.canvas, self.dock)
        self.segment_tool = BambuSegmentBrushTool(self.canvas, self.dock)
        self.eraser_tool = BambuEraserTool(self.canvas, self.dock)
        self.dock.set_tools(self.linear_poly_tool, self.stream_tool, self.segment_tool, self.eraser_tool)

        # 3. Crear la Barra de Herramientas
        self.toolbar = self.iface.addToolBar("BambuLabel — Etiquetado de Bambú")
        self.toolbar.setObjectName("BambuLabelToolBar")

        # Acción: Abrir/Cerrar Panel
        act_toggle = QAction(get_icon("logo"), "Panel BambuLabel", self.iface.mainWindow())
        act_toggle.setCheckable(True)
        act_toggle.setChecked(True)
        act_toggle.triggered.connect(self.toggle_dock)
        self.toolbar.addAction(act_toggle)
        self.iface.addPluginToMenu("&BambuLabel", act_toggle)
        self.actions.append(act_toggle)

        self.toolbar.addSeparator()

        # Acción: Polígono Lineal Directo (Estilo QGIS)
        act_linear = QAction(get_icon("polygon"), "Polígono Lineal (Estilo QGIS)", self.iface.mainWindow())
        act_linear.setCheckable(True)
        act_linear.setChecked(True)
        act_linear.triggered.connect(self.dock.activate_linear_poly)
        self.toolbar.addAction(act_linear)
        self.actions.append(act_linear)

        # Acción: Pincel por Flujo
        act_stream = QAction(get_icon("brush"), "Pincel por Flujo (Arrastre continuo)", self.iface.mainWindow())
        act_stream.setCheckable(True)
        act_stream.triggered.connect(self.dock.activate_stream_brush)
        self.toolbar.addAction(act_stream)
        self.actions.append(act_stream)

        # Acción: Pincel por Tramos Gruesos
        act_segment = QAction(get_icon("brush_segment"), "Tramos Gruesos (Punto a punto)", self.iface.mainWindow())
        act_segment.setCheckable(True)
        act_segment.triggered.connect(self.dock.activate_segment_brush)
        self.toolbar.addAction(act_segment)
        self.actions.append(act_segment)

        # Acción: Borrador
        act_eraser = QAction(get_icon("eraser"), "Borrador de Etiquetas", self.iface.mainWindow())
        act_eraser.setCheckable(True)
        act_eraser.triggered.connect(self.dock.activate_eraser)
        self.toolbar.addAction(act_eraser)
        self.actions.append(act_eraser)

        self.toolbar.addSeparator()

        # Acción: Deshacer último clic (Backspace)
        act_undo_pt = QAction(get_icon("undo_point"), "Deshacer último clic (Backspace / Ctrl+Z)", self.iface.mainWindow())
        act_undo_pt.triggered.connect(self.dock.undo_last_point_clicked)
        self.toolbar.addAction(act_undo_pt)
        self.actions.append(act_undo_pt)

        # Acción: Deshacer etiqueta completada (Ctrl+Z)
        act_undo = QAction(get_icon("undo"), "Deshacer etiqueta (Ctrl+Z)", self.iface.mainWindow())
        act_undo.triggered.connect(self.dock.undo_action)
        self.toolbar.addAction(act_undo)
        self.actions.append(act_undo)

        # Acción: Rehacer (Ctrl+Y)
        act_redo = QAction(get_icon("redo"), "Rehacer (Ctrl+Y)", self.iface.mainWindow())
        act_redo.triggered.connect(self.dock.redo_action)
        self.toolbar.addAction(act_redo)
        self.actions.append(act_redo)

        self.toolbar.addSeparator()

        # Acción: Tabla de Atributos
        act_table = QAction(get_icon("table"), "Abrir Tabla de Atributos (F6)", self.iface.mainWindow())
        act_table.triggered.connect(self.dock.open_full_attribute_table)
        self.toolbar.addAction(act_table)
        self.actions.append(act_table)

    def toggle_dock(self, checked):
        if self.dock:
            self.dock.setVisible(checked)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu("&BambuLabel", action)
            self.iface.removeToolBarIcon(action)

        if self.toolbar:
            del self.toolbar

        if self.dock:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
