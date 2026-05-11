# -*- coding: utf-8 -*-
"""
main.py
=======
Demo UR5e + UR3e adaptada al estado actual real del proyecto.

FLUJO:
1) Se lee un JSON generado previamente por el script de visión artificial.
2) Del JSON se toma la pieza seleccionada: posición, tamaño y orientación.
3) El UR5e va a la posición de esa pieza.
4) Detecta la mesa mediante fuerza.
5) Simula recoger la baldosa.
6) Lleva la baldosa a la zona compartida.
7) UR3e dibuja sobre la zona compartida.
8) UR5e vuelve y simula devolver la baldosa.

IMPORTANTE:
- Este archivo NO usa cámara.
- Este archivo NO procesa una imagen de escena.
- La visión ya se considera hecha antes.
- El programa solo usa el archivo JSON de salida de visión.
"""

import argparse
import logging
import sys

from config import (
    UR3E_IP,
    UR5E_IP,
    PORT,
    DRAWING_SCALE_ON_TILE,
    MAX_DRAWING_WIDTH_M,
    MIN_DRAWING_WIDTH_M,
)

# La visión ahora solo consiste en leer el JSON ya generado.
from vision import cargar_deteccion_json

from image_processing import (
    cargar_imagen,
    preprocesar_imagen,
    guardar_debug,
)

from trajectory import extraer_trayectorias

from urscript_generator import (
    generar_script_ur5e_recoger,
    generar_script_ur3e_dibujar,
    generar_script_ur5e_devolver,
    guardar_script,
)

from robot_comm import ejecutar_flujo_completo


# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger(__name__)


# =============================================================================
# ARCHIVOS POR DEFECTO
# =============================================================================

# Imagen del dibujo que hará el UR3e.
DEFAULT_DIBUJO = r"C:\Users\Sofia\Desktop\codigosPythonUR\imagenes\oso.webp"

# JSON generado por el script de visión artificial.
DEFAULT_JSON =  r"C:\Users\Sofia\Desktop\codigosPythonUR\dibujo_colab\v8\datos_robot.json"


# =============================================================================
# ARGUMENTOS
# =============================================================================

def parse_args():
    p = argparse.ArgumentParser(
        description="Demo UR5e + UR3e usando únicamente JSON de visión"
    )

    p.add_argument(
        "--dibujo",
        default=DEFAULT_DIBUJO,
        help="Imagen del dibujo que hará el UR3e"
    )

    p.add_argument(
        "--json",
        default=DEFAULT_JSON,
        help="Archivo JSON generado por la visión artificial"
    )

    p.add_argument(
        "--pieza",
        default=1,
        type=int,
        help="Número de pieza del JSON que se quiere usar"
    )

    p.add_argument(
        "--ip3",
        default=UR3E_IP
    )

    p.add_argument(
        "--ip5",
        default=UR5E_IP
    )

    p.add_argument(
        "--port",
        default=PORT,
        type=int
    )

    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Genera scripts pero NO los envía a los robots"
    )

    p.add_argument(
        "--out-recoger",
        default="script_ur5e_recoger.urscript"
    )

    p.add_argument(
        "--out-dibujar",
        default="script_ur3e_dibujar.urscript"
    )

    p.add_argument(
        "--out-devolver",
        default="script_ur5e_devolver.urscript"
    )

    p.add_argument(
        "--debug-edges",
        default="debug_edges.png"
    )

    return p.parse_args()


# =============================================================================
# ESCALADO DEL DIBUJO
# =============================================================================

def calcular_ancho_dibujo(det):
    ancho = det.lado_menor_m * DRAWING_SCALE_ON_TILE
    ancho = max(
        MIN_DRAWING_WIDTH_M,
        min(MAX_DRAWING_WIDTH_M, ancho)
    )
    return ancho


# =============================================================================
# MAIN
# =============================================================================

