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
Implementa el panel (pestaÃ±a) para "CalibraciÃ³n y Transferencia".

Permite al usuario crear curvas de calibraciÃ³n de sesiÃ³n (Abs vs. C) y
modelos de transferencia (A_ref vs. A_custom), y aplicar sus resultados
en la aplicaciÃ³n principal.
"""
import numpy as np
from scipy.stats import linregress
import csv
import os
import time

from PyQt5.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QLabel, QMessageBox,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QGridLayout, QFileDialog, QFrame, QRadioButton
)
from PyQt5.QtCore import Qt, QStandardPaths, pyqtSignal

from base_panel import BasePanel
from utils import CollapsibleGroupBox, PlotWidget
from constants import WAVELENGTHS, WAVELENGTH_LABELS

class CalibrationCurveTab(BasePanel):
    """Define la UI y lÃ³gica para la pestaÃ±a de calibraciÃ³n."""
    PANEL_ID = "calibration_curve_abs_vs_conc_tab"

    # SeÃ±ales para enviar los modelos calculados a la app principal
    calibrationApplied = pyqtSignal(dict)
    transferModelApplied = pyqtSignal(dict)
    transferModelCleared = pyqtSignal(int)

    def __init__(self, parent_app=None):
        """Inicializa el panel, sus variables y la UI."""
        self.calibration_points = []
        self.fit_result_abs_vs_conc = None
        self.fit_result_transfer_model = None
        super().__init__(parent_app)

        if self.parent_app and hasattr(self.parent_app, 'direct_measurement_signal'):
            self.parent_app.direct_measurement_signal.connect(self.handle_direct_measurement_result)

    def _log(self, message, is_error=False, is_debug=False):
        """Registra un mensaje con el prefijo de esta pestaÃ±a."""
        super()._log(f"[CurvaCalibTab] {message}", is_error, is_debug)

    def _init_plots(self):
        """Inicializa el widget del grÃ¡fico para las curvas."""
        self.plot_widget = PlotWidget(self, height=3)
        self.left_column_layout.addWidget(self.plot_widget)

    def _init_controls(self):
        """Inicializa todos los widgets de control de la pestaÃ±a."""
        view_select_group = QGroupBox("Seleccionar GrÃ¡fico a Visualizar")
        view_select_layout = QHBoxLayout(view_select_group)
        self.cal_view_radio = QRadioButton("CalibraciÃ³n (A_custom vs C)")
        self.cal_view_radio.setChecked(True)
        self.transfer_view_radio = QRadioButton("Transferencia (A_ref vs A_custom)")
        view_select_layout.addWidget(self.cal_view_radio)
        view_select_layout.addWidget(self.transfer_view_radio)
        self.right_column_layout.addWidget(view_select_group)


        controls_group = CollapsibleGroupBox(
            "AÃ±adir Puntos de CalibraciÃ³n",
            "calibration_curve_abs_vs_conc_tab_main",
            self.parent_app
        )
        controls_grid_layout = QGridLayout(controls_group.content_widget)
        controls_grid_layout.setSpacing(6)
        
        self.cal_wavelength_label = QLabel("Longitud de onda:")
        self.cal_wavelength_combo = QComboBox()
        for i, label in enumerate(WAVELENGTH_LABELS):
            self.cal_wavelength_combo.addItem(label, WAVELENGTHS[i])
        controls_grid_layout.addWidget(self.cal_wavelength_label, 0, 0)
        controls_grid_layout.addWidget(self.cal_wavelength_combo, 0, 1, 1, 2)

        self.conc_label = QLabel("ConcentraciÃ³n EstÃ¡ndar:")
        self.conc_input = QDoubleSpinBox()
        self.conc_input.setDecimals(6); self.conc_input.setRange(0, 100000); self.conc_input.setSingleStep(0.1)
        controls_grid_layout.addWidget(self.conc_label, 1, 0)
        controls_grid_layout.addWidget(self.conc_input, 1, 1, 1, 2)

        self.abs_custom_label = QLabel("Abs. Medida (A_custom):")
        self.abs_custom_input = QDoubleSpinBox()
        self.abs_custom_input.setDecimals(4); self.abs_custom_input.setRange(-2, 7); self.abs_custom_input.setEnabled(False)
        controls_grid_layout.addWidget(self.abs_custom_label, 2, 0)
        controls_grid_layout.addWidget(self.abs_custom_input, 2, 1, 1, 2)
        
        self.measure_abs_button = QPushButton("Medir A_custom EstÃ¡ndar")
        controls_grid_layout.addWidget(self.measure_abs_button, 3, 0, 1, 3)

        self.abs_ref_label = QLabel("Abs. Referencia (A_ref) (Opcional):")
        self.abs_ref_input = QDoubleSpinBox()
        self.abs_ref_input.setDecimals(4); self.abs_ref_input.setRange(-2, 7); self.abs_ref_input.setSpecialValueText(" ")
        self.abs_ref_input.setValue(self.abs_ref_input.minimum())
        self.abs_ref_input.setToolTip("Ingrese la absorbancia del estÃ¡ndar medida en un equipo de referencia.")
        controls_grid_layout.addWidget(self.abs_ref_label, 4, 0)
        controls_grid_layout.addWidget(self.abs_ref_input, 4, 1, 1, 2)

        self.add_point_button = QPushButton("AÃ±adir Punto a la Curva")
        controls_grid_layout.addWidget(self.add_point_button, 5, 0, 1, 3)
        self.right_column_layout.addWidget(controls_group)
        
        action_buttons_group = QGroupBox("Acciones y Resultados")
        action_buttons_layout_main = QVBoxLayout(action_buttons_group)
        
        self.apply_curve_button = QPushButton("Aplicar Curva(s) a App Principal")
        action_buttons_layout_main.addWidget(self.apply_curve_button)

        results_layout = QGridLayout()
        self.equation_label_abs_vs_c = QLabel("EcuaciÃ³n (A_custom vs C): N/A")
        self.r_squared_label_abs_vs_c = QLabel("RÂ² (SesiÃ³n): N/A")
        self.transfer_equation_label = QLabel("EcuaciÃ³n Transferencia: N/A")
        self.transfer_r_squared_label = QLabel("RÂ² (Transfer): N/A")
        results_layout.addWidget(QLabel("<b><u>CalibraciÃ³n de SesiÃ³n:</u></b>"), 0, 0)
        results_layout.addWidget(self.equation_label_abs_vs_c, 1, 0)
        results_layout.addWidget(self.r_squared_label_abs_vs_c, 2, 0)
        results_layout.addWidget(QLabel("<b><u>Modelo de Transferencia:</u></b>"), 3, 0)
        results_layout.addWidget(self.transfer_equation_label, 4, 0)
        results_layout.addWidget(self.transfer_r_squared_label, 5, 0)
        action_buttons_layout_main.addLayout(results_layout)
        self.right_column_layout.addWidget(action_buttons_group)

        table_group = CollapsibleGroupBox(
            "Puntos de CalibraciÃ³n (Î» Actual)",
            "calibration_curve_abs_vs_conc_tab_main",
            self.parent_app
        )
        table_layout = QVBoxLayout(table_group.content_widget)
        table_layout.setContentsMargins(0, 2, 0, 0)
        self.points_table = QTableWidget()
        self.points_table.setColumnCount(4)
        self.points_table.setHorizontalHeaderLabels(["ConcentraciÃ³n", "A_custom", "A_ref (Opc.)", "Î» (nm)"])
        self.points_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.points_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.points_table.setSelectionMode(QTableWidget.SingleSelection)
        self.points_table.setMinimumHeight(120); self.points_table.setMaximumHeight(250)
        table_layout.addWidget(self.points_table)
        
        table_buttons_layout = QHBoxLayout()
        self.remove_point_button = QPushButton("Eliminar Punto Seleccionado")
        self.clear_current_wl_button = QPushButton("Limpiar Puntos (Î» Actual)")
        table_buttons_layout.addWidget(self.remove_point_button)
        table_buttons_layout.addWidget(self.clear_current_wl_button)
        table_layout.addLayout(table_buttons_layout)
        self.right_column_layout.addWidget(table_group)

        file_buttons_group = QGroupBox("GestiÃ³n de Archivos de Curva")
        file_buttons_layout = QHBoxLayout(file_buttons_group)
        self.save_curve_data_button = QPushButton("Guardar Datos (Î» Actual)")
        self.load_curve_data_button = QPushButton("Cargar Datos (Î» Actual)")
        self.clear_all_button = QPushButton("Limpiar Todos los Puntos")
        file_buttons_layout.addWidget(self.save_curve_data_button)
        file_buttons_layout.addWidget(self.load_curve_data_button)
        file_buttons_layout.addWidget(self.clear_all_button)
        self.right_column_layout.addWidget(file_buttons_group)
        
        self.right_column_layout.addStretch(1)

        self.on_theme_changed(self.is_dark_theme)
        self.update_table_and_plot_all()

    def _connect_panel_signals(self):
        """Conecta las seÃ±ales de los widgets a sus respectivos manejadores (slots)."""
        self.cal_wavelength_combo.currentIndexChanged.connect(self.update_table_and_plot_all)
        self.cal_view_radio.toggled.connect(self.update_table_and_plot_all)
        self.transfer_view_radio.toggled.connect(self.update_table_and_plot_all)
        self.measure_abs_button.clicked.connect(self.request_direct_absorbance_measurement)
        self.add_point_button.clicked.connect(self.add_calibration_point)
        self.remove_point_button.clicked.connect(self.remove_selected_calibration_point)
        self.apply_curve_button.clicked.connect(self.apply_calibration_to_main_app)
        self.clear_current_wl_button.clicked.connect(self.clear_points_for_current_wl)
        self.clear_all_button.clicked.connect(self.clear_all_points)
        self.save_curve_data_button.clicked.connect(self.save_calibration_data_to_file)
        self.load_curve_data_button.clicked.connect(self.load_calibration_data_from_file)

    def request_direct_absorbance_measurement(self):
        """Emite una seÃ±al para solicitar una mediciÃ³n Ãºnica y directa a la app principal."""
        self._log("BotÃ³n 'Medir A_custom EstÃ¡ndar' clickeado.", is_debug=True)
        if self.parent_app is None:
            QMessageBox.warning(self, "Error de AplicaciÃ³n", "Funcionalidad de mediciÃ³n no disponible.")
            return
        
        selected_wl_value = self.cal_wavelength_combo.currentData()
        self.abs_custom_input.setEnabled(False)
        self.measure_abs_button.setEnabled(False)
        self.requestMeasurement.emit(self.PANEL_ID, selected_wl_value, "Absorbancia")

    def handle_direct_measurement_result(self, panel_id: str, wavelength_nm: int, value_type: str, value: float, success: bool, error_message: str = None):
        """Slot que procesa el resultado de una mediciÃ³n directa y actualiza la UI."""
        if panel_id != self.PANEL_ID: return
        self.measure_abs_button.setEnabled(True)
        if success and value_type == "Absorbancia" and wavelength_nm == self.cal_wavelength_combo.currentData():
            if not np.isnan(value):
                self.abs_custom_input.setValue(value)
                self.abs_custom_input.setEnabled(True)
                self._log(f"A_custom directa @ {wavelength_nm}nm: {value:.4f} recibida.", is_debug=True)
            else:
                QMessageBox.warning(self, "Error MediciÃ³n", f"A_custom NaN para {wavelength_nm}nm.")
                self.abs_custom_input.setValue(0); self.abs_custom_input.setEnabled(False)
        elif not success:
            default_msg = f"Fallo al medir A_custom para {wavelength_nm}nm."
            QMessageBox.warning(self, "Error MediciÃ³n", f"{default_msg}\n{error_message or ''}")
            self.abs_custom_input.setValue(0); self.abs_custom_input.setEnabled(False)

    def add_calibration_point(self):
        """Valida los datos de entrada y aÃ±ade un nuevo punto de calibraciÃ³n a la lista."""
        try:
            conc = self.conc_input.value()
            abs_custom = self.abs_custom_input.value()
            wl_cal_value = self.cal_wavelength_combo.currentData()

            abs_ref_val = self.abs_ref_input.value()
            abs_ref = abs_ref_val if abs_ref_val != self.abs_ref_input.minimum() else np.nan

            if conc < 0:
                 QMessageBox.warning(self, "Entrada InvÃ¡lida", "ConcentraciÃ³n no puede ser negativa.")
                 return
            if not self.abs_custom_input.isEnabled():
                QMessageBox.warning(self, "A_custom No Medida", "Mida 'A_custom EstÃ¡ndar' primero.")
                return
            if np.isnan(abs_custom):
                QMessageBox.warning(self, "Entrada InvÃ¡lida", "Valor de A_custom es NaN. Mida de nuevo.")
                return

            self.calibration_points.append((conc, abs_custom, wl_cal_value, abs_ref))
            self.update_table_and_plot_all()
            self.abs_custom_input.setValue(0); self.abs_custom_input.setEnabled(False)
            self.abs_ref_input.setValue(self.abs_ref_input.minimum())
            self.conc_input.setFocus(); self.conc_input.selectAll()
            self._log(f"Punto aÃ±adido: C={conc}, Acustom={abs_custom}, WL={wl_cal_value}, Aref={abs_ref}")
        except Exception as e:
            self._log(f"Error en add_calibration_point: {e}", is_error=True)
            QMessageBox.critical(self, "Error al AÃ±adir Punto", f"OcurriÃ³ un error inesperado al aÃ±adir el punto:\n{e}")

    def remove_selected_calibration_point(self):
        """Elimina el punto de calibraciÃ³n seleccionado en la tabla."""
        selected_rows = self.points_table.selectionModel().selectedRows()
        if not selected_rows: return
        row_idx_in_table = selected_rows[0].row()
        current_wl = self.cal_wavelength_combo.currentData()
        points_for_current_wl = sorted([p for p in self.calibration_points if p[2] == current_wl], key=lambda x: x[0])
        if 0 <= row_idx_in_table < len(points_for_current_wl):
            point_to_remove = points_for_current_wl[row_idx_in_table]
            if QMessageBox.Yes == QMessageBox.question(self, "Confirmar", f"Â¿Eliminar punto seleccionado?"):
                self.calibration_points.remove(point_to_remove)
                self.update_table_and_plot_all()

    def update_table_and_plot_all(self):
        """Actualiza la tabla de puntos, recalcula los ajustes y redibuja el grÃ¡fico."""
        current_wl = self.cal_wavelength_combo.currentData()
        points_for_current_wl = sorted([p for p in self.calibration_points if p[2] == current_wl], key=lambda x: x[0])
        
        self.points_table.setRowCount(0)
        for i, (conc, abs_custom, wl_val, abs_ref) in enumerate(points_for_current_wl):
            self.points_table.insertRow(i)
            self.points_table.setItem(i, 0, QTableWidgetItem(f"{conc:.6g}"))
            self.points_table.setItem(i, 1, QTableWidgetItem(f"{abs_custom:.4f}"))
            self.points_table.setItem(i, 2, QTableWidgetItem(f"{abs_ref:.4f}" if not np.isnan(abs_ref) else "N/A"))
            self.points_table.setItem(i, 3, QTableWidgetItem(str(wl_val)))

        self._calculate_fits(points_for_current_wl)
        
        self.plot_widget.clear()
        if self.cal_view_radio.isChecked():
            self._plot_abs_vs_conc(points_for_current_wl)
        else:
            self._plot_transfer_model(points_for_current_wl)
        
        self.on_theme_changed(self.is_dark_theme)

    def _calculate_fits(self, points_data):
        """Calcula las regresiones lineales para la curva de sesiÃ³n y el modelo de transferencia."""
        self.fit_result_abs_vs_conc = None
        self.fit_result_transfer_model = None

        if len(points_data) >= 2:
            concentrations = np.array([p[0] for p in points_data])
            abs_custom_values = np.array([p[1] for p in points_data])
            valid_mask = ~np.isnan(concentrations) & ~np.isnan(abs_custom_values)
            if np.sum(valid_mask) >= 2:
                res = linregress(concentrations[valid_mask], abs_custom_values[valid_mask])
                if not (np.isnan(res.slope) or np.isnan(res.intercept)):
                    self.fit_result_abs_vs_conc = res
        
        transfer_points = [p for p in points_data if not np.isnan(p[1]) and not np.isnan(p[3])]
        if len(transfer_points) >= 2:
            abs_custom_tm = np.array([p[1] for p in transfer_points])
            abs_ref_tm = np.array([p[3] for p in transfer_points])
            res_tm = linregress(abs_custom_tm, abs_ref_tm)
            if not (np.isnan(res_tm.slope) or np.isnan(res_tm.intercept)):
                self.fit_result_transfer_model = res_tm
        
        if self.fit_result_abs_vs_conc:
            res = self.fit_result_abs_vs_conc
            self.equation_label_abs_vs_c.setText(f"A_custom = {res.slope:.4g}*C + {res.intercept:.4g}")
            self.r_squared_label_abs_vs_c.setText(f"RÂ² (SesiÃ³n): {res.rvalue**2:.4f}")
        else:
            self.equation_label_abs_vs_c.setText("EcuaciÃ³n (A_custom vs C): N/A")
            self.r_squared_label_abs_vs_c.setText("RÂ² (SesiÃ³n): N/A")
        
        if self.fit_result_transfer_model:
            res_tm = self.fit_result_transfer_model
            self.transfer_equation_label.setText(f"A_ref = {res_tm.slope:.4g}*A_custom + {res_tm.intercept:.4g}")
            self.transfer_r_squared_label.setText(f"RÂ² (Transfer): {res_tm.rvalue**2:.4f}")
        else:
            self.transfer_equation_label.setText("EcuaciÃ³n Transferencia: N/A")
            self.transfer_r_squared_label.setText("RÂ² (Transfer): N/A")

    def _plot_abs_vs_conc(self, points_data):
        """Dibuja el grÃ¡fico de calibraciÃ³n (A_custom vs ConcentraciÃ³n)."""
        wl_text = self.cal_wavelength_combo.currentText()
        colors = self._get_plot_colors()
        
        if points_data:
            concentrations = np.array([p[0] for p in points_data])
            abs_custom_values = np.array([p[1] for p in points_data])
            self.plot_widget.ax.plot(concentrations, abs_custom_values, 'o', label='Puntos A_custom', color=colors['point_color_cal_curve'])
            
            if self.fit_result_abs_vs_conc:
                res = self.fit_result_abs_vs_conc
                line_x = np.array(self.plot_widget.ax.get_xlim())
                self.plot_widget.ax.plot(line_x, res.intercept + res.slope * line_x, '-', color=colors['line_color_fit_cal_curve'])
        
        self.plot_widget.ax.set_xlabel("ConcentraciÃ³n")
        self.plot_widget.ax.set_ylabel(f"A_custom @ {wl_text}")
        self.plot_widget.ax.set_title(f"CalibraciÃ³n SesiÃ³n (A_custom vs C) @ {wl_text}", fontsize=colors['title_fontsize'])
        self.plot_widget.draw()

    def _plot_transfer_model(self, points_data):
        """Dibuja el grÃ¡fico del Modelo de Transferencia (A_ref vs A_custom)."""
        wl_text = self.cal_wavelength_combo.currentText()
        colors = self._get_plot_colors()
        transfer_points = [p for p in points_data if not np.isnan(p[1]) and not np.isnan(p[3])]

        if transfer_points:
            abs_custom_tm = np.array([p[1] for p in transfer_points])
            abs_ref_tm = np.array([p[3] for p in transfer_points])
            self.plot_widget.ax.plot(abs_custom_tm, abs_ref_tm, 'o', label='Puntos (A_ref vs A_custom)', color=colors['transfer_model_points_color'])
            
            if self.fit_result_transfer_model:
                res_tm = self.fit_result_transfer_model
                line_x_tm = np.array(self.plot_widget.ax.get_xlim())
                self.plot_widget.ax.plot(line_x_tm, res_tm.intercept + res_tm.slope * line_x_tm, '-', color=colors['transfer_model_fit_line_color'])

        self.plot_widget.ax.set_xlabel(f"A_custom @ {wl_text}")
        self.plot_widget.ax.set_ylabel(f"A_ref @ {wl_text}")
        self.plot_widget.ax.set_title(f"Modelo de Transferencia @ {wl_text}", fontsize=colors['title_fontsize'])
        self.plot_widget.draw()

    def apply_calibration_to_main_app(self):
        """Emite los modelos calculados (curva de sesiÃ³n, modelo de transferencia) a la app principal."""
        wl = self.cal_wavelength_combo.currentData()
        applied_something = False
        log_msgs = []

        if self.fit_result_abs_vs_conc:
            res = self.fit_result_abs_vs_conc
            params = {'slope': res.slope, 'intercept': res.intercept, 'r_squared': res.rvalue**2, 'wavelength_nm': wl}
            self.calibrationApplied.emit(params)
            log_msgs.append(f"Curva SesiÃ³n (A_custom vs C) aplicada para {wl}nm.")
            applied_something = True

        if self.fit_result_transfer_model:
            res_tm = self.fit_result_transfer_model
            params_tm = {'slope_t': res_tm.slope, 'intercept_t': res_tm.intercept, 'r_sq_t': res_tm.rvalue**2, 'wavelength_nm': wl}
            self.transferModelApplied.emit(params_tm)
            log_msgs.append(f"Modelo de Transferencia aplicado para {wl}nm.")
            applied_something = True
        else:
            self.transferModelCleared.emit(wl)
            log_msgs.append(f"Modelo de Transferencia limpiado para {wl}nm (no habÃ­a uno vÃ¡lido para aplicar).")

        if applied_something:
            QMessageBox.information(self, "AplicaciÃ³n de Curvas", "\n".join(log_msgs))
        else:
            QMessageBox.warning(self, "AplicaciÃ³n de Curvas", "No se aplicÃ³ ninguna curva o modelo vÃ¡lido.")
        self._log("\n".join(log_msgs))

    def clear_points_for_current_wl(self):
        """Limpia todos los puntos de calibraciÃ³n para la longitud de onda seleccionada."""
        wl_to_clear = self.cal_wavelength_combo.currentData()
        points_before = len(self.calibration_points)
        self.calibration_points = [p for p in self.calibration_points if p[2] != wl_to_clear]
        num_deleted = points_before - len(self.calibration_points)
        if num_deleted > 0:
            QMessageBox.information(self, "Puntos Limpiados", f"{num_deleted} puntos para la Î» actual han sido borrados.")
        else:
            QMessageBox.information(self, "Puntos Limpiados", "No habÃ­a puntos para la Î» actual.")
        self.update_table_and_plot_all()

    def clear_all_points(self):
        """Limpia todos los puntos de calibraciÃ³n de todas las longitudes de onda."""
        if not self.calibration_points:
            QMessageBox.information(self, "Limpiar Todos los Puntos", "No hay puntos para borrar.")
            return
        if QMessageBox.Yes == QMessageBox.question(self, "Confirmar", "Â¿Borrar TODOS los puntos de calibraciÃ³n?"):
            points_count = len(self.calibration_points)
            self.calibration_points.clear()
            self.update_table_and_plot_all()
            QMessageBox.information(self, "Puntos Limpiados", f"Todos los {points_count} puntos han sido borrados.")

    def on_theme_changed(self, is_dark_theme: bool):
        """Aplica el cambio de tema al grÃ¡fico del panel."""
        self.is_dark_theme = is_dark_theme
        colors = self._get_plot_colors()
        if hasattr(self, 'plot_widget'):
            self.plot_widget.apply_theme(colors)
        
    def save_calibration_data_to_file(self):
        """Guarda los puntos de la longitud de onda actual en un archivo CSV."""
        current_wl = self.cal_wavelength_combo.currentData()
        points_to_save = [p for p in self.calibration_points if p[2] == current_wl]
        if not points_to_save: 
            QMessageBox.information(self, "Guardar Datos", "No hay puntos de calibraciÃ³n para la Î» actual para guardar.")
            return

        default_path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar Datos", os.path.join(default_path, f"cal_data_wl{current_wl}.csv"), "CSV (*.csv)")
        if not filename: return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Concentracion", "Absorbancia_Custom", "LongitudOnda_nm", "Absorbancia_Referencia_Opcional"])
                for p in points_to_save: writer.writerow(p)
            self._log(f"Datos guardados en {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar el archivo:\n{e}")
            self._log(f"Error al guardar: {e}", is_error=True)

    def load_calibration_data_from_file(self):
        """Carga puntos de calibraciÃ³n desde un archivo CSV para la longitud de onda actual."""
        current_wl = self.cal_wavelength_combo.currentData()
        if QMessageBox.No == QMessageBox.question(self, "Cargar Datos", f"Esto reemplazarÃ¡ los puntos para {current_wl}nm. Â¿Continuar?"): return

        filename, _ = QFileDialog.getOpenFileName(self, "Cargar Datos", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation), "CSV (*.csv)")
        if not filename: return
        
        try:
            loaded_points = []
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                header = next(reader)
                for i, row in enumerate(reader):
                    if len(row) != 4:
                        raise ValueError(f"La fila {i+2} no tiene 4 columnas.")
                    conc, abs_c, wl, abs_r_str = row
                    abs_r = float(abs_r_str) if abs_r_str and abs_r_str.lower() != 'nan' else np.nan
                    
                    if int(wl) == current_wl:
                        loaded_points.append((float(conc), float(abs_c), int(wl), abs_r))
            
            self.calibration_points = [p for p in self.calibration_points if p[2] != current_wl] + loaded_points
            self.update_table_and_plot_all()
            self._log(f"Datos cargados desde {filename}")
        except FileNotFoundError:
            msg = f"El archivo no se encontrÃ³: {filename}"
            QMessageBox.critical(self, "Error al Cargar", msg)
            self._log(msg, is_error=True)
        except (ValueError, IndexError) as e:
            msg = f"El archivo CSV tiene un formato incorrecto o estÃ¡ daÃ±ado.\nError: {e}"
            QMessageBox.critical(self, "Error de Formato", msg)
            self._log(msg, is_error=True)
        except Exception as e:
            msg = f"OcurriÃ³ un error inesperado al cargar el archivo:\n{e}"
            QMessageBox.critical(self, "Error Inesperado", msg)
            self._log(msg, is_error=True)
