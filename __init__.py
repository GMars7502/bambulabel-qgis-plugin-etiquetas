# -*- coding: utf-8 -*-
"""
BambuLabel - Plugin QGIS para Etiquetado de Bambú con Pincel
"""

def classFactory(iface):
    from .bambu_label_plugin import BambuLabelPlugin
    return BambuLabelPlugin(iface)
