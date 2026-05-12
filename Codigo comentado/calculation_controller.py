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
Contiene la clase CalculationController, que encapsula toda la lÃ³gica
para el cÃ¡lculo de concentraciÃ³n.
"""
from __future__ import annotations
import numpy as np
import time

from measurement_type import PlotType
from constants import WAVELENGTHS

# Se declara el tipo de la clase principal para type hinting sin causar importaciÃ³n circular
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import SpectrometerApp


class CalculationController:
    """Clase para encapsular toda la lÃ³gica de cÃ¡lculo de concentraciÃ³n."""
    def __init__(self, app: 'SpectrometerApp'):
        """Inicializador del controlador de cÃ¡lculos."""
        self.app = app

    def update_display_only(self):
        """Calcula la concentraciÃ³n y actualiza las etiquetas de la UI, pero no registra el dato."""
        concentration, success, msg, _, _, A_custom, A_adj = self._calculate_concentration_core()
        
        wl_val = self.app.beer_wavelength_combo.currentData()
        self.app.calculated_abs_custom_label.setText(f"A_custom (@{wl_val}nm): {A_custom:.4f}" if not np.isnan(A_custom) else "A_custom (@Î»): N/A")
        self.app.calculated_abs_adjusted_label.setText(f"A_ajustada (@{wl_val}nm): {A_adj:.4f}" if not np.isnan(A_adj) else "A_ajustada (@Î»): N/A")

        if success:
            label_text = f"C (@{wl_val}nm): {concentration:.4e}"
            if self.app.use_session_cal_curve_checkbox.isChecked():
                _, _, r_sq, _ = self.app.calibration_state.active_session_calibration_curve 
                label_text = f"C (SesiÃ³n @{wl_val}nm): {concentration:.4e} (RÂ²={r_sq:.3f})"
            elif self.app.use_transfer_model_checkbox.isChecked():
                 label_text = f"C (Transfer @{wl_val}nm): {concentration:.4e}"
            self.app.calculated_concentration_label.setText(label_text)
        else:
            self.app.calculated_concentration_label.setText(msg)

    def calculate_and_register(self):
        """Calcula la concentraciÃ³n y guarda el espectro de absorbancia como una nueva mediciÃ³n."""
        if self.app.plot_options.main_plot_type != PlotType.ABSORBANCE:
            self.app._show_error("El cÃ¡lculo de concentraciÃ³n requiere estar en modo 'Absorbancia'.")
            return

        concentration, success, error_msg, A_used, wl_val, A_custom, A_adj = self._calculate_concentration_core()
        self.update_display_only() 

        if not success:
            self.app._show_error(f"No se pudo calcular la concentraciÃ³n: {error_msg}")
            return
        
        current_A_spectrum = self._get_current_absorbance_spectrum()
        if current_A_spectrum is None:
            self.app._show_error("No hay espectro de absorbancia para registrar.")
            return

        label_prefix = "ConcCalc_Beer"
        A_val_label = A_used
        if self.app.use_session_cal_curve_checkbox.isChecked():
            label_prefix = "ConcCalc_Sesion"
            A_val_label = A_custom
        elif self.app.use_transfer_model_checkbox.isChecked():
            label_prefix = "ConcCalc_Transfer"
            A_val_label = A_adj

        label = f"{label_prefix}_C{concentration:.2e}_A{A_val_label:.2f}@{wl_val}nm_{time.strftime('%H%M%S')}"
        data_line = f"{label}," + ",".join(map(lambda x: f'{x:.4f}' if not np.isnan(x) else "NaN", current_A_spectrum))
        self.app.data_state.measurement_data_raw.append(data_line) 
        self.app._update_superimpose_list()
        self.app._log(f"ConcentraciÃ³n registrada: {concentration:.4e}")
        self.app._show_info(f"ConcentraciÃ³n: {concentration:.4e}\nEspectro registrado como '{label}'.")

    def _calculate_concentration_core(self):
        """FunciÃ³n central que realiza el cÃ¡lculo de concentraciÃ³n segÃºn el mÃ©todo seleccionado."""
        A_custom, A_adj, A_used = np.nan, np.nan, np.nan
        wl_val = self.app.beer_wavelength_combo.currentData()
        
        try:
            current_A_spectrum = self._get_current_absorbance_spectrum()
            if current_A_spectrum is None:
                return np.nan, False, "C: N/A (A_custom no disp.)", A_used, wl_val, A_custom, A_adj

            wl_idx = np.where(WAVELENGTHS == wl_val)[0][0]
            A_custom = current_A_spectrum[wl_idx]
            if np.isnan(A_custom):
                return np.nan, False, f"C (@{wl_val}nm): N/A (A_custom es NaN)", A_used, wl_val, A_custom, A_adj
            
            if self.app.use_transfer_model_checkbox.isChecked():
                model = self.app.calibration_state.active_transfer_model.get(wl_val)
                ref_cal = self.app.calibration_state.reference_calibration_parameters.get(wl_val)
                if not model or not ref_cal:
                    return np.nan, False, f"C (Transfer @{wl_val}nm): Modelo/Cal.Ref. incompletos", A_used, wl_val, A_custom, A_adj
                
                slope_t, intercept_t, _ = model
                A_adj = slope_t * A_custom + intercept_t
                A_used = A_adj

                if ref_cal['type'] == 'curve':
                    m_ref, b_ref = ref_cal.get('m_ref', 0), ref_cal.get('b_ref', 0)
                    if abs(m_ref) < 1e-12: return np.nan, False, "C (Transfer): m_ref â‰ˆ 0", A_used, wl_val, A_custom, A_adj
                    concentration = (A_adj - b_ref) / m_ref
                    return concentration, True, "", A_used, wl_val, A_custom, A_adj
                else:
                    eps_l_ref = ref_cal.get('epsilon_l_ref')
                    if not eps_l_ref or abs(eps_l_ref) < 1e-12: return np.nan, False, "C (Transfer): (ÎµL)_ref â‰ˆ 0", A_used, wl_val, A_custom, A_adj
                    concentration = A_adj / eps_l_ref
                    return concentration, True, "", A_used, wl_val, A_custom, A_adj

            if self.app.use_session_cal_curve_checkbox.isChecked():
                cal_curve = self.app.calibration_state.active_session_calibration_curve
                if cal_curve and cal_curve[3] == wl_val:
                    slope, intercept, _, _ = cal_curve
                    if abs(slope) < 1e-12: return np.nan, False, "C (SesiÃ³n): Pendiente â‰ˆ 0", A_custom, wl_val, A_custom, A_adj
                    concentration = (A_custom - intercept) / slope
                    return concentration, True, "", A_custom, wl_val, A_custom, A_adj
            
            epsilon = float(self.app.epsilon_input.text().strip().replace(',', '.'))
            b = float(self.app.path_length_input.text().strip().replace(',', '.'))
            if abs(epsilon * b) < 1e-12: 
                return np.nan, False, f"C (Beer @{wl_val}nm): Îµ*b â‰ˆ 0", A_custom, wl_val, A_custom, A_adj
            concentration = A_custom / (epsilon * b)
            return concentration, True, "", A_custom, wl_val, A_custom, A_adj

        except (ValueError, IndexError):
            return np.nan, False, "C: Error (Îµ, b numÃ©ricos)", A_used, wl_val, A_custom, A_adj
        except Exception as e:
            self.app._log(f"Error en _calculate_concentration_core: {e}", is_error=True)
            return np.nan, False, "C: Error de cÃ¡lculo", A_used, wl_val, A_custom, A_adj

    def _get_current_absorbance_spectrum(self):
        """Calcula el espectro de absorbancia actual a partir de I e I0."""
        i_vals = self.app.data_state.last_measurement_values
        i0_vals = self.app.data_state.last_calibration_values
        if i_vals is None or i0_vals is None: return None

        with np.errstate(divide='ignore', invalid='ignore'):
            i0_safe = np.where(i0_vals > 1e-9, i0_vals, np.nan)
            ratio = i_vals / i0_safe
            absorbance = -np.log10(ratio)
        absorbance[~np.isfinite(absorbance)] = np.nan
        return absorbance
