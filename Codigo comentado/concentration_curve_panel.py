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
Implementa el panel (pestaÃ±a) "Curva Conc. vs MediciÃ³n".

Permite construir un grÃ¡fico genÃ©rico de una variable X (ej. ConcentraciÃ³n)
contra un valor Y medido directamente (Intensidad, Absorbancia, etc.),
siendo una herramienta flexible para diversos tipos de experimentos.
"""
import numpy as np
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QApplication, QAbstractItemView, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt

from base_panel import BasePanel
from utils import CollapsibleGroupBox, PlotWidget
from constants import WAVELENGTHS, WAVELENGTH_LABELS

class ConcentrationCurvePanel(BasePanel):
    """Define la UI y lÃ³gica para la pestaÃ±a de curva de concentraciÃ³n."""
    PANEL_ID = "concentration_curve_panel"

    def __init__(self, parent_app=None):
        """Inicializa el panel, sus variables y la UI."""
        self.data_points = []
        super().__init__(parent_app)

        if self.parent_app and hasattr(self.parent_app, 'direct_measurement_signal'):
            self.parent_app.direct_measurement_signal.connect(self.handle_direct_measurement_result)

    def _log(self, message, is_error=False, is_debug=False):
        """Registra un mensaje con el prefijo de esta pestaÃ±a."""
        super()._log(f"[CurvaConc] {message}", is_error, is_debug)

    def _init_plots(self):
        """Inicializa el widget del grÃ¡fico para la curva."""
        self.plot_widget = PlotWidget(self, height=3)
        self.left_column_layout.addWidget(self.plot_widget)

    def _init_controls(self):
        """Inicializa todos los widgets de control de la pestaÃ±a."""
        controls_group = CollapsibleGroupBox(
            "Controles de la Curva",
            "concentration_curve_tab_main",
            self.parent_app
        )
        controls_layout = QGridLayout(controls_group.content_widget)
        controls_layout.setSpacing(6)

        self.y_type_label = QLabel("Tipo de Valor Y:")
        self.y_type_combo = QComboBox()
        self.y_type_combo.addItems(["Intensidad", "Absorbancia", "Transmitancia"])
        controls_layout.addWidget(self.y_type_label, 0, 0)
        controls_layout.addWidget(self.y_type_combo, 0, 1, 1, 2)

        self.wl_label = QLabel("Longitud de Onda:")
        self.wl_combo = QComboBox()
        for i, label in enumerate(WAVELENGTH_LABELS):
            self.wl_combo.addItem(label, WAVELENGTHS[i])
        controls_layout.addWidget(self.wl_label, 1, 0)
        controls_layout.addWidget(self.wl_combo, 1, 1, 1, 2)

        self.x_value_label = QLabel("Valor Eje X (ej. ConcentraciÃ³n):")
        self.x_value_input = QDoubleSpinBox()
        self.x_value_input.setDecimals(6)
        self.x_value_input.setRange(0, 1e9)
        self.x_value_input.setSingleStep(0.1)
        controls_layout.addWidget(self.x_value_label, 2, 0)
        controls_layout.addWidget(self.x_value_input, 2, 1, 1, 2)

        self.measured_value_label = QLabel("Valor Medido (Y):")
        self.measured_value_input = QDoubleSpinBox()
        self.measured_value_input.setDecimals(6)
        self.measured_value_input.setRange(-1e9, 1e9)
        self.measured_value_input.setSingleStep(0.01)
        self.measured_value_input.setEnabled(False)
        controls_layout.addWidget(self.measured_value_label, 3, 0)
        controls_layout.addWidget(self.measured_value_input, 3, 1, 1, 2)

        self.take_measurement_button = QPushButton("Medir Valor Y Directamente")
        controls_layout.addWidget(self.take_measurement_button, 4, 0, 1, 3)

        self.add_point_button = QPushButton("AÃ±adir Punto a la Curva")
        controls_layout.addWidget(self.add_point_button, 5, 0, 1, 3)
        self.right_column_layout.addWidget(controls_group)

        table_group = CollapsibleGroupBox(
            "Puntos de la Curva (Vista Actual)",
            "concentration_curve_tab_main",
            self.parent_app
        )
        table_layout_v = QVBoxLayout(table_group.content_widget)
        table_layout_v.setContentsMargins(0, 2, 0, 0)
        self.points_table = QTableWidget()
        self.points_table.setColumnCount(4)
        self.points_table.setHorizontalHeaderLabels(["Valor X", "Valor Medido Y", "Tipo Y", "Î» (nm)"])
        self.points_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.points_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.points_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.points_table.setMinimumHeight(100)
        self.points_table.setMaximumHeight(200)
        table_layout_v.addWidget(self.points_table)

        self.remove_point_button = QPushButton("Eliminar Punto Seleccionado")
        table_layout_v.addWidget(self.remove_point_button)
        self.right_column_layout.addWidget(table_group)

        clear_buttons_layout = QHBoxLayout()
        self.clear_current_view_button = QPushButton("Limpiar Puntos (Vista Actual)")
        self.clear_all_button = QPushButton("Limpiar Todos los Puntos")
        clear_buttons_layout.addStretch()
        clear_buttons_layout.addWidget(self.clear_current_view_button)
        clear_buttons_layout.addWidget(self.clear_all_button)
        self.right_column_layout.addLayout(clear_buttons_layout)

        self.right_column_layout.addStretch(1)
        
        self.on_theme_changed(self.is_dark_theme)
        self.update_table_and_plot()

    def _connect_panel_signals(self):
        """Conecta las seÃ±ales de los widgets a sus manejadores (slots)."""
        self.y_type_combo.currentTextChanged.connect(self.update_table_and_plot)
        self.wl_combo.currentIndexChanged.connect(self.update_table_and_plot)
        self.take_measurement_button.clicked.connect(self.request_direct_value_measurement)
        self.add_point_button.clicked.connect(self.add_data_point)
        self.remove_point_button.clicked.connect(self.remove_selected_data_point)
        self.clear_current_view_button.clicked.connect(self.clear_points_for_current_view)
        self.clear_all_button.clicked.connect(self.clear_all_points)

    def request_direct_value_measurement(self):
        """Emite una seÃ±al para solicitar una mediciÃ³n Ãºnica y directa a la app principal."""
        self._log("BotÃ³n 'Medir Valor Y Directamente' clickeado.", is_debug=True)
        if not self.parent_app:
            QMessageBox.warning(self, "Error de AplicaciÃ³n", "La referencia a la aplicaciÃ³n principal no estÃ¡ disponible.")
            return

        current_y_type = self.y_type_combo.currentText()
        selected_wl_value_numeric = self.wl_combo.currentData()
        
        self.measured_value_input.setEnabled(False)
        self.measured_value_input.setValue(0)
        self.take_measurement_button.setEnabled(False)
        self.requestMeasurement.emit(self.PANEL_ID, selected_wl_value_numeric, current_y_type)

    def handle_direct_measurement_result(self, panel_id: str, wavelength_nm: int, value_type: str, value: float, success: bool, error_message: str = None):
        """Slot que procesa el resultado de una mediciÃ³n directa y actualiza la UI."""
        if panel_id != self.PANEL_ID: return
        
        self.take_measurement_button.setEnabled(True)
        
        if success and value_type == self.y_type_combo.currentText() and wavelength_nm == self.wl_combo.currentData():
            if not np.isnan(value):
                self.measured_value_input.setValue(value)
                self.measured_value_input.setEnabled(True)
                self._log(f"Valor directo '{value_type}' @ {wavelength_nm}nm: {value:.4f} recibido y cargado.", is_debug=True)
            else:
                QMessageBox.warning(self, "Error de MediciÃ³n", f"No se pudo obtener un valor vÃ¡lido (NaN) para '{value_type}' en {wavelength_nm}nm.")
                self.measured_value_input.setValue(0)
                self.measured_value_input.setEnabled(False)
        elif not success:
            default_msg = f"No se pudo completar la mediciÃ³n directa para '{value_type}' en {wavelength_nm}nm."
            QMessageBox.warning(self, "Error de MediciÃ³n", f"{default_msg}\n{error_message or ''}")
            self.measured_value_input.setValue(0)
            self.measured_value_input.setEnabled(False)

    def add_data_point(self):
        """Valida los datos de entrada y aÃ±ade el par (X, Y) a la lista de datos."""
        try:
            x_val = self.x_value_input.value()
            measured_y_val = self.measured_value_input.value()
            y_type = self.y_type_combo.currentText()
            wl_val_numeric = self.wl_combo.currentData()

            if not self.measured_value_input.isEnabled():
                QMessageBox.warning(self, "Valor Y No Medido", "Por favor, use 'Medir Valor Y Directamente' para obtener un nuevo valor.")
                return

            if np.isnan(measured_y_val):
                QMessageBox.warning(self, "Entrada InvÃ¡lida", "El valor medido no es vÃ¡lido (NaN). Intente medir de nuevo.")
                return

            self.data_points.append((x_val, measured_y_val, y_type, wl_val_numeric))
            self.update_table_and_plot()
            self.measured_value_input.setValue(0)
            self.measured_value_input.setEnabled(False)
            self.x_value_input.setFocus()
            self.x_value_input.selectAll()
            self._log(f"Punto aÃ±adido: (X:{x_val:.4f}, Y:{measured_y_val:.4f}, Tipo:{y_type}, WL:{wl_val_numeric}nm)")

        except Exception as e:
            self._log(f"Error en add_data_point: {e}", is_error=True)
            QMessageBox.warning(self, "Error", f"OcurriÃ³ un error al aÃ±adir el punto: {e}")

    def remove_selected_data_point(self):
        """Elimina el punto seleccionado en la tabla de la lista de datos."""
        selected_rows = self.points_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Eliminar Punto", "Seleccione un punto de la tabla para eliminar.")
            return

        current_y_type_filter = self.y_type_combo.currentText()
        current_wl_filter = self.wl_combo.currentData()
        row_to_remove_display = selected_rows[0].row()

        displayable_points = sorted([p for p in self.data_points if p[2] == current_y_type_filter and p[3] == current_wl_filter], key=lambda x: x[0])

        if 0 <= row_to_remove_display < len(displayable_points):
            point_to_remove_tuple = displayable_points[row_to_remove_display]
            reply = QMessageBox.question(self, "Confirmar EliminaciÃ³n", f"Â¿Eliminar el punto: X={point_to_remove_tuple[0]:.4f}, Y={point_to_remove_tuple[1]:.4f}?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.data_points.remove(point_to_remove_tuple)
                self._log(f"Punto eliminado: {point_to_remove_tuple}")
                self.update_table_and_plot()
        else:
             QMessageBox.warning(self, "Error de SelecciÃ³n", "La selecciÃ³n de la tabla no es vÃ¡lida.")

    def update_table_and_plot(self):
        """Filtra los datos segÃºn la vista actual y actualiza la tabla y el grÃ¡fico."""
        current_y_type_filter = self.y_type_combo.currentText()
        current_wl_filter = self.wl_combo.currentData()
        current_wl_text_filter = self.wl_combo.currentText()

        self.points_table.setRowCount(0)
        points_for_current_view = sorted([p for p in self.data_points if p[2] == current_y_type_filter and p[3] == current_wl_filter], key=lambda x: x[0])

        for i, (x_val, y_val, y_type, wl) in enumerate(points_for_current_view):
            self.points_table.insertRow(i)
            self.points_table.setItem(i, 0, QTableWidgetItem(f"{x_val:.6g}"))
            self.points_table.setItem(i, 1, QTableWidgetItem(f"{y_val:.6g}"))
            self.points_table.setItem(i, 2, QTableWidgetItem(str(y_type)))
            self.points_table.setItem(i, 3, QTableWidgetItem(str(wl)))

        self.plot_widget.clear()
        colors = self._get_plot_colors()
        
        if points_for_current_view:
            x_values = np.array([p[0] for p in points_for_current_view])
            y_values = np.array([p[1] for p in points_for_current_view])
            point_color = colors.get('point_color_conc_curve')
            line_color_data = colors.get('line_color_data_conc_curve')
            self.plot_widget.ax.plot(x_values, y_values, marker='o', linestyle='-', label=f'{current_y_type_filter} @ {current_wl_text_filter}', color=line_color_data, markerfacecolor=point_color, markersize=5, linewidth=1.5)
        
        self.plot_widget.ax.set_xlabel("Valor Eje X (ej. ConcentraciÃ³n, Tiempo)")
        self.plot_widget.ax.set_ylabel(f"{current_y_type_filter} @ {current_wl_text_filter}")
        self.plot_widget.ax.set_title(f"GrÃ¡fico: Eje X vs. {current_y_type_filter}", fontsize=colors['title_fontsize'])
        
        self.on_theme_changed(self.is_dark_theme)
        self.plot_widget.draw()

    def clear_points_for_current_view(self):
        """Limpia los puntos solo para la combinaciÃ³n de tipo Y y Î» seleccionada."""
        current_y_type_filter = self.y_type_combo.currentText()
        current_wl_filter = self.wl_combo.currentData()
        points_before = len(self.data_points)
        self.data_points = [p for p in self.data_points if not (p[2] == current_y_type_filter and p[3] == current_wl_filter)]
        num_deleted = points_before - len(self.data_points)
        if num_deleted > 0:
            QMessageBox.information(self, "Puntos Limpiados", f"{num_deleted} puntos para la vista actual han sido borrados.")
            self.update_table_and_plot()
        else:
            QMessageBox.information(self, "Puntos Limpiados", "No habÃ­a puntos para la vista actual.")

    def clear_all_points(self):
        """Limpia todos los puntos de datos almacenados en este panel."""
        if not self.data_points:
            QMessageBox.information(self, "Limpiar Todos los Puntos", "No hay puntos para borrar.")
            return
        reply = QMessageBox.question(self, "Confirmar Limpiar Todos", f"Â¿Borrar TODOS los {len(self.data_points)} puntos de datos?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            points_count = len(self.data_points)
            self.data_points.clear()
            self.update_table_and_plot()
            QMessageBox.information(self, "Puntos Limpiados", f"Todos los {points_count} puntos han sido borrados.")

    def on_theme_changed(self, is_dark_theme: bool):
        """Aplica el cambio de tema al grÃ¡fico del panel."""
        self.is_dark_theme = is_dark_theme
        colors = self._get_plot_colors()
        if hasattr(self, 'plot_widget'):
            self.plot_widget.apply_theme(colors)
