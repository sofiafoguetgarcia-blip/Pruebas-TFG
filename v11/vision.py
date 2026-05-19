# -*- coding: utf-8 -*-
"""
vision.py
=========
Lectura directa del JSON generado por visión artificial.

Este archivo NO interpreta la geometría de la baldosa.
Este archivo NO calcula centros.
Este archivo NO aplica offsets.
Este archivo NO usa el ángulo para modificar X/Y.

Si el JSON contiene:
    "robot_x": 168.09,
    "robot_y": -394.87
entonces se devuelve:
    x_robot = 0.16809
    y_robot = -0.39487
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json
import logging
import os

log = logging.getLogger(__name__)


@dataclass
class DeteccionBaldosa:
    numero: int
    x_robot: float
    y_robot: float
    ancho_m: float
    alto_m: float
    angulo_deg: float
    imagen: str = ""
    pipeline: str = ""

    @property
    def lado_menor_m(self) -> float:
        return min(self.ancho_m, self.alto_m)

    @property
    def lado_mayor_m(self) -> float:
        return max(self.ancho_m, self.alto_m)

    def __str__(self) -> str:
        return (
            f"Pieza {self.numero} | "
            f"JSON directo=({self.x_robot:.5f}, {self.y_robot:.5f}) m | "
            f"tam=({self.ancho_m*1000:.1f} x {self.alto_m*1000:.1f}) mm | "
            f"ángulo={self.angulo_deg:.2f}°"
        )


def _leer_json(path_json: str) -> Dict[str, Any]:
    if not os.path.isfile(path_json):
        raise FileNotFoundError(f"No existe el archivo JSON de visión: {path_json}")

    with open(path_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("El JSON debe contener un objeto principal.")
    if "piezas" not in data:
        raise ValueError("El JSON debe contener una lista llamada 'piezas'.")
    if not isinstance(data["piezas"], list):
        raise ValueError("'piezas' debe ser una lista.")
    if len(data["piezas"]) == 0:
        raise ValueError("El JSON no contiene piezas.")

    return data


def _campo_float(pieza: Dict[str, Any], *nombres: str) -> float:
    for nombre in nombres:
        if nombre in pieza:
            return float(pieza[nombre])
    raise ValueError(
        f"Falta uno de estos campos en la pieza del JSON: {', '.join(nombres)}"
    )


def _pieza_a_deteccion(
    pieza: Dict[str, Any],
    imagen: str = "",
    pipeline: str = ""
) -> DeteccionBaldosa:

    if "numero" not in pieza:
        raise ValueError("Falta el campo 'numero' en una pieza del JSON.")

    numero = int(pieza["numero"])

    robot_x_mm = _campo_float(pieza, "robot_x", "x_robot", "x")
    robot_y_mm = _campo_float(pieza, "robot_y", "y_robot", "y")
    ancho_mm = _campo_float(pieza, "ancho_mm", "width_mm", "ancho")
    alto_mm = _campo_float(pieza, "alto_mm", "height_mm", "alto")
    angulo_deg = _campo_float(pieza, "angulo_grados", "angulo_deg", "angle_deg")

    # LECTURA DIRECTA, SIN NINGUNA CORRECCIÓN.
    x_robot_m = robot_x_mm / 1000.0 
    y_robot_m = robot_y_mm / 1000.0 

    log.warning(
        f"PIEZA {numero} | SE ENVÍA JSON TAL CUAL | "
        f"robot_x={robot_x_mm:.2f} mm -> x={x_robot_m:.5f} m | "
        f"robot_y={robot_y_mm:.2f} mm -> y={y_robot_m:.5f} m | "
        f"ángulo leído pero NO usado={angulo_deg:.2f}°"
    )

    return DeteccionBaldosa(
        numero=numero,
        x_robot=x_robot_m,
        y_robot=y_robot_m,
        ancho_m=ancho_mm / 1000.0,
        alto_m=alto_mm / 1000.0,
        angulo_deg=angulo_deg,
        imagen=str(imagen or ""),
        pipeline=str(pipeline or ""),
    )


def cargar_deteccion_json(
    path_json: str,
    numero_pieza: Optional[int] = 1
) -> DeteccionBaldosa:

    data = _leer_json(path_json)
    piezas: List[Dict[str, Any]] = data["piezas"]

    imagen = data.get("imagen", "")
    pipeline = data.get("pipeline", "json_directo")

    if numero_pieza is None:
        pieza = max(
            piezas,
            key=lambda p: float(p.get("ancho_mm", 0.0)) * float(p.get("alto_mm", 0.0))
        )
    else:
        pieza = next(
            (p for p in piezas if int(p.get("numero", -1)) == int(numero_pieza)),
            None,
        )
        if pieza is None:
            disponibles = [p.get("numero") for p in piezas]
            raise ValueError(
                f"No existe la pieza {numero_pieza}. Disponibles: {disponibles}"
            )

    det = _pieza_a_deteccion(pieza, imagen=imagen, pipeline=pipeline)
    log.info(f"JSON leído: {path_json}")
    log.info(str(det))
    return det
