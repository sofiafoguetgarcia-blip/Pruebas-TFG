# -*- coding: utf-8 -*-
"""
robot_comm.py
=============
Comunicación PC ↔ robots usando XML-RPC.

Flujo:
  1. El PC arranca servidor XML-RPC.
  2. El PC envía primero el script al UR5e, que queda esperando can_ur5_start().
  3. El PC envía el script al UR3e.
  4. El UR3e dibuja y llama rpc.ur3_done().
  5. El UR5e detecta can_ur5_start() == True y empieza.
  6. El UR5e termina y llama rpc.ur5_done().
  7. El PC cierra el programa.
"""

import socket
import time
import logging
import threading
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler

from config_xmlrpc_final import UR3E_IP, UR5E_IP, PORT, PC_IP, XMLRPC_PORT, WAIT_TIMEOUT_S

log = logging.getLogger(__name__)

estado = {
    "ur3_done": False,
    "ur5_done": False,
}


def ur3_done():
    log.info("XML-RPC: UR3e ha terminado. Se autoriza inicio del UR5e.")
    estado["ur3_done"] = True
    return True


def can_ur5_start():
    return bool(estado["ur3_done"])


def ur5_done():
    log.info("XML-RPC: UR5e ha terminado.")
    estado["ur5_done"] = True
    return True


class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ("/RPC2",)


def iniciar_servidor_xmlrpc():
    """Arranca el servidor XML-RPC en el PC."""
    server = SimpleXMLRPCServer(
        (PC_IP, XMLRPC_PORT),
        requestHandler=RequestHandler,
        allow_none=True,
        logRequests=False,
    )
    server.register_function(ur3_done, "ur3_done")
    server.register_function(can_ur5_start, "can_ur5_start")
    server.register_function(ur5_done, "ur5_done")

    log.info(f"Servidor XML-RPC escuchando en http://{PC_IP}:{XMLRPC_PORT}/RPC2")
    server.serve_forever()


def _enviar(ip: str, port: int, script: str, timeout: float = 5.0, pausa: float = 2.0) -> None:
    """Envía un URScript a un robot por el puerto 30002."""
    log.info(f"Conectando a {ip}:{port}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((ip, port))
        s.sendall((script + "\n").encode("utf-8"))
        log.info(f"Script enviado a {ip} ({len(script)} caracteres)")
        time.sleep(pausa)
    log.info(f"Conexión cerrada con {ip}")


def enviar_scripts_dual(
    script_ur3e: str,
    script_ur5e: str,
    ip_ur3e: str = UR3E_IP,
    ip_ur5e: str = UR5E_IP,
    port: int = PORT,
) -> None:
    """Envía los scripts y mantiene vivo el servidor XML-RPC hasta que termine UR5e."""
    estado["ur3_done"] = False
    estado["ur5_done"] = False

    log.info("=" * 60)
    log.info("Arrancando comunicación XML-RPC PC ↔ robots")
    log.info("=" * 60)

    hilo_rpc = threading.Thread(target=iniciar_servidor_xmlrpc, daemon=True)
    hilo_rpc.start()
    time.sleep(1.0)

    # UR5e primero: se queda vivo esperando can_ur5_start() en el PC.
    log.info(f"[1/2] Enviando script al UR5e ({ip_ur5e}) para que espere autorización...")
    try:
        _enviar(ip_ur5e, port, script_ur5e)
    except OSError as e:
        raise ConnectionError(f"No se pudo enviar script al UR5e ({ip_ur5e}:{port}): {e}")

    time.sleep(1.0)

    # UR3e después: dibuja y al final llama rpc.ur3_done().
    log.info(f"[2/2] Enviando script al UR3e ({ip_ur3e})...")
    try:
        _enviar(ip_ur3e, port, script_ur3e)
    except OSError as e:
        raise ConnectionError(f"No se pudo enviar script al UR3e ({ip_ur3e}:{port}): {e}")

    log.info("Scripts enviados. El PC queda esperando a que UR5e termine...")

    t0 = time.time()
    while not estado["ur5_done"]:
        time.sleep(1.0)
        if time.time() - t0 > WAIT_TIMEOUT_S:
            raise ConnectionError("Timeout: el PC no recibió ur5_done() del UR5e.")

    log.info("UR5e ha terminado. Comunicación completada correctamente.")
