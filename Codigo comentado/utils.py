# -----------------------------------------------------------------------------
# PROPRIETARY AND CONFIDENTIAL
# Copyright (c) 2024. All Rights Reserved.
#
# This file is part of the AS726X Spectrophotometer Suite.
# Unauthorized use, copying, or distribution is strictly prohibited.
# Requires express written authorization from:
# 1. The Author / Lead Developer
# 2. Universidad de los Andes
# 3. The Biomicrosystems Research Group
# -----------------------------------------------------------------------------
# -*- coding: utf-8 -*-
"""
Proporciona clases de utilidad reutilizables para la interfaz grÃ¡fica.

Clases:
- PlotWidget: Encapsula una figura de Matplotlib para su fÃ¡cil integraciÃ³n en PyQt.
- CollapsibleGroupBox: Un QGroupBox que se puede expandir o contraer.
"""
from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget, QMessageBox
)
from PyQt5.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.legend import Legend
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

class PlotWidget(QWidget):
    """Un widget personalizado para mostrar grÃ¡ficos de Matplotlib en una app PyQt."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """Inicializa la figura, el lienzo y la barra de herramientas de Matplotlib."""
        super().__init__(parent)
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

    def apply_theme(self, theme_colors: dict):
        """Aplica una paleta de colores (clara u oscura) al grÃ¡fico."""
        self.ax.set_facecolor(theme_colors['bg_color'])
        self.figure.patch.set_facecolor(theme_colors['fig_bg_color'])
        self.ax.tick_params(axis='x', colors=theme_colors['text_color'], which='both')
        self.ax.tick_params(axis='y', colors=theme_colors['text_color'], which='both')
        for label_obj in [self.ax.xaxis.label, self.ax.yaxis.label, self.ax.title]:
            label_obj.set_color(theme_colors['text_color'])
        self.ax.grid(True, linestyle=':', linewidth=0.7, color=theme_colors['grid_color'], alpha=0.7)
        self.style_legend(theme_colors)
        
        self.figure.subplots_adjust(left=0.07, bottom=0.09, right=0.99, top=0.97)
        
        self.canvas.draw_idle()

    def style_legend(self, theme_colors: dict):
        """Aplica el estilo del tema a la leyenda del grÃ¡fico."""
        legend = self.ax.get_legend()
        if legend:
            legend.get_frame().set_facecolor(theme_colors.get('bg_color', '#FFFFFF'))
            legend.get_frame().set_edgecolor(theme_colors.get('grid_color', '#DCDCDC'))
            for text in legend.get_texts():
                text.set_color(theme_colors.get('text_color', '#000000'))

    def clear(self):
        """Limpia el contenido (ejes, lÃ­neas) del grÃ¡fico."""
        self.ax.clear()

    def draw(self):
        """Redibuja el lienzo del grÃ¡fico para reflejar los cambios."""
        self.canvas.draw_idle()

class CollapsibleGroupBox(QGroupBox):
    """Un QGroupBox con un botÃ³n para mostrar/ocultar su contenido."""
    def __init__(self, title, help_key, parent_app=None, initial_state=True, parent=None):
        """Inicializa el GroupBox y sus controles para colapsar y de ayuda."""
        super().__init__(title, parent)
        self.parent_app = parent_app
        self.help_key = help_key
        
        self.content_widget = QWidget()

        self.toggle_button = QPushButton("â–¼" if initial_state else "â–¶")
        self.toggle_button.setFixedSize(22, 22)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(initial_state)
        self.toggle_button.setStyleSheet("QPushButton { border: none; background-color: transparent; }")
        self.toggle_button.clicked.connect(self._toggle_content)

        self.help_button = QPushButton("?")
        if self.parent_app and hasattr(self.parent_app, '_show_context_help'):
             self.help_button.clicked.connect(lambda: self.parent_app._show_context_help(self.help_key))
        else:
             self.help_button.clicked.connect(lambda: QMessageBox.information(self, "Ayuda no disponible", "La ayuda contextual no estÃ¡ conectada."))

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 4, 0)
        header_layout.setSpacing(5)
        header_layout.addStretch()
        header_layout.addWidget(self.toggle_button)
        header_layout.addWidget(self.help_button)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 3, 6, 6)
        main_layout.setSpacing(4)
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.content_widget)
        
        self.content_widget.setVisible(initial_state)

    def _toggle_content(self):
        """Muestra u oculta el widget de contenido y actualiza el icono del botÃ³n."""
        is_visible = not self.content_widget.isVisible()
        self.content_widget.setVisible(is_visible)
        self.toggle_button.setText("â–¼" if is_visible else "â–¶")
        self.setMinimumHeight(0)
        self.adjustSize()
