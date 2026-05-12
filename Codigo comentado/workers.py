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
Define el 'SerialWorker', que gestiona la comunicaciÃ³n serial en un hilo
separado para no bloquear la interfaz grÃ¡fica.

Emite seÃ±ales para notificar al hilo principal sobre datos recibidos,
errores o la pÃ©rdida de conexiÃ³n, siguiendo las mejores prÃ¡cticas de Qt.
"""
import serial
from PyQt5.QtCore import pyqtSignal, QThread, QObject

class SerialWorker(QObject):
    """Worker que se ejecuta en un QThread para manejar la lectura serial."""
    # SeÃ±ales para comunicar eventos al hilo principal
    data_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    connection_lost = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self, serial_instance):
        """Inicializa el worker con la instancia del puerto serial."""
        super().__init__()
        self.ser = serial_instance
        self._running = False
        self.consecutive_errors = 0
        self.MAX_CONSECUTIVE_ERRORS = 5

    def run(self):
        """Bucle principal del worker que lee el puerto serial continuamente."""
        self._running = True
        while self._running and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='replace').strip()
                    if line:
                        self.data_received.emit(line)
                        self.consecutive_errors = 0 # Reinicia contador tras lectura exitosa
                else:
                    QThread.msleep(20) # Pausa para no saturar la CPU
            except serial.SerialException as e:
                # Si ocurren demasiados errores seguidos, asume desconexiÃ³n
                if self._running:
                    self.consecutive_errors += 1
                    error_msg = f"Error de lectura serial: {e}"
                    self.error_occurred.emit(error_msg)
                    if self.consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                        self.error_occurred.emit(
                            f"Demasiados errores ({self.consecutive_errors}). Asumiendo desconexiÃ³n."
                        )
                        self.connection_lost.emit()
                        self._running = False
            except (IOError, TypeError) as e: 
                # Detiene el worker ante errores inesperados
                if self._running:
                     self.error_occurred.emit(f"Error inesperado en worker: {e}")
                self._running = False
        self.finished.emit()

    def stop(self):
        """Detiene el bucle de ejecuciÃ³n del worker de forma segura."""
        self._running = False
