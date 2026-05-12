# AS726X Multi-channel Spectrophotometer Suite

![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Framework](https://img.shields.io/badge/framework-PyQt5-green.svg)
![Status](https://img.shields.io/badge/Status-Confidential-orange.svg)

---

### ⚠️ **IMPORTANT: INTELLECTUAL PROPERTY NOTICE** ⚠️

**This repository contains proprietary and confidential information. ALL RIGHTS ARE RESERVED.**

No part of this software, including source code, designs, and documentation, may be used, copied, modified, or distributed without the express written permission of:
1.  **The Lead Researcher / Author**
2.  **Universidad de los Andes**
3.  **The Biomicrosystems Research Group**

Please refer to the [LICENSE](LICENSE) file for the full legal terms. If you do not have authorization, you must leave this repository and delete any local copies immediately.

---

## 🔬 Project Overview

The **AS726X Multi-channel Spectrophotometer Suite** is a high-precision, low-cost multispectral analysis platform designed for professional and academic research. It provides a robust, thread-safe environment for real-time spectral data acquisition, scientific calibration, and advanced concentration analysis.

### 🌟 Key Scientific Capabilities

*   **Multispectral Precision**: Discrete wavelength acquisition across 6 bands (450nm - 650nm) using the AS726X sensor.
*   **Advanced Concentration Engine**:
    *   **Beer-Lambert Law Integration**: Direct calculation of concentration ($C$) based on molar absorptivity ($\epsilon$) and path length ($b$).
    *   **Dynamic Calibration**: Support for session-based calibration curves ($A_{custom}$ vs $C$).
    *   **Cross-Device Validation**: Transfer models for adjusting custom absorbance readings to reference standards.
*   **Intelligent Baseline Management**: Automated $I_0$ reference measurement and blank subtraction for drift-free analysis.
*   **Kinetic Studies**: Support for continuous, single-averaged, and sequential measurement modes.

## 💻 Technical Architecture

The system is engineered using a modular **State-Controller-View (SCV)** pattern to ensure high performance and stability on platforms like the Raspberry Pi:

*   **Asynchronous Processing**: Non-blocking serial I/O using `QThread` and dedicated `SerialWorker` objects to maintain UI responsiveness during high-frequency measurements.
*   **Real-time Visualization**: Interactive spectral plotting powered by `Matplotlib`, featuring dynamic scaling, logarithmic transforms, and spectral superimposition.
*   **State Persistence**: Centralized management of calibration states, measurement history, and system configurations.
*   **Premium UX/UI**: A professional PyQt5 interface supporting native **Dark and Light modes**, collapsible control panels, and integrated help documentation.

## 🛠️ Technology Stack

| Component | Technology |
| :--- | :--- |
| **Backend** | Python 3.10+ |
| **Frontend** | PyQt5 (Custom Design System) |
| **Scientific Logic** | NumPy, SciPy (Linear Regression, Statistics) |
| **Data Visualization** | Matplotlib (Scientific Plotting) |
| **Hardware Orchestration** | Arduino (C++) / I2C Bus Management |
| **Hardware Interface** | Serial communication (PySerial) |

## 📂 Repository Structure

*   **`Codigo comentado/`**: Fully documented source code (Python & Arduino).
*   **`Diseño/`**: Mechanical designs and microfluidic system specifications (CAD/PDF).
*   **`Diagrama de clases/`**: UML architectural documentation.
*   **`Manuales/`**: Operational and calibration guides.
*   **`Espectrophotometer.pdf`**: Comprehensive scientific whitepaper and hardware specs.

---

## 🔒 Access & Authorization

This project is part of a restricted research initiative. To request access for peer review or collaborative purposes, please contact the **Biomicrosystems Research Group**.

---
*Developed by the Biomicrosystems Team.*
