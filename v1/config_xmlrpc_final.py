# -*- coding: utf-8 -*-
"""
config.py
=========
Configuración global del sistema colaborativo UR3e + UR5e con XML-RPC.
"""

# =============================================================================
# ROBOTS
# =============================================================================
UR3E_IP = "192.168.56.101"
UR5E_IP = "192.168.56.102"
PORT = 30002

# =============================================================================
# PC / XML-RPC
# =============================================================================
# IP del ordenador en la red Ethernet de los robots.
PC_IP = "192.168.56.2"
XMLRPC_PORT = 50080
XMLRPC_URL = f"http://{PC_IP}:{XMLRPC_PORT}/RPC2"

# Tiempo máximo que el PC espera hasta que termine UR5e.
WAIT_TIMEOUT_S = 1800

# =============================================================================
# ORÍGENES CALIBRADOS DE CADA ROBOT
# =============================================================================
# Centro del papel / zona común expresado en la base de cada robot.
# Formato: [x, y, z, rx, ry, rz]
# Para pruebas de comunicación, puedes poner una Z más alta si el robot no llega.
UR3E_TCP_ORIGEN = [-0.30000, -0.25000, 0.18000, 1.346, 2.839, 0.0]
UR5E_TCP_ORIGEN = [ 0.68387, -0.03000, 0.06000, 2.481, -1.927, 0.0]

# Si un robot está enfrentado al otro y dibuja invertido, cambia estos booleanos.
UR3E_ESPEJO_X = False
UR3E_ESPEJO_Y = False
UR5E_ESPEJO_X = True
UR5E_ESPEJO_Y = False

# =============================================================================
# ALCANCE
# =============================================================================
UR3E_MAX_REACH = 0.44
UR5E_MAX_REACH = 0.80

# =============================================================================
# IMAGEN / CONTORNOS
# =============================================================================
MAX_ANCHO_M = 0.09
EPSILON_PX = 0.7
DECIMATE_STEP = 1
MIN_PUNTOS_CONTORNO = 5
MIN_LONGITUD_PX = 20
MAX_PUNTOS_TOTAL = 1000

CANNY_FINO_LOW = 30
CANNY_FINO_HIGH = 90
CANNY_GRUESO_LOW = 80
CANNY_GRUESO_HIGH = 160

# =============================================================================
# MOVIMIENTO / SEGURIDAD
# =============================================================================
# Valores finos. Para pruebas rápidas puedes subir V_DIBUJO y reducir puntos.
V_DIBUJO = 0.002
V_SUBIDA = 0.010
A_DIBUJO = 0.008
Z_SUBIDA = 0.012
Z_PAPEL = 0.0025

V_HOME = 0.05
A_HOME = 0.05

# =============================================================================
# MODO PRUEBAS RÁPIDAS
# =============================================================================
# Si quieres probar comunicación sin perder tiempo, pon valores tipo:
# V_DIBUJO = 0.010
# V_SUBIDA = 0.040
# A_DIBUJO = 0.050
# V_HOME = 0.080
# A_HOME = 0.080
# MAX_PUNTOS_TOTAL = 120
# EPSILON_PX = 2.5
# DECIMATE_STEP = 4
