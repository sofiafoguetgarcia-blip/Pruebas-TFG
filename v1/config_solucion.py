# -*- coding: utf-8 -*-
"""
config.py
=========
Parámetros globales del sistema de dibujo colaborativo UR3e + UR5e.
"""

# =============================================================================
# ROBOTS — IPs y puertos
# =============================================================================
UR3E_IP   = "192.168.56.101"
UR5E_IP   = "192.168.56.102"
PORT      = 30002
PORT_DASH = 29999

# =============================================================================
# COMUNICACIÓN PC COMO INTERMEDIARIO
# =============================================================================
# IP del PC en la misma red que los robots. Compruébala con ipconfig.
PC_IP = "192.168.56.2"

# Puerto donde el PC escucha el aviso LISTO del UR3e.
PORT_UR3_DONE = 50001

# Mensaje que manda UR3e al PC cuando termina.
SYNC_MSG = "LISTO"

# =============================================================================
# TRANSFORMACIONES TCP → BASE DE CADA ROBOT
# Origen coincidente en el espacio de trabajo compartido/papel.
# =============================================================================
UR3E_TCP_ORIGEN = [-0.24715, -0.13962, 0.07344, 1.360, 2.832, 0.0]
UR5E_TCP_ORIGEN = [ 0.68387, -0.03000,  0.00221,  2.481, -1.927, 0.0]

# =============================================================================
# ALCANCE MÁXIMO ÚTIL
# =============================================================================
UR3E_MAX_REACH = 0.44
UR5E_MAX_REACH = 0.80

# =============================================================================
# IMAGEN / CONTORNOS
# =============================================================================
MAX_ANCHO_M         = 0.09
EPSILON_PX          = 0.7
DECIMATE_STEP       = 1
MIN_PUNTOS_CONTORNO = 5
MIN_LONGITUD_PX     = 20
MAX_PUNTOS_TOTAL    = 1000

CANNY_FINO_LOW      = 30
CANNY_FINO_HIGH     = 90
CANNY_GRUESO_LOW    = 80
CANNY_GRUESO_HIGH   = 160

# =============================================================================
# MOVIMIENTO / SEGURIDAD
# =============================================================================
V_BAJA      = 0.008
V_DIBUJO    = 0.5
V_SUBIDA    = 0.1
A_DIBUJO    = 0.008
Z_PAPEL     = 0.020
Z_SUBIDA    = 0.030
F_UMBRAL    = 1.0

V_HOME      = 0.05
A_HOME      = 0.05
