# -*- coding: utf-8 -*-
"""
main.py
=======
Punto de entrada del sistema UR5e + UR3e para pintar baldosas.

El UR5e mantiene la manipulacion de piezas:
  1. Lee del JSON la posicion de la baldosa en coordenadas del UR5e.
  2. Recoge la baldosa con ventosa.
  3. La deja en la zona compartida.
  4. Vuelve a HOME y espera.

El UR3e realiza una tarea nueva con pincel:
  1. Cuando el UR5e confirma que la baldosa esta en la zona compartida,
     el PC le envia el script de pintura.
  2. Va al cuenco de pintura.
  3. Moja el pincel y limpia el exceso en los laterales del cuenco.
  4. Va a la zona compartida.
  5. Pinta la baldosa completa con pasadas suaves.
  6. Vuelve a HOME y avisa al PC.

Finalmente, el PC espera 5 segundos y envia al UR5e el script para devolver
la baldosa a su posicion original.

Uso rapido:
  python main.py                          # procesa todas las piezas
  python main.py --pieza 3               # solo la pieza numero 3
  python main.py --pieza 1 --dry-run     # genera scripts pero no envia nada
"""

import argparse
import logging
import sys
import json
import os
from typing import Any, Dict, List, Tuple

from config import (
    UR3E_IP,
    UR5E_IP,
    PORT,
)

from vision import cargar_deteccion_json
from urscript_generator import (
    generar_script_ur5e_recoger,
    generar_script_ur3e_pintar,
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


DEFAULT_JSON = r"..\..\codigosPythonUR\dibujo_colab\v13\Robot\resultados\datos_robot.json"
RESULTADOS_DIR = "Resultados"


def parse_args():
    p = argparse.ArgumentParser(
        description="Demo UR5e + UR3e: manipulacion de baldosa y pintura con pincel"
    )
    p.add_argument("--json", default=DEFAULT_JSON,
                   help="Ruta al JSON generado por vision artificial")
    p.add_argument(
        "--pieza",
        default=0,
        type=int,
        help="Numero de pieza a procesar. Con 0 se procesan todas."
    )
    p.add_argument("--ip3", default=UR3E_IP, help="IP del UR3e")
    p.add_argument("--ip5", default=UR5E_IP, help="IP del UR5e")
    p.add_argument("--port", default=PORT, type=int, help="Puerto URScript")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Genera los scripts pero no los envia a los robots"
    )
    return p.parse_args()


