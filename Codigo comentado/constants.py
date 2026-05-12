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
Este archivo centraliza todas las constantes utilizadas en la aplicaciÃ³n para
facilitar el mantenimiento y la consistencia.
"""
import numpy as np
import matplotlib.colors as mcolors

# --- ParÃ¡metros del Sensor AS726X ---
WAVELENGTHS = np.array([450, 500, 550, 570, 600, 650])
WAVELENGTH_LABELS = ["Violeta (450nm)", "Azul (500nm)", "Verde (550nm)",
                     "Amarillo (570nm)", "Naranja (600nm)", "Rojo (650nm)"]

# --- Paletas de Colores para GrÃ¡ficos ---
DARK_PLOT_COLORS = {
    'bg_color': '#3c3c3c',
    'text_color': '#e0e0e0',
    'grid_color': '#555555',
    'fig_bg_color': '#2e2e2e',
    'title_fontsize': 11,
    'point_color': '#56b4e9',
    'line_color_fit': '#e69f00',
    'line_color_data': '#009e73',
    'i0_color': '#f0e442',
    'point_color_cal_curve': '#4dc9ff',
    'line_color_fit_cal_curve': '#ff7043',
    'point_color_conc_curve': '#56b4e9',
    'line_color_data_conc_curve': '#009e73',
    'transfer_model_fit_line_color': '#9932CC',
    'transfer_model_points_color': '#BA55D3'
}

LIGHT_PLOT_COLORS = {
    'bg_color': '#ffffff',
    'text_color': '#000000',
    'grid_color': '#dcdcdc',
    'fig_bg_color': '#f0f0f0',
    'title_fontsize': 11,
    'point_color': '#0072b2',
    'line_color_fit': '#d55e00',
    'line_color_data': '#009e73',
    'i0_color': '#cc79a7',
    'point_color_cal_curve': '#007acc',
    'line_color_fit_cal_curve': '#d32f2f',
    'point_color_conc_curve': '#0072b2',
    'line_color_data_conc_curve': '#009e73',
    'transfer_model_fit_line_color': '#8A2BE2',
    'transfer_model_points_color': '#9370DB'
}

# Ciclo de colores para mÃºltiples lÃ­neas en un grÃ¡fico (superposiciÃ³n)
PLOT_COLOR_CYCLE = list(mcolors.TABLEAU_COLORS.values()) + \
                   ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

# --- Hojas de Estilo (QSS) para la Interfaz GrÃ¡fica ---
DARK_STYLESHEET = """
QWidget {
    background-color: #2b2b2b;
    color: #d0d0d0;
    font-size: 10pt;
}
QMainWindow {
    background-color: #2b2b2b;
}
QGroupBox {
    background-color: #353535;
    border: 1px solid #484848;
    border-radius: 3px;
    margin-top: 0.6ex;
    font-weight: bold;
    padding-top: 12px;
    padding-bottom: 3px;
    padding-left: 4px;
    padding-right: 4px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 2px;
    background-color: #353535;
    color: #d0d0d0;
}
QLabel#logoLabel {
    background-color: transparent;
    padding: 2px;
}
QLabel {
    background-color: transparent;
    padding: 1px;
}
QPushButton {
    background-color: #4a4a4a;
    color: #d0d0d0;
    border: 1px solid #585858;
    padding: 3px 5px;
    border-radius: 2px;
    min-height: 16px;
}
QPushButton:hover {
    background-color: #525252;
    border: 1px solid #666666;
}
QPushButton:pressed {
    background-color: #404040;
}
QPushButton:disabled {
    background-color: #383838;
    color: #707070;
    border-color: #454545;
}
QPushButton[text="?"] {
    padding: 0px;
    min-height: 18px;
    min-width: 18px;
    max-width: 18px;
    max-height: 18px;
    font-weight: bold;
    font-size: 8pt;
}
QComboBox {
    border: 1px solid #484848;
    border-radius: 2px;
    padding: 1px 3px;
    background-color: #3a3a3a;
    min-height: 16px;
}
QComboBox:hover {
    border: 1px solid #555555;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;
    border-left-width: 1px;
    border-left-color: #484848;
    border-left-style: solid;
    border-top-right-radius: 2px;
    border-bottom-right-radius: 2px;
}
QComboBox QAbstractItemView {
    border: 1px solid #484848;
    background-color: #3a3a3a;
    color: #d0d0d0;
    selection-background-color: #525252;
}
QLineEdit, QTextEdit, QDoubleSpinBox {
    background-color: #333333;
    color: #d0d0d0;
    border: 1px solid #484848;
    border-radius: 2px;
    padding: 1px 3px;
    min-height: 16px;
}
QLineEdit:disabled, QTextEdit:disabled, QDoubleSpinBox:disabled {
    background-color: #2c2c2c;
    color: #6a6a6a;
}
QTextEdit {
    font-family: Consolas, Courier New, monospace;
}
QRadioButton, QCheckBox {
    background-color: transparent;
    spacing: 3px;
    padding: 1px;
}
QRadioButton::indicator::unchecked, QCheckBox::indicator::unchecked {
    border: 1px solid #777777; background-color: #3a3a3a; border-radius:3px; width:11px; height:11px;
}
QRadioButton::indicator::checked, QCheckBox::indicator::checked {
    border: 1px solid #55aaff; background-color: #007acc;border-radius:3px;width:11px; height:11px;
}
QTableWidget {
    gridline-color: #484848;
    background-color: #353535;
    alternate-background-color: #3a3a3a;
}
QTableWidget::item:hover {
    background-color: #4f4f4f;
}
QTableWidget QTableCornerButton::section {
    background-color: #353535;
    border: 1px solid #484848;
}
QHeaderView::section {
    background-color: #404040;
    color: #d0d0d0;
    padding: 3px;
    border: 1px solid #484848;
    font-weight: bold;
}
QScrollBar:horizontal {
    border: none;
    background: #2b2b2b;
    height: 10px;
    margin: 0px 15px 0 15px;
}
QScrollBar::handle:horizontal {
    background: #4a4a4a;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    background: none; border: none; width: 15px;
}
QScrollBar:vertical {
    border: none;
    background: #2b2b2b;
    width: 10px;
    margin: 15px 0 15px 0;
}
QScrollBar::handle:vertical {
    background: #4a4a4a;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background: none; border: none; height: 15px;
}
QSplitter::handle {
    background-color: #404040;
    border: 1px solid #353535;
}
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical { height: 2px; }

