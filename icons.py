# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QIcon, QPolygonF, QFont
from qgis.PyQt.QtCore import Qt, QPointF, QRectF

def create_icon_pixmap(name, size=32):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    if name == "brush":
        # Freehand streaming brush
        p.setPen(QPen(QColor(27, 94, 32), 2))
        p.setBrush(QBrush(QColor(76, 175, 80)))
        p.drawEllipse(6, 12, 14, 14)
        p.setPen(QPen(QColor(121, 85, 72), 3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(16, 16, 28, 4)

    elif name == "polygon":
        # Linear polygon tool (QGIS style straight line boundaries)
        p.setPen(QPen(QColor(46, 125, 50), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(QBrush(QColor(165, 214, 167, 180)))
        poly = QPolygonF([QPointF(6, 22), QPointF(10, 8), QPointF(24, 6), QPointF(26, 20), QPointF(16, 26)])
        p.drawPolygon(poly)
        p.setBrush(QBrush(QColor(27, 94, 32)))
        for pt in [QPointF(6, 22), QPointF(10, 8), QPointF(24, 6), QPointF(26, 20), QPointF(16, 26)]:
            p.drawEllipse(pt, 2, 2)

    elif name == "brush_segment":
        # Segment brush with thickness
        p.setPen(QPen(QColor(46, 125, 50), 2.5, Qt.DashLine, Qt.RoundCap))
        p.drawLine(6, 24, 16, 10)
        p.drawLine(16, 10, 26, 16)
        p.setPen(QPen(QColor(27, 94, 32), 1.5))
        p.setBrush(QBrush(QColor(129, 199, 132)))
        p.drawEllipse(4, 22, 5, 5)
        p.drawEllipse(14, 8, 5, 5)
        p.drawEllipse(24, 14, 5, 5)

    elif name == "eraser":
        p.setPen(QPen(QColor(60, 60, 60), 1.5))
        p.setBrush(QBrush(QColor(240, 98, 146)))
        poly = QPolygonF([QPointF(6, 20), QPointF(16, 6), QPointF(26, 13), QPointF(16, 27)])
        p.drawPolygon(poly)
        p.setBrush(QBrush(QColor(255, 255, 255)))
        poly_white = QPolygonF([QPointF(6, 20), QPointF(11, 13), QPointF(21, 20), QPointF(16, 27)])
        p.drawPolygon(poly_white)

    elif name == "undo":
        p.setPen(QPen(QColor(25, 118, 210), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawArc(6, 10, 20, 16, 0, 180 * 16)
        p.drawLine(6, 18, 6, 10)
        p.drawLine(6, 10, 14, 10)

    elif name == "redo":
        p.setPen(QPen(QColor(25, 118, 210), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawArc(6, 10, 20, 16, 0, -180 * 16)
        p.drawLine(26, 18, 26, 10)
        p.drawLine(26, 10, 18, 10)

    elif name == "undo_point":
        # Undo single vertex point
        p.setPen(QPen(QColor(230, 81, 0), 2, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(8, 10, 16, 14, 0, 180 * 16)
        p.drawLine(8, 17, 8, 10)
        p.drawLine(8, 10, 14, 10)
        p.setBrush(QBrush(QColor(230, 81, 0)))
        p.drawEllipse(19, 18, 3, 3)

    elif name == "fill_hole":
        # Donut to solid fill icon
        p.setPen(QPen(QColor(56, 142, 60), 2))
        p.setBrush(QBrush(QColor(200, 230, 201)))
        p.drawEllipse(4, 4, 24, 24)
        p.setBrush(QBrush(QColor(76, 175, 80)))
        p.drawEllipse(10, 10, 12, 12)

    elif name == "table":
        p.setPen(QPen(QColor(40, 40, 40), 1.5))
        p.setBrush(QBrush(QColor(245, 245, 245)))
        p.drawRect(4, 5, 24, 22)
        p.setBrush(QBrush(QColor(56, 142, 60)))
        p.drawRect(4, 5, 24, 6)
        p.drawLine(4, 16, 28, 16)
        p.drawLine(4, 22, 28, 22)
        p.drawLine(12, 11, 12, 27)
        p.drawLine(20, 11, 20, 27)

    elif name == "new_layer":
        p.setPen(QPen(QColor(46, 125, 50), 1.5))
        p.setBrush(QBrush(QColor(200, 230, 201)))
        poly = QPolygonF([QPointF(4, 18), QPointF(14, 6), QPointF(26, 10), QPointF(22, 26), QPointF(8, 24)])
        p.drawPolygon(poly)
        p.setPen(QPen(QColor(27, 94, 32), 3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(22, 16, 22, 26)
        p.drawLine(17, 21, 27, 21)

    elif name == "export":
        p.setPen(QPen(QColor(67, 160, 71), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(16, 22, 16, 6)
        p.drawLine(10, 12, 16, 6)
        p.drawLine(22, 12, 16, 6)
        p.setPen(QPen(QColor(80, 80, 80), 2))
        p.drawLine(6, 24, 6, 28)
        p.drawLine(6, 28, 26, 28)
        p.drawLine(26, 28, 26, 24)

    elif name == "import":
        p.setPen(QPen(QColor(30, 136, 229), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(16, 6, 16, 22)
        p.drawLine(10, 16, 16, 22)
        p.drawLine(22, 16, 16, 22)
        p.setPen(QPen(QColor(80, 80, 80), 2))
        p.drawLine(6, 24, 6, 28)
        p.drawLine(6, 28, 26, 28)
        p.drawLine(26, 28, 26, 24)

    elif name == "zoom":
        p.setPen(QPen(QColor(50, 50, 50), 2))
        p.setBrush(QBrush(QColor(227, 242, 253)))
        p.drawEllipse(6, 6, 14, 14)
        p.setPen(QPen(QColor(50, 50, 50), 3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(17, 17, 26, 26)

    elif name == "delete":
        p.setPen(QPen(QColor(211, 47, 47), 2.5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(8, 8, 24, 24)
        p.drawLine(24, 8, 8, 24)

    elif name == "logo":
        p.setPen(QPen(QColor(27, 94, 32), 1.5))
        p.setBrush(QBrush(QColor(76, 175, 80)))
        p.drawRoundedRect(10, 4, 12, 24, 3, 3)
        p.setPen(QPen(QColor(27, 94, 32), 2))
        p.drawLine(10, 12, 22, 12)
        p.drawLine(10, 20, 22, 20)
        p.setBrush(QBrush(QColor(129, 199, 132)))
        poly_leaf = QPolygonF([QPointF(22, 12), QPointF(30, 8), QPointF(26, 15)])
        p.drawPolygon(poly_leaf)
        poly_leaf2 = QPolygonF([QPointF(10, 20), QPointF(2, 16), QPointF(6, 23)])
        p.drawPolygon(poly_leaf2)

    p.end()
    return pm

def get_icon(name):
    return QIcon(create_icon_pixmap(name))
