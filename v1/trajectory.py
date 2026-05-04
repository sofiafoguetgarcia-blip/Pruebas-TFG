# -*- coding: utf-8 -*-
"""
trajectory.py
=============
Extracción y filtrado de trayectorias 2-D (en metros) a partir de
un mapa de bordes. Igual que el proyecto single-robot.
"""

import cv2
import logging
import numpy as np
from typing import List, Tuple

from config_v0 import (
    MAX_ANCHO_M, EPSILON_PX, DECIMATE_STEP,
    MIN_PUNTOS_CONTORNO, MIN_LONGITUD_PX, MAX_PUNTOS_TOTAL,
)

log = logging.getLogger(__name__)

Punto       = Tuple[float, float]
Trayectoria = List[Punto]


def extraer_trayectorias(
    edges: np.ndarray,
    img_shape: Tuple[int, int],
) -> List[Trayectoria]:
    """
    Convierte un mapa de bordes en trayectorias métricas centradas en (0,0).
    El origen corresponde al centro del papel (punto coincidente de ambos robots).
    """
    img_h, img_w = img_shape[:2]
    escala = MAX_ANCHO_M / float(img_w)

    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError("No se detectaron contornos en la imagen.")

    log.info(f"Contornos crudos: {len(contours)}")
    contours = sorted(contours, key=lambda c: cv2.arcLength(c, False), reverse=True)

    trayectorias: List[Trayectoria] = []
    total_puntos = 0
    descartados  = 0

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w >= img_w * 0.98 or h >= img_h * 0.98:
            descartados += 1
            continue
        if cv2.arcLength(c, False) < MIN_LONGITUD_PX:
            descartados += 1
            continue

        approx = cv2.approxPolyDP(c, EPSILON_PX, closed=False)
        pts    = approx.reshape(-1, 2)
        if DECIMATE_STEP > 1:
            pts = pts[::DECIMATE_STEP]
        if len(pts) < MIN_PUNTOS_CONTORNO:
            descartados += 1
            continue

        trayectoria = [
            ((px - img_w / 2.0) * escala, -(py - img_h / 2.0) * escala)
            for px, py in pts
        ]
        trayectorias.append(trayectoria)
        total_puntos += len(trayectoria)

        if total_puntos >= MAX_PUNTOS_TOTAL:
            log.warning(f"Límite {MAX_PUNTOS_TOTAL} puntos alcanzado.")
            break

    if not trayectorias:
        raise ValueError("No hay trayectorias válidas tras el filtrado.")

    log.info(
        f"Trayectorias: {len(trayectorias)} válidas | "
        f"{total_puntos} puntos | {descartados} descartados"
    )
    return trayectorias
