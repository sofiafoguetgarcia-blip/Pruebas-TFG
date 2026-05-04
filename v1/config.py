# -*- coding: utf-8 -*-
"""
config.py
=========
Parámetros globales del sistema de dibujo colaborativo UR3e + UR5e.
Modifica solo este archivo para ajustar el comportamiento del sistema.
"""

# =============================================================================
# ROBOTS — IPs y puertos
# =============================================================================
# Puerto 30002: Primary Interface (URScript via texto plano)
# Puerto 29999: Dashboard Server (comandos de estado)

UR3E_IP   = "192.168.56.101"
UR5E_IP   = "192.168.56.102"
PORT      = 30002          # Puerto de envío de URScript
PORT_DASH = 29999          # Puerto Dashboard (para confirmación de estado)

# Puerto en el que cada robot escucha el aviso "he terminado" del otro.
# El UR3e escucha en este puerto; el UR5e también escucha en este puerto
# (cada uno en su propia IP). El mensaje es simplemente "LISTO\n".
PORT_SYNC = 50001

# =============================================================================
# TRANSFORMACIONES TCP → BASE DE CADA ROBOT
# Origen coincidente en el espacio de trabajo compartido (el papel).
# Estas son las poses TCP que corresponden al centro del papel
# expresadas en el frame BASE de cada robot.
#
# Formato: [x_m, y_m, z_m, rx_rad, ry_rad, rz_rad]
# =============================================================================
UR3E_TCP_ORIGEN = [-0.52777, -0.01601,  0.00821,  1.346,  2.839, 0.0]
UR5E_TCP_ORIGEN = [ 0.68387, -0.03000,  0.00221,  2.481, -1.927, 0.0]

# =============================================================================
# ALCANCE MÁXIMO ÚTIL (metros desde la base de cada robot)
# Se usa para filtrar qué trayectorias puede alcanzar cada robot con seguridad.
# El UR3e tiene alcance nominal 500mm; usamos 0.44m como margen seguro.
# El UR5e tiene alcance nominal 850mm; usamos 0.80m como margen seguro.
# =============================================================================
UR3E_MAX_REACH = 0.44   # metros — margen conservador sobre 500mm nominal
UR5E_MAX_REACH = 0.80   # metros — margen conservador sobre 850mm nominal

# =============================================================================
# IMAGEN / CONTORNOS
# =============================================================================
MAX_ANCHO_M         = 0.09      # Ancho máximo del dibujo en metros
EPSILON_PX          = 0.7       # Tolerancia approxPolyDP
DECIMATE_STEP       = 1         # Saltar puntos (1 = sin decimación)
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
V_BAJA      = 0.1     # Velocidad de descenso para detectar mesa (m/s)
V_DIBUJO    = 0.05     # Velocidad de trazado (m/s)
V_SUBIDA    = 0.010     # Velocidad de subida entre trazos (m/s)
A_DIBUJO    = 0.008     # Aceleración durante el dibujo (m/s²)
Z_SUBIDA    = 0.012     # Altura de seguridad sobre el papel (m)

# Offset sobre el punto de contacto con la mesa.
# Si no pinta: bajar. Si aprieta demasiado: subir.
Z_PAPEL     = 0.0025    # metros

F_UMBRAL    = 1.0       # Fuerza mínima de contacto (N)

# Velocidad y aceleración para movimientos de home y aproximación
V_HOME      = 0.05      # m/s — movimiento hacia/desde home
A_HOME      = 0.05      # m/s²

# =============================================================================
# SINCRONIZACIÓN
# =============================================================================
# Tiempo máximo (segundos) que el UR5e espera el aviso del UR3e antes de abortar.
SYNC_TIMEOUT = 600      # 10 minutos

# Mensaje de sincronización que el UR3e envía al UR5e al terminar
SYNC_MSG = "LISTO"
