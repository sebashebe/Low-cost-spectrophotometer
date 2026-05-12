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
Implementa el panel (pestaÃ±a) "Espectro Principal".

Es la vista principal para la visualizaciÃ³n de datos espectrales, permitiendo
cambiar entre tipos de grÃ¡fico (Intensidad, Absorbancia, Transmitancia)
y personalizar la visualizaciÃ³n.
"""
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QRadioButton, QGroupBox,
    QLabel, QListWidget, QListWidgetItem, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
import matplotlib.ticker as ticker

from base_panel import BasePanel
from utils import CollapsibleGroupBox, PlotWidget
from constants import WAVELENGTHS, PLOT_COLOR_CYCLE
from measurement_type import PlotType

class MainSpectrumPanel(BasePanel):
    """Define la UI y lÃ³gica para la pestaÃ±a de visualizaciÃ³n de espectros."""
    # SeÃ±ales para notificar a la app principal sobre cambios en las opciones
    plotTypeChanged = pyqtSignal(PlotType)
    superimposeSelectionChanged = pyqtSignal(list)
    logScaleYChanged = pyqtSignal(bool)
    showMarkersChanged = pyqtSignal(bool)
    showI0Changed = pyqtSignal(bool)

    def __init__(self, parent_app=None):
        """Inicializa el panel, sus variables y la UI."""
        self.plot_tooltip = None
        self.plot_color_cycle = PLOT_COLOR_CYCLE
        super().__init__(parent_app)

    def _log(self, message, is_error=False, is_debug=False):
        """Registra un mensaje con el prefijo de esta pestaÃ±a."""
        super()._log(f"[PanelEspectro] {message}", is_error, is_debug)

    def _init_plots(self):
        """Inicializa el widget del grÃ¡fico principal y el tooltip."""
        self.plot_widget = PlotWidget(self, width=6, height=4)
        self.ax = self.plot_widget.ax

        self.plot_tooltip = self.ax.text(0.5, 0.5, "", transform=self.ax.transAxes, ha="center", va="center",
                                         fontsize=9, bbox={'facecolor': 'wheat', 'alpha': 0.8, 'pad': 3},
                                         visible=False)

        self.left_column_layout.addWidget(self.plot_widget)

    def _init_controls(self):
        """Inicializa los controles de tipo de grÃ¡fico y opciones de personalizaciÃ³n."""
        plot_options_group_box = QGroupBox("Tipo de GrÃ¡fico")
        plot_type_layout = QHBoxLayout(plot_options_group_box)
        self.intensity_radio = QRadioButton("Intensidad")
        self.absorbance_radio = QRadioButton("Absorbancia")
        self.transmittance_radio = QRadioButton("Transmitancia (%T)")
        self.intensity_radio.setChecked(True)
        plot_type_layout.addWidget(self.intensity_radio)
        plot_type_layout.addWidget(self.absorbance_radio)
        plot_type_layout.addWidget(self.transmittance_radio)
        plot_type_layout.addStretch()
        self.right_column_layout.addWidget(plot_options_group_box)

        adv_plot_options_group = CollapsibleGroupBox("PersonalizaciÃ³n del GrÃ¡fico", "plot_customization", self.parent_app)
        adv_plot_options_content_layout = QVBoxLayout(adv_plot_options_group.content_widget)
        self.superimpose_list_label = QLabel("Superponer mediciones guardadas:")
        self.superimpose_list_widget = QListWidget()
        self.superimpose_list_widget.setMaximumHeight(150)
        self.log_scale_y_checkbox = QCheckBox("Usar Escala LogarÃ­tmica (Eje Y)")
        self.show_markers_checkbox = QCheckBox("Mostrar Marcadores")
        self.show_I0_checkbox = QCheckBox("Mostrar Iâ‚€ (en modo Intensidad)")
        
        adv_plot_options_content_layout.addWidget(self.superimpose_list_label)
        adv_plot_options_content_layout.addWidget(self.superimpose_list_widget)
        adv_plot_options_content_layout.addWidget(self.log_scale_y_checkbox)
        adv_plot_options_content_layout.addWidget(self.show_markers_checkbox)
        adv_plot_options_content_layout.addWidget(self.show_I0_checkbox)
        self.right_column_layout.addWidget(adv_plot_options_group)

        self.right_column_layout.addStretch(1)

    def _connect_panel_signals(self):
        """Conecta las seÃ±ales de los widgets a sus manejadores."""
        self.intensity_radio.toggled.connect(lambda checked: self.plotTypeChanged.emit(PlotType.INTENSITY) if checked else None)
        self.absorbance_radio.toggled.connect(lambda checked: self.plotTypeChanged.emit(PlotType.ABSORBANCE) if checked else None)
        self.transmittance_radio.toggled.connect(lambda checked: self.plotTypeChanged.emit(PlotType.TRANSMITTANCE) if checked else None)
        self.superimpose_list_widget.itemChanged.connect(self._on_superimpose_item_changed)
        self.log_scale_y_checkbox.toggled.connect(self.logScaleYChanged.emit)
        self.show_markers_checkbox.toggled.connect(self.showMarkersChanged.emit)
        self.show_I0_checkbox.toggled.connect(self.showI0Changed.emit)
        self.plot_widget.canvas.mpl_connect('motion_notify_event', self._on_plot_hover)

    def update_plot(self, plot_data: dict):
        """Redibuja el grÃ¡fico principal con los datos y opciones actuales."""
        if not self.isVisible() or not self.ax: return
        self.ax.clear()
        
        colors = self._get_plot_colors()
        data_to_plot_list = []
        current_color_idx = 0

        plot_type = plot_data.get('plot_type', PlotType.INTENSITY)
        is_intensity_mode = plot_type == PlotType.INTENSITY
        is_absorbance_mode = plot_type == PlotType.ABSORBANCE
        
        last_calibration_values = plot_data.get('i0_values')
        
        if plot_data.get('superimposed_labels'):
            for line_str in plot_data.get('session_data_raw', []):
                try:
                    parts = line_str.strip().split(',')
                    label = parts[0]
                    if label in plot_data.get('superimposed_labels'):
                        values = np.array([float(v) if v != "NaN" else np.nan for v in parts[1:]])
                        data = self._transform_data_for_plotting(values, last_calibration_values, plot_type, label)
                        if data is not None:
                            data_to_plot_list.append({
                                "label": label, "data": data, "color": self.plot_color_cycle[current_color_idx % len(self.plot_color_cycle)], "linestyle": '-'
                            })
                            current_color_idx += 1
                except (ValueError, IndexError):
                    pass
        
        if not data_to_plot_list and plot_data.get('last_measurement_values') is not None:
            data = self._transform_data_for_plotting(plot_data.get('last_measurement_values'), last_calibration_values, plot_type)
            if data is not None:
                data_to_plot_list.append({
                    "label": "Ãšltima MediciÃ³n", "data": data, "color": colors.get('line_color_data'), "linestyle": '-'
                })

        if is_absorbance_mode and plot_data.get('use_transfer_model'):
            data = self._get_adjusted_absorbance(plot_data)
            if data is not None:
                 data_to_plot_list.append({
                    "label": "A_ajustada (modelo trans.)", "data": data, "color": colors.get('transfer_model_fit_line_color'), "linestyle": ':'
                })

        if is_intensity_mode and plot_data.get('show_i0') and last_calibration_values is not None:
            data_to_plot_list.append({
                "label": "Referencia (Iâ‚€)", "data": last_calibration_values, "color": colors.get('i0_color'), "linestyle": '--'
            })

        all_finite_data = []
        for item in data_to_plot_list:
            if np.any(np.isfinite(item["data"])):
                marker = 'o' if plot_data.get('show_markers', True) else None
                self.ax.plot(WAVELENGTHS, item["data"], marker=marker, linestyle=item["linestyle"], color=item["color"], markersize=5, label=item["label"], picker=5)
                all_finite_data.extend(item["data"][np.isfinite(item["data"])])
        
        self._finalize_plot_style(plot_data, all_finite_data, colors)
        self.on_theme_changed(self.is_dark_theme)

    def _transform_data_for_plotting(self, intensity_data, i0_data, plot_type, label=""):
        """Convierte datos de intensidad a absorbancia o transmitancia."""
        if plot_type == PlotType.INTENSITY:
            return intensity_data
        
        if i0_data is None: return np.full_like(WAVELENGTHS, np.nan)
        
        if "ConcCalc_" in label and plot_type == PlotType.ABSORBANCE:
             return intensity_data
        
        i0_safe = np.where(i0_data > 1e-9, i0_data, np.nan)
        ratio = np.full_like(intensity_data, np.nan)
        valid_mask = ~np.isnan(i0_safe) & ~np.isnan(intensity_data)
        np.divide(intensity_data, i0_safe, out=ratio, where=valid_mask)
        
        if plot_type == PlotType.ABSORBANCE:
            abs_spec = np.full_like(ratio, np.nan)
            valid_log = ~np.isnan(ratio) & (ratio > 1e-9)
            abs_spec[valid_log] = -np.log10(ratio[valid_log])
            return abs_spec
        elif plot_type == PlotType.TRANSMITTANCE:
            return ratio * 100
        return None

    def _get_adjusted_absorbance(self, plot_data):
        """Calcula el espectro de absorbancia ajustada usando el modelo de transferencia."""
        selected_wl = plot_data.get('beer_wavelength')
        transfer_model_params = plot_data.get('active_transfer_model', {}).get(selected_wl)
        last_measurement_values = plot_data.get('last_measurement_values')
        i0_values = plot_data.get('i0_values')
        
        if not all([transfer_model_params, last_measurement_values is not None, i0_values is not None]):
            return None

        a_custom_spectrum = self._transform_data_for_plotting(last_measurement_values, i0_values, PlotType.ABSORBANCE)
        if a_custom_spectrum is None:
            return None
            
        slope_t, intercept_t, _ = transfer_model_params
        a_adjusted_spectrum = slope_t * a_custom_spectrum + intercept_t
        return a_adjusted_spectrum

    def _finalize_plot_style(self, plot_data, all_data_points, colors):
        """Aplica etiquetas, tÃ­tulos, escalas y leyendas al grÃ¡fico."""
        plot_type = plot_data.get('plot_type', PlotType.INTENSITY)
        y_label = "Valor"
        title = "Espectro"
        
        if plot_type == PlotType.INTENSITY:
            title = "Espectro de Intensidad"
            y_label = r"Intensidad Corregida ($I - I_0$)" if plot_data.get('subtraction_active') else "Intensidad (Relativa)"
        elif plot_type == PlotType.ABSORBANCE:
            title = "Espectro de Absorbancia"
            y_label = r"Absorbancia ($-\log_{10}((I-I_0)/I_0)$)" if plot_data.get('subtraction_active') else r"Absorbancia ($-\log_{10}(I/I_0)$)"
        elif plot_type == PlotType.TRANSMITTANCE:
            title = "Espectro de Transmitancia"
            y_label = r"Transmitancia ($\%T, ((I-I_0)/I_0) \times 100$)" if plot_data.get('subtraction_active') else r"Transmitancia ($\%T, (I/I_0) \times 100$)"

        self.ax.set_xlabel("Longitud de Onda (nm)")
        self.ax.set_ylabel(y_label)
        self.ax.set_title(title, fontsize=colors['title_fontsize'])
        
        self.ax.set_xticks(WAVELENGTHS)
        self.ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
        self.ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())

        if plot_data.get('use_log_scale_y'):
            self.ax.set_yscale('log')
        else:
            self.ax.set_yscale('linear')

        if all_data_points:
            min_val, max_val = np.min(all_data_points), np.max(all_data_points)
            data_range = max_val - min_val if max_val > min_val else 1.0
            padding = data_range * 0.1
            self.ax.set_ylim(min_val - padding, max_val + padding)
        
        if self.ax.has_data():
            self.ax.legend(fontsize='small')
        
    def _on_plot_hover(self, event):
        """Muestra un tooltip con informaciÃ³n del punto de datos al pasar el ratÃ³n."""
        if event.inaxes != self.ax:
            if self.plot_tooltip.get_visible():
                self.plot_tooltip.set_visible(False)
                self.plot_widget.canvas.draw_idle()
            return
        
        visible_lines = [line for line in self.ax.get_lines() if line.get_visible() and line.get_picker()]
        
        for line in reversed(visible_lines):
            contains, ind = line.contains(event)
            if contains:
                idx = ind['ind'][0]
                x_data, y_data = line.get_data()
                if idx < len(x_data) and idx < len(y_data):
                    wl, val = x_data[idx], y_data[idx]
                    if np.isfinite(val) and line.get_label() and not line.get_label().startswith('_'):
                        self.plot_tooltip.set_text(f"{line.get_label()}\nÎ»: {wl:.0f} nm\nValor: {val:.3f}")
                        self.plot_tooltip.set_position((wl, val))
                        self.plot_tooltip.set_visible(True)
                        self.plot_widget.canvas.draw_idle()
                        return

        if self.plot_tooltip.get_visible():
            self.plot_tooltip.set_visible(False)
            self.plot_widget.canvas.draw_idle()
    
    def _on_superimpose_item_changed(self):
        """Notifica a la app principal sobre cambios en la selecciÃ³n de espectros a superponer."""
        selected_labels = [self.superimpose_list_widget.item(i).data(Qt.UserRole)
                           for i in range(self.superimpose_list_widget.count())
                           if self.superimpose_list_widget.item(i).checkState() == Qt.Checked]
        self.superimposeSelectionChanged.emit(selected_labels)

    def update_superimpose_list(self, measurement_data_raw, selected_labels):
        """Actualiza la lista de mediciones disponibles para superponer en el grÃ¡fico."""
        self.superimpose_list_widget.blockSignals(True)
        self.superimpose_list_widget.clear()
        for i, data_line_str in enumerate(measurement_data_raw):
            try:
                label = data_line_str.split(',')[0]
                item = QListWidgetItem(f"{label} (Med. #{i+1})")
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setData(Qt.UserRole, label)
                item.setCheckState(Qt.Checked if label in selected_labels else Qt.Unchecked)
                self.superimpose_list_widget.addItem(item)
            except IndexError:
                pass
        self.superimpose_list_widget.blockSignals(False)
    
    def set_plot_options_state(self, show_markers, use_log_scale, show_i0, i0_available, is_intensity_mode):
        """Actualiza el estado de los checkboxes de opciones segÃºn el estado de la app."""
        self.show_markers_checkbox.setChecked(show_markers)
        self.log_scale_y_checkbox.setChecked(use_log_scale)
        
        can_show_i0 = i0_available and is_intensity_mode
        self.show_I0_checkbox.setEnabled(can_show_i0)
        if not can_show_i0:
            self.show_I0_checkbox.setChecked(False)
        else:
            self.show_I0_checkbox.setChecked(show_i0)

    def on_theme_changed(self, is_dark_theme: bool):
        """Aplica el cambio de tema al grÃ¡fico del panel."""
        self.is_dark_theme = is_dark_theme
        colors = self._get_plot_colors()
        if hasattr(self, 'plot_widget'):
            self.plot_widget.apply_theme(colors)
