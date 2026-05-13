# -*- coding: utf-8 -*-
"""
config.py
=========
Configuración limpia para demo UR5e + UR3e leyendo el JSON TAL CUAL.

Criterio principal:
- robot_x y robot_y del JSON ya están en coordenadas del UR5e, en milímetros.
- vision.py solo divide entre 1000.
- No hay offsets por pieza.
- No se usa el ángulo de visión para girar la muñeca.
"""

# =============================================================================
# ROBOTS
# =============================================================================
UR3E_IP = "192.168.56.101"
UR5E_IP = "192.168.56.102"
PORT = 30002
PC_IP = "192.168.56.2"

PORT_UR5_LISTO_UR3 = 50001
PORT_UR3_LISTO_UR5 = 50002
SYNC_MSG_LISTO = "LISTO"

# =============================================================================
# POSES UR5e / UR3e
# =============================================================================
# HOME del UR5e. Se usa para retirarse y para empezar cada fase.
UR5E_HOME_POSE = [0.54216, -0.32723, 0.38191, 3.066, -0.685, 0.0]

# Orientación REAL medida en tablet sobre el centro de la pieza:
# [167.95, -394.41, Z, 2.979, -0.997, 0.0]
# Se usa SIEMPRE para coger/devolver piezas, independientemente del ángulo del JSON.
UR5E_PICK_ORIENTATION = [2.79604, -1.43234, 0.00003]

UR3E_HOME_POSE = [0.31875, -0.05563, 0.07194, 2.974, -1.013, 0.0]

# Zona compartida vista desde cada robot.
DROP_ZONE_UR5E = [-0.04511, 0.51128, -0.0102, 1.9626, 2.482, 0.0]
DROP_ZONE_UR3E = [0.0573, 0.34812, -0.00126, 2.84, 1.344, 0.0]

# Punto alto para entrar/salir de la zona compartida.
UR5E_DROP_APPROACH_POSE = [-0.04511, 0.51128, 0.2987, 1.9626, 2.482, 0.0]

# =============================================================================
# ALTURAS / FUERZA
# =============================================================================
Z_APROX_UR5 = 0.250
Z_SUBIDA_UR5 = 0.080
Z_PIEZA_OFFSET = 0.003
F_UMBRAL_UR5 = 1.5

# =============================================================================
# VENTOSA / SIMULACIÓN
# =============================================================================
SIMULAR_VENTOSA = True
VENTOSA_DO_PIN = 0
VENTOSA_DELAY_ON = 0.4
VENTOSA_DELAY_OFF = 0.3

# =============================================================================
# MOVIMIENTOS UR5e
# =============================================================================
V_APROX = 0.080
V_BAJA_UR5 = 0.008
V_TRASLADO = 0.125
V_DEPOSITO = 0.008
A_LENTO = 0.030
A_RAPIDO = 0.120
V_HOME = 0.100
A_HOME = 0.030

# =============================================================================
# MOVIMIENTOS UR3e
# =============================================================================
V_BAJA_UR3 = 0.006
V_DIBUJO = 0.010
V_SUBIDA = 0.020
A_DIBUJO = 0.004
Z_PAPEL = 0.0008
Z_SUBIDA = 0.025
F_UMBRAL_UR3 = 1.2

# =============================================================================
# ESCALADO DEL DIBUJO
# =============================================================================
DRAWING_SCALE_ON_TILE = 0.55
MAX_DRAWING_WIDTH_M = 0.080
MIN_DRAWING_WIDTH_M = 0.020

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
