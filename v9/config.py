# -*- coding: utf-8 -*-
"""
config.py
=========
Configuración del proyecto UR5e + UR3e para una demo realista sin cámara real
ni ventosa real.

Flujo:
1) El PC detecta una baldosa en una imagen offline.
2) UR5e simula recogerla con ventosa y la lleva a la zona compartida.
3) UR3e dibuja encima, adaptando el tamaño del dibujo a la baldosa detectada.
4) UR5e simula recogerla de la zona compartida y devolverla al origen.
"""

# =============================================================================
# ROBOTS
# =============================================================================
UR3E_IP = "192.168.56.101"
UR5E_IP = "192.168.56.102"
PORT = 30002                        # Puerto estándar para enviar comandos URScript

# IP del PC en la red de los robots
PC_IP = "192.168.56.2"

# Puertos de sincronización robot -> PC
PORT_UR5_LISTO_UR3 = 50001          # Canal para que el UR5 avise que ya dejó la baldosa
PORT_UR3_LISTO_UR5 = 50002          # Canal para que el UR3 avise que ya terminó de dibujar
SYNC_MSG_LISTO = "LISTO"            # El mensaje de texto que se envían entre ellos

# =============================================================================
# HOMES / POSES SEGURAS
# =============================================================================
UR5E_HOME_POSE = [0.14429, -0.14454, 0.65794, 0.0, 0.0, 4.196]
UR3E_HOME_POSE = [0.42863, -0.10136, 0.22627, 2.898, -1.214, 0.0]

# Punto físico de zona compartida visto desde cada robot.
DROP_ZONE_UR5E = [0.01939, 0.4482, -0.41385, 0.107, -3.14, 0.0]

# UR3e = robot pequeño, mesa derecha
DROP_ZONE_UR3E = [-0.0621, 0.40344, 0.1414, 2.341, 2.095, 0.0]

UR5E_SAFE_TRANSFER_POSE = [0.0167, -0.50046, 0.40902, 0.918, -3.005, 0.000]

UR5E_DROP_APPROACH_POSE = [-0.06345, 0.45836, 0.36156, 2.966, 1.035, 0.0]

# Altura segura sobre mesa
Z_APROX_UR5 = 0.250                 # Altura a la que se mueve el UR5 para no chocar con nada
Z_SUBIDA_UR5 = 0.080                # Cuánto levanta la pieza tras recogerla

# Como solo tienes lápiz, no activar salida digital real
SIMULAR_VENTOSA = True

# =============================================================================
# VISIÓN OFFLINE
# =============================================================================
# Estos valores convierten píxeles -> metros en la base del UR5e.
# Son de prueba. Debes ajustarlos con puntos reales de la mesa.
CAMERA_ORIGIN_X_M = 0.50
CAMERA_ORIGIN_Y_M = 0.10
CAMERA_SCALE_X = 0.00030
CAMERA_SCALE_Y = 0.00030

MIN_AREA_BALDOSA = 5000
MAX_AREA_BALDOSA = 400000

# Elige qué baldosa usar si la imagen tiene varias.
# Opciones: "largest", "leftmost", "rightmost", "topmost", "bottommost"
TILE_SELECTION_MODE = "largest"

# =============================================================================
# ESCALADO DEL DIBUJO
# =============================================================================
# El dibujo ocupará como máximo este porcentaje del lado menor de la baldosa.
"OSO"
#DRAWING_SCALE_ON_TILE = 0.90        # Si la baldosa mide 20cm, el dibujo ocupará como máximo 18cm.
#MAX_DRAWING_WIDTH_M = 0.180         # Si el dibujo es muy grande, se limita a este tamaño real máximo.
#MIN_DRAWING_WIDTH_M = 0.020

"FLOR"
DRAWING_SCALE_ON_TILE = 0.55
MAX_DRAWING_WIDTH_M = 0.080
MIN_DRAWING_WIDTH_M = 0.020
# =============================================================================
# MOVIMIENTOS UR5e: MANIPULACIÓN SIMULADA
# =============================================================================
V_APROX = 0.080
V_BAJA_UR5 = 0.008
V_TRASLADO = 0.125
V_DEPOSITO = 0.008
A_LENTO = 0.030
A_RAPIDO = 0.120

Z_APROX_UR5 = 0.250       # altura segura para ir por encima de pieza/zona compartida
Z_SUBIDA_UR5 = 0.080      # subida tras contacto
Z_PIEZA_OFFSET = 0.003    # margen sobre la superficie detectada
F_UMBRAL_UR5 = 1.5

# Como no hay ventosa real, por defecto NO activa ninguna salida digital.
SIMULAR_VENTOSA = True
VENTOSA_DO_PIN = 0
VENTOSA_DELAY_ON = 0.4
VENTOSA_DELAY_OFF = 0.3

# =============================================================================
# MOVIMIENTOS UR3e: DIBUJO
# =============================================================================
V_BAJA_UR3 = 0.006
V_DIBUJO = 0.010
V_SUBIDA = 0.020
A_DIBUJO = 0.004
V_HOME = 0.100
A_HOME = 0.030

Z_PAPEL = 0.0008
Z_SUBIDA = 0.025
F_UMBRAL_UR3 = 2.0

# =============================================================================
# IMAGEN DE DIBUJO / CONTORNOS
# =============================================================================
EPSILON_PX = 0.7
DECIMATE_STEP = 2
MIN_PUNTOS_CONTORNO = 3
MIN_LONGITUD_PX = 5
MAX_PUNTOS_TOTAL = 1200

CANNY_FINO_LOW = 30
CANNY_FINO_HIGH = 90
CANNY_GRUESO_LOW = 80
CANNY_GRUESO_HIGH = 160

OFFSETS_POR_PIEZA_M = {
    1: (0.072, -0.069),
    2: (0.000, 0.000),
    3: (0.000, 0.000),
    4: (0.000, 0.000),
    5: (0.000, 0.000),
    6: (0.000, 0.000),
    7: (0.000, 0.000),
    8: (0.000, 0.000),
    9: (0.000, 0.000),
}