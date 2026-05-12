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
Define la clase 'BasePanel', una clase base abstracta para los paneles (pestaÃ±as)
de la UI. Proporciona una estructura y funcionalidad comunes, como la disposiciÃ³n
de dos columnas y seÃ±ales estÃ¡ndar para la comunicaciÃ³n.
"""
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QApplication, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal

from constants import DARK_PLOT_COLORS, LIGHT_PLOT_COLORS

class BasePanel(QWidget):
    """
    Clase base para todos los paneles de pestaÃ±as, asegurando una estructura
    y comportamiento consistentes.
    """
    # SeÃ±ales para comunicarse con la ventana principal (main.py)
    logMessage = pyqtSignal(str, bool, bool)
    requestMeasurement = pyqtSignal(str, int, str)

    def __init__(self, parent_app=None):
        """Inicializa el panel base, configura la UI y detecta el tema."""
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.is_dark_theme = True

        # Intenta determinar el tema actual de la aplicaciÃ³n
        if self.parent_app and hasattr(self.parent_app, 'current_theme_is_dark'):
            self.is_dark_theme = self.parent_app.current_theme_is_dark
        else:
            try:
                app_style = QApplication.instance().styleSheet()
                if app_style:
                    self.is_dark_theme = "background-color: #2b2b2b" in app_style or \
                                         "background-color:#2b2b2b" in app_style
            except Exception:
                pass

        self._setup_base_ui()
        self._init_plots()
        self._init_controls()
        self._connect_panel_signals()

    def _setup_base_ui(self):
        """Configura la disposiciÃ³n bÃ¡sica de la UI con un divisor horizontal."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)

        self.main_splitter = QSplitter(Qt.Horizontal)

        self.left_column_widget = QWidget()
        self.left_column_layout = QVBoxLayout(self.left_column_widget)
        self.left_column_layout.setContentsMargins(0, 0, 0, 0)
        self.left_column_layout.setSpacing(5)
        self.left_column_widget.setMinimumWidth(400)

        self.right_column_widget = QWidget()
        self.right_column_layout = QVBoxLayout(self.right_column_widget)
        self.right_column_layout.setContentsMargins(5, 5, 5, 5)
        self.right_column_layout.setSpacing(5)
        
        # --- CORRECCIÃ“N DEL BUG DE DEFORMACIÃ“N ---
        # Se establece una polÃ­tica de tamaÃ±o fija en horizontal para evitar que el splitter
        # redimensione la columna de controles al actualizar su contenido.
        self.right_column_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.right_column_widget.setFixedWidth(460)

        self.main_splitter.addWidget(self.left_column_widget)
        self.main_splitter.addWidget(self.right_column_widget)

        self.main_splitter.setStretchFactor(0, 1) # Columna de grÃ¡ficos se expande
        self.main_splitter.setStretchFactor(1, 0) # Columna de controles es fija

        main_layout.addWidget(self.main_splitter)

    def _init_plots(self):
        """MÃ©todo abstracto para inicializar grÃ¡ficos. Debe ser implementado por subclases."""
        raise NotImplementedError("La subclase debe implementar _init_plots")

    def _init_controls(self):
        """MÃ©todo abstracto para inicializar controles. Debe ser implementado por subclases."""
        raise NotImplementedError("La subclase debe implementar _init_controls")

    def _connect_panel_signals(self):
        """Conecta las seÃ±ales internas del panel. Puede ser sobreescrito si es necesario."""
        pass

    def _log(self, message, is_error=False, is_debug=False):
        """Emite una seÃ±al para registrar un mensaje en el log principal de la aplicaciÃ³n."""
        self.logMessage.emit(message, is_error, is_debug)

    def _get_plot_colors(self):
        """Obtiene el diccionario de colores correspondiente al tema actual de la aplicaciÃ³n."""
        if self.parent_app and hasattr(self.parent_app, 'current_theme_is_dark'):
            return DARK_PLOT_COLORS if self.parent_app.current_theme_is_dark else LIGHT_PLOT_COLORS
        return DARK_PLOT_COLORS if self.is_dark_theme else LIGHT_PLOT_COLORS

    def on_theme_changed(self, is_dark_theme: bool):
        """Actualiza el tema del panel y sus componentes grÃ¡ficos."""
        self.is_dark_theme = is_dark_theme
        if hasattr(self, '_apply_all_plot_themes'):
            self._apply_all_plot_themes()