QDialog { background-color: #2b2b2b; }
QDialogButtonBox QPushButton {
    min-width: 70px;
    padding: 4px 10px;
}
QMenuBar {
    background-color: #2b2b2b;
    color: #d0d0d0;
    padding: 2px;
}
QMenuBar::item {
    background-color: #2b2b2b;
    color: #d0d0d0;
    padding: 3px 6px;
}
QMenuBar::item:selected { background-color: #4a4a4a; }
QMenu {
    background-color: #353535;
    color: #d0d0d0;
    border: 1px solid #484848;
    padding: 2px;
}
QMenu::item { padding: 3px 15px; }
QMenu::item:selected { background-color: #4a4a4a; }

QTabWidget::pane {
    border: 1px solid #484848;
    border-top: 1px solid #404040;
    background-color: #303030;
    padding: 4px;
}
QTabBar::tab {
    background-color: #3a3a3a;
    color: #b0b0b0;
    border: 1px solid #484848;
    border-bottom-color: #404040;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    min-width: 8ex;
    padding: 5px 10px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #3c3c3c;
    color: #ffffff;
    border-color: #585858;
    border-bottom-color: #3c3c3c;
}
QTabBar::tab:!selected:hover {
    background-color: #454545;
    color: #d0d0d0;
}
QTabBar::tab:last { margin-right: 0; }
QTabBar {
    qproperty-drawBase: 0;
    left: 4px;
    background-color: transparent;
}
QFrame[frameShape="5"] {
    color: #484848;
    margin-top: 2px;
    margin-bottom: 2px;
}
"""

LIGHT_STYLESHEET = """
QWidget {
    background-color: #fdfdfd;
    color: #101010;
    font-size: 10pt;
}
QMainWindow {
    background-color: #fdfdfd;
}
QGroupBox {
    background-color: #f5f5f5;
    border: 1px solid #c0c0c0;
    border-radius: 3px;
    margin-top: 0.6ex;
    font-weight: bold;
    padding-top: 12px;
    padding-bottom: 3px;
    padding-left: 4px;
    padding-right: 4px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 2px;
    background-color: #f5f5f5;
    color: #101010;
}
QLabel#logoLabel {
    background-color: transparent;
    padding: 2px;
}
QLabel {
    background-color: transparent;
     padding: 1px;
}
QPushButton {
    background-color: #e8e8e8;
    color: #101010;
    border: 1px solid #b8b8b8;
    padding: 3px 5px;
    border-radius: 2px;
    min-height: 16px;
}
QPushButton:hover {
    background-color: #dddddd;
    border: 1px solid #adadad;
}
QPushButton:pressed {
    background-color: #d0d0d0;
}
QPushButton:disabled {
    background-color: #e0e0e0;
    color: #707070;
    border-color: #c8c8c8;
}
QPushButton[text="?"] {
    padding: 0px;
    min-height: 18px;
    min-width: 18px;
    max-width: 18px;
    max-height: 18px;
    font-weight: bold;
    font-size: 8pt;
    background-color: #e0e0e0;
}
QComboBox {
    border: 1px solid #b8b8b8;
    border-radius: 2px;
    padding: 1px 3px;
    background-color: #ffffff;
    min-height: 16px;
}
QComboBox:hover {
    border: 1px solid #adadad;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;
    border-left-width: 1px;
    border-left-color: #b8b8b8;
    border-left-style: solid;
    border-top-right-radius: 2px;
    border-bottom-right-radius: 2px;
}
QComboBox QAbstractItemView {
    border: 1px solid #b8b8b8;
    background-color: #ffffff;
    color: #101010;
    selection-background-color: #d8d8d8;
}
QLineEdit, QTextEdit, QDoubleSpinBox {
    background-color: #ffffff;
    color: #101010;
    border: 1px solid #b8b8b8;
    border-radius: 2px;
    padding: 1px 3px;
    min-height: 16px;
}
QLineEdit:disabled, QTextEdit:disabled, QDoubleSpinBox:disabled {
    background-color: #ebebeb;
    color: #6a6a6a;
}
QTextEdit {
    font-family: Consolas, Courier New, monospace;
}
QRadioButton, QCheckBox {
    background-color: transparent;
    spacing: 3px;
    padding: 1px;
}
QRadioButton::indicator::unchecked, QCheckBox::indicator::unchecked {
    border: 1px solid #777777; background-color: #f0f0f0; border-radius:3px; width:11px; height:11px;
}
QRadioButton::indicator::checked, QCheckBox::indicator::checked {
    border: 1px solid #007acc; background-color: #55aaff;border-radius:3px;width:11px; height:11px;
}
QTableWidget {
    gridline-color: #c0c0c0;
    background-color: #ffffff;
    alternate-background-color: #f8f8f8;
}
QTableWidget::item:hover {
    background-color: #eaf6ff;
}
QTableWidget QTableCornerButton::section {
    background-color: #f5f5f5;
    border: 1px solid #c0c0c0;
}
QHeaderView::section {
    background-color: #e8e8e8;
    color: #101010;
    padding: 3px;
    border: 1px solid #b8b8b8;
    font-weight: bold;
}
QScrollBar:horizontal {
    border: none;
    background: #e8e8e8;
    height: 10px;
    margin: 0px 15px 0 15px;
}
QScrollBar::handle:horizontal {
    background: #b8b8b8;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    background: none; border: none; width: 15px;
}
QScrollBar:vertical {
    border: none;
    background: #e8e8e8;
    width: 10px;
    margin: 15px 0 15px 0;
}
QScrollBar::handle:vertical {
    background: #b8b8b8;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background: none; border: none; height: 15px;
}
QSplitter::handle {
    background-color: #d8d8d8;
    border: 1px solid #c0c0c0;
}
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical { height: 2px; }

QDialog { background-color: #fdfdfd; }
QDialogButtonBox QPushButton {
    min-width: 70px;
    padding: 4px 10px;
}
QMenuBar {
    background-color: #fdfdfd;
    color: #101010;
    padding: 2px;
}
QMenuBar::item {
    background-color: #fdfdfd;
    color: #101010;
    padding: 3px 6px;
}
QMenuBar::item:selected { background-color: #e0e0e0; }
QMenu {
    background-color: #ffffff;
    color: #101010;
    border: 1px solid #c0c0c0;
    padding: 2px;
}
QMenu::item { padding: 3px 15px; }
QMenu::item:selected { background-color: #e8e8e8; }

QTabWidget::pane {
    border: 1px solid #c0c0c0;
    border-top: 1px solid #d0d0d0;
    background-color: #f0f0f0;
    padding: 4px;
}
QTabBar::tab {
    background-color: #e8e8e8;
    color: #404040;
    border: 1px solid #b8b8b8;
    border-bottom-color: #d0d0d0;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    min-width: 8ex;
    padding: 5px 10px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #f0f0f0;
    color: #000000;
    border-color: #b0b0b0;
    border-bottom-color: #f0f0f0;
}
QTabBar::tab:!selected:hover {
    background-color: #dddddd;
    color: #000000;
}
QTabBar::tab:last { margin-right: 0; }
QTabBar {
    qproperty-drawBase: 0;
    left: 4px;
    background-color: transparent;
}
QFrame[frameShape="5"] {
    color: #c0c0c0;
    margin-top: 2px;
    margin-bottom: 2px;
}
"""

# --- Textos de Ayuda Contextual ---
CONTEXT_HELP_TEXTS = {
    "connection": """Ayuda: ConexiÃ³n Serial
    - Puerto: Selecciona el puerto COM del espectrofotÃ³metro.
    - Refrescar: Busca puertos COM disponibles.
    - Conectar/Desconectar: Inicia/termina la comunicaciÃ³n.
    - Estado: Indica el estado actual.""",
    "measurement": """Ayuda: Control y ConfiguraciÃ³n de MediciÃ³n
    - Medir Referencia (Iâ‚€): Mide el espectro del solvente/blanco. Necesario para Absorbancia y SustracciÃ³n.
    - Tipo de MediciÃ³n: Continuo (tiempo real), Ãšnico (promedia M espectros), Secuencial (P mediciones promediadas de M espectros, guarda en CSV).
    - M: NÂº de espectros a promediar por cada mediciÃ³n final (para Ãšnico/Secuencial).
    - P: NÂº total de mediciones finales (para Secuencial).
    - Iniciar/Detener: Comienza/Para la mediciÃ³n seleccionada.""",
    "data_management": """Ayuda: GestiÃ³n de Datos
    - Guardar Datos Acumulados: Guarda Iâ‚€ y mediciones I (Ãšnicas/Continuas detenidas) de la sesiÃ³n actual en un CSV.
    - Limpiar Datos en Memoria: Borra Iâ‚€ e I de la memoria (no afecta archivos ni curva).
    - Exportar GrÃ¡fico: Guarda la imagen del grÃ¡fico actual.""",
    "numeric_display": """Ayuda: Ãšltimos Valores Registrados
    - Muestra los valores numÃ©ricos (intensidad) del Ãºltimo espectro de Referencia (Iâ‚€) y de la Ãºltima MediciÃ³n (I) para cada longitud de onda.
    - Si la 'SustracciÃ³n de Blanco' estÃ¡ activa, los valores de 'I' son I_medida - Iâ‚€.""",
    "plot_display": """Ayuda: VisualizaciÃ³n del Espectro
    - Muestra el espectro actual. Incluye una barra de herramientas para zoom/paneo.
    - Usa los botones de 'Tipo de GrÃ¡fico' para cambiar entre Intensidad, Absorbancia y Transmitancia.
    - Opciones adicionales de grÃ¡fico disponibles en su propia secciÃ³n.""",
    "plot_options": """Ayuda: Tipo de GrÃ¡fico (PestaÃ±a Espectro)
    - Intensidad: Muestra la intensidad lumÃ­nica (I o I-Iâ‚€) vs Î».
    - Absorbancia: Muestra Absorbancia (-log(I/Iâ‚€) o -log((I-Iâ‚€)/Iâ‚€)) vs Î».
    - Transmitancia (%T): Muestra Transmitancia ( (I/Iâ‚€)*100 o ((I-Iâ‚€)/Iâ‚€)*100 ) vs Î».""",
    "plot_customization": """Ayuda: PersonalizaciÃ³n del GrÃ¡fico (PestaÃ±a Espectro)
    - Superponer Espectros: Permite seleccionar mÃºltiples mediciones de la sesiÃ³n actual para mostrarlas juntas en el grÃ¡fico.
    - Escala del Eje Y: Cambia entre escala Lineal y LogarÃ­tmica para el eje Y.
    - Mostrar/Ocultar Marcadores: Activa o desactiva los marcadores en los puntos de datos del grÃ¡fico.
    - Mostrar/Ocultar Iâ‚€: En modo Intensidad, permite visualizar el espectro de referencia Iâ‚€ junto con la mediciÃ³n I.""",
    "log_display": """Ayuda: Log de ComunicaciÃ³n y Eventos
    - Muestra mensajes importantes, comandos enviados (TX), datos recibidos (RX) y errores.""",
    "beer_lambert": """Ayuda: CÃ¡lculo de ConcentraciÃ³n (Principal)
    - Estima 'C' usando la Ley de Beer-Lambert, una Curva de CalibraciÃ³n de SesiÃ³n o un Modelo de Transferencia.
    - Requiere estar en modo 'Absorbancia' en la PestaÃ±a Espectro Principal.
    - Îµ y b: Coeficiente de absortividad molar y camino Ã³ptico. Se usan para Beer-Lambert si no hay curvas activas.
    - Usar Curva de SesiÃ³n (A_custom vs C): Usa la curva generada en la pestaÃ±a 'Curva CalibraciÃ³n'.
    - Usar Ajuste con Modelo de Transferencia: Si estÃ¡ activo, A_custom se convierte a A_ajustada usando el modelo de transferencia, y luego 'C' se calcula usando los parÃ¡metros de una calibraciÃ³n de referencia.""",
    "blank_subtraction": """Ayuda: SustracciÃ³n de Blanco
    - Si se activa (requiere medir Iâ‚€ primero), resta el espectro Iâ‚€ de las mediciones I posteriores (I_corregida = I_medida - Iâ‚€).
    - Afecta la visualizaciÃ³n de Intensidad y el cÃ¡lculo de Absorbancia/Transmitancia.""",
    "concentration_curve_tab_main": """Ayuda: PestaÃ±a Curva de ConcentraciÃ³n vs. MediciÃ³n
    - PropÃ³sito: Construir un grÃ¡fico de una variable independiente (eje X, ej: ConcentraciÃ³n, Tiempo) vs. un valor medido (Intensidad, Absorbancia o Transmitancia en eje Y) para una Î» especÃ­fica.
    - Controles:
        - Tipo de Valor Y: Selecciona la magnitud para el eje Y.
        - Longitud de Onda: Elige la Î» para los valores del eje Y.
        - Valor Eje X (ej. ConcentraciÃ³n): Ingresa el valor del eje X.
        - Medir Valor Y Directamente: Realiza una nueva mediciÃ³n y carga el valor en 'Valor Medido (Y)'. Requiere Iâ‚€ si es Abs/Tx.
        - AÃ±adir Punto a la Curva: AÃ±ade el par (Valor X, Valor Medido Y) al grÃ¡fico/tabla.""",
    "calibration_curve_abs_vs_conc_tab_main": """Ayuda: PestaÃ±a Curva de CalibraciÃ³n y Transferencia
    - PropÃ³sito:
        1. Crear curvas de calibraciÃ³n de sesiÃ³n (A_custom vs. ConcentraciÃ³n).
        2. (Opcional) Crear un modelo de transferencia (A_ref vs. A_custom) si se dispone de datos de un equipo de referencia.
    - Controles:
        - Longitud de Onda: Selecciona la Î» para la curva.
        - ConcentraciÃ³n EstÃ¡ndar: ConcentraciÃ³n conocida del estÃ¡ndar.
        - Medir A_custom EstÃ¡ndar: Mide la absorbancia del estÃ¡ndar con este dispositivo. Requiere Iâ‚€.
        - Abs. Referencia (A_ref) (Opcional): Ingresa la absorbancia del mismo estÃ¡ndar medida por un equipo de referencia.
        - AÃ±adir Punto: AÃ±ade el punto a la tabla.
    - Acciones:
        - Aplicar Curva(s) a App Principal: EnvÃ­a las curvas calculadas a la App Principal para ser usadas en el cÃ¡lculo de concentraciÃ³n.
        - Guardar/Cargar Datos: Guarda o carga los puntos de calibraciÃ³n para la Î» actual.""",
    "ref_cal_config_group": """Ayuda: Configurar CalibraciÃ³n de Referencia
    - PropÃ³sito: Ingresar los parÃ¡metros de una calibraciÃ³n obtenida en un espectrofotÃ³metro de referencia. Estos parÃ¡metros se usarÃ¡n junto con el 'Modelo de Transferencia' para calcular la concentraciÃ³n.
    - Longitud de Onda: Seleccione la Î» para la cual va a ingresar los parÃ¡metros.
    - Tipo de CalibraciÃ³n:
        - Curva (A_ref = mC + b): Si su calibraciÃ³n de referencia es una lÃ­nea recta con pendiente (m_ref) e intercepto (b_ref).
        - Factor (A_ref = (ÎµL)C): Si su calibraciÃ³n de referencia es un factor Ãºnico (producto de absortividad molar y camino Ã³ptico).
    - Guardar ParÃ¡metros: Guarda los valores ingresados para la Î» seleccionada, permitiendo que se usen en el cÃ¡lculo de concentraciÃ³n."""
}
