# -*- coding: utf-8 -*-
"""
robot_comm.py
=============
Envío de scripts URScript a los robots mediante TCP/IP.

El PC central envía los dos scripts casi simultáneamente:
  - El UR5e arranca su script primero (para que el servidor socket
    esté escuchando antes de que el UR3e intente conectarse).
  - El UR3e arranca a continuación.

Ambos robots funcionan de forma autónoma a partir de ese momento.
El PC no necesita mantener la conexión abierta.
"""

import socket
import time
import logging
import threading

from config_v0 import UR3E_IP, UR5E_IP, PORT

log = logging.getLogger(__name__)


def _enviar(ip: str, port: int, script: str, timeout: float = 5.0, pausa: float = 2.0) -> None:
    """Envía un URScript a un robot por TCP."""
    log.info(f"  Conectando a {ip}:{port}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((ip, port))
        s.sendall((script + "\n").encode("utf-8"))
        log.info(f"  Script enviado a {ip} ({len(script)} chars)")
        time.sleep(pausa)
    log.info(f"  Conexión cerrada: {ip}")


def enviar_scripts_dual(
    script_ur3e: str,
    script_ur5e: str,
    ip_ur3e: str = UR3E_IP,
    ip_ur5e: str = UR5E_IP,
    port: int    = PORT,
) -> None:
    """
    Envía los dos scripts al sistema dual de robots.

    Orden de envío:
      1. UR5e primero — para que su servidor socket esté listo antes de
         que el UR3e intente conectarse al final de su programa.
      2. UR3e a continuación (con 1s de margen).

    Parameters
    ----------
    script_ur3e : URScript completo para el UR3e
    script_ur5e : URScript completo para el UR5e
    """
    log.info("=" * 55)
    log.info("Enviando scripts al sistema dual...")
    log.info("=" * 55)

    # Paso 1: UR5e primero (servidor de sincronización)
    log.info(f"[1/2] Enviando script al UR5e ({ip_ur5e})...")
    try:
        _enviar(ip_ur5e, port, script_ur5e)
    except OSError as e:
        raise ConnectionError(f"No se pudo conectar al UR5e ({ip_ur5e}:{port}): {e}")

    # Pequeña pausa para que el UR5e levante su socket servidor
    log.info("Esperando 2s para que el UR5e levante el servidor de sincronización...")
    time.sleep(2.0)

    # Paso 2: UR3e
    log.info(f"[2/2] Enviando script al UR3e ({ip_ur3e})...")
    try:
        _enviar(ip_ur3e, port, script_ur3e)
    except OSError as e:
        raise ConnectionError(f"No se pudo conectar al UR3e ({ip_ur3e}:{port}): {e}")

    log.info("=" * 55)
    log.info("Ambos scripts enviados. Los robots operan de forma autónoma.")
    log.info("Sigue el progreso en las tablets de cada robot (textmsg).")
    log.info("=" * 55)
