# -*- coding: utf-8 -*-
"""
main.py
=======
Demo UR5e + UR3e leyendo directamente un JSON de visión.

Flujo:
1) Lee el JSON ya generado por visión artificial.
2) Para cada pieza seleccionada, usa robot_x y robot_y TAL CUAL.
3) Genera script UR5e recoger.
4) Genera script UR3e dibujar.
5) Genera script UR5e devolver.
6) Si no está en dry-run, envía los scripts a los robots con sincronización.
"""

import argparse
import logging
import sys
import json

from config import (
    UR3E_IP,
    UR5E_IP,
    PORT,
    DRAWING_SCALE_ON_TILE,
    MAX_DRAWING_WIDTH_M,
    MIN_DRAWING_WIDTH_M,
)

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


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger(__name__)


DEFAULT_DIBUJO = r"C:\Users\Sofia\Desktop\codigosPythonUR\imagenes\flor_simple.jpg"
DEFAULT_JSON = r"C:\Users\Sofia\Desktop\codigosPythonUR\dibujo_colab\v10\datos_robot 1.json"


def parse_args():
    p = argparse.ArgumentParser(
        description="Demo UR5e + UR3e usando JSON directo de visión"
    )

    p.add_argument("--dibujo", default=DEFAULT_DIBUJO)
    p.add_argument("--json", default=DEFAULT_JSON)

    p.add_argument(
        "--pieza",
        default=1,
        type=int,
        help="Número de pieza a procesar. Usa 0 para procesar todas."
    )

    p.add_argument("--ip3", default=UR3E_IP)
    p.add_argument("--ip5", default=UR5E_IP)
    p.add_argument("--port", default=PORT, type=int)

    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Genera scripts pero NO los envía a los robots"
    )

    p.add_argument("--debug-edges", default="debug_edges.png")

    return p.parse_args()


def calcular_ancho_dibujo(det):
    ancho = det.lado_menor_m * DRAWING_SCALE_ON_TILE
    return max(MIN_DRAWING_WIDTH_M, min(MAX_DRAWING_WIDTH_M, ancho))


def cargar_lista_piezas(path_json: str, pieza_arg: int):
    with open(path_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    piezas = data.get("piezas", [])
    if not piezas:
        raise ValueError("El JSON no contiene piezas.")

    if pieza_arg == 0:
        return piezas

    seleccion = [p for p in piezas if int(p.get("numero", -1)) == int(pieza_arg)]
    if not seleccion:
        disponibles = [p.get("numero") for p in piezas]
        raise ValueError(f"No existe la pieza {pieza_arg}. Disponibles: {disponibles}")

    return seleccion


def main():
    args = parse_args()

    log.info("=" * 70)
    log.info(" DEMO UR5e + UR3e CON JSON DIRECTO ")
    log.info("=" * 70)

    try:
        piezas_a_procesar = cargar_lista_piezas(args.json, args.pieza)
    except Exception as e:
        log.error(f"Error leyendo JSON: {e}")
        sys.exit(1)

    log.info(f"Piezas a procesar: {[p.get('numero') for p in piezas_a_procesar]}")

    try:
        img = cargar_imagen(args.dibujo)
        edges = preprocesar_imagen(img)
        guardar_debug(edges, args.debug_edges)
    except Exception as e:
        log.error(f"Error procesando dibujo: {e}")
        sys.exit(1)

    for pieza in piezas_a_procesar:
        try:
            numero = int(pieza["numero"])

            log.info("")
            log.info("=" * 60)
            log.info(f"PIEZA {numero}")
            log.info("=" * 60)

            det = cargar_deteccion_json(args.json, numero_pieza=numero)

            x_baldosa_ur5 = det.x_robot
            y_baldosa_ur5 = det.y_robot
            angulo_baldosa = det.angulo_deg

            log.warning(
                f"SE VA A ENVIAR AL UR5e EXACTAMENTE: "
                f"x={x_baldosa_ur5:.5f} m, y={y_baldosa_ur5:.5f} m"
            )

            ancho_dibujo_m = calcular_ancho_dibujo(det)
            log.info(f"Ancho dibujo: {ancho_dibujo_m*1000:.1f} mm")

            trayectorias = extraer_trayectorias(
                edges,
                img.shape,
                ancho_dibujo_m=ancho_dibujo_m
            )

            script_recoger = generar_script_ur5e_recoger(
                x_baldosa_ur5,
                y_baldosa_ur5,
                angulo_baldosa
            )

            script_dibujar = generar_script_ur3e_dibujar(trayectorias)

            script_devolver = generar_script_ur5e_devolver(
                x_baldosa_ur5,
                y_baldosa_ur5
            )

            path_recoger = f"pieza_{numero}_ur5_recoger.urscript"
            path_dibujar = f"pieza_{numero}_ur3_dibujar.urscript"
            path_devolver = f"pieza_{numero}_ur5_devolver.urscript"

            guardar_script(script_recoger, path_recoger)
            guardar_script(script_dibujar, path_dibujar)
            guardar_script(script_devolver, path_devolver)

            if args.dry_run:
                log.info(f"Dry-run pieza {numero}: scripts generados")
                continue

            ejecutar_flujo_completo(
                script_ur5_recoger=script_recoger,
                script_ur3_dibujar=script_dibujar,
                script_ur5_devolver=script_devolver,
                ip_ur5e=args.ip5,
                ip_ur3e=args.ip3,
                port=args.port,
            )

            log.info(f"PIEZA {numero} TERMINADA")

        except Exception as e:
            log.error(f"Error en pieza {pieza}: {e}")
            continue

    log.info("")
    log.info("PROCESO TERMINADO")


if __name__ == "__main__":
    main()
