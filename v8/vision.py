# -*- coding: utf-8 -*-
"""
vision.py
=========
Lectura de datos de visión desde JSON.

Esta versión NO usa cámara, NO procesa imágenes y NO hace detección online/offline.
El programa solo recibe un archivo JSON ya generado por el script de visión artificial
con la lista de piezas detectadas y sus coordenadas para el robot.

Formato esperado del JSON:
{
  "imagen": "DSC07665.jpg",
  "pipeline": "clasico",
  "total_piezas": 9,
  "piezas": [
    {
      "numero": 1,
      "robot_x": 97.74,
      "robot_y": -327.53,
      "ancho_mm": 141.1,
      "alto_mm": 142.08,
      "angulo_grados": 7.5
    }
  ],
  "calibracion": {...}
}

IMPORTANTE:
- El JSON trabaja en milímetros.
- Los robots URScript trabajan en metros.
- Por eso aquí se convierten robot_x, robot_y, ancho_mm y alto_mm de mm a m.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json
import logging
import os

from config import OFFSET_JSON_X_M, OFFSET_JSON_Y_M

log = logging.getLogger(__name__)


@dataclass
class DeteccionBaldosa:
    """Datos mínimos que necesita el resto del programa."""

    numero: int
    x_robot: float          # metros
    y_robot: float          # metros
    ancho_m: float          # metros
    alto_m: float           # metros
    angulo_deg: float       # grados
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
        raise FileNotFoundError(f"No existe el archivo JSON de visión: {path_json}")

    with open(path_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("El JSON de visión debe contener un objeto principal.")

    if "piezas" not in data or not isinstance(data["piezas"], list):
        raise ValueError("El JSON debe contener una lista llamada 'piezas'.")

    if len(data["piezas"]) == 0:
        raise ValueError("El JSON no contiene ninguna pieza detectada.")

    return data


def _pieza_a_deteccion(pieza: Dict[str, Any], imagen: str = "", pipeline: str = "") -> DeteccionBaldosa:
    """Convierte una pieza del JSON a metros para poder usarla en URScript."""

    campos = ["numero", "robot_x", "robot_y", "ancho_mm", "alto_mm", "angulo_grados"]

    for campo in campos:
        if campo not in pieza:
            raise ValueError(f"Falta el campo '{campo}' en una pieza del JSON.")

    return DeteccionBaldosa(
        numero=int(pieza["numero"]),

        x_robot=float(pieza["robot_x"]) / 1000.0 + OFFSET_JSON_X_M,
        y_robot=float(pieza["robot_y"]) / 1000.0 + OFFSET_JSON_Y_M,

        ancho_m=float(pieza["ancho_mm"]) / 1000.0,
        alto_m=float(pieza["alto_mm"]) / 1000.0,

        angulo_deg=float(pieza["angulo_grados"]),

        imagen=str(imagen or ""),
        pipeline=str(pipeline or ""),
    )


def cargar_deteccion_json(path_json: str, numero_pieza: Optional[int] = 1) -> DeteccionBaldosa:
    """
    Lee el JSON de visión y devuelve una única pieza.

    Parámetros:
    - path_json: ruta del archivo datos_robot.json.
    - numero_pieza: número de pieza que se quiere usar. Por defecto usa la pieza 1.

    Si numero_pieza es None, se selecciona la pieza de mayor tamaño.
    """
    data = _leer_json(path_json)
    piezas: List[Dict[str, Any]] = data["piezas"]

    imagen = data.get("imagen", "")
    pipeline = data.get("pipeline", "")

    if numero_pieza is None:
        pieza = max(
            piezas,
            key=lambda p: float(p.get("ancho_mm", 0.0)) * float(p.get("alto_mm", 0.0)),
        )
    else:
        pieza = next((p for p in piezas if int(p.get("numero", -1)) == int(numero_pieza)), None)
        if pieza is None:
            disponibles = [p.get("numero") for p in piezas]
            raise ValueError(
                f"No existe la pieza {numero_pieza} en el JSON. "
                f"Piezas disponibles: {disponibles}"
            )

    det = _pieza_a_deteccion(pieza, imagen=imagen, pipeline=pipeline)
    log.info(f"JSON de visión leído: {path_json}")
    log.info(str(det))
    return det
