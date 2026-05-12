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
Contiene la clase FileManager, que encapsula todas las operaciones de guardado y
carga de archivos, manteniendo la clase principal mÃ¡s limpia y organizada.
"""
from __future__ import annotations
import os
import time
import csv
import numpy as np

from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QStandardPaths

from constants import WAVELENGTHS
from app_state import MeasurementControlState
from main_spectrum_panel import MainSpectrumPanel
from concentration_curve_panel import ConcentrationCurvePanel
from calibration_curve_tab import CalibrationCurveTab

# Se declara el tipo de la clase principal para type hinting sin causar importaciÃ³n circular
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import SpectrometerApp


class FileManager:
    """Clase para manejar todas las operaciones de archivos (guardar, exportar)."""
    def __init__(self, app: 'SpectrometerApp'):
        """Inicializador del gestor de archivos."""
        self.app = app
        self.parent = app

    def export_log(self):
        """Exporta el contenido del log de eventos a un archivo de texto."""
        content = self.app.log_output.toPlainText().strip()
        if not content:
            self.app._show_info("El log estÃ¡ vacÃ­o.")
            return
        filename = self._get_save_filename("Exportar Log", "log_espectro.txt", "Text Files (*.txt)")
        if not filename: return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f: f.write(content)
            self.app._log(f"Log exportado a {filename}")
            self.app._show_info(f"Log guardado en:\n{filename}")
        except Exception as e:
            self.app._show_error(f"Error al exportar el log: {e}")

    def export_graph_active_tab(self):
        """Exporta una imagen del grÃ¡fico de la pestaÃ±a actualmente visible."""
        figure, filename_prefix = self._get_active_figure_and_prefix()
        if not figure:
            self.app._show_info("No hay grÃ¡fico con datos para exportar en la pestaÃ±a actual.")
            return

        filename = self._get_save_filename(
            "Guardar GrÃ¡fico Como", f"{filename_prefix}.png", 
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf);;JPEG (*.jpg)"
        )
        if not filename: return
        
        try:
            bg_color = figure.get_facecolor()
            figure.savefig(filename, dpi=300, bbox_inches='tight', facecolor=bg_color)
            self.app._log(f"GrÃ¡fico guardado en {filename}")
        except Exception as e:
            self.app._show_error(f"Error al guardar el grÃ¡fico: {e}")

    def save_session_data(self):
        """Guarda todos los datos acumulados de la sesiÃ³n (I0 e I) en un archivo CSV."""
        if not self.app.data_state.measurement_data_raw:
            self.app._show_info("No hay datos de sesiÃ³n para guardar.")
            return
        filename = self._get_save_filename("Guardar Datos de SesiÃ³n", "espectro_sesion.csv", "CSV (*.csv)")
        if not filename: return
        self._write_csv(filename, self.app.data_state.measurement_data_raw, is_selection=False)

    def save_selected_superimposed_data(self):
        """Guarda solo los espectros que estÃ¡n seleccionados para superponer."""
        labels = self.app.plot_options.superimposed_spectra_labels
        if not labels:
            self.app._show_info("No hay espectros seleccionados para guardar.")
            return
        
        data_to_save = [line for line in self.app.data_state.measurement_data_raw if line.strip().split(',')[0] in labels]
        if not data_to_save:
            self.app._show_info("No se encontraron datos para los espectros seleccionados.")
            return

        filename = self._get_save_filename("Guardar SelecciÃ³n", "espectros_seleccionados.csv", "CSV (*.csv)")
        if not filename: return
        self._write_csv(filename, data_to_save, is_selection=True)

    def get_save_filename_for_sequential(self) -> str:
        """Abre un diÃ¡logo para obtener la ruta de guardado para una mediciÃ³n secuencial."""
        return self._get_save_filename("Guardar MediciÃ³n Secuencial", "med_secuencial.csv", "CSV (*.csv)")

    def save_sequential_data(self, m_state: MeasurementControlState):
        """Escribe los resultados de una mediciÃ³n secuencial a un archivo CSV."""
        if not m_state.collected_final_sequential_points or not m_state.sequential_output_filename:
            self.app._log("No hay datos secuenciales para guardar.", is_error=True)
            return
        
        filename = m_state.sequential_output_filename
        try:
            with open(filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["### CONFIGURACIÃ“N DE MEDICIÃ“N SECUENCIAL ###"])
                writer.writerow([f"Timestamp:", time.strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([f"P Solicitadas:", m_state.p_measurements])
                writer.writerow([f"M Nominal:", m_state.m_samples])
                
                header_meas = ["Etiqueta_Punto"] + \
                              [f"Intensidad_Corregida_{wl}nm" for wl in WAVELENGTHS] + \
                              [f"Intensidad_Cruda_Promedio_{wl}nm" for wl in WAVELENGTHS]
                writer.writerow([]); writer.writerow(["### DATOS ###"]); writer.writerow(header_meas)

                for spectrum_corr, label, spectrum_raw in m_state.collected_final_sequential_points:
                    row_data = [label] + \
                               [f"{v:.4f}" if not np.isnan(v) else "NaN" for v in spectrum_corr] + \
                               [f"{v:.4f}" if spectrum_raw is not None and not np.isnan(v) else "NaN" for v in spectrum_raw]
                    writer.writerow(row_data)

            self.app._log(f"Datos secuenciales guardados en {filename}")
            self.app._show_info(f"Datos secuenciales guardados en:\n{filename}")
        except Exception as e:
            self.app._show_error(f"Error al guardar archivo secuencial: {e}")

    def _get_active_figure_and_prefix(self):
        """Identifica la pestaÃ±a actual y devuelve su figura de Matplotlib para exportarla."""
        widget = self.app.right_tabs.currentWidget()
        if isinstance(widget, MainSpectrumPanel) and widget.ax.has_data():
            return widget.plot_widget.figure, "espectro_principal"
        if isinstance(widget, ConcentrationCurvePanel) and widget.plot_widget.ax.has_data():
            return widget.plot_widget.figure, "curva_concentracion"
        if isinstance(widget, CalibrationCurveTab):
            if widget.plot_widget.ax.has_data():
                return widget.plot_widget.figure, "curva_calibracion_sesion_o_transferencia"
        return None, None

    def _get_save_filename(self, title, default_name, file_filter):
        """Abre un diÃ¡logo de 'Guardar como...' estÃ¡ndar con un nombre por defecto."""
        default_path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        base, ext = os.path.splitext(default_name)
        default_filename = os.path.join(default_path, f"{base}_{timestamp}{ext}")
        
        filename, _ = QFileDialog.getSaveFileName(self.parent, title, default_filename, file_filter)
        return filename

    def _write_csv(self, filename: str, data_lines: list, is_selection: bool):
        """FunciÃ³n auxiliar para escribir los datos de sesiÃ³n o selecciÃ³n a un CSV."""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                title = "SELECCIÃ“N DE ESPECTROS" if is_selection else "DATOS DE SESIÃ“N"
                writer.writerow([f"### {title} ###"])
                writer.writerow([f"Timestamp:", time.strftime('%Y-%m-%d %H:%M:%S')])
                
                header_i0 = ["RawLine_Arduino_I0"] + [f"{wl}nm" for wl in WAVELENGTHS]
                if not is_selection:
                    writer.writerow([]); writer.writerow(["### DATOS DE REFERENCIA (I0) ###"])
                    writer.writerow(header_i0)
                    for line in self.app.data_state.calibration_data_raw:
                        writer.writerow([line] + line.strip().split(',')[1:])
                
                writer.writerow([]); writer.writerow(["### DATOS DE MEDICIÃ“N (I o A_custom) ###"])
                header_meas = ["Etiqueta"] + [f"Valor_{wl}nm" for wl in WAVELENGTHS]
                writer.writerow(header_meas)
                for line in data_lines:
                    writer.writerow(line.strip().split(','))
            
            self.app._log(f"Datos guardados en {filename}")
        except Exception as e:
            self.app._show_error(f"Error al guardar CSV: {e}")
