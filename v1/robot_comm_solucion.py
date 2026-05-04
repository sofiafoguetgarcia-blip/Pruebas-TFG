# -*- coding: utf-8 -*-
"""
robot_comm.py
=============
Comunicación estable para sistema UR3e + UR5e.

Estrategia:
  1. El PC abre un servidor TCP en PORT_UR3_DONE.
  2. El PC envía el script al UR3e.
  3. El UR3e dibuja y, al terminar, conecta al PC y envía LISTO.
  4. El PC recibe LISTO.
  5. El PC envía entonces el script al UR5e.

Esto evita intentar que un robot haga de servidor TCP, que es lo que estaba fallando.
"""

import socket
import time
import logging

from config_solucion import UR3E_IP, UR5E_IP, PORT, PORT_UR3_DONE, SYNC_MSG

log = logging.getLogger(__name__)


def _enviar(ip: str, port: int, script: str, timeout: float = 5.0, pausa: float = 2.0) -> None:
    """Envía un URScript a un robot por TCP."""
    log.info(f"Conectando a {ip}:{port}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((ip, port))
        s.sendall((script + "\n").encode("utf-8"))
        log.info(f"Script enviado a {ip} ({len(script)} caracteres)")
        time.sleep(pausa)
    log.info(f"Conexión cerrada: {ip}")


def _crear_servidor_ur3_done(timeout: float = 1200.0):
    """Crea el servidor del PC para recibir LISTO del UR3e."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT_UR3_DONE))
    srv.listen(1)
    srv.settimeout(timeout)
    log.info(f"PC escuchando LISTO del UR3e en puerto {PORT_UR3_DONE}...")
    return srv

def esperar_listo_ur3e():
    import socket

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 50001))
    srv.listen(1)

    log.info("PC esperando LISTO del UR3e en puerto 50001...")

    conn, addr = srv.accept()
    log.info(f"Conexión recibida desde: {addr}")

    data = conn.recv(1024).decode("utf-8", errors="ignore")
    log.info(f"Mensaje recibido del UR3e: {data}")

    conn.close()
    srv.close()

    if "LISTO" not in data:
        raise ConnectionError(f"Mensaje inesperado del UR3e: {data}")


def enviar_scripts_dual(script_ur3e, script_ur5e, ip_ur3e, ip_ur5e, port):
    log.info("Abriendo servidor PC para esperar al UR3e...")

    # Abrir servidor ANTES de enviar al UR3e
    import threading

    error_sync = []

    def servidor():
        try:
            esperar_listo_ur3e()
        except Exception as e:
            error_sync.append(e)

    hilo = threading.Thread(target=servidor)
    hilo.start()

    time.sleep(1.0)

    log.info("Enviando script al UR3e...")
    _enviar(ip_ur3e, port, script_ur3e)

    log.info("Esperando a que UR3e termine y avise al PC...")
    hilo.join()

    if error_sync:
        raise ConnectionError(error_sync[0])

    log.info("UR3e ha terminado. Enviando script al UR5e...")
    _enviar(ip_ur5e, port, script_ur5e)

    log.info("Script enviado al UR5e.")