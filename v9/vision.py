# =========================
# vision.py
# =========================

# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json
import logging
import os

from config import OFFSETS_POR_PIEZA_M

log = logging.getLogger(__name__)


# =============================================================================
# OFFSETS INDIVIDUALES POR PIEZA
# =============================================================================

OFFSETS_POR_PIEZA_M = {   # cuanto más se ha de ajustar al centro de la pieza en X e Y

    1: (0.07032, -0.06907),

    2: (0.34221, -0.32834),

    3: (0.42012, -0.39884),

    4: (-0.15430, 0.14440),

    5: (0.15521, -0.14665),

    6: (-0.08046, 0.06469),

    7: (0.18593, -0.16752),

    8: (-0.34024, 0.32781),

    9: (-0.07751, 0.08387),
}


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
            f"robot=({self.x_robot:.4f}, {self.y_robot:.4f}) m | "
            f"tam=({self.ancho_m*1000:.1f} x {self.alto_m*1000:.1f}) mm | "
            f"ángulo={self.angulo_deg:.2f}°"
        )


def _leer_json(path_json: str) -> Dict[str, Any]:

    if not os.path.isfile(path_json):
        raise FileNotFoundError(
            f"No existe el archivo JSON de visión: {path_json}"
        )

    with open(path_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            "El JSON de visión debe contener un objeto principal."
        )

    if "piezas" not in data:
        raise ValueError(
            "El JSON debe contener una lista llamada 'piezas'."
        )

    if not isinstance(data["piezas"], list):
        raise ValueError(
            "'piezas' debe ser una lista."
        )

    if len(data["piezas"]) == 0:
        raise ValueError(
            "El JSON no contiene piezas."
        )

    return data

def _pieza_a_deteccion(
    pieza: Dict[str, Any],
    imagen: str = "",
    pipeline: str = ""
) -> DeteccionBaldosa:

    campos = [
        "numero",
        "robot_x",
        "robot_y",
        "ancho_mm",
        "alto_mm",
        "angulo_grados"
    ]

    for campo in campos:

        if campo not in pieza:
            raise ValueError(
                f"Falta el campo '{campo}' en una pieza del JSON."
            )

    numero = int(pieza["numero"])

    offset_x, offset_y = OFFSETS_POR_PIEZA_M.get(
        numero,
        (0.0, 0.0)
    )

    return DeteccionBaldosa(

        numero=numero,

        x_robot=float(pieza["robot_x"]) / 1000.0 + offset_x,

        y_robot=float(pieza["robot_y"]) / 1000.0 + offset_y,

        ancho_m=float(pieza["ancho_mm"]) / 1000.0,

        alto_m=float(pieza["alto_mm"]) / 1000.0,

        angulo_deg=float(pieza["angulo_grados"]),

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

    pipeline = data.get("pipeline", "")

    if numero_pieza is None:

        pieza = max(
            piezas,
            key=lambda p:
                float(p.get("ancho_mm", 0.0))
                *
                float(p.get("alto_mm", 0.0))
        )

    else:

        pieza = next(
            (
                p for p in piezas
                if int(p.get("numero", -1)) == int(numero_pieza)
            ),
            None
        )

        if pieza is None:

            disponibles = [p.get("numero") for p in piezas]

            raise ValueError(
                f"No existe la pieza {numero_pieza}. "
                f"Disponibles: {disponibles}"
            )

    det = _pieza_a_deteccion(
        pieza,
        imagen=imagen,
        pipeline=pipeline
    )

    log.info(f"JSON leído: {path_json}")

    log.info(str(det))

    return det