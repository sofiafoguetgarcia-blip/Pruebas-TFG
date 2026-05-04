# -*- coding: utf-8 -*-
"""
robot_comm.py
=============
Envía los scripts y usa XML-RPC en el PC como coordinador.

UR5e pregunta al PC si puede empezar.
UR3e avisa al PC cuando termina.
"""

import socket
import time
import logging
import threading
from xmlrpc.server import SimpleXMLRPCServer

from config_xmlrpc import UR3E_IP, UR5E_IP, PORT, PC_IP, XMLRPC_PORT

log = logging.getLogger(__name__)


class SyncState:
    def __init__(self):
        self._lock = threading.Lock()
        self.ur3_finished = False

    def ur3_done(self):
        with self._lock:
            self.ur3_finished = True
        log.info("XML-RPC: UR3e ha llamado ur3_done().")
        return 1

    def can_ur5_start(self):
        with self._lock:
            return 1 if self.ur3_finished else 0

    def reset(self):
        with self._lock:
            self.ur3_finished = False
        return 1


def arrancar_servidor_xmlrpc(state: SyncState):
    server = SimpleXMLRPCServer((PC_IP, XMLRPC_PORT), allow_none=True, logRequests=False)
    server.register_instance(state)
    log.info(f"XML-RPC escuchando en http://{PC_IP}:{XMLRPC_PORT}/RPC2")
    server.serve_forever()


def _enviar(ip: str, port: int, script: str, timeout: float = 5.0, pausa: float = 2.0) -> None:
    log.info(f"  Conectando a {ip}:{port}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((ip, port))
        s.sendall((script + "\n").encode("utf-8"))
        log.info(f"  Script enviado a {ip} ({len(script)} chars)")
        time.sleep(pausa)
    log.info(f"  Conexión cerrada: {ip}")


def enviar_scripts_dual(script_ur3e: str, script_ur5e: str,
                        ip_ur3e: str = UR3E_IP, ip_ur5e: str = UR5E_IP,
                        port: int = PORT) -> None:
    log.info("=" * 55)
    log.info("Enviando scripts con sincronización XML-RPC")
    log.info("=" * 55)

    state = SyncState()
    hilo_rpc = threading.Thread(target=arrancar_servidor_xmlrpc, args=(state,), daemon=True)
    hilo_rpc.start()
    time.sleep(1.0)

    # UR5e primero: se queda esperando al PC.
    log.info(f"[1/2] Enviando script al UR5e ({ip_ur5e})...")
    try:
        _enviar(ip_ur5e, port, script_ur5e)
    except OSError as e:
        raise ConnectionError(f"No se pudo conectar al UR5e ({ip_ur5e}:{port}): {e}")

    time.sleep(1.0)

    # UR3e segundo: dibuja y al terminar llama ur3_done() al PC.
    log.info(f"[2/2] Enviando script al UR3e ({ip_ur3e})...")
    try:
        _enviar(ip_ur3e, port, script_ur3e)
    except OSError as e:
        raise ConnectionError(f"No se pudo conectar al UR3e ({ip_ur3e}:{port}): {e}")

    log.info("Scripts enviados. Mantén esta consola abierta.")
