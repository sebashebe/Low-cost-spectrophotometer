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
Define estructuras de datos para gestionar el estado de la aplicaciÃ³n de
forma centralizada y organizada, facilitando el mantenimiento y la
transferencia de estado entre componentes.
"""

from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from measurement_type import PlotType

@dataclass
class PlotOptionsState:
    """Almacena el estado de las opciones de visualizaciÃ³n de grÃ¡ficos."""
    superimposed_spectra_labels: List[str] = field(default_factory=list)
    use_log_scale_y: bool = False
    show_markers: bool = True
    show_I0_on_intensity_graph: bool = False
    main_plot_type: PlotType = PlotType.INTENSITY

@dataclass
class MeasurementDataState:
    """Almacena todos los datos de mediciÃ³n de la sesiÃ³n actual."""
    calibration_data_raw: List[str] = field(default_factory=list)
    measurement_data_raw: List[str] = field(default_factory=list)
    last_calibration_values: Optional[np.ndarray] = None
    last_raw_measurement_spectrum: Optional[np.ndarray] = None
    last_measurement_values: Optional[np.ndarray] = None
    blank_subtraction_active: bool = False

@dataclass
class CalibrationState:
    """Almacena parÃ¡metros y estados relacionados con la calibraciÃ³n."""
    active_session_calibration_curve: Optional[Tuple[float, float, float, int]] = None
    active_transfer_model: Dict[int, Tuple[float, float, float]] = field(default_factory=dict)
    reference_calibration_parameters: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    epsilon_session: str = ""
    path_length_session: str = "0.6"

@dataclass
class MeasurementControlState:
    """Gestiona el estado de una mediciÃ³n activa (ej. secuencial)."""
    is_active: bool = False
    current_type: Optional[str] = None
    m_samples: int = 1
    p_measurements: int = 5
    current_m_count: int = 0
    current_p_count: int = 0
    accumulated_sub_samples_raw_lines: List[str] = field(default_factory=list)
    collected_final_sequential_points: List[Tuple] = field(default_factory=list)
    sequential_output_filename: Optional[str] = None
    sequential_initial_I0_line: Optional[str] = None
    sequential_subtraction_active_at_start: bool = False
