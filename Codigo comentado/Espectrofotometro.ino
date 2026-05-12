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
/*
 * ============================================================================
 * GuÃ­a de Funcionamiento y Uso
 * ============================================================================
 * Este sketch para Arduino controla un LED blanco y un sensor espectrÃ³metro AS726X.
 * 
 * Funcionalidades:
 * 1. Recibe comandos a travÃ©s del Monitor Serial (115200 baudios) de forma no bloqueante.
 * 2. El comando "blanco" simplemente enciende el LED en blanco (valor por defecto).
 * 3. El comando "calibrar" inicia una calibraciÃ³n:
 *      - Enciende el LED blanco, espera 50 ms (usando millis() de forma no bloqueante)
 *        y toma la mediciÃ³n.
 *      - Se envÃ­a por Serial con el formato: "calblanco,<violeta>,<azul>,<verde>,<amarillo>,<naranja>,<rojo>".
 * 4. El comando "empezar" inicia la mediciÃ³n continua:
 *      - Se envÃ­a de forma continua una lÃ­nea con el formato:
 *        "blanco,<violeta>,<azul>,<verde>,<amarillo>,<naranja>,<rojo>"
 *      - No se emplea ningÃºn retardo en la mediciÃ³n continua.
 * 5. El comando "detener" finaliza la mediciÃ³n continua.
 * 6. Si se ingresa un comando no reconocido, se informa con "Comando no reconocido".
 * ============================================================================
 */

#include <Wire.h>
#include "AS726X.h"

// Pin para el LED blanco (usar un pin PWM adecuado; en este ejemplo se usa el 13)
const int LED_WHITE = 13;

AS726X sensor; // Objeto para el sensor AS726X (espectrÃ³metro)

// Variables de estado
bool measuring = false;         // Modo de mediciÃ³n continua
bool calibrating = false;       // Modo de calibraciÃ³n activado

// Variables para la calibraciÃ³n basada en millis()
int calibrationState = 0;       // 0: Encender LED y registrar tiempo; 1: Esperar 50ms y medir
unsigned long lastCalibrationTime = 0; // Tiempo de inicio para la espera
const unsigned long CALIBRATION_DELAY_MS = 50;  // Tiempo de espera en calibraciÃ³n (ms)

// Variables para lectura no bloqueante de comandos Serial
#define CMD_BUFFER_SIZE 64
char cmdBuffer[CMD_BUFFER_SIZE];
uint8_t cmdIndex = 0;

// FunciÃ³n que toma las mediciones del sensor y las envÃ­a por Serial
// El "prefix" indica el prefijo de salida (por ejemplo, "blanco" o "calblanco")
void printMeasurements(const String &prefix) {
  sensor.takeMeasurements();
  float measurements[6] = {
    sensor.getCalibratedViolet(),
    sensor.getCalibratedBlue(),
    sensor.getCalibratedGreen(),
    sensor.getCalibratedYellow(),
    sensor.getCalibratedOrange(),
    sensor.getCalibratedRed()
  };

  Serial.print(prefix);
  for (int i = 0; i < 6; i++) {
    Serial.print(",");
    Serial.print(measurements[i], 2); // 2 decimales
  }
  Serial.println();
}

// FunciÃ³n para encender el LED blanco
void setWhiteLEDOn() {
  analogWrite(LED_WHITE, 255); // brillo mÃ¡ximo
}

// FunciÃ³n para apagar el LED (si se requiere)
void setWhiteLEDOff() {
  analogWrite(LED_WHITE, 0);
}

// Procesa el comando recibido a travÃ©s del Serial
void processCommand(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd.equalsIgnoreCase("blanco")) {
    // Asegura que el LED blanco se encienda (por defecto)
    setWhiteLEDOn();
  }
  else if (cmd.equalsIgnoreCase("calibrar")) {
    calibrating = true;
    measuring = false;   // Se desactiva mediciÃ³n continua durante calibraciÃ³n
    calibrationState = 0;
  }
  else if (cmd.equalsIgnoreCase("empezar")) {
    measuring = true;
    Serial.println(F("MediciÃ³n iniciada"));
  }
  else if (cmd.equalsIgnoreCase("detener")) {
    measuring = false;
    Serial.println(F("MediciÃ³n detenida"));
  }
  else {
    Serial.println(F("Comando no reconocido"));
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  
  // Verifica la correcta inicializaciÃ³n del sensor AS726X
  if (!sensor.begin()) {
    Serial.println(F("Error: No se pudo inicializar el sensor AS726X"));
    while (1) { } // Detiene la ejecuciÃ³n en caso de error
  }
  
  // Configura el pin del LED blanco como salida
  pinMode(LED_WHITE, OUTPUT);
  
  // Enciende el LED blanco por defecto
  setWhiteLEDOn();
}

void loop() {
  // Lectura no bloqueante de comandos Serial
  while (Serial.available() > 0) {
    char inChar = Serial.read();
    if (inChar == '\n' || inChar == '\r') {
      if (cmdIndex > 0) {
        cmdBuffer[cmdIndex] = '\0';
        String cmd = String(cmdBuffer);
        processCommand(cmd);
        cmdIndex = 0; // Reinicia el buffer
      }
    } else {
      if (cmdIndex < CMD_BUFFER_SIZE - 1) {
        cmdBuffer[cmdIndex++] = inChar;
      }
    }
  }

  // MÃ¡quina de estados para la calibraciÃ³n
  if (calibrating) {
    if (calibrationState == 0) {
      // Enciende el LED blanco y registra el tiempo
      setWhiteLEDOn();
      lastCalibrationTime = millis();
      calibrationState = 1;
    } else if (calibrationState == 1) {
      // Espera 50 ms de forma no bloqueante y luego toma la mediciÃ³n
      if (millis() - lastCalibrationTime >= CALIBRATION_DELAY_MS) {
        printMeasurements("calblanco");
        calibrating = false;  // Finaliza la calibraciÃ³n
      }
    }
  }
  // MediciÃ³n continua sin retardo (sin delay)
  else if (measuring) {
    printMeasurements("blanco");
  }
}

