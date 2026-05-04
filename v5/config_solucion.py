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
PORT      = 30002 # Puerto estándar para enviar URScript a los robots. 
PORT_DASH = 29999 # Puerto del dashboard server, para leer estado del robot.

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
UR3E_MAX_REACH = 0.25 # El UR3e es más pequeño, así que le damos un alcance máximo de 30 cm desde su origen calibrado.
UR5E_MAX_REACH = 0.80 # El UR5e es más grande, así que le damos un alcance máximo de 80 cm desde su origen calibrado.

# =============================================================================
# IMAGEN / CONTORNOS
# =============================================================================
MAX_ANCHO_M         = 0.065 # Ancho máximo del dibujo en metros. Si la imagen es más ancha, se escala proporcionalmente.
EPSILON_PX          = 0.7   # Distancia máxima en píxeles para considerar que dos puntos del contorno pertenecen al mismo segmento.
DECIMATE_STEP       = 1     # Cada cuántos puntos del contorno se toma uno para formar la trayectoria. 1 = todos, 2 = la mitad, etc.
MIN_PUNTOS_CONTORNO = 5     # Un contorno con menos puntos no se considera una trayectoria válida (puede ser ruido).
MIN_LONGITUD_PX     = 20    # Un contorno con longitud menor a este umbral en píxeles se descarta (puede ser ruido).
MAX_PUNTOS_TOTAL    = 2000  # Si el número total de puntos de todas las trayectorias supera este umbral, se detiene el programa para evitar sobrecarga.

CANNY_FINO_LOW      = 30    # Umbral bajo para bordes finos (más sensibles, detectan detalles pero también ruido).
CANNY_FINO_HIGH     = 90    # Umbral alto para bordes finos (menos sensibles, detectan solo bordes más fuertes).
CANNY_GRUESO_LOW    = 80    # Umbral bajo para bordes gruesos (más sensibles, detectan detalles pero también ruido).
CANNY_GRUESO_HIGH   = 160   # Umbral alto para bordes gruesos (menos sensibles, detectan solo bordes más fuertes).

# =============================================================================
# MOVIMIENTO / SEGURIDAD / FUERZA
# =============================================================================
V_BAJA      = 0.008         # Velocidad baja para movimientos delicados (por ejemplo, al acercarse al papel).
V_DIBUJO    = 0.1           # Velocidad de dibujo. No es necesario que sea muy alta, y velocidades muy altas pueden causar vibraciones o pérdida de precisión.
V_SUBIDA    = 0.1           # Velocidad para movimientos de subida/descenso (Z). Es mejor que sea más lenta para evitar golpes contra el papel.
A_DIBUJO    = 0.008         # Aceleración para movimientos de dibujo. Al igual que la velocidad, es mejor que sea baja para mejorar la precisión.
Z_PAPEL     = 0.020         # Altura Z a la que el robot considera que está tocando el papel. Este valor puede necesitar ajustes según tu calibración y el grosor del lápiz.
Z_SUBIDA    = 0.030         # Altura Z para movimientos de traslado (cuando el lápiz está levantado). Debe ser suficientemente alta para evitar colisiones con el papel o con las trayectorias dibujadas.
F_UMBRAL    = 1.0           # Fuerza umbral para detectar la superficie del papel (N). Si el robot detecta una fuerza mayor a este valor al descender, considera que ha tocado la superficie.
F_DETECT    = F_UMBRAL      # Alias de F_UMBRAL para compatibilidad con main.py.
F_DIBUJO    = 3.0           # Fuerza de contacto durante el dibujo (N). El robot mantiene esta fuerza contra el papel usando force_mode. Ajustar si el lápiz presiona demasiado (bajar) o muy poco (subir).

V_HOME      = 0.05          # Velocidad para movimientos a home/origen. Puede ser más rápida que la velocidad de dibujo, pero no demasiado para evitar golpes.
A_HOME      = 0.05          # Aceleración para movimientos a home/origen. Al igual que la velocidad, puede ser más alta que la de dibujo, pero sin excederse para mantener la seguridad.    
