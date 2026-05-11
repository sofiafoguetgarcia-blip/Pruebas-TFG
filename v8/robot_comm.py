# -*- coding: utf-8 -*-
"""Comunicación PC -> robots y sincronización robot -> PC."""

import logging
import socket
import threading
import time

from config import PORT_UR5_LISTO_UR3, PORT_UR3_LISTO_UR5, SYNC_MSG_LISTO

log = logging.getLogger(__name__)


def enviar_script(ip: str, port: int, script: str, timeout: float = 10.0, pausa: float = 2.0) -> None:
    log.info(f"Conectando a {ip}:{port}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((ip, port))
        except OSError as e:
            raise ConnectionError(f"No se pudo conectar con {ip}:{port}. Error: {e}")
        s.sendall((script + "\n").encode("utf-8"))
        log.info(f"Script enviado a {ip} ({len(script)} caracteres)")
        time.sleep(pausa)


def esperar_mensaje(puerto: int, esperado: str = SYNC_MSG_LISTO, timeout: float = 1200.0, descripcion: str = "") -> None:
    desc = descripcion or f"puerto {puerto}"
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", puerto))
    srv.listen(1)
    srv.settimeout(timeout)
    log.info(f"PC escuchando en {puerto}: {desc}")

    try:
        conn, addr = srv.accept()
    except socket.timeout:
        srv.close()
        raise TimeoutError(f"Timeout esperando {esperado} en {desc}")

    data = conn.recv(1024).decode("utf-8", errors="ignore").strip()
    conn.close()
    srv.close()
    log.info(f"Mensaje recibido desde {addr}: {data}")

    if esperado not in data:
        raise ConnectionError(f"Mensaje inesperado en {desc}. Esperado={esperado}, recibido={data}")


def _servidor_en_hilo(puerto: int, descripcion: str):
    errores = []

    def worker():
        try:
            esperar_mensaje(puerto, SYNC_MSG_LISTO, descripcion=descripcion)
        except Exception as e:
            errores.append(e)

    hilo = threading.Thread(target=worker, daemon=True)
    hilo.start()
    return hilo, errores


def ejecutar_flujo_completo(script_ur5_recoger: str, script_ur3_dibujar: str, script_ur5_devolver: str, ip_ur5e: str, ip_ur3e: str, port: int) -> None:
    """
    Orden seguro:
    1) PC abre servidor para UR5e.
    2) PC envía script recoger al UR5e.
    3) UR5e avisa LISTO.
    4) PC abre servidor para UR3e.
    5) PC envía script dibujar al UR3e.
    6) UR3e avisa LISTO.
    7) PC envía script devolver al UR5e.
    """
    log.info("PASO 1/7: esperando aviso futuro del UR5e")
    hilo5, err5 = _servidor_en_hilo(PORT_UR5_LISTO_UR3, "UR5e -> PC: baldosa en DROP_ZONE")
    time.sleep(1.0)

    log.info("PASO 2/7: enviando UR5e recoger")
    enviar_script(ip_ur5e, port, script_ur5_recoger)

    log.info("PASO 3/7: esperando LISTO del UR5e")
    hilo5.join()
    if err5:
        raise err5[0]

    log.info("PASO 4/7: esperando aviso futuro del UR3e")
    hilo3, err3 = _servidor_en_hilo(PORT_UR3_LISTO_UR5, "UR3e -> PC: dibujo terminado")
    time.sleep(1.0)

    log.info("PASO 5/7: enviando UR3e dibujar")
    enviar_script(ip_ur3e, port, script_ur3_dibujar)

    log.info("PASO 6/7: esperando LISTO del UR3e")
    hilo3.join()
    if err3:
        raise err3[0]

    log.info("PASO 7/7: enviando UR5e devolver")
    enviar_script(ip_ur5e, port, script_ur5_devolver)
    log.info("Flujo completo enviado correctamente.")
