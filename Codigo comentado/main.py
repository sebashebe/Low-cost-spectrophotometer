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
Este es el archivo principal y punto de entrada de la aplicaciÃ³n del espectrofotÃ³metro.

Contiene la clase `SpectrometerApp` (QMainWindow), que construye y orquesta todos
los componentes de la interfaz grÃ¡fica, la lÃ³gica de negocio y la comunicaciÃ³n
con el hardware.
"""

import sys
import os
import serial
import serial.tools.list_ports
import time
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QLabel, QTextEdit, QMessageBox, QRadioButton, QSplitter, 
    QGridLayout, QLineEdit, QCheckBox, QAction, QMenuBar, QSizePolicy,
    QFrame, QScrollArea, QTabWidget
)
from PyQt5.QtCore import pyqtSlot, QThread, Qt, QTimer, QStandardPaths, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QPixmap

from constants import (
    WAVELENGTHS, WAVELENGTH_LABELS, DARK_STYLESHEET, LIGHT_STYLESHEET,
    CONTEXT_HELP_TEXTS
)
from workers import SerialWorker
from measurement_type import MeasurementType, PlotType, AppState
from help_dialog import HelpDialog
from utils import CollapsibleGroupBox
from concentration_curve_panel import ConcentrationCurvePanel
from calibration_curve_tab import CalibrationCurveTab
from main_spectrum_panel import MainSpectrumPanel
from app_state import (
    PlotOptionsState, MeasurementDataState, CalibrationState, 
    MeasurementControlState
)

from file_manager import FileManager
from calculation_controller import CalculationController

# --- Constantes de la aplicaciÃ³n ---
MAX_LOGO_WIDTH = 450
DIRECT_MEASUREMENT_TIMEOUT_MS = 7000
PORT_CHECK_INTERVAL_MS = 3000

class SpectrometerApp(QMainWindow):
    """
    Clase principal que define la ventana y la lÃ³gica central de la aplicaciÃ³n.
    """
    # SeÃ±al para enviar resultados de mediciones directas a los paneles que las soliciten.
    direct_measurement_signal = pyqtSignal(str, int, str, float, bool, str)

    def __init__(self):
        """Inicializador de la aplicaciÃ³n."""
        super().__init__()
        self.setWindowTitle("Software de EspectrofotÃ³metro AS726X")
        self.setGeometry(50, 50, 1750, 1050)

        # --- InicializaciÃ³n de Estados y Atributos ---
        self.app_state = AppState.IDLE
        self.current_theme_is_dark = True
        self.logo_label = None
        self.logo_dark_path = "BiomicrosystemsLogo_WhiteText.png"
        self.logo_light_path = "BiomicrosystemsLogo.png"
        self.startup_info_shown = False # Flag para mostrar el mensaje de bienvenida solo una vez.

        # Instancias de las clases de estado para una gestiÃ³n centralizada.
        self.plot_options = PlotOptionsState()
        self.data_state = MeasurementDataState()
        self.calibration_state = CalibrationState()
        self.measurement_control_state = MeasurementControlState()

        # Atributos para la comunicaciÃ³n serial y el hilo de trabajo.
        self.ser = None
        self.serial_thread = None
        self.serial_worker = None
        self.is_connected = False
        
        # Timers para tareas periÃ³dicas y timeouts.
        self.port_check_timer = QTimer(self)
        self.port_check_timer.timeout.connect(self._check_for_new_ports_and_autoconnect)
        self.last_known_ports_devices = []

        self.measurement_timeout_timer = QTimer(self)
        self.measurement_timeout_timer.setSingleShot(True)
        self.measurement_timeout_timer.timeout.connect(lambda: self._finish_current_measurement(timed_out=True))
        
        self.direct_measurement_timer = QTimer(self)
        self.direct_measurement_timer.setSingleShot(True)
        self.direct_measurement_timer.timeout.connect(self._handle_direct_measurement_timeout)
        self.direct_measurement_pending_request = None

        # Controladores para lÃ³gica de negocio encapsulada.
        self.file_manager = FileManager(self)
        self.calculation_controller = CalculationController(self)
        
        # Diccionario para manejar los comandos recibidos por el puerto serial.
        self.serial_handlers = {
            "calblanco": self._process_calblanco_data,
            "blanco": self._process_blanco_data,
            "medicion detenida": self._process_medicion_detenida_msg,
            "error": self._process_error_msg,
            "listo": lambda p, l: self._log("Dispositivo reporta estar listo."),
        }

        # InicializaciÃ³n de los paneles de la UI.
        self.right_tabs = None
        self.main_spectrum_panel = None
        self.concentration_curve_tab = None
        self.calibration_curve_abs_vs_conc_tab = None
        
        # --- ConstrucciÃ³n de la UI y Conexiones ---
        self._create_widgets()
        self._create_menu()
        self._create_layouts()
        self._connect_signals()

        # --- Estado Inicial de la AplicaciÃ³n ---
        self._apply_initial_theme()
        self._update_ui_state()
        self._populate_ports()
        self._update_numeric_displays()
        self._load_reference_calibration_params_for_wl()

        # Inicia la revisiÃ³n periÃ³dica de puertos.
        self.port_check_timer.start(PORT_CHECK_INTERVAL_MS)

    def _set_theme(self, is_dark: bool):
        """Aplica la hoja de estilos del tema (claro/oscuro) y notifica a los componentes."""
        self.current_theme_is_dark = is_dark
        stylesheet = DARK_STYLESHEET if is_dark else LIGHT_STYLESHEET
        QApplication.instance().setStyleSheet(stylesheet)

        self._log(f"Modo {'Oscuro' if is_dark else 'Claro'} Activado.")
        self._update_logo()
        
        # Notificar a cada panel para que actualice su propio tema.
        if self.main_spectrum_panel: self.main_spectrum_panel.on_theme_changed(is_dark)
        if self.concentration_curve_tab: self.concentration_curve_tab.on_theme_changed(is_dark)
        if self.calibration_curve_abs_vs_conc_tab: self.calibration_curve_abs_vs_conc_tab.on_theme_changed(is_dark)

        self._update_status_label_style()
        self.update()
        QApplication.processEvents()
        self._full_plot_update()

    def _manual_toggle_theme(self, checked: bool):
        """Slot para el menÃº de cambio de tema."""
        self._set_theme(checked)

    def _apply_initial_theme(self):
        """Aplica el tema por defecto al iniciar la aplicaciÃ³n."""
        if hasattr(self, 'dark_mode_action'):
            self.dark_mode_action.setChecked(self.current_theme_is_dark)
        self._set_theme(self.current_theme_is_dark)

    def _create_menu(self):
        """Construye y configura la barra de menÃº superior de la aplicaciÃ³n."""
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&Archivo')

        self.export_log_action = QAction('Exportar Log de ComunicaciÃ³n...', self)
        self.export_log_action.triggered.connect(self.file_manager.export_log)
        file_menu.addAction(self.export_log_action)

        self.export_graph_action_menu = QAction('Exportar GrÃ¡fico (PestaÃ±a Actual)...', self)
        self.export_graph_action_menu.triggered.connect(self.file_manager.export_graph_active_tab)
        file_menu.addAction(self.export_graph_action_menu)

        self.save_data_action_menu = QAction('Guardar Datos Acumulados (SesiÃ³n Espectro)...', self)
        self.save_data_action_menu.triggered.connect(self._save_session_data)
        file_menu.addAction(self.save_data_action_menu)

        self.save_superimposed_action_menu = QAction('Guardar SelecciÃ³n Superpuesta...', self)
        self.save_superimposed_action_menu.triggered.connect(self.file_manager.save_selected_superimposed_data)
        file_menu.addAction(self.save_superimposed_action_menu)

        self.clear_data_action_menu = QAction('Limpiar Datos en Memoria (SesiÃ³n Espectro)', self)
        self.clear_data_action_menu.triggered.connect(self._clear_session_data)
        file_menu.addAction(self.clear_data_action_menu)

        file_menu.addSeparator()
        exit_action = QAction('&Salir', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu('&Ver')
        self.dark_mode_action = QAction('Modo Oscuro', self)
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.triggered.connect(self._manual_toggle_theme)
        view_menu.addAction(self.dark_mode_action)

        tools_menu = menubar.addMenu('&Herramientas')
        self.goto_spectrum_tab_action = QAction('Ir a PestaÃ±a Espectro Principal', self)
        self.goto_spectrum_tab_action.triggered.connect(lambda: self.right_tabs.setCurrentWidget(self.main_spectrum_panel) if self.right_tabs else None)
        tools_menu.addAction(self.goto_spectrum_tab_action)

        self.goto_conc_curve_tab_action = QAction('Ir a PestaÃ±a Curva Conc. vs MediciÃ³n', self)
        self.goto_conc_curve_tab_action.triggered.connect(lambda: self.right_tabs.setCurrentWidget(self.concentration_curve_tab) if self.right_tabs else None)
        tools_menu.addAction(self.goto_conc_curve_tab_action)

        self.goto_calib_curve_tab_action = QAction('Ir a PestaÃ±a CalibraciÃ³n y Transferencia', self)
        self.goto_calib_curve_tab_action.triggered.connect(lambda: self.right_tabs.setCurrentWidget(self.calibration_curve_abs_vs_conc_tab) if self.right_tabs else None)
        tools_menu.addAction(self.goto_calib_curve_tab_action)

        help_menu = menubar.addMenu('A&yuda')
        help_action = QAction('Ver Ayuda General (Ãrbol)', self)
        help_action.setShortcut('F1')
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)

        help_menu.addSeparator()
        about_action = QAction('Acerca de EspectrofotÃ³metro AS726X', self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _create_widgets(self):
        """Crea todas las instancias de los widgets que componen la interfaz."""
        # --- Logo y Estado ---
        self.logo_label = QLabel(self)
        self.logo_label.setObjectName("logoLabel")
        self.logo_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.logo_label.setMinimumHeight(int(80 * 1.2))
        self.logo_label.setMaximumWidth(MAX_LOGO_WIDTH + 20)
        self.logo_label.setAlignment(Qt.AlignCenter)

        self.status_label = QLabel("Estado: Desconectado")
        self.status_label.setFont(self.status_label.font())
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # --- Grupo de ConexiÃ³n ---
        self.connection_group = CollapsibleGroupBox("ConexiÃ³n Serial", "connection", self, initial_state=True)
        self.port_label = QLabel("Puerto:")
        self.port_combo = QComboBox()
        self.refresh_button = QPushButton("Refrescar Puertos")
        self.connect_button = QPushButton("Conectar")
        self.disconnect_button = QPushButton("Desconectar")
        self.autoconnect_arduino_checkbox = QCheckBox("Autoconectar Arduino")
        self.autoconnect_arduino_checkbox.setChecked(False)

        # --- Grupo de MediciÃ³n ---
        self.unified_measurement_group = CollapsibleGroupBox("Control y ConfiguraciÃ³n de MediciÃ³n", "measurement", self, initial_state=True)
        self.calibrate_button = QPushButton("Medir Referencia (Iâ‚€)")
        self.measurement_type_label = QLabel("Tipo de MediciÃ³n:")
        self.measurement_type_combo = QComboBox()
        self.measurement_type_combo.addItems([MeasurementType.CONTINUOUS, MeasurementType.SINGLE_AVERAGED, MeasurementType.SEQUENTIAL])
        self.num_M_samples_label = QLabel("Espectros a promediar por mediciÃ³n (M):")
        self.num_M_samples_input = QLineEdit("1")
        self.num_M_samples_input.setValidator(QIntValidator(1, 10000, self))
        self.num_P_points_label = QLabel("NÃºmero total de mediciones finales (P):")
        self.num_P_points_input = QLineEdit("5")
        self.num_P_points_input.setValidator(QIntValidator(1, 10000, self))
        self.start_unified_measurement_button = QPushButton("Iniciar MediciÃ³n")
        self.stop_measurement_button = QPushButton("Detener MediciÃ³n")

        # --- Grupo de GestiÃ³n de Datos ---
        self.data_group = CollapsibleGroupBox("GestiÃ³n de Datos", "data_management", self, initial_state=False)
        self.save_button = QPushButton("Guardar Datos Acumulados (SesiÃ³n Espectro)")
        self.save_superimposed_button = QPushButton("Guardar SelecciÃ³n Superpuesta")
        self.clear_button = QPushButton("Limpiar Datos en Memoria (SesiÃ³n Espectro)")
        self.export_graph_button = QPushButton("Exportar GrÃ¡fico (PestaÃ±a Actual)")
        
        # --- Grupo de Display NumÃ©rico ---
        self.numeric_display_group = CollapsibleGroupBox("Ãšltimos Valores Registrados", "numeric_display", self, initial_state=False)
        self.cal_labels, self.cal_values_labels, self.meas_values_labels = [], [], []
        for label_text in WAVELENGTH_LABELS:
            self.cal_labels.append(QLabel(f"{label_text.split(' ')[0]}:"))
            self.cal_values_labels.append(QLabel("N/A"))
            self.meas_values_labels.append(QLabel("N/A"))

        # --- Grupo de CÃ¡lculo de ConcentraciÃ³n ---
        self.concentration_calc_group = CollapsibleGroupBox("CÃ¡lculo de ConcentraciÃ³n", "beer_lambert", self, initial_state=True)
        self.epsilon_label = QLabel("Coef. Absortividad Molar SesiÃ³n (Îµ):")
        self.epsilon_input = QLineEdit()
        self.epsilon_input.setValidator(QDoubleValidator(0, 1e9, 6, self))
        self.path_length_label = QLabel("Camino Ã“ptico SesiÃ³n (b, cm):")
        self.path_length_input = QLineEdit(self.calibration_state.path_length_session)
        self.path_length_input.setValidator(QDoubleValidator(0.01, 100, 2, self))
        self.beer_wavelength_label = QLabel("Longitud de Onda para CÃ¡lculo:")
        self.beer_wavelength_combo = QComboBox()
        for i, label in enumerate(WAVELENGTH_LABELS):
            self.beer_wavelength_combo.addItem(label, WAVELENGTHS[i])
        self.use_session_cal_curve_checkbox = QCheckBox("Usar Curva de SesiÃ³n (A_custom vs C)")
        self.use_transfer_model_checkbox = QCheckBox("Usar Ajuste con Modelo de Transferencia")
        self.use_transfer_model_checkbox.setToolTip("Si estÃ¡ marcado, usa A_custom, el modelo de transferencia (A_ref vs A_custom)\ny una calibraciÃ³n de referencia (A_ref vs C) para calcular la concentraciÃ³n.")
        self.calculate_concentration_button = QPushButton("Calcular y Registrar ConcentraciÃ³n")
        self.calculated_concentration_label = QLabel("ConcentraciÃ³n Calculada (C): N/A")
        self.calculated_abs_custom_label = QLabel("A_custom (@Î»): N/A")
        self.calculated_abs_adjusted_label = QLabel("A_ajustada (@Î»): N/A")

        # --- Grupo de CalibraciÃ³n de Referencia ---
        self.ref_cal_params_group = CollapsibleGroupBox("Configurar CalibraciÃ³n de Referencia", "ref_cal_config_group", self, initial_state=False)
        self.ref_cal_wl_label = QLabel("Longitud de Onda para ParÃ¡metros Ref:")
        self.ref_cal_wl_combo = QComboBox()
        for i, label in enumerate(WAVELENGTH_LABELS):
            self.ref_cal_wl_combo.addItem(label, WAVELENGTHS[i])
        self.ref_cal_type_label = QLabel("Tipo de CalibraciÃ³n de Referencia:")
        self.ref_cal_type_curve_radio = QRadioButton("Curva: A_ref = mC + b")
        self.ref_cal_type_factor_radio = QRadioButton("Factor: A_ref = (ÎµL)C")
        self.ref_cal_type_curve_radio.setChecked(True)
        self.ref_cal_m_label = QLabel("Pendiente Ref. (m_ref):")
        self.ref_cal_m_input = QLineEdit()
        self.ref_cal_m_input.setValidator(QDoubleValidator(-1e9, 1e9, 6, self))
        self.ref_cal_b_label = QLabel("Intercepto Ref. (b_ref):")
        self.ref_cal_b_input = QLineEdit()
        self.ref_cal_b_input.setValidator(QDoubleValidator(-1e9, 1e9, 6, self))
        self.ref_cal_epsilon_l_label = QLabel("Factor Ref. (ÎµL)_ref:")
        self.ref_cal_epsilon_l_input = QLineEdit()
        self.ref_cal_epsilon_l_input.setValidator(QDoubleValidator(0, 1e9, 6, self))
        self.save_ref_cal_params_button = QPushButton("Guardar ParÃ¡metros de Referencia para esta Î»")
        self.current_ref_cal_params_display_label = QLabel("ParÃ¡metros Ref. Guardados (Î» actual): Ninguno")
        self.current_ref_cal_params_display_label.setWordWrap(True)

        # --- Grupo de SustracciÃ³n de Blanco ---
        self.blank_subtraction_group = CollapsibleGroupBox("SustracciÃ³n de Blanco (con Iâ‚€)", "blank_subtraction", self, initial_state=False)
        self.enable_I0_blank_subtraction_checkbox = QCheckBox("Activar SustracciÃ³n de Blanco (con Iâ‚€)")
        self.blank_status_label = QLabel("Referencia Iâ‚€ no medida.")

        # --- Log de Eventos ---
        self.log_group = CollapsibleGroupBox("Log de ComunicaciÃ³n y Eventos", "log_display", self, initial_state=True)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setLineWrapMode(QTextEdit.WidgetWidth)

        # --- PestaÃ±as de la Derecha ---
        self.right_tabs = QTabWidget()
        self.right_tabs.setTabPosition(QTabWidget.North)
        
        self.main_spectrum_panel = MainSpectrumPanel(parent_app=self)
        self.concentration_curve_tab = ConcentrationCurvePanel(parent_app=self)
        self.calibration_curve_abs_vs_conc_tab = CalibrationCurveTab(parent_app=self)

    def _update_logo(self):
        """Carga y escala el logo apropiado para el tema actual."""
        if self.logo_label:
            try:
                logo_path_to_use = self.logo_dark_path if self.current_theme_is_dark else self.logo_light_path
                script_dir = os.path.dirname(os.path.abspath(__file__))
                full_logo_path = os.path.join(script_dir, logo_path_to_use)

                if not os.path.exists(full_logo_path):
                    self._log(f"Advertencia: No se pudo cargar el logo: {full_logo_path}", is_error=True)
                    self.logo_label.setText(f"Logo '{os.path.basename(logo_path_to_use)}' no encontrado")
                    return

                original_pixmap = QPixmap(full_logo_path)
                if original_pixmap.isNull():
                    self._log(f"Advertencia: Pixmap del logo es nulo: {full_logo_path}", is_error=True)
                    self.logo_label.setText("Error al cargar Logo")
                    return

                current_label_width = self.logo_label.width()
                effective_scale_width = min(current_label_width, MAX_LOGO_WIDTH)
                scaled_pixmap = original_pixmap.scaledToWidth(effective_scale_width, Qt.SmoothTransformation)
                self.logo_label.setPixmap(scaled_pixmap)
            except Exception as e:
                self._log(f"Error al actualizar el logo: {e}", is_error=True)
                self.logo_label.setText("Error de Logo")

    def resizeEvent(self, event):
        """Se activa al cambiar el tamaÃ±o de la ventana para reescalar el logo."""
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_logo)

    def showEvent(self, event):
        """Se activa cuando la ventana se muestra por primera vez para cargar el logo y mostrar el mensaje inicial."""
        super().showEvent(event)
        QTimer.singleShot(50, self._update_logo)
        if not self.startup_info_shown:
            QTimer.singleShot(100, self._show_startup_info)
            self.startup_info_shown = True

    def _show_startup_info(self):
        """Muestra una ventana emergente con informaciÃ³n sobre el cierre de la aplicaciÃ³n."""
        QMessageBox.information(self, "InformaciÃ³n Importante",
                                """
                                <h3>Bienvenido al Software del EspectrofotÃ³metro</h3>
                                <p><b>Nota sobre el cierre de la aplicaciÃ³n:</b></p>
                                <p>Si intenta cerrar la aplicaciÃ³n mientras una mediciÃ³n estÃ¡ en curso (por ejemplo, en modo "Continuo"), se le pedirÃ¡ confirmaciÃ³n para detener la tarea.</p>
                                <p>Es importante que haga clic en "SÃ­" para permitir que la aplicaciÃ³n detenga la comunicaciÃ³n con el dispositivo de forma segura antes de cerrar. De lo contrario, la aplicaciÃ³n podrÃ­a no responder.</p>
                                <p>El cierre seguro garantiza que el puerto de comunicaciÃ³n quede liberado correctamente.</p>
                                """)

    def _create_layouts(self):
        """Ensambla todos los widgets creados en la disposiciÃ³n final de la ventana."""
        # --- Contenido Fijo Superior Izquierdo (Logo y Estado) ---
        fixed_top_left_widget = QWidget()
        fixed_top_left_layout = QVBoxLayout(fixed_top_left_widget)
        fixed_top_left_layout.setContentsMargins(5, 5, 5, 5)
        fixed_top_left_layout.setSpacing(5)
        fixed_top_left_layout.addWidget(self.logo_label)
        fixed_top_left_layout.addWidget(self.status_label)
        fixed_top_left_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # --- Llenado de los GroupBox con sus widgets ---
        connection_content_layout = QGridLayout(self.connection_group.content_widget)
        connection_content_layout.addWidget(self.port_label, 0, 0)
        connection_content_layout.addWidget(self.port_combo, 0, 1, 1, 2)
        connection_content_layout.addWidget(self.refresh_button, 1, 0)
        connection_content_layout.addWidget(self.connect_button, 1, 1)
        connection_content_layout.addWidget(self.disconnect_button, 1, 2)
        connection_content_layout.addWidget(self.autoconnect_arduino_checkbox, 2, 0, 1, 3)
        connection_content_layout.setColumnStretch(1, 1)

        unified_measurement_content_layout = QGridLayout(self.unified_measurement_group.content_widget)
        unified_measurement_content_layout.addWidget(self.calibrate_button, 0, 0, 1, 3)
        unified_measurement_content_layout.addWidget(self.measurement_type_label, 1, 0)
        unified_measurement_content_layout.addWidget(self.measurement_type_combo, 1, 1, 1, 2)
        unified_measurement_content_layout.addWidget(self.num_M_samples_label, 2, 0)
        unified_measurement_content_layout.addWidget(self.num_M_samples_input, 2, 1, 1, 2)
        unified_measurement_content_layout.addWidget(self.num_P_points_label, 3, 0)
        unified_measurement_content_layout.addWidget(self.num_P_points_input, 3, 1, 1, 2)
        start_stop_layout_meas = QHBoxLayout()
        start_stop_layout_meas.addWidget(self.start_unified_measurement_button)
        start_stop_layout_meas.addWidget(self.stop_measurement_button)
        unified_measurement_content_layout.addLayout(start_stop_layout_meas, 4, 0, 1, 3)

        data_content_layout = QVBoxLayout(self.data_group.content_widget)
        data_content_layout.addWidget(self.save_button)
        data_content_layout.addWidget(self.save_superimposed_button)
        data_content_layout.addWidget(self.clear_button)
        data_content_layout.addWidget(self.export_graph_button)

        numeric_content_layout = QGridLayout(self.numeric_display_group.content_widget)
        numeric_content_layout.addWidget(QLabel("<b>Longitud de Onda:</b>"), 0, 0, alignment=Qt.AlignLeft)
        numeric_content_layout.addWidget(QLabel("<b>Ref (Iâ‚€):</b>"), 0, 1, alignment=Qt.AlignCenter)
        numeric_content_layout.addWidget(QLabel("<b>Med (I):</b>"), 0, 2, alignment=Qt.AlignCenter)
        for i in range(len(WAVELENGTH_LABELS)):
            numeric_content_layout.addWidget(self.cal_labels[i], i + 1, 0)
            numeric_content_layout.addWidget(self.cal_values_labels[i], i + 1, 1, alignment=Qt.AlignCenter)
            numeric_content_layout.addWidget(self.meas_values_labels[i], i + 1, 2, alignment=Qt.AlignCenter)
        numeric_content_layout.setColumnStretch(0, 0)
        numeric_content_layout.setColumnStretch(1, 1)
        numeric_content_layout.setColumnStretch(2, 1)

        conc_calc_content_grid = QGridLayout(self.concentration_calc_group.content_widget)
        conc_calc_content_grid.addWidget(self.epsilon_label, 0, 0)
        conc_calc_content_grid.addWidget(self.epsilon_input, 0, 1)
        conc_calc_content_grid.addWidget(self.path_length_label, 1, 0)
        conc_calc_content_grid.addWidget(self.path_length_input, 1, 1)
        conc_calc_content_grid.addWidget(self.beer_wavelength_label, 2, 0)
        conc_calc_content_grid.addWidget(self.beer_wavelength_combo, 2, 1)
        conc_calc_content_grid.addWidget(self.use_session_cal_curve_checkbox, 3, 0, 1, 2)
        conc_calc_content_grid.addWidget(self.use_transfer_model_checkbox, 4, 0, 1, 2)
        conc_calc_content_grid.addWidget(self.calculate_concentration_button, 5, 0, 1, 2)
        conc_calc_content_grid.addWidget(self.calculated_concentration_label, 6, 0, 1, 2)
        conc_calc_content_grid.addWidget(self.calculated_abs_custom_label, 7, 0, 1, 2)
        conc_calc_content_grid.addWidget(self.calculated_abs_adjusted_label, 8, 0, 1, 2)

        ref_cal_content_grid = QGridLayout(self.ref_cal_params_group.content_widget)
        ref_cal_content_grid.addWidget(self.ref_cal_wl_label, 0, 0)
        ref_cal_content_grid.addWidget(self.ref_cal_wl_combo, 0, 1)
        ref_cal_content_grid.addWidget(self.ref_cal_type_label, 1, 0, 1, 2)
        ref_cal_type_layout = QHBoxLayout()
        ref_cal_type_layout.addWidget(self.ref_cal_type_curve_radio)
        ref_cal_type_layout.addWidget(self.ref_cal_type_factor_radio)
        ref_cal_type_layout.addStretch()
        ref_cal_content_grid.addLayout(ref_cal_type_layout, 2, 0, 1, 2)
        ref_cal_content_grid.addWidget(self.ref_cal_m_label, 3, 0)
        ref_cal_content_grid.addWidget(self.ref_cal_m_input, 3, 1)
        ref_cal_content_grid.addWidget(self.ref_cal_b_label, 4, 0)
        ref_cal_content_grid.addWidget(self.ref_cal_b_input, 4, 1)
        ref_cal_content_grid.addWidget(self.ref_cal_epsilon_l_label, 5, 0)
        ref_cal_content_grid.addWidget(self.ref_cal_epsilon_l_input, 5, 1)
        ref_cal_content_grid.addWidget(self.save_ref_cal_params_button, 6, 0, 1, 2)
        ref_cal_content_grid.addWidget(self.current_ref_cal_params_display_label, 7, 0, 1, 2)
        self._toggle_ref_cal_inputs()
        
        blank_sub_content_layout = QVBoxLayout(self.blank_subtraction_group.content_widget)
        blank_sub_content_layout.addWidget(self.enable_I0_blank_subtraction_checkbox)
        blank_sub_content_layout.addWidget(self.blank_status_label)
        
        log_content_main_layout = QVBoxLayout(self.log_group.content_widget)
        log_content_main_layout.addWidget(self.log_output)
        self.log_group.setMinimumHeight(150)
        
        # --- Ãrea de Scroll para la columna de controles ---
        left_scrollable_content_widget = QWidget()
        left_scrollable_layout = QVBoxLayout(left_scrollable_content_widget)
        left_scrollable_layout.setSpacing(10)
        left_scrollable_layout.addWidget(self.connection_group)
        left_scrollable_layout.addWidget(self.unified_measurement_group)
        left_scrollable_layout.addWidget(self.data_group)
        left_scrollable_layout.addWidget(self.numeric_display_group)
        left_scrollable_layout.addWidget(self.concentration_calc_group)
        left_scrollable_layout.addWidget(self.ref_cal_params_group)
        left_scrollable_layout.addWidget(self.blank_subtraction_group)
        left_scrollable_layout.addStretch(1)

        left_scroll_area = QScrollArea()
        left_scroll_area.setWidgetResizable(True)
        left_scroll_area.setWidget(left_scrollable_content_widget)
        left_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll_area.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        left_scroll_area.setMinimumWidth(480)
        left_scroll_area.setMaximumWidth(600)

        # --- Ensamblaje de la Columna Izquierda ---
        main_left_column_widget = QWidget()
        main_left_column_layout = QVBoxLayout(main_left_column_widget)
        main_left_column_layout.setContentsMargins(0,0,0,0)
        main_left_column_layout.setSpacing(0)
        main_left_column_layout.addWidget(fixed_top_left_widget)
        main_left_column_layout.addWidget(left_scroll_area)
        main_left_column_layout.setStretchFactor(fixed_top_left_widget, 0)
        main_left_column_layout.setStretchFactor(left_scroll_area, 1)

        # --- Llenado de las PestaÃ±as de la Derecha ---
        self.right_tabs.addTab(self.main_spectrum_panel, "Espectro Principal")
        self.right_tabs.addTab(self.concentration_curve_tab, "Curva Conc. vs MediciÃ³n")
        self.right_tabs.addTab(self.calibration_curve_abs_vs_conc_tab, "CalibraciÃ³n y Transferencia")

        # --- Ensamblaje de la Columna Derecha (PestaÃ±as y Log) ---
        right_column_splitter = QSplitter(Qt.Vertical)
        right_column_splitter.addWidget(self.right_tabs)
        right_column_splitter.addWidget(self.log_group)
        right_column_splitter.setStretchFactor(0, 4)
        right_column_splitter.setStretchFactor(1, 1)
        right_column_splitter.setSizes([750, 200])

        # --- Ensamblaje Final de la Ventana Principal ---
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(main_left_column_widget)
        main_splitter.addWidget(right_column_splitter)
        main_splitter.setStretchFactor(0, 0) # La columna izquierda no se estira
        main_splitter.setStretchFactor(1, 1) # La columna derecha sÃ­
        main_splitter.setSizes([left_scroll_area.minimumWidth() + 20, 1200])

        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.addWidget(main_splitter)
        self.setCentralWidget(central_widget)

    def _connect_signals(self):
        """Conecta todas las seÃ±ales de la UI a sus respectivos slots (manejadores)."""
        # --- Conexiones de la LÃ³gica Principal ---
        self.refresh_button.clicked.connect(self._populate_ports)
        self.connect_button.clicked.connect(self._connect_serial)
        self.disconnect_button.clicked.connect(self._disconnect_serial)

        self.calibrate_button.clicked.connect(self._measure_reference_i0)
        self.measurement_type_combo.currentTextChanged.connect(self._toggle_measurement_config_widgets)
        self.start_unified_measurement_button.clicked.connect(self._start_unified_measurement)
        self.stop_measurement_button.clicked.connect(self._stop_current_measurement)

        self.save_button.clicked.connect(self._save_session_data)
        self.save_superimposed_button.clicked.connect(self.file_manager.save_selected_superimposed_data)
        self.clear_button.clicked.connect(self._clear_session_data)
        self.export_graph_button.clicked.connect(self.file_manager.export_graph_active_tab)

        # --- Conexiones de la LÃ³gica de CÃ¡lculo de ConcentraciÃ³n ---
        self.calculate_concentration_button.clicked.connect(self._on_calculate_and_register_concentration_clicked)
        self.use_session_cal_curve_checkbox.stateChanged.connect(self._on_concentration_config_changed)
        self.use_transfer_model_checkbox.stateChanged.connect(self._on_concentration_config_changed)
        self.epsilon_input.textChanged.connect(self._on_concentration_config_changed)
        self.path_length_input.textChanged.connect(self._on_concentration_config_changed)
        self.beer_wavelength_combo.currentIndexChanged.connect(self._on_concentration_config_changed)

        self.ref_cal_wl_combo.currentIndexChanged.connect(self._load_reference_calibration_params_for_wl)
        self.ref_cal_type_curve_radio.toggled.connect(self._toggle_ref_cal_inputs)
        self.save_ref_cal_params_button.clicked.connect(self._save_reference_calibration_params)
        
        self.enable_I0_blank_subtraction_checkbox.toggled.connect(self._on_I0_blank_subtraction_toggled)
        
        # --- Conexiones de los Paneles (PestaÃ±as) ---
        self.main_spectrum_panel.plotTypeChanged.connect(self._on_plot_type_changed)
        self.main_spectrum_panel.superimposeSelectionChanged.connect(self._on_superimpose_selection_changed)
        self.main_spectrum_panel.logScaleYChanged.connect(self._on_log_scale_y_toggled)
        self.main_spectrum_panel.showMarkersChanged.connect(self._on_show_markers_toggled)
        self.main_spectrum_panel.showI0Changed.connect(self._on_show_I0_toggled)
        
        self.concentration_curve_tab.logMessage.connect(self._log)
        self.concentration_curve_tab.requestMeasurement.connect(self.request_single_value_measurement)
        
        self.calibration_curve_abs_vs_conc_tab.logMessage.connect(self._log)
        self.calibration_curve_abs_vs_conc_tab.requestMeasurement.connect(self.request_single_value_measurement)
        self.calibration_curve_abs_vs_conc_tab.calibrationApplied.connect(self._on_calibration_applied)
        self.calibration_curve_abs_vs_conc_tab.transferModelApplied.connect(self._on_transfer_model_applied)
        self.calibration_curve_abs_vs_conc_tab.transferModelCleared.connect(self.clear_active_transfer_model)

        # --- ConexiÃ³n para mediciones directas solicitadas por los paneles ---
        self.direct_measurement_signal.connect(self.concentration_curve_tab.handle_direct_measurement_result)
        self.direct_measurement_signal.connect(self.calibration_curve_abs_vs_conc_tab.handle_direct_measurement_result)

        # InicializaciÃ³n del estado de la UI.
        self._toggle_measurement_config_widgets()
        self.calculation_controller.update_display_only()
    
    @pyqtSlot(PlotType)
    def _on_plot_type_changed(self, plot_type_enum):
        """Slot que se activa al cambiar el tipo de grÃ¡fico. Actualiza el estado y redibuja."""
        self.plot_options.main_plot_type = plot_type_enum
        self._full_plot_update()
        self.calculation_controller.update_display_only()

    @pyqtSlot(list)
    def _on_superimpose_selection_changed(self, labels: list):
        """Slot que se activa al cambiar la selecciÃ³n de espectros a superponer."""
        self.plot_options.superimposed_spectra_labels = labels
        self._full_plot_update()
        self._update_ui_state()

    @pyqtSlot(bool)
    def _on_log_scale_y_toggled(self, checked: bool):
        """Slot para activar/desactivar la escala logarÃ­tmica en el grÃ¡fico."""
        self.plot_options.use_log_scale_y = checked
        self._full_plot_update()

    @pyqtSlot(bool)
    def _on_show_markers_toggled(self, checked: bool):
        """Slot para mostrar/ocultar los marcadores de puntos en el grÃ¡fico."""
        self.plot_options.show_markers = checked
        self._full_plot_update()

    @pyqtSlot(bool)
    def _on_show_I0_toggled(self, checked: bool):
        """Slot para mostrar/ocultar la lÃ­nea de referencia I0 en el grÃ¡fico de intensidad."""
        self.plot_options.show_I0_on_intensity_graph = checked
        self._full_plot_update()

    @pyqtSlot(dict)
    def _on_calibration_applied(self, params: dict):
        """Slot que recibe y aplica una nueva curva de calibraciÃ³n de sesiÃ³n."""
        self.set_active_calibration_curve(params['slope'], params['intercept'], params['r_squared'], params['wavelength_nm'])
    
    @pyqtSlot(dict)
    def _on_transfer_model_applied(self, params: dict):
        """Slot que recibe y aplica un nuevo modelo de transferencia."""
        self.set_active_transfer_model(params['slope_t'], params['intercept_t'], params['r_sq_t'], params['wavelength_nm'])
        
    def _on_concentration_config_changed(self):
        """Slot que gestiona la lÃ³gica y dependencias de las opciones de cÃ¡lculo de concentraciÃ³n."""
        # Asegura que solo una de las casillas (curva de sesiÃ³n o modelo de transferencia) estÃ© activa a la vez.
        if self.sender() == self.use_session_cal_curve_checkbox and self.use_session_cal_curve_checkbox.isChecked():
            if self.use_transfer_model_checkbox.isChecked():
                self.use_transfer_model_checkbox.setChecked(False)
        elif self.sender() == self.use_transfer_model_checkbox and self.use_transfer_model_checkbox.isChecked():
            if self.use_session_cal_curve_checkbox.isChecked():
                self.use_session_cal_curve_checkbox.setChecked(False)
        
        # Guarda los valores de Îµ y b en el estado de la aplicaciÃ³n.
        self.calibration_state.epsilon_session = self.epsilon_input.text()
        self.calibration_state.path_length_session = self.path_length_input.text()

        self.calculation_controller.update_display_only()
        self._update_ui_state()
    
    def _populate_ports(self, called_by_timer=False):
        """Busca los puertos seriales disponibles y los aÃ±ade al ComboBox."""
        if self.is_connected and called_by_timer:
            return 
        current_selection_text = self.port_combo.currentText()
        self.port_combo.clear()
        ports = sorted(list(serial.tools.list_ports.comports()))
        if not ports:
            self.port_combo.addItem("No hay puertos disponibles")
            self.last_known_ports_devices = []
            self._update_ui_state()
            return

        self.port_combo.setEnabled(True)
        selected_port_text_to_restore = None
        arduino_port_devices = [] 
        # Palabras clave para identificar dispositivos tipo Arduino.
        arduino_keywords = ["arduino", "ch340", "cp210x", "usb serial", "ttl232r", "uart", "usb-serial", "ftdi", "vcp", "serial port"]
        arduino_ports_display = []
        other_ports_display = []
        new_port_devices_this_scan = [p.device for p in ports]
        self.last_known_ports_devices = new_port_devices_this_scan 

        for p in ports:
            port_desc_full = f"{p.device} - {p.description}"
            description_lower = (p.description or "").lower()
            manufacturer_lower = (p.manufacturer or "").lower()
            product_lower = (p.product or "").lower()
            is_arduino_like = any(keyword in description_lower or \
                                  keyword in manufacturer_lower or \
                                  keyword in product_lower for keyword in arduino_keywords)
            if is_arduino_like:
                arduino_ports_display.append(port_desc_full)
                arduino_port_devices.append(p.device) 
            else:
                other_ports_display.append(port_desc_full)
        
        # AÃ±ade los puertos de Arduino primero a la lista para mayor conveniencia.
        for port_desc in arduino_ports_display:
            self.port_combo.addItem(port_desc)
            if port_desc == current_selection_text: 
                selected_port_text_to_restore = port_desc
        for port_desc in other_ports_display:
            self.port_combo.addItem(port_desc)
            if port_desc == current_selection_text and selected_port_text_to_restore is None:
                selected_port_text_to_restore = port_desc

        if selected_port_text_to_restore:
            self.port_combo.setCurrentText(selected_port_text_to_restore)
        elif self.port_combo.count() > 0:
            self.port_combo.setCurrentIndex(0) 

        self._update_ui_state()
        return arduino_port_devices
    
    def _check_for_new_ports_and_autoconnect(self):
        """Revisa periÃ³dicamente si se han conectado o desconectado puertos seriales."""
        if self.is_connected or self.app_state != AppState.IDLE:
            return 
        current_ports_info = serial.tools.list_ports.comports()
        current_port_devices_str = sorted([p.device for p in current_ports_info])
        if current_port_devices_str != sorted(self.last_known_ports_devices):
            self._log("Cambio detectado en puertos seriales. Actualizando lista...", is_debug=True)
            detected_arduino_devices = self._populate_ports(called_by_timer=True)
            # Intenta autoconectar si la opciÃ³n estÃ¡ marcada y se detecta un Arduino.
            if self.autoconnect_arduino_checkbox.isChecked() and not self.is_connected:
                if detected_arduino_devices:
                    target_device_to_autoconnect = detected_arduino_devices[0]
                    self._log(f"AutoconexiÃ³n habilitada. Intentando conectar a Arduino en: {target_device_to_autoconnect}", is_debug=True)
                    items = [self.port_combo.itemText(i) for i in range(self.port_combo.count())]
                    target_item_text = next((item for item in items if target_device_to_autoconnect in item), None)
                    if target_item_text:
                        self.port_combo.setCurrentText(target_item_text)
                        self._connect_serial() 
        self.last_known_ports_devices = current_port_devices_str

    def _connect_serial(self):
        """Establece la conexiÃ³n serial con el dispositivo e inicia el hilo de lectura."""
        if self.is_connected:
            self._log("Ya estÃ¡ conectado.")
            return
        selected_text = self.port_combo.currentText()
        if not selected_text or "No hay puertos" in selected_text:
            self._show_error("Seleccione un puerto vÃ¡lido.")
            return

        port_name = selected_text.split(" - ")[0] 
        try:
            self._log(f"Intentando conectar a {port_name}...")
            self.connect_button.setEnabled(False)
            QApplication.processEvents() 

            # Inicia la instancia serial y espera a que el dispositivo (Arduino) se reinicie.
            self.ser = serial.Serial(port_name, 115200, timeout=1.0, write_timeout=1.0) 
            self._log("Esperando posible reinicio del dispositivo (2s)...")
            QThread.msleep(2000) 

            if self.ser.is_open: 
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer() 
                self.is_connected = True
                self._update_status_label("Conectado", "success")
                
                # Configura e inicia el worker en un hilo separado para la lectura asÃ­ncrona.
                self.serial_worker = SerialWorker(self.ser)
                self.serial_thread = QThread(self) 
                self.serial_worker.moveToThread(self.serial_thread)
                
                self.serial_worker.data_received.connect(self._handle_serial_data)
                self.serial_worker.error_occurred.connect(self._handle_serial_error_message)
                self.serial_worker.connection_lost.connect(self._handle_connection_lost)
                self.serial_worker.finished.connect(self._on_worker_finished) 
                
                self.serial_thread.started.connect(self.serial_worker.run) 
                self.serial_thread.finished.connect(self.serial_worker.deleteLater)
                self.serial_thread.finished.connect(self.serial_thread.deleteLater)
                self.serial_thread.start() 
                
                self._log("Hilo de lectura serial iniciado.")
                self._clear_session_data_internal(log=False) 
        except (serial.SerialException, Exception) as e:
            self._show_error(f"Error al conectar a {port_name}: {e}")
            if self.ser and self.ser.is_open: self.ser.close()
            self.ser = None
            self.is_connected = False
            self._update_status_label("Error ConexiÃ³n", "error")
        finally:
            self._update_ui_state()
            
    def _disconnect_serial(self, due_to_error=False):
        """Inicia el proceso de desconexiÃ³n del puerto serial."""
        if not self.is_connected and not due_to_error:
            if not due_to_error: self._log("Ya estÃ¡ desconectado.")
            return 
        self._log("Desconectando..." if not due_to_error else "DesconexiÃ³n forzada por error...")
        
        # Si hay una mediciÃ³n en curso, la detiene primero.
        if self.app_state == AppState.MEASURING_MAIN:
             self._finish_current_measurement(manual_stop=True, success=False)
        if self.app_state == AppState.MEASURING_DIRECT:
            self._handle_direct_measurement_timeout("DesconexiÃ³n del dispositivo.")
        
        # Llama a la desconexiÃ³n real con un pequeÃ±o retraso para permitir que se procesen los eventos.
        QTimer.singleShot(50, lambda: self._perform_actual_disconnect(due_to_error))

    def _perform_actual_disconnect(self, due_to_error=False):
        """Realiza la desconexiÃ³n efectiva, deteniendo el hilo y cerrando el puerto."""
        if self.serial_worker:
            self.serial_worker.stop() 
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.quit() 
            if not self.serial_thread.wait(1500): 
                self._log("Advertencia: El hilo serial no terminÃ³ limpiamente.", is_error=True)
                self.serial_thread.terminate() 
                self.serial_thread.wait()

        if self.ser and self.ser.is_open:
            try:
                if not due_to_error: self._send_command_direct("detener")
                self.ser.close()
            except Exception as e:
                self._log(f"Error al cerrar el puerto serial: {e}", is_error=True)

        self.ser = None
        self.is_connected = False
        self.app_state = AppState.IDLE

        if not due_to_error:
            self._update_status_label("Desconectado", "warning")
        else:
             if "Error" not in self.status_label.text() and "Perdida" not in self.status_label.text():
                 self._update_status_label("Desconectado (Error)", "error")
        
        self._update_ui_state()
        self._log("DesconexiÃ³n completada.")

    @pyqtSlot(str)
    def _handle_serial_error_message(self, error_message: str):
        """Slot que registra los errores reportados por el SerialWorker."""
        self._log(f"Error reportado por SerialWorker: {error_message}", is_error=True)

    @pyqtSlot()
    def _handle_connection_lost(self):
        """Slot que se activa cuando el worker detecta que la conexiÃ³n se ha perdido."""
        self._log("SeÃ±al de conexiÃ³n perdida recibida del worker.", is_error=True)
        if self.is_connected: 
            self._show_error("Se perdiÃ³ la conexiÃ³n con el dispositivo.")
            self._update_status_label("Error ConexiÃ³n Perdida", "error")
            self._disconnect_serial(due_to_error=True) 
        else: 
            self._update_ui_state()

    @pyqtSlot()
    def _on_worker_finished(self):
        """Slot que se activa cuando el hilo del worker termina su ejecuciÃ³n."""
        self._log("Hilo de lectura serial terminado (worker.finished signal).")
        # Si el worker termina inesperadamente mientras la app cree que estÃ¡ conectada, fuerza la desconexiÃ³n.
        if self.is_connected and (not self.serial_worker or not self.serial_worker._running):
            self._handle_connection_lost()
            
    def _send_command_direct(self, command: str) -> bool:
        """EnvÃ­a un comando directamente al puerto serial sin las validaciones de _send_command."""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{command}\n".encode('utf-8'))
                self.ser.flush() 
                return True
            except (serial.SerialTimeoutException, OSError):
                return False
        return False

    def _send_command(self, command: str) -> bool:
        """Valida la conexiÃ³n y envÃ­a un comando al dispositivo, registrÃ¡ndolo en el log."""
        if not self.is_connected or not self.ser or not self.ser.is_open:
            self._log(f"Error: No conectado. No se puede enviar comando: {command}", is_error=True)
            return False
        try:
            self.ser.write(f"{command}\n".encode('utf-8'))
            self.ser.flush()
            self._log(f"TX: {command}")
            return True
        except serial.SerialTimeoutException:
            self._log(f"Error: Timeout al escribir comando '{command}' en puerto serial.", is_error=True)
            self._show_error(f"Timeout al enviar comando '{command}'. Verifique la conexiÃ³n.")
            self._handle_connection_lost()
            return False
        except Exception as e:
            self._log(f"Error al enviar comando '{command}': {e}", is_error=True)
            self._show_error(f"Error al enviar comando: {e}")
            return False

    @pyqtSlot(str)
    def _handle_serial_data(self, raw_line: str):
        """Procesa una lÃ­nea de datos recibida desde el puerto serial y la enruta al manejador apropiado."""
        log_rx_as_debug = "blanco" in raw_line.lower() and self.app_state != AppState.IDLE
        self._log(f"RX: {raw_line}", is_debug=log_rx_as_debug)
        
        parts = raw_line.strip().split(',')
        if not parts: return

        command_type = parts[0].lower()
        # Si se estÃ¡ esperando una mediciÃ³n directa, se usa un procesador especÃ­fico.
        if self.app_state == AppState.MEASURING_DIRECT:
            self._process_direct_measurement_data(command_type, parts, raw_line)
            return

        # Enruta el comando al manejador correspondiente del diccionario `serial_handlers`.
        handler = self.serial_handlers.get(command_type)
        if handler:
            handler(parts, raw_line)
        elif "as726x espectrofotometro listo" in raw_line.lower():
            self._log("Dispositivo reporta estar listo.")
        else:
            self._log(f"Mensaje desconocido del dispositivo: {raw_line}", is_debug=True)

    def _process_error_msg(self, parts: list[str], raw_line: str):
        """Procesa un mensaje de error explÃ­cito enviado por el dispositivo."""
        if len(parts) > 1:
            error_msg_device = ",".join(parts[1:])
            self._show_error(f"Error reportado por el dispositivo: {error_msg_device}")

    def _process_calblanco_data(self, parts: list[str], raw_line: str):
        """Procesa y almacena los datos de la mediciÃ³n de referencia (I0)."""
        if len(parts) != 7: return
        try:
            values_np = np.array([float(p) for p in parts[1:7]])
            if np.any(np.isinf(values_np)) or np.any(np.isnan(values_np)):
                 raise ValueError("Datos I0 contienen Inf o NaN.")
        except (ValueError, IndexError):
            self._log(f"Error de formato en datos I0 '{raw_line}'. Descartando.", is_error=True)
            return

        self.data_state.calibration_data_raw.append(raw_line)
        self.data_state.last_calibration_values = values_np
        self._update_numeric_displays()
        self.blank_status_label.setText(f"Iâ‚€ medido @ {time.strftime('%H:%M:%S')}. Listo.")

        # Si se estÃ¡ en modo Abs/Tx, actualiza el grÃ¡fico ya que I0 ha cambiado.
        if self.plot_options.main_plot_type in [PlotType.ABSORBANCE, PlotType.TRANSMITTANCE]:
            self._full_plot_update()
        self.calculation_controller.update_display_only()
        self._update_ui_state()
        self._log("Datos de Referencia (Iâ‚€) procesados.")
        
    def _process_blanco_data(self, parts: list[str], raw_line: str):
        """Procesa un espectro de mediciÃ³n de muestra (I)."""
        if len(parts) != 7: return
        try:
            raw_intensity_values_np = np.array([float(p) for p in parts[1:7]])
            if np.any(np.isinf(raw_intensity_values_np)) or np.any(np.isnan(raw_intensity_values_np)):
                raise ValueError("Datos I contienen Inf o NaN.")
        except (ValueError, IndexError):
            self._log(f"Error de formato en datos I '{raw_line}'. Descartando.", is_error=True)
            return

        self.data_state.last_raw_measurement_spectrum = raw_intensity_values_np
        
        # Aplica la sustracciÃ³n de blanco si estÃ¡ activa.
        if self.data_state.blank_subtraction_active and self.data_state.last_calibration_values is not None:
            self.data_state.last_measurement_values = np.maximum(0, self.data_state.last_raw_measurement_spectrum - self.data_state.last_calibration_values)
        else:
            self.data_state.last_measurement_values = self.data_state.last_raw_measurement_spectrum
        
        if self.app_state != AppState.MEASURING_MAIN and self.is_connected:
             self._update_numeric_displays()
             self._full_plot_update()
             self.calculation_controller.update_display_only()
             return

        current_type = self.measurement_control_state.current_type
        if current_type == MeasurementType.CONTINUOUS:
            self._update_numeric_displays()
            self._full_plot_update()
            self.calculation_controller.update_display_only()
        
        elif current_type in [MeasurementType.SINGLE_AVERAGED, MeasurementType.SEQUENTIAL]:
            # Acumula sub-muestras para promediar.
            self.measurement_control_state.accumulated_sub_samples_raw_lines.append(raw_line)
            self.measurement_control_state.current_m_count += 1
            self._update_numeric_displays()
            self._full_plot_update()
            self.calculation_controller.update_display_only()

            # Si se han recogido las M muestras necesarias, las procesa.
            if self.measurement_control_state.current_m_count >= self.measurement_control_state.m_samples:
                self._process_collected_sub_samples()
                
                if current_type == MeasurementType.SINGLE_AVERAGED:
                    self._finish_current_measurement(success=True)
                elif current_type == MeasurementType.SEQUENTIAL:
                    self.measurement_control_state.current_p_count += 1
                    self._log(f"MediciÃ³n final P {self.measurement_control_state.current_p_count}/{self.measurement_control_state.p_measurements} completada.")
                    if self.measurement_control_state.current_p_count >= self.measurement_control_state.p_measurements:
                        self._finish_current_measurement(success=True)
                    else:
                        # Prepara el siguiente ciclo P
                        self.measurement_control_state.current_m_count = 0
                        self.measurement_control_state.accumulated_sub_samples_raw_lines.clear()
                        if self.measurement_timeout_timer.isActive(): self.measurement_timeout_timer.stop()
                        self.measurement_timeout_timer.start(self.measurement_control_state.m_samples * 200 + 5000)

    def _process_medicion_detenida_msg(self, parts: list[str], raw_line: str):
        """Procesa el mensaje de confirmaciÃ³n de detenciÃ³n del dispositivo."""
        self._log("Arduino confirma detenciÃ³n de mediciÃ³n.")
        if self.app_state == AppState.MEASURING_MAIN and self.measurement_control_state.current_type != MeasurementType.CONTINUOUS:
            self._log("Advertencia: Arduino detuvo mediciÃ³n Ãšnica/Secuencial inesperadamente.", is_error=True)
            self._finish_current_measurement(success=False, arduino_stopped=True)
        elif self.app_state == AppState.MEASURING_DIRECT:
             self._handle_direct_measurement_timeout("El dispositivo detuvo la mediciÃ³n prematuramente.")

    def _process_direct_measurement_data(self, command_type: str, parts: list[str], raw_line: str):
        """Procesa datos recibidos durante una mediciÃ³n directa para un panel especÃ­fico."""
        if not self.direct_measurement_pending_request:
            self._log(f"ADVERTENCIA: Se recibiÃ³ '{raw_line}' pero no hay mediciÃ³n directa pendiente.", is_error=True)
            if self.is_connected: self._send_command_direct("detener")
            return

        req = self.direct_measurement_pending_request
        panel_id, req_wl_nm, req_value_type = req['panel_id'], req['wavelength_nm'], req['value_type']

        if "mediciÃ³n iniciada" in raw_line.lower() or "listo" in raw_line.lower(): return
        if self.direct_measurement_timer.isActive(): self.direct_measurement_timer.stop()
        
        error_msg_to_panel = None
        value_to_emit = np.nan
        measurement_ok = False
        try:
            if command_type not in ["calblanco", "blanco"] or len(parts) != 7:
                raise ValueError(f"Formato de datos inesperado: {raw_line}")

            i_raw_direct_spectrum = np.array([float(p) for p in parts[1:7]])
            if np.any(np.isinf(i_raw_direct_spectrum)) or np.any(np.isnan(i_raw_direct_spectrum)):
                raise ValueError("Datos de espectro contienen Inf o NaN.")

            target_idx = np.where(WAVELENGTHS == req_wl_nm)[0][0]
            
            # Calcula el valor solicitado (Intensidad, Absorbancia, etc.)
            if req_value_type == "Intensidad":
                temp_spectrum = i_raw_direct_spectrum
                if self.data_state.blank_subtraction_active and self.data_state.last_calibration_values is not None:
                    temp_spectrum = np.maximum(0, i_raw_direct_spectrum - self.data_state.last_calibration_values)
                value_to_emit = temp_spectrum[target_idx]
            
            elif req_value_type in ["Absorbancia", "Transmitancia"]:
                i0_main_app = self.data_state.last_calibration_values
                if i0_main_app is None:
                    raise ValueError("Iâ‚€ no medido en App Principal.")
                
                i_sample_val_at_wl_raw = i_raw_direct_spectrum[target_idx]
                i0_val_at_wl = i0_main_app[target_idx]
                
                if self.data_state.blank_subtraction_active:
                     i_sample_val_at_wl_corrected = np.maximum(0, i_sample_val_at_wl_raw - i0_val_at_wl)
                else:
                    i_sample_val_at_wl_corrected = i_sample_val_at_wl_raw

                if i0_val_at_wl <= 1e-9:
                     self._log(f"Advertencia: Iâ‚€ ({i0_val_at_wl:.3f}) en {req_wl_nm}nm es casi cero.", is_error=True)
                else:
                    ratio = i_sample_val_at_wl_corrected / i0_val_at_wl 
                    if req_value_type == "Absorbancia":
                        value_to_emit = -np.log10(ratio) if ratio > 1e-9 else np.nan
                    else:
                        value_to_emit = ratio * 100
            
            measurement_ok = not np.isnan(value_to_emit)
        except (ValueError, IndexError) as e:
            error_msg_to_panel = f"Error procesando datos: {e}"
            self._log(error_msg_to_panel, is_error=True)
        finally:
            # Emite la seÃ±al con el resultado final para que el panel solicitante la reciba.
            self.direct_measurement_signal.emit(panel_id, req_wl_nm, req_value_type, value_to_emit, measurement_ok, error_msg_to_panel)
            self.direct_measurement_pending_request = None
            self.app_state = AppState.IDLE
            if self.is_connected: self._send_command("detener")
            self._update_ui_state()

            if self.app_state == AppState.CLOSING:
                QTimer.singleShot(50, self.close)

    def _check_preconditions_for_measurement(self, measurement_name: str) -> bool:
        """Verifica si se cumplen las condiciones para iniciar cualquier tipo de mediciÃ³n."""
        if not self.is_connected:
            self._show_error(f"No se puede '{measurement_name}': Dispositivo no conectado.")
            return False
        if self.app_state != AppState.IDLE: 
            self._show_info(f"No se puede '{measurement_name}': Ya hay otra mediciÃ³n en curso.")
            return False
        return True

    def _measure_reference_i0(self):
        """Inicia la mediciÃ³n de la referencia (blanco)."""
        if not self._check_preconditions_for_measurement("Medir Referencia (Iâ‚€)"):
            return
        if self._send_command("calibrar"):
            self._log("Comando 'calibrar' (Iâ‚€) enviado.")
        else:
            self._show_error("Fallo al enviar comando 'calibrar'.")

    def _toggle_measurement_config_widgets(self, _=None):
        """Habilita o deshabilita los inputs de configuraciÃ³n de mediciÃ³n (M y P)."""
        can_configure = self.app_state == AppState.IDLE and self.is_connected
        current_type = self.measurement_type_combo.currentText()
        is_seq = current_type == MeasurementType.SEQUENTIAL
        is_cont = current_type == MeasurementType.CONTINUOUS
        self.num_M_samples_input.setEnabled(can_configure and not is_cont)
        self.num_P_points_input.setEnabled(can_configure and is_seq)
        
    def _start_unified_measurement(self):
        """Inicia una mediciÃ³n principal (Continua, Ãšnica o Secuencial)."""
        if not self._check_preconditions_for_measurement("Iniciar MediciÃ³n"):
            return
        
        self.app_state = AppState.MEASURING_MAIN
        self.measurement_control_state = MeasurementControlState(is_active=True)
        self.measurement_control_state.current_type = self.measurement_type_combo.currentText()
        try:
            m_samples = int(self.num_M_samples_input.text())
            if m_samples < 1: raise ValueError()
            self.measurement_control_state.m_samples = m_samples
        except ValueError:
            self._show_error("NÃºmero M invÃ¡lido. Debe ser un entero >= 1.")
            self.app_state = AppState.IDLE; return

        if self.measurement_control_state.current_type == MeasurementType.SEQUENTIAL:
            try:
                p_points = int(self.num_P_points_input.text())
                if p_points < 1: raise ValueError()
                self.measurement_control_state.p_measurements = p_points
            except ValueError:
                self._show_error("NÃºmero P invÃ¡lido. Debe ser un entero >= 1.")
                self.app_state = AppState.IDLE; return
            
            filename = self.file_manager.get_save_filename_for_sequential()
            if not filename:
                self._log("Inicio de mediciÃ³n secuencial cancelado por usuario.")
                self.app_state = AppState.IDLE; return
            
            self.measurement_control_state.sequential_output_filename = filename
            self.measurement_control_state.sequential_initial_I0_line = self.data_state.calibration_data_raw[-1] if self.data_state.calibration_data_raw else None
            self.measurement_control_state.sequential_subtraction_active_at_start = self.data_state.blank_subtraction_active
            self._log(f"MediciÃ³n Secuencial iniciada. Guardando en: {filename}")
        else:
            self._log(f"MediciÃ³n {self.measurement_control_state.current_type} iniciada.")

        if not self._send_command("empezar"):
            self._log("Fallo al enviar 'empezar'. Abortando.", is_error=True)
            self._finish_current_measurement(success=False, error_starting=True) 
            return
        
        self._update_ui_state()

        if self.measurement_control_state.current_type != MeasurementType.CONTINUOUS:
             timeout_duration_ms = self.measurement_control_state.m_samples * 300 + 5000 
             if self.measurement_timeout_timer.isActive(): self.measurement_timeout_timer.stop()
             self.measurement_timeout_timer.start(timeout_duration_ms)
             
    def _stop_current_measurement(self, silent=False):
        """Detiene la mediciÃ³n principal que estÃ© en curso."""
        if self.app_state != AppState.MEASURING_MAIN:
            if not silent: self._log("No hay mediciÃ³n principal para detener.")
            return
        self._log("Deteniendo mediciÃ³n principal...")
        self._finish_current_measurement(manual_stop=True)
        
    def _finish_current_measurement(self, success=False, manual_stop=False, arduino_stopped=False, timed_out=False, error_starting=False):
        """Finaliza una mediciÃ³n principal, actualiza estados y la UI."""
        if self.app_state != AppState.MEASURING_MAIN and not error_starting: 
            return

        current_type_being_finished = self.measurement_control_state.current_type
        
        is_closing = self.app_state == AppState.CLOSING
        self.app_state = AppState.IDLE
        
        if self.measurement_timeout_timer.isActive(): self.measurement_timeout_timer.stop()
        if self.is_connected and not arduino_stopped and not error_starting:
            self._send_command("detener")

        if error_starting:
            self._log(f"Error al iniciar mediciÃ³n '{current_type_being_finished}'.", is_error=True)
        elif timed_out:
            self._log(f"MediciÃ³n '{current_type_being_finished}' finalizada por TIMEOUT.", is_error=True)
        elif arduino_stopped:
            self._log(f"MediciÃ³n '{current_type_being_finished}' detenida por Arduino.", is_error=True)
        elif manual_stop:
            self._log(f"MediciÃ³n '{current_type_being_finished}' DETENIDA MANUALMENTE.")
        elif success:
            self._log(f"MediciÃ³n '{current_type_being_finished}' completada exitosamente.")
        else: 
            self._log(f"MediciÃ³n '{current_type_being_finished}' finalizada CON ERRORES.", is_error=True)
        
        if current_type_being_finished in [MeasurementType.SINGLE_AVERAGED, MeasurementType.SEQUENTIAL] and self.measurement_control_state.accumulated_sub_samples_raw_lines:
            self._process_collected_sub_samples()
        
        if success and current_type_being_finished == MeasurementType.SEQUENTIAL:
            self.file_manager.save_sequential_data(self.measurement_control_state)

        self.measurement_control_state = MeasurementControlState()
        self._update_ui_state()

        if is_closing:
            QTimer.singleShot(50, self.close)
            
    def _process_collected_sub_samples(self):
        """Promedia las sub-muestras (M) acumuladas y actualiza el estado y la UI."""
        m_state = self.measurement_control_state
        if not m_state.accumulated_sub_samples_raw_lines:
            return
            
        num_collected_m = len(m_state.accumulated_sub_samples_raw_lines)
        spectra_matrix = [np.array([float(p) for p in line.strip().split(',')[1:7]]) for line in m_state.accumulated_sub_samples_raw_lines if "blanco" in line]
        
        if not spectra_matrix:
            avg_raw_spectrum = np.full_like(WAVELENGTHS, np.nan, dtype=float)
        else:
            avg_raw_spectrum = np.mean(np.array(spectra_matrix), axis=0)
        
        self.data_state.last_raw_measurement_spectrum = avg_raw_spectrum

        subtraction_active = self.data_state.blank_subtraction_active
        i0_to_use = self.data_state.last_calibration_values
        if m_state.current_type == MeasurementType.SEQUENTIAL:
            subtraction_active = m_state.sequential_subtraction_active_at_start
            if m_state.sequential_initial_I0_line: 
                try: i0_to_use = np.array([float(p) for p in m_state.sequential_initial_I0_line.strip().split(',')[1:7]])
                except (ValueError, IndexError): pass

        if subtraction_active and i0_to_use is not None:
            self.data_state.last_measurement_values = np.maximum(0, avg_raw_spectrum - i0_to_use)
        else:
            self.data_state.last_measurement_values = avg_raw_spectrum

        self._update_numeric_displays()
        self._full_plot_update()
        self.calculation_controller.update_display_only()

        label_suffix = f"_AvgM{num_collected_m}"
        if m_state.current_type == MeasurementType.SINGLE_AVERAGED:
            label = f"Unica{label_suffix}_{time.strftime('%H%M%S')}"
            data_line = f"{label}," + ",".join(map(lambda x: f'{x:.3f}' if not np.isnan(x) else "NaN", self.data_state.last_measurement_values))
            self.data_state.measurement_data_raw.append(data_line)
            self._update_superimpose_list()
        elif m_state.current_type == MeasurementType.SEQUENTIAL:
            label = f"P{m_state.current_p_count + 1}{label_suffix}" 
            m_state.collected_final_sequential_points.append(
                (self.data_state.last_measurement_values, label, avg_raw_spectrum)
            )

        # --- FIX ---
        # Limpia el buffer aquÃ­ para asegurar que este lote de muestras solo se procese una vez.
        # Esto previene la doble llamada desde _finish_current_measurement.
        m_state.accumulated_sub_samples_raw_lines.clear()
        # --- END FIX ---

    @pyqtSlot(str, int, str)
    def request_single_value_measurement(self, panel_id: str, wavelength_nm: int, value_type: str):
        """Slot para manejar solicitudes de mediciones directas de otros paneles."""
        self._log(f"Solicitud directa de {panel_id} para {value_type} @ {wavelength_nm}nm.", is_debug=True)
        if not self._check_preconditions_for_measurement(f"MediciÃ³n Directa"):
             self.direct_measurement_signal.emit(panel_id, wavelength_nm, value_type, np.nan, False, "Conflicto de mediciÃ³n o no conectado.")
             return
        
        if value_type in ["Absorbancia", "Transmitancia"] and self.data_state.last_calibration_values is None:
            error_msg = f"Para medir '{value_type}', mida una Referencia (Iâ‚€) en la app principal."
            self._log(error_msg, is_error=True)
            self.direct_measurement_signal.emit(panel_id, wavelength_nm, value_type, np.nan, False, error_msg)
            return

        self.app_state = AppState.MEASURING_DIRECT
        self.direct_measurement_pending_request = {'panel_id': panel_id, 'wavelength_nm': wavelength_nm, 'value_type': value_type}
        self._update_ui_state() 

        if self._send_command("empezar"):
            self.direct_measurement_timer.start(DIRECT_MEASUREMENT_TIMEOUT_MS)
        else:
            self._handle_direct_measurement_timeout("Fallo al enviar comando 'empezar'.")

    def _handle_direct_measurement_timeout(self, reason: str = "Timeout"):
        """Manejador para cuando una mediciÃ³n directa falla por timeout o error."""
        self._log(f"Timeout/Error en mediciÃ³n directa: {reason}", is_error=True)
        if self.direct_measurement_timer.isActive(): self.direct_measurement_timer.stop()
        
        if self.direct_measurement_pending_request: 
            req = self.direct_measurement_pending_request
            self.direct_measurement_signal.emit(req['panel_id'], req['wavelength_nm'], req['value_type'], np.nan, False, reason)
        
        if self.is_connected: self._send_command_direct("detener")
        self.direct_measurement_pending_request = None
        
        is_closing = self.app_state == AppState.CLOSING

        self.app_state = AppState.IDLE
        self._update_ui_state()
        
        if is_closing:
            QTimer.singleShot(50, self.close)

    def _full_plot_update(self):
        """Recopila todo el estado relevante para el grÃ¡fico y solicita una actualizaciÃ³n."""
        if not self.main_spectrum_panel: return
        plot_data_dict = {
            "plot_type": self.plot_options.main_plot_type,
            "i0_values": self.data_state.last_calibration_values,
            "last_measurement_values": self.data_state.last_measurement_values,
            "session_data_raw": self.data_state.measurement_data_raw,
            "superimposed_labels": self.plot_options.superimposed_spectra_labels,
            "use_log_scale_y": self.plot_options.use_log_scale_y,
            "show_markers": self.plot_options.show_markers,
            "show_i0": self.plot_options.show_I0_on_intensity_graph,
            "subtraction_active": self.data_state.blank_subtraction_active,
            "use_transfer_model": self.use_transfer_model_checkbox.isChecked(),
            "beer_wavelength": self.beer_wavelength_combo.currentData(),
            "active_transfer_model": self.calibration_state.active_transfer_model
        }
        self.main_spectrum_panel.update_plot(plot_data_dict)

    def _on_calculate_and_register_concentration_clicked(self):
        """Inicia el cÃ¡lculo de concentraciÃ³n y registra el resultado."""
        self.calculation_controller.calculate_and_register()

    def _on_I0_blank_subtraction_toggled(self, state: bool):
        """Activa/desactiva la sustracciÃ³n de blanco y recalcula el Ãºltimo espectro."""
        if state and self.data_state.last_calibration_values is None: 
            self._show_info("Mida una Referencia (Iâ‚€) primero para poder activar la sustracciÃ³n.")
            self.enable_I0_blank_subtraction_checkbox.setChecked(False)
            return 
        self.data_state.blank_subtraction_active = state
        self._log(f"SustracciÃ³n de Blanco {'Activada' if state else 'Desactivada'}.")
        if self.data_state.last_raw_measurement_spectrum is not None: 
            if state and self.data_state.last_calibration_values is not None: 
                self.data_state.last_measurement_values = np.maximum(0, self.data_state.last_raw_measurement_spectrum - self.data_state.last_calibration_values)
            else: 
                self.data_state.last_measurement_values = self.data_state.last_raw_measurement_spectrum 
        self._update_numeric_displays()
        self._full_plot_update()
        self.calculation_controller.update_display_only()

    def set_active_calibration_curve(self, slope: float, intercept: float, r_squared: float, wavelength_nm: int):
        """Almacena una nueva curva de calibraciÃ³n de sesiÃ³n en el estado de la app."""
        self.calibration_state.active_session_calibration_curve = (slope, intercept, r_squared, wavelength_nm)
        self._log(f"Curva de sesiÃ³n aplicada: Î»={wavelength_nm}nm, m={slope:.3e}, b={intercept:.3f}, RÂ²={r_squared:.4f}")
        if (idx := [i for i, w in enumerate(WAVELENGTHS) if w == wavelength_nm]):
            self.beer_wavelength_combo.setCurrentIndex(idx[0])
        self.use_session_cal_curve_checkbox.setChecked(True) 
        self.calculation_controller.update_display_only()
        self._update_ui_state()

    def set_active_transfer_model(self, slope_t: float, intercept_t: float, r_sq_t: float, wavelength_nm: int):
        """Almacena un nuevo modelo de transferencia en el estado de la app."""
        self.calibration_state.active_transfer_model[wavelength_nm] = (slope_t, intercept_t, r_sq_t)
        self._log(f"Modelo Transferencia Aplicado para Î»={wavelength_nm}nm: m_t={slope_t:.3e}, b_t={intercept_t:.3f}, RÂ²_t={r_sq_t:.4f}")
        self.calculation_controller.update_display_only()
        self._update_ui_state()
        self._full_plot_update()

    @pyqtSlot(int)
    def clear_active_transfer_model(self, wavelength_nm: int):
        """Elimina un modelo de transferencia activo para una longitud de onda especÃ­fica."""
        if wavelength_nm in self.calibration_state.active_transfer_model:
            del self.calibration_state.active_transfer_model[wavelength_nm]
            self._log(f"Modelo de transferencia para Î»={wavelength_nm}nm limpiado.")
            self.calculation_controller.update_display_only()
            self._update_ui_state()
            self._full_plot_update()

    def _save_reference_calibration_params(self):
        """Guarda los parÃ¡metros de una calibraciÃ³n de referencia externa."""
        selected_wl = self.ref_cal_wl_combo.currentData()
        params = {'type': 'curve' if self.ref_cal_type_curve_radio.isChecked() else 'factor'}

        if params['type'] == 'curve':
            m_text = self.ref_cal_m_input.text().strip()
            b_text = self.ref_cal_b_input.text().strip()
            if not m_text or not b_text:
                self._show_error("Debe ingresar un valor para la Pendiente (m_ref) y el Intercepto (b_ref).")
                return
        else:
            eps_l_text = self.ref_cal_epsilon_l_input.text().strip()
            if not eps_l_text:
                self._show_error("Debe ingresar un valor para el Factor (ÎµL)_ref.")
                return

        try:
            if params['type'] == 'curve':
                params['m_ref'] = float(m_text.replace(',', '.'))
                params['b_ref'] = float(b_text.replace(',', '.'))
            else:
                eps_l_ref = float(eps_l_text.replace(',', '.'))
                if eps_l_ref <= 0: raise ValueError("Factor (ÎµL)_ref debe ser positivo.")
                params['epsilon_l_ref'] = eps_l_ref
            
            self.calibration_state.reference_calibration_parameters[selected_wl] = params
            self._log(f"ParÃ¡metros de ref. guardados para Î»={selected_wl}nm: {params}")
            self._update_ref_cal_display(selected_wl)
            self.calculation_controller.update_display_only()
            self._update_ui_state()
        except ValueError as e:
            self._show_error(f"Valores de calibraciÃ³n de referencia invÃ¡lidos. Ingrese solo nÃºmeros.\n\nError original: {e}")

    def _load_reference_calibration_params_for_wl(self):
        """Carga en la UI los parÃ¡metros de calibraciÃ³n de referencia guardados para la Î» seleccionada."""
        selected_wl = self.ref_cal_wl_combo.currentData()
        params = self.calibration_state.reference_calibration_parameters.get(selected_wl)
        self.ref_cal_m_input.setText("")
        self.ref_cal_b_input.setText("")
        self.ref_cal_epsilon_l_input.setText("")
        if params:
            if params['type'] == 'curve':
                self.ref_cal_type_curve_radio.setChecked(True)
                self.ref_cal_m_input.setText(str(params.get('m_ref', '')))
                self.ref_cal_b_input.setText(str(params.get('b_ref', '')))
            elif params['type'] == 'factor':
                self.ref_cal_type_factor_radio.setChecked(True)
                self.ref_cal_epsilon_l_input.setText(str(params.get('epsilon_l_ref', '')))
        else:
            self.ref_cal_type_curve_radio.setChecked(True)
        self._toggle_ref_cal_inputs()
        self._update_ref_cal_display(selected_wl)

    def _toggle_ref_cal_inputs(self):
        """Habilita los inputs de 'curva' o 'factor' segÃºn el radio button seleccionado."""
        is_curve = self.ref_cal_type_curve_radio.isChecked()
        for widget in [self.ref_cal_m_label, self.ref_cal_m_input, self.ref_cal_b_label, self.ref_cal_b_input]:
            widget.setEnabled(is_curve)
        for widget in [self.ref_cal_epsilon_l_label, self.ref_cal_epsilon_l_input]:
            widget.setEnabled(not is_curve)

    def _update_ref_cal_display(self, wavelength_nm):
        """Actualiza la etiqueta que muestra quÃ© parÃ¡metros de referencia estÃ¡n guardados."""
        params = self.calibration_state.reference_calibration_parameters.get(wavelength_nm)
        text = f"ParÃ¡metros Ref. Guardados ({wavelength_nm}nm): "
        if params:
            text += f"Curva (m={params.get('m_ref', 'N/A')}, b={params.get('b_ref', 'N/A')})" if params['type'] == 'curve' else f"Factor (ÎµL={params.get('epsilon_l_ref', 'N/A')})"
        else:
            text += "Ninguno"
        self.current_ref_cal_params_display_label.setText(text)

    def _update_status_label(self, text: str, style: str):
        """Actualiza el texto y color de la etiqueta de estado de conexiÃ³n."""
        self.status_label.setText(f"Estado: {text}")
        color_map = {
            "success": ("#55ff7f", "green"),
            "error": ("#ff5555", "red"),
            "warning": ("#ffcc00", "orange"),
        }
        dark, light = color_map.get(style, ("#d0d0d0", "#101010"))
        color = dark if self.current_theme_is_dark else light
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def _update_status_label_style(self):
        """Refresca el estilo de la etiqueta de estado, Ãºtil al cambiar de tema."""
        text = self.status_label.text()
        if "Conectado" in text: self._update_status_label("Conectado", "success")
        elif "Error" in text or "Perdida" in text: self._update_status_label(text.replace("Estado: ", ""), "error")
        else: self._update_status_label("Desconectado", "warning")

    def _update_value_labels(self, value_array, label_widgets_list):
        """FunciÃ³n auxiliar para actualizar un conjunto de etiquetas con valores de un array."""
        for i, label in enumerate(label_widgets_list):
            val_str = "N/A"
            if value_array is not None and i < len(value_array):
                val = value_array[i]
                val_str = f"{val:.2f}" if not np.isnan(val) else "NaN" 
            label.setText(val_str)

    def _update_numeric_displays(self):
        """Actualiza los displays numÃ©ricos de I0 e I."""
        self._update_value_labels(self.data_state.last_calibration_values, self.cal_values_labels)
        self._update_value_labels(self.data_state.last_measurement_values, self.meas_values_labels)
        
    def _update_ui_state(self):
        """Habilita o deshabilita todos los controles de la UI segÃºn el estado de la aplicaciÃ³n."""
        is_idle = self.app_state == AppState.IDLE
        is_measuring = not is_idle
        
        # --- Controles de ConexiÃ³n ---
        self.port_combo.setEnabled(is_idle and not self.is_connected)
        self.refresh_button.setEnabled(is_idle and not self.is_connected)
        self.connect_button.setEnabled(is_idle and not self.is_connected and self.port_combo.count() > 0 and "No hay puertos" not in self.port_combo.currentText())
        self.disconnect_button.setEnabled(self.is_connected)
        self.autoconnect_arduino_checkbox.setEnabled(is_idle and not self.is_connected)

        # --- Controles de MediciÃ³n ---
        can_start_main = is_idle and self.is_connected
        self.calibrate_button.setEnabled(can_start_main)
        self.measurement_type_combo.setEnabled(can_start_main)
        self.start_unified_measurement_button.setEnabled(can_start_main)
        self.stop_measurement_button.setEnabled(self.app_state == AppState.MEASURING_MAIN)
        self._toggle_measurement_config_widgets()

        # --- Controles de Datos ---
        has_data = bool(self.data_state.measurement_data_raw)
        has_superimposed = bool(self.plot_options.superimposed_spectra_labels)
        self.save_button.setEnabled(is_idle and has_data)
        self.save_superimposed_button.setEnabled(is_idle and has_superimposed)
        self.clear_button.setEnabled(is_idle and has_data)
        self.export_graph_button.setEnabled(is_idle)
        
        # --- Controles de AnÃ¡lisis ---
        self.concentration_calc_group.setEnabled(is_idle)
        self.ref_cal_params_group.setEnabled(is_idle)
        self.blank_subtraction_group.setEnabled(is_idle)
        self.enable_I0_blank_subtraction_checkbox.setEnabled(is_idle and self.data_state.last_calibration_values is not None)
        
        # --- Acciones del MenÃº ---
        if hasattr(self, 'save_data_action_menu'):
            self.save_data_action_menu.setEnabled(self.save_button.isEnabled())
            self.save_superimposed_action_menu.setEnabled(self.save_superimposed_button.isEnabled())
            self.clear_data_action_menu.setEnabled(self.clear_button.isEnabled())
            self.export_graph_action_menu.setEnabled(self.export_graph_button.isEnabled())
            self.export_log_action.setEnabled(bool(self.log_output.toPlainText().strip()))

        # --- LÃ³gica de habilitaciÃ³n para cÃ¡lculo de concentraciÃ³n ---
        current_wl_beer = self.beer_wavelength_combo.currentData()
        can_use_session_curve = is_idle and self.calibration_state.active_session_calibration_curve is not None and self.calibration_state.active_session_calibration_curve[3] == current_wl_beer
        self.use_session_cal_curve_checkbox.setEnabled(can_use_session_curve)
        if not can_use_session_curve: self.use_session_cal_curve_checkbox.setChecked(False)
        
        can_use_transfer_model = is_idle and current_wl_beer in self.calibration_state.active_transfer_model and current_wl_beer in self.calibration_state.reference_calibration_parameters
        self.use_transfer_model_checkbox.setEnabled(can_use_transfer_model)
        if not can_use_transfer_model: self.use_transfer_model_checkbox.setChecked(False)
        
        self.calculate_concentration_button.setEnabled(is_idle and self.plot_options.main_plot_type == PlotType.ABSORBANCE)
        
        # --- Estado de las opciones del grÃ¡fico ---
        if self.main_spectrum_panel:
            self.main_spectrum_panel.set_plot_options_state(
                self.plot_options.show_markers,
                self.plot_options.use_log_scale_y,
                self.plot_options.show_I0_on_intensity_graph,
                self.data_state.last_calibration_values is not None,
                self.plot_options.main_plot_type == PlotType.INTENSITY
            )

    @pyqtSlot(str, bool, bool)
    def _log(self, message: str, is_error=False, is_debug=False):
        """AÃ±ade un mensaje con timestamp al widget del log."""
        timestamp = time.strftime("%H:%M:%S")
        prefix = "ERROR: " if is_error else "DEBUG: " if is_debug else ""
        self.log_output.append(f"[{timestamp}] {prefix}{message}")

    def _show_error(self, message: str):
        """Muestra un diÃ¡logo de error crÃ­tico y lo registra en el log."""
        self._log(message, is_error=True) 
        QMessageBox.critical(self, "Error", message)

    def _show_info(self, message: str):
        """Muestra un diÃ¡logo de informaciÃ³n y lo registra en el log."""
        self._log(message) 
        QMessageBox.information(self, "InformaciÃ³n", message)

    def _show_help(self):
        """Muestra la ventana principal de ayuda."""
        HelpDialog(self).exec_()

    def _show_context_help(self, help_id_key: str):
        """Muestra una ayuda contextual especÃ­fica para un widget."""
        help_text = CONTEXT_HELP_TEXTS.get(help_id_key, "No hay ayuda disponible.")
        QMessageBox.information(self, f"Ayuda: {help_id_key.replace('_',' ').title()}", help_text)

    def _show_about_dialog(self):
        """Muestra el diÃ¡logo 'Acerca de...'."""
        QMessageBox.about(self, "Acerca de EspectrofotÃ³metro AS726X", """
        <h3>Software para EspectrofotÃ³metro AS726X</h3>
        <p><b>Hecho por:</b> Sebastian Herrera Betancur</p>
        <p><b>Grupo de InvestigaciÃ³n:</b> Biomicrosystems</p>
        <hr>
        <p><b>Contacto:</b> <a href="mailto:s.herrerab@uniandes.edu.co">s.herrerab@uniandes.edu.co</a></p>
        <p><b>GitHub:</b> <a href="https://github.com/Biomicrosystems">Biomicrosystems</a></p>
        """)

    def closeEvent(self, event):
        """Manejador del evento de cierre de la ventana para un apagado seguro."""
        if self.app_state == AppState.CLOSING:
            event.ignore(); return

        self._log("Solicitud de cierre de aplicaciÃ³n...")
        self.port_check_timer.stop()

        # Si hay una tarea en curso, pregunta al usuario si desea detenerla.
        if self.app_state != AppState.IDLE:
            blocker = "mediciÃ³n principal" if self.app_state == AppState.MEASURING_MAIN else "mediciÃ³n para panel"
            reply = QMessageBox.warning(self, "Cerrar AplicaciÃ³n",
                                        f"Hay una {blocker} en progreso.\nÂ¿Desea detenerla y cerrar?",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                state_before_closing = self.app_state
                self.app_state = AppState.CLOSING
                self._update_status_label("Cerrando...", "warning")
                self.setEnabled(False) 
                
                if state_before_closing == AppState.MEASURING_MAIN:
                    self._stop_current_measurement(silent=True)
                elif state_before_closing == AppState.MEASURING_DIRECT:
                    self._handle_direct_measurement_timeout("Cierre de la aplicaciÃ³n.")
                
                event.ignore()
            else:
                event.ignore()
        else:
            # Si no hay tareas, procede con el cierre.
            self.app_state = AppState.CLOSING
            self._finalize_close(event)

    def _finalize_close(self, event):
        """Realiza los pasos finales de cierre, como desconectar el puerto serial."""
        if self.is_connected:
            self._disconnect_serial(due_to_error=False)
        self._log("Cierre de aplicaciÃ³n aceptado. Â¡AdiÃ³s!")
        event.accept()

    def _update_superimpose_list(self):
        """Actualiza la lista de mediciones disponibles para superponer en el panel de espectro."""
        if self.main_spectrum_panel:
            self.main_spectrum_panel.update_superimpose_list(self.data_state.measurement_data_raw, self.plot_options.superimposed_spectra_labels)

    def _save_session_data(self):
        """Guarda los datos de la sesiÃ³n actual (mediciones I y I0)."""
        if self.app_state != AppState.IDLE:
             self._show_info("Detenga la mediciÃ³n actual antes de guardar los datos.")
             return 
        self.file_manager.save_session_data()

    def _clear_session_data_internal(self, log: bool = True):
        """Reinicia todos los estados de datos y calibraciÃ³n a sus valores por defecto."""
        self.data_state = MeasurementDataState()
        self.calibration_state = CalibrationState()
        self.plot_options.superimposed_spectra_labels.clear()

        self._update_numeric_displays()
        self._full_plot_update()
        self.calculation_controller.update_display_only()
        self._load_reference_calibration_params_for_wl()

        self.blank_status_label.setText("Referencia Iâ‚€ no medida.")
        self.enable_I0_blank_subtraction_checkbox.setChecked(False)

        self._update_superimpose_list()
        self._update_ui_state() 
        if log:
            self._log("Datos de sesiÃ³n en memoria borrados.")

    def _clear_session_data(self):
        """Pide confirmaciÃ³n al usuario antes de borrar todos los datos de la sesiÃ³n."""
        if not any([self.data_state.measurement_data_raw, self.calibration_state.active_session_calibration_curve, self.calibration_state.active_transfer_model]):
            self._show_info("No hay datos de sesiÃ³n en memoria para limpiar.")
            return
        
        reply = QMessageBox.question(self, 'Confirmar Limpieza',
                                     "Â¿Borrar TODOS los datos de la sesiÃ³n actual?\n"
                                     "(Incluye mediciones, curvas activas y modelos)",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._clear_session_data_internal()


if __name__ == '__main__':
    # --- Punto de Entrada de la AplicaciÃ³n ---
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setApplicationName("EspectrofotometroAS726X")
    app.setOrganizationName("Biomicrosystems")

    main_window = SpectrometerApp()
    main_window.show()
    sys.exit(app.exec_())
