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
Define la clase 'HelpDialog', que crea la ventana de ayuda de la aplicaciÃ³n.

Muestra una ventana con un Ã¡rbol de temas navegable y el contenido del
tema seleccionado, facilitando la consulta de la documentaciÃ³n.
"""

from PyQt5.QtWidgets import (
    QVBoxLayout, QDialog, QDialogButtonBox, QTreeWidget,
    QTreeWidgetItem, QTextBrowser, QSplitter
)
from PyQt5.QtCore import Qt

class HelpDialog(QDialog):
    """Implementa la ventana de diÃ¡logo de ayuda."""
    def __init__(self, parent=None):
        """Inicializa la ventana, sus widgets y pobla el Ã¡rbol de ayuda."""
        super().__init__(parent)
        self.setWindowTitle("Ayuda - EspectrofotÃ³metro AS726X")
        self.setMinimumWidth(850) 
        self.setMinimumHeight(650)

        self.help_topics = self._create_help_topics()

        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("Temas de Ayuda")
        self._populate_tree()
        self.tree_widget.currentItemChanged.connect(self._on_tree_item_changed)
        self.tree_widget.setMinimumWidth(300) 
        self.tree_widget.setMaximumWidth(450)

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)

        splitter.addWidget(self.tree_widget)
        splitter.addWidget(self.text_browser)
        splitter.setStretchFactor(1, 1) 

        main_layout.addWidget(splitter)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        main_layout.addWidget(button_box)

        first_item = self.tree_widget.topLevelItem(0)
        if first_item:
            self.tree_widget.setCurrentItem(first_item)
            
    def _create_help_topics(self):
        """Define y retorna el diccionario que contiene todo el texto de ayuda."""
        topics = {
            "IntroducciÃ³n": """
                <h2>1. IntroducciÃ³n</h2>
                <p>Esta aplicaciÃ³n permite controlar un espectrofotÃ³metro basado en el sensor AS726X para realizar diversas mediciones espectrales. Esta guÃ­a detalla las funcionalidades y cÃ³mo utilizarlas.</p>
                <p>La interfaz se divide en un panel de control a la izquierda y un Ã¡rea de visualizaciÃ³n principal a la derecha, organizada en pestaÃ±as.</p>
            """,
            "Panel de Control (Izquierda)": {
                "ConexiÃ³n Serial": """
                    <h3>2.1. ConexiÃ³n Serial</h3>
                    <p>Gestiona la comunicaciÃ³n con el espectrofotÃ³metro.</p>
                    <ul>
                        <li><b>Puerto:</b> Selecciona el puerto COM al que estÃ¡ conectado el dispositivo.</li>
                        <li><b>Refrescar Puertos:</b> Actualiza la lista de puertos disponibles.</li>
                        <li><b>Conectar/Desconectar:</b> Inicia o termina la comunicaciÃ³n.</li>
                    </ul>
                """,
                "Control de MediciÃ³n": """
                    <h3>2.2. Control y ConfiguraciÃ³n de MediciÃ³n</h3>
                    <p>Configura y ejecuta los diferentes tipos de mediciones.</p>
                    <ul>
                        <li><b>Medir Referencia (Iâ‚€):</b> Mide el espectro del solvente o blanco. Este valor (Iâ‚€) es <strong>esencial</strong> para calcular Absorbancia/Transmitancia y para la sustracciÃ³n de blanco. Coloque la cubeta con el blanco y presione este botÃ³n antes de medir muestras.</li>
                        <li><b>Tipo de MediciÃ³n:</b>
                            <ul>
                                <li><b>Continuo:</b> Muestra espectros en tiempo real.</li>
                                <li><b>Ãšnico (Promediado):</b> Realiza 'M' lecturas y las promedia para obtener <u>un</u> espectro final que se guarda en la sesiÃ³n.</li>
                                <li><b>Secuencial (AutomÃ¡tico):</b> Realiza 'P' mediciones. Cada una es el promedio de 'M' sub-muestras. Los resultados se guardan automÃ¡ticamente en un archivo CSV.</li>
                            </ul>
                        </li>
                        <li><b>Iniciar/Detener MediciÃ³n:</b> Comienza o detiene el proceso segÃºn la configuraciÃ³n.</li>
                    </ul>
                """,
                "GestiÃ³n de Datos": """
                    <h3>2.3. GestiÃ³n de Datos</h3>
                    <p>Permite administrar los datos de la sesiÃ³n actual.</p>
                    <ul>
                        <li><b>Guardar Datos Acumulados:</b> Guarda la referencia (Iâ‚€) y las mediciones (I) de la sesiÃ³n (obtenidas en modo "Ãšnico") en un archivo CSV.</li>
                        <li><b>Guardar SelecciÃ³n Superpuesta:</b> Guarda Ãºnicamente los espectros seleccionados en la lista de superposiciÃ³n.</li>
                        <li><b>Limpiar Datos en Memoria:</b> Borra todos los datos de la sesiÃ³n (Iâ‚€, I, curvas activas) de la memoria interna.</li>
                        <li><b>Exportar GrÃ¡fico:</b> Guarda una imagen del grÃ¡fico de la pestaÃ±a actualmente visible.</li>
                    </ul>
                """,
                "CÃ¡lculo de ConcentraciÃ³n": """
                    <h3>2.4. CÃ¡lculo de ConcentraciÃ³n</h3>
                    <p>Estima la concentraciÃ³n 'C' de una muestra. El mÃ©todo de cÃ¡lculo depende de las opciones activadas:</p>
                    <ul>
                        <li><b>Requisito:</b> El tipo de grÃ¡fico en la pestaÃ±a "Espectro Principal" debe ser "Absorbancia".</li>
                        <li><b>ParÃ¡metros Base (Ley de Beer-Lambert):</b>
                            <ul>
                                <li><b>Coef. Absortividad Molar (Îµ) y Camino Ã“ptico (b):</b> Se usan para el cÃ¡lculo A = Îµbc si ninguna otra opciÃ³n estÃ¡ activa.</li>
                            </ul>
                        </li>
                        <li><b>Longitud de Onda para CÃ¡lculo:</b> Î» en la que se toma la absorbancia (A) para el cÃ¡lculo.</li>
                        <li><b>Usar Curva de SesiÃ³n (A_custom vs C):</b> Calcula 'C' usando la curva de calibraciÃ³n creada en la pestaÃ±a "CalibraciÃ³n". Tiene prioridad sobre la Ley de Beer-Lambert.</li>
                        <li><b>Usar Ajuste con Modelo de Transferencia:</b> Este mÃ©todo convierte la absorbancia medida (A_custom) a una absorbancia ajustada (A_ajustada) usando un modelo de transferencia y luego calcula 'C' con una calibraciÃ³n de referencia. Requiere configuraciÃ³n previa en el panel de "CalibraciÃ³n de Referencia".</li>
                        <li><b>Calcular y Registrar ConcentraciÃ³n:</b> Realiza el cÃ¡lculo y guarda el espectro de absorbancia actual con una etiqueta que incluye la concentraciÃ³n resultante.</li>
                    </ul>
                """,
                "CalibraciÃ³n de Referencia": """
                    <h3>2.5. Configurar CalibraciÃ³n de Referencia</h3>
                    <p>Permite ingresar los parÃ¡metros de una curva de calibraciÃ³n obtenida con un equipo de referencia. Estos parÃ¡metros son <b>necesarios</b> para que funcione la opciÃ³n "Usar Ajuste con Modelo de Transferencia".</p>
                     <ul>
                        <li><b>Tipo de CalibraciÃ³n:</b> Permite definir la calibraciÃ³n de referencia como una curva lineal (A_ref = mC + b) o un factor (A_ref = (ÎµL)C).</li>
                        <li><b>Guardar ParÃ¡metros:</b> Almacena los valores ingresados para la longitud de onda seleccionada.</li>
                    </ul>
                """
            },
            "PestaÃ±as de VisualizaciÃ³n": {
                 "PestaÃ±a: Espectro Principal": """
                    <h3>3.1. Espectro Principal</h3>
                    <p>Muestra grÃ¡ficamente los datos espectrales. Incluye una barra de herramientas para zoom, paneo y guardado de imagen.</p>
                    <h4>Tipo de GrÃ¡fico:</h4>
                    <ul>
                        <li><b>Intensidad:</b> Muestra los valores de intensidad lumÃ­nica (I).</li>
                        <li><b>Absorbancia:</b> Muestra A = -logâ‚â‚€(I / Iâ‚€). Requiere una mediciÃ³n de referencia (Iâ‚€) previa.</li>
                        <li><b>Transmitancia (%T):</b> Muestra (I/Iâ‚€)Ã—100. Requiere Iâ‚€.</li>
                    </ul>
                    <h4>PersonalizaciÃ³n del GrÃ¡fico:</h4>
                    <ul>
                        <li><b>Superponer mediciones guardadas:</b> Permite visualizar mÃºltiples mediciones de la sesiÃ³n actual juntas.</li>
                        <li><b>Opciones adicionales:</b> Permite usar escala logarÃ­tmica, mostrar marcadores en los puntos y visualizar la referencia Iâ‚€ en el modo de intensidad.</li>
                    </ul>
                """,
                "PestaÃ±a: Curva Conc. vs MediciÃ³n": """
                    <h3>3.2. Curva Conc. vs MediciÃ³n</h3>
                    <p>Permite construir un grÃ¡fico genÃ©rico de una variable X (ej. ConcentraciÃ³n, Tiempo) contra un valor Y medido directamente (Intensidad, Absorbancia, etc.) para una longitud de onda especÃ­fica.</p>
                    <h4>Flujo de trabajo:</h4>
                    <ol>
                        <li>Seleccione el tipo de valor Y y la longitud de onda.</li>
                        <li>Ingrese el valor correspondiente para el eje X.</li>
                        <li>Presione "Medir Valor Y Directamente".</li>
                        <li>Una vez obtenido el valor Y, presione "AÃ±adir Punto a la Curva".</li>
                    </ol>
                """,
                "PestaÃ±a: CalibraciÃ³n y Transferencia": """
                    <h3>3.3. CalibraciÃ³n y Transferencia</h3>
                    <p>Esta pestaÃ±a permite crear curvas de calibraciÃ³n y modelos de transferencia. Un selector en la parte superior permite elegir quÃ© grÃ¡fico visualizar.</p>
                    <h4>GrÃ¡fico: CalibraciÃ³n (A_custom vs C)</h4>
                    <p>Permite crear una curva de calibraciÃ³n de sesiÃ³n usando soluciones de concentraciÃ³n conocida.</p>
                    <ol>
                        <li>Mida Iâ‚€ en el panel de control principal.</li>
                        <li>Para cada estÃ¡ndar: ingrese su concentraciÃ³n, mida su absorbancia (A_custom) y aÃ±ada el punto.</li>
                        <li>Una vez tenga suficientes puntos, presione "Aplicar Curva(s)" para que pueda ser usada en el panel de "CÃ¡lculo de ConcentraciÃ³n".</li>
                    </ol>
                    <h4>GrÃ¡fico: Transferencia (A_ref vs A_custom)</h4>
                    <p>Permite crear un modelo matemÃ¡tico para correlacionar las mediciones de este equipo (A_custom) con las de un equipo de referencia (A_ref).</p>
                    <ol>
                        <li>Al aÃ±adir puntos de calibraciÃ³n, ingrese tambiÃ©n el valor de absorbancia medido en el equipo de referencia (A_ref).</li>
                        <li>El sistema ajustarÃ¡ una recta a los puntos (A_custom, A_ref).</li>
                        <li>Presione "Aplicar Curva(s)" para enviar este modelo a la aplicaciÃ³n principal.</li>
                    </ol>
                """
            },
            "Soporte y CrÃ©ditos": """
                <h3>4. Soporte y CrÃ©ditos</h3>
                <hr>
                <p>Para soporte, reporte de errores o sugerencias, por favor contacte al desarrollador.</p>
                <ul>
                    <li><b>Desarrollador:</b> Sebastian Herrera Betancur</li>
                    <li><b>Correo:</b> <a href="mailto:s.herrerab@uniandes.edu.co">s.herrerab@uniandes.edu.co</a></li>
                    <li><b>Grupo de InvestigaciÃ³n:</b> Biomicrosystems (<a href="https://github.com/Biomicrosystems">GitHub</a>)</li>
                </ul>
                <p>Al reportar un error, es Ãºtil incluir los pasos para reproducirlo y, si es posible, exportar el "Log de ComunicaciÃ³n" desde el menÃº Archivo.</p>
            """
        }
        return topics

    def _populate_tree(self, parent_item=None, dictionary=None):
        """Llena el QTreeWidget recursivamente a partir del diccionario de temas."""
        if dictionary is None:
            dictionary = self.help_topics
        if parent_item is None:
            parent_widget = self.tree_widget
        else:
            parent_widget = parent_item

        for key, value in dictionary.items():
            item = QTreeWidgetItem(parent_widget, [key])
            if isinstance(value, dict):
                # Es una categorÃ­a, llamada recursiva
                self._populate_tree(item, value)
            else:
                # Es un tema, guarda el contenido HTML
                item.setData(0, Qt.UserRole, value) 

            if parent_item is None: 
                item.setExpanded(True)


    def _on_tree_item_changed(self, current_item, previous_item):
        """Se activa al seleccionar un nuevo tema para mostrar su contenido."""
        if current_item:
            self._display_topic(current_item)

    def _display_topic(self, item):
        """Muestra el contenido HTML del tema seleccionado en el QTextBrowser."""
        html_content = item.data(0, Qt.UserRole) 
        if html_content:
            self.text_browser.setHtml(f"<html><body>{html_content}</body></html>")
        else:
            default_text = f"<h2>{item.text(0)}</h2><p>Seleccione un subtema especÃ­fico de la lista para ver su contenido detallado.</p>"
            if item.childCount() > 0:
                first_child = item.child(0)
                self.tree_widget.setCurrentItem(first_child) 
                return 
            self.text_browser.setHtml(f"<html><body>{default_text}</body></html>")