def cargar_json_vision(path_json: str) -> Dict[str, Any]:
    """Carga el JSON de vision una sola vez y valida que contenga piezas."""
    with open(path_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    piezas = data.get("piezas", [])
    if not piezas:
        raise ValueError("El JSON no contiene piezas.")

    return data


def seleccionar_piezas(piezas: List[Dict[str, Any]], pieza_arg: int) -> List[Dict[str, Any]]:
    """Selecciona todas las piezas o una pieza concreta segun el argumento recibido."""
    if pieza_arg == 0:
        return piezas

    seleccion = [p for p in piezas if int(p.get("numero", -1)) == int(pieza_arg)]
    if not seleccion:
        disponibles = [p.get("numero") for p in piezas]
        raise ValueError(f"No existe la pieza {pieza_arg}. Disponibles: {disponibles}")

    return seleccion


def guardar_scripts_pieza(
    numero: int,
    script_recoger: str,
    script_pintar: str,
    script_devolver: str,
) -> None:
    """Guarda los tres scripts URScript de la pieza dentro de la carpeta Resultados."""
    os.makedirs(RESULTADOS_DIR, exist_ok=True)

    guardar_script(
        script_recoger,
        os.path.join(RESULTADOS_DIR, f"pieza_{numero}_ur5_recoger.urscript")
    )
    guardar_script(
        script_pintar,
        os.path.join(RESULTADOS_DIR, f"pieza_{numero}_ur3_pintar.urscript")
    )
    guardar_script(
        script_devolver,
        os.path.join(RESULTADOS_DIR, f"pieza_{numero}_ur5_devolver.urscript")
    )


def generar_scripts_pieza(
    numero: int,
    x_baldosa_ur5: float,
    y_baldosa_ur5: float,
    angulo_baldosa: float,
    ancho_baldosa_m: float,
    alto_baldosa_m: float,
) -> Tuple[str, str, str]:
    """Genera los scripts de recogida, pintura y devolucion de una pieza."""
    script_recoger = generar_script_ur5e_recoger(
        x_baldosa_ur5,
        y_baldosa_ur5,
        angulo_baldosa,
    )
    script_pintar = generar_script_ur3e_pintar(
        ancho_baldosa_m=ancho_baldosa_m,
        alto_baldosa_m=alto_baldosa_m,
    )
    script_devolver = generar_script_ur5e_devolver(
        x_baldosa_ur5,
        y_baldosa_ur5,
    )

    guardar_scripts_pieza(numero, script_recoger, script_pintar, script_devolver)
    return script_recoger, script_pintar, script_devolver


def procesar_pieza(pieza: Dict[str, Any], args) -> None:
    """Procesa una pieza completa: lectura del JSON, generacion de scripts y ejecucion."""
    numero = int(pieza["numero"])

    log.info("")
    log.info("=" * 60)
    log.info(f"             PIEZA {numero}")
    log.info("=" * 60)

    det = cargar_deteccion_json(args.json, numero_pieza=numero)

    x_baldosa_ur5 = det.x_robot
    y_baldosa_ur5 = det.y_robot
    angulo_baldosa = det.angulo_deg
    ancho_baldosa_m = det.ancho_m
    alto_baldosa_m = det.alto_m

    log.warning(
        f"SE VA A ENVIAR AL UR5e EXACTAMENTE: "
        f"x={x_baldosa_ur5:.5f} m, y={y_baldosa_ur5:.5f} m"
    )
    log.info(
        f"Baldosa {numero}: {ancho_baldosa_m*1000:.1f} x {alto_baldosa_m*1000:.1f} mm "
        f"-> se pintara con pasadas suaves desde el UR3e"
    )

    script_recoger, script_pintar, script_devolver = generar_scripts_pieza(
        numero=numero,
        x_baldosa_ur5=x_baldosa_ur5,
        y_baldosa_ur5=y_baldosa_ur5,
        angulo_baldosa=angulo_baldosa,
        ancho_baldosa_m=ancho_baldosa_m,
        alto_baldosa_m=alto_baldosa_m,
    )

    if args.dry_run:
        log.info(f"Dry-run pieza {numero}: scripts generados, no se envian")
        return

    ejecutar_flujo_completo(
        script_ur5_recoger=script_recoger,
        script_ur3_dibujar=script_pintar,
        script_ur5_devolver=script_devolver,
        ip_ur5e=args.ip5,
        ip_ur3e=args.ip3,
        port=args.port,
    )

    log.info(f"PIEZA {numero} TERMINADA")


def main():
    args = parse_args()

    log.info("=" * 70)
    log.info(" DEMO UR5e + UR3e: MANIPULACION Y PINTURA CON PINCEL ")
    log.info("=" * 70)

    try:
        datos_json = cargar_json_vision(args.json)
        todas_las_piezas = datos_json["piezas"]
        piezas_a_procesar = seleccionar_piezas(todas_las_piezas, args.pieza)
    except Exception as e:
        log.error(f"Error leyendo JSON: {e}")
        sys.exit(1)

    log.info(f"Piezas a procesar: {[p.get('numero') for p in piezas_a_procesar]}")

    for pieza in piezas_a_procesar:
        try:
            procesar_pieza(pieza, args)
        except Exception as e:
            log.error(f"Error en pieza {pieza}: {e}")
            continue

    log.info("")
    log.info("PROCESO TERMINADO")


if __name__ == "__main__":
    main()
