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
Define constantes y enumeraciones (Enum) para representar los diferentes
estados y modos de la aplicaciÃ³n, mejorando la legibilidad y previniendo
errores de tipeo.
"""
from enum import Enum, auto

class MeasurementType:
    """Define los tipos de mediciÃ³n que puede realizar el espectrofotÃ³metro."""
    CONTINUOUS = "Continuo"
    SINGLE_AVERAGED = "Ãšnico (Promediado)"
    SEQUENTIAL = "Secuencial (AutomÃ¡tico)"

class PlotType(Enum):
    """Define los tipos de grÃ¡ficos que se pueden visualizar."""
    INTENSITY = auto()
    ABSORBANCE = auto()
    TRANSMITTANCE = auto()

class AppState(Enum):
    """Define los estados operativos principales de la aplicaciÃ³n."""
    IDLE = auto()
    MEASURING_MAIN = auto()
    MEASURING_DIRECT = auto()
    CLOSING = auto()
