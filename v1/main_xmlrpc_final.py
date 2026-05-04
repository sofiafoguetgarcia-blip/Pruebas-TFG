# -*- coding: utf-8 -*-
"""
main.py
=======
Entrada principal del sistema colaborativo UR3e + UR5e con XML-RPC.
"""

import sys
import logging
import argparse

from config_xmlrpc_final import UR3E_IP, UR5E_IP, PORT, Z_PAPEL, XMLRPC_URL
from image_processing import cargar_imagen, preprocesar_imagen, guardar_debug
from trajectory import extraer_trayectorias
from distributor import repartir_trayectorias, resumen_reparto
from urscript_generator_xmlrpc_final import generar_script_ur3e, generar_script_ur5e, guardar_script
from robot_comm_xmlrpc_final import enviar_scripts_dual

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_IMAGE = r"C:\Users\Sofia\Desktop\codigosPythonUR\imagenes\flor_simple.jpg"


def parse_args():
    p = argparse.ArgumentParser(description="Dibujo colaborativo UR3e + UR5e con XML-RPC.")
    p.add_argument("imagen", nargs="?", default=None, help=f"Imagen JPG/PNG. Default: {DEFAULT_IMAGE}")
    p.add_argument("--ip3", default=UR3E_IP, help=f"IP del UR3e. Default: {UR3E_IP}")
    p.add_argument("--ip5", default=UR5E_IP, help=f"IP del UR5e. Default: {UR5E_IP}")
    p.add_argument("--port", default=PORT, type=int, help=f"Puerto URScript. Default: {PORT}")
    p.add_argument("--seed", default=None, type=int, help="Semilla para reparto reproducible.")
    p.add_argument("--dry-run", action="store_true", help="Genera scripts pero no los envía.")
    p.add_argument("--out3", default="script_ur3e.urscript", help="Salida script UR3e.")
    p.add_argument("--out5", default="script_ur5e.urscript", help="Salida script UR5e.")
    p.add_argument("--debug-edges", default="debug_edges.png", help="Imagen de bordes para depuración.")
    return p.parse_args()


def main():
    args = parse_args()
    image_path = args.imagen or DEFAULT_IMAGE

    log.info("=" * 60)
    log.info("Sistema de dibujo colaborativo UR3e + UR5e XML-RPC")
    log.info("=" * 60)
    log.info(f"Imagen  : {image_path}")
    log.info(f"UR3e    : {args.ip3}:{args.port}")
    log.info(f"UR5e    : {args.ip5}:{args.port}")
    log.info(f"XML-RPC : {XMLRPC_URL}")
    log.info(f"Z_PAPEL : {Z_PAPEL * 1000:.1f} mm")
    log.info(f"Seed    : {args.seed}")
    log.info(f"Dry-run : {args.dry_run}")
    log.info("=" * 60)

    try:
        img = cargar_imagen(image_path)
        edges = preprocesar_imagen(img)
        guardar_debug(edges, args.debug_edges)
    except (FileNotFoundError, ValueError) as e:
        log.error(f"Error de imagen: {e}")
        sys.exit(1)

    try:
        trayectorias = extraer_trayectorias(edges, img.shape)
    except ValueError as e:
        log.error(f"Error de trayectorias: {e}")
        sys.exit(1)

    t_ur3e, t_ur5e = repartir_trayectorias(trayectorias, semilla=args.seed)
    log.info(resumen_reparto(t_ur3e, t_ur5e))

    if not t_ur3e:
        log.error("Al UR3e no se le han asignado trayectorias.")
        sys.exit(1)
    if not t_ur5e:
        log.error("Al UR5e no se le han asignado trayectorias.")
        sys.exit(1)

    try:
        script_ur3e = generar_script_ur3e(t_ur3e)
        script_ur5e = generar_script_ur5e(t_ur5e)
    except ValueError as e:
        log.error(f"Error al generar scripts: {e}")
        sys.exit(1)

    guardar_script(script_ur3e, args.out3)
    guardar_script(script_ur5e, args.out5)
    log.info(f"Scripts guardados: {args.out3} | {args.out5}")

    if args.dry_run:
        log.info("Dry-run activado: scripts generados pero NO enviados.")
        return

    try:
        enviar_scripts_dual(
            script_ur3e,
            script_ur5e,
            ip_ur3e=args.ip3,
            ip_ur5e=args.ip5,
            port=args.port,
        )
    except ConnectionError as e:
        log.error(str(e))
        sys.exit(1)

    log.info("Sistema dual finalizado correctamente.")


if __name__ == "__main__":
    main()
