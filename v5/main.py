# -*- coding: utf-8 -*-
"""
main.py
=======
Punto de entrada del sistema de dibujo colaborativo UR3e + UR5e.

Flujo completo:
  1. Carga y procesa la imagen → mapa de bordes
  2. Extrae trayectorias métricas centradas en el origen (centro del papel)
  3. Reparte trayectorias entre UR3e y UR5e (aleatorio + filtro de alcance)
  4. Genera los dos URScripts
  5. Envía UR5e primero (levanta servidor socket) → luego UR3e

Uso:
    python main.py imagen.jpg
    python main.py imagen.jpg --seed 42         # reparto reproducible
    python main.py imagen.jpg --dry-run         # solo genera scripts, no envía
    python main.py imagen.jpg --ip3 192.168.1.10 --ip5 192.168.1.11
"""

import sys
import logging
import argparse

from config_solucion             import UR3E_IP, UR5E_IP, PORT, Z_PAPEL, F_DETECT
from image_processing     import cargar_imagen, preprocesar_imagen, guardar_debug
from trajectory           import extraer_trayectorias
from distributor          import repartir_trayectorias, resumen_reparto
from urscript_generator_solucion   import generar_script_ur3e, generar_script_ur5e, guardar_script
from robot_comm_solucion           import enviar_scripts_dual

# =============================================================================
# LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_IMAGE = r"C:\Users\Sofia\Desktop\codigosPythonUR\imagenes\flor_simple.jpg"


def parse_args():
    p = argparse.ArgumentParser(
        description="Dibujo colaborativo UR3e + UR5e."
    )
    p.add_argument("imagen", nargs="?", default=None,
                   help=f"Imagen JPG/PNG. Default: {DEFAULT_IMAGE}")
    p.add_argument("--ip3",  default=UR3E_IP,
                   help=f"IP del UR3e. Default: {UR3E_IP}")
    p.add_argument("--ip5",  default=UR5E_IP,
                   help=f"IP del UR5e. Default: {UR5E_IP}")
    p.add_argument("--port", default=PORT, type=int,
                   help=f"Puerto URScript. Default: {PORT}")
    p.add_argument("--seed", default=None, type=int,
                   help="Semilla aleatoria para el reparto (reproducibilidad).")
    p.add_argument("--dry-run", action="store_true",
                   help="Genera los scripts pero NO los envía a los robots.")
    p.add_argument("--out3",  default="script_ur3e.urscript",
                   help="Archivo de salida script UR3e.")
    p.add_argument("--out5",  default="script_ur5e.urscript",
                   help="Archivo de salida script UR5e.")
    p.add_argument("--debug-edges", default="debug_edges.png",
                   help="Imagen de bordes para depuración.")
    return p.parse_args()


def main():
    args = parse_args()
    image_path = args.imagen or DEFAULT_IMAGE

    log.info("=" * 60)
    log.info("  Sistema de dibujo colaborativo  UR3e + UR5e")
    log.info("=" * 60)
    log.info(f"  Imagen     : {image_path}")
    log.info(f"  UR3e       : {args.ip3}:{args.port}")
    log.info(f"  UR5e       : {args.ip5}:{args.port}")
    log.info(f"  Z_PAPEL    : {Z_PAPEL * 1000:.1f} mm sobre contacto")
    log.info(f"  F_DETECT   : {F_DETECT:.1f} N (umbral detección mesa)")
    log.info(f"  Semilla    : {args.seed}")
    log.info(f"  Dry-run    : {args.dry_run}")
    log.info("  Sensor F/T : Habilitado (detección automática de mesa)")
    log.info("=" * 60)

    # ------------------------------------------------------------------
    # 1. Procesar imagen
    # ------------------------------------------------------------------
    try:
        img   = cargar_imagen(image_path)
        edges = preprocesar_imagen(img)
        guardar_debug(edges, args.debug_edges)
    except (FileNotFoundError, ValueError) as e:
        log.error(f"Error de imagen: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2. Extraer trayectorias
    # ------------------------------------------------------------------
    try:
        trayectorias = extraer_trayectorias(edges, img.shape)
    except ValueError as e:
        log.error(f"Error de trayectorias: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3. Repartir entre robots
    # ------------------------------------------------------------------
    t_ur3e, t_ur5e = repartir_trayectorias(trayectorias, semilla=args.seed)
    log.info(resumen_reparto(t_ur3e, t_ur5e))

    if not t_ur3e:
        log.error("Al UR3e no le han asignado trayectorias. "
                  "Revisa MAX_ANCHO_M o la posición del papel.")
        sys.exit(1)
    if not t_ur5e:
        log.error("Al UR5e no le han asignado trayectorias.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 4. Generar URScripts
    # ------------------------------------------------------------------
    try:
        script_ur3e = generar_script_ur3e(t_ur3e)
        script_ur5e = generar_script_ur5e(t_ur5e)
    except ValueError as e:
        log.error(f"Error al generar scripts: {e}")
        sys.exit(1)

    guardar_script(script_ur3e, args.out3)
    guardar_script(script_ur5e, args.out5)
    log.info(f"Scripts guardados: {args.out3}  |  {args.out5}")

    # ------------------------------------------------------------------
    # 5. Enviar a los robots
    # ------------------------------------------------------------------
    if args.dry_run:
        log.info("Dry-run activado — scripts generados pero NO enviados.")
        log.info(f"Revisa los scripts en: {args.out3} y {args.out5}")
        return

    try:
        enviar_scripts_dual(
            script_ur3e, script_ur5e,
            ip_ur3e=args.ip3,
            ip_ur5e=args.ip5,
            port=args.port,
        )
    except ConnectionError as e:
        log.error(str(e))
        sys.exit(1)

    log.info("Sistema dual en marcha. Sigue el progreso en las tablets.")


if __name__ == "__main__":
    main()