def main():
    args = parse_args()

    log.info("=" * 70)
    log.info(" DEMO UR5e + UR3e CON JSON DE VISIÓN ")
    log.info("=" * 70)

    log.info(f"JSON visión      : {args.json}")
    log.info(f"Pieza JSON       : {args.pieza}")
    log.info(f"Dibujo           : {args.dibujo}")
    log.info(f"UR5e             : {args.ip5}:{args.port}")
    log.info(f"UR3e             : {args.ip3}:{args.port}")
    log.info(f"Dry-run          : {args.dry_run}")

    # -------------------------------------------------------------------------
    # 1) LEER JSON DE VISIÓN
    # -------------------------------------------------------------------------

    try:
        det = cargar_deteccion_json(
            args.json,
            numero_pieza=args.pieza
        )
    except Exception as e:
        log.error(f"Error leyendo JSON de visión: {e}")
        sys.exit(1)

    x_baldosa_ur5 = det.x_robot
    y_baldosa_ur5 = det.y_robot
    angulo_baldosa = det.angulo_deg

    log.info(f"Posición UR5e X  : {x_baldosa_ur5:.4f} m")
    log.info(f"Posición UR5e Y  : {y_baldosa_ur5:.4f} m")
    log.info(f"Ángulo baldosa   : {angulo_baldosa:.2f} grados")

    # -------------------------------------------------------------------------
    # 2) CALCULAR TAMAÑO DEL DIBUJO
    # -------------------------------------------------------------------------

    try:
        ancho_dibujo_m = calcular_ancho_dibujo(det)
    except Exception as e:
        log.error(f"Error calculando tamaño del dibujo: {e}")
        sys.exit(1)

    log.info(f"Ancho dibujo     : {ancho_dibujo_m*1000:.1f} mm")

    # -------------------------------------------------------------------------
    # 3) PROCESAR IMAGEN DEL DIBUJO
    # -------------------------------------------------------------------------

    try:
        img = cargar_imagen(args.dibujo)
        edges = preprocesar_imagen(img)
        guardar_debug(edges, args.debug_edges)

        trayectorias = extraer_trayectorias(
            edges,
            img.shape,
            ancho_dibujo_m=ancho_dibujo_m
        )

    except Exception as e:
        log.error(f"Error procesando dibujo: {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # 4) GENERAR SCRIPTS
    # -------------------------------------------------------------------------

    try:
        script_recoger = generar_script_ur5e_recoger(
            x_baldosa_ur5,
            y_baldosa_ur5,
            angulo_baldosa
        )

        script_dibujar = generar_script_ur3e_dibujar(
            trayectorias
        )

        script_devolver = generar_script_ur5e_devolver(
            x_baldosa_ur5,
            y_baldosa_ur5
        )

    except Exception as e:
        log.error(f"Error generando URScript: {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # 5) GUARDAR SCRIPTS
    # -------------------------------------------------------------------------

    guardar_script(script_recoger, args.out_recoger)
    guardar_script(script_dibujar, args.out_dibujar)
    guardar_script(script_devolver, args.out_devolver)

    log.info("Scripts generados correctamente")

    # -------------------------------------------------------------------------
    # 6) DRY RUN
    # -------------------------------------------------------------------------

    if args.dry_run:
        log.info("Dry-run activado: no se envía nada a los robots")
        return

    # -------------------------------------------------------------------------
    # 7) EJECUTAR FLUJO REAL
    # -------------------------------------------------------------------------

    try:
        ejecutar_flujo_completo(
            script_ur5_recoger=script_recoger,
            script_ur3_dibujar=script_dibujar,
            script_ur5_devolver=script_devolver,
            ip_ur5e=args.ip5,
            ip_ur3e=args.ip3,
            port=args.port,
        )

    except Exception as e:
        log.error(f"Error comunicación: {e}")
        sys.exit(1)

    log.info("Proceso completo finalizado")


if __name__ == "__main__":
    main()
